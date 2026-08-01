from __future__ import annotations

import json
import os
from pathlib import Path
import re
from typing import Any, Iterable

from local_kb.common import (
    normalize_string_list,
    normalize_text,
    parse_route_segments,
    safe_float,
    tokenize,
)
from local_kb.adoption import card_exchange_hash, dedupe_local_entries_by_exchange_hash
from local_kb.models import Entry
from local_kb.logicguard_models import ExactBindingError, read_bound_argument_context, read_foreign_argument_context
from local_kb.model_projection import binding_from_projection
from local_kb.source_labels import card_source_summary


TERMINAL_RETRIEVAL_STATUSES = {
    "merged",
    "rejected",
    "superseded",
    "parked",
    "retired",
    "deprecated",
    "history_only",
}
RETRIEVAL_POLICY_VERSION = 3
TRUSTED_MIN_RELEVANCE_SCORE = 3.0
CANDIDATE_MIN_RELEVANCE_SCORE = 6.0
TRUSTED_MIN_CONFIDENCE = 0.25
CANDIDATE_MIN_CONFIDENCE = 0.40
MODEL_NEIGHBOR_SCORE_FACTOR = 0.20
MODEL_IMPORTANCE_SCORE_WEIGHT = 1.5
MODEL_RELATION_SCORE_WEIGHT = 0.75
MODEL_MEMBERSHIP_SCORE_WEIGHT = 0.5
MODEL_ROOT_ROLE_SCORE = 0.5


def _stable_ref(prefix: str, payload: Any) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    import hashlib

    return f"{prefix}:{hashlib.sha256(encoded).hexdigest()[:32]}"


def _attach_result_identity(entry: Entry) -> None:
    source_kind = (
        "organization" if entry.source.get("kind") == "organization" else "local"
    )
    source_id = (
        str(entry.source.get("organization_id") or entry.source.get("source_id") or "")
        if source_kind == "organization"
        else "local"
    )
    entry_id = str(entry.data.get("id") or entry.path.stem)
    authority = (
        {
            "snapshot_generation": str(entry.source.get("snapshot_generation") or ""),
            "snapshot_manifest_digest": str(
                entry.source.get("snapshot_manifest_digest") or ""
            ),
            "source_commit": str(entry.source.get("source_commit") or ""),
            "source_path": str(entry.source.get("path") or ""),
            "bundle_digest": str(
                (entry.source.get("logicguard_bundle") or {}).get("bundle_digest")
                if isinstance(entry.source.get("logicguard_bundle"), dict)
                else ""
            ),
        }
        if source_kind == "organization"
        else {
            "index_generation": int(entry.source.get("active_index_generation") or 0),
            "index_digest": str(entry.source.get("active_index_digest") or ""),
            "path": str(entry.source.get("path") or entry.path),
        }
    )
    knowledge_ref = _stable_ref(
        "knowledge",
        {"source_kind": source_kind, "source_id": source_id, "entry_id": entry_id},
    )
    result_ref = _stable_ref(
        "result",
        {
            "knowledge_ref": knowledge_ref,
            "authority": authority,
            "exchange_hash": card_exchange_hash(entry.data),
            "logicguard_binding": (entry.source.get("logicguard") or {}).get("binding", {}),
        },
    )
    entry.source.update(
        {
            "source_kind": source_kind,
            "source_id": source_id,
            "knowledge_ref": knowledge_ref,
            "result_ref": result_ref,
            "result_authority": authority,
        }
    )


def _global_rank(candidates: list[Entry], top_k: int) -> list[Entry]:
    """Rank all sources together while keeping local authority first on ID conflicts."""

    by_entry_id: dict[str, list[Entry]] = {}
    for entry in candidates:
        by_entry_id.setdefault(str(entry.data.get("id") or entry.path.stem), []).append(entry)
    groups: list[tuple[float, str, list[Entry]]] = []
    for entry_id, members in by_entry_id.items():
        if len(members) == 1:
            member = members[0]
            groups.append((member.score, str(member.source.get("result_ref") or ""), members))
            continue
        local_members = [
            item for item in members if str(item.source.get("source_kind") or "") == "local"
        ]
        conflict = {
            "entry_id": entry_id,
            "kind": "same-entry-id-different-content",
            "local_primary": bool(local_members),
            "alternatives": [
                str(item.source.get("result_ref") or "") for item in members
            ],
        }
        for member in members:
            member.source["source_conflict"] = {
                **conflict,
                "role": "primary" if member in local_members else "alternative",
            }
        ordered_members = sorted(
            members,
            key=lambda item: (
                0 if item in local_members else 1,
                -item.score,
                str(item.source.get("source_id") or ""),
            ),
        )
        groups.append((max(item.score for item in members), f"conflict:{entry_id}", ordered_members))
    groups.sort(key=lambda item: (-item[0], item[1]))
    ranked = [member for _score, _key, members in groups for member in members]
    return ranked[: max(0, int(top_k))]


