"""Single scheduled organization maintenance/exchange owner."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from local_kb.feedback import build_observation, record_observation
from local_kb.org_automation import run_organization_contribution, run_organization_maintenance
from local_kb.org_contribution import current_git_branch
from local_kb.org_sources import _run_git
from local_kb.settings import load_desktop_settings, organization_sources_from_settings


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


def run_organization_cycle(
    repo_root: Path,
    *,
    run_id: str | None = None,
    push: bool = True,
    remote: str = "origin",
    base_branch: str = "main",
) -> dict[str, Any]:
    """Run the existing organization maintenance and contribution owners in order."""

    repo_root = Path(repo_root)
    resolved_run_id = str(run_id or "kb-organization-cycle")
    effective_base_branch = _effective_base_branch(repo_root, base_branch)
    maintenance = run_organization_maintenance(
        repo_root,
        push=push,
        remote=remote,
        base_branch=effective_base_branch,
        record_postflight=False,
        run_id=f"{resolved_run_id}-maintenance",
    )
    if maintenance.get("ok") or maintenance.get("skipped"):
        contribution = run_organization_contribution(
            repo_root,
            push=push,
            remote=remote,
            base_branch=effective_base_branch,
            record_postflight=False,
            run_id=f"{resolved_run_id}-contribute",
        )
    else:
        contribution = {
            "ok": False,
            "skipped": False,
            "status": "not_run",
            "run_id": f"{resolved_run_id}-contribute",
            "reason": "organization-maintenance-blocked",
            "not_run_reason": "organization maintenance did not produce a valid current snapshot",
        }
    child_ok = bool(maintenance.get("ok")) and bool(contribution.get("ok"))
    cycle = {
        "schema_version": 1,
        "kind": "organization-maintenance-cycle",
        "run_id": resolved_run_id,
        "status": "completed" if child_ok else "failed",
        "sequence": ["organization-maintenance", "organization-contribution"],
        "maintenance": maintenance,
        "contribution": contribution,
        "snapshot": (contribution.get("sync") or {}).get("snapshot")
        or (maintenance.get("sync") or {}).get("snapshot")
        or {},
    }
    cycle_root = repo_root / ".local" / "maintenance-cycles" / resolved_run_id
    cycle_root.mkdir(parents=True, exist_ok=True)
    cycle_path = cycle_root / "cycle-receipt.json"
    cycle_path.write_text(json.dumps(cycle, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    postflight_path = ""
    if not maintenance.get("skipped") or not contribution.get("skipped"):
        observation = build_observation(
            task_summary="Organization maintenance cycle synchronized the local card snapshot",
            route_hint="system/knowledge-library/organization",
            hit_quality="trusted",
            outcome=cycle["status"],
            comment="The organization cycle maintained the shared repository and refreshed a complete local snapshot; local retrieval remains read-only and direct-use does not auto-adopt cards.",
            suggested_action="none" if child_ok else "update-card",
            exposed_gap=not child_ok,
            scenario="A machine participates in organization synchronization.",
            action_taken="Ran organization maintenance followed by contribution through the existing native facades.",
            observed_result=f"maintenance={maintenance.get('ok')} contribution={contribution.get('ok')}",
            operational_use="Use the current snapshot for retrieval; Sleep owns any later local model publication.",
            reuse_judgment="Reusable for other machines that need the same two-owner organization cycle.",
            source_kind="organization-maintenance",
            agent_name="kb-organization-cycle",
            workspace_root=str(repo_root),
        )
        try:
            postflight_path = str(record_observation(repo_root, observation))
        except Exception:
            postflight_path = ""
    return {
        **maintenance,
        "ok": child_ok,
        "skipped": bool(maintenance.get("skipped") and contribution.get("skipped")),
        "run_id": resolved_run_id,
        "status": cycle["status"],
        "cycle_run_id": resolved_run_id,
        "maintenance": maintenance,
        "contribution": contribution,
        "snapshot": cycle["snapshot"],
        "cycle_receipt_path": str(cycle_path),
        "postflight_path": postflight_path,
        "postflight_recorded": bool(postflight_path),
    }
