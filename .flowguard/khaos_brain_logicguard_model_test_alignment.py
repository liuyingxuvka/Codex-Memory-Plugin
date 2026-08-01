"""Frozen Model-Test Alignment plan for LogicGuard-native Khaos Brain.

This is a planning artifact, not passing test evidence.  It proves that every
OpenSpec obligation has exactly one planned external code owner and one named
test-evidence slot.  All evidence is intentionally ``not_run`` until the
implementation exists and the frozen final execution owner runs it.
"""

from __future__ import annotations

import json
from dataclasses import replace

from flowguard.model_test_alignment import (
    CodeContract,
    ModelObligation,
    ModelTestAlignmentPlan,
    TestEvidence,
    review_model_test_alignment,
)


MODEL_ID = "khaos_brain_logicguard_authority_cutover"

# obligation id, code-contract id, path, symbol, primary test path
BINDINGS = (
    ("req.authority.exact-projection", "contract.projection.validate-exact-binding", "local_kb/model_projection.py", "validate_card_projection", "tests/test_khaos_model_projection.py"),
    ("req.authority.argument-block", "contract.models.build-argument-block", "local_kb/logicguard_models.py", "build_predictive_argument_model", "tests/test_khaos_logicguard_models.py"),
    ("req.authority.projection-only", "contract.projection.project-card", "local_kb/model_projection.py", "project_card", "tests/test_khaos_model_projection.py"),
    ("req.authority.atomic-publication", "contract.lifecycle.publish-complete-generation", "local_kb/lifecycle.py", "run_incremental_sleep", "tests/test_khaos_sleep_model_maintenance.py"),
    ("req.authority.privacy", "contract.models.validate-scope", "local_kb/logicguard_models.py", "normalize_authority_scope", "tests/test_khaos_logicguard_models.py"),
    ("req.card.foreground-observation-only", "contract.foreground.feedback-history-only", "local_kb/lifecycle.py", "record_observation_result", "tests/test_kb_preflight_entry_compat.py"),
    ("req.maintenance.sleep-owner", "contract.lifecycle.sleep-owner", "local_kb/lifecycle.py", "run_incremental_sleep", "tests/test_khaos_sleep_model_maintenance.py"),
    ("req.maintenance.lifecycle-batch", "contract.lifecycle.bounded-candidate-batch", "local_kb/lifecycle.py", "_run_incremental_sleep_locked", "tests/test_kb_lifecycle.py"),
    ("req.maintenance.raw-candidate-upgrade", "contract.lifecycle.raw-candidate-upgrade", "local_kb/lifecycle.py", "_run_incremental_sleep_locked", "tests/test_kb_lifecycle_sleep_batch_integration.py"),
    ("req.maintenance.mesh-consolidation", "contract.maintenance.publish-model-generation", "local_kb/model_maintenance.py", "publish_sleep_model_generation", "tests/test_khaos_sleep_model_maintenance.py"),
    ("req.maintenance.gap-review", "contract.maintenance.summarize-model-gaps", "local_kb/model_maintenance.py", "_gap_summary", "tests/test_khaos_sleep_model_maintenance.py"),
    ("req.maintenance.dream-read-only", "contract.dream.run-read-only", "local_kb/dream.py", "run_dream_maintenance", "tests/test_kb_dream.py"),
    ("req.maintenance.dream-convergence", "contract.dream.fingerprint-experiment", "local_kb/dream.py", "_evidence_fingerprint", "tests/test_kb_dream.py"),
    ("req.maintenance.dream-bounded-artifact", "contract.dream.bound-opportunity-projection", "local_kb/dream.py", "_bounded_opportunity_projection", "tests/test_kb_dream.py"),
    ("req.maintenance.local-cycle-timeout-budget", "contract.automation.local-cycle-timeout-tree", "local_kb/automation_contracts.py", "native_timeout_seconds", "tests/test_kb_automation_native_receipts.py"),
    ("req.retrieval.current-index", "contract.search.unified-current-sources", "local_kb/search.py", "search_with_receipt", "tests/test_multi_source_search.py"),
    ("req.retrieval.publisher-authority", "contract.index.explicit-publisher", "local_kb/active_index.py", "rebuild_active_index", "tests/test_kb_retrieval_calibration.py"),
    ("req.retrieval.neighborhood", "contract.models.materialize-neighborhood", "local_kb/logicguard_models.py", "materialize_bound_neighborhood", "tests/test_khaos_model_native_retrieval.py"),
    ("req.retrieval.ranking", "contract.search.rank-entry-then-grounded-neighborhood", "local_kb/search.py", "search_model_bound_entries", "tests/test_khaos_model_native_retrieval.py"),
    ("req.retrieval.desktop", "contract.desktop.render-exact-model-detail", "local_kb/ui_data.py", "build_card_detail_payload", "tests/test_kb_desktop_ui.py"),
    ("req.retrieval.performance", "contract.readiness.measure-model-retrieval", "scripts/check_khaos_logicguard_runtime.py", "build_report", "tests/test_khaos_model_runtime_readiness.py"),
    ("req.migration.only-legacy-reader", "contract.migration.consume-legacy-direct", "local_kb/maintenance_migration.py", "plan_logicguard_native_migration", "tests/test_khaos_logicguard_migration.py"),
    ("req.migration.complete-conservative", "contract.migration.map-every-card", "local_kb/maintenance_migration.py", "migrate_legacy_card_generation", "tests/test_khaos_logicguard_migration.py"),
    ("req.migration.transactional", "contract.migration.cutover-or-rollback", "local_kb/maintenance_migration.py", "commit_logicguard_native_generation", "tests/test_khaos_logicguard_migration.py"),
    ("req.migration.install", "contract.installer.require-model-authority", "scripts/install_codex_kb.py", "main", "tests/test_codex_install.py"),
    ("req.assurance.flowguard", "contract.flowguard.authority-cutover-model", ".flowguard/khaos_brain_logicguard_authority_cutover.py", "main", "tests/test_khaos_logicguard_assurance.py"),
    ("req.assurance.alignment", "contract.flowguard.model-test-alignment", ".flowguard/khaos_brain_logicguard_model_test_alignment.py", "main", "tests/test_khaos_logicguard_assurance.py"),
    ("req.assurance.execution-owner", "contract.readiness.single-final-owner", "scripts/check_khaos_logicguard_native_readiness.py", "main", "tests/test_khaos_logicguard_readiness.py"),
    ("req.assurance.surface-parity", "contract.readiness.surface-parity", "scripts/check_kb_skillguard.py", "main", "tests/test_kb_automation_skillguard.py"),
    ("req.assurance.release-gates", "contract.readiness.release-gates", "scripts/check_khaos_logicguard_native_readiness.py", "build_report", "tests/test_khaos_logicguard_readiness.py"),
    ("req.organization.snapshot-bundle", "contract.organization.stage-complete-logicguard-snapshot", "local_kb/org_snapshot.py", "stage_organization_snapshot", "tests/test_org_snapshot.py"),
    ("req.organization.legacy-upgrade", "contract.organization.upgrade-legacy-card", "local_kb/org_migration.py", "migrate_organization_repo_to_current", "tests/test_org_sources.py"),
    ("req.organization.foreign-reader", "contract.organization.read-foreign-bundle", "local_kb/logicguard_models.py", "read_foreign_argument_context", "tests/test_multi_source_search.py"),
    ("req.organization.snapshot-retrieval", "contract.organization.snapshot-only-retrieval", "local_kb/search.py", "search_multi_source_result", "tests/test_multi_source_search.py"),
    ("req.organization.interaction", "contract.organization.record-source-qualified-interaction", "local_kb/lifecycle.py", "record_retrieval_interaction", "tests/test_multi_source_search.py"),
    ("req.organization.feedback-token", "contract.organization.resolve-pinned-feedback", "local_kb/lifecycle.py", "record_outcome_receipt", "tests/test_kb_retrieval_calibration.py"),
    ("req.organization.sleep-calibration", "contract.organization.plan-local-foreign-calibration", "local_kb/calibration.py", "plan_foreign_calibration", "tests/test_kb_retrieval_calibration.py"),
    ("req.organization.current-source", "contract.organization.schema2-catalog-bundles", "local_kb/org_source_contract.py", "materialize_current_source", "tests/test_org_sources.py"),
    ("req.organization.remote-gate-parity", "contract.organization.remote-schema2-portable-checker", "templates/github/org_kb_check.py", "check_manifest", "tests/test_org_github_automation.py"),
    ("req.organization.automatic-review-policy", "contract.organization.pr-checks-zero-human-review", "local_kb/github_repo_config.py", "build_branch_protection_payload", "tests/test_github_repo_config.py"),
    ("req.organization.merge-split", "contract.organization.reversible-apply-or-reopen", "local_kb/org_cleanup.py", "apply_organization_cleanup_proposal", "tests/test_org_maintenance.py"),
    ("req.organization.nonoverlap-packet-selection", "contract.organization.select-nonoverlap-packets", "local_kb/org_maintenance.py", "build_organization_cleanup_review", "tests/test_org_maintenance.py"),
    ("req.organization.materialized-change-inventory", "contract.organization.pre-post-path-union", "local_kb/org_cleanup.py", "apply_organization_cleanup_proposal", "tests/test_org_automation.py"),
    ("req.organization.ui-detail", "contract.organization.render-foreign-detail", "local_kb/ui_data.py", "build_card_detail_payload", "tests/test_e2e_multi_source_browsing.py"),
    ("req.organization.cli-surface", "contract.organization.cli-snapshot-source", ".agents/skills/local-kb-retrieve/scripts/kb_search.py", "main", "tests/test_cli_output_contract.py"),
    ("req.organization.default-source-status", "contract.organization.default-source-status-envelope", "local_kb/search.py", "render_search_envelope", "tests/test_kb_preflight_entry_compat.py"),
    ("req.organization.snapshot-schema-cutover", "contract.organization.snapshot-v3-only-runtime", "local_kb/org_snapshot.py", "load_current_organization_snapshot", "tests/test_org_snapshot.py"),
    ("req.maintenance.local-cycle", "contract.cycle.local-sleep-dream-receipt", "local_kb/local_cycle.py", "run_local_maintenance_cycle", "tests/test_local_maintenance_cycle.py"),
    ("req.maintenance.organization-cycle", "contract.cycle.organization-pinned-sync", "local_kb/org_cycle.py", "run_organization_cycle", "tests/test_organization_cycle.py"),
    ("req.maintenance.global-writer", "contract.cycle.single-global-delegated-writer", "local_kb/maintenance_lanes.py", "acquire_global_write_lease", "tests/test_maintenance_lanes.py"),
    ("req.maintenance.receipt-v3", "contract.cycle.identity-bound-terminal-receipt", "local_kb/maintenance_lanes.py", "validate_cycle_receipt_v3", "tests/test_local_maintenance_cycle.py"),
    ("req.assurance.execution-classification", "contract.install.five-two-two-one", "local_kb/operator_activation.py", "_expected_skill_inventory", "tests/test_kb_operator_activation.py"),
)