def longest_common_prefix(left: list[str], right: list[str]) -> int:
    count = 0
    for left_item, right_item in zip(left, right):
        if left_item != right_item:
            break
        count += 1
    return count


def unique_overlap(left: Iterable[str], right: Iterable[str]) -> int:
    return len(set(left) & set(right))


def get_guidance(data: dict[str, Any]) -> str:
    return normalize_text(data.get("use", {}).get("guidance"))


def get_predicted_result(data: dict[str, Any]) -> str:
    return normalize_text(data.get("predict", {}).get("expected_result"))


def get_body_text(data: dict[str, Any]) -> str:
    return " ".join(
        part
        for part in [
            normalize_text(data.get("if")),
            normalize_text(data.get("action")),
            normalize_text(data.get("predict")),
            normalize_text(data.get("use")),
            normalize_text(data.get("source")),
            normalize_text(data.get("i18n")),
        ]
        if part
    )


def score_entry(
    entry: Entry,
    query_tokens: list[str],
    path_hint_segments: list[str],
    *,
    allow_untrusted_candidates: bool = False,
) -> float:
    data = entry.data
    title_tokens = tokenize(normalize_text(data.get("title", "")))
    tag_tokens = tokenize(normalize_text(data.get("tags", [])))
    trigger_tokens = tokenize(normalize_text(data.get("trigger_keywords", [])))
    body_tokens = tokenize(get_body_text(data))
    confidence = safe_float(data.get("confidence", 0.5) or 0.5, default=0.5)
    status = str(data.get("status", "candidate")).lower()

    if status in TERMINAL_RETRIEVAL_STATUSES:
        return 0.0
    if status == "candidate":
        if not allow_untrusted_candidates and not bool(data.get("retrieval_eligible", False)):
            return 0.0
        # Candidate knowledge can help bounded internal comparisons, but it
        # never receives trusted authority and its confidence contribution is
        # capped.  The active-index boundary decides whether it may be served.
        confidence = min(confidence, 0.65)
        if confidence < CANDIDATE_MIN_CONFIDENCE:
            return 0.0
    elif status == "trusted" and confidence < TRUSTED_MIN_CONFIDENCE:
        return 0.0

    domain_path = parse_route_segments(data.get("domain_path", []))
    cross_index_segments = parse_route_segments(data.get("cross_index", []))

    relevance_score = 0.0
    if path_hint_segments:
        relevance_score += longest_common_prefix(path_hint_segments, domain_path) * 8.0
        relevance_score += unique_overlap(path_hint_segments, domain_path) * 5.0
        relevance_score += unique_overlap(path_hint_segments, cross_index_segments) * 4.0

    relevance_score += unique_overlap(query_tokens, title_tokens) * 3.0
    relevance_score += unique_overlap(query_tokens, tag_tokens) * 5.0
    relevance_score += unique_overlap(query_tokens, trigger_tokens) * 4.0
    relevance_score += unique_overlap(query_tokens, body_tokens) * 1.0

    if relevance_score <= 0:
        return 0.0

    score = relevance_score + confidence * 2.0
    if status == "trusted":
        score += 4.0
    elif status == "candidate":
        score -= 1.0
    threshold = (
        CANDIDATE_MIN_RELEVANCE_SCORE
        if status == "candidate"
        else TRUSTED_MIN_RELEVANCE_SCORE
    )
    if score < threshold:
        return 0.0
    return score


def _direct_identifier_match(query: str, entry_id: str) -> bool:
    normalized_query = str(query or "").strip().casefold()
    normalized_id = str(entry_id or "").strip().casefold()
    if not normalized_query or not normalized_id:
        return False
    if normalized_query in {normalized_id, f"id:{normalized_id}", f"[{normalized_id}]"}:
        return True
    return bool(
        re.search(
            rf"(?<![\w-]){re.escape(normalized_id)}(?![\w-])",
            normalized_query,
        )
    )


