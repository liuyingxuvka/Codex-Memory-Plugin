from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

from local_kb.adoption import card_exchange_hash
from local_kb.common import normalize_text, safe_float, tokenize, utc_now_iso
from local_kb.org_sources import validate_organization_repo
from local_kb.org_source_contract import (
    authoring_card_from_projection,
    canonical_digest,
    load_current_catalog,
    materialize_current_source,
)
from local_kb.store import append_jsonl, load_yaml_file, write_yaml_file


ORG_CLEANUP_AUDIT_RELATIVE_PATH = Path("maintenance") / "cleanup_audit.jsonl"
TARGET_CARD_ROOTS = ("kb/main", "kb/imports")
CARD_ROOTS = TARGET_CARD_ROOTS
LOW_RISK_APPLY_ACTIONS = {"confidence-adjust", "status-adjust", "mark-duplicate", "accept-import", "promote-card", "merge-cards", "split-card"}
APPLY_PACKET_SCHEMA = "khaos-brain.organization-apply-packet.v1"
ORGANIZATION_EXCHANGE_SLEEP_MODEL = {
    "role": "organization-exchange-sleep",
    "description": (
        "Organization maintenance treats the shared repository as an exchange layer, "
        "not a central truth layer. The target layout is kb/imports as the incoming lane "
        "and kb/main as the exchange surface. Obsolete organization layouts are rejected "
        "by normal maintenance and can only be rewritten by the one-time upgrade migration."
    ),
    "local_final_assimilation_by_sleep": True,
    "incoming_lane": "kb/imports",
    "exchange_surface": "kb/main",
    "current_layout_only": True,
    "exchange_surface_content_maintenance": "in-scope",
    "trusted_card_content_maintenance": "in-scope",
    "extra_boundaries": ["privacy", "skill-safety"],
}
TEST_ARTIFACT_PHRASES = (
    "smoke test",
    "demo candidate",
    "demo registry",
    "dummy",
    "test fixture",
    "for testing",
)


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _is_skill_sidecar(path: Path, root: Path) -> bool:
    relative_parts = path.relative_to(root).parts
    return "skills" in relative_parts


def _is_card_payload(payload: dict[str, Any]) -> bool:
    if not str(payload.get("id") or "").strip():
        return False
    return any(payload.get(key) for key in ("title", "if", "action", "predict", "use"))


def _iter_org_card_files(org_root: Path) -> list[Path]:
    # kb/main is enumerated by the exact source catalog.  A legitimate card
    # may itself live under a route segment named ``skills``; substring path
    # filtering used to hide those cards and produced false full-coverage
    # reports.  kb/imports remains the separate incoming proposal lane.
    catalog = load_current_catalog(org_root)
    files = [
        org_root / str(row.get("source_path") or "")
        for row in (catalog.get("cards") or [])
        if isinstance(row, dict) and str(row.get("source_path") or "")
    ]
    imports_root = org_root / "kb" / "imports"
    if imports_root.is_dir():
        for path in sorted(imports_root.rglob("*.yaml")):
            if _is_skill_sidecar(path, org_root):
                continue
            payload = load_yaml_file(path)
            if isinstance(payload, dict) and _is_card_payload(payload):
                files.append(path)
    return files


def _confidence(payload: dict[str, Any]) -> float:
    return max(0.0, min(1.0, safe_float(payload.get("confidence"), 0.5)))


def _status(payload: dict[str, Any]) -> str:
    return str(payload.get("status") or "candidate").strip().lower()


def _risk_for_path(path: str) -> str:
    if path.startswith("kb/main/"):
        return "high"
    if path.startswith("kb/imports/"):
        return "low"
    return "medium"


def _action_id(action_type: str, target_path: str, reason: str = "") -> str:
    digest = hashlib.sha256(f"{action_type}|{target_path}|{reason}".encode("utf-8")).hexdigest()[:12]
    return f"{action_type}-{digest}"


def _action(action_type: str, target_path: str, **payload: Any) -> dict[str, Any]:
    reason = str(payload.get("reason") or "")
    identity_payload = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return {
        "action_id": _action_id(
            action_type,
            target_path,
            f"{reason}|{identity_payload}",
        ),
        "action_type": action_type,
        "target_path": target_path,
        **payload,
    }


def _safe_segment(value: Any, *, default: str = "card") -> str:
    text = re.sub(r"[^A-Za-z0-9_.-]+", "-", str(value or "").strip()).strip(".-")
    return text[:120] or default


