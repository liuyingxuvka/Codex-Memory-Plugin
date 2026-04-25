from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from local_kb.adoption import card_exchange_hash
from local_kb.common import normalize_text, safe_float, tokenize, utc_now_iso
from local_kb.org_sources import validate_organization_repo
from local_kb.store import append_jsonl, load_yaml_file, write_yaml_file


ORG_CLEANUP_AUDIT_RELATIVE_PATH = Path("maintenance") / "cleanup_audit.jsonl"
CARD_ROOTS = ("kb/trusted", "kb/candidates", "kb/imports")
LOW_RISK_APPLY_ACTIONS = {"confidence-adjust", "status-adjust", "mark-duplicate"}


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
    files: list[Path] = []
    for relative_root in CARD_ROOTS:
        target = org_root / relative_root
        if not target.exists():
            continue
        for path in sorted(target.rglob("*.yaml")):
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
    if path.startswith("kb/trusted/"):
        return "high"
    if path.startswith("kb/imports/"):
        return "low"
    return "medium"


def _action_id(action_type: str, target_path: str, reason: str = "") -> str:
    digest = hashlib.sha256(f"{action_type}|{target_path}|{reason}".encode("utf-8")).hexdigest()[:12]
    return f"{action_type}-{digest}"


def _action(action_type: str, target_path: str, **payload: Any) -> dict[str, Any]:
    reason = str(payload.get("reason") or "")
    return {
        "action_id": _action_id(action_type, target_path, reason),
        "action_type": action_type,
        "target_path": target_path,
        **payload,
    }


def _title_tokens(payload: dict[str, Any]) -> set[str]:
    return set(tokenize(normalize_text(payload.get("title"))))


def _similarity(left: dict[str, Any], right: dict[str, Any]) -> float:
    left_tokens = _title_tokens(left)
    right_tokens = _title_tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / max(len(left_tokens), len(right_tokens))


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