def _direct_logicguard_identifier_match(
    query: str,
    data: dict[str, Any],
) -> tuple[bool, str]:
    normalized_query = " ".join(str(query or "").strip().casefold().split())
    if not normalized_query:
        return False, ""
    model_id = str(data.get("logicguard_model_id") or "").casefold()
    node_id = str(data.get("logicguard_node_id") or "").casefold()
    block_id = str(data.get("logicguard_block_id") or "").casefold()
    revision_id = str(data.get("logicguard_revision_id") or "").casefold()
    mesh_id = str(data.get("logicguard_mesh_id") or "").casefold()
    mesh_revision_id = str(
        data.get("logicguard_mesh_revision_id") or ""
    ).casefold()
    exact_values = (
        ("model", model_id),
        ("revision", revision_id),
        ("mesh", mesh_id),
        ("mesh-revision", mesh_revision_id),
    )
    for kind, value in exact_values:
        if value and normalized_query in {value, f"{kind}:{value}"}:
            return True, kind
    if model_id and node_id and normalized_query in {
        f"node:{model_id}#{node_id}",
        f"node:{model_id}/{node_id}",
        f"model:{model_id} node:{node_id}",
    }:
        return True, "qualified-node"
    if model_id and block_id and normalized_query in {
        f"block:{model_id}#{block_id}",
        f"block:{model_id}/{block_id}",
        f"model:{model_id} block:{block_id}",
    }:
        return True, "qualified-block"
    return False, ""


def _model_ranking_signals(
    context: dict[str, Any],
    *,
    discovery: str,
    base_score: float,
    distance: int,
    relation_types: Iterable[str] = (),
    direct_identifier_kind: str = "",
) -> dict[str, Any]:
    binding = context.get("binding") if isinstance(context.get("binding"), dict) else {}
    root_node_id = str(binding.get("logicguard_node_id") or "")
    nodes = [item for item in context.get("nodes", []) if isinstance(item, dict)]
    root_node = next(
        (item for item in nodes if str(item.get("id") or "") == root_node_id),
        {},
    )
    root_importance = safe_float(root_node.get("importance"), default=0.0)
    root_role = str(root_node.get("role") or "")
    normalized_relations = sorted(
        {str(item).lower() for item in relation_types if str(item)}
    )
    support_relations = sum(
        item in {"supports", "derives", "refines", "contextualizes"}
        for item in normalized_relations
    )
    opposition_relations = sum(
        item in {"attacks", "rebuts", "undercuts", "contradicts"}
        for item in normalized_relations
    )
    neighborhood = (
        context.get("neighborhood")
        if isinstance(context.get("neighborhood"), dict)
        else {}
    )
    membership_count = len(
        [item for item in neighborhood.get("memberships", []) if isinstance(item, dict)]
    )
    importance_adjustment = round(
        max(0.0, min(1.0, root_importance)) * MODEL_IMPORTANCE_SCORE_WEIGHT,
        6,
    )
    role_adjustment = MODEL_ROOT_ROLE_SCORE if root_role == "predicted_result" else 0.0
    relation_adjustment = round(
        (support_relations + opposition_relations) * MODEL_RELATION_SCORE_WEIGHT,
        6,
    )
    membership_adjustment = round(
        membership_count * MODEL_MEMBERSHIP_SCORE_WEIGHT,
        6,
    )
    adjustment = round(
        importance_adjustment
        + role_adjustment
        + relation_adjustment
        + membership_adjustment,
        6,
    )
    return {
        "discovery": discovery,
        "base_score": round(float(base_score), 6),
        "model_adjustment": adjustment,
        "final_score": round(float(base_score) + adjustment, 6),
        "distance": max(0, int(distance)),
        "root_role": root_role,
        "root_importance": root_importance,
        "relation_types": normalized_relations,
        "support_relation_count": support_relations,
        "opposition_relation_count": opposition_relations,
        "membership_count": membership_count,
        "open_gap_count": len(context.get("open_role_gaps") or []),
        "direct_identifier_kind": direct_identifier_kind,
        "claim_boundary": (
            "Model signals rerank a lexical or grounded-mesh candidate; they never admit an unrelated model."
        ),
    }


def _entry_can_surface(
    entry: Entry,
    *,
    allow_untrusted_candidates: bool = False,
) -> bool:
    status = str(entry.data.get("status") or "candidate").lower()
    if status in TERMINAL_RETRIEVAL_STATUSES:
        return False
    if status == "candidate":
        return allow_untrusted_candidates or bool(entry.data.get("retrieval_eligible", False))
    return status == "trusted"