def _promotion_target_path(record: dict[str, Any], org_root: Path) -> str:
    payload = record["payload"] if isinstance(record.get("payload"), dict) else {}
    route = payload.get("domain_path") if isinstance(payload.get("domain_path"), list) else []
    route_segments = [_safe_segment(item, default="route") for item in route if str(item or "").strip()]
    entry_id = _safe_segment(record.get("entry_id") or Path(str(record.get("relative_path") or "")).stem)
    target = Path("kb") / "main"
    for segment in route_segments[:6]:
        target /= segment
    target /= f"{entry_id}.yaml"
    if (org_root / target).exists():
        digest = hashlib.sha256(str(record.get("content_hash") or "").encode("utf-8")).hexdigest()[:8]
        target = target.with_name(f"{target.stem}-{digest}{target.suffix}")
    return target.as_posix()


def _title_tokens(payload: dict[str, Any]) -> set[str]:
    return set(tokenize(normalize_text(payload.get("title"))))


def _similarity(left: dict[str, Any], right: dict[str, Any]) -> float:
    left_tokens = _title_tokens(left)
    right_tokens = _title_tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / max(len(left_tokens), len(right_tokens))


def _value_tokens(value: Any) -> set[str]:
    if isinstance(value, dict):
        parts = [f"{key} {item}" for key, item in value.items()]
    elif isinstance(value, list):
        parts = [str(item) for item in value]
    else:
        parts = [str(value or "")]
    return set(tokenize(normalize_text(" ".join(parts))))


def _token_overlap(left: Any, right: Any) -> float:
    left_tokens = _value_tokens(left)
    right_tokens = _value_tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / max(len(left_tokens), len(right_tokens))


def _similarity_dimensions(left: dict[str, Any], right: dict[str, Any]) -> dict[str, float]:
    dimensions = {
        "title": _similarity(left, right),
        "scenario": _token_overlap(left.get("if"), right.get("if")),
        "action": _token_overlap(left.get("action"), right.get("action")),
        "prediction": _token_overlap(left.get("predict"), right.get("predict")),
        "route": _token_overlap(left.get("domain_path"), right.get("domain_path")),
        "evidence": _token_overlap(
            [left.get("evidence"), left.get("evidence_refs"), left.get("provenance")],
            [right.get("evidence"), right.get("evidence_refs"), right.get("provenance")],
        ),
    }
    meaningful = [
        dimensions[key]
        for key in ("scenario", "action", "prediction", "route", "evidence")
        if dimensions[key] > 0
    ]
    dimensions["semantic_composite"] = (
        sum(meaningful) / len(meaningful) if meaningful else 0.0
    )
    return {key: round(value, 3) for key, value in dimensions.items()}


