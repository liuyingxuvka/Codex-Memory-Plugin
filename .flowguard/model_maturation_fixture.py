"""Current-schema typed maturation fixture used by model-miss reviews.

This module only builds review inputs for the checked-in model-miss scripts. It
does not publish model authority or alter normal runtime behavior.
"""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from flowguard import (
    COVERAGE_DISPOSITION_SATISFIED,
    COVERAGE_TIER_STANDARD,
    CoverageDemandRow,
    ModelMaturationCoverageContribution,
    ModelMaturationPlan,
    ModelMaturationSignal,
    OwnerCoverageResolution,
    ProofArtifactRef,
    TaskCoverageDemand,
    review_model_maturation_loop,
)
from flowguard.evidence_receipts import (
    InputSnapshot,
    ReceiptVerificationContext,
    fingerprint_value,
    save_evidence_receipt,
)
from flowguard.model_maturation_receipt import (
    ModelMaturationReceiptPublication,
    ModelMaturationReceiptRef,
    ModelMaturationVerificationContext,
    build_model_maturation_receipt,
    verify_model_maturation_receipt,
)
from flowguard.model_path_quality import (
    PathQualityResult,
    PathQualitySubject,
    canonical_fingerprint,
)


def _fingerprint(value: object) -> str:
    return value if isinstance(value, str) and value.startswith("sha256:") else canonical_fingerprint(value)