def _preferred_duplicate_record(records: list[dict[str, Any]]) -> dict[str, Any]:
    status_rank = {"trusted": 0, "approved": 0, "candidate": 1, "deprecated": 2, "rejected": 3}
    path_rank = {"kb/trusted/": 0, "kb/candidates/": 1, "kb/imports/": 2}

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
                }
            )

    actions: list[dict[str, Any]] = []
    for bundle_id, versions in by_bundle.items():
        unique_versions = {(item["version_time"], item["content_hash"]) for item in versions}
        if len(unique_versions) <= 1:
            continue
        latest = sorted(versions, key=lambda item: (item["version_time"], item["content_hash"]))[-1]
        for item in versions:
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
            proposed_status = "deprecated" if duplicate["relative_path"].startswith("kb/trusted/") else "rejected"
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
        if status == "candidate" and confidence <= weak_confidence_threshold:
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
        elif status == "candidate" and confidence >= strong_candidate_threshold:
            actions.append(
                _action(
                    "status-adjust",
                    path,
                    entry_id=record["entry_id"],
                    current_status=status,
                    proposed_status="trusted",
                    current_confidence=confidence,
                    proposed_confidence=min(0.95, confidence + 0.03),
                    risk="medium",
                    apply_supported=False,
                    reason="High-confidence candidate should be reviewed for promotion.",
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

    for index, left in enumerate(records):
        for right in records[index + 1 :]:
            if left["content_hash"] == right["content_hash"]:
                continue
            similarity = _similarity(left["payload"], right["payload"])
            if similarity < similar_title_threshold:
                continue
            actions.append(
                _action(
                    "merge-cards",
                    left["relative_path"],
                    entry_id=left["entry_id"],
                    related_path=right["relative_path"],
                    related_entry_id=right["entry_id"],
                    similarity=round(similarity, 3),
                    risk="medium",
                    apply_supported=False,
                    reason="Card titles are similar enough to require a merge review.",
                )
            )

    actions.extend(_skill_version_actions(records))
    counts: dict[str, int] = {}
    for action in actions:
        action_type = str(action.get("action_type") or "")
        counts[action_type] = counts.get(action_type, 0) + 1

    return {
        "ok": True,
        "organization_id": organization_id,
        "generated_at": utc_now_iso(),
        "card_count": len(records),
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


def apply_organization_cleanup_proposal(
    org_root: Path,
    proposal: dict[str, Any],
    *,
    allow_actions: set[str] | None = None,
    allow_trusted: bool = False,
    allow_delete: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    org_root = Path(org_root)
    allowed = allow_actions or LOW_RISK_APPLY_ACTIONS
    applied: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    errors: list[str] = []
    now = utc_now_iso()

    for action in proposal.get("actions") or []:
        if not isinstance(action, dict):
            continue
        action_type = str(action.get("action_type") or "").strip()
        action_id = str(action.get("action_id") or "").strip()
        target_path = str(action.get("target_path") or "").strip()
        target = _safe_target_path(org_root, target_path)
        if action.get("apply_supported") is False:
            skipped.append({"action_id": action_id, "reason": "proposal action is not implemented for apply", "action_type": action_type})
            continue
        if action_type not in allowed:
            skipped.append({"action_id": action_id, "reason": "action type is not allowed", "action_type": action_type})
            continue
        if target is None or not target.exists():
            skipped.append({"action_id": action_id, "reason": "target path is missing or unsafe", "target_path": target_path})
            continue
        if target_path.startswith("kb/trusted/") and not allow_trusted:
            skipped.append({"action_id": action_id, "reason": "trusted card apply requires allow_trusted", "target_path": target_path})
            continue
        if action_type == "delete-card":
            if not allow_delete:
                skipped.append({"action_id": action_id, "reason": "delete requires allow_delete", "target_path": target_path})
                continue
            if not dry_run:
                payload = load_yaml_file(target)
                target.unlink()
                _append_audit(
                    org_root,
                    {
                        "event_type": "organization-cleanup-applied",
                        "action_id": action_id,
                        "action_type": action_type,
                        "target_path": target_path,
                        "previous_payload": payload,
                        "created_at": now,
                    },
                )
            applied.append({"action_id": action_id, "action_type": action_type, "target_path": target_path})
            continue

        payload = load_yaml_file(target)
        previous_status = str(payload.get("status") or "")
        previous_confidence = payload.get("confidence")
        if "proposed_status" in action:
            payload["status"] = str(action.get("proposed_status") or previous_status)
        if "proposed_confidence" in action:
            payload["confidence"] = max(0.0, min(1.0, safe_float(action.get("proposed_confidence"), _confidence(payload))))
        cleanup = payload.get("organization_cleanup") if isinstance(payload.get("organization_cleanup"), dict) else {}
        cleanup.update(
            {
                "last_action_id": action_id,
                "last_action_type": action_type,
                "last_reason": str(action.get("reason") or ""),
                "updated_at": now,
            }
        )
        if action.get("duplicate_of"):
            cleanup["duplicate_of"] = str(action.get("duplicate_of") or "")
        payload["organization_cleanup"] = cleanup
        if not dry_run:
            write_yaml_file(target, payload)
            _append_audit(
                org_root,
                {
                    "event_type": "organization-cleanup-applied",
                    "action_id": action_id,
                    "action_type": action_type,
                    "target_path": target_path,
                    "previous_status": previous_status,
                    "updated_status": payload.get("status"),
                    "previous_confidence": previous_confidence,
                    "updated_confidence": payload.get("confidence"),
                    "created_at": now,
                },
            )
        applied.append({"action_id": action_id, "action_type": action_type, "target_path": target_path})

    return {
        "ok": not errors,
        "dry_run": dry_run,
        "applied_count": len(applied),
        "skipped_count": len(skipped),
        "applied": applied,
        "skipped": skipped,
        "errors": errors,
        "audit_path": str(organization_cleanup_audit_path(org_root)),
    }