KNOWN_BAD_TARGET_IDS = (
    "bad.standalone-yaml-authority",
    "bad.projection-before-model",
    "bad.index-before-projection",
    "bad.partial-migration-current",
    "bad.unowned-model-writer",
    "bad.duplicate-sleep-owner",
    "bad.duplicate-search-owner",
    "bad.dream-canonical-mutation",
    "bad.dream-handoff-without-simulation",
    "bad.flat-yaml-fallback",
    "bad.floating-head-substitution",
    "bad.projection-digest-mismatch",
    "bad.private-cross-scope-edge",
    "bad.retrieval-without-neighborhood",
    "bad.performance-small-fixture-overclaim",
    "bad.per-candidate-full-lifecycle-replay",
    "bad.unauthorized-active-index-publisher",
    "bad.view-counted-as-use",
    "bad.local-block-suppresses-organization",
    "bad.dual-global-writer",
    "bad.invalid-delegated-writer",
    "bad.stale-cycle-receipt-reuse",
    "bad.partial-cycle-result-promotion",
    "bad.irreversible-similarity-only-merge",
    "bad.overlapping-organization-packets-selected",
    "bad.organization-deletion-inventory-omitted",
    "bad.organization-backup-path-limit",
    "bad.default-search-hides-organization-status",
    "bad.retired-organization-snapshot-reader",
    "bad.foreground-direct-candidate-write",
    "bad.sleep-raw-candidate-repair-omitted",
    "bad.dream-unbounded-opportunity-artifact",
    "bad.local-cycle-timeout-underbudgeted",
    "bad.organization-remote-schema1-checker",
    "bad.organization-remote-bundle-rejection",
    "bad.organization-remote-platform-digest",
    "bad.organization-human-approval-required",
    "bad.organization-admin-merge-bypass",
)

