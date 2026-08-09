from __future__ import annotations

from pathlib import Path
from typing import Any

from local_kb.org_checks import check_organization_repository
from local_kb.org_cleanup import apply_organization_cleanup_proposal, build_organization_cleanup_proposal
from local_kb.org_outbox import organization_outbox_dir
from local_kb.org_sources import validate_organization_repo
from local_kb.skill_sharing import find_local_skill_metadata, load_organization_skill_registry
from local_kb.store import load_organization_entries


ORGANIZATION_REVIEW_SKILL_ID = "organization-review"


def _card_surface_checkpoint(
    *,
    validation: dict[str, Any],
    organization_check: dict[str, Any],
    card_decisions: list[dict[str, Any]],
    duplicate_content_hashes: dict[str, Any],
    skill_safety_checkpoint: dict[str, Any],
) -> dict[str, Any]:
    """Project the organization card surface into one explicit checkpoint."""

    low_confidence_main_trusted = [
        str(item.get("entry_id") or "")
        for item in card_decisions
        if isinstance(item, dict)
        and str(item.get("target_path") or "").replace("\\", "/").startswith("kb/main/")
        and str((item.get("evidence") or {}).get("status") or "") == "trusted"
        and float((item.get("evidence") or {}).get("confidence") or 0.0) < 0.45
    ]
    stale_status_ids = [
        str(item.get("entry_id") or "")
        for item in card_decisions
        if isinstance(item, dict)
        and str((item.get("evidence") or {}).get("status") or "") in {"rejected", "deprecated"}
    ]
    card_check = ((organization_check.get("checks") or {}).get("cards") or {})
    privacy_check = ((organization_check.get("checks") or {}).get("privacy_scan") or {})
    retired_residuals = [
        str(error)
        for error in validation.get("errors") or []
        if "obsolete" in str(error).lower() or "retired" in str(error).lower()
    ]
    return {
        "complete": bool(
            validation.get("ok")
            and organization_check.get("ok")
            and isinstance(validation.get("main_status_counts"), dict)
            and isinstance(validation.get("imports_status_counts"), dict)
            and not retired_residuals
        ),
        "main_status_counts": dict(validation.get("main_status_counts") or {}),
        "imports_status_counts": dict(validation.get("imports_status_counts") or {}),
        "main_count": int(validation.get("main_count") or 0),
        "main_active_count": int(validation.get("main_active_count") or 0),
        "imports_count": int(validation.get("imports_count") or 0),
        "trusted_count": int(validation.get("trusted_count") or 0),
        "candidate_count": int(validation.get("candidate_count") or 0),
        "low_confidence_main_trusted_entry_ids": low_confidence_main_trusted,
        "stale_rejected_or_deprecated_entry_ids": stale_status_ids,
        "duplicate_content_hash_count": len(duplicate_content_hashes),
        "skill_linked_card_count": int(card_check.get("bundle_count") or 0),
        "retired_layout_residual_count": len(retired_residuals),
        "privacy_risk_count": len(privacy_check.get("errors") or []),
        "skill_risk_count": len(skill_safety_checkpoint.get("errors") or []),
        "errors": [
            *[str(item) for item in organization_check.get("errors") or []],
            *retired_residuals,
        ],
    }


def _candidate_intake_checkpoint(
    *,
    validation: dict[str, Any],
    card_decisions: list[dict[str, Any]],
    cleanup_actions: list[dict[str, Any]],
    cleanup_review: dict[str, Any],
) -> dict[str, Any]:
    import_decisions = [
        item
        for item in card_decisions
        if isinstance(item, dict)
        and str(item.get("target_path") or "").replace("\\", "/").startswith("kb/imports/")
    ]
    import_actions = [
        item
        for item in cleanup_actions
        if isinstance(item, dict)
        and str(item.get("target_path") or "").replace("\\", "/").startswith("kb/imports/")
    ]
    import_review_rows = [
        item
        for item in cleanup_review.get("decisions") or []
        if isinstance(item, dict)
        and str(item.get("target_path") or "").replace("\\", "/").startswith("kb/imports/")
    ]
    accepted = [
        str(item.get("action_id") or "")
        for item in import_review_rows
        if str(item.get("decision") or "") == "selected-for-apply"
    ]
    rejected = [
        str(item.get("action_id") or "")
        for item in import_review_rows
        if str(item.get("decision") or "") in {"keep", "blocked_evidence"}
    ]
    import_count = int(validation.get("imports_count") or 0)
    return {
        "complete": bool(
            validation.get("ok")
            and import_count >= 0
            and len(import_decisions) == import_count
            and len({str(item.get("decision_id") or "") for item in import_decisions}) == len(import_decisions)
            and len(import_review_rows) == len(import_actions) + len(import_decisions) - len(import_actions)
        ),
        "imports_count": import_count,
        "import_status_counts": dict(validation.get("imports_status_counts") or {}),
        "reviewed_import_count": len(import_decisions),
        "proposal_action_count": len(import_actions),
        "accepted_action_ids": sorted(set(accepted)),
        "rejected_or_blocked_action_ids": sorted(set(rejected)),
        "decision_ids": [str(item.get("decision_id") or "") for item in import_decisions],
        "errors": [],
    }