def build_typed_maturation_report(
    *,
    plan_id: str,
    task_id: str,
    task_purpose: str,
    owner_model_id: str,
    risk_id: str,
    coverage_source_refs: tuple[str, ...],
    candidate_fingerprint: str,
    evidence_fingerprint: str,
    signal_specs: tuple[tuple[str, str, str, str], ...],
    source_file: str,
) -> object:
    """Return a closed report bound to one exact demand and owner proof."""

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
        command=f"python {source_file} --json",
        result_path=str(Path(source_file).resolve()),
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
        model_id=owner_model_id,
        boundary_id=f"model-miss:{risk_id}:path-quality",
        model_fingerprint=candidate_sha,
        normalized_facts_fingerprint=_fingerprint({"risk_id": risk_id, "facts": "current"}),
        retained_element_inventory_fingerprint=_fingerprint({"risk_id": risk_id, "retained": "declared"}),
        purpose_fingerprint=_fingerprint({"risk_id": risk_id, "purpose": "close-model-miss"}),
        intent_fingerprint=_fingerprint({"risk_id": risk_id, "intent": "current-observed"}),
        obligation_fingerprint=_fingerprint({"risk_id": risk_id, "obligations": list(coverage_ids)}),
        provider_fingerprint=_fingerprint({"provider": "model_miss_review", "risk_id": risk_id}),
        dependency_fingerprint=_fingerprint({"dependencies": [owner_model_id], "risk_id": risk_id}),
        code_fingerprint=_fingerprint({"code": str(Path(source_file).resolve()), "risk_id": risk_id}),
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
        task_purpose=task_purpose,
        model_id=owner_model_id,
        risk_id=risk_id,
        coverage_universe_id=demand.demand_id,
        coverage_demand_fingerprint=demand.fingerprint,
        coverage_owner="flowguard-model-miss-review",
        coverage_source_refs=coverage_source_refs,
        coverage_ids=coverage_ids,
        required_probe_ids=probe_ids,
        base_model_fingerprint=_fingerprint({"base": risk_id}),
        candidate_model_fingerprint=candidate_sha,
        evidence_fingerprint=evidence_sha,
        required_path_quality_model_ids=(owner_model_id,),
        path_quality_subjects=(subject,),
        path_quality_results=(path_quality_result,),
        owner_resolution_ids=(resolution.resolution_id,),
        owner_resolution_fingerprints=(resolution.resolution_fingerprint,),
        owner_resolution_owner_ids=(resolution.owner_route,),
    )
    plan = plan.__class__(**{**plan.__dict__, "coverage_universe_fingerprint": plan.expected_coverage_fingerprint()})
    signals = tuple(
        ModelMaturationSignal(
            signal_id=signal_id,
            signal_type=signal_type,
            source_route="model_miss_review",
            model_id=owner_model_id,
            risk_id=risk_id,
            evidence_id=evidence_id,
            description=description,
            coverage_id=coverage_ids[index],
            probe_id=probe_ids[index],
            resolution_class="model_edit",
            prediction=description,
            falsifier=f"The same-class probe {probe_ids[index]} fails against the candidate model.",
            evidence_fingerprint=_fingerprint({"evidence_id": evidence_id}),
            resolved=True,
            current=True,
            receipt_id=f"receipt:{risk_id}:{index}",
            receipt_fingerprint=_fingerprint({"receipt": risk_id, "index": index}),
            receipt_status="pass",
            receipt_task_id=task_id,
            receipt_probe_id=probe_ids[index],
            receipt_candidate_fingerprint=candidate_sha,
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
        coverage_source_refs=coverage_source_refs,
        coverage_ids=coverage_ids,
        required_probe_ids=probe_ids,
        signals=signals,
        evidence_ref=proof,
        owner_resolution=resolution,
        candidate_model_fingerprint=candidate_sha,
        subject_fingerprints={proof_id: proof_fingerprint},
        status="pass",
        current=True,
    )
    report = review_model_maturation_loop(
        plan.__class__(
            **{
                **plan.__dict__,
                "signals": signals,
                "owner_resolution_contributions": (contribution,),
            }
        )
    )
    if not report.ok:
        return _UnverifiedMaturation(report)

    input_fingerprint = _fingerprint({"risk_id": risk_id, "candidate": candidate_sha})
    input_snapshot = InputSnapshot(
        artifact_id=f"input:{risk_id}:model-miss",
        path_token="<WORKSPACE>/.flowguard/model_maturation_fixture.py",
        hash_policy="both",
        raw_sha256=input_fingerprint,
        semantic_sha256=input_fingerprint,
        obligation_ids=coverage_ids,
    )
    environment_metadata: dict[str, str] = {}
    publication = ModelMaturationReceiptPublication(
        producer_id="flowguard.model-miss-review",
        producer_version="current",
        command=("python", "<WORKSPACE>/.flowguard/model-miss-review.py", "--json"),
        started_at="2026-08-08T00:00:00+00:00",
        finished_at="2026-08-08T00:00:01+00:00",
        environment_metadata=environment_metadata,
        contract_hash=_fingerprint({"contract": "model-maturation"}),
        check_manifest_hash=_fingerprint({"manifest": "model-miss-review"}),
        suite_map_hash=_fingerprint({"suite": "model-miss-review"}),
        input_snapshots=(input_snapshot,),
        covered_obligation_ids=coverage_ids,
    )
    receipt = build_model_maturation_receipt(report, publication)
    receipt_context = ReceiptVerificationContext(
        input_snapshots={input_snapshot.artifact_id: input_snapshot},
        contract_hash=publication.contract_hash,
        check_manifest_hash=publication.check_manifest_hash,
        suite_map_hash=publication.suite_map_hash,
        producer_id=publication.producer_id,
        producer_version=publication.producer_version,
        environment_fingerprint=fingerprint_value(environment_metadata),
        proof_artifact_fingerprint=report.evidence_fingerprint,
        result_fingerprint=receipt.result_fingerprint,
        command=publication.command,
        working_directory_token="<WORKSPACE>",
        proof_artifact_id=report.evidence_id,
        required_obligation_ids=coverage_ids,
        eligible_claim_scopes=("task_model_maturation",),
    )
    maturation_context = ModelMaturationVerificationContext(
        receipt_context=receipt_context,
        task_id=report.task_id,
        model_id=report.model_id,
        candidate_model_fingerprint=report.candidate_model_fingerprint,
        coverage_demand_fingerprint=report.coverage_demand_fingerprint,
        coverage_universe_id=report.coverage_universe_id,
        coverage_universe_fingerprint=report.coverage_universe_fingerprint,
        input_fingerprint=report.input_fingerprint,
        evidence_fingerprint=report.evidence_fingerprint,
        required_path_quality_model_ids=report.required_path_quality_model_ids,
        path_quality_subjects=report.path_quality_subjects,
        path_quality_results=report.path_quality_results,
        path_quality_result_set_fingerprint=report.path_quality_result_set_fingerprint,
        owner_resolution_ids=report.owner_resolution_ids,
        owner_resolution_fingerprints=report.owner_resolution_fingerprints,
        owner_resolution_owner_ids=report.owner_resolution_owner_ids,
        required_receipt_fingerprint=receipt.fingerprint,
    )
    with TemporaryDirectory(prefix="flowguard-maturation-") as temp_root:
        output_directory = Path(temp_root) / "receipts"
        save_evidence_receipt(receipt, temp_root, output_directory=output_directory)
        return verify_model_maturation_receipt(
            ModelMaturationReceiptRef(receipt.receipt_id, receipt.fingerprint),
            maturation_context,
            temp_root,
            output_directory=output_directory,
        )


class _UnverifiedMaturation:
    """Small diagnostic wrapper used only when the typed report is blocked."""

    def __init__(self, report: object) -> None:
        self.ok = False
        self.verified_maturation = None
        self._report = report

    def to_dict(self) -> dict[str, object]:
        return {"ok": False, "report": self._report.to_dict()}


def verify_typed_maturation_report(report: object, *, source_file: str) -> object:
    """Independently verify an already-built current maturation report."""

    if not getattr(report, "ok", False):
        return _UnverifiedMaturation(report)
    coverage_ids = (str(getattr(report, "risk_id", "model-miss")),)
    input_fingerprint = _fingerprint({"risk_id": report.risk_id, "candidate": report.candidate_model_fingerprint})
    input_snapshot = InputSnapshot(
        artifact_id=f"input:{report.risk_id}:model-miss",
        path_token="<WORKSPACE>/.flowguard/model_maturation_fixture.py",
        hash_policy="both",
        raw_sha256=input_fingerprint,
        semantic_sha256=input_fingerprint,
        obligation_ids=coverage_ids,
    )
    environment_metadata: dict[str, str] = {}
    publication = ModelMaturationReceiptPublication(
        producer_id="flowguard.model-miss-review",
        producer_version="current",
        command=("python", "<WORKSPACE>/.flowguard/model-miss-review.py", "--json"),
        started_at="2026-08-08T00:00:00+00:00",
        finished_at="2026-08-08T00:00:01+00:00",
        environment_metadata=environment_metadata,
        contract_hash=_fingerprint({"contract": "model-maturation"}),
        check_manifest_hash=_fingerprint({"manifest": "model-miss-review"}),
        suite_map_hash=_fingerprint({"suite": "model-miss-review"}),
        input_snapshots=(input_snapshot,),
        covered_obligation_ids=coverage_ids,
    )
    receipt = build_model_maturation_receipt(report, publication)
    receipt_context = ReceiptVerificationContext(
        input_snapshots={input_snapshot.artifact_id: input_snapshot},
        contract_hash=publication.contract_hash,
        check_manifest_hash=publication.check_manifest_hash,
        suite_map_hash=publication.suite_map_hash,
        producer_id=publication.producer_id,
        producer_version=publication.producer_version,
        environment_fingerprint=fingerprint_value(environment_metadata),
        proof_artifact_fingerprint=report.evidence_fingerprint,
        result_fingerprint=receipt.result_fingerprint,
        command=publication.command,
        working_directory_token="<WORKSPACE>",
        proof_artifact_id=report.evidence_id,
        required_obligation_ids=coverage_ids,
        eligible_claim_scopes=("task_model_maturation",),
    )
    maturation_context = ModelMaturationVerificationContext(
        receipt_context=receipt_context,
        task_id=report.task_id,
        model_id=report.model_id,
        candidate_model_fingerprint=report.candidate_model_fingerprint,
        coverage_demand_fingerprint=report.coverage_demand_fingerprint,
        coverage_universe_id=report.coverage_universe_id,
        coverage_universe_fingerprint=report.coverage_universe_fingerprint,
        input_fingerprint=report.input_fingerprint,
        evidence_fingerprint=report.evidence_fingerprint,
        required_path_quality_model_ids=report.required_path_quality_model_ids,
        path_quality_subjects=report.path_quality_subjects,
        path_quality_results=report.path_quality_results,
        path_quality_result_set_fingerprint=report.path_quality_result_set_fingerprint,
        owner_resolution_ids=report.owner_resolution_ids,
        owner_resolution_fingerprints=report.owner_resolution_fingerprints,
        owner_resolution_owner_ids=report.owner_resolution_owner_ids,
        required_receipt_fingerprint=receipt.fingerprint,
    )
    with TemporaryDirectory(prefix="flowguard-maturation-") as temp_root:
        output_directory = Path(temp_root) / "receipts"
        save_evidence_receipt(receipt, temp_root, output_directory=output_directory)
        return verify_model_maturation_receipt(
            ModelMaturationReceiptRef(receipt.receipt_id, receipt.fingerprint),
            maturation_context,
            temp_root,
            output_directory=output_directory,
        )
