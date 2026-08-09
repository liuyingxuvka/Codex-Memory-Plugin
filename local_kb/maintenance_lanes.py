from __future__ import annotations

import json
import hashlib
import hmac
import os
import platform
import secrets
import shutil
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Iterable, Mapping

from local_kb.common import utc_now_iso


LANE_STATUS_DIR = Path("kb") / "history" / "lane-status"
LANE_LOCK_DIR = LANE_STATUS_DIR / "locks"
CORE_MAINTENANCE_LANES = ("kb-sleep", "kb-dream")
LOCAL_CYCLE_LANES = ("kb-local-maintenance-cycle",)
ORGANIZATION_MAINTENANCE_LANES = ("kb-org-contribute", "kb-org-maintenance")
ORGANIZATION_CYCLE_LANES = ("kb-organization-cycle",)
MAINTENANCE_LOCK_GROUPS: dict[str, tuple[str, ...]] = {
    "local-maintenance": CORE_MAINTENANCE_LANES,
    "local-cycle": LOCAL_CYCLE_LANES,
    "organization-maintenance": ORGANIZATION_MAINTENANCE_LANES,
    "organization-cycle": ORGANIZATION_CYCLE_LANES,
}
DEFAULT_LOCK_POLL_SECONDS = 5
DEFAULT_STALE_AFTER_SECONDS = 12 * 60 * 60
DEFAULT_GLOBAL_WRITE_LEASE_SECONDS = 120
DEFAULT_GLOBAL_WRITE_WAIT_SECONDS = 120
GLOBAL_WRITE_LOCK_GROUP = "global-maintenance-writer"
GLOBAL_WRITE_LEASE_SCHEMA = "khaos-brain.global-write-lease.v1"
CYCLE_RECEIPT_SCHEMA = "khaos-brain.maintenance-cycle-receipt.v3"
CYCLE_TERMINAL_STATUSES = frozenset(
    {
        "completed",
        "completed_with_blocks",
        "progress_saved",
        "not_applicable",
        "blocked",
        "failed",
    }
)
CYCLE_PHASE_STATUSES = frozenset((*CYCLE_TERMINAL_STATUSES, "not_run"))
CYCLE_RECEIPT_FIELDS = frozenset(
    {
        "schema_version",
        "kind",
        "cycle_run_id",
        "scheduled_owner_skill_id",
        "automation_id",
        "workflow_revision",
        "status",
        "request_parameters",
        "request_digest",
        "input_snapshot",
        "input_digest",
        "result_snapshot",
        "result_state_digest",
        "source_component_digest",
        "toolchain_digest",
        "child_plan_digest",
        "sequence",
        "phases",
        "cycle_lease",
        "write_lease_events",
        "outputs",
        "child_receipts_immutable",
        "created_at",
        "finished_at",
        "payload_digest",
    }
)