def _content_hash_checkpoint(
    *,
    validation: dict[str, Any],
    organization_check: dict[str, Any],
    duplicate_content_hashes: dict[str, Any],
    cleanup_actions: list[dict[str, Any]],
) -> dict[str, Any]:
    duplicate_actions = [
        item
        for item in cleanup_actions
        if isinstance(item, dict) and str(item.get("action_type") or "") == "mark-duplicate"
    ]
    duplicate_ids = [str(item.get("action_id") or "") for item in duplicate_actions]
    card_check = ((organization_check.get("checks") or {}).get("cards") or {})
    return {
        "complete": bool(
            validation.get("ok")
            and organization_check.get("ok")
            and isinstance(duplicate_content_hashes, dict)
            and len(duplicate_ids) == len(set(duplicate_ids))
            and not any(
                "duplicate card id" in str(error).lower()
                for error in card_check.get("errors") or []
            )
        ),
        "duplicate_content_hash_count": len(duplicate_content_hashes),
        "duplicate_content_hashes": duplicate_content_hashes,
        "duplicate_decision_ids": duplicate_ids,
        "source_generation_id": str(validation.get("source_generation_id") or ""),
        "source_catalog_digest": str(validation.get("source_catalog_digest") or ""),
        "current_identity_count": len(validation.get("main_active_entry_ids") or []),
        "errors": [str(item) for item in organization_check.get("errors") or []],
    }


