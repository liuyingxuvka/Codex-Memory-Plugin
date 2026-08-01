"""Single scheduled local maintenance owner with current-only cycle evidence.

Sleep remains the sole canonical publisher.  The local cycle owns only the
ordered Sleep -> Dream workflow, its independent task lease, and the delegated
use of the one global maintenance writer lease.
"""

from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path
from typing import Any, Callable

from local_kb.common import utc_now_iso
from local_kb.dream import run_dream_maintenance
from local_kb.lifecycle import run_incremental_sleep
from local_kb.maintenance_lanes import (
    CYCLE_RECEIPT_SCHEMA,
    acquire_cycle_lease,
    acquire_global_write_lease,
    canonical_digest,
    current_toolchain_digest,
    delegate_global_write_lease,
    file_content_identity,
    heartbeat_global_write_lease,
    redact_lease_secrets,
    release_cycle_lease,
    release_delegated_write_lease,
    release_global_write_lease,
    source_component_digest,
    tree_content_identity,
    validate_cycle_receipt_v3,
    validate_global_write_delegation,
    write_cycle_receipt_v3,
)


LOCAL_CYCLE_KIND = "local-maintenance-cycle"
LOCAL_CYCLE_OWNER = "kb-sleep-maintenance"
LOCAL_CYCLE_AUTOMATION_ID = "kb-sleep"
LOCAL_CYCLE_WORKFLOW_REVISION = "local-sleep-dream.v3"
LOCAL_CYCLE_SEQUENCE = ("sleep", "dream")
LOCAL_SUCCESS_STATES = {"completed", "completed_with_blocks", "progress_saved"}


def _absolute_receipt_path(repo_root: Path, raw: object) -> Path | None:
    text = str(raw or "").strip()
    if not text:
        return None
    path = Path(text)
    if not path.is_absolute():
        path = repo_root / path
    return path if path.is_file() else None


def _receipt_identity(repo_root: Path, raw: object) -> tuple[str, str]:
    path = _absolute_receipt_path(repo_root, raw)
    if path is None:
        return "", ""
    return str(path), "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _local_state_snapshot(repo_root: Path) -> dict[str, Any]:
    relative_files = (
        Path("kb/history/events.jsonl"),
        Path("kb/history/lifecycle/current.json"),
        Path("kb/history/lifecycle/sleep_state.json"),
        Path("kb/history/lifecycle/dream_handoffs.jsonl"),
        Path("kb/history/lifecycle/dream_handoff_acks.jsonl"),
        Path(".local/khaos-brain/logicguard-authority/current-generation.json"),
    )
    return {
        "files": {
            path.as_posix(): file_content_identity(repo_root / path)
            for path in relative_files
        },
        "trees": {
            "kb/public": tree_content_identity(repo_root / "kb" / "public"),
            "kb/candidates": tree_content_identity(repo_root / "kb" / "candidates"),
        },
    }


def _local_source_digest() -> str:
    return source_component_digest(
        (
            Path(__file__),
            Path(__file__).with_name("lifecycle.py"),
            Path(__file__).with_name("dream.py"),
            Path(__file__).with_name("maintenance_lanes.py"),
        )
    )


def _local_child_plan_digest() -> str:
    return canonical_digest(
        {
            "workflow_revision": LOCAL_CYCLE_WORKFLOW_REVISION,
            "sequence": list(LOCAL_CYCLE_SEQUENCE),
            "dream_gate": "sleep-completed-unblocked-only",
            "writer_policy": "single-global-writer-delegated-to-sleep-only",
        }
    )


def _phase_record(
    *,
    phase_id: str,
    status: str,
    reason_code: str,
    run_id: str,
    started_at: str,
    finished_at: str,
    input_digest: str,
    result: dict[str, Any],
    receipt_path: str = "",
    receipt_digest: str = "",
    lease: object = None,
    cleanup_confirmed: bool = True,
) -> dict[str, Any]:
    raw_exit = result.get("exit_code")
    exit_code = raw_exit if isinstance(raw_exit, int) and not isinstance(raw_exit, bool) else (
        0 if status in {"completed", "completed_with_blocks", "progress_saved", "not_applicable", "not_run"} else 1
    )
    return {
        "phase_id": phase_id,
        "applicability": "not_applicable" if status == "not_run" else "applicable",
        "status": status,
        "reason_code": reason_code,
        "run_id": run_id,
        "started_at": started_at,
        "finished_at": finished_at,
        "receipt_path": receipt_path,
        "receipt_digest": receipt_digest,
        "input_digest": input_digest,
        "output_digest": canonical_digest(result),
        "exit_code": exit_code,
        "cleanup_confirmed": bool(cleanup_confirmed),
        "lease": redact_lease_secrets(lease or {}),
    }