def canonical_digest(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def file_content_identity(path: Path) -> dict[str, Any]:
    path = Path(path)
    if not path.is_file():
        return {"exists": False, "digest": "", "size": 0}
    payload = path.read_bytes()
    return {
        "exists": True,
        "digest": "sha256:" + hashlib.sha256(payload).hexdigest(),
        "size": len(payload),
    }


def tree_content_identity(path: Path) -> dict[str, Any]:
    path = Path(path)
    rows: list[dict[str, Any]] = []
    if path.is_dir():
        for candidate in sorted(
            (item for item in path.rglob("*") if item.is_file()),
            key=lambda item: item.relative_to(path).as_posix(),
        ):
            rows.append(
                {
                    "path": candidate.relative_to(path).as_posix(),
                    **file_content_identity(candidate),
                }
            )
    return {
        "exists": path.is_dir(),
        "file_count": len(rows),
        "digest": canonical_digest(rows),
    }


def source_component_digest(paths: Iterable[Path]) -> str:
    rows = [
        {"path": str(Path(path).resolve()), **file_content_identity(Path(path))}
        for path in sorted({Path(path) for path in paths}, key=lambda item: str(item))
    ]
    return canonical_digest(rows)


def current_toolchain_digest() -> str:
    return canonical_digest(
        {
            "python_implementation": platform.python_implementation(),
            "python_version": platform.python_version(),
            "os_name": os.name,
            "platform_system": platform.system(),
        }
    )


def cycle_receipt_payload_digest(receipt: Mapping[str, Any]) -> str:
    unsigned = dict(receipt)
    unsigned.pop("payload_digest", None)
    return canonical_digest(unsigned)


def validate_cycle_receipt_v3(
    receipt: Mapping[str, Any],
    *,
    expected_kind: str = "",
    expected_run_id: str = "",
    expected_owner: str = "",
    expected_automation_id: str = "",
    expected_workflow_revision: str = "",
    expected_request_digest: str = "",
    expected_source_component_digest: str = "",
    expected_toolchain_digest: str = "",
    expected_child_plan_digest: str = "",
    current_state_digest: str = "",
) -> dict[str, Any]:
    issues: list[str] = []
    if set(receipt) != set(CYCLE_RECEIPT_FIELDS):
        missing = sorted(set(CYCLE_RECEIPT_FIELDS) - set(receipt))
        extra = sorted(set(receipt) - set(CYCLE_RECEIPT_FIELDS))
        issues.append(f"receipt-fields-mismatch:missing={missing}:extra={extra}")
    if receipt.get("schema_version") != CYCLE_RECEIPT_SCHEMA:
        issues.append("receipt-schema-mismatch")
    if str(receipt.get("payload_digest") or "") != cycle_receipt_payload_digest(receipt):
        issues.append("receipt-payload-digest-mismatch")
    if str(receipt.get("request_digest") or "") != canonical_digest(
        receipt.get("request_parameters") or {}
    ):
        issues.append("receipt-request-digest-mismatch")
    if str(receipt.get("input_digest") or "") != canonical_digest(
        receipt.get("input_snapshot") or {}
    ):
        issues.append("receipt-input-digest-mismatch")
    if str(receipt.get("result_state_digest") or "") != canonical_digest(
        receipt.get("result_snapshot") or {}
    ):
        issues.append("receipt-result-state-digest-mismatch")
    if str(receipt.get("status") or "") not in CYCLE_TERMINAL_STATUSES:
        issues.append("receipt-terminal-status-invalid")
    sequence = receipt.get("sequence")
    phases = receipt.get("phases")
    if not isinstance(sequence, list) or not all(isinstance(item, str) and item for item in sequence):
        issues.append("receipt-sequence-invalid")
        sequence = []
    if not isinstance(phases, list):
        issues.append("receipt-phases-invalid")
        phases = []
    phase_ids: list[str] = []
    for index, phase in enumerate(phases):
        if not isinstance(phase, Mapping):
            issues.append(f"receipt-phase-not-object:{index}")
            continue
        phase_id = str(phase.get("phase_id") or "")
        phase_ids.append(phase_id)
        if str(phase.get("status") or "") not in CYCLE_PHASE_STATUSES:
            issues.append(f"receipt-phase-status-invalid:{phase_id or index}")
        if not str(phase.get("reason_code") or ""):
            issues.append(f"receipt-phase-reason-missing:{phase_id or index}")
    if phase_ids != list(sequence):
        issues.append("receipt-phase-sequence-mismatch")
    phase_status = {
        str(phase.get("phase_id") or ""): str(phase.get("status") or "")
        for phase in phases
        if isinstance(phase, Mapping)
    }
    receipt_kind = str(receipt.get("kind") or "")
    cycle_status = str(receipt.get("status") or "")
    if receipt_kind == "local-maintenance-cycle" and list(sequence) == ["sleep", "dream"]:
        sleep_status = phase_status.get("sleep", "")
        dream_status = phase_status.get("dream", "")
        expected_cycle_status = ""
        if sleep_status == "completed":
            expected_cycle_status = (
                dream_status
                if dream_status in {"completed", "blocked", "failed"}
                else ""
            )
        elif sleep_status in {
            "completed_with_blocks",
            "progress_saved",
            "blocked",
            "failed",
        } and dream_status == "not_run":
            expected_cycle_status = sleep_status
        if not expected_cycle_status or cycle_status != expected_cycle_status:
            issues.append("receipt-local-status-matrix-invalid")
        outputs = receipt.get("outputs")
        if not isinstance(outputs, Mapping):
            issues.append("receipt-local-outputs-missing")
            outputs = {}
        postflight = outputs.get("postflight")
        if not isinstance(postflight, Mapping):
            issues.append("receipt-local-postflight-missing")
        elif cycle_status in {"completed", "completed_with_blocks", "progress_saved"}:
            if str(postflight.get("status") or "") != "completed":
                issues.append("receipt-local-postflight-stale")
            if not str(postflight.get("event_id") or ""):
                issues.append("receipt-local-postflight-event-missing")
            if not str(postflight.get("path") or ""):
                issues.append("receipt-local-postflight-path-missing")
        lane_status = outputs.get("lane_status")
        if not isinstance(lane_status, Mapping):
            issues.append("receipt-local-lane-status-missing")
        else:
            phase_by_id = {
                str(phase.get("phase_id") or ""): phase
                for phase in phases
                if isinstance(phase, Mapping)
            }
            for lane, phase_id in (("kb-sleep", "sleep"), ("kb-dream", "dream")):
                row = lane_status.get(lane)
                if not isinstance(row, Mapping):
                    continue
                lane_state = str(row.get("status") or "").lower()
                phase = phase_by_id.get(phase_id, {})
                phase_state = str(phase.get("status") or "")
                if phase_state not in {"not_run", ""} and lane_state in {"running", "stale", "unknown"}:
                    issues.append(f"receipt-local-lane-status-stale:{lane}")
                phase_expected_run_id = str(phase.get("run_id") or "")
                actual_run_id = str(row.get("run_id") or "")
                if phase_expected_run_id and actual_run_id and phase_expected_run_id != actual_run_id:
                    issues.append(f"receipt-local-lane-run-id-mismatch:{lane}")
    elif receipt_kind == "organization-maintenance-cycle" and list(sequence) == [
        "organization-maintenance",
        "organization-contribution",
    ]:
        maintenance_status = phase_status.get("organization-maintenance", "")
        contribution_status = phase_status.get("organization-contribution", "")
        expected_cycle_status = ""
        if maintenance_status == "completed":
            if contribution_status in {"completed", "blocked", "failed"}:
                expected_cycle_status = contribution_status
            elif contribution_status == "not_applicable":
                expected_cycle_status = "blocked"
        elif maintenance_status in {"not_applicable", "blocked", "failed"} and contribution_status == "not_run":
            expected_cycle_status = maintenance_status
        if not expected_cycle_status or cycle_status != expected_cycle_status:
            issues.append("receipt-organization-status-matrix-invalid")
    forbidden_secret_keys = {"lease_token", "delegation_token", "raw_token"}

    def secret_keys(value: object) -> set[str]:
        found: set[str] = set()
        if isinstance(value, Mapping):
            for key, item in value.items():
                if str(key) in forbidden_secret_keys:
                    found.add(str(key))
                found.update(secret_keys(item))
        elif isinstance(value, list):
            for item in value:
                found.update(secret_keys(item))
        return found

    exposed = secret_keys(receipt)
    if exposed:
        issues.append(f"receipt-contains-lease-secret:{sorted(exposed)}")
    exact_expectations = (
        ("kind", expected_kind, str(receipt.get("kind") or "")),
        ("run-id", expected_run_id, str(receipt.get("cycle_run_id") or "")),
        ("owner", expected_owner, str(receipt.get("scheduled_owner_skill_id") or "")),
        ("automation", expected_automation_id, str(receipt.get("automation_id") or "")),
        (
            "workflow-revision",
            expected_workflow_revision,
            str(receipt.get("workflow_revision") or ""),
        ),
        ("request", expected_request_digest, str(receipt.get("request_digest") or "")),
        (
            "source-component",
            expected_source_component_digest,
            str(receipt.get("source_component_digest") or ""),
        ),
        ("toolchain", expected_toolchain_digest, str(receipt.get("toolchain_digest") or "")),
        ("child-plan", expected_child_plan_digest, str(receipt.get("child_plan_digest") or "")),
        ("current-state", current_state_digest, str(receipt.get("result_state_digest") or "")),
    )
    for label, expected, actual in exact_expectations:
        if expected and actual != expected:
            issues.append(f"receipt-{label}-mismatch")
    return {"ok": not issues, "issues": issues}


def write_cycle_receipt_v3(path: Path, receipt: Mapping[str, Any]) -> Path:
    path = Path(path)
    payload = dict(receipt)
    payload["payload_digest"] = cycle_receipt_payload_digest(payload)
    validation = validate_cycle_receipt_v3(payload)
    if not validation["ok"]:
        raise ValueError("invalid cycle receipt: " + ";".join(validation["issues"]))
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
        default=str,
    ) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        handle.write(serialized)
        handle.flush()
        os.fsync(handle.fileno())
    return path


