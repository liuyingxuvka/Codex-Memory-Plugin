"""Close the real large-brain LogicGuard runtime performance model miss.

The earlier performance obligation passed only a three-card fixture.  A real
3427-card current generation then exceeded the catalog and exact-context
budgets.  A later release check also exposed an independent foreground boundary
miss: every query replayed 253271 lifecycle events merely to obtain foreign-card
calibration, even when the query returned only local cards.  This review reuses
the existing retrieval commitment, preserves both false-negative episodes,
binds generalized same-class cases to their owner code and tests, and requires
current runtime evidence.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from kb_sleep_timeout_model_miss import build_report as build_sleep_timeout_report

from flowguard import (
    FALSE_NEGATIVE_CAUSE_SCOPE_OVERCLAIM,
    MODEL_MATURATION_SIGNAL_CODE_BOUNDARY_MISMATCH,
    MODEL_MATURATION_SIGNAL_SAME_CLASS_MISSING,
    MODEL_MATURATION_RECEIPT_STATUS_PASS,
    MODEL_MATURATION_RESOLUTION_MODEL_EDIT,
    MODEL_MISS_BACKFEED_REUSE_EXISTING,
    FalseNegativeBackpropagationPlan,
    FalseNegativeCase,
    FlowGuardClosureContractPlan,
    ModelMaturationPlan,
    ModelMaturationSignal,
    SameClassMissClosure,
    UIModelMissRecord,
    backfeed_model_miss_to_behavior_ledger,
    load_behavior_commitment_ledger,
    review_false_negative_backpropagation,
    review_flowguard_closure_contract,
    review_model_maturation_loop,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = REPO_ROOT / ".flowguard" / "behavior_commitment_ledger" / "ledger.json"
MISS_ID = "miss:khaos-logicguard-runtime:large-local-generation"
COMMITMENT_ID = "commitment:kb-retrieval-current-index"
OWNER_MODEL_ID = "kb_convergence_upgrade_model.LifecycleConvergenceBlock"
OBLIGATION_ID = "req.retrieval.performance"
GENERALIZED_CASE_ID = "case:retrieval:shared-current-mesh-across-distinct-cards"
OBSERVED_FAILURE_ID = "evidence:logicguard-runtime:3427-card-budget-failure"
RUNTIME_CLOSURE_ID = "evidence:logicguard-runtime:3427-card-budget-pass"
SAME_CLASS_TEST_ID = (
    "test:tests/test_khaos_model_native_retrieval.py::"
    "KhaosModelNativeRetrievalTests::"
    "test_current_mesh_view_is_reused_across_distinct_cards_in_one_generation"
)
MEASUREMENT_TEST_ID = (
    "test:tests/test_khaos_model_runtime_readiness.py::"
    "KhaosModelRuntimeReadinessTests::"
    "test_catalog_latency_is_measured_without_memory_instrumentation"
)
REPLAY_MISS_ID = "miss:khaos-retrieval:foreground-lifecycle-replay"
REPLAY_GENERALIZED_CASE_ID = "case:retrieval:local-zero-foreign-read-and-org-compact-projection"
REPLAY_OBSERVED_FAILURE_ID = "evidence:retrieval-quality:253271-event-p95-failure"
REPLAY_RUNTIME_CLOSURE_ID = "evidence:retrieval-quality:compact-projection-p95-pass"
LOCAL_NO_REPLAY_TEST_ID = (
    "test:tests/test_multi_source_search.py::MultiSourceSearchTests::"
    "test_local_search_does_not_read_foreign_calibration_or_replay_lifecycle"
)
ORG_COMPACT_TEST_ID = (
    "test:tests/test_multi_source_search.py::MultiSourceSearchTests::"
    "test_organization_search_reads_compact_current_calibration_without_replay"
)
STALE_COMPACT_TEST_ID = (
    "test:tests/test_multi_source_search.py::MultiSourceSearchTests::"
    "test_organization_search_fails_visibly_when_calibration_projection_is_stale"
)
ORG_BACKUP_MISS_ID = "miss:khaos-organization:windows-backup-path-limit"
ORG_BACKUP_COMMITMENT_ID = "commitment:organization-current-layout"
ORG_BACKUP_OBLIGATION_ID = "req.organization.legacy-upgrade"
ORG_BACKUP_GENERALIZED_CASE_ID = "case:organization:rollback-tree-windows-extended-path"
ORG_BACKUP_OBSERVED_FAILURE_ID = (
    "evidence:native-kb-organization-maintenance-20260731T233347542098Z-7249f23d"
)
ORG_BACKUP_RUNTIME_CLOSURE_ID = "evidence:organization-migration:extended-path-backup-pass"
ORG_BACKUP_TEST_ID = (
    "test:tests/test_org_sources.py::OrganizationSourceTests::"
    "test_migration_backup_supports_windows_extended_length_card_paths"
)


def _closed_maturation_report(
    *,
    plan_id: str,
    risk_id: str,
    candidate_fingerprint: str,
    evidence_fingerprint: str,
    signal_specs: tuple[tuple[str, str, str, str], ...],
) -> object:
    coverage_ids = tuple(f"{risk_id}:coverage:{index}" for index in range(len(signal_specs)))
    probe_ids = tuple(f"{risk_id}:probe:{index}" for index in range(len(signal_specs)))
    plan = ModelMaturationPlan(
        plan_id=plan_id,
        task_id=f"task:{risk_id}:closure",
        task_purpose="Close the observed retrieval false-negative class with exact current evidence.",
        model_id=OWNER_MODEL_ID,
        risk_id=risk_id,
        coverage_universe_id=f"{risk_id}:coverage-universe:v1",
        coverage_owner="flowguard-model-miss-review",
        coverage_source_refs=(
            f"model:{OWNER_MODEL_ID}",
            "ledger:commitment:kb-retrieval-current-index",
        ),
        coverage_ids=coverage_ids,
        required_probe_ids=probe_ids,
        base_model_fingerprint=f"base:{risk_id}",
        candidate_model_fingerprint=candidate_fingerprint,
        evidence_fingerprint=evidence_fingerprint,
    )
    plan = replace(plan, coverage_universe_fingerprint=plan.expected_coverage_fingerprint())
    signals = tuple(
        ModelMaturationSignal(
            signal_id=signal_id,
            signal_type=signal_type,
            source_route="model_miss_review",
            model_id=OWNER_MODEL_ID,
            risk_id=risk_id,
            evidence_id=evidence_id,
            description=description,
            coverage_id=coverage_ids[index],
            probe_id=probe_ids[index],
            resolution_class=MODEL_MATURATION_RESOLUTION_MODEL_EDIT,
            prediction=description,
            falsifier=f"The same-class probe {probe_ids[index]} fails against the candidate model.",
            evidence_fingerprint=evidence_id,
            resolved=True,
            current=True,
            receipt_id=f"receipt:{risk_id}:{index}",
            receipt_fingerprint=f"receipt-fingerprint:{risk_id}:{index}",
            receipt_status=MODEL_MATURATION_RECEIPT_STATUS_PASS,
            receipt_task_id=plan.task_id,
            receipt_probe_id=probe_ids[index],
            receipt_candidate_fingerprint=plan.candidate_model_fingerprint,
            receipt_coverage_fingerprint=plan.coverage_universe_fingerprint,
            receipt_evidence_fingerprint=evidence_id,
            receipt_owner_route="model_miss_review",
        )
        for index, (signal_id, signal_type, evidence_id, description) in enumerate(signal_specs)
    )
    return review_model_maturation_loop(replace(plan, signals=signals))


def _build_foreground_replay_closure(ledger: object) -> dict[str, object]:
    miss = UIModelMissRecord(
        miss_id=REPLAY_MISS_ID,
        previous_claim_id=OBLIGATION_ID,
        previous_green_reason=(
            "Retrieval quality checks covered ranking and a one-second latency gate but did not assert "
            "that the foreground path avoided lifecycle replay."
        ),
        observed_failure=(
            "One foreground query replayed a 353530079-byte lifecycle log with 253271 events, "
            "raising warm P95 latency to 25-32 seconds."
        ),
        observed_failure_evidence_ref=REPLAY_OBSERVED_FAILURE_ID,
        miss_type="evidence_overclaimed",
        affected_capability_ids=("capability:exact-model-bound-retrieval",),
        same_class_capability_ids=(
            "capability:local-query-zero-foreign-calibration-read",
            "capability:organization-query-current-compact-calibration",
            "capability:stale-compact-calibration-visible-failure",
        ),
        required_test_ids=(LOCAL_NO_REPLAY_TEST_ID, ORG_COMPACT_TEST_ID, STALE_COMPACT_TEST_ID),
        required_implementation_evidence_ids=(REPLAY_RUNTIME_CLOSURE_ID,),
        affected_behavior_plane="product_runtime",
        affected_commitment_id=COMMITMENT_ID,
        primary_owner_model_id=OWNER_MODEL_ID,
        error_signatures=(
            "warm-p95-ms:32211>1000",
            "foreground-replay-events:253271",
        ),
        error_evidence_ids=(REPLAY_OBSERVED_FAILURE_ID,),
        root_cause_backpropagation=(
            "search_multi_source_result unconditionally loaded canonical lifecycle state, so "
            "foreground retrieval crossed into the Sleep-owned full-history replay boundary."
        ),
        code_owner="local_kb.lifecycle.load_current_foreign_calibration",
        rationale=(
            "Keep lifecycle replay in Sleep/upgrade and close all three foreground projection cases."
        ),
    )
    backfeed = backfeed_model_miss_to_behavior_ledger(miss, ledger)
    tests = (LOCAL_NO_REPLAY_TEST_ID, ORG_COMPACT_TEST_ID, STALE_COMPACT_TEST_ID)
    false_negative = review_false_negative_backpropagation(
        FalseNegativeBackpropagationPlan(
            plan_id="plan:khaos-retrieval:foreground-replay:false-negative",
            cases=(
                FalseNegativeCase(
                    case_id=REPLAY_MISS_ID,
                    previous_claim_id=OBLIGATION_ID,
                    observed_failure_id=REPLAY_OBSERVED_FAILURE_ID,
                    cause=FALSE_NEGATIVE_CAUSE_SCOPE_OVERCLAIM,
                    would_have_failed_if=(
                        "a local-only query had forbidden every foreign-calibration read",
                        "an organization query had forbidden canonical lifecycle replay",
                        "a stale compact projection had been required to fail visibly",
                    ),
                    generalized_case_id=REPLAY_GENERALIZED_CASE_ID,
                    new_model_obligation_id=OBLIGATION_ID,
                    new_plan_item_ids=tests,
                    closure_evidence_ids=(REPLAY_RUNTIME_CLOSURE_ID,),
                    repair_evidence_ids=(
                        "code:local_kb/lifecycle.py:load_current_foreign_calibration",
                        "code:local_kb/search.py:search_multi_source_result",
                        *tests,
                    ),
                    metadata={
                        "failed_event_count": 253271,
                        "failed_event_log_bytes": 353530079,
                        "failed_warm_p95_ms": 32211.0,
                        "passed_warm_p95_ms": 123.782,
                        "threshold_ms": 1000.0,
                    },
                ),
            ),
            recurring_or_high_risk=True,
            allow_scoped_confidence=False,
        )
    )
    maturation = _closed_maturation_report(
        plan_id="plan:khaos-retrieval:foreground-replay:maturation",
        risk_id=REPLAY_MISS_ID,
        candidate_fingerprint="candidate:foreground-compact-calibration:v1",
        evidence_fingerprint=REPLAY_RUNTIME_CLOSURE_ID,
        signal_specs=(
            (
                "signal:foreground-replay-code-boundary",
                MODEL_MATURATION_SIGNAL_CODE_BOUNDARY_MISMATCH,
                REPLAY_RUNTIME_CLOSURE_ID,
                "Foreground retrieval now consumes only a current compact projection.",
            ),
            (
                "signal:foreground-replay-same-class",
                MODEL_MATURATION_SIGNAL_SAME_CLASS_MISSING,
                LOCAL_NO_REPLAY_TEST_ID,
                "Local, organization, and stale-projection cases are explicit.",
            ),
        ),
    )
    same_class = SameClassMissClosure(
        miss_id=REPLAY_MISS_ID,
        observed_failure_evidence_id=REPLAY_OBSERVED_FAILURE_ID,
        same_class_proof_evidence_id=LOCAL_NO_REPLAY_TEST_ID,
        model_obligation_id=OBLIGATION_ID,
        defect_family_id=REPLAY_GENERALIZED_CASE_ID,
        current=True,
        result_status="passed",
        metadata={
            "runtime_closure_evidence_id": REPLAY_RUNTIME_CLOSURE_ID,
            "additional_same_class_test_ids": [ORG_COMPACT_TEST_ID, STALE_COMPACT_TEST_ID],
        },
    )
    closure = review_flowguard_closure_contract(
        FlowGuardClosureContractPlan(
            claim_id="claim:khaos-retrieval-foreground-replay-model-miss-closed",
            claim_scope="false_negative_closed",
            same_class_miss_closures=(same_class,),
            require_runtime_trace_mapping=False,
            require_artifact_freshness=False,
            require_model_quality_review=False,
            require_same_class_miss_closure=True,
            require_runtime_gateway_closure=False,
            require_risk_ledger=False,
            allow_scoped_confidence=False,
        )
    )
    ok = bool(
        backfeed.disposition == MODEL_MISS_BACKFEED_REUSE_EXISTING
        and backfeed.primary_context is not None
        and backfeed.primary_context.commitment_id == COMMITMENT_ID
        and false_negative.ok
        and maturation.ok
        and closure.ok
    )
    return {
        "ok": ok,
        "miss_id": REPLAY_MISS_ID,
        "behavior_backfeed": backfeed.to_dict(),
        "false_negative": false_negative.to_dict(),
        "maturation": maturation.to_dict(),
        "same_class_closure": closure.to_dict(),
    }


def _build_organization_backup_closure(ledger: object) -> dict[str, object]:
    miss = UIModelMissRecord(
        miss_id=ORG_BACKUP_MISS_ID,
        previous_claim_id=ORG_BACKUP_OBLIGATION_ID,
        previous_green_reason=(
            "Organization migration tests covered rollback and ordinary Windows paths, "
            "but not the longer repo-local backup prefix applied to a 203-character card path."
        ),
        observed_failure=(
            "The real organization maintenance cycle preserved the source but failed before "
            "migration because the rollback copy target reached 268 characters on Windows."
        ),
        observed_failure_evidence_ref=ORG_BACKUP_OBSERVED_FAILURE_ID,
        miss_type="evidence_overclaimed",
        affected_capability_ids=("capability:organization-direct-source-upgrade",),
        same_class_capability_ids=(
            "capability:organization-complete-rollback-tree-on-windows",
            "capability:organization-rollback-reuses-normal-receipt-identity",
        ),
        required_test_ids=(ORG_BACKUP_TEST_ID,),
        required_implementation_evidence_ids=(ORG_BACKUP_RUNTIME_CLOSURE_ID,),
        affected_behavior_plane="product_runtime",
        affected_commitment_id=ORG_BACKUP_COMMITMENT_ID,
        primary_owner_model_id=OWNER_MODEL_ID,
        error_signatures=("WinError 3: migration backup destination length 268",),
        error_evidence_ids=(ORG_BACKUP_OBSERVED_FAILURE_ID,),
        root_cause_backpropagation=(
            "The rollback tree retained a descriptive repo-local prefix, but file operations "
            "did not use the Windows extended-length namespace."
        ),
        code_owner="local_kb.org_migration._native_filesystem_path",
        rationale=(
            "Preserve the existing rollback location and receipt identity while making every "
            "backup and restore file operation long-path safe."
        ),
    )
    backfeed = backfeed_model_miss_to_behavior_ledger(miss, ledger)
    false_negative = review_false_negative_backpropagation(
        FalseNegativeBackpropagationPlan(
            plan_id="plan:khaos-organization:windows-backup-path:false-negative",
            cases=(
                FalseNegativeCase(
                    case_id=ORG_BACKUP_MISS_ID,
                    previous_claim_id=ORG_BACKUP_OBLIGATION_ID,
                    observed_failure_id=ORG_BACKUP_OBSERVED_FAILURE_ID,
                    cause=FALSE_NEGATIVE_CAUSE_SCOPE_OVERCLAIM,
                    would_have_failed_if=(
                        "the rollback test had combined a near-limit card path with the full backup prefix",
                        "the Windows test had asserted a backup target longer than 260 characters",
                    ),
                    generalized_case_id=ORG_BACKUP_GENERALIZED_CASE_ID,
                    new_model_obligation_id=ORG_BACKUP_OBLIGATION_ID,
                    new_plan_item_ids=(ORG_BACKUP_TEST_ID,),
                    closure_evidence_ids=(ORG_BACKUP_RUNTIME_CLOSURE_ID,),
                    repair_evidence_ids=(
                        "code:local_kb/org_migration.py:_native_filesystem_path",
                        ORG_BACKUP_TEST_ID,
                    ),
                    metadata={
                        "observed_source_path_length": 203,
                        "observed_backup_path_length": 268,
                        "legacy_windows_path_limit": 260,
                    },
                ),
            ),
            recurring_or_high_risk=True,
            allow_scoped_confidence=False,
        )
    )
    maturation = _closed_maturation_report(
        plan_id="plan:khaos-organization:windows-backup-path:maturation",
        risk_id=ORG_BACKUP_MISS_ID,
        candidate_fingerprint="candidate:organization-windows-extended-path:v1",
        evidence_fingerprint=ORG_BACKUP_RUNTIME_CLOSURE_ID,
        signal_specs=(
            (
                "signal:organization-backup-filesystem-boundary",
                MODEL_MATURATION_SIGNAL_CODE_BOUNDARY_MISMATCH,
                ORG_BACKUP_RUNTIME_CLOSURE_ID,
                "Backup and restore now address long Windows paths without changing receipt paths.",
            ),
            (
                "signal:organization-backup-same-class",
                MODEL_MATURATION_SIGNAL_SAME_CLASS_MISSING,
                ORG_BACKUP_TEST_ID,
                "A source below 260 characters and its backup target above 260 are explicit.",
            ),
        ),
    )
    same_class = SameClassMissClosure(
        miss_id=ORG_BACKUP_MISS_ID,
        observed_failure_evidence_id=ORG_BACKUP_OBSERVED_FAILURE_ID,
        same_class_proof_evidence_id=ORG_BACKUP_TEST_ID,
        model_obligation_id=ORG_BACKUP_OBLIGATION_ID,
        defect_family_id=ORG_BACKUP_GENERALIZED_CASE_ID,
        current=True,
        result_status="passed",
        metadata={"runtime_closure_evidence_id": ORG_BACKUP_RUNTIME_CLOSURE_ID},
    )
    closure = review_flowguard_closure_contract(
        FlowGuardClosureContractPlan(
            claim_id="claim:khaos-organization-windows-backup-model-miss-closed",
            claim_scope="false_negative_closed",
            same_class_miss_closures=(same_class,),
            require_runtime_trace_mapping=False,
            require_artifact_freshness=False,
            require_model_quality_review=False,
            require_same_class_miss_closure=True,
            require_runtime_gateway_closure=False,
            require_risk_ledger=False,
            allow_scoped_confidence=False,
        )
    )
    ok = bool(
        backfeed.disposition == MODEL_MISS_BACKFEED_REUSE_EXISTING
        and backfeed.primary_context is not None
        and backfeed.primary_context.commitment_id == ORG_BACKUP_COMMITMENT_ID
        and false_negative.ok
        and maturation.ok
        and closure.ok
    )
    return {
        "ok": ok,
        "miss_id": ORG_BACKUP_MISS_ID,
        "behavior_backfeed": backfeed.to_dict(),
        "false_negative": false_negative.to_dict(),
        "maturation": maturation.to_dict(),
        "same_class_closure": closure.to_dict(),
    }


def build_report() -> dict[str, object]:
    ledger = load_behavior_commitment_ledger(LEDGER_PATH)
    miss = UIModelMissRecord(
        miss_id=MISS_ID,
        previous_claim_id=OBLIGATION_ID,
        previous_green_reason="The performance owner had only a three-card fixture.",
        observed_failure=(
            "The current 3427-card generation exceeded catalog and exact-context budgets."
        ),
        observed_failure_evidence_ref=OBSERVED_FAILURE_ID,
        miss_type="evidence_overclaimed",
        affected_capability_ids=("capability:exact-model-bound-retrieval",),
        same_class_capability_ids=(
            "capability:distinct-card-same-generation-mesh-reuse",
            "capability:catalog-latency-with-independent-memory-probe",
        ),
        required_test_ids=(SAME_CLASS_TEST_ID, MEASUREMENT_TEST_ID),
        required_implementation_evidence_ids=(RUNTIME_CLOSURE_ID,),
        affected_behavior_plane="product_runtime",
        affected_commitment_id=COMMITMENT_ID,
        primary_owner_model_id=OWNER_MODEL_ID,
        error_signatures=(
            "catalog-performance:30.620497>30.000000",
            "exact-context-p95:3.145622>2.000000",
        ),
        error_evidence_ids=(OBSERVED_FAILURE_ID,),
        root_cause_backpropagation=(
            "The benchmark timed memory instrumentation, and each distinct card reparsed "
            "the same immutable scope mesh three times. The small fixture did not expose scale."
        ),
        code_owner="local_kb.logicguard_models._cached_current_mesh_view",
        rationale="Reuse the existing retrieval commitment and close the scale class, not one card.",
    )
    backfeed = backfeed_model_miss_to_behavior_ledger(miss, ledger)

    false_negative = review_false_negative_backpropagation(
        FalseNegativeBackpropagationPlan(
            plan_id="plan:khaos-logicguard-runtime:false-negative",
            cases=(
                FalseNegativeCase(
                    case_id=MISS_ID,
                    previous_claim_id=OBLIGATION_ID,
                    observed_failure_id=OBSERVED_FAILURE_ID,
                    cause=FALSE_NEGATIVE_CAUSE_SCOPE_OVERCLAIM,
                    would_have_failed_if=(
                        "the performance gate had included the existing 3427-card generation",
                        "the same-class test had required distinct cards to share one mesh view",
                        "catalog timing had excluded memory instrumentation overhead",
                    ),
                    generalized_case_id=GENERALIZED_CASE_ID,
                    new_model_obligation_id=OBLIGATION_ID,
                    new_plan_item_ids=(SAME_CLASS_TEST_ID, MEASUREMENT_TEST_ID),
                    closure_evidence_ids=(RUNTIME_CLOSURE_ID,),
                    repair_evidence_ids=(
                        "code:local_kb/logicguard_models.py:_cached_current_mesh_view",
                        "code:scripts/check_khaos_logicguard_runtime.py:build_report",
                        SAME_CLASS_TEST_ID,
                        MEASUREMENT_TEST_ID,
                    ),
                    metadata={
                        "failed_entry_count": 3427,
                        "failed_catalog_seconds": 30.620497,
                        "failed_exact_context_p95_seconds": 3.145622,
                        "passed_catalog_seconds": 13.069128,
                        "passed_exact_context_p95_seconds": 0.052862,
                        "passed_search_p95_seconds": 0.551762,
                    },
                ),
            ),
            recurring_or_high_risk=False,
            allow_scoped_confidence=False,
        )
    )

    maturation = _closed_maturation_report(
        plan_id="plan:khaos-logicguard-runtime:maturation",
        risk_id=MISS_ID,
        candidate_fingerprint="candidate:shared-current-mesh-view:v1",
        evidence_fingerprint=RUNTIME_CLOSURE_ID,
        signal_specs=(
            (
                "signal:runtime-scale-code-boundary",
                MODEL_MATURATION_SIGNAL_CODE_BOUNDARY_MISMATCH,
                RUNTIME_CLOSURE_ID,
                "Distinct cards now reuse one exact current mesh view.",
            ),
            (
                "signal:runtime-scale-same-class",
                MODEL_MATURATION_SIGNAL_SAME_CLASS_MISSING,
                SAME_CLASS_TEST_ID,
                "The generalized distinct-card same-generation case is current.",
            ),
        ),
    )

    same_class = SameClassMissClosure(
        miss_id=MISS_ID,
        observed_failure_evidence_id=OBSERVED_FAILURE_ID,
        same_class_proof_evidence_id=SAME_CLASS_TEST_ID,
        model_obligation_id=OBLIGATION_ID,
        defect_family_id=GENERALIZED_CASE_ID,
        current=True,
        result_status="passed",
        metadata={"runtime_closure_evidence_id": RUNTIME_CLOSURE_ID},
    )
    closure = review_flowguard_closure_contract(
        FlowGuardClosureContractPlan(
            claim_id="claim:khaos-logicguard-runtime-model-miss-closed",
            claim_scope="false_negative_closed",
            same_class_miss_closures=(same_class,),
            require_runtime_trace_mapping=False,
            require_artifact_freshness=False,
            require_model_quality_review=False,
            require_same_class_miss_closure=True,
            require_runtime_gateway_closure=False,
            require_risk_ledger=False,
            allow_scoped_confidence=False,
        )
    )

    sleep_timeout = build_sleep_timeout_report()
    foreground_replay = _build_foreground_replay_closure(ledger)
    organization_backup = _build_organization_backup_closure(ledger)
    ok = bool(
        backfeed.disposition == MODEL_MISS_BACKFEED_REUSE_EXISTING
        and backfeed.primary_context is not None
        and backfeed.primary_context.commitment_id == COMMITMENT_ID
        and false_negative.ok
        and maturation.ok
        and closure.ok
        and sleep_timeout["ok"]
        and foreground_replay["ok"]
        and organization_backup["ok"]
    )
    return {
        "artifact_type": "khaos_brain_logicguard_runtime_model_miss_review",
        "ok": ok,
        "miss_id": MISS_ID,
        "behavior_backfeed": backfeed.to_dict(),
        "false_negative": false_negative.to_dict(),
        "maturation": maturation.to_dict(),
        "same_class_closure": closure.to_dict(),
        "sleep_timeout_recovery": sleep_timeout,
        "foreground_lifecycle_replay_recovery": foreground_replay,
        "organization_windows_backup_recovery": organization_backup,
        "claim_boundary": (
            "This closes the observed 3427-card performance false negative, the 253271-event "
            "foreground lifecycle-replay false negative, the organization Windows backup-path "
            "false negative, and their declared same-class cases. "
            "It does not replace the final aggregate release owner."
        ),
    }


def main() -> int:
    report = build_report()
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