def _skill_bundle_version_checkpoint(
    org_root: Path,
    *,
    organization_id: str,
    validation: dict[str, Any],
    cleanup_actions: list[dict[str, Any]],
    skill_safety_checkpoint: dict[str, Any],
) -> dict[str, Any]:
    """Bind card Skill versions by bundle id without installing anything."""

    all_entries = load_organization_entries(
        Path(org_root),
        organization_id,
        source_commit=str(validation.get("commit") or ""),
        scopes=("main", "imports"),
        allowed_statuses=None,
    )
    by_bundle: dict[str, list[dict[str, Any]]] = {}
    for entry in all_entries:
        proposal = entry.data.get("organization_proposal")
        dependencies = proposal.get("skill_dependencies") if isinstance(proposal, dict) else []
        if not isinstance(dependencies, list):
            continue
        for dependency in dependencies:
            if not isinstance(dependency, dict):
                continue
            bundle_id = str(dependency.get("bundle_id") or "").strip()
            if not bundle_id:
                continue
            by_bundle.setdefault(bundle_id, []).append(
                {
                    "entry_id": str(entry.data.get("id") or ""),
                    "path": entry.path.relative_to(Path(org_root)).as_posix(),
                    "bundle_id": bundle_id,
                    "content_hash": str(dependency.get("content_hash") or ""),
                    "version_time": str(dependency.get("version_time") or ""),
                    "original_author": str(dependency.get("original_author") or ""),
                    "status": str(entry.data.get("status") or ""),
                    "source": "card-dependency",
                }
            )

    registry = load_organization_skill_registry(Path(org_root))
    registry_errors = [str(item) for item in registry.get("errors") or []]
    for item in registry.get("skills") or []:
        if not isinstance(item, dict):
            continue
        bundle_id = str(item.get("bundle_id") or "").strip()
        if not bundle_id:
            continue
        by_bundle.setdefault(bundle_id, []).append(
            {
                "entry_id": str(item.get("id") or ""),
                "path": "skills/registry.yaml",
                "bundle_id": bundle_id,
                "content_hash": str(item.get("content_hash") or ""),
                "version_time": str(item.get("version_time") or item.get("version") or ""),
                "original_author": str(item.get("original_author") or item.get("owner") or ""),
                "status": str(item.get("status") or ""),
                "source": "registry",
            }
        )

    bundles: list[dict[str, Any]] = []
    latest_approved_by_bundle: dict[str, dict[str, Any]] = {}
    forked_versions: list[dict[str, Any]] = []
    for bundle_id, versions in sorted(by_bundle.items()):
        ordered = sorted(versions, key=lambda item: (item["version_time"], item["content_hash"], item["entry_id"]))
        authors = sorted({str(item.get("original_author") or "") for item in ordered if item.get("original_author")})
        latest = ordered[-1] if ordered else {}
        lineage_author = next(
            (str(item.get("original_author") or "") for item in ordered if item.get("original_author")),
            "",
        )
        for item in ordered:
            item_author = str(item.get("original_author") or "")
            if lineage_author and item_author and item_author != lineage_author:
                forked_versions.append(
                    {
                        "bundle_id": bundle_id,
                        "entry_id": str(item.get("entry_id") or ""),
                        "original_author": item_author,
                        "lineage_original_author": lineage_author,
                        "content_hash": str(item.get("content_hash") or ""),
                        "version_time": str(item.get("version_time") or ""),
                    }
                )
        approved = [
            item
            for item in ordered
            if str(item.get("status") or "").strip().lower() == "approved"
            and str(item.get("version_time") or "").strip()
            and str(item.get("content_hash") or "").startswith("sha256:")
        ]
        approved_authors = sorted({str(item.get("original_author") or "") for item in approved if item.get("original_author")})
        approved_lineage_author = approved_authors[0] if approved_authors else ""
        same_author = [
            item for item in approved
            if not approved_lineage_author or str(item.get("original_author") or "") == approved_lineage_author
        ]
        fork_keys = {
            (str(item.get("bundle_id") or ""), str(item.get("entry_id") or ""), str(item.get("content_hash") or ""))
            for item in forked_versions
        }
        for item in approved:
            item_author = str(item.get("original_author") or "")
            key = (bundle_id, str(item.get("entry_id") or ""), str(item.get("content_hash") or ""))
            if approved_lineage_author and item_author and item_author != approved_lineage_author and key not in fork_keys:
                forked_versions.append(
                    {
                        "bundle_id": bundle_id,
                        "entry_id": str(item.get("entry_id") or ""),
                        "original_author": item_author,
                        "lineage_original_author": approved_lineage_author,
                        "content_hash": str(item.get("content_hash") or ""),
                        "version_time": str(item.get("version_time") or ""),
                    }
                )
        if same_author:
            selected = sorted(
                same_author,
                key=lambda item: (item["version_time"], item["content_hash"], item["entry_id"]),
            )[-1]
            latest_approved_by_bundle[bundle_id] = {
                "entry_id": str(selected.get("entry_id") or ""),
                "content_hash": str(selected.get("content_hash") or ""),
                "version_time": str(selected.get("version_time") or ""),
                "original_author": str(selected.get("original_author") or ""),
                "status": "approved",
            }
        bundles.append(
            {
                "bundle_id": bundle_id,
                "version_count": len(ordered),
                "original_authors": authors,
                "approved_version_count": len(approved),
                "approved_authors": approved_authors,
                "latest_version": {
                    "version_time": str(latest.get("version_time") or ""),
                    "content_hash": str(latest.get("content_hash") or ""),
                    "entry_id": str(latest.get("entry_id") or ""),
                },
                "version_times": [str(item.get("version_time") or "") for item in ordered],
            }
        )

    version_actions = [
        item
        for item in cleanup_actions
        if str(item.get("action_type") or "") in {"skill-version-select", "skill-bundle-fork-required", "skill-bundle-safety-block"}
    ]
    version_decision_ids = [str(item.get("action_id") or "") for item in version_actions]
    errors: list[str] = []
    for bundle in bundles:
        approved_count = int(bundle.get("approved_version_count") or 0)
        if approved_count and bundle["bundle_id"] not in latest_approved_by_bundle:
            errors.append(f"bundle {bundle['bundle_id']} has no same-author approved version")
    errors.extend(registry_errors)
    for bundle in bundles:
        if any(
            str(item.get("status") or "").strip().lower() == "approved"
            and (
                not str(item.get("version_time") or "").strip()
                or not str(item.get("content_hash") or "").startswith("sha256:")
            )
            for item in by_bundle.get(bundle["bundle_id"], [])
        ):
            errors.append(f"bundle {bundle['bundle_id']} is missing a hash-pinned version")
    return {
        "complete": bool(
            skill_safety_checkpoint.get("complete") is True
            and isinstance(bundles, list)
            and len(version_decision_ids) == len(set(version_decision_ids))
            and not errors
        ),
        "passed": bool(skill_safety_checkpoint.get("passed") is True and not errors),
        "bundle_count": len(bundles),
        "bundles": bundles,
        "version_decision_ids": version_decision_ids,
        "latest_approved_by_bundle": latest_approved_by_bundle,
        "forked_versions": forked_versions,
        "registry_error_count": len(registry_errors),
        "errors": errors,
        "not_applicable": not bool(bundles),
    }


def _apply_changed_paths(org_root: Path, apply_result: dict[str, Any]) -> list[str]:
    declared = [str(item).replace("\\", "/") for item in apply_result.get("changed_paths") or [] if str(item)]
    if declared:
        return sorted(set(declared))
    paths: set[str] = set()
    for item in apply_result.get("applied") or []:
        if not isinstance(item, dict):
            continue
        for key in ("target_path", "updated_path"):
            value = str(item.get(key) or "").strip().replace("\\", "/")
            if value:
                paths.add(value)
    audit_path = str(apply_result.get("audit_path") or "").strip()
    if audit_path:
        try:
            paths.add(Path(audit_path).resolve().relative_to(Path(org_root).resolve()).as_posix())
        except ValueError:
            pass
    return sorted(paths)