EXPECTED_PLANNING_GAP_CODES = {
    "test_evidence_not_passing",
    "missing_test_evidence",
    "missing_code_contract_test_evidence",
    "missing_required_test_kind",
}


def _description(obligation_id: str) -> str:
    return "Frozen implementation and verification obligation imported from the LogicGuard-native Khaos Brain OpenSpec contract: " + obligation_id


def build_plan() -> ModelTestAlignmentPlan:
    obligations = tuple(
        ModelObligation(
            obligation_id=obligation_id,
            obligation_type="external_contract",
            description=_description(obligation_id),
            required=True,
            required_test_kinds=(
                ("happy_path", "same_class")
                if obligation_id in {
                    "req.retrieval.performance",
                    "req.maintenance.lifecycle-batch",
                    "req.maintenance.raw-candidate-upgrade",
                    "req.maintenance.dream-bounded-artifact",
                    "req.maintenance.local-cycle-timeout-budget",
                    "req.organization.legacy-upgrade",
                    "req.organization.default-source-status",
                    "req.organization.snapshot-schema-cutover",
                    "req.organization.nonoverlap-packet-selection",
                    "req.organization.materialized-change-inventory",
                    "req.card.foreground-observation-only",
                }
                else ("happy_path",)
            ),
            risk_level="high",
            allow_shared_evidence=False,
            allow_shared_implementation=False,
            exact_external_contract=True,
        )
        for obligation_id, _contract_id, _path, _symbol, _test_path in BINDINGS
    )
    contracts = tuple(
        CodeContract(
            code_contract_id=contract_id,
            path=path,
            symbol=symbol,
            surface_type="function",
            role="owner",
            implements_obligations=(obligation_id,),
            required=True,
        )
        for obligation_id, contract_id, path, symbol, _test_path in BINDINGS
    )
    evidence = tuple(
        TestEvidence(
            evidence_id=f"evidence.planned.{obligation_id}",
            test_name=f"planned::{obligation_id}",
            path=test_path,
            command=f"python -m pytest -q {test_path}",
            result_status="not_run",
            evidence_current=True,
            test_kind="happy_path",
            covered_obligations=(obligation_id,),
            covered_code_contracts=(contract_id,),
            assertion_scope="external_contract",
            evidence_role="primary",
        )
        for obligation_id, contract_id, _path, _symbol, test_path in BINDINGS
    )
    performance_contract_id = next(
        contract_id
        for obligation_id, contract_id, _path, _symbol, _test_path in BINDINGS
        if obligation_id == "req.retrieval.performance"
    )
    evidence = (*evidence, TestEvidence(
        evidence_id="evidence.planned.req.retrieval.performance.same-class-scale",
        test_name="planned::req.retrieval.performance::same-class-scale",
        path="tests/test_khaos_model_native_retrieval.py",
        command=(
            "python -m pytest -q tests/test_khaos_model_native_retrieval.py "
            "tests/test_khaos_model_runtime_readiness.py"
        ),
        result_status="not_run",
        evidence_current=True,
        test_kind="same_class",
        covered_obligations=("req.retrieval.performance",),
        covered_code_contracts=(performance_contract_id,),
        assertion_scope="external_contract",
        evidence_role="primary",
    ))
    raw_upgrade_contract_id = next(
        contract_id
        for obligation_id, contract_id, _path, _symbol, _test_path in BINDINGS
        if obligation_id == "req.maintenance.raw-candidate-upgrade"
    )
    evidence = (*evidence, TestEvidence(
        evidence_id="evidence.planned.req.maintenance.raw-candidate-upgrade.same-class-boundaries",
        test_name="planned::req.maintenance.raw-candidate-upgrade::same-class-boundaries",
        path="tests/test_khaos_sleep_model_maintenance.py",
        command=(
            "python -m pytest -q tests/test_khaos_sleep_model_maintenance.py "
            "tests/test_kb_lifecycle_sleep_batch_integration.py -k raw_candidate"
        ),
        result_status="not_run",
        evidence_current=True,
        test_kind="same_class",
        covered_obligations=("req.maintenance.raw-candidate-upgrade",),
        covered_code_contracts=(raw_upgrade_contract_id,),
        assertion_scope="external_contract",
        evidence_role="primary",
    ))
    organization_upgrade_contract_id = next(
        contract_id
        for obligation_id, contract_id, _path, _symbol, _test_path in BINDINGS
        if obligation_id == "req.organization.legacy-upgrade"
    )
    evidence = (*evidence, TestEvidence(
        evidence_id="evidence.planned.req.organization.legacy-upgrade.same-class-windows-path",
        test_name="planned::req.organization.legacy-upgrade::same-class-windows-path",
        path="tests/test_org_sources.py",
        command=(
            "python -m pytest -q tests/test_org_sources.py -k "
            "migration_backup_supports_windows_extended_length_card_paths"
        ),
        result_status="not_run",
        evidence_current=True,
        test_kind="same_class",
        covered_obligations=("req.organization.legacy-upgrade",),
        covered_code_contracts=(organization_upgrade_contract_id,),
        assertion_scope="external_contract",
        evidence_role="primary",
    ))
    lifecycle_contract_id = next(
        contract_id
        for obligation_id, contract_id, _path, _symbol, _test_path in BINDINGS
        if obligation_id == "req.maintenance.lifecycle-batch"
    )
    evidence = (*evidence, TestEvidence(
        evidence_id="evidence.planned.req.maintenance.lifecycle-batch.same-class-family",
        test_name="planned::req.maintenance.lifecycle-batch::same-class-family",
        path="tests/test_kb_lifecycle.py",
        command=(
            "python -m pytest -q tests/test_kb_lifecycle.py -k "
            "'candidate_events_commit_in_one_bounded_batch or "
            "candidate_transition_family_retry_is_bounded'"
        ),
        result_status="not_run",
        evidence_current=True,
        test_kind="same_class",
        covered_obligations=("req.maintenance.lifecycle-batch",),
        covered_code_contracts=(lifecycle_contract_id,),
        assertion_scope="external_contract",
        evidence_role="primary",
    ))
    return ModelTestAlignmentPlan(
        model_id=MODEL_ID,
        obligations=obligations,
        code_contracts=contracts,
        test_evidence=evidence,
        require_proof_artifacts=False,
        require_runtime_path_evidence=False,
        require_source_audit=False,
        allow_orphan_tests=False,
        allow_orphan_code_contracts=False,
    )


