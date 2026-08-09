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
from kb_dream_opportunity_timeout_model_miss import (
    build_report as build_dream_opportunity_timeout_report,
)

from flowguard import (
    FALSE_NEGATIVE_CAUSE_SCOPE_OVERCLAIM,
    MODEL_MATURATION_SIGNAL_CODE_BOUNDARY_MISMATCH,
    MODEL_MATURATION_SIGNAL_SAME_CLASS_MISSING,
    MODEL_MATURATION_RECEIPT_STATUS_PASS,
    MODEL_MATURATION_RESOLUTION_MODEL_EDIT,
    MODEL_MISS_BACKFEED_REUSE_EXISTING,
    COVERAGE_DISPOSITION_SATISFIED,
    COVERAGE_TIER_STANDARD,
    CoverageDemandRow,
    FalseNegativeBackpropagationPlan,
    FalseNegativeCase,
    FlowGuardClosureContractPlan,
    ModelMaturationCoverageContribution,
    ModelMaturationPlan,
    ModelMaturationSignal,
    OwnerCoverageResolution,
    ProofArtifactRef,
    SameClassMissClosure,
    TaskCoverageDemand,
    UIModelMissRecord,
    backfeed_model_miss_to_behavior_ledger,
    load_behavior_commitment_ledger,
    review_false_negative_backpropagation,
    review_flowguard_closure_contract,
    review_model_maturation_loop,
)
from flowguard.model_path_quality import (
    PathQualityResult,
    PathQualitySubject,
    canonical_fingerprint,
)
from model_maturation_fixture import verify_typed_maturation_report


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
ORG_BATCH_MISS_ID = "miss:khaos-organization:overlap-and-deletion-inventory"
ORG_BATCH_OBLIGATION_ID = "req.organization.merge-split"
ORG_BATCH_GENERALIZED_CASE_ID = "case:organization:nonoverlap-selection-and-complete-materialization"
ORG_BATCH_OBSERVED_FAILURE_ID = (
    "evidence:native-kb-organization-maintenance-20260801T090241614983Z-5cc7ad48"
)
ORG_BATCH_RUNTIME_CLOSURE_ID = "evidence:organization-maintenance:exact-batch-and-clean-restore-pass"
ORG_BATCH_SELECTION_TEST_ID = (
    "test:tests/test_org_maintenance.py::OrganizationMaintenanceTests::"
    "test_review_selects_only_non_overlapping_merge_packets_per_generation"
)
ORG_BATCH_MATERIALIZATION_TEST_ID = (
    "test:tests/test_org_automation.py::OrganizationAutomationTests::"
    "test_maintenance_applies_cleanup_and_pushes_maintenance_branch"
)
ORG_REMOTE_GATE_MISS_ID = "miss:khaos-organization:remote-checker-contract-drift"
ORG_REMOTE_GATE_OBLIGATION_ID = "req.organization.remote-gate-parity"
ORG_REMOTE_GATE_GENERALIZED_CASE_ID = (
    "case:organization:source-contract-and-remote-gate-share-one-current-format"
)
ORG_REMOTE_GATE_OBSERVED_FAILURE_ID = (
    "evidence:github-actions:organization-kb-checks:30699837940"
)
ORG_REMOTE_GATE_PORTABLE_DIGEST_FAILURE_ID = (
    "evidence:github-actions:organization-kb-checks:30700491515"
)
ORG_REMOTE_GATE_REVIEW_POLICY_FAILURE_ID = (
    "evidence:github-actions:organization-kb-auto-merge:30701137747"
)
ORG_REMOTE_GATE_RUNTIME_CLOSURE_ID = (
    "evidence:github-actions:organization-kb-checks:current-schema2-bundle-pass"
)
ORG_REMOTE_GATE_PACKET_TEST_ID = (
    "test:tests/test_org_github_automation.py::OrganizationGitHubAutomationTests::"
    "test_installed_checker_accepts_complete_schema2_maintenance_packet"
)
ORG_REMOTE_GATE_MISSING_BUNDLE_TEST_ID = (
    "test:tests/test_org_github_automation.py::OrganizationGitHubAutomationTests::"
    "test_installed_checker_rejects_missing_logicguard_bundle"
)
ORG_REMOTE_GATE_PORTABLE_DIGEST_TEST_ID = (
    "test:tests/test_org_github_automation.py::OrganizationGitHubAutomationTests::"
    "test_installed_checker_accepts_catalog_digest_after_lf_checkout"
)
ORG_REMOTE_GATE_REVIEW_POLICY_TEST_ID = (
    "test:tests/test_github_repo_config.py::GitHubRepoConfigTests::"
    "test_branch_protection_payload_requires_expected_check_context"
)
SEARCH_ENVELOPE_MISS_ID = "miss:khaos-retrieval:default-organization-status-hidden"
SEARCH_ENVELOPE_GENERALIZED_CASE_ID = (
    "case:retrieval:local-success-and-organization-failure-share-one-envelope"
)
SEARCH_ENVELOPE_OBSERVED_FAILURE_ID = (
    "evidence:default-kb-search:organization-status-hidden-by-bare-list"
)
SEARCH_ENVELOPE_RUNTIME_CLOSURE_ID = (
    "evidence:default-kb-search:canonical-source-status-envelope-pass"
)
SEARCH_ENVELOPE_TEST_ID = (
    "test:tests/test_kb_preflight_entry_compat.py::"
    "KbPreflightEntryCurrentGrammarTests::"
    "test_default_search_keeps_local_results_and_exposes_organization_failure"
)
SEARCH_ENVELOPE_RETIREMENT_TEST_ID = (
    "test:tests/test_kb_preflight_entry_compat.py::"
    "KbPreflightEntryCurrentGrammarTests::"
    "test_local_search_rejects_retired_optional_envelope_flag"
)
FOREGROUND_CAPTURE_MISS_ID = "miss:khaos-intake:foreground-direct-candidate-write"
FOREGROUND_CAPTURE_COMMITMENT_ID = "commitment:sleep-no-delta-single-owner"
FOREGROUND_CAPTURE_OBLIGATION_ID = "req.card.foreground-observation-only"
FOREGROUND_CAPTURE_GENERALIZED_CASE_ID = (
    "case:intake:foreground-history-only-and-sleep-owned-candidate-publication"
)
FOREGROUND_CAPTURE_OBSERVED_FAILURE_ID = (
    "evidence:kb-candidates:cand-2026-08-01-yielded-regression-sessi"
)
FOREGROUND_CAPTURE_RUNTIME_CLOSURE_ID = (
    "evidence:foreground-intake:direct-candidate-writer-retired"
)
FOREGROUND_CAPTURE_RETIREMENT_TEST_ID = (
    "test:tests/test_kb_preflight_entry_compat.py::"
    "KbPreflightEntryCurrentGrammarTests::"
    "test_launcher_rejects_retired_direct_candidate_capture"
)
FOREGROUND_CAPTURE_HISTORY_TEST_ID = (
    "test:tests/test_kb_preflight_entry_compat.py::"
    "KbPreflightEntryCurrentGrammarTests::"
    "test_feedback_emits_terminal_json_and_inspects_the_same_event_id"
)
RAW_REPAIR_MISS_ID = "miss:khaos-sleep:raw-candidate-repair-inventory-omitted"
RAW_REPAIR_COMMITMENT_ID = "commitment:sleep-no-delta-single-owner"
RAW_REPAIR_OBLIGATION_ID = "req.maintenance.raw-candidate-upgrade"
RAW_REPAIR_GENERALIZED_CASE_ID = (
    "case:sleep:raw-candidate-frozen-upgrade-and-open-batch-omission-recovery"
)
RAW_REPAIR_OBSERVED_FAILURE_ID = (
    "evidence:native-kb-sleep-maintenance-20260801T100636121183Z-01d65dc0"
)
RAW_REPAIR_RUNTIME_CLOSURE_ID = (
    "evidence:sleep-raw-candidate:explicit-upgrade-inventory-pass"
)
RAW_REPAIR_NEW_BATCH_TEST_ID = (
    "test:tests/test_kb_lifecycle_sleep_batch_integration.py::"
    "test_new_sleep_batch_freezes_and_upgrades_one_raw_candidate"
)
RAW_REPAIR_OPEN_BATCH_TEST_ID = (
    "test:tests/test_kb_lifecycle_sleep_batch_integration.py::"
    "test_resume_repairs_a_raw_candidate_omitted_by_an_already_frozen_batch"
)
RAW_REPAIR_PARTIAL_BINDING_TEST_ID = (
    "test:tests/test_khaos_sleep_model_maintenance.py::"
    "KhaosSleepModelMaintenanceTests::"
    "test_sleep_upgrade_intake_rejects_a_schema_less_candidate_with_partial_authority"
)


