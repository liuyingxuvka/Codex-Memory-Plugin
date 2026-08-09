"""Single scheduled organization maintenance/exchange owner."""

from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path
from typing import Any, Callable

from local_kb.common import utc_now_iso
from local_kb.feedback import build_observation, record_observation
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
    resolve_cycle_outputs,
    validate_cycle_receipt_v3,
    validate_global_write_delegation,
    write_cycle_receipt_v3,
)
from local_kb.org_automation import run_organization_contribution, run_organization_maintenance
from local_kb.org_contribution import current_git_branch
from local_kb.org_snapshot import snapshot_pointer_path
from local_kb.org_sources import _run_git, cleanup_organization_worktree
from local_kb.settings import load_desktop_settings, organization_sources_from_settings


ORGANIZATION_CYCLE_KIND = "organization-maintenance-cycle"
ORGANIZATION_CYCLE_OWNER = "kb-organization-maintenance"
ORGANIZATION_CYCLE_AUTOMATION_ID = "kb-org-maintenance"
ORGANIZATION_CYCLE_WORKFLOW_REVISION = "organization-maintenance-contribution.v3"
ORGANIZATION_CYCLE_SEQUENCE = (
    "organization-maintenance",
    "organization-contribution",
)
ORGANIZATION_SUCCESS_STATES = {"completed", "not_applicable"}


def _effective_base_branch(repo_root: Path, requested: str) -> str:
    desired = str(requested or "main").strip() or "main"
    settings = load_desktop_settings(repo_root)
    sources = organization_sources_from_settings(settings)
    if not sources:
        return desired
    org_root = Path(str(sources[0].get("path") or ""))
    check = _run_git(["rev-parse", "--verify", f"refs/heads/{desired}"], cwd=org_root)
    if check.returncode == 0:
        return desired
    current = current_git_branch(org_root)
    return current or desired


def _git_value(org_root: Path, *args: str) -> str:
    if not org_root.is_dir():
        return ""
    result = _run_git(list(args), cwd=org_root)
    return result.stdout.strip() if result.returncode == 0 else ""


def _organization_state_snapshot(repo_root: Path) -> dict[str, Any]:
    settings = load_desktop_settings(repo_root)
    sources = organization_sources_from_settings(settings)
    source_rows: list[dict[str, Any]] = []
    snapshot_pointers: dict[str, Any] = {}
    outboxes: dict[str, Any] = {}
    for source in sources:
        organization_id = str(source.get("organization_id") or source.get("id") or "").strip()
        org_root = Path(str(source.get("path") or ""))
        source_rows.append(
            {
                "organization_id": organization_id,
                "path": str(org_root.resolve()) if org_root else "",
                "repo_url": str(source.get("repo_url") or ""),
                "branch": _git_value(org_root, "rev-parse", "--abbrev-ref", "HEAD"),
                "commit": _git_value(org_root, "rev-parse", "HEAD"),
            }
        )
        if organization_id:
            snapshot_pointers[organization_id] = file_content_identity(
                snapshot_pointer_path(repo_root, organization_id)
            )
            outboxes[organization_id] = tree_content_identity(
                repo_root / "kb" / "outbox" / "organization" / organization_id
            )
    return {
        "settings": settings,
        "sources": source_rows,
        "snapshot_pointers": snapshot_pointers,
        "organization_outboxes": outboxes,
        "local_shareable_trees": {
            "kb/public": tree_content_identity(repo_root / "kb" / "public"),
            "kb/candidates": tree_content_identity(repo_root / "kb" / "candidates"),
        },
        "history_events": file_content_identity(repo_root / "kb" / "history" / "events.jsonl"),
    }


def _organization_source_digest() -> str:
    return source_component_digest(
        (
            Path(__file__),
            Path(__file__).with_name("org_automation.py"),
            Path(__file__).with_name("org_snapshot.py"),
            Path(__file__).with_name("feedback.py"),
            Path(__file__).with_name("maintenance_lanes.py"),
        )
    )


def _organization_child_plan_digest() -> str:
    return canonical_digest(
        {
            "workflow_revision": ORGANIZATION_CYCLE_WORKFLOW_REVISION,
            "sequence": list(ORGANIZATION_CYCLE_SEQUENCE),
            "contribution_gate": "maintenance-completed-only",
            "writer_policy": "single-global-writer-delegated-per-phase",
        }
    )