def build_known_bad_plan() -> ModelTestAlignmentPlan:
    current = build_plan()
    duplicate = CodeContract(
        code_contract_id="contract.parallel-controller.duplicate-sleep-owner",
        path="local_kb/logicguard_controller.py",
        symbol="commit_sleep_model_change",
        surface_type="function",
        role="owner",
        implements_obligations=("req.maintenance.sleep-owner",),
        required=True,
    )
    return replace(current, code_contracts=(*current.code_contracts, duplicate))


def main() -> int:
    current = review_model_test_alignment(build_plan())
    known_bad = review_model_test_alignment(build_known_bad_plan())
    current_codes = {finding.code for finding in current.findings}
    known_bad_codes = {finding.code for finding in known_bad.findings}
    rows_have_one_owner = all(
        len(row.owner_code_contract_ids) == 1 and row.status == "blocked"
        for row in current.binding_rows
    )
    payload = {
        "artifact_type": "khaos_brain_logicguard_native_model_test_alignment_plan",
        "current": current.to_dict(),
        "known_bad": known_bad.to_dict(),
        "obligation_count": len(build_plan().obligations),
        "code_contract_count": len(build_plan().code_contracts),
        "planned_test_evidence_count": len(build_plan().test_evidence),
        "known_bad_target_ids": list(KNOWN_BAD_TARGET_IDS),
        "planning_state": "frozen_not_run",
        "ok": (
            len(current.binding_rows) == len(BINDINGS)
            and rows_have_one_owner
            and current_codes
            and current_codes.issubset(EXPECTED_PLANNING_GAP_CODES)
            and "duplicate_code_contract_owner" in known_bad_codes
        ),
        "claim_boundary": (
            "This artifact freezes one planned code owner and one not-run evidence slot for every required OpenSpec "
            "obligation and rejects a duplicate Sleep code owner. Its blocked alignment status is intentional: no "
            "implementation or test is treated as passing until current external-contract evidence is produced. "
            "The performance obligation requires the generalized large-generation same-class slot, and organization "
            "maintenance separately binds overlapping-packet selection and deletion-aware publication tests."
        ),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
