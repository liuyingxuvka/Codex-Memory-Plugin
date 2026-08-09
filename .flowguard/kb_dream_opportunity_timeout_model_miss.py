"""Close the observed Dream opportunity-ocean and local-timeout model miss."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from model_maturation_fixture import build_typed_maturation_report

from flowguard import (
    FALSE_NEGATIVE_CAUSE_SCOPE_OVERCLAIM,
    MODEL_MATURATION_RECEIPT_STATUS_PASS,
    MODEL_MATURATION_RESOLUTION_MODEL_EDIT,
    MODEL_MATURATION_SIGNAL_CODE_BOUNDARY_MISMATCH,
    MODEL_MATURATION_SIGNAL_SAME_CLASS_MISSING,
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
MISS_ID = "miss:khaos-local-cycle:dream-opportunity-ocean-and-timeout-underbudget"
COMMITMENT_ID = "commitment:automation-proof-bound-depth-terminal"
OWNER_MODEL_ID = "khaos_brain_two_maintenance_cycle_flow.TwoMaintenanceCycleBlock"
OBLIGATION_ID = "req.maintenance.dream-bounded-artifact-and-timeout"
OBSERVED_FAILURE_ID = (
    "evidence:native-kb-sleep-maintenance-20260801T103457272618Z-dde8644f"
)
GENERALIZED_CASE_ID = (
    "case:local-cycle:full-dream-scan-bounded-persistence-and-timeout-headroom"
)
RUNTIME_CLOSURE_ID = "evidence:dream:bounded-opportunity-and-timeout-tree-pass"
BOUNDED_ARTIFACT_TEST_ID = (
    "test:tests/test_kb_dream.py::DreamMaintenanceTests::"
    "test_large_opportunity_ocean_is_compacted_before_it_becomes_a_run_artifact"
)
TIMEOUT_TREE_TEST_ID = (
    "test:tests/test_kb_automation_native_receipts.py::"
    "test_sleep_wrapper_uses_cycle_budget_and_declares_the_complete_timeout_tree"
)


def _maturation_report() -> object:
    specs = (
        (
            "signal:dream-opportunity-artifact-boundary",
            MODEL_MATURATION_SIGNAL_CODE_BOUNDARY_MISMATCH,
            BOUNDED_ARTIFACT_TEST_ID,
            "The full scan retains count/digest/fingerprints while durable opportunity rows are capped at 64.",
        ),
        (
            "signal:local-cycle-timeout-same-class",
            MODEL_MATURATION_SIGNAL_SAME_CLASS_MISSING,
            TIMEOUT_TREE_TEST_ID,
            "The local native and owner budgets are route-specific and remain below aggregate and installer owners.",
        ),
    )
    return build_typed_maturation_report(
        plan_id="plan:khaos-local-cycle:dream-ocean-timeout:maturation",
        task_id=f"task:{MISS_ID}:closure",
        task_purpose=(
            "Bound Dream persistence while preserving exact scan identity and give the "
            "combined local owner enough ordered timeout headroom."
        ),
        owner_model_id=OWNER_MODEL_ID,
        risk_id=MISS_ID,
        coverage_source_refs=(
            f"model:{OWNER_MODEL_ID}",
            f"ledger:{COMMITMENT_ID}",
        ),
        candidate_fingerprint="candidate:dream-bounded-artifact-native-timeout-2400:v1",
        evidence_fingerprint=RUNTIME_CLOSURE_ID,
        signal_specs=specs,
        source_file=__file__,
    )


def build_report() -> dict[str, object]:
    ledger = load_behavior_commitment_ledger(LEDGER_PATH)
    tests = (BOUNDED_ARTIFACT_TEST_ID, TIMEOUT_TREE_TEST_ID)
    miss = UIModelMissRecord(
        miss_id=MISS_ID,
        previous_claim_id=COMMITMENT_ID,
        previous_green_reason=(
            "The local owner modeled Sleep-then-Dream ordering and a 900-second native timeout, "
            "but did not model the size of Dream's durable opportunity artifact or the observed "
            "duration of a complete atomic Sleep publication."
        ),
        observed_failure=(
            "The exact real run completed and published its Sleep child, generation 167, and active "
            "index, then Dream persisted 3,019 full opportunities in a 44 MB file and the native "
            "owner timed out before a Dream report or outer cycle receipt could close."
        ),
        observed_failure_evidence_ref=OBSERVED_FAILURE_ID,
        miss_type="evidence_overclaimed",
        affected_capability_ids=(
            "capability:bounded-dream-opportunity-persistence",
            "capability:local-cycle-timeout-headroom",
        ),
        same_class_capability_ids=(
            "capability:large-historical-opportunity-scan",
            "capability:atomic-sleep-publication-then-dream",
        ),
        required_test_ids=tests,
        required_implementation_evidence_ids=(RUNTIME_CLOSURE_ID,),
        affected_behavior_plane="product_runtime",
        affected_commitment_id=COMMITMENT_ID,
        primary_owner_model_id=OWNER_MODEL_ID,
        error_signatures=(
            "opportunities.json size=44721148 opportunity_count=3019",
            "native hard timeout after 900 seconds after successful Sleep receipt",
        ),
        error_evidence_ids=(OBSERVED_FAILURE_ID,),
        root_cause_backpropagation=(
            "Dream duplicated complete consolidation actions and task/event lists into every opportunity, "
            "wrote that full list twice, and the local route reused the generic 900/1200-second budget even "
            "though its first atomic child alone consumed 692 seconds."
        ),
        code_owner="local_kb.dream._bounded_opportunity_projection",
        rationale=(
            "Keep exact inventory count/digest/fingerprints, persist only a bounded diagnostic projection, "
            "and give this composite route a larger ordered timeout without inferring timeout success."
        ),
    )
    backfeed = backfeed_model_miss_to_behavior_ledger(miss, ledger)
    false_negative = review_false_negative_backpropagation(
        FalseNegativeBackpropagationPlan(
            plan_id="plan:khaos-local-cycle:dream-ocean-timeout:false-negative",
            cases=(
                FalseNegativeCase(
                    case_id=MISS_ID,
                    previous_claim_id=COMMITMENT_ID,
                    observed_failure_id=OBSERVED_FAILURE_ID,
                    cause=FALSE_NEGATIVE_CAUSE_SCOPE_OVERCLAIM,
                    would_have_failed_if=(
                        "Dream artifact rows and repeated source evidence had explicit hard caps",
                        "the local composite timeout was distinct from ordinary single-child routes",
                        "the previous green claim required a real combined Sleep-plus-Dream terminal",
                    ),
                    generalized_case_id=GENERALIZED_CASE_ID,
                    new_model_obligation_id=OBLIGATION_ID,
                    new_plan_item_ids=tests,
                    closure_evidence_ids=(RUNTIME_CLOSURE_ID,),
                    repair_evidence_ids=(
                        "code:local_kb/dream.py:_bounded_opportunity_projection",
                        "code:local_kb/automation_contracts.py:native_timeout_seconds",
                        *tests,
                    ),
                    metadata={
                        "failed_run_id": "native-kb-sleep-maintenance-20260801T103457272618Z-dde8644f",
                        "sleep_terminal_preserved": True,
                        "opportunity_count": 3019,
                        "artifact_bytes": 44721148,
                        "old_native_timeout_seconds": 900,
                        "new_native_timeout_seconds": 2400,
                        "new_owner_timeout_seconds": 2700,
                    },
                ),
            ),
            recurring_or_high_risk=True,
            allow_scoped_confidence=False,
        )
    )
    maturation = _maturation_report()
    same_class = SameClassMissClosure(
        miss_id=MISS_ID,
        observed_failure_evidence_id=OBSERVED_FAILURE_ID,
        same_class_proof_evidence_id=BOUNDED_ARTIFACT_TEST_ID,
        model_obligation_id=OBLIGATION_ID,
        defect_family_id=GENERALIZED_CASE_ID,
        current=True,
        result_status="passed",
        metadata={
            "runtime_closure_evidence_id": RUNTIME_CLOSURE_ID,
            "additional_same_class_test_ids": [TIMEOUT_TREE_TEST_ID],
        },
    )
    closure = review_flowguard_closure_contract(
        FlowGuardClosureContractPlan(
            claim_id="claim:khaos-dream-opportunity-timeout-model-miss-closed",
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
        "artifact_type": "kb_dream_opportunity_timeout_model_miss_review",
        "ok": ok,
        "miss_id": MISS_ID,
        "behavior_backfeed": backfeed.to_dict(),
        "false_negative": false_negative.to_dict(),
        "maturation": maturation.to_dict(),
        "same_class_closure": closure.to_dict(),
        "claim_boundary": (
            "This closes the modeled opportunity-persistence and local-timeout same class. "
            "A new real native wrapper receipt remains required before installation."
        ),
    }


if __name__ == "__main__":
    import json

    result = build_report()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    raise SystemExit(0 if result["ok"] else 1)