def redact_lease_secrets(value: object) -> object:
    if isinstance(value, Mapping):
        return {
            str(key): redact_lease_secrets(item)
            for key, item in value.items()
            if str(key) not in {"lease_token", "delegation_token", "raw_token", "path"}
        }
    if isinstance(value, list):
        return [redact_lease_secrets(item) for item in value]
    return value


def _safe_name(value: str) -> str:
    return value.strip().lower().replace("/", "-").replace("\\", "-")


def lane_status_path(repo_root: Path, lane: str) -> Path:
    safe_lane = _safe_name(lane)
    return repo_root / LANE_STATUS_DIR / f"{safe_lane}.json"


def lane_lock_group(lane: str) -> str:
    for group, lanes in MAINTENANCE_LOCK_GROUPS.items():
        if lane in lanes:
            return group
    return _safe_name(lane)


def lane_lock_dir(repo_root: Path, group: str) -> Path:
    return repo_root / LANE_LOCK_DIR / f"{_safe_name(group)}.lock"


def lane_lock_path(repo_root: Path, group: str) -> Path:
    return lane_lock_dir(repo_root, group) / "lock.json"


def read_lane_status(repo_root: Path, lane: str) -> dict[str, Any]:
    path = lane_status_path(repo_root, lane)
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {"lane": lane, "status": "unknown", "path": str(path)}
    return payload if isinstance(payload, dict) else {}


def read_lane_lock(repo_root: Path, group: str) -> dict[str, Any]:
    path = lane_lock_path(repo_root, group)
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {"group": group, "status": "unknown", "path": str(path)}
    if not isinstance(payload, dict):
        return {}
    payload["path"] = str(path)
    return payload