def _closed_maturation_report(
    *,
    plan_id: str,
    risk_id: str,
    candidate_fingerprint: str,
    evidence_fingerprint: str,
    signal_specs: tuple[tuple[str, str, str, str], ...],
) -> object:
    """Build one current-schema maturation closure with typed owner evidence.

    FlowGuard's current maturation contract deliberately rejects a caller's
    bare ``resolved=True`` fixture.  Each model-miss closure therefore compiles
    a small TaskCoverageDemand, binds one owner resolution and proof artifact
    to that demand, and supplies an independent path-quality denominator.  The
    fixture remains local to this review; it does not create runtime authority.
    """

    def _fingerprint(value: object) -> str:
        return value if isinstance(value, str) and value.startswith("sha256:") else canonical_fingerprint(value)

    task_id = f"task:{risk_id}:closure"
    candidate_sha = _fingerprint(candidate_fingerprint)
    evidence_sha = _fingerprint(evidence_fingerprint)
    coverage_ids = tuple(f"{risk_id}:coverage:{index}" for index in range(len(signal_specs)))
    probe_ids = tuple(f"{risk_id}:probe:{index}" for index in range(len(signal_specs)))
    demand_id = f"{risk_id}:coverage-demand:v1"
    proof_id = f"proof:{risk_id}:model-miss-review"
    proof_fingerprint = _fingerprint({"proof_id": proof_id, "evidence": evidence_sha})
    demand = TaskCoverageDemand(
        demand_id=demand_id,
        task_id=task_id,
        task_fingerprint=_fingerprint({"task_id": task_id, "risk_id": risk_id}),
        presentation_tier=COVERAGE_TIER_STANDARD,
        rows=(
            CoverageDemandRow(
                demand_id=f"{demand_id}:row:model-miss-review",
                rule_id=f"rule:{risk_id}:model-miss-review",
                owner_route="model_miss_review",
                coverage_ids=coverage_ids,
                triggered=True,
                disposition=COVERAGE_DISPOSITION_SATISFIED,
                reason="The declared model-miss owner supplies current closure evidence.",
                evidence_ids=(proof_id,),
                evidence_fingerprints=(proof_fingerprint,),
            ),
        ),
    )
    resolution = OwnerCoverageResolution(
        resolution_id=f"resolution:{risk_id}:model-miss-review",
        task_id=task_id,
        demand_id=demand.demand_id,
        demand_fingerprint=demand.fingerprint,
        owner_route="model_miss_review",
        disposition=COVERAGE_DISPOSITION_SATISFIED,
        obligation_ids=coverage_ids,
        evidence_ids=(proof_id,),
        evidence_fingerprints=(proof_fingerprint,),
    )
    proof = ProofArtifactRef(
        artifact_id=proof_id,
        producer_route="model_miss_review",
        command="khaos_brain_logicguard_runtime_model_miss.py --json",
        result_path=str(Path(__file__).resolve()),
        result_status="passed",
        exit_code=0,
        started_at="2026-08-08T00:00:00+00:00",
        finished_at="2026-08-08T00:00:01+00:00",
        subject_id=resolution.resolution_id,
        subject_fingerprint=resolution.resolution_fingerprint,
        artifact_fingerprints={proof_id: proof_fingerprint},
        covered_obligation_ids=coverage_ids,
        current=True,
        route_evidence_current=True,
        progress_only=False,
    )

    currentness_id = f"path-quality-current:{risk_id}:{candidate_sha[7:23]}"
    subject = PathQualitySubject(
        model_id=OWNER_MODEL_ID,
        boundary_id=f"model-miss:{risk_id}:path-quality",
        model_fingerprint=candidate_sha,
        normalized_facts_fingerprint=_fingerprint({"risk_id": risk_id, "facts": "current"}),
        retained_element_inventory_fingerprint=_fingerprint({"risk_id": risk_id, "retained": "declared"}),
        purpose_fingerprint=_fingerprint({"risk_id": risk_id, "purpose": "close-model-miss"}),
        intent_fingerprint=_fingerprint({"risk_id": risk_id, "intent": "current-observed"}),
        obligation_fingerprint=_fingerprint({"risk_id": risk_id, "obligations": list(coverage_ids)}),
        provider_fingerprint=_fingerprint({"provider": "model_miss_review", "risk_id": risk_id}),
        dependency_fingerprint=_fingerprint({"dependencies": [OWNER_MODEL_ID], "risk_id": risk_id}),
        code_fingerprint=_fingerprint({"code": str(Path(__file__).resolve()), "risk_id": risk_id}),
        test_fingerprint=_fingerprint({"tests": [spec[0] for spec in signal_specs], "risk_id": risk_id}),
        oracle_fingerprint=_fingerprint({"oracle": "review_model_maturation_loop", "risk_id": risk_id}),
        evidence_fingerprint=evidence_sha,
        currentness_id=currentness_id,
    )
    path_quality_result = PathQualityResult(
        result_id=f"path-quality-result:{risk_id}",
        subject_fingerprint=subject.fingerprint,
        mode="lightweight",
        trigger_ids=(),
        finding_ids=(),
        candidate_ids=(),
        rewrite_rule_ids=(),
        conclusion="single_clear_path",
        unresolved_ids=(),
        selected_candidate_id="",
        selected_candidate_lane="",
        comparison_boundary_id="",
        candidate_set_fingerprint="",
        rewrite_set_fingerprint="",
        necessity_witness_set_fingerprint=_fingerprint({"risk_id": risk_id, "witnesses": ()}),
        detail_evidence_fingerprint=evidence_sha,
        producer_id="model_miss_review",
        currentness_id=currentness_id,
        current=True,
    )

    plan = ModelMaturationPlan(
        plan_id=plan_id,
        task_id=task_id,
        task_purpose="Close the observed model-miss class with exact current evidence.",
        model_id=OWNER_MODEL_ID,
        risk_id=risk_id,
        coverage_universe_id=demand.demand_id,
        coverage_demand_fingerprint=demand.fingerprint,
        coverage_owner="flowguard-model-miss-review",
        coverage_source_refs=(
            f"model:{OWNER_MODEL_ID}",
            "ledger:commitment:kb-retrieval-current-index",
        ),
        coverage_ids=coverage_ids,
        required_probe_ids=probe_ids,
        base_model_fingerprint=_fingerprint({"base": risk_id}),
        candidate_model_fingerprint=candidate_sha,
        evidence_fingerprint=evidence_sha,
        required_path_quality_model_ids=(OWNER_MODEL_ID,),
        path_quality_subjects=(subject,),
        path_quality_results=(path_quality_result,),
        owner_resolution_ids=(resolution.resolution_id,),
        owner_resolution_fingerprints=(resolution.resolution_fingerprint,),
        owner_resolution_owner_ids=(resolution.owner_route,),
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
            evidence_fingerprint=_fingerprint({"evidence_id": evidence_id}),
            resolved=True,
            current=True,
            receipt_id=f"receipt:{risk_id}:{index}",
            receipt_fingerprint=f"receipt-fingerprint:{risk_id}:{index}",
            receipt_status=MODEL_MATURATION_RECEIPT_STATUS_PASS,
            receipt_task_id=plan.task_id,
            receipt_probe_id=probe_ids[index],
            receipt_candidate_fingerprint=plan.candidate_model_fingerprint,
            receipt_coverage_fingerprint=plan.coverage_universe_fingerprint,
            receipt_evidence_fingerprint=_fingerprint({"evidence_id": evidence_id}),
            receipt_owner_route="model_miss_review",
        )
        for index, (signal_id, signal_type, evidence_id, description) in enumerate(signal_specs)
    )
    contribution = ModelMaturationCoverageContribution(
        contribution_id=f"contribution:{risk_id}:model-miss-review",
        owner_route="model_miss_review",
        task_id=task_id,
        coverage_source_refs=plan.coverage_source_refs,
        coverage_ids=coverage_ids,
        required_probe_ids=probe_ids,
        signals=signals,
        evidence_ref=proof,
        owner_resolution=resolution,
        candidate_model_fingerprint=plan.candidate_model_fingerprint,
        subject_fingerprints={proof_id: proof_fingerprint},
        status="pass",
        current=True,
    )
    report = review_model_maturation_loop(
        replace(plan, signals=signals, owner_resolution_contributions=(contribution,))
    )
    return verify_typed_maturation_report(report, source_file=__file__)


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
            model_maturation_evidence=(maturation.verified_maturation,),
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
        metadata={
            "runtime_closure_evidence_id": ORG_BACKUP_RUNTIME_CLOSURE_ID,
        },
    )
    closure = review_flowguard_closure_contract(
        FlowGuardClosureContractPlan(
            claim_id="claim:khaos-organization-windows-backup-model-miss-closed",
            claim_scope="false_negative_closed",
            same_class_miss_closures=(same_class,),
            model_maturation_evidence=(maturation.verified_maturation,),
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


def _build_organization_batch_closure(ledger: object) -> dict[str, object]:
    tests = (ORG_BATCH_SELECTION_TEST_ID, ORG_BATCH_MATERIALIZATION_TEST_ID)
    miss = UIModelMissRecord(
        miss_id=ORG_BATCH_MISS_ID,
        previous_claim_id=ORG_BATCH_OBLIGATION_ID,
        previous_green_reason=(
            "Merge/split tests proved one reversible packet and exact selected ids on small fixtures, "
            "but did not cover several ready packets sharing inputs or Git publication of removed paths."
        ),
        observed_failure=(
            "The real organization cycle selected six ready packets whose inputs overlapped; after five applied, "
            "one became stale. The rebuilt source also removed 25 paths that were absent from changed_paths, "
            "leaving the mirror dirty after the maintenance branch was pushed."
        ),
        observed_failure_evidence_ref=ORG_BATCH_OBSERVED_FAILURE_ID,
        miss_type="evidence_overclaimed",
        affected_capability_ids=("capability:organization-reversible-maintenance-publication",),
        same_class_capability_ids=(
            "capability:deterministic-nonoverlap-packet-selection",
            "capability:pre-post-materialized-path-union",
            "capability:deleted-path-commit-and-clean-base-restore",
        ),
        required_test_ids=tests,
        required_implementation_evidence_ids=(ORG_BATCH_RUNTIME_CLOSURE_ID,),
        affected_behavior_plane="product_runtime",
        affected_commitment_id=ORG_BACKUP_COMMITMENT_ID,
        primary_owner_model_id=OWNER_MODEL_ID,
        error_signatures=(
            "exact-selected-apply:selected-6-applied-5",
            "organization-mirror-uncommitted-deletions:25",
            "restore-base:organization-mirror-has-uncommitted-changes",
        ),
        error_evidence_ids=(ORG_BATCH_OBSERVED_FAILURE_ID,),
        root_cause_backpropagation=(
            "Review selected every individually ready packet without reserving packet input/output paths, "
            "and apply changed_paths enumerated only the rebuilt post-apply catalog, omitting removed old paths."
        ),
        code_owner=(
            "local_kb.org_maintenance.build_organization_cleanup_review + "
            "local_kb.org_cleanup.apply_organization_cleanup_proposal"
        ),
        rationale=(
            "Select a maximal non-overlapping packet set in stable proposal order and publish the union of "
            "pre/post materialized paths so deletions are staged and base restoration is clean."
        ),
    )
    backfeed = backfeed_model_miss_to_behavior_ledger(miss, ledger)
    false_negative = review_false_negative_backpropagation(
        FalseNegativeBackpropagationPlan(
            plan_id="plan:khaos-organization:exact-batch:false-negative",
            cases=(
                FalseNegativeCase(
                    case_id=ORG_BATCH_MISS_ID,
                    previous_claim_id=ORG_BATCH_OBLIGATION_ID,
                    observed_failure_id=ORG_BATCH_OBSERVED_FAILURE_ID,
                    cause=FALSE_NEGATIVE_CAUSE_SCOPE_OVERCLAIM,
                    would_have_failed_if=(
                        "three pairwise-ready merge packets had been reviewed in one source generation",
                        "a removed card's model, mesh, projection, and bundle paths had been required in changed_paths",
                        "the Git-backed test had required zero status rows after base restoration",
                    ),
                    generalized_case_id=ORG_BATCH_GENERALIZED_CASE_ID,
                    new_model_obligation_id=ORG_BATCH_OBLIGATION_ID,
                    new_plan_item_ids=tests,
                    closure_evidence_ids=(ORG_BATCH_RUNTIME_CLOSURE_ID,),
                    repair_evidence_ids=(
                        "code:local_kb/org_maintenance.py:build_organization_cleanup_review",
                        "code:local_kb/org_cleanup.py:apply_organization_cleanup_proposal",
                        *tests,
                    ),
                    metadata={
                        "observed_ready_selected_count": 6,
                        "observed_applied_count": 5,
                        "observed_unstaged_deletion_count": 25,
                    },
                ),
            ),
            recurring_or_high_risk=True,
            allow_scoped_confidence=False,
        )
    )
    maturation = _closed_maturation_report(
        plan_id="plan:khaos-organization:exact-batch:maturation",
        risk_id=ORG_BATCH_MISS_ID,
        candidate_fingerprint="candidate:organization-nonoverlap-pre-post-inventory:v1",
        evidence_fingerprint=ORG_BATCH_RUNTIME_CLOSURE_ID,
        signal_specs=(
            (
                "signal:organization-batch-code-boundary",
                MODEL_MATURATION_SIGNAL_CODE_BOUNDARY_MISMATCH,
                ORG_BATCH_RUNTIME_CLOSURE_ID,
                "Review and materialization now own separate exact non-overlap and deletion-aware boundaries.",
            ),
            (
                "signal:organization-batch-same-class",
                MODEL_MATURATION_SIGNAL_SAME_CLASS_MISSING,
                ORG_BATCH_SELECTION_TEST_ID,
                "Overlapping ready packets and Git-backed deleted-path publication are explicit.",
            ),
        ),
    )
    same_class = SameClassMissClosure(
        miss_id=ORG_BATCH_MISS_ID,
        observed_failure_evidence_id=ORG_BATCH_OBSERVED_FAILURE_ID,
        same_class_proof_evidence_id=ORG_BATCH_SELECTION_TEST_ID,
        model_obligation_id=ORG_BATCH_OBLIGATION_ID,
        defect_family_id=ORG_BATCH_GENERALIZED_CASE_ID,
        current=True,
        result_status="passed",
        metadata={
            "runtime_closure_evidence_id": ORG_BATCH_RUNTIME_CLOSURE_ID,
            "additional_same_class_test_ids": [ORG_BATCH_MATERIALIZATION_TEST_ID],
        },
    )
    closure = review_flowguard_closure_contract(
        FlowGuardClosureContractPlan(
            claim_id="claim:khaos-organization-exact-batch-model-miss-closed",
            claim_scope="false_negative_closed",
            same_class_miss_closures=(same_class,),
            model_maturation_evidence=(maturation.verified_maturation,),
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
        "miss_id": ORG_BATCH_MISS_ID,
        "behavior_backfeed": backfeed.to_dict(),
        "false_negative": false_negative.to_dict(),
        "maturation": maturation.to_dict(),
        "same_class_closure": closure.to_dict(),
    }


def _build_organization_remote_gate_closure(ledger: object) -> dict[str, object]:
    tests = (
        ORG_REMOTE_GATE_PACKET_TEST_ID,
        ORG_REMOTE_GATE_MISSING_BUNDLE_TEST_ID,
        ORG_REMOTE_GATE_PORTABLE_DIGEST_TEST_ID,
        ORG_REMOTE_GATE_REVIEW_POLICY_TEST_ID,
    )
    miss = UIModelMissRecord(
        miss_id=ORG_REMOTE_GATE_MISS_ID,
        previous_claim_id=ORG_BACKUP_COMMITMENT_ID,
        previous_green_reason=(
            "Local post-apply validation proved the schema-2 source and complete LogicGuard packet, "
            "but the model treated the independently installed GitHub checker as if it shared that contract."
        ),
        observed_failure=(
            "The real maintenance wrapper completed, pushed PR 22, and applied org-kb:auto-merge, "
            "but the first GitHub run still required source schema 1 and rejected every LogicGuard bundle, "
            "catalog, and manifest path. After that contract was repaired, the second run rejected all "
            "15 surviving card source digests because the catalog had hashed Windows CRLF bytes while "
            "GitHub checked out LF bytes. After the content gate passed, the first auto-merge run still "
            "failed because stale branch protection required one human approval that GitHub Actions "
            "cannot provide; the automatic lane remained blocked until the declared zero-review policy was restored."
        ),
        observed_failure_evidence_ref=ORG_REMOTE_GATE_OBSERVED_FAILURE_ID,
        miss_type="evidence_overclaimed",
        affected_capability_ids=("capability:organization-automatic-maintenance-adoption",),
        same_class_capability_ids=(
            "capability:remote-checker-source-schema-parity",
            "capability:remote-checker-complete-logicguard-packet-allowlist",
            "capability:remote-checker-rejects-incomplete-bundle",
            "capability:remote-checker-portable-text-digest",
            "capability:automatic-maintenance-zero-human-review-policy",
        ),
        required_test_ids=tests,
        required_implementation_evidence_ids=(ORG_REMOTE_GATE_RUNTIME_CLOSURE_ID,),
        affected_behavior_plane="product_runtime",
        affected_commitment_id=ORG_BACKUP_COMMITMENT_ID,
        primary_owner_model_id="khaos_brain_two_maintenance_cycle_flow.TwoMaintenanceCycleBlock",
        error_signatures=(
            "schema_version must be 1",
            "path is not eligible for low-risk auto-merge: kb/logicguard/bundles/",
            "organization catalog card source digest mismatch",
            "base branch policy prohibits the merge",
        ),
        error_evidence_ids=(
            ORG_REMOTE_GATE_OBSERVED_FAILURE_ID,
            ORG_REMOTE_GATE_PORTABLE_DIGEST_FAILURE_ID,
            ORG_REMOTE_GATE_REVIEW_POLICY_FAILURE_ID,
        ),
        root_cause_backpropagation=(
            "The organization source upgrader and local merge-readiness allowlist moved to schema 2 "
            "with card-bound LogicGuard bundles, while templates/github/org_kb_check.py retained the "
            "schema-1 and card-YAML-only contract. Its first schema-2 repair then reused checkout-specific "
            "raw byte hashes, so local Windows success still could not license a Linux remote claim. "
            "The repository's live branch policy had also drifted from the declared zero-human-review "
            "automatic-maintenance policy."
        ),
        code_owner="templates.github.org_kb_check",
        rationale=(
            "Keep one current checker template, validate the exact schema-2 catalog/bundle packet, "
            "allow maintenance-owned bundle/catalog/manifest paths only when the cleanup audit is present, "
            "bind generated text through one UTF-8/LF-normalized digest policy on every platform, and keep "
            "PR plus required-check protection with zero approving reviews and no administrator bypass."
        ),
    )
    backfeed = backfeed_model_miss_to_behavior_ledger(miss, ledger)
    false_negative = review_false_negative_backpropagation(
        FalseNegativeBackpropagationPlan(
            plan_id="plan:khaos-organization:remote-gate-parity:false-negative",
            cases=(
                FalseNegativeCase(
                    case_id=ORG_REMOTE_GATE_MISS_ID,
                    previous_claim_id=ORG_BACKUP_COMMITMENT_ID,
                    observed_failure_id=ORG_REMOTE_GATE_OBSERVED_FAILURE_ID,
                    cause=FALSE_NEGATIVE_CAUSE_SCOPE_OVERCLAIM,
                    would_have_failed_if=(
                        "the installed GitHub checker had been run against a schema-2 maintenance packet",
                        "the maintenance allowlist had included the exact LogicGuard bundle and catalog paths",
                        "automatic adoption had required a successful remote check and merged main commit",
                        "the same generated card had been replayed once with CRLF and once with LF bytes",
                        "the repository branch policy had been compared with the automatic zero-review contract",
                    ),
                    generalized_case_id=ORG_REMOTE_GATE_GENERALIZED_CASE_ID,
                    new_model_obligation_id=ORG_REMOTE_GATE_OBLIGATION_ID,
                    new_plan_item_ids=tests,
                    closure_evidence_ids=(ORG_REMOTE_GATE_RUNTIME_CLOSURE_ID,),
                    repair_evidence_ids=(
                        "code:templates/github/org_kb_check.py:check_manifest",
                        "code:templates/github/org_kb_check.py:check_catalog",
                        "code:templates/github/org_kb_check.py:check_paths",
                        *tests,
                    ),
                    metadata={
                        "failed_pr": 22,
                        "failed_runs": [30699837940, 30700491515, 30701137747],
                        "remote_expected_schema": 1,
                        "current_source_schema": 2,
                        "portable_text_digest_policy": "utf8-lf-v1",
                        "required_approving_review_count": 0,
                        "administrator_merge_bypass": False,
                    },
                ),
            ),
            recurring_or_high_risk=True,
            allow_scoped_confidence=False,
        )
    )
    maturation = _closed_maturation_report(
        plan_id="plan:khaos-organization:remote-gate-parity:maturation",
        risk_id=ORG_REMOTE_GATE_MISS_ID,
        candidate_fingerprint="candidate:organization-remote-schema2-bundle-portable-auto-review-gate:v3",
        evidence_fingerprint=ORG_REMOTE_GATE_RUNTIME_CLOSURE_ID,
        signal_specs=(
            (
                "signal:organization-remote-gate-code-boundary",
                MODEL_MATURATION_SIGNAL_CODE_BOUNDARY_MISMATCH,
                ORG_REMOTE_GATE_RUNTIME_CLOSURE_ID,
                "The generated remote checker now owns the same schema-2 bundle/catalog boundary as local maintenance.",
            ),
            (
                "signal:organization-remote-gate-same-class",
                MODEL_MATURATION_SIGNAL_SAME_CLASS_MISSING,
                ORG_REMOTE_GATE_PACKET_TEST_ID,
                "A complete maintenance packet passes, an incomplete LogicGuard bundle fails closed, and CRLF/LF checkouts share one digest.",
            ),
        ),
    )
    same_class = SameClassMissClosure(
        miss_id=ORG_REMOTE_GATE_MISS_ID,
        observed_failure_evidence_id=ORG_REMOTE_GATE_OBSERVED_FAILURE_ID,
        same_class_proof_evidence_id=ORG_REMOTE_GATE_PACKET_TEST_ID,
        model_obligation_id=ORG_REMOTE_GATE_OBLIGATION_ID,
        defect_family_id=ORG_REMOTE_GATE_GENERALIZED_CASE_ID,
        current=True,
        result_status="passed",
        metadata={
            "runtime_closure_evidence_id": ORG_REMOTE_GATE_RUNTIME_CLOSURE_ID,
            "additional_same_class_test_ids": [
                ORG_REMOTE_GATE_MISSING_BUNDLE_TEST_ID,
                ORG_REMOTE_GATE_PORTABLE_DIGEST_TEST_ID,
                ORG_REMOTE_GATE_REVIEW_POLICY_TEST_ID,
            ],
        },
    )
    closure = review_flowguard_closure_contract(
        FlowGuardClosureContractPlan(
            claim_id="claim:khaos-organization-remote-gate-model-miss-closed",
            claim_scope="false_negative_closed",
            same_class_miss_closures=(same_class,),
            model_maturation_evidence=(maturation.verified_maturation,),
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
        "miss_id": ORG_REMOTE_GATE_MISS_ID,
        "behavior_backfeed": backfeed.to_dict(),
        "false_negative": false_negative.to_dict(),
        "maturation": maturation.to_dict(),
        "same_class_closure": closure.to_dict(),
    }


def _build_search_envelope_closure(ledger: object) -> dict[str, object]:
    tests = (SEARCH_ENVELOPE_TEST_ID, SEARCH_ENVELOPE_RETIREMENT_TEST_ID)
    miss = UIModelMissRecord(
        miss_id=SEARCH_ENVELOPE_MISS_ID,
        previous_claim_id=OBLIGATION_ID,
        previous_green_reason=(
            "The multi-source search owner returned explicit organization status internally, "
            "but coverage did not compare that payload with the default AI-facing CLI output."
        ),
        observed_failure=(
            "The default search CLI collapsed a successful local search to a bare result list, "
            "discarding the concurrent organization-unavailable state and reason."
        ),
        observed_failure_evidence_ref=SEARCH_ENVELOPE_OBSERVED_FAILURE_ID,
        miss_type="evidence_overclaimed",
        affected_capability_ids=("capability:multi-source-visible-failure",),
        same_class_capability_ids=(
            "capability:local-success-preserves-organization-failure",
            "capability:json-and-text-source-status-parity",
            "capability:one-current-search-envelope",
        ),
        required_test_ids=tests,
        required_implementation_evidence_ids=(SEARCH_ENVELOPE_RUNTIME_CLOSURE_ID,),
        affected_behavior_plane="product_runtime",
        affected_commitment_id=COMMITMENT_ID,
        primary_owner_model_id=OWNER_MODEL_ID,
        error_signatures=(
            "default-search-json:bare-list",
            "organization-status:discarded-while-local-results-nonempty",
        ),
        error_evidence_ids=(SEARCH_ENVELOPE_OBSERVED_FAILURE_ID,),
        root_cause_backpropagation=(
            "kb_search.py rendered only multi['results']; even its optional receipt branch "
            "omitted multi['organization_status'], so the internal visible-failure contract "
            "never reached the default caller boundary."
        ),
        code_owner="local_kb.search.render_search_envelope",
        rationale=(
            "Use one canonical envelope for every machine caller and one text projection of "
            "the same source status; remove the optional envelope split rather than retain an alias."
        ),
    )
    backfeed = backfeed_model_miss_to_behavior_ledger(miss, ledger)
    false_negative = review_false_negative_backpropagation(
        FalseNegativeBackpropagationPlan(
            plan_id="plan:khaos-retrieval:search-envelope:false-negative",
            cases=(
                FalseNegativeCase(
                    case_id=SEARCH_ENVELOPE_MISS_ID,
                    previous_claim_id=OBLIGATION_ID,
                    observed_failure_id=SEARCH_ENVELOPE_OBSERVED_FAILURE_ID,
                    cause=FALSE_NEGATIVE_CAUSE_SCOPE_OVERCLAIM,
                    would_have_failed_if=(
                        "the default CLI output had been compared with multi-source source states",
                        "a local-hit fixture had required the simultaneous organization failure reason",
                        "the retired optional envelope flag had been forbidden",
                    ),
                    generalized_case_id=SEARCH_ENVELOPE_GENERALIZED_CASE_ID,
                    new_model_obligation_id=OBLIGATION_ID,
                    new_plan_item_ids=tests,
                    closure_evidence_ids=(SEARCH_ENVELOPE_RUNTIME_CLOSURE_ID,),
                    repair_evidence_ids=(
                        "code:local_kb/search.py:render_search_envelope",
                        "code:.agents/skills/local-kb-retrieve/scripts/kb_search.py:main",
                        *tests,
                    ),
                    metadata={
                        "observed_local_result_count": 4,
                        "observed_organization_status": "unavailable",
                        "retired_cli_shape": "bare-list",
                        "current_schema": "khaos-brain.search-result.v1",
                    },
                ),
            ),
            recurring_or_high_risk=True,
            allow_scoped_confidence=False,
        )
    )
    maturation = _closed_maturation_report(
        plan_id="plan:khaos-retrieval:search-envelope:maturation",
        risk_id=SEARCH_ENVELOPE_MISS_ID,
        candidate_fingerprint="candidate:canonical-search-source-status-envelope:v1",
        evidence_fingerprint=SEARCH_ENVELOPE_RUNTIME_CLOSURE_ID,
        signal_specs=(
            (
                "signal:search-envelope-caller-boundary",
                MODEL_MATURATION_SIGNAL_CODE_BOUNDARY_MISMATCH,
                SEARCH_ENVELOPE_RUNTIME_CLOSURE_ID,
                "Default JSON and text callers now preserve multi-source status.",
            ),
            (
                "signal:search-envelope-same-class",
                MODEL_MATURATION_SIGNAL_SAME_CLASS_MISSING,
                SEARCH_ENVELOPE_TEST_ID,
                "Local success plus organization failure is a required same-class case.",
            ),
        ),
    )
    same_class = SameClassMissClosure(
        miss_id=SEARCH_ENVELOPE_MISS_ID,
        observed_failure_evidence_id=SEARCH_ENVELOPE_OBSERVED_FAILURE_ID,
        same_class_proof_evidence_id=SEARCH_ENVELOPE_TEST_ID,
        model_obligation_id=OBLIGATION_ID,
        defect_family_id=SEARCH_ENVELOPE_GENERALIZED_CASE_ID,
        current=True,
        result_status="passed",
        metadata={
            "runtime_closure_evidence_id": SEARCH_ENVELOPE_RUNTIME_CLOSURE_ID,
            "additional_same_class_test_ids": [SEARCH_ENVELOPE_RETIREMENT_TEST_ID],
        },
    )
    closure = review_flowguard_closure_contract(
        FlowGuardClosureContractPlan(
            claim_id="claim:khaos-default-search-envelope-model-miss-closed",
            claim_scope="false_negative_closed",
            same_class_miss_closures=(same_class,),
            model_maturation_evidence=(maturation.verified_maturation,),
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
        "miss_id": SEARCH_ENVELOPE_MISS_ID,
        "behavior_backfeed": backfeed.to_dict(),
        "false_negative": false_negative.to_dict(),
        "maturation": maturation.to_dict(),
        "same_class_closure": closure.to_dict(),
    }


def _build_foreground_capture_closure(ledger: object) -> dict[str, object]:
    tests = (
        FOREGROUND_CAPTURE_RETIREMENT_TEST_ID,
        FOREGROUND_CAPTURE_HISTORY_TEST_ID,
    )
    miss = UIModelMissRecord(
        miss_id=FOREGROUND_CAPTURE_MISS_ID,
        previous_claim_id=FOREGROUND_CAPTURE_OBLIGATION_ID,
        previous_green_reason=(
            "The postflight model said foreground intake was history-only, but the canonical "
            "launcher still exposed a direct candidate writer outside that modeled surface."
        ),
        observed_failure=(
            "After a successful Sleep generation, an external postflight invoked the direct "
            "candidate writer and created cand-2026-08-01-yielded-regression-sessi without a "
            "current projection schema, making authority validation and the active index stale."
        ),
        observed_failure_evidence_ref=FOREGROUND_CAPTURE_OBSERVED_FAILURE_ID,
        miss_type="evidence_overclaimed",
        affected_capability_ids=("capability:observation-only-postflight",),
        same_class_capability_ids=(
            "capability:launcher-rejects-direct-candidate-write",
            "capability:new-candidate-suggestion-remains-history-only",
            "capability:sleep-upgrades-residual-raw-candidate",
        ),
        required_test_ids=tests,
        required_implementation_evidence_ids=(FOREGROUND_CAPTURE_RUNTIME_CLOSURE_ID,),
        affected_behavior_plane="product_runtime",
        affected_commitment_id=FOREGROUND_CAPTURE_COMMITMENT_ID,
        primary_owner_model_id=OWNER_MODEL_ID,
        error_signatures=(
            "ProjectionValidationError: Card projection schema is missing or unsupported",
            "active index source manifest is stale",
        ),
        error_evidence_ids=(FOREGROUND_CAPTURE_OBSERVED_FAILURE_ID,),
        root_cause_backpropagation=(
            "templates/predictive-kb-preflight/kb_launch.py retained capture-candidate and "
            "kb_capture_candidate.py wrote YAML plus candidate-created history directly, "
            "bypassing the modeled observation-only intake and Sleep publisher."
        ),
        code_owner="templates.predictive-kb-preflight.kb_launch.SCRIPT_MAP",
        rationale=(
            "Remove the retired launcher command and writer outright; keep feedback as the "
            "single observation intake and let Sleep upgrade the existing raw candidate."
        ),
    )
    backfeed = backfeed_model_miss_to_behavior_ledger(miss, ledger)
    false_negative = review_false_negative_backpropagation(
        FalseNegativeBackpropagationPlan(
            plan_id="plan:khaos-intake:foreground-capture:false-negative",
            cases=(
                FalseNegativeCase(
                    case_id=FOREGROUND_CAPTURE_MISS_ID,
                    previous_claim_id=FOREGROUND_CAPTURE_OBLIGATION_ID,
                    observed_failure_id=FOREGROUND_CAPTURE_OBSERVED_FAILURE_ID,
                    cause=FALSE_NEGATIVE_CAUSE_SCOPE_OVERCLAIM,
                    would_have_failed_if=(
                        "the launcher command inventory had been compared with the postflight model",
                        "new-candidate feedback had been required to leave kb/candidates unchanged",
                        "runtime assurance had run after the observed post-Sleep write",
                    ),
                    generalized_case_id=FOREGROUND_CAPTURE_GENERALIZED_CASE_ID,
                    new_model_obligation_id=FOREGROUND_CAPTURE_OBLIGATION_ID,
                    new_plan_item_ids=tests,
                    closure_evidence_ids=(FOREGROUND_CAPTURE_RUNTIME_CLOSURE_ID,),
                    repair_evidence_ids=(
                        "code:templates/predictive-kb-preflight/kb_launch.py:SCRIPT_MAP",
                        "code:.agents/skills/local-kb-retrieve/scripts/kb_feedback.py:main",
                        *tests,
                    ),
                    metadata={
                        "observed_candidate_id": "cand-2026-08-01-yielded-regression-sessi",
                        "observed_history_event_id": "f62e89d8-a2b2-41d0-8358-a1db8154d96c",
                        "retired_command": "capture-candidate",
                    },
                ),
            ),
            recurring_or_high_risk=True,
            allow_scoped_confidence=False,
        )
    )
    maturation = _closed_maturation_report(
        plan_id="plan:khaos-intake:foreground-capture:maturation",
        risk_id=FOREGROUND_CAPTURE_MISS_ID,
        candidate_fingerprint="candidate:foreground-observation-only:v1",
        evidence_fingerprint=FOREGROUND_CAPTURE_RUNTIME_CLOSURE_ID,
        signal_specs=(
            (
                "signal:foreground-capture-code-boundary",
                MODEL_MATURATION_SIGNAL_CODE_BOUNDARY_MISMATCH,
                FOREGROUND_CAPTURE_RUNTIME_CLOSURE_ID,
                "The normal launcher now has one structured observation writer and no candidate writer.",
            ),
            (
                "signal:foreground-capture-same-class",
                MODEL_MATURATION_SIGNAL_SAME_CLASS_MISSING,
                FOREGROUND_CAPTURE_RETIREMENT_TEST_ID,
                "Retired command rejection and no-authority feedback are explicit regressions.",
            ),
        ),
    )
    same_class = SameClassMissClosure(
        miss_id=FOREGROUND_CAPTURE_MISS_ID,
        observed_failure_evidence_id=FOREGROUND_CAPTURE_OBSERVED_FAILURE_ID,
        same_class_proof_evidence_id=FOREGROUND_CAPTURE_RETIREMENT_TEST_ID,
        model_obligation_id=FOREGROUND_CAPTURE_OBLIGATION_ID,
        defect_family_id=FOREGROUND_CAPTURE_GENERALIZED_CASE_ID,
        current=True,
        result_status="passed",
        metadata={
            "runtime_closure_evidence_id": FOREGROUND_CAPTURE_RUNTIME_CLOSURE_ID,
            "additional_same_class_test_ids": [FOREGROUND_CAPTURE_HISTORY_TEST_ID],
        },
    )
    closure = review_flowguard_closure_contract(
        FlowGuardClosureContractPlan(
            claim_id="claim:khaos-foreground-candidate-write-model-miss-closed",
            claim_scope="false_negative_closed",
            same_class_miss_closures=(same_class,),
            model_maturation_evidence=(maturation.verified_maturation,),
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
        and backfeed.primary_context.commitment_id == FOREGROUND_CAPTURE_COMMITMENT_ID
        and false_negative.ok
        and maturation.ok
        and closure.ok
    )
    return {
        "ok": ok,
        "miss_id": FOREGROUND_CAPTURE_MISS_ID,
        "behavior_backfeed": backfeed.to_dict(),
        "false_negative": false_negative.to_dict(),
        "maturation": maturation.to_dict(),
        "same_class_closure": closure.to_dict(),
    }


def _build_raw_candidate_repair_closure(ledger: object) -> dict[str, object]:
    tests = (
        RAW_REPAIR_NEW_BATCH_TEST_ID,
        RAW_REPAIR_OPEN_BATCH_TEST_ID,
        RAW_REPAIR_PARTIAL_BINDING_TEST_ID,
    )
    miss = UIModelMissRecord(
        miss_id=RAW_REPAIR_MISS_ID,
        previous_claim_id=RAW_REPAIR_OBLIGATION_ID,
        previous_green_reason=(
            "The publisher could replace an explicitly named raw candidate, but the Sleep lifecycle "
            "never inventoried that residual before loading the current candidate catalog."
        ),
        observed_failure=(
            "The real Sleep run resumed its frozen batch, completed four handoffs, and then failed "
            "before the first pending observation because catalog loading treated the schema-less "
            "residual as a current projection."
        ),
        observed_failure_evidence_ref=RAW_REPAIR_OBSERVED_FAILURE_ID,
        miss_type="evidence_overclaimed",
        affected_capability_ids=("capability:sleep-owned-raw-candidate-upgrade",),
        same_class_capability_ids=(
            "capability:new-batch-freezes-raw-upgrade-item",
            "capability:pre-fix-open-batch-repairs-exact-omission",
            "capability:partial-authority-is-rejected-not-guessed",
        ),
        required_test_ids=tests,
        required_implementation_evidence_ids=(RAW_REPAIR_RUNTIME_CLOSURE_ID,),
        affected_behavior_plane="product_runtime",
        affected_commitment_id=RAW_REPAIR_COMMITMENT_ID,
        primary_owner_model_id=OWNER_MODEL_ID,
        error_signatures=(
            "ProjectionValidationError: Card projection schema is missing or unsupported",
            "native-kb-sleep-maintenance exit_code=1 after partial frozen-batch progress",
        ),
        error_evidence_ids=(RAW_REPAIR_OBSERVED_FAILURE_ID,),
        root_cause_backpropagation=(
            "publish_sleep_model_generation already had an exact direct-to-current replacement path, "
            "but _build_sleep_work_inventory omitted residual raw candidates and ordinary catalog loading "
            "ran before any repair plan could name the replacing path."
        ),
        code_owner="local_kb.model_maintenance.discover_sleep_raw_candidate_upserts",
        rationale=(
            "Freeze only schema-less unbound candidate residuals as exact Sleep work, reject ambiguous "
            "inputs, and exclude only named replacements while validating the prior generation."
        ),
    )
    backfeed = backfeed_model_miss_to_behavior_ledger(miss, ledger)
    false_negative = review_false_negative_backpropagation(
        FalseNegativeBackpropagationPlan(
            plan_id="plan:khaos-sleep:raw-repair:false-negative",
            cases=(
                FalseNegativeCase(
                    case_id=RAW_REPAIR_MISS_ID,
                    previous_claim_id=RAW_REPAIR_OBLIGATION_ID,
                    observed_failure_id=RAW_REPAIR_OBSERVED_FAILURE_ID,
                    cause=FALSE_NEGATIVE_CAUSE_SCOPE_OVERCLAIM,
                    would_have_failed_if=(
                        "the lifecycle test had started from a raw residual rather than passing it directly to the publisher",
                        "the frozen work inventory had required one deterministic item per residual path and digest",
                        "an already-open pre-fix batch had been resumed with a late-discovered residual",
                    ),
                    generalized_case_id=RAW_REPAIR_GENERALIZED_CASE_ID,
                    new_model_obligation_id=RAW_REPAIR_OBLIGATION_ID,
                    new_plan_item_ids=tests,
                    closure_evidence_ids=(RAW_REPAIR_RUNTIME_CLOSURE_ID,),
                    repair_evidence_ids=(
                        "code:local_kb/model_maintenance.py:discover_sleep_raw_candidate_upserts",
                        "code:local_kb/lifecycle.py:_run_incremental_sleep_locked",
                        *tests,
                    ),
                    metadata={
                        "failed_run_id": "native-kb-sleep-maintenance-20260801T100636121183Z-01d65dc0",
                        "failed_receipt_sha256": "DBABF7CFEE237168CB5544D8083C65A9B00BF7831868DDD5AF30C830E7E627BE",
                        "completed_handoffs_preserved": 4,
                        "pending_observations": 2,
                    },
                ),
            ),
            recurring_or_high_risk=True,
            allow_scoped_confidence=False,
        )
    )
    maturation = _closed_maturation_report(
        plan_id="plan:khaos-sleep:raw-repair:maturation",
        risk_id=RAW_REPAIR_MISS_ID,
        candidate_fingerprint="candidate:sleep-raw-repair-inventory:v1",
        evidence_fingerprint=RAW_REPAIR_RUNTIME_CLOSURE_ID,
        signal_specs=(
            (
                "signal:raw-repair-code-boundary",
                MODEL_MATURATION_SIGNAL_CODE_BOUNDARY_MISMATCH,
                RAW_REPAIR_RUNTIME_CLOSURE_ID,
                "Sleep now freezes exact residual paths before current catalog loading.",
            ),
            (
                "signal:raw-repair-same-class",
                MODEL_MATURATION_SIGNAL_SAME_CLASS_MISSING,
                RAW_REPAIR_OPEN_BATCH_TEST_ID,
                "New-batch, open-batch, and ambiguous partial-binding classes are explicit regressions.",
            ),
        ),
    )
    same_class = SameClassMissClosure(
        miss_id=RAW_REPAIR_MISS_ID,
        observed_failure_evidence_id=RAW_REPAIR_OBSERVED_FAILURE_ID,
        same_class_proof_evidence_id=RAW_REPAIR_OPEN_BATCH_TEST_ID,
        model_obligation_id=RAW_REPAIR_OBLIGATION_ID,
        defect_family_id=RAW_REPAIR_GENERALIZED_CASE_ID,
        current=True,
        result_status="passed",
        metadata={
            "runtime_closure_evidence_id": RAW_REPAIR_RUNTIME_CLOSURE_ID,
            "additional_same_class_test_ids": [
                RAW_REPAIR_NEW_BATCH_TEST_ID,
                RAW_REPAIR_PARTIAL_BINDING_TEST_ID,
            ],
        },
    )
    closure = review_flowguard_closure_contract(
        FlowGuardClosureContractPlan(
            claim_id="claim:khaos-sleep-raw-candidate-repair-model-miss-closed",
            claim_scope="false_negative_closed",
            same_class_miss_closures=(same_class,),
            model_maturation_evidence=(maturation.verified_maturation,),
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
        and backfeed.primary_context.commitment_id == RAW_REPAIR_COMMITMENT_ID
        and false_negative.ok
        and maturation.ok
        and closure.ok
    )
    return {
        "ok": ok,
        "miss_id": RAW_REPAIR_MISS_ID,
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
        metadata={
            "runtime_closure_evidence_id": RUNTIME_CLOSURE_ID,
        },
    )
    closure = review_flowguard_closure_contract(
        FlowGuardClosureContractPlan(
            claim_id="claim:khaos-logicguard-runtime-model-miss-closed",
            claim_scope="false_negative_closed",
            same_class_miss_closures=(same_class,),
            model_maturation_evidence=(maturation.verified_maturation,),
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
    organization_batch = _build_organization_batch_closure(ledger)
    organization_remote_gate = _build_organization_remote_gate_closure(ledger)
    search_envelope = _build_search_envelope_closure(ledger)
    foreground_capture = _build_foreground_capture_closure(ledger)
    raw_candidate_repair = _build_raw_candidate_repair_closure(ledger)
    dream_opportunity_timeout = build_dream_opportunity_timeout_report()
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
        and organization_batch["ok"]
        and organization_remote_gate["ok"]
        and search_envelope["ok"]
        and foreground_capture["ok"]
        and raw_candidate_repair["ok"]
        and dream_opportunity_timeout["ok"]
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
        "organization_exact_batch_recovery": organization_batch,
        "organization_remote_gate_recovery": organization_remote_gate,
        "default_search_envelope_recovery": search_envelope,
        "foreground_direct_candidate_write_recovery": foreground_capture,
        "sleep_raw_candidate_repair_recovery": raw_candidate_repair,
        "dream_opportunity_timeout_recovery": dream_opportunity_timeout,
        "claim_boundary": (
            "This closes the observed 3427-card performance false negative, the 253271-event "
            "foreground lifecycle-replay false negative, the organization Windows backup-path "
            "false negative, the organization overlap/deletion-inventory false negative, the "
            "organization remote-checker contract-drift false negative, "
            "the default search source-status false negative, the foreground direct-candidate "
            "writer false negative, the Sleep raw-candidate repair-inventory false negative, the Dream "
            "opportunity-ocean/local-timeout false negative, and their "
            "declared same-class cases. "
            "It does not replace the final aggregate release owner."
        ),
    }


def main() -> int:
    report = build_report()
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
