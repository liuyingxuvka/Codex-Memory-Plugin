from __future__ import annotations

from pathlib import Path
from typing import Any

from local_kb.card_ids import installation_short_label
from local_kb.feedback import build_observation, record_observation
from local_kb.org_contribution import prepare_organization_import_branch
from local_kb.org_maintenance import build_organization_maintenance_report
from local_kb.org_outbox import build_organization_outbox, organization_outbox_dir
from local_kb.search import search_entries
from local_kb.settings import (
    load_desktop_settings,
    maintenance_participation_status_from_settings,
    organization_sources_from_settings,
)


ORG_AUTOMATION_ROUTE = "system/knowledge-library/organization"


def _preflight(repo_root: Path, *, query: str) -> dict[str, Any]:
    results = search_entries(
        repo_root,
        query=query,
        path_hint=ORG_AUTOMATION_ROUTE,
        top_k=5,
    )
    return {
        "route_hint": ORG_AUTOMATION_ROUTE,
        "query": query,
        "matched_entry_ids": [str(item.data.get("id") or item.path.stem) for item in results],
        "matched_entry_count": len(results),
    }


def _record_postflight(
    repo_root: Path,
    *,
    task_summary: str,
    preflight: dict[str, Any],
    outcome: str,
    comment: str,
    action_taken: str,
    observed_result: str,
    operational_use: str,
    agent_name: str,
    suggested_action: str = "none",
) -> str:
    observation = build_observation(
        task_summary=task_summary,
        route_hint=ORG_AUTOMATION_ROUTE,
        entry_ids=",".join(preflight.get("matched_entry_ids", [])),
        hit_quality="hit" if preflight.get("matched_entry_ids") else "none",
        outcome=outcome,
        comment=comment,
        scenario="Scheduled organization KB automation ran against a locally configured organization source.",
        action_taken=action_taken,
        observed_result=observed_result,
        operational_use=operational_use,
        reuse_judgment="Reusable as an audit trail for organization KB automation behavior.",
        suggested_action=suggested_action,
        source_kind="automation",
        agent_name=agent_name,
        project_ref="organization-kb",
        workspace_root=str(repo_root),
    )
    path = record_observation(repo_root, observation)
    return str(path)


def _first_organization_source(repo_root: Path) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    settings = load_desktop_settings(repo_root)
    sources = organization_sources_from_settings(settings)
    if not sources:
        return {}, [], settings
    return sources[0], sources, settings


def run_organization_contribution(
    repo_root: Path,
    *,
    dry_run: bool = False,
    prepare_branch: bool = False,
    contributor_id: str = "",
    branch_name: str = "",
    commit: bool = True,
    push: bool = False,
    remote: str = "origin",
    base_branch: str = "main",
    record_postflight: bool = True,
) -> dict[str, Any]:
    repo_root = Path(repo_root)
    source, sources, settings = _first_organization_source(repo_root)
    if not source:
        return {
            "ok": True,
            "skipped": True,
            "reason": "organization mode is not connected to a validated repository",
            "settings_gate": {
                "available": False,
                "mode": str(settings.get("mode") or "personal"),
                "organization_validated": bool(
                    (settings.get("organization") if isinstance(settings.get("organization"), dict) else {}).get(
                        "validated"
                    )
                ),
            },
            "settings_mode": str(settings.get("mode") or "personal"),
            "preflight": {},
            "postflight_recorded": False,
        }

    organization_id = str(source.get("organization_id") or "").strip()
    preflight = _preflight(
        repo_root,
        query="organization contribution outbox card upload content hash skill dependency",
    )
    outbox = build_organization_outbox(
        repo_root,
        organization_id=organization_id,
        dry_run=dry_run,
        organization_sources=sources,
    )
    branch_result: dict[str, Any] = {"attempted": False}
    if outbox.get("ok") and prepare_branch and not dry_run and int(outbox.get("created_count", 0) or 0) > 0:
        branch_result = prepare_organization_import_branch(
            Path(str(source.get("path") or "")),
            organization_outbox_dir(repo_root, organization_id),
            contributor_id=contributor_id or installation_short_label(repo_root),
            branch_name=branch_name,
            commit=commit,
            push=push,
            remote=remote,
            base_branch=base_branch,
        )
        branch_result["attempted"] = True

    ok = bool(outbox.get("ok")) and bool(branch_result.get("ok", True))
    postflight_path = ""
    if record_postflight and not dry_run:
        postflight_path = _record_postflight(
            repo_root,
            task_summary="Organization KB contribution automation",
            preflight=preflight,
            outcome=(
                f"created={outbox.get('created_count', 0)} skipped={outbox.get('skipped_count', 0)} "
                f"branch_attempted={bool(branch_result.get('attempted'))}"
            ),
            comment="Organization contribution automation inspected local shareable cards and prepared organization proposals when eligible.",
            action_taken="Read desktop organization settings, ran content-hash-gated organization outbox export, and optionally prepared an import branch.",
            observed_result=f"Outbox created {outbox.get('created_count', 0)} proposal(s).",
            operational_use="Use this audit event to confirm scheduled contribution automation is respecting organization-mode settings and content-hash dedupe.",
            agent_name="kb-organization-contribute",
        )

    return {
        "ok": ok,
        "skipped": False,
        "settings_gate": {
            "available": True,
            "mode": str(settings.get("mode") or "personal"),
            "organization_validated": True,
        },
        "organization_id": organization_id,
        "source": source,
        "preflight": preflight,
        "outbox": outbox,
        "branch": branch_result,
        "postflight_recorded": bool(postflight_path),
        "postflight_path": postflight_path,
    }


