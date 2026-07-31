"""Single scheduled local maintenance owner.

Sleep remains the only canonical publisher.  This facade merely sequences the
existing Dream simulation and Sleep publisher under the already shared
maintenance lane; it does not create a second lifecycle implementation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from local_kb.dream import run_dream_maintenance
from local_kb.lifecycle import _atomic_write_json, run_incremental_sleep


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
    sleep = run_incremental_sleep(
        repo_root,
        run_id=resolved_run_id,
        max_observations=max_observations,
        soft_deadline_seconds=soft_deadline_seconds,
    )
    final_state = str(sleep.get("final_run_state") or "")
    dream: dict[str, Any]
    if final_state == "completed" and not sleep.get("blockers"):
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

    mode = "resume_sleep" if bool(sleep.get("batch_resumed")) else "fresh_cycle"
    cycle_status = "completed" if dream_ok and final_state in {"completed", "completed_with_blocks", "progress_saved"} else "failed"
    cycle = {
        "schema_version": 1,
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
    }
    cycle_root = repo_root / ".local" / "maintenance-cycles" / resolved_run_id
    cycle_root.mkdir(parents=True, exist_ok=True)
    cycle_path = cycle_root / "cycle-receipt.json"
    cycle_path.write_text(json.dumps(cycle, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    receipt_path = Path(str(sleep.get("receipt_path") or ""))
    if receipt_path.is_file():
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            receipt = {}
        if isinstance(receipt, dict):
            receipt["local_cycle"] = {
                "status": cycle_status,
                "mode": mode,
                "sequence": ["sleep", "dream"],
                "dream_status": str(dream.get("status") or "not_run"),
                "dream_run_id": str(dream.get("run_id") or ""),
                "cycle_receipt_path": str(cycle_path),
            }
            _atomic_write_json(receipt_path, receipt)
    return {
        **sleep,
        "local_cycle": {
            "status": cycle_status,
            "mode": mode,
            "sequence": ["sleep", "dream"],
            "sleep": sleep,
            "dream": dream,
            "cycle_receipt_path": str(cycle_path),
        },
    }