def search_loaded_entries(
    entries: list[Entry],
    query: str,
    path_hint: str = "",
    top_k: int = 5,
    *,
    allow_untrusted_candidates: bool = False,
) -> list[Entry]:
    query_tokens = tokenize(query)
    path_hint_segments = parse_route_segments(path_hint)
    for entry in entries:
        entry.score = score_entry(
            entry,
            query_tokens,
            path_hint_segments,
            allow_untrusted_candidates=allow_untrusted_candidates,
        )
        if _entry_can_surface(
            entry,
            allow_untrusted_candidates=allow_untrusted_candidates,
        ) and _direct_identifier_match(
            query, str(entry.data.get("id") or "")
        ):
            entry.score = max(entry.score, 1000.0)
    primary = [
        entry
        for entry in entries
        if entry.score > 0
        and _entry_can_surface(
            entry,
            allow_untrusted_candidates=allow_untrusted_candidates,
        )
    ]
    ranked = [
        entry
        for entry in sorted(
            entries,
            key=lambda item: (-item.score, str(item.data.get("id") or "")),
        )
        if entry.score > 0
        and _entry_can_surface(
            entry,
            allow_untrusted_candidates=allow_untrusted_candidates,
        )
    ]
    return ranked[:top_k]


def search_model_bound_entries(
    repo_root: Path,
    entries: list[Entry],
    *,
    query: str,
    path_hint: str = "",
    top_k: int = 5,
) -> list[Entry]:
    """Rank exact projections, then expand only through grounded ModelMesh paths."""

    lexical = search_loaded_entries(
        entries,
        query=query,
        path_hint=path_hint,
        top_k=max(1, top_k),
    )
    direct_model_entries: list[Entry] = []
    direct_identifier_kinds: dict[tuple[str, str], str] = {}
    for entry in entries:
        matched, identifier_kind = _direct_logicguard_identifier_match(
            query,
            entry.data,
        )
        if not matched or not _entry_can_surface(entry):
            continue
        entry.score = max(entry.score, 1000.0)
        binding = binding_from_projection(entry.data)
        direct_identifier_kinds[(binding.model_id, binding.revision_id)] = identifier_kind
        direct_model_entries.append(entry)
    lexical_by_key: dict[tuple[str, str], Entry] = {}
    for entry in [*lexical, *direct_model_entries]:
        binding = binding_from_projection(entry.data)
        lexical_by_key[(binding.model_id, binding.revision_id)] = entry
    lexical = sorted(
        lexical_by_key.values(),
        key=lambda item: (-item.score, str(item.data.get("id") or "")),
    )[: max(1, top_k)]
    primary_keys = {
        (
            binding_from_projection(entry.data).model_id,
            binding_from_projection(entry.data).revision_id,
        )
        for entry in lexical
    }
    by_model_revision: dict[tuple[str, str], Entry] = {}
    for entry in entries:
        binding = binding_from_projection(entry.data)
        by_model_revision[(binding.model_id, binding.revision_id)] = entry

    selected: dict[tuple[str, str], Entry] = {}
    contexts: dict[tuple[str, str], dict[str, Any]] = {}
    for entry in lexical:
        binding = binding_from_projection(entry.data)
        key = (binding.model_id, binding.revision_id)
        context = read_bound_argument_context(repo_root, binding)
        contexts[key] = context
        selected[key] = entry
        entry.source["logicguard_discovery"] = "lexical-model-entry"
        primary_signals = _model_ranking_signals(
            context,
            discovery="lexical-model-entry",
            base_score=entry.score,
            distance=0,
            direct_identifier_kind=direct_identifier_kinds.get(key, ""),
        )
        entry.score = float(primary_signals["final_score"])
        entry.source["logicguard_ranking"] = primary_signals
        for pin in context.get("neighborhood", {}).get("model_pins", []):
            if not isinstance(pin, dict):
                continue
            neighbor_key = (str(pin.get("model_id") or ""), str(pin.get("revision") or ""))
            if neighbor_key == key:
                continue
            # A model already admitted by the query remains a primary result;
            # another primary model's neighborhood must not overwrite its
            # discovery/ranking evidence.
            if neighbor_key in primary_keys:
                continue
            neighbor = by_model_revision.get(neighbor_key)
            if neighbor is None:
                continue
            cross_edges = [
                item
                for item in context.get("neighborhood", {}).get("cross_edges", [])
                if isinstance(item, dict)
                and {
                    str(item.get("source", {}).get("model_id") or ""),
                    str(item.get("target", {}).get("model_id") or ""),
                }
                == {binding.model_id, neighbor_key[0]}
            ]
            neighbor_context = contexts.get(neighbor_key)
            if neighbor_context is None:
                neighbor_context = read_bound_argument_context(
                    repo_root,
                    binding_from_projection(neighbor.data),
                )
                contexts[neighbor_key] = neighbor_context
            neighbor_base = round(
                entry.score * MODEL_NEIGHBOR_SCORE_FACTOR,
                6,
            )
            neighbor_signals = _model_ranking_signals(
                neighbor_context,
                discovery="grounded-model-neighborhood",
                base_score=neighbor_base,
                distance=1,
                relation_types=(item.get("type") for item in cross_edges),
            )
            neighbor.score = max(neighbor.score, float(neighbor_signals["final_score"]))
            neighbor.source["logicguard_discovery"] = "grounded-model-neighborhood"
            neighbor.source["logicguard_discovered_from"] = str(entry.data.get("id") or "")
            neighbor.source["logicguard_ranking"] = neighbor_signals
            selected[neighbor_key] = neighbor

    ranked = sorted(
        selected.values(),
        key=lambda item: (-item.score, str(item.data.get("id") or "")),
    )[:top_k]
    for entry in ranked:
        binding = binding_from_projection(entry.data)
        key = (binding.model_id, binding.revision_id)
        context = contexts.get(key)
        if context is None:
            context = read_bound_argument_context(repo_root, binding)
            contexts[key] = context
        entry.source["logicguard"] = context
    return ranked