def _execute_writer_phase(
    repo_root: Path,
    *,
    cycle_run_id: str,
    phase_id: str,
    child_run_id: str,
    runner: Callable[[dict[str, str]], dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    lease = acquire_global_write_lease(
        repo_root,
        cycle_kind=LOCAL_CYCLE_KIND,
        run_id=cycle_run_id,
        scope=phase_id,
    )
    events: list[dict[str, Any]] = [
        {"event": "acquire", "phase_id": phase_id, **dict(redact_lease_secrets(lease))}
    ]
    if lease.get("acquired") is not True:
        return (
            {
                "ok": False,
                "status": "blocked",
                "run_id": child_run_id,
                "reason": "global-writer-unavailable",
            },
            events,
            lease,
        )
    lease_id = str(lease["lease_id"])
    lease_token = str(lease["lease_token"])
    delegation = delegate_global_write_lease(
        repo_root,
        lease_id=lease_id,
        lease_token=lease_token,
        child_phase_id=phase_id,
        child_run_id=child_run_id,
        scope=phase_id,
    )
    events.append(
        {"event": "delegate", "phase_id": phase_id, **dict(redact_lease_secrets(delegation))}
    )
    if delegation.get("ok") is not True:
        released = release_global_write_lease(
            repo_root, lease_id=lease_id, lease_token=lease_token
        )
        events.append({"event": "release", "phase_id": phase_id, **released})
        return (
            {
                "ok": False,
                "status": "blocked",
                "run_id": child_run_id,
                "reason": "global-writer-delegation-failed",
            },
            events,
            lease,
        )
    delegation_token = str(delegation["delegation_token"])
    validation = validate_global_write_delegation(
        repo_root,
        lease_id=lease_id,
        child_phase_id=phase_id,
        child_run_id=child_run_id,
        delegation_token=delegation_token,
    )
    events.append({"event": "validate-delegation", "phase_id": phase_id, **validation})
    if validation.get("ok") is not True:
        release_delegated_write_lease(
            repo_root,
            lease_id=lease_id,
            lease_token=lease_token,
            child_phase_id=phase_id,
            child_run_id=child_run_id,
            delegation_token=delegation_token,
        )
        released = release_global_write_lease(
            repo_root, lease_id=lease_id, lease_token=lease_token
        )
        events.append({"event": "release", "phase_id": phase_id, **released})
        return (
            {
                "ok": False,
                "status": "blocked",
                "run_id": child_run_id,
                "reason": "global-writer-delegation-invalid",
            },
            events,
            lease,
        )
    heartbeat_stop = threading.Event()
    heartbeat_failures: list[dict[str, Any]] = []

    def keep_lease_current() -> None:
        while not heartbeat_stop.wait(30.0):
            heartbeat = heartbeat_global_write_lease(
                repo_root,
                lease_id=lease_id,
                lease_token=lease_token,
            )
            if heartbeat.get("ok") is not True:
                heartbeat_failures.append(dict(redact_lease_secrets(heartbeat)))
                return

    heartbeat_thread = threading.Thread(
        target=keep_lease_current,
        name=f"{phase_id}-global-writer-heartbeat",
        daemon=True,
    )
    heartbeat_thread.start()
    try:
        result = runner(
            {
                "lease_id": lease_id,
                "child_phase_id": phase_id,
                "child_run_id": child_run_id,
                "delegation_token": delegation_token,
            }
        )
        if not isinstance(result, dict):
            raise TypeError("maintenance child must return a mapping")
    except Exception as exc:  # Cycle receipt must close the exact failed child attempt.
        result = {
            "ok": False,
            "status": "failed",
            "run_id": child_run_id,
            "reason": "child-exception",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
    finally:
        heartbeat_stop.set()
        heartbeat_thread.join(timeout=2.0)
    events.append(
        {
            "event": "heartbeat-summary",
            "phase_id": phase_id,
            "ok": not heartbeat_failures and not heartbeat_thread.is_alive(),
            "failures": heartbeat_failures,
        }
    )
    if (heartbeat_failures or heartbeat_thread.is_alive()) and str(
        result.get("status") or ""
    ) != "failed":
        result = {
            **result,
            "ok": False,
            "status": "failed",
            "reason": "global-writer-heartbeat-unconfirmed",
        }
    delegated_release = release_delegated_write_lease(
        repo_root,
        lease_id=lease_id,
        lease_token=lease_token,
        child_phase_id=phase_id,
        child_run_id=child_run_id,
        delegation_token=delegation_token,
    )
    events.append(
        {"event": "release-delegation", "phase_id": phase_id, **delegated_release}
    )
    root_release = release_global_write_lease(
        repo_root, lease_id=lease_id, lease_token=lease_token
    )
    events.append({"event": "release", "phase_id": phase_id, **root_release})
    cleanup_confirmed = bool(
        delegated_release.get("ok") is True and root_release.get("released") is True
    )
    if not cleanup_confirmed and str(result.get("status") or "") != "failed":
        result = {
            **result,
            "ok": False,
            "status": "failed",
            "reason": "global-writer-release-unconfirmed",
        }
    return result, events, {**lease, "cleanup_confirmed": cleanup_confirmed}


def _sleep_status(sleep: dict[str, Any]) -> tuple[str, str]:
    final_state = str(sleep.get("final_run_state") or sleep.get("status") or "")
    blockers = list(sleep.get("blockers") or [])
    if final_state == "completed" and not blockers:
        return "completed", "sleep-completed"
    if final_state == "completed_with_blocks":
        return "completed_with_blocks", "sleep-completed-with-blocks"
    if final_state == "progress_saved":
        return "progress_saved", "sleep-progress-saved"
    if final_state == "blocked" or str(sleep.get("status") or "") == "blocked":
        return "blocked", str(sleep.get("reason") or "sleep-blocked")
    return "failed", str(sleep.get("reason") or "sleep-failed")


def _dream_status(dream: dict[str, Any]) -> tuple[str, str]:
    status = str(dream.get("status") or "")
    if status == "completed":
        no_delta = int(dream.get("valuable_opportunity_count") or 0) == 0
        return "completed", "dream-no-delta" if no_delta else "dream-completed"
    if status in {"no_delta", "no_delta_closed"}:
        return "completed", "dream-no-delta"
    if status == "blocked":
        return "blocked", str(dream.get("reason") or "dream-blocked")
    if status == "skipped":
        return "blocked", str(dream.get("reason") or "dream-skipped")
    return "failed", str(dream.get("reason") or "dream-failed")


def _response_from_receipt(
    receipt: dict[str, Any],
    *,
    cycle_path: Path,
    idempotent_reuse: bool,
) -> dict[str, Any]:
    outputs = dict(receipt.get("outputs") or {})
    sleep = dict(outputs.get("sleep") or {})
    dream = dict(outputs.get("dream") or {})
    status = str(receipt.get("status") or "failed")
    return {
        **sleep,
        "ok": status in LOCAL_SUCCESS_STATES,
        "status": status,
        "final_run_state": status,
        "sleep_final_run_state": str(
            sleep.get("final_run_state") or outputs.get("sleep_status") or ""
        ),
        "local_cycle": {
            "schema_version": CYCLE_RECEIPT_SCHEMA,
            "status": status,
            "mode": str(outputs.get("mode") or "fresh_cycle"),
            "sequence": list(receipt.get("sequence") or []),
            "sleep": sleep,
            "dream": dream,
            "phases": list(receipt.get("phases") or []),
            "cycle_receipt_path": str(cycle_path),
            "cycle_receipt_digest": str(receipt.get("payload_digest") or ""),
        },
        "idempotent_reuse": idempotent_reuse,
    }


def run_local_maintenance_cycle(
    repo_root: Path,
    *,
    run_id: str | None = None,
    max_observations: int = 250,
    soft_deadline_seconds: float | None = None,
) -> dict[str, Any]:
    """Run writer-delegated Sleep, then bounded read-only Dream, in one task."""

    repo_root = Path(repo_root)
    resolved_run_id = str(run_id or "kb-local-maintenance")
    request_parameters = {
        "max_observations": int(max_observations),
        "soft_deadline_seconds": (
            None
            if soft_deadline_seconds is None
            else float(soft_deadline_seconds)
        ),
    }
    request_digest = canonical_digest(request_parameters)
    source_digest = _local_source_digest()
    toolchain_digest = current_toolchain_digest()
    child_plan_digest = _local_child_plan_digest()
    current_snapshot = _local_state_snapshot(repo_root)
    current_state_digest = canonical_digest(current_snapshot)
    cycle_root = repo_root / ".local" / "maintenance-cycles" / resolved_run_id
    cycle_path = cycle_root / "cycle-receipt.json"
    if cycle_path.is_file():
        try:
            prior = json.loads(cycle_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            prior = {}
        validation = validate_cycle_receipt_v3(
            prior if isinstance(prior, dict) else {},
            expected_kind=LOCAL_CYCLE_KIND,
            expected_run_id=resolved_run_id,
            expected_owner=LOCAL_CYCLE_OWNER,
            expected_automation_id=LOCAL_CYCLE_AUTOMATION_ID,
            expected_workflow_revision=LOCAL_CYCLE_WORKFLOW_REVISION,
            expected_request_digest=request_digest,
            expected_source_component_digest=source_digest,
            expected_toolchain_digest=toolchain_digest,
            expected_child_plan_digest=child_plan_digest,
            current_state_digest=current_state_digest,
        )
        if validation["ok"]:
            return _response_from_receipt(
                prior, cycle_path=cycle_path, idempotent_reuse=True
            )
        return {
            "ok": False,
            "status": "blocked",
            "final_run_state": "blocked",
            "run_id": resolved_run_id,
            "reason": "cycle-receipt-identity-conflict",
            "receipt_validation": validation,
            "cycle_receipt_path": str(cycle_path),
            "idempotent_reuse": False,
        }

    cycle_lock = acquire_cycle_lease(
        repo_root,
        cycle_kind=LOCAL_CYCLE_KIND,
        run_id=resolved_run_id,
        note="independent local Sleep/Dream scheduled task",
    )
    if cycle_lock.get("acquired") is not True:
        return {
            "ok": False,
            "status": "blocked",
            "final_run_state": "blocked",
            "run_id": resolved_run_id,
            "reason": "local-cycle-task-lease-active",
            "cycle_lock": redact_lease_secrets(cycle_lock),
        }

    created_at = utc_now_iso()
    phases: list[dict[str, Any]] = []
    lease_events: list[dict[str, Any]] = []
    input_snapshot = current_snapshot
    input_digest = canonical_digest(input_snapshot)
    try:
        sleep_run_id = resolved_run_id
        sleep_started = utc_now_iso()
        sleep_input_digest = canonical_digest(_local_state_snapshot(repo_root))
        sleep, sleep_events, sleep_lease = _execute_writer_phase(
            repo_root,
            cycle_run_id=resolved_run_id,
            phase_id="sleep",
            child_run_id=sleep_run_id,
            runner=lambda writer_delegation: run_incremental_sleep(
                repo_root,
                run_id=sleep_run_id,
                max_observations=max_observations,
                soft_deadline_seconds=soft_deadline_seconds,
                writer_delegation=writer_delegation,
            ),
        )
        lease_events.extend(sleep_events)
        sleep_status, sleep_reason = _sleep_status(sleep)
        sleep_receipt_path, sleep_receipt_digest = _receipt_identity(
            repo_root, sleep.get("receipt_path")
        )
        phases.append(
            _phase_record(
                phase_id="sleep",
                status=sleep_status,
                reason_code=sleep_reason,
                run_id=str(sleep.get("run_id") or sleep_run_id),
                started_at=sleep_started,
                finished_at=utc_now_iso(),
                input_digest=sleep_input_digest,
                result=sleep,
                receipt_path=sleep_receipt_path,
                receipt_digest=sleep_receipt_digest,
                lease=sleep_lease,
                cleanup_confirmed=bool(sleep_lease.get("cleanup_confirmed", False)),
            )
        )

        mode = "resume_sleep" if sleep.get("batch_resumed") else "fresh_cycle"
        dream_run_id = f"{resolved_run_id}-dream"
        if sleep_status == "completed":
            dream_started = utc_now_iso()
            dream_input_digest = canonical_digest(_local_state_snapshot(repo_root))
            dream = run_dream_maintenance(repo_root, run_id=dream_run_id)
            dream_lease = {
                "mode": "read-only",
                "global_writer": "not-required",
                "cleanup_confirmed": True,
            }
            lease_events.append(
                {
                    "event": "read-only-phase",
                    "phase_id": "dream",
                    "mode": "read-only",
                    "global_writer": "not-required",
                }
            )
            dream_status, dream_reason = _dream_status(dream)
            dream_receipt_path, dream_receipt_digest = _receipt_identity(
                repo_root, (dream.get("artifact_paths") or {}).get("report_path")
            )
            phases.append(
                _phase_record(
                    phase_id="dream",
                    status=dream_status,
                    reason_code=dream_reason,
                    run_id=str(dream.get("run_id") or dream_run_id),
                    started_at=dream_started,
                    finished_at=utc_now_iso(),
                    input_digest=dream_input_digest,
                    result=dream,
                    receipt_path=dream_receipt_path,
                    receipt_digest=dream_receipt_digest,
                    lease=dream_lease,
                    cleanup_confirmed=bool(dream_lease.get("cleanup_confirmed", False)),
                )
            )
            cycle_status = dream_status
        else:
            downstream_reason = {
                "completed_with_blocks": "sleep-completed-with-blocks",
                "progress_saved": "sleep-progress-saved",
                "blocked": "predecessor-blocked",
                "failed": "predecessor-failed",
            }[sleep_status]
            dream = {
                "ok": False,
                "status": "not_run",
                "run_id": dream_run_id,
                "reason": downstream_reason,
            }
            now = utc_now_iso()
            phases.append(
                _phase_record(
                    phase_id="dream",
                    status="not_run",
                    reason_code=downstream_reason,
                    run_id=dream_run_id,
                    started_at=now,
                    finished_at=now,
                    input_digest=canonical_digest(_local_state_snapshot(repo_root)),
                    result=dream,
                    cleanup_confirmed=True,
                )
            )
            cycle_status = sleep_status

        result_snapshot = _local_state_snapshot(repo_root)
        receipt: dict[str, Any] = {
            "schema_version": CYCLE_RECEIPT_SCHEMA,
            "kind": LOCAL_CYCLE_KIND,
            "cycle_run_id": resolved_run_id,
            "scheduled_owner_skill_id": LOCAL_CYCLE_OWNER,
            "automation_id": LOCAL_CYCLE_AUTOMATION_ID,
            "workflow_revision": LOCAL_CYCLE_WORKFLOW_REVISION,
            "status": cycle_status,
            "request_parameters": request_parameters,
            "request_digest": request_digest,
            "input_snapshot": input_snapshot,
            "input_digest": input_digest,
            "result_snapshot": result_snapshot,
            "result_state_digest": canonical_digest(result_snapshot),
            "source_component_digest": source_digest,
            "toolchain_digest": toolchain_digest,
            "child_plan_digest": child_plan_digest,
            "sequence": list(LOCAL_CYCLE_SEQUENCE),
            "phases": phases,
            "cycle_lease": redact_lease_secrets(cycle_lock),
            "write_lease_events": lease_events,
            "outputs": {
                "mode": mode,
                "sleep_status": sleep_status,
                "sleep": sleep,
                "dream": dream,
            },
            "child_receipts_immutable": True,
            "created_at": created_at,
            "finished_at": utc_now_iso(),
            "payload_digest": "",
        }
        write_cycle_receipt_v3(cycle_path, receipt)
        persisted = json.loads(cycle_path.read_text(encoding="utf-8"))
        return _response_from_receipt(
            persisted, cycle_path=cycle_path, idempotent_reuse=False
        )
    finally:
        release_cycle_lease(
            repo_root,
            cycle_kind=LOCAL_CYCLE_KIND,
            run_id=resolved_run_id,
        )
