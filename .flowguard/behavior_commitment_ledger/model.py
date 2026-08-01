"""Thin loader for the canonical Chaos Brain behavior commitment ledger."""

from __future__ import annotations

import json
from pathlib import Path

from flowguard import BehaviorCommitmentLedger, load_behavior_commitment_ledger, write_behavior_commitment_ledger


LEDGER_PATH = Path(__file__).with_name("ledger.json")
CURRENT_REVISION = "logicguard-org-windows-rollback-path-20260731"


def _surface(
    surface_id: str,
    *,
    source_ref: str,
    owner: str,
    commitment_id: str,
    business_intent_id: str,
    rationale: str,
    validation_boundary: str,
    surface_kind: str = "process",
) -> dict[str, object]:
    return {
        "surface_id": surface_id,
        "surface_kind": surface_kind,
        "source_ref": source_ref,
        "freshness_state": "current",
        "in_scope": True,
        "owner": owner,
        "commitment_ids": [commitment_id],
        "business_intent_ids": [business_intent_id],
        "source_authority_role": "normative",
        "coverage_disposition": "modeled",
        "rationale": rationale,
        "validation_boundary": validation_boundary,
    }


def _apply_current_logicguard_upgrade(payload: dict[str, object]) -> dict[str, object]:
    """Directly replace the stale adoption/four-task BCL projection."""

    commitments = {
        str(item.get("commitment_id") or ""): item
        for item in payload.get("commitments", [])
        if isinstance(item, dict)
    }

    retrieval = commitments["commitment:kb-retrieval-current-index"]
    retrieval.update(
        {
            "label": "Rank current local and organization knowledge in one source-qualified retrieval",
            "expected_result": (
                "one globally ranked result list and one receipt bind exact local "
                "or foreign result references; foreign context remains read-only, "
                "and foreground retrieval never replays lifecycle history"
            ),
            "expected_terminal": "combined_ranked_results_or_no_card",
            "failure_boundary": (
                "missing current local authority or foreign snapshot, local-first "
                "truncation, task-time network fetch, or ambiguous result identity "
                "fails visibly; missing or stale compact foreign calibration blocks "
                "foreign results without a replay fallback"
            ),
            "primary_owner_model_id": "khaos_brain_logicguard_system",
            "supporting_model_ids": [
                "khaos_brain_logicguard_runtime_model_miss",
                "khaos_brain_two_maintenance_cycle_flow",
            ],
            "source_surface_ids": [
                "surface:retrieval-api",
                "surface:retrieval-cli",
                "surface:retrieval-spec",
                "surface:organization-snapshot-retrieval",
                "surface:retrieval-interactions",
                "surface:foreign-calibration-projection",
            ],
            "state_writes": [
                "combined retrieval receipt",
                "viewed/selected/used/outcome evidence",
            ],
            "excluded_behavior_ids": [
                "filtered-scan-on-index-failure",
                "unindexed-card-scan-before-current-standard",
                "local-first-result-truncation",
                "task-time-organization-fetch",
                "view-counted-as-use",
                "foreign-card-adoption-or-skill-install",
                "foreground-full-lifecycle-replay",
            ],
        }
    )

    writer = commitments["commitment:lifecycle-writer-exclusive-current-owner"]
    writer.update(
        {
            "label": "Serialize overlapping durable mutation through one global delegated writer",
            "expected_result": (
                "local and organization tasks keep independent leases while every "
                "overlapping durable write has exactly one global owner or exact child delegation"
            ),
            "failure_boundary": (
                "dual ownership, partial delegation identity, leaked token, live-owner "
                "steal, or cleanup-unconfirmed recovery blocks mutation visibly"
            ),
            "primary_owner_model_id": "khaos_brain_logicguard_system",
            "supporting_model_ids": ["khaos_brain_two_maintenance_cycle_flow"],
            "source_surface_ids": [
                "surface:lifecycle-writer-lock",
                "surface:active-index-lifecycle-lock",
                "surface:lifecycle-writer-lock-spec",
                "surface:global-maintenance-writer",
            ],
            "state_writes": [
                "lifecycle/model/index authority",
                "organization source/snapshot authority",
                "global writer/delegation lease state",
            ],
        }
    )

    manual_update = commitments[
        "commitment:manual-conversation-authorized-update"
    ]
    manual_update["side_effects"] = [
        (
            "restore both scheduled composite automations after closure"
            if str(item) == "restore four surviving automations after closure"
            else item
        )
        for item in manual_update.get("side_effects", [])
    ]

    retired_update = commitments[
        "commitment:installer-keeps-system-update-automation-absent"
    ]
    retired_update.update(
        {
            "expected_result": (
                "fresh install, upgrade, repair, and repeat install retain two "
                "scheduled composite automations, keep both child Skills and "
                "the explicit-user-only updater, and keep the exact old task absent"
            ),
            "expected_terminal": (
                "exact_retired_task_absent_and_two_scheduled_owners_preserved"
            ),
            "side_effects": [
                "remove exact managed automation directory",
                "preserve both scheduled-owner states",
                "install composite-child and explicit-user-only Skills",
            ],
        }
    )
    retired_update["lookup_binding"]["task_terms"] = [
        "retire system update automation",
        "two scheduled composite automations",
        "repeat install",
        "explicit-user-only update skill",
    ]

    organization = commitments["commitment:organization-current-layout"]
    organization.update(
        {
            "label": "Upgrade, maintain, and snapshot one current organization card contract",
            "expected_result": (
                "schema-2 catalog, exact card-bound LogicGuard bundles, reversible "
                "maintenance decisions, and one complete content-addressed foreign snapshot"
            ),
            "expected_terminal": "current_source_and_snapshot_or_explicit_blocker",
            "failure_boundary": (
                "old runtime reader, incomplete identity coverage, unsupported upgrade "
                "item, incomplete Windows rollback copy, irreversible merge/split, or partial "
                "pointer activation remains blocked"
            ),
            "primary_owner_model_id": "khaos_brain_logicguard_system",
            "supporting_model_ids": ["khaos_brain_two_maintenance_cycle_flow"],
            "source_surface_ids": [
                "surface:organization-connect",
                "surface:organization-validation",
                "surface:organization-maintenance",
                "surface:organization-runtime-reader",
                "surface:organization-outbox-dedupe",
                "surface:organization-github-check",
                "surface:organization-decision-identity",
                "surface:organization-source-contract",
                "surface:organization-snapshot",
                "surface:organization-merge-split-packets",
                "surface:organization-migration-rollback",
            ],
            "excluded_behavior_ids": [
                "legacy-trusted-candidates-runtime-reader",
                "legacy-layout-download-path",
                "task-time-lazy-download",
                "local-adopted-card-copy",
                "card-triggered-skill-install",
                "equal-card-count-coverage-substitution",
                "irreversible-similarity-only-merge",
            ],
        }
    )
    organization["lookup_binding"]["path_patterns"] = [
        "local_kb/org_source_contract.py",
        "local_kb/org_migration.py",
        "local_kb/org_sources.py",
        "local_kb/org_snapshot.py",
        "local_kb/org_cleanup.py",
        "local_kb/org_maintenance.py",
        "local_kb/org_cycle.py",
        "local_kb/org_outbox.py",
        "templates/github/org_kb_check.py",
    ]

    automation = commitments[
        "commitment:automation-proof-bound-depth-terminal"
    ]
    automation.update(
        {
            "label": "Close two scheduled owners from exact receipt-v3 terminal evidence",
            "expected_result": (
                "five maintained Skills are classified as two scheduled owners, two "
                "composite children, and one explicit-user-only updater; each scheduled "
                "owner writes one identity-bound immutable receipt-v3 terminal"
            ),
            "failure_boundary": (
                "stale or partial child evidence, run-id-only reuse, cross-task not_run, "
                "cleanup-unconfirmed timeout, child/outer receipt inversion, or planning-only "
                "test evidence blocks completion"
            ),
            "primary_owner_model_id": "khaos_brain_logicguard_system",
            "supporting_model_ids": ["khaos_brain_two_maintenance_cycle_flow"],
            "source_surface_ids": [
                "surface:automation-native-evidence",
                "surface:automation-depth-projection",
                "surface:automation-contract-generation",
                "surface:automation-terminal-builder",
                "surface:automation-frozen-supervision-session",
                "surface:local-cycle-receipt-v3",
                "surface:organization-cycle-receipt-v3",
                "surface:automation-receipt-layering",
            ],
        }
    )

    upgrade = commitments["commitment:upgrade-direct-canonicalization"]
    upgrade["preconditions"] = [
        "both retained scheduled automations are transaction-paused"
    ]

    replaced_surface_ids = {
        "surface:organization-adoption",
        "surface:organization-snapshot-retrieval",
        "surface:retrieval-interactions",
        "surface:foreign-calibration-projection",
        "surface:global-maintenance-writer",
        "surface:organization-source-contract",
        "surface:organization-snapshot",
        "surface:organization-merge-split-packets",
        "surface:organization-migration-rollback",
        "surface:local-cycle-receipt-v3",
        "surface:organization-cycle-receipt-v3",
        "surface:automation-receipt-layering",
    }
    surfaces = [
        item
        for item in payload.get("source_surfaces", [])
        if isinstance(item, dict)
        and item.get("surface_id") not in replaced_surface_ids
    ]
    for item in surfaces:
        if item.get("surface_id") == "surface:update-automation-retirement":
            item["rationale"] = (
                "Installer-owned exact retirement, two-scheduled-owner state "
                "preservation, two child Skills, and manual-skill retention."
            )
    surfaces.extend(
        [
            _surface(
                "surface:organization-snapshot-retrieval",
                source_ref="local_kb/search.py#search_with_receipt",
                owner="Unified retrieval owner",
                commitment_id="commitment:kb-retrieval-current-index",
                business_intent_id="intent:serve-predictive-retrieval",
                rationale="One ranking consumes the already cached foreign snapshot without task-time networking.",
                validation_boundary="multi-source global-ranking, no-network, and exact result-ref tests",
                surface_kind="api",
            ),
            _surface(
                "surface:retrieval-interactions",
                source_ref="local_kb/lifecycle.py#record_retrieval_interaction",
                owner="Retrieval evidence owner",
                commitment_id="commitment:kb-retrieval-current-index",
                business_intent_id="intent:serve-predictive-retrieval",
                rationale="Viewed, selected, used, and outcome evidence retain exact source-qualified result identity.",
                validation_boundary="interaction ordering, UI detail-view, and foreign calibration tests",
                surface_kind="api",
            ),
            _surface(
                "surface:foreign-calibration-projection",
                source_ref="local_kb/lifecycle.py#load_current_foreign_calibration",
                owner="Foreign calibration projection owner",
                commitment_id="commitment:kb-retrieval-current-index",
                business_intent_id="intent:serve-predictive-retrieval",
                rationale=(
                    "Foreground organization retrieval reads one current compact "
                    "projection; Sleep/upgrade alone repairs it from lifecycle history."
                ),
                validation_boundary=(
                    "local zero-read, organization no-replay, stale-projection, and "
                    "P95 retrieval tests"
                ),
                surface_kind="api",
            ),
            _surface(
                "surface:global-maintenance-writer",
                source_ref="local_kb/maintenance_lanes.py#acquire_global_write_lease",
                owner="Global maintenance writer protocol",
                commitment_id="commitment:lifecycle-writer-exclusive-current-owner",
                business_intent_id="intent:serialize-lifecycle-mutation",
                rationale="Independent tasks serialize only overlapping durable writes and delegate exact child identity.",
                validation_boundary="concurrent writer, delegation, expiry, cleanup, and cycle integration tests",
                surface_kind="api",
            ),
            _surface(
                "surface:organization-source-contract",
                source_ref="local_kb/org_source_contract.py",
                owner="Organization current-source owner",
                commitment_id="commitment:organization-current-layout",
                business_intent_id="intent:consume-organization-knowledge",
                rationale="Schema-2 catalog and exact card-bound LogicGuard bundles are the sole runtime source contract.",
                validation_boundary="direct upgrade, catalog identity, bundle, residual, and rollback tests",
                surface_kind="api",
            ),
            _surface(
                "surface:organization-migration-rollback",
                source_ref="local_kb/org_migration.py#_native_filesystem_path",
                owner="Organization direct-source upgrade owner",
                commitment_id="commitment:organization-current-layout",
                business_intent_id="intent:consume-organization-knowledge",
                rationale=(
                    "The existing rollback tree and receipt identity remain unchanged while "
                    "Windows file operations address complete paths beyond 260 characters."
                ),
                validation_boundary=(
                    "below-limit source, above-limit backup target, complete copy, and rollback tests"
                ),
                surface_kind="api",
            ),
            _surface(
                "surface:organization-snapshot",
                source_ref="local_kb/org_snapshot.py#stage_organization_snapshot",
                owner="Organization snapshot publisher",
                commitment_id="commitment:organization-current-layout",
                business_intent_id="intent:consume-organization-knowledge",
                rationale="A complete content-addressed generation is validated before atomic pointer replacement.",
                validation_boundary="snapshot content, reuse, pointer conflict, and previous-generation preservation tests",
                surface_kind="api",
            ),
            _surface(
                "surface:organization-merge-split-packets",
                source_ref="local_kb/org_maintenance.py#build_organization_maintenance_report",
                owner="Organization maintenance decision owner",
                commitment_id="commitment:organization-current-layout",
                business_intent_id="intent:consume-organization-knowledge",
                rationale="Every merge/split has an exact reversible apply packet or concrete reopen contract.",
                validation_boundary="decision-id, apply-packet, reopen, rollback, and exact selected-id tests",
            ),
            _surface(
                "surface:local-cycle-receipt-v3",
                source_ref="local_kb/local_cycle.py#run_local_maintenance_cycle",
                owner="Local scheduled task",
                commitment_id="commitment:automation-proof-bound-depth-terminal",
                business_intent_id="intent:prove-complete-scheduled-automation",
                rationale="One Sleep-then-Dream task preserves strict status and exact terminal receipt identity.",
                validation_boundary="local phase matrix, tamper, reuse, task-independence, and native receipt tests",
            ),
            _surface(
                "surface:organization-cycle-receipt-v3",
                source_ref="local_kb/org_cycle.py#run_organization_cycle",
                owner="Organization scheduled task",
                commitment_id="commitment:automation-proof-bound-depth-terminal",
                business_intent_id="intent:prove-complete-scheduled-automation",
                rationale="One organization task binds maintenance, contribution, and snapshot child evidence.",
                validation_boundary="organization phase matrix, tamper, reuse, task-independence, and native receipt tests",
            ),
            _surface(
                "surface:automation-receipt-layering",
                source_ref="local_kb/automation_runtime.py#_real_artifact_issues",
                owner="Automation receipt validator",
                commitment_id="commitment:automation-proof-bound-depth-terminal",
                business_intent_id="intent:prove-complete-scheduled-automation",
                rationale=(
                    "The immutable Sleep child remains exact while the outer local-cycle payload "
                    "may add later Dream, writer, reuse, timeout, and orchestration evidence."
                ),
                validation_boundary=(
                    "child-field equality, outer strict-superset acceptance, and native receipt tests"
                ),
                surface_kind="api",
            ),
        ]
    )
    payload["source_surfaces"] = surfaces
    payload["current_revision"] = CURRENT_REVISION
    payload["expected_source_surface_ids"] = [
        str(item.get("surface_id") or "") for item in surfaces
    ]
    payload["rationale"] = (
        "Register the sole current LogicGuard, organization-snapshot, unified "
        "retrieval, and two-scheduled-owner success paths."
    )
    return payload