def _merge_readiness(
    *,
    changed_files: list[str],
    post_apply_check: dict[str, Any],
    exact_selected_apply: dict[str, Any],
    skill_safety_checkpoint: dict[str, Any],
) -> dict[str, Any]:
    blockers: list[str] = []
    allowed_prefixes = ("kb/imports/", "kb/main/", "kb/logicguard/bundles/")
    allowed_exact = {
        "maintenance/cleanup_audit.jsonl",
        "kb/organization_catalog.json",
        "khaos_org_kb.yaml",
    }
    if not changed_files:
        blockers.append("no reviewed maintenance changes")
    if "maintenance/cleanup_audit.jsonl" not in changed_files:
        blockers.append("cleanup audit receipt is missing")
    outside = [
        path
        for path in changed_files
        if not path.startswith(allowed_prefixes) and path not in allowed_exact
    ]
    if outside:
        blockers.append(f"changed paths are outside the maintenance allowlist: {outside}")
    if post_apply_check and post_apply_check.get("ok") is not True:
        blockers.append("post-apply organization check failed")
    if exact_selected_apply.get("exact") is not True:
        blockers.append("applied action ids do not exactly match the selected ids")
    if skill_safety_checkpoint.get("passed") is not True:
        blockers.append("Skill safety, author, fork, or version checkpoint failed")
    return {
        "complete": True,
        "eligible": not blockers,
        "blockers": blockers,
        "changed_files": changed_files,
        "requires_cleanup_audit": True,
        "label": "org-kb:auto-merge" if not blockers else "",
    }


def _report_layout_policy(validation: dict[str, Any]) -> dict[str, Any]:
    return {
        "target_layout": "main-imports",
        "incoming_lane_path": str(validation.get("incoming_lane_path") or "kb/imports"),
        "exchange_surface_path": str(validation.get("exchange_surface_path") or "kb/main"),
        "local_download_primary_path": str(validation.get("local_download_primary_path") or "kb/main"),
        "local_download_paths": validation.get("local_download_paths") or ["kb/main"],
        "local_download_excluded_paths": validation.get("local_download_excluded_paths") or ["kb/imports"],
        "contribution_writes": ["kb/imports"],
        "maintenance_moves_reviewed_cards_to": "kb/main",
        "current_layout_only": True,
    }