def _receipt_identity(repo_root: Path, raw: object) -> tuple[str, str]:
    text = str(raw or "").strip()
    if not text:
        return "", ""
    path = Path(text)
    if not path.is_absolute():
        path = repo_root / path
    if not path.is_file():
        return "", ""
    return str(path), "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


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
        0 if status in {"completed", "not_applicable", "not_run"} else 1
    )
    return {
        "phase_id": phase_id,
        "applicability": "not_applicable" if status in {"not_applicable", "not_run"} else "applicable",
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
    runner: Callable[[str, str, str], dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    lease = acquire_global_write_lease(
        repo_root,
        cycle_kind=ORGANIZATION_CYCLE_KIND,
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
        result = runner(lease_id, delegation_token, phase_id)
        if not isinstance(result, dict):
            raise TypeError("maintenance child must return a mapping")
    except Exception as exc:
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


def _organization_child_status(result: dict[str, Any], *, phase_id: str) -> tuple[str, str]:
    terminal_gate = result.get("terminal_gate") or {}
    if result.get("skipped") is True and terminal_gate.get("applicable") is False:
        return "not_applicable", str(result.get("reason") or f"{phase_id}-not-applicable")
    if result.get("ok") is True:
        return "completed", f"{phase_id}-completed"
    if str(result.get("status") or "") == "blocked":
        return "blocked", str(result.get("reason") or f"{phase_id}-blocked")
    return "failed", str(result.get("reason") or f"{phase_id}-failed")


def _response_from_receipt(
    receipt: dict[str, Any],
    *,
    cycle_path: Path,
    idempotent_reuse: bool,
) -> dict[str, Any]:
    outputs, output_issues = resolve_cycle_outputs(receipt, receipt_path=cycle_path)
    if output_issues:
        raise ValueError("invalid cycle outputs: " + ";".join(output_issues))
    maintenance = dict(outputs.get("maintenance") or {})
    contribution = dict(outputs.get("contribution") or {})
    status = str(receipt.get("status") or "failed")
    return {
        **maintenance,
        "ok": status in ORGANIZATION_SUCCESS_STATES,
        "skipped": status == "not_applicable",
        "status": status,
        "run_id": str(receipt.get("cycle_run_id") or ""),
        "cycle_run_id": str(receipt.get("cycle_run_id") or ""),
        "maintenance": maintenance,
        "contribution": contribution,
        "snapshot": dict(outputs.get("snapshot") or {}),
        "cycle_receipt_path": str(cycle_path),
        "cycle_receipt_digest": str(receipt.get("payload_digest") or ""),
        "cycle_lock": dict(receipt.get("cycle_lease") or {}),
        "postflight_path": str(outputs.get("postflight_path") or ""),
        "postflight_recorded": bool(outputs.get("postflight_path")),
        "idempotent_reuse": idempotent_reuse,
    }


def run_organization_cycle(
    repo_root: Path,
    *,
    run_id: str | None = None,
    push: bool = True,
    remote: str = "origin",
    base_branch: str = "main",
) -> dict[str, Any]:
    """Run organization maintenance and contribution without coupling local work."""

    repo_root = Path(repo_root)
    resolved_run_id = str(run_id or "kb-organization-cycle")
    request_parameters = {
        "push": bool(push),
        "remote": str(remote),
        "base_branch": str(base_branch),
    }
    request_digest = canonical_digest(request_parameters)
    source_digest = _organization_source_digest()
    toolchain_digest = current_toolchain_digest()
    child_plan_digest = _organization_child_plan_digest()
    current_snapshot = _organization_state_snapshot(repo_root)
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
            receipt_path=cycle_path,
            expected_kind=ORGANIZATION_CYCLE_KIND,
            expected_run_id=resolved_run_id,
            expected_owner=ORGANIZATION_CYCLE_OWNER,
            expected_automation_id=ORGANIZATION_CYCLE_AUTOMATION_ID,
            expected_workflow_revision=ORGANIZATION_CYCLE_WORKFLOW_REVISION,
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
            "run_id": resolved_run_id,
            "reason": "cycle-receipt-identity-conflict",
            "receipt_validation": validation,
            "cycle_receipt_path": str(cycle_path),
            "idempotent_reuse": False,
        }

    cycle_lock = acquire_cycle_lease(
        repo_root,
        cycle_kind=ORGANIZATION_CYCLE_KIND,
        run_id=resolved_run_id,
        note="independent organization maintenance/contribution scheduled task",
    )
    if cycle_lock.get("acquired") is not True:
        return {
            "ok": False,
            "status": "blocked",
            "run_id": resolved_run_id,
            "reason": "organization-cycle-task-lease-active",
            "cycle_lock": redact_lease_secrets(cycle_lock),
        }

    created_at = utc_now_iso()
    input_snapshot = current_snapshot
    input_digest = canonical_digest(input_snapshot)
    phases: list[dict[str, Any]] = []
    lease_events: list[dict[str, Any]] = []
    try:
        effective_base_branch = _effective_base_branch(repo_root, base_branch)
        maintenance_run_id = f"{resolved_run_id}-maintenance"
        maintenance_started = utc_now_iso()
        maintenance_input_digest = canonical_digest(_organization_state_snapshot(repo_root))
        maintenance, maintenance_events, maintenance_lease = _execute_writer_phase(
            repo_root,
            cycle_run_id=resolved_run_id,
            phase_id="organization-maintenance",
            child_run_id=maintenance_run_id,
            runner=lambda writer_lease_id, writer_delegation_token, writer_phase_id: run_organization_maintenance(
                repo_root,
                push=push,
                remote=remote,
                base_branch=effective_base_branch,
                record_postflight=False,
                cleanup_worktree=False,
                run_id=maintenance_run_id,
                writer_lease_id=writer_lease_id,
                writer_delegation_token=writer_delegation_token,
                writer_phase_id=writer_phase_id,
            ),
        )
        lease_events.extend(maintenance_events)
        maintenance_status, maintenance_reason = _organization_child_status(
            maintenance, phase_id="organization-maintenance"
        )
        maintenance_receipt_path, maintenance_receipt_digest = _receipt_identity(
            repo_root, maintenance.get("receipt_path")
        )
        phases.append(
            _phase_record(
                phase_id="organization-maintenance",
                status=maintenance_status,
                reason_code=maintenance_reason,
                run_id=str(maintenance.get("run_id") or maintenance_run_id),
                started_at=maintenance_started,
                finished_at=utc_now_iso(),
                input_digest=maintenance_input_digest,
                result=maintenance,
                receipt_path=maintenance_receipt_path,
                receipt_digest=maintenance_receipt_digest,
                lease=maintenance_lease,
                cleanup_confirmed=bool(maintenance_lease.get("cleanup_confirmed", False)),
            )
        )

        contribution_run_id = f"{resolved_run_id}-contribute"
        postflight_path = ""
        if maintenance_status == "completed":
            settings = load_desktop_settings(repo_root)

            def contribution_with_postflight(
                writer_lease_id: str,
                writer_delegation_token: str,
                writer_phase_id: str,
            ) -> dict[str, Any]:
                nonlocal postflight_path
                contribution_result = run_organization_contribution(
                    repo_root,
                    push=push,
                    remote=remote,
                    base_branch=effective_base_branch,
                    record_postflight=False,
                    cleanup_worktree=False,
                    run_id=contribution_run_id,
                    sync_context={
                        "source": maintenance.get("source") or {},
                        "sources": organization_sources_from_settings(settings),
                        "settings": settings,
                        "sync": maintenance.get("sync") or {},
                    },
                    writer_lease_id=writer_lease_id,
                    writer_delegation_token=writer_delegation_token,
                    writer_phase_id=writer_phase_id,
                )
                child_ok = bool(maintenance.get("ok")) and bool(contribution_result.get("ok"))
                observation = build_observation(
                    task_summary="Organization maintenance cycle synchronized the local card snapshot",
                    route_hint="system/knowledge-library/organization",
                    hit_quality="trusted",
                    outcome="completed" if child_ok else "failed",
                    comment="The organization cycle maintained the shared repository and refreshed a complete local snapshot; local retrieval remains read-only and direct-use does not auto-adopt cards.",
                    suggested_action="none" if child_ok else "update-card",
                    exposed_gap=not child_ok,
                    scenario="A machine participates in organization synchronization.",
                    action_taken="Ran organization maintenance followed by contribution through the existing native facades.",
                    observed_result=f"maintenance={maintenance.get('ok')} contribution={contribution_result.get('ok')}",
                    operational_use="Use the current snapshot for retrieval; Sleep owns any later local model publication.",
                    reuse_judgment="Reusable for other machines that need the same two-owner organization cycle.",
                    source_kind="organization-maintenance",
                    agent_name="kb-organization-cycle",
                    workspace_root=str(repo_root),
                )
                try:
                    postflight_path = str(record_observation(repo_root, observation))
                except Exception as exc:
                    return {
                        **contribution_result,
                        "ok": False,
                        "status": "failed",
                        "reason": "cycle-postflight-failed",
                        "postflight_error_type": type(exc).__name__,
                        "postflight_error": str(exc),
                    }
                return {
                    **contribution_result,
                    "postflight_path": postflight_path,
                    "postflight_recorded": True,
                }

            contribution_started = utc_now_iso()
            contribution_input_digest = canonical_digest(
                _organization_state_snapshot(repo_root)
            )
            contribution, contribution_events, contribution_lease = _execute_writer_phase(
                repo_root,
                cycle_run_id=resolved_run_id,
                phase_id="organization-contribution",
                child_run_id=contribution_run_id,
                runner=contribution_with_postflight,
            )
            lease_events.extend(contribution_events)
            contribution_status, contribution_reason = _organization_child_status(
                contribution, phase_id="organization-contribution"
            )
            if contribution_status == "not_applicable":
                cycle_status = "blocked"
                contribution_reason = "organization-settings-changed-after-maintenance"
            else:
                cycle_status = contribution_status
            contribution_receipt_path, contribution_receipt_digest = _receipt_identity(
                repo_root, contribution.get("receipt_path")
            )
            phases.append(
                _phase_record(
                    phase_id="organization-contribution",
                    status=contribution_status,
                    reason_code=contribution_reason,
                    run_id=str(contribution.get("run_id") or contribution_run_id),
                    started_at=contribution_started,
                    finished_at=utc_now_iso(),
                    input_digest=contribution_input_digest,
                    result=contribution,
                    receipt_path=contribution_receipt_path,
                    receipt_digest=contribution_receipt_digest,
                    lease=contribution_lease,
                    cleanup_confirmed=bool(contribution_lease.get("cleanup_confirmed", False)),
                )
            )
        else:
            downstream_reason = {
                "not_applicable": "prerequisite-not-applicable",
                "blocked": "predecessor-blocked",
                "failed": "predecessor-failed",
            }[maintenance_status]
            contribution = {
                "ok": False,
                "skipped": False,
                "status": "not_run",
                "run_id": contribution_run_id,
                "reason": downstream_reason,
                "not_run_reason": "organization maintenance did not produce a valid current snapshot",
            }
            now = utc_now_iso()
            phases.append(
                _phase_record(
                    phase_id="organization-contribution",
                    status="not_run",
                    reason_code=downstream_reason,
                    run_id=contribution_run_id,
                    started_at=now,
                    finished_at=now,
                    input_digest=canonical_digest(_organization_state_snapshot(repo_root)),
                    result=contribution,
                    cleanup_confirmed=True,
                )
            )
            cycle_status = maintenance_status

        effective_sync = (maintenance.get("sync") or {}) if isinstance(maintenance, dict) else {}
        # The native contribution owner returns ``ok`` and a receipt, while
        # the cycle derives its terminal status through
        # ``_organization_child_status``.  Do not require a redundant child
        # ``status`` field here: treating an otherwise successful contribution
        # as a failure leaves the exact disposable worktree retained after a
        # completed cycle and makes the rehearsal look unsafe.
        contribution_ok = bool((contribution or {}).get("ok", True))
        contribution_terminal = str((contribution or {}).get("status") or "")
        if not contribution_terminal and maintenance_status == "completed":
            contribution_terminal = "completed" if contribution_ok else "failed"
        cleanup_success = bool(
            maintenance_status == "completed"
            and contribution_terminal in {"completed", "not_applicable"}
            and contribution_ok
        )
        worktree_cleanup = cleanup_organization_worktree(
            effective_sync.get("worktree"), success=cleanup_success
        )
        if isinstance(effective_sync, dict):
            effective_sync["worktree_cleanup"] = worktree_cleanup
        if isinstance(contribution, dict) and isinstance(contribution.get("sync"), dict):
            contribution["sync"]["worktree_cleanup"] = worktree_cleanup

        snapshot = (
            (contribution.get("sync") or {}).get("snapshot")
            or (maintenance.get("sync") or {}).get("snapshot")
            or {}
        )
        result_snapshot = _organization_state_snapshot(repo_root)
        receipt: dict[str, Any] = {
            "schema_version": CYCLE_RECEIPT_SCHEMA,
            "kind": ORGANIZATION_CYCLE_KIND,
            "cycle_run_id": resolved_run_id,
            "scheduled_owner_skill_id": ORGANIZATION_CYCLE_OWNER,
            "automation_id": ORGANIZATION_CYCLE_AUTOMATION_ID,
            "workflow_revision": ORGANIZATION_CYCLE_WORKFLOW_REVISION,
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
            "sequence": list(ORGANIZATION_CYCLE_SEQUENCE),
            "phases": phases,
            "cycle_lease": redact_lease_secrets(cycle_lock),
            "write_lease_events": lease_events,
            "outputs": {
                "maintenance": maintenance,
                "contribution": contribution,
                "snapshot": snapshot,
                "worktree_cleanup": worktree_cleanup,
                "postflight_path": postflight_path,
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
            cycle_kind=ORGANIZATION_CYCLE_KIND,
            run_id=resolved_run_id,
        )