def run_organization_maintenance(
    repo_root: Path,
    *,
    record_postflight: bool = True,
) -> dict[str, Any]:
    repo_root = Path(repo_root)
    settings = load_desktop_settings(repo_root)
    participation = maintenance_participation_status_from_settings(settings)
    sources = organization_sources_from_settings(settings)
    if not participation.get("available") or not sources:
        return {
            "ok": True,
            "skipped": True,
            "reason": str(participation.get("reason") or "organization maintenance participation is not available"),
            "settings_gate": {
                "available": False,
                "mode": str(settings.get("mode") or "personal"),
                "organization_validated": bool(
                    (settings.get("organization") if isinstance(settings.get("organization"), dict) else {}).get(
                        "validated"
                    )
                ),
                "maintenance_requested": bool(participation.get("requested")),
            },
            "participation": participation,
            "preflight": {},
            "postflight_recorded": False,
        }

    source = sources[0]
    organization_id = str(source.get("organization_id") or "").strip()
    preflight = _preflight(
        repo_root,
        query="organization maintenance review candidates skills merge split auto merge",
    )
    report = build_organization_maintenance_report(
        Path(str(source.get("path") or "")),
        repo_root=repo_root,
        organization_id=organization_id,
    )
    postflight_path = ""
    if record_postflight:
        postflight_path = _record_postflight(
            repo_root,
            task_summary="Organization KB maintenance automation",
            preflight=preflight,
            outcome=(
                f"candidate_count={report.get('candidate_count', 0)} "
                f"skill_count={report.get('skill_count', 0)} "
                f"recommendations={len(report.get('recommendations', []))}"
            ),
            comment="Organization maintenance automation inspected the validated organization mirror and produced a review report.",
            action_taken="Read desktop organization maintenance settings, validated participation, then inspected the organization KB mirror with organization-review requirements.",
            observed_result=f"Report recommendations: {', '.join(report.get('recommendations', [])) or 'none'}.",
            operational_use="Use this audit event to confirm scheduled organization maintenance runs only on opted-in machines and leaves reviewable recommendations.",
            agent_name="kb-organization-maintenance",
        )

    return {
        "ok": bool(report.get("ok")),
        "skipped": False,
        "settings_gate": {
            "available": True,
            "mode": str(settings.get("mode") or "personal"),
            "organization_validated": True,
            "maintenance_requested": bool(participation.get("requested")),
        },
        "organization_id": organization_id,
        "source": source,
        "participation": participation,
        "preflight": preflight,
        "report": report,
        "postflight_recorded": bool(postflight_path),
        "postflight_path": postflight_path,
    }
