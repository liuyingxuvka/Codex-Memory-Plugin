"""Single scheduled local maintenance owner.

Sleep remains the only canonical publisher.  This facade merely sequences the
existing Dream simulation and Sleep publisher under the already shared
maintenance lane; it does not create a second lifecycle implementation.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from local_kb.dream import run_dream_maintenance
from local_kb.lifecycle import _atomic_write_json, run_incremental_sleep
from local_kb.maintenance_lanes import acquire_lane_lock, release_lane_lock


def run_local_maintenance_cycle(
    repo_root: Path,
    *,
    run_id: str | None = None,
    max_observations: int = 250,
    soft_deadline_seconds: float | None = None,
) -> dict[str, Any]:
    """Run one local owner: Sleep first, then Dream only after clean publish."""

    repo_root = Path(repo_root)
    resolved_run_id = str(run_id or "kb-local-maintenance")
    cycle_root = repo_root / ".local" / "maintenance-cycles" / resolved_run_id
    cycle_path = cycle_root / "cycle-receipt.json"
    if cycle_path.is_file():
        try:
            prior = json.loads(cycle_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            prior = {}
        if isinstance(prior, dict) and str(prior.get("run_id") or "") == resolved_run_id:
            return {
                "ok": str(prior.get("status") or "") == "completed",
                "status": str(prior.get("status") or "conflict"),
                "final_run_state": str(prior.get("sleep_final_run_state") or ""),
                "local_cycle": prior,
                "idempotent_reuse": True,
            }
    cycle_lock = acquire_lane_lock(
        repo_root,
        "kb-local-maintenance-cycle",
        run_id=resolved_run_id,
        wait=False,
        note="outer Sleep/Dream maintenance cycle transaction",
    )
    if cycle_lock.get("acquired") is not True:
        return {
            "ok": False,
            "status": "blocked",
            "final_run_state": "blocked",
            "local_cycle": {
                "schema_version": 2,
                "kind": "local-maintenance-cycle",
                "run_id": resolved_run_id,
                "status": "blocked",
                "reason": "local maintenance cycle lease is active",
                "cycle_lock": cycle_lock,
            },
        }
    try:
        sleep = run_incremental_sleep(
            repo_root,
            run_id=resolved_run_id,
            max_observations=max_observations,
            soft_deadline_seconds=soft_deadline_seconds,
        )
        final_state = str(sleep.get("final_run_state") or "")
        resumed = bool(sleep.get("batch_resumed"))
        dream: dict[str, Any]
        if resumed:
            reason = "Sleep resumed an unfinished batch; Dream is deferred until the batch closes."
            dream = {
                "status": "not_run",
                "reason": reason,
                "terminal_gate": {
                    "gate_id": "local-maintenance-cycle",
                    "evaluated": True,
                    "applicable": False,
                    "reason": "resume-sleep-defers-dream",
                },
            }
            dream_ok = True
        elif final_state == "completed" and not sleep.get("blockers"):
            dream = run_dream_maintenance(repo_root, run_id=f"{resolved_run_id}-dream")
            dream_status = str(dream.get("status") or "")
            dream_ok = dream_status in {"completed", "skipped"}
        else:
            reason = "sleep did not reach an unblocked completed terminal"
            dream = {
                "status": "not_run",
                "reason": reason,
                "terminal_gate": {
                    "gate_id": "local-maintenance-cycle",
                    "evaluated": True,
                    "applicable": False,
                    "reason": reason,
                },
            }
            dream_ok = True

        mode = "resume_sleep" if resumed else "fresh_cycle"
        sleep_receipt_path = str(sleep.get("receipt_path") or "")
        sleep_receipt_digest = ""
        if sleep_receipt_path and Path(sleep_receipt_path).is_file():
            sleep_receipt_digest = "sha256:" + hashlib.sha256(Path(sleep_receipt_path).read_bytes()).hexdigest()
        dream_receipt_path = str(
            (dream.get("artifact_paths") or {}).get("report_path") or ""
        )
        dream_receipt_digest = ""
        if dream_receipt_path:
            dream_absolute = Path(dream_receipt_path)
            if not dream_absolute.is_absolute():
                dream_absolute = repo_root / dream_absolute
            if dream_absolute.is_file():
                dream_receipt_digest = "sha256:" + hashlib.sha256(dream_absolute.read_bytes()).hexdigest()
        cycle_status = "completed" if dream_ok and final_state in {"completed", "completed_with_blocks", "progress_saved"} else "failed"
        cycle = {
            "schema_version": 2,
            "kind": "local-maintenance-cycle",
            "run_id": resolved_run_id,
            "status": cycle_status,
            "owner": "kb-sleep-maintenance",
            "mode": mode,
            "sequence": ["sleep", "dream"],
            "sleep_run_id": str(sleep.get("run_id") or resolved_run_id),
            "dream_run_id": str(dream.get("run_id") or ""),
            "sleep_final_run_state": final_state,
            "dream_status": str(dream.get("status") or "not_run"),
            "sleep": dict(sleep),
            "dream": dict(dream),
            "sleep_receipt_path": sleep_receipt_path,
            "sleep_receipt_digest": sleep_receipt_digest,
            "dream_receipt_path": dream_receipt_path,
            "dream_receipt_digest": dream_receipt_digest,
            "cycle_lock": dict(cycle_lock),
            "child_receipts_immutable": True,
        }
        cycle_root.mkdir(parents=True, exist_ok=True)
        _atomic_write_json(cycle_path, cycle)
        cycle["cycle_receipt_digest"] = "sha256:" + hashlib.sha256(cycle_path.read_bytes()).hexdigest()
        _atomic_write_json(cycle_path, cycle)
        return {
            **sleep,
            "local_cycle": {
                "status": cycle_status,
                "mode": mode,
                "sequence": ["sleep", "dream"],
                "sleep": sleep,
                "dream": dream,
                "cycle_receipt_path": str(cycle_path),
                "cycle_receipt_digest": str(cycle.get("cycle_receipt_digest") or ""),
            },
        }
    finally:
        release_lane_lock(repo_root, "kb-local-maintenance-cycle", run_id=resolved_run_id)
