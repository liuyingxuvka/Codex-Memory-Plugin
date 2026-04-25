from __future__ import annotations

from pathlib import Path
from typing import Any

from local_kb.org_checks import check_organization_repository
from local_kb.org_cleanup import build_organization_cleanup_proposal
from local_kb.org_outbox import organization_outbox_dir
from local_kb.org_sources import validate_organization_repo
from local_kb.skill_sharing import find_local_skill_metadata
from local_kb.store import load_organization_entries


ORGANIZATION_REVIEW_SKILL_ID = "organization-review"


def build_organization_maintenance_report(
    org_root: Path,
    *,
    repo_root: Path | None = None,
    organization_id: str = "",
) -> dict[str, Any]:
    validation = validate_organization_repo(org_root)
    if not validation.get("ok"):
        return {
            "ok": False,
            "validation": validation,
            "entry_count": 0,
            "outbox_count": 0,
            "recommendations": ["fix-organization-repository-validation"],
        }

    organization_id = organization_id or str(validation.get("organization_id") or "")
    entries = load_organization_entries(
        Path(org_root),
        organization_id,
        source_commit=str(validation.get("commit") or ""),
    )
    organization_check = check_organization_repository(org_root)
    duplicate_content_hashes = (
        organization_check.get("checks", {})
        .get("cards", {})
        .get("duplicate_content_hashes", {})
    )
    if not isinstance(duplicate_content_hashes, dict):
        duplicate_content_hashes = {}

    outbox_count = 0
    review_skill: dict[str, Any] = {
        "id": ORGANIZATION_REVIEW_SKILL_ID,
        "installed": False,
        "status": "missing",
    }
    if repo_root is not None:
        outbox_dir = organization_outbox_dir(Path(repo_root), organization_id)
        outbox_count = len(list(outbox_dir.glob("*.yaml"))) if outbox_dir.exists() else 0
        skill_metadata = find_local_skill_metadata(Path(repo_root), ORGANIZATION_REVIEW_SKILL_ID)
        if skill_metadata is not None:
            review_skill = {
                **skill_metadata,
                "installed": True,
            }

    recommendations: list[str] = []
    if validation.get("candidate_count", 0):
        recommendations.append("review-organization-candidates")
    if outbox_count:
        recommendations.append("review-local-outbox-proposals")
    if validation.get("skill_count", 0):
        recommendations.append("review-skill-registry")
    if duplicate_content_hashes:
        recommendations.append("review-duplicate-card-content-hashes")
    if organization_check.get("errors"):
        recommendations.append("fix-organization-check-errors")
    if not review_skill["installed"]:
        recommendations.append("install-organization-review-skill-before-full-maintenance")
    cleanup_proposal = build_organization_cleanup_proposal(org_root, organization_id=organization_id)
    cleanup_actions = cleanup_proposal.get("actions") if isinstance(cleanup_proposal.get("actions"), list) else []
    if cleanup_actions:
        recommendations.append("review-organization-cleanup-proposals")

    return {
        "ok": True,
        "validation": validation,
        "organization_check": {
            "ok": bool(organization_check.get("ok")),
            "error_count": len(organization_check.get("errors") or []),
            "warning_count": len(organization_check.get("warnings") or []),
            "auto_merge_eligible": bool(organization_check.get("auto_merge_eligible")),
            "auto_merge_blockers": organization_check.get("auto_merge_blockers") or [],
        },
        "cleanup": {
            "duplicate_content_hash_count": len(duplicate_content_hashes),
            "duplicate_content_hashes": duplicate_content_hashes,
            "proposal_action_count": len(cleanup_actions),
            "proposal_counts": cleanup_proposal.get("counts") or {},
            "similar_card_merge_apply": "planned",
            "weak_card_rejection_apply": "planned",
            "candidate_delete_apply": "planned",
            "skill_bundle_cleanup_apply": "partial",
        },
        "organization_id": organization_id,
        "entry_count": len(entries),
        "trusted_count": validation.get("trusted_count", 0),
        "candidate_count": validation.get("candidate_count", 0),
        "skill_count": validation.get("skill_count", 0),
        "outbox_count": outbox_count,
        "organization_review_skill": review_skill,
        "recommendations": recommendations,
    }