def build_organization_cleanup_review(proposal: dict[str, Any]) -> dict[str, Any]:
    decisions: list[dict[str, Any]] = []
    selected_action_ids: list[str] = []
    selected_action_types: set[str] = set()
    allow_trusted = False
    allow_delete = False
    allow_promote = False

    for action in proposal.get("actions") or []:
        if not isinstance(action, dict):
            continue
        action_id = str(action.get("action_id") or "").strip()
        action_type = str(action.get("action_type") or "").strip()
        target_path = str(action.get("target_path") or "").replace("\\", "/")
        risk = str(action.get("risk") or "").strip()
        approve = False
        decision = "keep"
        reason = ""

        if action.get("apply_supported") is False:
            source_reason = str(action.get("reason") or "").strip()
            decision = str(action.get("review_status") or "blocked_evidence")
            missing_roles = [str(item) for item in action.get("missing_roles") or []]
            reason = (f"{source_reason} Reopen only when new evidence satisfies: {missing_roles}.").strip()
        elif action_type in {"merge-cards", "split-card"}:
            packet = action.get("apply_packet") if isinstance(action.get("apply_packet"), dict) else {}
            approve = packet.get("review_status") == "ready" and bool(packet.get("packet_digest"))
            decision = "selected-for-apply" if approve else "blocked_evidence"
            reason = (
                "A complete reversible apply packet is ready and selected."
                if approve
                else "Merge/split remains blocked until its packet declares complete outputs and field ownership."
            )
        elif action_type == "delete-card":
            current_status = str(action.get("current_status") or "").strip()
            current_confidence = float(action.get("current_confidence") or 1.0)
            approve = (
                not target_path.startswith("kb/main/")
                and current_status in {"rejected", "deprecated"}
                and current_confidence <= 0.2
            )
            reason = (
                "Rejected or deprecated low-confidence organization card can be deleted with audit."
                if approve
                else "Deletion did not meet the audited low-confidence rejected/deprecated card rule."
            )
        elif action_type == "promote-card":
            proposed_path = str(action.get("proposed_path") or "").replace("\\", "/")
            approve = (
                str(action.get("current_status") or "") == "candidate"
                and str(action.get("proposed_status") or "") == "trusted"
                and proposed_path.startswith("kb/main/")
                and float(action.get("current_confidence") or 0.0) >= 0.85
            )
            reason = (
                "High-confidence candidate has a concrete main target path and can be promoted."
                if approve
                else "Promotion did not meet the organization Sleep promotion rule."
            )
        elif action_type == "accept-import":
            proposed_path = str(action.get("proposed_path") or "").replace("\\", "/")
            approve = (
                target_path.startswith("kb/imports/")
                and str(action.get("current_status") or "") == "candidate"
                and str(action.get("proposed_status") or "") == "candidate"
                and proposed_path.startswith("kb/main/")
            )
            reason = (
                "Imported candidate has a concrete main target path and can enter the organization exchange surface."
                if approve
                else "Import acceptance did not meet the organization Sleep main-transfer rule."
            )
        elif action_type in {"status-adjust", "confidence-adjust", "mark-duplicate"}:
            approve = True
            reason = "Deterministic organization cleanup action is selected for Sleep-style apply."
        else:
            decision = "blocked_evidence"
            reason = "Unknown organization cleanup action type is blocked with no executable packet."

        if approve:
            decision = "selected-for-apply"
            selected_action_ids.append(action_id)
            selected_action_types.add(action_type)
            if target_path.startswith("kb/main/"):
                allow_trusted = True
            if action_type == "delete-card":
                allow_delete = True
            if action_type in {"accept-import", "promote-card"}:
                allow_promote = True

        decisions.append(
            {
                "action_id": action_id,
                "action_type": action_type,
                "target_path": target_path,
                "decision": decision,
                "risk": risk,
                "reason": reason,
            }
        )

    action_by_id = {
        str(action.get("action_id") or ""): action
        for action in proposal.get("actions") or []
        if isinstance(action, dict)
    }
    selected_set = set(selected_action_ids)
    selected_targets = {
        str(action_by_id[action_id].get("target_path") or "")
        for action_id in selected_set
        if action_id in action_by_id
        and str(action_by_id[action_id].get("action_type") or "") not in {"merge-cards", "split-card"}
    }
    for decision_row in decisions:
        action_id = str(decision_row.get("action_id") or "")
        action = action_by_id.get(action_id, {})
        if action_id not in selected_set or str(action.get("action_type") or "") not in {"merge-cards", "split-card"}:
            continue
        packet = action.get("apply_packet") if isinstance(action.get("apply_packet"), dict) else {}
        input_paths = {str(item.get("path") or "") for item in packet.get("inputs") or [] if isinstance(item, dict)}
        if input_paths & selected_targets:
            selected_set.remove(action_id)
            decision_row["decision"] = "blocked_evidence"
            decision_row["reason"] = "Another selected lifecycle action changes this packet input first; reopen the merge/split packet against the rebuilt source generation."

    # A proposal may contain several individually valid merge/split packets whose
    # inputs overlap.  Applying the first packet changes the generation observed
    # by every later overlapping packet, so selecting all of them would make an
    # exact-selected apply impossible by construction.  Keep the deterministic
    # proposal order and select a maximal non-overlapping packet set; deferred
    # packets remain visible and must be rebuilt from the next source generation.
    reserved_packet_paths: set[str] = set()
    for action_id in selected_action_ids:
        action = action_by_id.get(action_id, {})
        if action_id not in selected_set or str(action.get("action_type") or "") not in {"merge-cards", "split-card"}:
            continue
        packet = action.get("apply_packet") if isinstance(action.get("apply_packet"), dict) else {}
        input_paths = {
            str(item.get("path") or "").replace("\\", "/")
            for item in packet.get("inputs") or []
            if isinstance(item, dict) and str(item.get("path") or "")
        }
        output_paths = {
            str(item.get("target_path") or "").replace("\\", "/")
            for item in packet.get("outputs") or []
            if isinstance(item, dict) and str(item.get("target_path") or "")
        }
        packet_paths = input_paths | output_paths
        conflicts = sorted(packet_paths & reserved_packet_paths)
        if conflicts:
            selected_set.remove(action_id)
            decision_row = next(
                (row for row in decisions if str(row.get("action_id") or "") == action_id),
                None,
            )
            if decision_row is not None:
                decision_row["decision"] = "blocked_evidence"
                decision_row["reason"] = (
                    "Another selected merge/split packet changes the same materialized path in this batch "
                    f"({', '.join(conflicts)}); reopen this packet against the next source generation."
                )
            continue
        reserved_packet_paths.update(packet_paths)

    selected_action_ids = [item for item in selected_action_ids if item in selected_set]
    selected_action_types = {
        str(action_by_id[item].get("action_type") or "")
        for item in selected_action_ids
        if item in action_by_id
    }
    selected_actions = [action_by_id[item] for item in selected_action_ids if item in action_by_id]
    allow_trusted = any(
        str(action.get("target_path") or "").replace("\\", "/").startswith("kb/main/")
        or any(
            str(output.get("target_path") or "").replace("\\", "/").startswith("kb/main/")
            for output in (
                action.get("apply_packet", {}).get("outputs")
                if isinstance(action.get("apply_packet"), dict)
                else []
            ) or []
            if isinstance(output, dict)
        )
        for action in selected_actions
    )
    allow_delete = any(str(action.get("action_type") or "") == "delete-card" for action in selected_actions)
    allow_promote = any(
        str(action.get("action_type") or "") in {"accept-import", "promote-card"}
        for action in selected_actions
    )

    return {
        "decision_count": len(decisions),
        "selected_count": len(selected_action_ids),
        "selected_action_ids": selected_action_ids,
        "selected_action_types": sorted(selected_action_types),
        "approved_count": len(selected_action_ids),
        "approved_action_ids": selected_action_ids,
        "approved_action_types": sorted(selected_action_types),
        "allow_trusted": allow_trusted,
        "allow_delete": allow_delete,
        "allow_promote": allow_promote,
        "decisions": decisions,
    }