def _lock_is_stale(payload: dict[str, Any], *, stale_after_seconds: int) -> bool:
    heartbeat = payload.get("heartbeat_epoch")
    try:
        heartbeat_epoch = float(heartbeat)
    except (TypeError, ValueError):
        return True
    return (time.time() - heartbeat_epoch) > stale_after_seconds


def process_owner_is_alive(pid: int) -> bool:
    """Conservatively determine whether a recorded process owner still exists."""

    if pid <= 0:
        return False
    if pid == os.getpid():
        return True
    if os.name == "nt":
        try:
            import ctypes

            process_query_limited_information = 0x1000
            handle = ctypes.windll.kernel32.OpenProcess(  # type: ignore[attr-defined]
                process_query_limited_information, False, int(pid)
            )
            if handle:
                ctypes.windll.kernel32.CloseHandle(handle)  # type: ignore[attr-defined]
                return True
            return int(ctypes.windll.kernel32.GetLastError()) == 5  # type: ignore[attr-defined]
        except (AttributeError, OSError, ValueError):
            return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except (PermissionError, OSError):
        return True
    return True


def _lock_owner_is_dead(payload: dict[str, Any]) -> bool:
    try:
        pid = int(payload.get("pid") or 0)
    except (TypeError, ValueError):
        return False
    return pid > 0 and not process_owner_is_alive(pid)


def _write_lane_lock(
    repo_root: Path,
    *,
    group: str,
    lane: str,
    run_id: str = "",
    note: str = "",
) -> dict[str, Any]:
    path = lane_lock_path(repo_root, group)
    payload = {
        "group": group,
        "lane": lane,
        "run_id": run_id,
        "note": note,
        "pid": os.getpid(),
        "thread_id": threading.get_ident(),
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso(),
        "heartbeat_epoch": time.time(),
    }
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    payload["path"] = str(path)
    return payload