def _collect_card_records(org_root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in _iter_org_card_files(org_root):
        payload = load_yaml_file(path)
        relative_path = _relative(path, org_root)
        records.append(
            {
                "path": path,
                "relative_path": relative_path,
                "entry_id": str(payload.get("id") or path.stem),
                "payload": payload,
                "status": _status(payload),
                "confidence": _confidence(payload),
                "content_hash": card_exchange_hash(payload),
                "risk": _risk_for_path(relative_path),
            }
        )
    return records


def _looks_like_test_artifact(record: dict[str, Any]) -> bool:
    payload = record["payload"] if isinstance(record.get("payload"), dict) else {}
    fields: list[str] = [
        str(record.get("entry_id") or ""),
        str(record.get("relative_path") or ""),
        str(payload.get("title") or ""),
    ]
    for key in ("tags", "trigger_keywords"):
        value = payload.get(key)
        if isinstance(value, list):
            fields.extend(str(item) for item in value)
        else:
            fields.append(str(value or ""))
    for key in ("description", "comment", "rationale"):
        fields.append(str(payload.get(key) or ""))
    text = normalize_text(" ".join(fields)).lower()
    return any(phrase in text for phrase in TEST_ARTIFACT_PHRASES)


def _overloaded_fields(payload: dict[str, Any]) -> list[str]:
    overloaded: list[str] = []
    for field in ("if", "action", "predict", "use"):
        value = payload.get(field)
        if isinstance(value, list) and len(value) > 1:
            overloaded.append(field)
            continue
        if not isinstance(value, dict):
            continue
        if any(
            key != "alternatives" and isinstance(item, list) and len(item) > 1
            for key, item in value.items()
        ):
            overloaded.append(field)
    return overloaded


def _packet_digest(packet: dict[str, Any]) -> str:
    return "sha256:" + canonical_digest({key: value for key, value in packet.items() if key != "packet_digest"})


def _attach_merge_split_packets(actions: list[dict[str, Any]], records: list[dict[str, Any]], *, organization_id: str, source_generation_id: str) -> None:
    by_path = {str(record["relative_path"]): record for record in records}
    for action in actions:
        action_type = str(action.get("action_type") or "")
        if action_type not in {"merge-cards", "split-card"}:
            continue
        target_path = str(action.get("target_path") or "")
        inputs = [target_path]
        if action_type == "merge-cards":
            inputs.append(str(action.get("related_path") or ""))
        input_rows = [by_path[path] for path in inputs if path in by_path]
        review_fingerprint = "sha256:" + canonical_digest(
            [{"path": row["relative_path"], "content_hash": row["content_hash"]} for row in input_rows]
        )
        missing_roles: list[str] = []
        outputs: list[dict[str, Any]] = []
        field_ownership: list[dict[str, str]] = []
        status = "blocked_evidence"
        if action_type == "merge-cards" and len(input_rows) == 2:
            dimensions = action.get("similarity_dimensions") if isinstance(action.get("similarity_dimensions"), dict) else {}
            exact_semantic = all(float(dimensions.get(key) or 0.0) >= 0.999 for key in ("scenario", "action", "prediction", "route", "evidence"))
            if exact_semantic:
                canonical = _preferred_duplicate_record(input_rows)
                other = input_rows[0] if input_rows[1] is canonical else input_rows[1]
                output = authoring_card_from_projection(canonical["payload"])
                related = set(str(item) for item in output.get("related_cards") or [] if str(item))
                related.update(str(item) for item in other["payload"].get("related_cards") or [] if str(item))
                related.discard(str(canonical["entry_id"]))
                related.discard(str(other["entry_id"]))
                output["related_cards"] = sorted(related)
                outputs = [{"target_path": canonical["relative_path"], "card": output}]
                field_ownership = [
                    {"field": field, "owner_entry_id": str(canonical["entry_id"])}
                    for field in ("if", "action", "predict", "use", "status", "confidence")
                ]
                status = "ready"
            else:
                missing_roles = ["field-by-field-merge-ownership", "conflict-resolution-evidence"]
        elif action_type == "split-card":
            missing_roles = ["independent-output-boundaries", "per-output-prediction", "field-ownership"]
        packet = {
            "schema_version": APPLY_PACKET_SCHEMA,
            "packet_id": "packet-" + canonical_digest({"action_id": action.get("action_id"), "review_fingerprint": review_fingerprint})[:20],
            "action_type": action_type,
            "organization_id": organization_id,
            "source_generation_id": source_generation_id,
            "input_digest": review_fingerprint,
            "builder_identity": {"name": "khaos-brain.organization-cleanup", "version": 1},
            "inputs": [
                {"entry_id": row["entry_id"], "path": row["relative_path"], "content_hash": row["content_hash"]}
                for row in input_rows
            ],
            "field_ownership": field_ownership,
            "provenance": [{"kind": "organization-card", "path": row["relative_path"], "content_hash": row["content_hash"]} for row in input_rows],
            "identity_map": [
                {"input_entry_id": row["entry_id"], "output_entry_ids": [str(item["card"]["id"]) for item in outputs]}
                for row in input_rows
            ],
            "outputs": outputs,
            "model_mesh_rebuild": "required",
            "rollback_inventory": [row["relative_path"] for row in input_rows],
            "post_apply_checks": ["current-source-validation", "catalog-exactness", "model-mesh-binding"],
            "review_status": status,
            "missing_roles": missing_roles,
            "reopen": {
                "review_fingerprint": review_fingerprint,
                "required_inputs": missing_roles,
                "prior_evidence_digest": review_fingerprint,
                "predicate": "new_evidence_digest_and_roles_satisfied",
                "unchanged_digest_policy": "skip",
                "changed_but_unsatisfied_policy": "record_once_then_skip",
            },
        }
        packet["packet_digest"] = _packet_digest(packet)
        action["apply_packet"] = packet
        action["apply_supported"] = status == "ready"
        action["review_status"] = status
        action["review_fingerprint"] = review_fingerprint
        action["missing_roles"] = missing_roles


def _preferred_duplicate_record(records: list[dict[str, Any]]) -> dict[str, Any]:
    status_rank = {"trusted": 0, "approved": 0, "candidate": 1, "deprecated": 2, "rejected": 3}
    path_rank = {"kb/main/": 0, "kb/imports/": 1}

    def sort_key(record: dict[str, Any]) -> tuple[int, int, float, str]:
        relative_path = str(record["relative_path"])
        prefix_rank = next((rank for prefix, rank in path_rank.items() if relative_path.startswith(prefix)), 9)
        return (
            status_rank.get(str(record["status"]), 4),
            prefix_rank,
            -float(record["confidence"]),
            relative_path,
        )

    return sorted(records, key=sort_key)[0]


def _skill_version_actions(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_bundle: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        proposal = record["payload"].get("organization_proposal")
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
                    "record": record,
                    "dependency": dependency,
                    "version_time": str(dependency.get("version_time") or ""),
                    "content_hash": str(dependency.get("content_hash") or ""),
                    "original_author": str(dependency.get("original_author") or ""),
                }
            )

    actions: list[dict[str, Any]] = []
    for bundle_id, versions in by_bundle.items():
        for item in versions:
            dependency = item["dependency"]
            missing: list[str] = []
            if not item["content_hash"].startswith("sha256:"):
                missing.append("sha256-content-hash")
            if not item["version_time"]:
                missing.append("version-time")
            if not item["original_author"]:
                missing.append("original-author")
            if str(dependency.get("update_policy") or "") != "original_author_only":
                missing.append("original-author-update-policy")
            if dependency.get("readonly_when_imported") is not True:
                missing.append("readonly-import")
            if missing:
                record = item["record"]
                actions.append(
                    _action(
                        "skill-bundle-safety-block",
                        record["relative_path"],
                        entry_id=record["entry_id"],
                        bundle_id=bundle_id,
                        issues=missing,
                        risk="high",
                        apply_supported=False,
                        reason="Card-bound Skill metadata is incomplete or violates the original-author safety policy.",
                    )
                )

        ordered = sorted(
            versions,
            key=lambda item: (item["version_time"], item["content_hash"], item["original_author"]),
        )
        lineage_author = next((item["original_author"] for item in ordered if item["original_author"]), "")
        if lineage_author:
            for item in ordered:
                if not item["original_author"] or item["original_author"] == lineage_author:
                    continue
                record = item["record"]
                actions.append(
                    _action(
                        "skill-bundle-fork-required",
                        record["relative_path"],
                        entry_id=record["entry_id"],
                        bundle_id=bundle_id,
                        lineage_original_author=lineage_author,
                        conflicting_original_author=item["original_author"],
                        risk="high",
                        apply_supported=False,
                        reason="A different author cannot update the original bundle lineage and must publish a new fork bundle_id.",
                    )
                )

        lineage_versions = [
            item
            for item in versions
            if not lineage_author or item["original_author"] == lineage_author
        ]
        unique_versions = {(item["version_time"], item["content_hash"]) for item in lineage_versions}
        if len(unique_versions) <= 1:
            continue
        latest = sorted(lineage_versions, key=lambda item: (item["version_time"], item["content_hash"]))[-1]
        for item in lineage_versions:
            if item is latest:
                continue
            record = item["record"]
            actions.append(
                _action(
                    "skill-version-select",
                    record["relative_path"],
                    entry_id=record["entry_id"],
                    bundle_id=bundle_id,
                    current_version_time=item["version_time"],
                    proposed_version_time=latest["version_time"],
                    current_content_hash=item["content_hash"],
                    proposed_content_hash=latest["content_hash"],
                    risk="medium",
                    apply_supported=False,
                    reason="A newer card-bound Skill bundle version exists for the same bundle_id.",
                )
            )
    return actions