def build_organization_maintenance_report(
    org_root: Path,
    *,
    repo_root: Path | None = None,
    organization_id: str = "",
    apply_reviewed_cleanup: bool = False,
    dry_run: bool = False,
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
    imports_count = int(validation.get("imports_count") or 0)
    main_active_count = int(validation.get("main_active_count") or 0)
    if imports_count:
        recommendations.append("review-organization-imports")
    if main_active_count:
        recommendations.append("review-main-exchange-surface")
    if outbox_count:
        recommendations.append("review-local-outbox-proposals")
    if validation.get("skill_count", 0):
        recommendations.append("review-skill-registry")
    if duplicate_content_hashes:
        recommendations.append("review-duplicate-card-content-hashes")
    if organization_check.get("errors"):
        recommendations.append("fix-organization-check-errors")
    cleanup_proposal = build_organization_cleanup_proposal(org_root, organization_id=organization_id)
    cleanup_actions = cleanup_proposal.get("actions") if isinstance(cleanup_proposal.get("actions"), list) else []
    card_decisions = (
        cleanup_proposal.get("card_decisions")
        if isinstance(cleanup_proposal.get("card_decisions"), list)
        else []
    )
    cleanup_review = build_organization_cleanup_review(cleanup_proposal)
    cleanup_apply: dict[str, Any] = {"attempted": False}
    post_apply_check: dict[str, Any] = {}
    post_apply_validation: dict[str, Any] = {}
    if apply_reviewed_cleanup and cleanup_review["selected_action_ids"]:
        cleanup_apply = apply_organization_cleanup_proposal(
            Path(org_root),
            cleanup_proposal,
            allow_actions=set(cleanup_review["selected_action_types"]),
            allow_action_ids=set(cleanup_review["selected_action_ids"]),
            allow_trusted=bool(cleanup_review["allow_trusted"]),
            allow_delete=bool(cleanup_review["allow_delete"]),
            allow_promote=bool(cleanup_review["allow_promote"]),
            dry_run=dry_run,
        )
        cleanup_apply["attempted"] = True
        post_validation = validate_organization_repo(org_root)
        changed_files = _apply_changed_paths(Path(org_root), cleanup_apply)
        post_check = check_organization_repository(org_root, changed_files=changed_files)
        post_apply_check = {
            "ok": bool(post_check.get("ok")),
            "validation_ok": bool(post_validation.get("ok")),
            "error_count": len(post_check.get("errors") or []),
            "warning_count": len(post_check.get("warnings") or []),
            "auto_merge_blockers": post_check.get("auto_merge_blockers") or [],
            "changed_files": changed_files,
            "privacy_scan_ok": bool(
                ((post_check.get("checks") or {}).get("privacy_scan") or {}).get("ok")
            ),
        }
        post_apply_validation = {
            "ok": bool(post_validation.get("ok")),
            "layout": post_validation.get("layout"),
            "incoming_lane_path": post_validation.get("incoming_lane_path"),
            "exchange_surface_path": post_validation.get("exchange_surface_path"),
            "main_count": post_validation.get("main_count", 0),
            "main_active_count": post_validation.get("main_active_count", 0),
            "main_status_counts": post_validation.get("main_status_counts") or {},
            "imports_count": post_validation.get("imports_count", 0),
            "imports_status_counts": post_validation.get("imports_status_counts") or {},
            "trusted_count": post_validation.get("trusted_count", 0),
            "candidate_count": post_validation.get("candidate_count", 0),
        }
    trusted_cleanup_actions = [
        action
        for action in cleanup_actions
        if str(action.get("target_path") or "").replace("\\", "/").startswith("kb/main/")
    ]
    if cleanup_actions:
        recommendations.append("review-organization-cleanup-proposals")
    if trusted_cleanup_actions:
        recommendations.append("review-trusted-organization-card-maintenance")

    merge_actions = [
        action for action in cleanup_actions if str(action.get("action_type") or "") == "merge-cards"
    ]
    split_actions = [
        action for action in cleanup_actions if str(action.get("action_type") or "") == "split-card"
    ]
    skill_actions = [
        action
        for action in cleanup_actions
        if str(action.get("action_type") or "").startswith("skill-")
    ]
    blocking_skill_actions = [
        action
        for action in skill_actions
        if str(action.get("action_type") or "")
        in {"skill-bundle-safety-block", "skill-bundle-fork-required"}
    ]
    merge_split_checkpoint = {
        "complete": all(
            isinstance(action.get("apply_packet"), dict)
            and str(action.get("review_status") or "") in {"ready", "blocked_evidence", "keep_separate", "keep_single"}
            for action in [*merge_actions, *split_actions]
        ),
        "resolved": all(str(action.get("review_status") or "") in {"ready", "keep_separate", "keep_single"} for action in [*merge_actions, *split_actions]),
        "reviewed_card_count": int(cleanup_proposal.get("card_count") or 0),
        "merge_decision_ids": [str(action.get("action_id") or "") for action in merge_actions],
        "split_decision_ids": [str(action.get("action_id") or "") for action in split_actions],
        "no_merge_candidates": not merge_actions,
        "no_split_candidates": not split_actions,
        "blocked_evidence_action_ids": [
            str(action.get("action_id") or "")
            for action in [*merge_actions, *split_actions]
            if str(action.get("review_status") or "") == "blocked_evidence"
        ],
    }
    card_count = int(cleanup_proposal.get("card_count") or 0)
    card_decision_ids = [
        str(item.get("decision_id") or "")
        for item in card_decisions
        if isinstance(item, dict)
    ]
    card_decision_paths = [
        str(item.get("target_path") or "")
        for item in card_decisions
        if isinstance(item, dict)
    ]
    required_dimensions = {"scenario", "action", "prediction", "route", "evidence"}
    card_decision_checkpoint = {
        "complete": (
            len(card_decisions) == card_count
            and len(card_decision_ids) == len(set(card_decision_ids))
            and len(card_decision_paths) == len(set(card_decision_paths))
            and all(
                isinstance(item, dict)
                and str(item.get("decision") or "").strip()
                and str(item.get("reason") or "").strip()
                and set(item.get("reviewed_dimensions") or []) == required_dimensions
                for item in card_decisions
            )
        ),
        "card_count": card_count,
        "decision_count": len(card_decisions),
        "decision_ids": card_decision_ids,
        "decisions": card_decisions,
        "required_dimensions": sorted(required_dimensions),
    }
    skill_registry_check = (
        (organization_check.get("checks") or {}).get("skill_registry") or {}
        if isinstance(organization_check.get("checks"), dict)
        else {}
    )
    card_check = (
        (organization_check.get("checks") or {}).get("cards") or {}
        if isinstance(organization_check.get("checks"), dict)
        else {}
    )
    skill_safety_checkpoint = {
        "complete": True,
        "passed": (
            bool(skill_registry_check.get("ok"))
            and bool(card_check.get("ok"))
            and not blocking_skill_actions
        ),
        "skill_count": int(validation.get("skill_count") or 0),
        "bundle_count": int(card_check.get("bundle_count") or 0),
        "decision_ids": [str(action.get("action_id") or "") for action in skill_actions],
        "blocking_decision_ids": [str(action.get("action_id") or "") for action in blocking_skill_actions],
        "errors": [
            *[str(item) for item in skill_registry_check.get("errors") or []],
            *[str(item) for item in card_check.get("errors") or []],
        ],
    }
    card_surface_checkpoint = _card_surface_checkpoint(
        validation=validation,
        organization_check=organization_check,
        card_decisions=card_decisions,
        duplicate_content_hashes=duplicate_content_hashes,
        skill_safety_checkpoint=skill_safety_checkpoint,
    )
    candidate_intake_checkpoint = _candidate_intake_checkpoint(
        validation=validation,
        card_decisions=card_decisions,
        cleanup_actions=cleanup_actions,
        cleanup_review=cleanup_review,
    )
    content_hash_checkpoint = _content_hash_checkpoint(
        validation=validation,
        organization_check=organization_check,
        duplicate_content_hashes=duplicate_content_hashes,
        cleanup_actions=cleanup_actions,
    )
    split_checkpoint = {
        "complete": bool(
            all(
                isinstance(action.get("apply_packet"), dict)
                and str(action.get("review_status") or "")
                in {"ready", "blocked_evidence", "keep_single"}
                for action in split_actions
            )
        ),
        "resolved": all(
            str(action.get("review_status") or "") in {"ready", "keep_single"}
            for action in split_actions
        ),
        "decision_ids": [str(action.get("action_id") or "") for action in split_actions],
        "blocked_evidence_action_ids": [
            str(action.get("action_id") or "")
            for action in split_actions
            if str(action.get("review_status") or "") == "blocked_evidence"
        ],
        "count": len(split_actions),
    }
    merge_checkpoint = {
        "complete": bool(
            all(
                isinstance(action.get("apply_packet"), dict)
                and str(action.get("review_status") or "")
                in {"ready", "blocked_evidence", "keep_separate"}
                for action in merge_actions
            )
        ),
        "resolved": all(
            str(action.get("review_status") or "") in {"ready", "keep_separate"}
            for action in merge_actions
        ),
        "decision_ids": [str(action.get("action_id") or "") for action in merge_actions],
        "blocked_evidence_action_ids": [
            str(action.get("action_id") or "")
            for action in merge_actions
            if str(action.get("review_status") or "") == "blocked_evidence"
        ],
        "count": len(merge_actions),
    }
    skill_bundle_version_checkpoint = _skill_bundle_version_checkpoint(
        Path(org_root),
        organization_id=organization_id,
        validation=validation,
        cleanup_actions=cleanup_actions,
        skill_safety_checkpoint=skill_safety_checkpoint,
    )
    selected_ids = [str(item) for item in cleanup_review.get("selected_action_ids") or []]
    applied_ids = [str(item) for item in cleanup_apply.get("applied_action_ids") or []]
    exact_selected_apply = {
        "complete": True,
        "applicable": bool(selected_ids),
        "selected_action_ids": selected_ids,
        "applied_action_ids": applied_ids,
        "missing_selected_action_ids": sorted(set(selected_ids) - set(applied_ids)),
        "unexpected_applied_action_ids": sorted(set(applied_ids) - set(selected_ids)),
        "exact": len(selected_ids) == len(set(selected_ids)) and set(selected_ids) == set(applied_ids),
    }
    post_apply_checkpoint = {
        "complete": not bool(selected_ids) or bool(post_apply_check and post_apply_validation),
        "applicable": bool(selected_ids),
        "ok": (not bool(selected_ids)) or bool(post_apply_check.get("ok")) and bool(post_apply_validation.get("ok")),
        "changed_files": [str(item) for item in post_apply_check.get("changed_files") or []],
        "errors": [
            *[str(item) for item in post_apply_check.get("auto_merge_blockers") or []],
            *[str(item) for item in (post_apply_validation.get("errors") or [])],
        ],
    }
    merge_readiness = _merge_readiness(
        changed_files=[str(item) for item in post_apply_check.get("changed_files") or []],
        post_apply_check=post_apply_check,
        exact_selected_apply=exact_selected_apply,
        skill_safety_checkpoint=skill_safety_checkpoint,
    )

    return {
        "ok": (
            bool(organization_check.get("ok"))
            and bool(skill_safety_checkpoint["passed"])
            and bool(card_decision_checkpoint["complete"])
            and bool(merge_split_checkpoint["complete"])
            and bool(card_surface_checkpoint["complete"])
            and bool(candidate_intake_checkpoint["complete"])
            and bool(content_hash_checkpoint["complete"])
            and bool(skill_bundle_version_checkpoint["complete"])
            and bool(post_apply_checkpoint["complete"])
        ),
        "maintenance_model": cleanup_proposal.get("maintenance_model") or {},
        "validation": validation,
        "layout_policy": _report_layout_policy(validation),
        "organization_check": {
            "ok": bool(organization_check.get("ok")),
            "error_count": len(organization_check.get("errors") or []),
            "warning_count": len(organization_check.get("warnings") or []),
            "auto_merge_eligible": bool(organization_check.get("auto_merge_eligible")),
            "auto_merge_blockers": organization_check.get("auto_merge_blockers") or [],
        },
        "cleanup": {
            "proposal": cleanup_proposal,
            "duplicate_content_hash_count": len(duplicate_content_hashes),
            "duplicate_content_hashes": duplicate_content_hashes,
            "proposal_action_count": len(cleanup_actions),
            "proposal_counts": cleanup_proposal.get("counts") or {},
            "trusted_card_action_count": len(trusted_cleanup_actions),
            "exchange_surface_action_count": len(trusted_cleanup_actions),
            "exchange_surface_maintenance": "in-scope-like-local-sleep",
            "trusted_card_maintenance": "in-scope-like-local-sleep",
            "similar_card_merge_apply": "planned",
            "weak_card_rejection_apply": "planned",
            "candidate_delete_apply": "planned",
            "skill_bundle_cleanup_apply": "partial",
            "card_surface_checkpoint": card_surface_checkpoint,
            "candidate_intake_checkpoint": candidate_intake_checkpoint,
            "content_hash_checkpoint": content_hash_checkpoint,
            "merge_split_checkpoint": merge_split_checkpoint,
            "merge_checkpoint": merge_checkpoint,
            "split_checkpoint": split_checkpoint,
            "card_decision_checkpoint": card_decision_checkpoint,
            "skill_safety_checkpoint": skill_safety_checkpoint,
            "skill_bundle_version_checkpoint": skill_bundle_version_checkpoint,
            "exact_selected_apply": exact_selected_apply,
            "decision_apply_checkpoint": exact_selected_apply,
            "github_merge_readiness": merge_readiness,
            "review": cleanup_review,
            "apply": cleanup_apply,
            "post_apply_check": post_apply_check,
            "post_apply_validation": post_apply_validation,
            "post_apply_checkpoint": post_apply_checkpoint,
            "checkpoints": {
                "card_surface": card_surface_checkpoint,
                "candidate_intake": candidate_intake_checkpoint,
                "content_hash": content_hash_checkpoint,
                "merge": merge_checkpoint,
                "split": split_checkpoint,
                "card_decisions": card_decision_checkpoint,
                "skill_safety": skill_safety_checkpoint,
                "skill_bundle_version": skill_bundle_version_checkpoint,
                "decision_apply": exact_selected_apply,
                "post_apply": post_apply_checkpoint,
                "github_merge_readiness": merge_readiness,
            },
        },
        "organization_id": organization_id,
        "entry_count": len(entries),
        "main_count": validation.get("main_count", 0),
        "main_active_count": validation.get("main_active_count", 0),
        "main_status_counts": validation.get("main_status_counts") or {},
        "imports_count": validation.get("imports_count", 0),
        "imports_status_counts": validation.get("imports_status_counts") or {},
        "trusted_count": validation.get("trusted_count", 0),
        "candidate_count": validation.get("candidate_count", 0),
        "skill_count": validation.get("skill_count", 0),
        "outbox_count": outbox_count,
        "organization_review_skill": review_skill,
        "recommendations": recommendations,
    }