def heartbeat_lane_lock(
    repo_root: Path,
    lane: str,
    *,
    run_id: str = "",
    group: str | None = None,
    note: str = "",
) -> dict[str, Any]:
    resolved_group = group or lane_lock_group(lane)
    payload = read_lane_lock(repo_root, resolved_group)
    if not payload:
        return {"group": resolved_group, "lane": lane, "status": "missing"}
    if payload.get("lane") != lane:
        return {"group": resolved_group, "lane": lane, "status": "not-owner", "lock": payload}
    if run_id and payload.get("run_id") not in ("", run_id):
        return {"group": resolved_group, "lane": lane, "status": "not-owner", "lock": payload}
    if int(payload.get("pid") or 0) != os.getpid() or int(payload.get("thread_id") or 0) != threading.get_ident():
        return {"group": resolved_group, "lane": lane, "status": "not-owner", "lock": payload}
    payload["updated_at"] = utc_now_iso()
    payload["heartbeat_epoch"] = time.time()
    if note:
        payload["note"] = note
    path = Path(str(payload["path"]))
    with path.open("w", encoding="utf-8") as handle:
        json.dump({key: value for key, value in payload.items() if key != "path"}, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    payload["status"] = "heartbeat"
    return payload


def acquire_lane_lock(
    repo_root: Path,
    lane: str,
    *,
    run_id: str = "",
    group: str | None = None,
    poll_seconds: int = DEFAULT_LOCK_POLL_SECONDS,
    stale_after_seconds: int = DEFAULT_STALE_AFTER_SECONDS,
    wait: bool = True,
    note: str = "",
) -> dict[str, Any]:
    resolved_group = group or lane_lock_group(lane)
    lock_dir = lane_lock_dir(repo_root, resolved_group)
    lock_dir.parent.mkdir(parents=True, exist_ok=True)
    waits = 0
    recovered_lock: dict[str, Any] = {}
    recovery_reason = ""
    while True:
        try:
            lock_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            existing = read_lane_lock(repo_root, resolved_group)
            owner_dead = _lock_owner_is_dead(existing)
            if (
                not owner_dead
                and existing.get("lane") == lane
                and (not run_id or existing.get("run_id") in ("", run_id))
                and int(existing.get("pid") or 0) == os.getpid()
                and int(existing.get("thread_id") or 0) == threading.get_ident()
            ):
                heartbeat = heartbeat_lane_lock(repo_root, lane, run_id=run_id, group=resolved_group, note=note)
                heartbeat["acquired"] = True
                heartbeat["reentrant"] = True
                heartbeat["wait_count"] = waits
                return heartbeat
            stale = bool(
                existing
                and _lock_is_stale(
                    existing, stale_after_seconds=stale_after_seconds
                )
            )
            if not existing or owner_dead or stale:
                recovered_lock = dict(existing)
                recovery_reason = (
                    "missing-or-invalid-lock"
                    if not existing
                    else "dead-owner"
                    if owner_dead
                    else "stale-heartbeat"
                )
                shutil.rmtree(lock_dir, ignore_errors=True)
                continue
            blocked = {
                "group": resolved_group,
                "lane": lane,
                "run_id": run_id,
                "acquired": False,
                "blocked_by": existing,
                "wait_count": waits,
            }
            if not wait:
                return blocked
            waits += 1
            time.sleep(max(0, poll_seconds))
            continue
        payload = _write_lane_lock(repo_root, group=resolved_group, lane=lane, run_id=run_id, note=note)
        payload["acquired"] = True
        payload["wait_count"] = waits
        if recovery_reason:
            payload["recovered"] = True
            payload["recovery_reason"] = recovery_reason
            payload["recovered_lock"] = recovered_lock
        return payload


def release_lane_lock(
    repo_root: Path,
    lane: str,
    *,
    run_id: str = "",
    group: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    resolved_group = group or lane_lock_group(lane)
    lock_dir = lane_lock_dir(repo_root, resolved_group)
    payload = read_lane_lock(repo_root, resolved_group)
    if not payload:
        return {"ok": False, "group": resolved_group, "lane": lane, "released": False, "reason": "missing"}
    owns_lock = bool(
        payload.get("lane") == lane
        and (not run_id or payload.get("run_id") in ("", run_id))
        and int(payload.get("pid") or 0) == os.getpid()
        and int(payload.get("thread_id") or 0) == threading.get_ident()
    )
    if not owns_lock and not force:
        return {"ok": False, "group": resolved_group, "lane": lane, "released": False, "reason": "not-owner", "lock": payload}
    shutil.rmtree(lock_dir, ignore_errors=True)
    return {"ok": True, "group": resolved_group, "lane": lane, "run_id": run_id, "released": True, "lock": payload}


def acquire_cycle_lease(
    repo_root: Path,
    *,
    cycle_kind: str,
    run_id: str,
    note: str = "",
) -> dict[str, Any]:
    lane = {
        "local-maintenance-cycle": "kb-local-maintenance-cycle",
        "organization-maintenance-cycle": "kb-organization-cycle",
    }.get(cycle_kind)
    if not lane:
        raise ValueError(f"Unsupported cycle kind: {cycle_kind}")
    return acquire_lane_lock(
        repo_root,
        lane,
        run_id=run_id,
        wait=False,
        note=note or f"independent {cycle_kind} task lease",
    )


def release_cycle_lease(
    repo_root: Path,
    *,
    cycle_kind: str,
    run_id: str,
) -> dict[str, Any]:
    lane = {
        "local-maintenance-cycle": "kb-local-maintenance-cycle",
        "organization-maintenance-cycle": "kb-organization-cycle",
    }.get(cycle_kind)
    if not lane:
        raise ValueError(f"Unsupported cycle kind: {cycle_kind}")
    return release_lane_lock(repo_root, lane, run_id=run_id)


def _token_hash(token: str) -> str:
    return "sha256:" + hashlib.sha256(str(token).encode("utf-8")).hexdigest()


def _global_write_lease_path(repo_root: Path) -> Path:
    return lane_lock_path(Path(repo_root), GLOBAL_WRITE_LOCK_GROUP)


def read_global_write_lease(repo_root: Path) -> dict[str, Any]:
    payload = read_lane_lock(Path(repo_root), GLOBAL_WRITE_LOCK_GROUP)
    if payload and payload.get("schema_version") != GLOBAL_WRITE_LEASE_SCHEMA:
        payload["valid"] = False
    elif payload:
        payload["valid"] = True
    return payload


def _write_global_write_lease(repo_root: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    path = _global_write_lease_path(Path(repo_root))
    with path.open("w", encoding="utf-8") as handle:
        json.dump(dict(payload), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    result = dict(payload)
    result["path"] = str(path)
    return result


def _global_lease_owned_by(
    payload: Mapping[str, Any],
    *,
    lease_id: str,
    lease_token: str,
    require_owner_thread: bool = True,
) -> bool:
    return bool(
        payload.get("schema_version") == GLOBAL_WRITE_LEASE_SCHEMA
        and str(payload.get("lease_id") or "") == str(lease_id)
        and int(payload.get("owner_pid") or 0) == os.getpid()
        and (
            not require_owner_thread
            or int(payload.get("owner_thread_id") or 0) == threading.get_ident()
        )
        and hmac.compare_digest(
            str(payload.get("token_hash") or ""),
            _token_hash(lease_token),
        )
    )


def _global_lease_expired(payload: Mapping[str, Any]) -> bool:
    try:
        return time.time() > float(payload.get("deadline_epoch") or 0)
    except (TypeError, ValueError):
        return True


def acquire_global_write_lease(
    repo_root: Path,
    *,
    cycle_kind: str,
    run_id: str,
    scope: str,
    wait: bool = True,
    poll_seconds: float = DEFAULT_LOCK_POLL_SECONDS,
    max_wait_seconds: float = DEFAULT_GLOBAL_WRITE_WAIT_SECONDS,
    lease_seconds: float = DEFAULT_GLOBAL_WRITE_LEASE_SECONDS,
    cleanup_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    repo_root = Path(repo_root)
    lock_dir = lane_lock_dir(repo_root, GLOBAL_WRITE_LOCK_GROUP)
    lock_dir.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    waits = 0
    while True:
        try:
            lock_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            existing = read_global_write_lease(repo_root)
            owner_dead = _lock_owner_is_dead(
                {"pid": existing.get("owner_pid")}
            ) if existing else False
            expired = bool(existing and _global_lease_expired(existing))
            remaining_process_count = (
                cleanup_evidence.get("remaining_process_count")
                if isinstance(cleanup_evidence, Mapping)
                else None
            )
            cleanup_confirmed = bool(
                isinstance(cleanup_evidence, Mapping)
                and cleanup_evidence.get("cleanup_confirmed") is True
                and isinstance(remaining_process_count, int)
                and not isinstance(remaining_process_count, bool)
                and remaining_process_count == 0
            )
            recoverable = bool((not existing or owner_dead or expired) and cleanup_confirmed)
            if recoverable:
                shutil.rmtree(lock_dir, ignore_errors=True)
                if not lock_dir.exists():
                    continue
                return {
                    "schema_version": GLOBAL_WRITE_LEASE_SCHEMA,
                    "acquired": False,
                    "cycle_kind": cycle_kind,
                    "run_id": run_id,
                    "scope": scope,
                    "wait_count": waits,
                    "reason": "global-writer-cleanup-unconfirmed",
                    "blocked_by": redact_lease_secrets(existing),
                }
            blocked = {
                "schema_version": GLOBAL_WRITE_LEASE_SCHEMA,
                "acquired": False,
                "cycle_kind": cycle_kind,
                "run_id": run_id,
                "scope": scope,
                "wait_count": waits,
                "reason": (
                    "cleanup-confirmation-required"
                    if not existing or owner_dead or expired
                    else "global-writer-active"
                ),
                "blocked_by": redact_lease_secrets(existing),
            }
            elapsed = time.monotonic() - started
            if not wait or elapsed >= max(0.0, max_wait_seconds):
                blocked["waited_seconds"] = elapsed
                return blocked
            waits += 1
            remaining = max(0.0, max_wait_seconds - elapsed)
            time.sleep(min(max(0.0, poll_seconds), remaining))
            continue
        token = secrets.token_urlsafe(32)
        now = time.time()
        lease_id = f"global-write-{uuid.uuid4().hex}"
        payload = {
            "schema_version": GLOBAL_WRITE_LEASE_SCHEMA,
            "lease_id": lease_id,
            "root_owner_kind": cycle_kind,
            "root_owner_run_id": run_id,
            "owner_pid": os.getpid(),
            "owner_thread_id": threading.get_ident(),
            "token_hash": _token_hash(token),
            "scope": scope,
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso(),
            "heartbeat_epoch": now,
            "deadline_epoch": now + max(1.0, lease_seconds),
            "delegations": [],
        }
        try:
            written = _write_global_write_lease(repo_root, payload)
        except Exception:
            shutil.rmtree(lock_dir, ignore_errors=True)
            raise
        return {
            **written,
            "acquired": True,
            "lease_token": token,
            "wait_count": waits,
            "waited_seconds": time.monotonic() - started,
        }


def heartbeat_global_write_lease(
    repo_root: Path,
    *,
    lease_id: str,
    lease_token: str,
    lease_seconds: float = DEFAULT_GLOBAL_WRITE_LEASE_SECONDS,
) -> dict[str, Any]:
    current = read_global_write_lease(Path(repo_root))
    if not _global_lease_owned_by(
        current,
        lease_id=lease_id,
        lease_token=lease_token,
        require_owner_thread=False,
    ):
        return {"ok": False, "status": "not-owner", "lease_id": lease_id}
    now = time.time()
    current.pop("path", None)
    current.pop("valid", None)
    current["updated_at"] = utc_now_iso()
    current["heartbeat_epoch"] = now
    current["deadline_epoch"] = now + max(1.0, lease_seconds)
    written = _write_global_write_lease(Path(repo_root), current)
    return {"ok": True, "status": "heartbeat", **written}


def delegate_global_write_lease(
    repo_root: Path,
    *,
    lease_id: str,
    lease_token: str,
    child_phase_id: str,
    child_run_id: str,
    scope: str,
) -> dict[str, Any]:
    current = read_global_write_lease(Path(repo_root))
    if not _global_lease_owned_by(current, lease_id=lease_id, lease_token=lease_token):
        return {"ok": False, "status": "not-owner", "lease_id": lease_id}
    active = [
        item
        for item in current.get("delegations", [])
        if isinstance(item, Mapping) and item.get("status") == "active"
    ]
    if active:
        return {
            "ok": False,
            "status": "delegation-active",
            "lease_id": lease_id,
            "active_delegation": redact_lease_secrets(active[0]),
        }
    child_token = secrets.token_urlsafe(32)
    delegation = {
        "delegation_id": f"delegation-{uuid.uuid4().hex}",
        "child_phase_id": child_phase_id,
        "child_run_id": child_run_id,
        "token_hash": _token_hash(child_token),
        "scope": scope,
        "status": "active",
        "created_at": utc_now_iso(),
        "released_at": "",
    }
    current.pop("path", None)
    current.pop("valid", None)
    current["delegations"] = [*current.get("delegations", []), delegation]
    current["updated_at"] = utc_now_iso()
    _write_global_write_lease(Path(repo_root), current)
    return {
        "ok": True,
        "status": "active",
        "lease_id": lease_id,
        **delegation,
        "delegation_token": child_token,
    }


def validate_global_write_delegation(
    repo_root: Path,
    *,
    lease_id: str,
    child_phase_id: str,
    child_run_id: str,
    delegation_token: str,
) -> dict[str, Any]:
    current = read_global_write_lease(Path(repo_root))
    if current.get("schema_version") != GLOBAL_WRITE_LEASE_SCHEMA or current.get("lease_id") != lease_id:
        return {"ok": False, "status": "lease-missing-or-mismatch"}
    for item in current.get("delegations", []):
        if not isinstance(item, Mapping):
            continue
        if (
            item.get("status") == "active"
            and item.get("child_phase_id") == child_phase_id
            and item.get("child_run_id") == child_run_id
            and hmac.compare_digest(
                str(item.get("token_hash") or ""),
                _token_hash(delegation_token),
            )
        ):
            return {
                "ok": True,
                "status": "active",
                "lease_id": lease_id,
                "delegation": redact_lease_secrets(item),
            }
    return {"ok": False, "status": "delegation-invalid"}


def release_delegated_write_lease(
    repo_root: Path,
    *,
    lease_id: str,
    lease_token: str,
    child_phase_id: str,
    child_run_id: str,
    delegation_token: str,
) -> dict[str, Any]:
    current = read_global_write_lease(Path(repo_root))
    if not _global_lease_owned_by(current, lease_id=lease_id, lease_token=lease_token):
        return {"ok": False, "status": "not-owner", "lease_id": lease_id}
    matched = False
    delegations: list[dict[str, Any]] = []
    for raw in current.get("delegations", []):
        if not isinstance(raw, Mapping):
            continue
        item = dict(raw)
        if (
            not matched
            and item.get("status") == "active"
            and item.get("child_phase_id") == child_phase_id
            and item.get("child_run_id") == child_run_id
            and hmac.compare_digest(
                str(item.get("token_hash") or ""),
                _token_hash(delegation_token),
            )
        ):
            item["status"] = "released"
            item["released_at"] = utc_now_iso()
            matched = True
        delegations.append(item)
    if not matched:
        return {"ok": False, "status": "delegation-invalid", "lease_id": lease_id}
    current.pop("path", None)
    current.pop("valid", None)
    current["delegations"] = delegations
    current["updated_at"] = utc_now_iso()
    _write_global_write_lease(Path(repo_root), current)
    return {"ok": True, "status": "released", "lease_id": lease_id}


def release_global_write_lease(
    repo_root: Path,
    *,
    lease_id: str,
    lease_token: str,
) -> dict[str, Any]:
    repo_root = Path(repo_root)
    current = read_global_write_lease(repo_root)
    if not _global_lease_owned_by(current, lease_id=lease_id, lease_token=lease_token):
        return {"ok": False, "released": False, "status": "not-owner", "lease_id": lease_id}
    active = [
        item
        for item in current.get("delegations", [])
        if isinstance(item, Mapping) and item.get("status") == "active"
    ]
    if active:
        return {
            "ok": False,
            "released": False,
            "status": "delegation-active",
            "lease_id": lease_id,
        }
    lock_dir = lane_lock_dir(repo_root, GLOBAL_WRITE_LOCK_GROUP)
    shutil.rmtree(lock_dir, ignore_errors=True)
    released = not lock_dir.exists()
    return {
        "ok": released,
        "released": released,
        "status": "released" if released else "cleanup-unconfirmed",
        "lease_id": lease_id,
    }


def recover_global_write_lease_after_cleanup(
    repo_root: Path,
    *,
    expected_root_owner_run_id: str,
    cleanup_evidence: Mapping[str, Any],
) -> dict[str, Any]:
    """Recover one abandoned global lease after an owned timeout cleanup.

    A hard owner timeout can terminate the process before its ``finally`` block
    releases the lease.  Recovery is deliberately narrower than normal lease
    acquisition: it requires the wrapper's immutable process-tree cleanup
    evidence, an exact root run-id match, and a dead or expired owner.  A
    mismatched or still-live owner remains visible and is never removed here.
    """

    repo_root = Path(repo_root)
    current = read_global_write_lease(repo_root)
    if not current:
        return {
            "ok": True,
            "status": "not_needed",
            "reason": "global-writer-lease-missing",
        }
    remaining = cleanup_evidence.get("remaining_process_count")
    cleanup_confirmed = bool(
        cleanup_evidence.get("cleanup_confirmed") is True
        and isinstance(remaining, int)
        and not isinstance(remaining, bool)
        and remaining == 0
    )
    if not cleanup_confirmed:
        return {
            "ok": False,
            "status": "blocked",
            "reason": "cleanup-confirmation-required",
            "lease": redact_lease_secrets(current),
        }
    actual_run_id = str(current.get("root_owner_run_id") or "")
    if actual_run_id != str(expected_root_owner_run_id or ""):
        return {
            "ok": False,
            "status": "blocked",
            "reason": "global-writer-owner-mismatch",
            "expected_root_owner_run_id": str(expected_root_owner_run_id or ""),
            "lease": redact_lease_secrets(current),
        }
    try:
        owner_pid = int(current.get("owner_pid") or 0)
    except (TypeError, ValueError):
        owner_pid = 0
    owner_dead = not process_owner_is_alive(owner_pid)
    expired = _global_lease_expired(current)
    if not owner_dead and not expired:
        return {
            "ok": False,
            "status": "blocked",
            "reason": "global-writer-active",
            "lease": redact_lease_secrets(current),
        }
    lock_dir = lane_lock_dir(repo_root, GLOBAL_WRITE_LOCK_GROUP)
    shutil.rmtree(lock_dir, ignore_errors=True)
    recovered = not lock_dir.exists()
    return {
        "ok": recovered,
        "status": "recovered" if recovered else "cleanup-unconfirmed",
        "reason": "abandoned-global-writer-lease" if recovered else "lock-remains",
        "lease_id": str(current.get("lease_id") or ""),
        "root_owner_run_id": actual_run_id,
        "owner_pid": owner_pid,
        "owner_dead": owner_dead,
        "expired": expired,
    }


def write_lane_status(
    repo_root: Path,
    lane: str,
    status: str,
    *,
    run_id: str = "",
    note: str = "",
) -> dict[str, Any]:
    path = lane_status_path(repo_root, lane)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "lane": lane,
        "status": status,
        "run_id": run_id,
        "note": note,
        "updated_at": utc_now_iso(),
    }
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    payload["path"] = str(path)
    return payload


def reconcile_stale_lane_statuses(
    repo_root: Path,
    *,
    lanes: tuple[str, ...] | None = None,
) -> list[dict[str, Any]]:
    reconciled: list[dict[str, Any]] = []
    active_lanes = lanes or tuple(lane for group_lanes in MAINTENANCE_LOCK_GROUPS.values() for lane in group_lanes)
    for lane in active_lanes:
        payload = read_lane_status(repo_root, lane)
        if str(payload.get("status", "") or "").lower() != "running":
            continue
        group = lane_lock_group(lane)
        lock = read_lane_lock(repo_root, group)
        if (
            lock
            and lock.get("lane") == lane
            and not _lock_owner_is_dead(lock)
            and not _lock_is_stale(
                lock, stale_after_seconds=DEFAULT_STALE_AFTER_SECONDS
            )
        ):
            continue
        reconciled.append(
            write_lane_status(
                repo_root,
                lane,
                "stale",
                run_id=str(payload.get("run_id", "") or ""),
                note="Reconciled running status without an active lane lock.",
            )
        )
    return reconciled


def lane_is_running(repo_root: Path, lane: str) -> bool:
    status = str(read_lane_status(repo_root, lane).get("status", "") or "").lower()
    return status == "running"


def build_lane_guard(
    repo_root: Path,
    lane: str,
    *,
    lanes: tuple[str, ...] = CORE_MAINTENANCE_LANES,
) -> dict[str, Any]:
    statuses: dict[str, dict[str, Any]] = {}
    blockers: list[str] = []
    legacy_running_without_lock: list[str] = []
    reconcile_stale_lane_statuses(repo_root, lanes=lanes)
    group = lane_lock_group(lane)
    lock = read_lane_lock(repo_root, group)
    if (
        lock
        and not _lock_owner_is_dead(lock)
        and not _lock_is_stale(
            lock, stale_after_seconds=DEFAULT_STALE_AFTER_SECONDS
        )
    ):
        lock_lane = str(lock.get("lane", "") or "")
        if lock_lane and lock_lane != lane and lock_lane in lanes:
            blockers.append(lock_lane)
    for other_lane in lanes:
        if other_lane == lane:
            continue
        payload = read_lane_status(repo_root, other_lane)
        statuses[other_lane] = payload
        if str(payload.get("status", "") or "").lower() == "running" and other_lane not in blockers:
            legacy_running_without_lock.append(other_lane)
    return {
        "lane": lane,
        "blocked": bool(blockers),
        "blocking_lanes": blockers,
        "lock_group": group,
        "active_lock": lock,
        "legacy_running_without_lock": legacy_running_without_lock,
        "statuses": statuses,
    }
