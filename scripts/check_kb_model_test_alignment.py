#!/usr/bin/env python3
"""Align each maintained skill with its own model, code, and test evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
FLOWGUARD_ROOT = REPO_ROOT / ".flowguard"
for root in (REPO_ROOT, FLOWGUARD_ROOT):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

from local_kb.automation_contracts import (  # noqa: E402
    AUTOMATION_COMPLETION_CONTRACTS,
    evidence_test_node_ids,
    obligation_id,
)
from scripts.build_kb_automation_skillguard_contracts import (  # noqa: E402
    MODEL_PATHS,
    build_contract_source,
)


RECEIPT_PATH = (
    REPO_ROOT / ".flowguard" / "evidence" / "kb_model_test_alignment.json"
)
EVIDENCE_SCHEMA = "khaos-brain.validation-evidence.v2"


def _load_evidence_manifest(
    evidence_manifest: dict[str, Any] | Path | None,
) -> tuple[dict[str, Any] | None, list[str]]:
    if evidence_manifest is None:
        return None, ["terminal_evidence_not_run"]
    if isinstance(evidence_manifest, Path):
        try:
            loaded = json.loads(evidence_manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return None, [f"evidence_manifest_unreadable:{type(exc).__name__}"]
    else:
        loaded = evidence_manifest
    if not isinstance(loaded, dict):
        return None, ["evidence_manifest_not_object"]
    issues: list[str] = []
    if loaded.get("schema_version") != EVIDENCE_SCHEMA:
        issues.append("evidence_manifest_schema_mismatch")
    if not str(loaded.get("run_id") or ""):
        issues.append("evidence_manifest_run_id_missing")
    if not str(loaded.get("inventory_revision") or ""):
        issues.append("evidence_manifest_inventory_revision_missing")
    if loaded.get("source_stable_during_leaf_execution") is not True:
        issues.append("source_changed_during_leaf_execution")
    if loaded.get("owner_components_stable_during_leaf_execution") is not True:
        issues.append("owner_components_changed_during_leaf_execution")
    return loaded, issues


def _terminal_full_regression(
    manifest: dict[str, Any] | None,
) -> tuple[dict[str, Any], list[str], set[str]]:
    if manifest is None:
        return {}, ["full_regression_not_run"], set()
    entries = manifest.get("entries")
    full = entries.get("full_regression") if isinstance(entries, dict) else None
    if not isinstance(full, dict):
        return {}, ["full_regression_receipt_missing"], set()
    issues: list[str] = []
    if not (
        full.get("schema_version") == EVIDENCE_SCHEMA
        and full.get("name") == "full_regression"
        and full.get("execution") in {"executed", "reused"}
        and full.get("terminal_status") == "passed"
        and full.get("ok") is True
        and full.get("timed_out") is False
        and full.get("cleanup_confirmed") is True
        and full.get("exit_code") == 0
    ):
        issues.append("full_regression_not_terminal_success")
    receipt_path_text = str(full.get("receipt_path") or "")
    receipt_hash = str(full.get("receipt_sha256") or "")
    if not receipt_path_text or not receipt_hash:
        issues.append("full_regression_receipt_identity_missing")
    else:
        receipt_path = Path(receipt_path_text).resolve()
        try:
            receipt_bytes = receipt_path.read_bytes()
        except OSError:
            issues.append("full_regression_receipt_unreadable")
        else:
            if hashlib.sha256(receipt_bytes).hexdigest() != receipt_hash:
                issues.append("full_regression_receipt_digest_mismatch")
            try:
                receipt_payload = json.loads(receipt_bytes.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                issues.append("full_regression_receipt_payload_invalid")
            else:
                for key in (
                    "schema_version",
                    "receipt_id",
                    "name",
                    "execution",
                    "identity_fingerprint",
                    "terminal_status",
                    "timed_out",
                    "cleanup_confirmed",
                    "exit_code",
                    "ok",
                    "junit",
                    "proof_artifact_ref",
                ):
                    if receipt_payload.get(key) != full.get(key):
                        issues.append(f"full_regression_receipt_manifest_mismatch:{key}")
    junit = full.get("junit")
    passed: set[str] = set()
    if not isinstance(junit, dict):
        issues.append("full_regression_junit_missing")
    else:
        passed = {str(item) for item in junit.get("passed_node_ids", []) if str(item)}
        if junit.get("present") is not True or junit.get("parse_error"):
            issues.append("full_regression_junit_invalid")
        if int(junit.get("testcase_count") or 0) <= 0:
            issues.append("full_regression_junit_empty")
        if junit.get("failed_node_ids"):
            issues.append("full_regression_junit_failed_nodes")
        if junit.get("errored_node_ids"):
            issues.append("full_regression_junit_error_nodes")
        if junit.get("skipped_node_ids"):
            issues.append("full_regression_junit_skipped_nodes")
        if junit.get("unparsed_cases"):
            issues.append("full_regression_junit_unparsed_nodes")
        proof = full.get("proof_artifact_ref")
        if not isinstance(proof, dict):
            issues.append("full_regression_proof_missing")
        else:
            proof_path = Path(str(proof.get("path") or "")).resolve()
            try:
                proof_bytes = proof_path.read_bytes()
            except OSError:
                issues.append("full_regression_proof_unreadable")
            else:
                if hashlib.sha256(proof_bytes).hexdigest() != str(proof.get("sha256") or ""):
                    issues.append("full_regression_proof_digest_mismatch")
                else:
                    from scripts.check_chaos_brain_readiness import _junit_summary

                    if _junit_summary(proof_path, REPO_ROOT) != junit:
                        issues.append("full_regression_junit_replay_mismatch")
    return full, issues, passed


def _obligation_rows() -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    for skill_id, spec in AUTOMATION_COMPLETION_CONTRACTS.items():
        resolved = evidence_test_node_ids(skill_id, repo_root=REPO_ROOT)
        for item in spec["obligations"]:
            rows.append(
                {
                    "id": obligation_id(skill_id, str(item["suffix"])),
                    "maintenance_unit_id": f"unit:{skill_id}",
                    "skill_id": skill_id,
                    "model_path": MODEL_PATHS[skill_id],
                    "code_path": str(spec["entrypoint_path"]),
                    "test_nodes": [
                        resolved[str(marker)]
                        for marker in item["evidence_tests"]
                    ],
                }
            )
    return tuple(rows)


OBLIGATIONS: tuple[dict[str, Any], ...] = _obligation_rows()


def build_report(
    *,
    evidence_manifest: dict[str, Any] | Path | None = None,
    run_missing: bool = False,
) -> dict[str, Any]:
    del run_missing
    manifest, manifest_issues = _load_evidence_manifest(evidence_manifest)
    full_regression, receipt_issues, passed_nodes = _terminal_full_regression(manifest)
    terminal_requested = evidence_manifest is not None
    owner_counts: dict[str, int] = {}
    node_owners: dict[str, str] = {}
    overlaps: list[dict[str, str]] = []
    binding_rows: list[dict[str, Any]] = []
    for row in OBLIGATIONS:
        obligation = str(row["id"])
        owner_counts[obligation] = owner_counts.get(obligation, 0) + 1
        issues: list[str] = []
        model_path = REPO_ROOT / str(row["model_path"])
        code_path = REPO_ROOT / str(row["code_path"])
        if not model_path.is_file():
            issues.append("model_missing")
        if not code_path.is_file():
            issues.append("code_owner_missing")
        for node_id in row["test_nodes"]:
            prior = node_owners.get(node_id)
            current = str(row["maintenance_unit_id"])
            if prior is not None and prior != current:
                overlaps.append(
                    {
                        "node_id": node_id,
                        "first_unit": prior,
                        "second_unit": current,
                    }
                )
                issues.append("cross_unit_test_evidence_reuse")
            node_owners[node_id] = current
            if terminal_requested and node_id not in passed_nodes:
                issues.append(f"required_test_node_not_passed:{node_id}")
        binding_rows.append(
            {
                "model_obligation_id": obligation,
                "maintenance_unit_id": row["maintenance_unit_id"],
                "skill_id": row["skill_id"],
                "model_path": row["model_path"],
                "code_path": row["code_path"],
                "test_nodes": row["test_nodes"],
                "status": (
                    "aligned_current"
                    if terminal_requested and not issues and not manifest_issues and not receipt_issues
                    else "planned_not_run"
                    if not terminal_requested and not issues
                    else "blocked"
                ),
                "open_gap_codes": sorted(set(issues)),
            }
        )
    unit_reports: dict[str, dict[str, Any]] = {}
    for skill_id in AUTOMATION_COMPLETION_CONTRACTS:
        source = build_contract_source(skill_id)
        expected = {
            obligation_id(skill_id, str(item["suffix"]))
            for item in AUTOMATION_COMPLETION_CONTRACTS[skill_id][
                "obligations"
            ]
        }
        closure_profiles = source.get("closure_profiles") or []
        enforced = next(
            (
                item
                for item in closure_profiles
                if item.get("profile_id") == "enforced"
            ),
            {},
        )
        actual = {
            str(item)
            for item in enforced.get("required_obligation_ids", [])
            if str(item)
        }
        unit_reports[skill_id] = {
            "ok": actual == expected,
            "maintenance_unit_id": f"unit:{skill_id}",
            "member_skill_ids": source["member_skill_ids"],
            "obligation_count": len(actual),
            "missing_obligation_ids": sorted(expected - actual),
            "extra_obligation_ids": sorted(actual - expected),
        }
    exactly_one_owner = all(count == 1 for count in owner_counts.values())
    planning_ok = bool(
        exactly_one_owner
        and not overlaps
        and all(
            not [
                code
                for code in row["open_gap_codes"]
                if not str(code).startswith("required_test_node_not_passed:")
            ]
            for row in binding_rows
        )
        and all(row["ok"] for row in unit_reports.values())
    )
    ok = bool(
        terminal_requested
        and planning_ok
        and not manifest_issues
        and not receipt_issues
        and all(row["status"] == "aligned_current" for row in binding_rows)
    )
    alignment = {
        "ok": ok,
        "decision": (
            "aligned_current"
            if ok
            else "frozen_not_run"
            if planning_ok and not terminal_requested
            else "model_test_alignment_blocked"
        ),
        "summary": (
            "Every maintenance unit owns current model/code/test bindings and every required test node passed in the exact full-regression receipt."
            if ok
            else "Static ownership is available, but terminal current test evidence is absent or incomplete."
        ),
        "binding_rows": binding_rows,
        "findings": overlaps,
    }
    return {
        "schema_version": "khaos-brain.model-code-test-alignment.v3",
        "check": "kb-model-code-test-alignment",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ok": ok,
        "planning_ok": planning_ok,
        "terminal_evidence_requested": terminal_requested,
        "alignment": alignment,
        "owner_counts": owner_counts,
        "exactly_one_primary_owner": exactly_one_owner,
        "cross_unit_test_evidence_overlaps": overlaps,
        "maintenance_units": unit_reports,
        "obligation_ids": [str(row["id"]) for row in OBLIGATIONS],
        "current_runs": {
            "full_regression": {
                "receipt_id": str(full_regression.get("receipt_id") or ""),
                "terminal_status": str(full_regression.get("terminal_status") or "not_run"),
                "passed_node_count": len(passed_nodes),
            }
        },
        "receipt_findings": sorted(set([*manifest_issues, *receipt_issues])),
        "test_mesh": {
            "schema_version": "khaos-brain.test-mesh-terminal.v1",
            "planning_inventory_count": len(OBLIGATIONS),
            "required_node_ids": sorted({node for row in OBLIGATIONS for node in row["test_nodes"]}),
            "passed_node_ids": sorted({node for row in OBLIGATIONS for node in row["test_nodes"] if node in passed_nodes}),
            "not_run_node_ids": sorted({node for row in OBLIGATIONS for node in row["test_nodes"] if node not in passed_nodes}),
            "failed_node_ids": list((full_regression.get("junit") or {}).get("failed_node_ids", [])) if isinstance(full_regression.get("junit"), dict) else [],
            "errored_node_ids": list((full_regression.get("junit") or {}).get("errored_node_ids", [])) if isinstance(full_regression.get("junit"), dict) else [],
            "skipped_node_ids": list((full_regression.get("junit") or {}).get("skipped_node_ids", [])) if isinstance(full_regression.get("junit"), dict) else [],
            "terminal_status": "passed" if ok else "not_run" if not terminal_requested else "blocked",
            "ok": ok,
        },
        "claim_boundary": (
            "Static ownership is reported separately as planning_ok. Terminal ok additionally requires the exact current full-regression receipt and every declared JUnit node to be passed; this consumer launches no tests."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-write-receipt", action="store_true")
    parser.add_argument("--evidence-manifest", type=Path)
    parser.add_argument("--run-missing", action="store_true")
    args = parser.parse_args()
    report = build_report(
        evidence_manifest=args.evidence_manifest,
        run_missing=args.run_missing,
    )
    if not args.no_write_receipt:
        RECEIPT_PATH.parent.mkdir(parents=True, exist_ok=True)
        RECEIPT_PATH.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print("Model-code-test alignment:", "PASS" if report["ok"] else "FAIL")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