def _foreign_bundle_for_entry(entry: Entry) -> dict[str, Any]:
    metadata = entry.source.get("logicguard_bundle") if isinstance(entry.source.get("logicguard_bundle"), dict) else {}
    snapshot_root = Path(str(entry.source.get("snapshot_path") or ""))
    if not snapshot_root:
        raise ExactBindingError("Organization entry has no immutable snapshot root")
    def read(relative: str) -> dict[str, Any]:
        path = snapshot_root / str(relative or "")
        if not path.is_file():
            raise ExactBindingError(f"Organization LogicGuard bundle file is missing: {relative}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ExactBindingError(f"Organization LogicGuard bundle file is invalid: {relative}") from exc
        if not isinstance(payload, dict):
            raise ExactBindingError(f"Organization LogicGuard bundle file is not an object: {relative}")
        return payload
    model = read(str(metadata.get("model_path") or ""))
    mesh = read(str(metadata.get("mesh_path") or ""))
    projection = read(str(metadata.get("projection_path") or ""))
    binding = dict(metadata.get("binding") or {})
    return {
        "schema_version": "khaos-brain.organization-logicguard-bundle.v1",
        "organization_id": str(entry.source.get("organization_id") or ""),
        "entry_id": str(entry.data.get("id") or ""),
        "generation_id": str(entry.source.get("snapshot_generation") or ""),
        "binding": binding,
        "model": model,
        "mesh": mesh,
        "projection": projection,
        "model_digest": str(metadata.get("model_digest") or ""),
        "mesh_digest": str(metadata.get("mesh_digest") or ""),
        "projection_digest": str(metadata.get("projection_digest") or ""),
        "bundle_digest": str(metadata.get("bundle_digest") or ""),
    }


def search_foreign_model_bound_entries(
    entries: list[Entry],
    *,
    query: str,
    path_hint: str = "",
    top_k: int = 5,
) -> list[Entry]:
    """Rank organization entries only after exact portable-bundle validation."""

    lexical = search_loaded_entries(
        entries,
        query=query,
        path_hint=path_hint,
        top_k=max(1, top_k),
        allow_untrusted_candidates=True,
    )
    selected: list[Entry] = []
    for entry in lexical:
        try:
            bundle = _foreign_bundle_for_entry(entry)
            context = read_foreign_argument_context(
                bundle,
                expected_binding=(entry.source.get("logicguard_bundle") or {}).get("binding")
                if isinstance(entry.source.get("logicguard_bundle"), dict)
                else None,
            )
        except (ExactBindingError, KeyError, ValueError, TypeError) as exc:
            entry.source["logicguard_error"] = f"{type(exc).__name__}: {exc}"
            continue
        entry.source["logicguard"] = context
        entry.source["logicguard_discovery"] = "foreign-snapshot-model-entry"
        entry.source["logicguard_ranking"] = _model_ranking_signals(
            context,
            discovery="foreign-snapshot-model-entry",
            base_score=entry.score,
            distance=0,
        )
        entry.score = float(entry.source["logicguard_ranking"]["final_score"])
        selected.append(entry)
    return sorted(selected, key=lambda item: (-item.score, str(item.data.get("id") or "")))[:top_k]


def search_entries(
    repo_root: Path,
    query: str,
    path_hint: str = "",
    top_k: int = 5,
    *,
    record_receipt: bool = False,
) -> list[Entry]:
    results, _receipt = search_with_receipt(
        repo_root,
        query=query,
        path_hint=path_hint,
        top_k=top_k,
        record_receipt=record_receipt,
    )
    return results


def search_with_receipt(
    repo_root: Path,
    query: str,
    path_hint: str = "",
    top_k: int = 5,
    *,
    record_receipt: bool = True,
) -> tuple[list[Entry], dict[str, Any]]:
    result = search_multi_source_result(
        repo_root,
        query=query,
        path_hint=path_hint,
        top_k=top_k,
        organization_sources=[],
        record_receipt=record_receipt,
    )
    return result["results"], dict(result.get("retrieval_receipt") or {})


def search_multi_source_entries(
    repo_root: Path,
    query: str,
    path_hint: str = "",
    top_k: int = 5,
    organization_sources: list[dict[str, Any]] | None = None,
    *,
    record_receipt: bool = True,
) -> list[Entry]:
    return search_multi_source_result(
        repo_root,
        query=query,
        path_hint=path_hint,
        top_k=top_k,
        organization_sources=organization_sources,
        record_receipt=record_receipt,
    )["results"]


def search_multi_source_result(
    repo_root: Path,
    query: str,
    path_hint: str = "",
    top_k: int = 5,
    organization_sources: list[dict[str, Any]] | None = None,
    *,
    record_receipt: bool = True,
) -> dict[str, Any]:
    """Return local and organization results plus explicit source status.

    Organization retrieval is snapshot-only.  A missing or invalid snapshot
    never downgrades to a mutable mirror; local results remain usable and the
    source status explains why foreign cards were not returned.
    """
    from local_kb.active_index import load_active_entries
    from local_kb.lifecycle import (
        load_current_foreign_calibration,
        record_retrieval_receipt,
    )
    from local_kb.maintenance_standard import maintenance_standard_is_active

    if not maintenance_standard_is_active(repo_root):
        raise RuntimeError(
            "Multi-source retrieval is unavailable because the current Chaos Brain "
            "maintenance standard is not committed. Run the versioned upgrade."
        )
    indexed_entries, index = load_active_entries(repo_root)
    local_entries = dedupe_local_entries_by_exchange_hash(indexed_entries)
    for entry in local_entries:
        entry.source["active_index_generation"] = int(index.get("generation") or 0)
        entry.source["active_index_digest"] = str(index.get("content_digest") or "")
    local_results = search_model_bound_entries(
        repo_root,
        local_entries,
        query=query,
        path_hint=path_hint,
        top_k=max(1, len(local_entries)),
    )
    local_exchange_hashes = {card_exchange_hash(entry.data) for entry in local_entries}
    organization_results: list[Entry] = []
    organization_status: list[dict[str, Any]] = []
    for source in organization_sources or []:
        organization_id = str(source.get("organization_id") or source.get("id") or "").strip()
        if not organization_id:
            continue
        from local_kb.store import load_current_organization_entries
        status_row = {
            "source_kind": "organization",
            "source_id": organization_id,
            "organization_id": organization_id,
            "source_repo": str(source.get("source_repo") or source.get("repo_url") or ""),
            "status": "unavailable",
            "snapshot_generation": "",
            "snapshot_manifest_digest": "",
            "returned_count": 0,
        }
        try:
            entries = load_current_organization_entries(
                repo_root,
                organization_id,
                source_repo=str(source.get("source_repo") or source.get("repo_url") or ""),
                source_commit=str(source.get("source_commit") or ""),
            )
        except RuntimeError as exc:
            status_row["reason"] = str(exc)
            organization_status.append(status_row)
            continue
        status_row.update({
            "status": "current",
            "snapshot_generation": str(entries[0].source.get("snapshot_generation") or "") if entries else "",
            "snapshot_manifest_digest": str(entries[0].source.get("snapshot_manifest_digest") or "") if entries else "",
        })
        eligible = search_foreign_model_bound_entries(
            entries,
            query=query,
            path_hint=path_hint,
            top_k=max(1, len(entries)),
        )
        status_row["eligible_count"] = len(eligible)
        for entry in eligible:
            if card_exchange_hash(entry.data) in local_exchange_hashes:
                continue
            organization_results.append(entry)
        organization_status.append(status_row)
    candidates = [*local_results, *organization_results]
    for entry in candidates:
        _attach_result_identity(entry)
    foreign_calibration = (
        load_current_foreign_calibration(repo_root).get("foreign_entries", {})
        if organization_results
        else {}
    )
    calibrated: list[Entry] = []
    for entry in candidates:
        if str(entry.source.get("source_kind") or "") != "organization":
            calibrated.append(entry)
            continue
        state = (
            foreign_calibration.get(str(entry.source.get("knowledge_ref") or ""), {})
            if isinstance(foreign_calibration, dict)
            else {}
        )
        if isinstance(state, dict) and not bool(state.get("retrieval_eligible", True)):
            continue
        adjustment = float(state.get("score_adjustment") or 0.0) if isinstance(state, dict) else 0.0
        entry.source["local_foreign_calibration"] = dict(state) if isinstance(state, dict) else {}
        entry.source["pre_calibration_score"] = entry.score
        entry.score += adjustment
        calibrated.append(entry)
    results = _global_rank(calibrated, top_k)
    returned_by_source: dict[str, int] = {}
    for entry in results:
        source_id = str(entry.source.get("source_id") or "")
        returned_by_source[source_id] = returned_by_source.get(source_id, 0) + 1
    for status_row in organization_status:
        status_row["returned_count"] = returned_by_source.get(
            str(status_row.get("organization_id") or ""), 0
        )
    source_states = [
        {
            "source_kind": "local",
            "source_id": "local",
            "status": "current",
            "index_generation": int(index.get("generation") or 0),
            "index_digest": str(index.get("content_digest") or ""),
            "eligible_count": len(local_results),
            "returned_count": returned_by_source.get("local", 0),
        },
        *[dict(item) for item in organization_status],
    ]
    receipt: dict[str, Any] = {}
    if record_receipt:
        receipt = record_retrieval_receipt(
            repo_root,
            query=query,
            path_hint=path_hint,
            ranked_entries=[
                {
                    "knowledge_ref": str(entry.source.get("knowledge_ref") or ""),
                    "result_ref": str(entry.source.get("result_ref") or ""),
                    "source_kind": str(entry.source.get("source_kind") or ""),
                    "source_id": str(entry.source.get("source_id") or ""),
                    "entry_id": str(entry.data.get("id") or ""),
                    "rank": rank,
                    "score": entry.score,
                    "status": str(entry.data.get("status") or ""),
                    "authority": dict(entry.source.get("result_authority") or {}),
                    "logicguard_binding": dict(
                        entry.source.get("logicguard", {}).get("binding") or {}
                    ),
                    "materialization_fingerprint": str(
                        entry.source.get("logicguard", {})
                        .get("neighborhood", {})
                        .get("materialization_fingerprint")
                        or ""
                    ),
                    "logicguard_ranking": dict(entry.source.get("logicguard_ranking") or {}),
                    "source_conflict": dict(entry.source.get("source_conflict") or {}),
                }
                for rank, entry in enumerate(results, start=1)
            ],
            source_states=source_states,
            thresholds={
                "trusted_minimum_score": TRUSTED_MIN_RELEVANCE_SCORE,
                "candidate_minimum_score": CANDIDATE_MIN_RELEVANCE_SCORE,
                "trusted_minimum_confidence": TRUSTED_MIN_CONFIDENCE,
                "candidate_minimum_confidence": CANDIDATE_MIN_CONFIDENCE,
                "top_k": top_k,
                "policy_version": RETRIEVAL_POLICY_VERSION,
            },
        )
        for entry in results:
            entry.source["retrieval_request_id"] = receipt["request_id"]
    return {
        "results": results,
        "organization_status": organization_status,
        "retrieval_receipt": receipt,
    }


def _display_path(entry: Entry, repo_root: Path) -> str:
    source_path = str(entry.source.get("path") or "").strip()
    if source_path and entry.source.get("kind") == "organization":
        return source_path
    try:
        return os.path.relpath(entry.path, repo_root)
    except ValueError:
        return str(entry.path)


def render_entry(entry: Entry, repo_root: Path) -> dict[str, Any]:
    data = entry.data
    logicguard_context = entry.source.get("logicguard")
    if not isinstance(logicguard_context, dict):
        logicguard_context = {}
    return {
        "id": data.get("id"),
        "knowledge_ref": str(entry.source.get("knowledge_ref") or ""),
        "result_ref": str(entry.source.get("result_ref") or ""),
        "retrieval_request_id": str(entry.source.get("retrieval_request_id") or ""),
        "source_kind": str(entry.source.get("source_kind") or ""),
        "source_id": str(entry.source.get("source_id") or ""),
        "title": data.get("title"),
        "type": data.get("type"),
        "scope": data.get("scope"),
        "status": data.get("status"),
        "trust_label": "untrusted-candidate" if str(data.get("status") or "").lower() == "candidate" else "trusted",
        "confidence": data.get("confidence"),
        "domain_path": parse_route_segments(data.get("domain_path", [])),
        "cross_index": normalize_string_list(data.get("cross_index", [])),
        "related_cards": normalize_string_list(data.get("related_cards", [])),
        "logicguard": logicguard_context,
        "logicguard_ranking": dict(entry.source.get("logicguard_ranking") or {}),
        "model_neighbors": [
            str(item.get("model_id") or "")
            for item in logicguard_context.get("neighborhood", {}).get("model_pins", [])
            if isinstance(item, dict)
            and str(item.get("model_id") or "")
            != str(data.get("logicguard_model_id") or "")
        ],
        "tags": data.get("tags", []),
        "trigger_keywords": data.get("trigger_keywords", []),
        "predicted_result": get_predicted_result(data),
        "guidance": get_guidance(data),
        "path": _display_path(entry, repo_root),
        "source_info": entry.source,
        **card_source_summary(data, entry.source),
        "score": round(entry.score, 3),
    }


def render_search_payload(entries: list[Entry], repo_root: Path) -> list[dict[str, Any]]:
    return [render_entry(entry, repo_root) for entry in entries]


def format_search_output(payload: list[dict[str, Any]], path_hint: str = "") -> str:
    lines: list[str] = []
    path_hint_segments = parse_route_segments(path_hint)
    if not payload:
        return "No relevant predictive KB entries found."

    if path_hint_segments:
        lines.append(f"Path hint: {' / '.join(path_hint_segments)}")
        lines.append("")

    lines.append("Top predictive KB entries across current sources:")
    lines.append("")
    for index, item in enumerate(payload, start=1):
        lines.append(f"{index}. [{item['id']}] {item['title']}")
        lines.append(
            "   "
            f"type={item['type']} scope={item['scope']} status={item['status']} score={item['score']}"
        )
        lines.append(
            "   "
            f"domain_path={' / '.join(item['domain_path']) if item['domain_path'] else '-'}"
        )
        lines.append(
            "   "
            f"cross_index={'; '.join(item['cross_index']) if item['cross_index'] else '-'}"
        )
        binding = item.get("logicguard", {}).get("binding", {})
        lines.append(
            "   "
            f"logicguard={binding.get('logicguard_model_id', '-')}@{binding.get('logicguard_revision_id', '-')} "
            f"node={binding.get('logicguard_node_id', '-')} mesh={binding.get('logicguard_mesh_id', '-')}@{binding.get('logicguard_mesh_revision_id', '-')}"
        )
        lines.append(
            "   "
            f"model_neighbors={'; '.join(item['model_neighbors']) if item['model_neighbors'] else '-'}"
        )
        gaps = item.get("logicguard", {}).get("open_role_gaps", [])
        lines.append(f"   model_gaps={'; '.join(gaps) if gaps else '-'}")
        lines.append(f"   predicted_result={item['predicted_result']}")
        lines.append(f"   guidance={item['guidance']}")
        lines.append(f"   tags={', '.join(item['tags'])}")
        lines.append(f"   trigger_keywords={', '.join(item['trigger_keywords'])}")
        lines.append(f"   path={item['path']}")
        lines.append(
            "   "
            f"source={item.get('source_kind', '-')}:{item.get('source_id', '-')} "
            f"result_ref={item.get('result_ref', '-')}"
        )
        lines.append("")
    return "\n".join(lines).rstrip()
