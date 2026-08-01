from __future__ import annotations

import copy
from datetime import date, datetime
import hashlib
import json
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

from local_kb.models import Entry
from local_kb.org_sources import utc_timestamp


EXCHANGE_LEDGER_RELATIVE_PATH = Path(".local") / "organization_exchange_hashes.json"
MODEL_PROJECTION_METADATA_KEYS = {
    "projection_schema_version",
    "projection_digest",
    "authority_generation_id",
    "authority_scope",
    "logicguard_model_id",
    "logicguard_node_id",
    "logicguard_block_id",
    "logicguard_revision_id",
    "logicguard_mesh_id",
    "logicguard_mesh_revision_id",
    "logicguard_open_role_gaps",
}
EXCHANGE_HASH_IGNORED_KEYS = {
    "organization_proposal",
    "id",
    "scope",
    "status",
    "confidence",
    "source",
    "updated_at",
    "created_at",
    "i18n",
    "related_cards",
    "legacy_upgrade",
    *MODEL_PROJECTION_METADATA_KEYS,
}
EXCHANGE_HASH_ORDER_INSENSITIVE_KEYS = {
    "cross_index",
    "related_cards",
    "required_skills",
    "tags",
    "trigger_keywords",
}


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    return value


def _exchange_hash_payload(value: Any, *, key: str = "", top_level: bool = True) -> Any:
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for item_key, item_value in value.items():
            text_key = str(item_key)
            if top_level and text_key in EXCHANGE_HASH_IGNORED_KEYS:
                continue
            normalized_value = _exchange_hash_payload(
                item_value, key=text_key, top_level=False
            )
            if normalized_value in ({}, [], "", None):
                continue
            normalized[text_key] = normalized_value
        return normalized
    if isinstance(value, list):
        items = [
            _exchange_hash_payload(item, key=key, top_level=False)
            for item in value
        ]
        if key in EXCHANGE_HASH_ORDER_INSENSITIVE_KEYS:
            return sorted(
                items,
                key=lambda item: json.dumps(
                    _json_safe(item), ensure_ascii=False, sort_keys=True
                ),
            )
        return items
    if isinstance(value, tuple):
        return [
            _exchange_hash_payload(item, key=key, top_level=False)
            for item in value
        ]
    return _json_safe(value)


def card_exchange_hash(data: dict[str, Any]) -> str:
    payload = _exchange_hash_payload(copy.deepcopy(data))
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def exchange_ledger_path(repo_root: Path) -> Path:
    return Path(repo_root) / EXCHANGE_LEDGER_RELATIVE_PATH


def load_exchange_ledger(repo_root: Path) -> dict[str, Any]:
    path = exchange_ledger_path(repo_root)
    if not path.exists():
        return {"hashes": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {"hashes": {}}
    if not isinstance(payload, dict):
        return {"hashes": {}}
    if not isinstance(payload.get("hashes"), dict):
        payload["hashes"] = {}
    return payload


def write_exchange_ledger(repo_root: Path, payload: dict[str, Any]) -> Path:
    path = exchange_ledger_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    return path


def record_exchange_hash(
    repo_root: Path,
    content_hash: str,
    *,
    direction: str,
    organization_id: str = "",
    source_repo: str = "",
    source_path: str = "",
    local_path: str = "",
    entry_id: str = "",
) -> None:
    clean_hash = str(content_hash or "").strip()
    if not clean_hash:
        return
    ledger = load_exchange_ledger(repo_root)
    hashes = ledger.setdefault("hashes", {})
    now = utc_timestamp()
    item = hashes.get(clean_hash)
    if not isinstance(item, dict):
        item = {"first_seen_at": now, "events": []}
    item["last_seen_at"] = now
    events = item.setdefault("events", [])
    if not isinstance(events, list):
        events = []
        item["events"] = events
    events.append(
        {
            "direction": str(direction or "").strip(),
            "organization_id": str(organization_id or "").strip(),
            "source_repo": str(source_repo or "").strip(),
            "source_path": str(source_path or "").strip(),
            "local_path": str(local_path or "").strip(),
            "entry_id": str(entry_id or "").strip(),
            "created_at": now,
        }
    )
    hashes[clean_hash] = item
    write_exchange_ledger(repo_root, ledger)


def recorded_exchange_hashes(
    repo_root: Path, directions: set[str] | None = None
) -> set[str]:
    ledger = load_exchange_ledger(repo_root)
    hashes = ledger.get("hashes") if isinstance(ledger.get("hashes"), dict) else {}
    if not directions:
        return {str(content_hash) for content_hash in hashes}
    selected: set[str] = set()
    for content_hash, item in hashes.items():
        events = item.get("events") if isinstance(item, dict) else []
        if isinstance(events, list) and any(
            str(event.get("direction") or "") in directions
            for event in events
            if isinstance(event, dict)
        ):
            selected.add(str(content_hash))
    return selected


def _local_preference_rank(entry: Entry) -> tuple[int, int, str]:
    source_scope = str(entry.source.get("scope") or "").strip().lower()
    status = str(entry.data.get("status") or "").strip().lower()
    scope_rank = {"public": 0, "private": 1, "candidate": 2}.get(source_scope, 3)
    status_rank = {"trusted": 0, "approved": 0, "candidate": 1, "deprecated": 3}.get(status, 2)
    return scope_rank, status_rank, str(entry.path)


def dedupe_local_entries_by_exchange_hash(entries: list[Entry]) -> list[Entry]:
    by_hash: dict[str, Entry] = {}
    for entry in entries:
        content_hash = card_exchange_hash(entry.data)
        existing = by_hash.get(content_hash)
        if existing is None or _local_preference_rank(entry) < _local_preference_rank(existing):
            by_hash[content_hash] = entry
    preferred_paths = {entry.path for entry in by_hash.values()}
    return [entry for entry in entries if entry.path in preferred_paths]


def find_local_entry_by_exchange_hash(repo_root: Path, content_hash: str) -> Entry | None:
    from local_kb.model_maintenance import load_current_model_entries

    matches = [
        entry
        for entry in load_current_model_entries(repo_root)[0]
        if card_exchange_hash(entry.data) == content_hash
    ]
    return sorted(matches, key=_local_preference_rank)[0] if matches else None