def build_ledger() -> BehaviorCommitmentLedger:
    """Load the sole current JSON authority without executing a duplicate inventory."""
    try:
        ledger = load_behavior_commitment_ledger(LEDGER_PATH)
        needs_source_upgrade = any(
            str(surface.surface_kind) == "openspec"
            for surface in ledger.source_surfaces
        ) or not ledger.expected_source_surface_ids
        payload = ledger.to_dict()
        payload["expected_source_surface_ids"] = [
            str(surface.get("surface_id") or "")
            for surface in payload.get("source_surfaces") or []
            if str(surface.get("surface_id") or "")
        ]
        for surface in payload.get("source_surfaces") or []:
            if isinstance(surface, dict) and surface.get("surface_kind") == "openspec":
                surface["surface_kind"] = "doc"
        migrated = BehaviorCommitmentLedger(
            **_apply_current_logicguard_upgrade(payload)
        )
        if needs_source_upgrade or migrated != ledger:
            write_behavior_commitment_ledger(LEDGER_PATH, migrated)
        return migrated
    except ValueError as exc:
        # One-time author-side direct migration for the FlowGuard package's
        # current source-surface fields.  This is not a product-runtime
        # compatibility reader: the official writer replaces the source file
        # and every later consumer reads only the current canonical shape.
        raw = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
        payload = dict(raw.get("ledger") or {})
        payload.setdefault("subject_lane", "normative_target")
        payload.setdefault("expected_source_surface_ids", [])
        payload.setdefault("source_inventory_revision", "")
        payload.setdefault("source_inventory_fingerprint", "")
        payload.setdefault("source_inventory_evidence_ids", [])
        payload.setdefault("require_complete_source_inventory", False)
        for surface in payload.get("source_surfaces") or []:
            if not isinstance(surface, dict):
                continue
            surface.setdefault("source_system_id", "")
            surface.setdefault("native_artifact_id", "")
            surface.setdefault("content_fingerprint", "")
            surface.setdefault("inventory_revision", "")
            surface.setdefault("discovery_evidence_ids", [])
            surface.setdefault("source_authority_role", "normative")
            surface.setdefault("declared_semantics_fingerprint", "")
            surface.setdefault("coverage_disposition", "modeled")
            surface.setdefault("delegated_owner_inventory_id", "")
            surface.setdefault("delegation_relation_type", "")
            surface.setdefault("native_evidence_ids", [])
        migrated = BehaviorCommitmentLedger(
            **_apply_current_logicguard_upgrade(payload)
        )
        write_behavior_commitment_ledger(LEDGER_PATH, migrated)
        return migrated