def _card_decisions(
    records: list[dict[str, Any]],
    actions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    decisions: list[dict[str, Any]] = []
    reviewed_dimensions = ["scenario", "action", "prediction", "route", "evidence"]
    for record in records:
        path = str(record["relative_path"])
        related = [
            action
            for action in actions
            if str(action.get("target_path") or "") == path
            or str(action.get("related_path") or "") == path
        ]
        action_types = [str(action.get("action_type") or "") for action in related]
        if any(action.get("apply_supported") is not False for action in related):
            decision = "change"
        elif related:
            decision = "blocked_evidence" if any(action.get("review_status") == "blocked_evidence" for action in related) else "keep_separate"
        else:
            decision = "keep"
        reasons = list(
            dict.fromkeys(
                str(action.get("reason") or "").strip()
                for action in related
                if str(action.get("reason") or "").strip()
            )
        )
        if not reasons:
            reasons = [
                "No lifecycle, duplicate, merge, split, confidence, or Skill-policy trigger was found under the current maintenance policy."
            ]
        reason = " ".join(reasons)
        decisions.append(
            {
                "decision_id": _action_id("card-decision", path, reason),
                "entry_id": str(record.get("entry_id") or ""),
                "target_path": path,
                "decision": decision,
                "reason": reason,
                "reviewed_dimensions": reviewed_dimensions,
                "action_ids": [str(action.get("action_id") or "") for action in related],
                "action_types": action_types,
                "evidence": {
                    "content_hash": str(record.get("content_hash") or ""),
                    "status": str(record.get("status") or ""),
                    "confidence": float(record.get("confidence") or 0.0),
                },
            }
        )
    return decisions


def build_organization_cleanup_proposal(
    org_root: Path,
    *,
    organization_id: str = "",
    weak_confidence_threshold: float = 0.35,
    strong_candidate_threshold: float = 0.85,
    similar_title_threshold: float = 0.75,
) -> dict[str, Any]:
    org_root = Path(org_root)
    validation = validate_organization_repo(org_root)
    if not validation.get("ok"):
        return {
            "ok": False,
            "validation": validation,
            "organization_id": organization_id,
            "actions": [],
            "counts": {},
        }

    organization_id = organization_id or str(validation.get("organization_id") or "")
    records = _collect_card_records(org_root)
    actions: list[dict[str, Any]] = []

    by_hash: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        by_hash.setdefault(record["content_hash"], []).append(record)
    for content_hash, duplicates in by_hash.items():
        if len(duplicates) <= 1:
            continue
        canonical = _preferred_duplicate_record(duplicates)
        for duplicate in duplicates:
            if duplicate is canonical:
                continue
            proposed_status = "deprecated" if duplicate["relative_path"].startswith("kb/main/") else "rejected"
            actions.append(
                _action(
                    "mark-duplicate",
                    duplicate["relative_path"],
                    entry_id=duplicate["entry_id"],
                    duplicate_of=canonical["relative_path"],
                    content_hash=content_hash,
                    current_status=duplicate["status"],
                    proposed_status=proposed_status,
                    current_confidence=duplicate["confidence"],
                    proposed_confidence=min(duplicate["confidence"], 0.25),
                    risk=duplicate["risk"],
                    apply_supported=True,
                    reason="Exact duplicate card content hash exists in the organization repository.",
                )
            )

    for record in records:
        status = record["status"]
        confidence = record["confidence"]
        path = record["relative_path"]
        if status in {"rejected", "deprecated"} and confidence <= 0.2:
            actions.append(
                _action(
                    "delete-card",
                    path,
                    entry_id=record["entry_id"],
                    current_status=status,
                    current_confidence=confidence,
                    risk="high",
                    apply_supported=True,
                    reason="Low-confidence rejected or deprecated card is eligible for audited deletion.",
                )
            )
            continue
        if status == "candidate" and _looks_like_test_artifact(record):
            actions.append(
                _action(
                    "status-adjust",
                    path,
                    entry_id=record["entry_id"],
                    current_status=status,
                    proposed_status="rejected",
                    current_confidence=confidence,
                    proposed_confidence=min(confidence, 0.25),
                    risk=record["risk"],
                    apply_supported=True,
                    reason="Candidate appears to be a smoke/demo/test fixture artifact rather than reusable organization knowledge.",
                )
            )
        elif status == "candidate" and confidence <= weak_confidence_threshold:
            actions.append(
                _action(
                    "status-adjust",
                    path,
                    entry_id=record["entry_id"],
                    current_status=status,
                    proposed_status="rejected",
                    current_confidence=confidence,
                    proposed_confidence=min(confidence, 0.25),
                    risk=record["risk"],
                    apply_supported=True,
                    reason="Candidate confidence is below the weak-card threshold.",
                )
            )
        elif status == "candidate" and path.startswith("kb/imports/") and confidence < strong_candidate_threshold:
            actions.append(
                _action(
                    "accept-import",
                    path,
                    entry_id=record["entry_id"],
                    current_status=status,
                    proposed_status="candidate",
                    current_confidence=confidence,
                    proposed_confidence=confidence,
                    proposed_path=_promotion_target_path(record, org_root),
                    risk="medium",
                    apply_supported=True,
                    reason="Imported candidate is usable organization exchange material and should enter main for future maintenance.",
                )
            )
        elif status == "candidate" and path.startswith("kb/main/") and confidence >= strong_candidate_threshold:
            actions.append(
                _action(
                    "status-adjust",
                    path,
                    entry_id=record["entry_id"],
                    current_status=status,
                    proposed_status="trusted",
                    current_confidence=confidence,
                    proposed_confidence=min(0.95, confidence + 0.03),
                    risk=record["risk"],
                    apply_supported=True,
                    reason="High-confidence main candidate is eligible for reviewed organization trust upgrade.",
                )
            )
        elif status == "candidate" and confidence >= strong_candidate_threshold:
            actions.append(
                _action(
                    "promote-card",
                    path,
                    entry_id=record["entry_id"],
                    current_status=status,
                    proposed_status="trusted",
                    current_confidence=confidence,
                    proposed_confidence=min(0.95, confidence + 0.03),
                    proposed_path=_promotion_target_path(record, org_root),
                    risk="medium",
                    apply_supported=True,
                    reason="High-confidence candidate is eligible for reviewed organization promotion.",
                )
            )
        elif status == "trusted" and confidence < 0.45:
            proposed_status = "deprecated" if confidence < 0.3 else "trusted"
            actions.append(
                _action(
                    "confidence-adjust" if proposed_status == "trusted" else "status-adjust",
                    path,
                    entry_id=record["entry_id"],
                    current_status=status,
                    proposed_status=proposed_status,
                    current_confidence=confidence,
                    proposed_confidence=max(0.1, round(confidence - 0.1, 2)),
                    risk="high",
                    apply_supported=True,
                    reason="Trusted card has low confidence and needs organization maintenance review.",
                )
            )

        overloaded_fields = _overloaded_fields(record["payload"])
        if overloaded_fields:
            actions.append(
                _action(
                    "split-card",
                    path,
                    entry_id=record["entry_id"],
                    overloaded_fields=overloaded_fields,
                    risk="medium",
                    apply_supported=False,
                    reason="The card contains multiple independent branches and requires an explicit split or hub decision.",
                )
            )

    for index, left in enumerate(records):
        for right in records[index + 1 :]:
            if left["content_hash"] == right["content_hash"]:
                continue
            dimensions = _similarity_dimensions(left["payload"], right["payload"])
            title_similarity = float(dimensions["title"])
            semantic_similarity = float(dimensions["semantic_composite"])
            if title_similarity < similar_title_threshold and semantic_similarity < max(0.82, similar_title_threshold):
                continue
            actions.append(
                _action(
                    "merge-cards",
                    left["relative_path"],
                    entry_id=left["entry_id"],
                    related_path=right["relative_path"],
                    related_entry_id=right["entry_id"],
                    similarity=max(title_similarity, semantic_similarity),
                    similarity_dimensions=dimensions,
                    risk="medium",
                    apply_supported=False,
                    reason="Scenario, action, prediction, route, evidence, and title similarity scores require an explicit merge-or-keep review.",
                )
            )

    actions.extend(_skill_version_actions(records))
    _attach_merge_split_packets(
        actions,
        records,
        organization_id=organization_id,
        source_generation_id=str(validation.get("source_generation_id") or ""),
    )
    card_decisions = _card_decisions(records, actions)
    counts: dict[str, int] = {}
    for action in actions:
        action_type = str(action.get("action_type") or "")
        counts[action_type] = counts.get(action_type, 0) + 1

    return {
        "ok": True,
        "organization_id": organization_id,
        "generated_at": utc_now_iso(),
        "maintenance_model": ORGANIZATION_EXCHANGE_SLEEP_MODEL,
        "lane_policy": {
            "incoming_lane": "kb/imports",
            "exchange_surface": "kb/main",
            "current_layout_only": True,
            "local_download_primary_path": "kb/main",
            "local_download_excluded_paths": ["kb/imports"],
            "contribution_writes": ["kb/imports"],
            "maintenance_moves_reviewed_cards_to": "kb/main",
        },
        "card_count": len(records),
        "card_decisions": card_decisions,
        "card_decision_count": len(card_decisions),
        "actions": actions,
        "counts": counts,
    }


def organization_cleanup_audit_path(org_root: Path) -> Path:
    return Path(org_root) / ORG_CLEANUP_AUDIT_RELATIVE_PATH


def _append_audit(org_root: Path, event: dict[str, Any]) -> None:
    append_jsonl(organization_cleanup_audit_path(org_root), event)


def _safe_target_path(org_root: Path, target_path: str) -> Path | None:
    text = str(target_path or "").strip().replace("\\", "/")
    if not text or text.startswith("/") or ".." in Path(text).parts:
        return None
    target = Path(org_root) / text
    try:
        target.resolve().relative_to(Path(org_root).resolve())
    except ValueError:
        return None
    return target


# Every accepted change is compiled into a complete schema-2 source generation
# so card projection, catalog, model, and mesh stay atomic.
def apply_organization_cleanup_proposal(
    org_root: Path,
    proposal: dict[str, Any],
    *,
    allow_actions: set[str] | None = None,
    allow_action_ids: set[str] | None = None,
    allow_trusted: bool = False,
    allow_delete: bool = False,
    allow_promote: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Apply selected actions by rebuilding one complete current generation."""

    org_root = Path(org_root)
    validation = validate_organization_repo(org_root)
    if not validation.get("ok"):
        return {"ok": False, "dry_run": dry_run, "applied": [], "skipped": [], "errors": list(validation.get("errors") or [])}
    catalog = load_current_catalog(org_root)
    allowed = allow_actions or LOW_RISK_APPLY_ACTIONS
    selected = {str(item) for item in allow_action_ids} if allow_action_ids is not None else None
    cards: dict[str, dict[str, Any]] = {}
    for row in catalog.get("cards") or []:
        if not isinstance(row, dict):
            continue
        path = str(row.get("source_path") or "")
        cards[path] = authoring_card_from_projection(load_yaml_file(org_root / path))
    applied: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    tombstones = [dict(item) for item in (catalog.get("tombstones") or []) if isinstance(item, dict)]
    removed_imports: set[str] = set()
    now = utc_now_iso()

    def skip(action_id: str, action_type: str, reason: str, target_path: str = "") -> None:
        skipped.append({"action_id": action_id, "action_type": action_type, "reason": reason, "target_path": target_path})

    for action in proposal.get("actions") or []:
        if not isinstance(action, dict):
            continue
        action_id = str(action.get("action_id") or "")
        action_type = str(action.get("action_type") or "")
        target_path = str(action.get("target_path") or "").replace("\\", "/")
        if selected is not None and action_id not in selected:
            skip(action_id, action_type, "action was not selected by organization Sleep", target_path)
            continue
        if action_type not in allowed:
            skip(action_id, action_type, "action type is not allowed", target_path)
            continue
        if target_path.startswith("kb/main/") and not allow_trusted:
            skip(action_id, action_type, "main card apply requires allow_trusted", target_path)
            continue
        if action_type in {"merge-cards", "split-card"}:
            packet = action.get("apply_packet") if isinstance(action.get("apply_packet"), dict) else {}
            if packet.get("schema_version") != APPLY_PACKET_SCHEMA or str(packet.get("packet_digest") or "") != _packet_digest(packet):
                skip(action_id, action_type, "apply packet is missing or its digest is invalid", target_path)
                continue
            if packet.get("review_status") != "ready":
                skip(action_id, action_type, "apply packet is blocked until its declared evidence roles are satisfied", target_path)
                continue
            current_inputs: list[dict[str, Any]] = []
            for item in packet.get("inputs") or []:
                if not isinstance(item, dict):
                    continue
                path = str(item.get("path") or "")
                payload = cards.get(path)
                if payload is None:
                    break
                current_inputs.append({"path": path, "content_hash": card_exchange_hash(payload)})
            current_fingerprint = "sha256:" + canonical_digest(current_inputs)
            expected_rows = [
                {"path": str(item.get("path") or ""), "content_hash": str(item.get("content_hash") or "")}
                for item in packet.get("inputs") or [] if isinstance(item, dict)
            ]
            expected_fingerprint = "sha256:" + canonical_digest(expected_rows)
            if current_fingerprint != expected_fingerprint:
                skip(action_id, action_type, "apply packet inputs changed and require reopen", target_path)
                continue
            output_paths: set[str] = set()
            for output in packet.get("outputs") or []:
                if not isinstance(output, dict):
                    continue
                path = str(output.get("target_path") or "")
                card = output.get("card") if isinstance(output.get("card"), dict) else {}
                if not path.startswith("kb/main/") or not card:
                    continue
                cards[path] = dict(card)
                output_paths.add(path)
            if not output_paths:
                skip(action_id, action_type, "apply packet has no complete current-card outputs", target_path)
                continue
            for item in packet.get("inputs") or []:
                if not isinstance(item, dict):
                    continue
                path = str(item.get("path") or "")
                if path not in output_paths:
                    retired = cards.pop(path, None)
                    tombstones.append(
                        {
                            "source_path": path,
                            "old_entry_id": str((retired or {}).get("id") or item.get("entry_id") or ""),
                            "disposition": "merged" if action_type == "merge-cards" else "split",
                            "packet_id": str(packet.get("packet_id") or ""),
                            "retained_entry_ids": [str(cards[path]["id"]) for path in sorted(output_paths)],
                        }
                    )
            applied.append({"action_id": action_id, "action_type": action_type, "target_path": target_path, "updated_path": sorted(output_paths)[0], "packet_id": packet.get("packet_id")})
            continue
        payload = cards.get(target_path)
        from_import = False
        if payload is None and target_path.startswith("kb/imports/"):
            target = _safe_target_path(org_root, target_path)
            if target is not None and target.is_file():
                raw = load_yaml_file(target)
                payload = dict(raw) if isinstance(raw, dict) else None
                from_import = payload is not None
        if payload is None:
            skip(action_id, action_type, "target path is missing or unsafe", target_path)
            continue
        if action_type in {"accept-import", "promote-card"}:
            if not allow_promote:
                skip(action_id, action_type, "main transfer requires allow_promote", target_path)
                continue
            proposed_path = str(action.get("proposed_path") or "").replace("\\", "/")
            if not proposed_path.startswith("kb/main/") or proposed_path in cards:
                skip(action_id, action_type, "main target path is missing, unsafe, or occupied", target_path)
                continue
            cards.pop(target_path, None)
            if from_import:
                removed_imports.add(target_path)
            payload["status"] = str(action.get("proposed_status") or ("trusted" if action_type == "promote-card" else "candidate"))
            if "proposed_confidence" in action:
                payload["confidence"] = max(0.0, min(1.0, safe_float(action.get("proposed_confidence"), _confidence(payload))))
            cleanup = payload.get("organization_cleanup") if isinstance(payload.get("organization_cleanup"), dict) else {}
            cleanup.update(
                {
                    "last_action_id": action_id,
                    "last_action_type": action_type,
                    "last_reason": str(action.get("reason") or ""),
                    "promoted_from": target_path,
                    "moved_to_main_from": target_path,
                    "updated_at": now,
                }
            )
            payload["organization_cleanup"] = cleanup
            cards[proposed_path] = payload
            applied.append({"action_id": action_id, "action_type": action_type, "target_path": target_path, "updated_path": proposed_path})
            continue
        if action_type == "delete-card":
            if not allow_delete:
                skip(action_id, action_type, "delete requires allow_delete", target_path)
                continue
            cards.pop(target_path, None)
            if from_import:
                removed_imports.add(target_path)
            tombstones.append({"source_path": target_path, "old_entry_id": str(payload.get("id") or ""), "disposition": "deleted", "action_id": action_id})
            applied.append({"action_id": action_id, "action_type": action_type, "target_path": target_path})
            continue
        if "proposed_status" in action:
            payload["status"] = str(action.get("proposed_status") or payload.get("status") or "candidate")
        if "proposed_confidence" in action:
            payload["confidence"] = max(0.0, min(1.0, safe_float(action.get("proposed_confidence"), _confidence(payload))))
        cleanup = payload.get("organization_cleanup") if isinstance(payload.get("organization_cleanup"), dict) else {}
        cleanup.update({"last_action_id": action_id, "last_action_type": action_type, "last_reason": str(action.get("reason") or ""), "updated_at": now})
        if action.get("duplicate_of"):
            cleanup["duplicate_of"] = str(action.get("duplicate_of") or "")
        payload["organization_cleanup"] = cleanup
        cards[target_path] = payload
        applied.append({"action_id": action_id, "action_type": action_type, "target_path": target_path})

    errors: list[str] = []
    changed_paths: list[str] = []
    if applied and not dry_run:
        try:
            with tempfile.TemporaryDirectory(prefix="khaos-org-apply-") as temporary:
                staged = Path(temporary) / "staged"
                materialize_current_source(
                    staged,
                    organization_id=str(validation.get("organization_id") or ""),
                    cards=sorted(cards.items()),
                    source_commit=str(catalog.get("source_commit") or validation.get("commit") or ""),
                    tombstones=tombstones,
                )
                imports_source = org_root / "kb" / "imports"
                if imports_source.exists():
                    shutil.copytree(imports_source, staged / "kb" / "imports", dirs_exist_ok=True)
                for relative in removed_imports:
                    imported = staged / relative
                    imported.unlink(missing_ok=True)
                backup = Path(temporary) / "backup"
                for relative in ("kb/main", "kb/logicguard", "kb/organization_catalog.json", "kb/imports", "khaos_org_kb.yaml"):
                    source = org_root / relative
                    target = backup / relative
                    if source.is_dir():
                        shutil.copytree(source, target)
                    elif source.is_file():
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(source, target)
                try:
                    for relative in ("kb/main", "kb/logicguard"):
                        target = org_root / relative
                        if target.exists():
                            shutil.rmtree(target)
                        shutil.copytree(staged / relative, target)
                    for relative in ("kb/organization_catalog.json", "khaos_org_kb.yaml"):
                        target = org_root / relative
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(staged / relative, target)
                    if removed_imports:
                        target = org_root / "kb" / "imports"
                        if target.exists():
                            shutil.rmtree(target)
                        shutil.copytree(staged / "kb" / "imports", target)
                    post = validate_organization_repo(org_root)
                    if not post.get("ok"):
                        raise RuntimeError("; ".join(post.get("errors") or ["post-apply current source validation failed"]))
                except Exception:
                    for relative in ("kb/main", "kb/logicguard", "kb/imports"):
                        target = org_root / relative
                        if target.exists():
                            shutil.rmtree(target)
                        source = backup / relative
                        if source.exists():
                            shutil.copytree(source, target)
                    for relative in ("kb/organization_catalog.json", "khaos_org_kb.yaml"):
                        source = backup / relative
                        if source.is_file():
                            shutil.copy2(source, org_root / relative)
                    raise
            for item in applied:
                _append_audit(org_root, {"event_type": "organization-cleanup-applied", **item, "created_at": now})
            rebuilt_catalog = load_current_catalog(org_root)
            changed_paths = sorted(
                {
                    "khaos_org_kb.yaml",
                    "kb/organization_catalog.json",
                    "maintenance/cleanup_audit.jsonl",
                    *removed_imports,
                    *(
                        str(row.get(field) or "")
                        for row in (rebuilt_catalog.get("cards") or [])
                        if isinstance(row, dict)
                        for field in ("source_path", "model_path", "mesh_path", "projection_path", "bundle_path")
                    ),
                }
            )
        except Exception as exc:
            errors.append(f"transactional organization apply failed: {type(exc).__name__}: {exc}")
            applied = []
    return {
        "ok": not errors,
        "dry_run": dry_run,
        "applied_count": len(applied),
        "skipped_count": len(skipped),
        "applied_action_ids": [str(item.get("action_id") or "") for item in applied],
        "skipped_action_ids": [str(item.get("action_id") or "") for item in skipped],
        "applied": applied,
        "skipped": skipped,
        "errors": errors,
        "changed_paths": changed_paths,
        "audit_path": str(organization_cleanup_audit_path(org_root)),
    }
