from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from local_kb.config import resolve_repo_root as resolve_configured_repo_root
from local_kb.models import Entry

try:
    import yaml  # type: ignore
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "Missing dependency: PyYAML. Install it with: pip install pyyaml"
    ) from exc


DEFAULT_SCOPES = ("public", "private", "candidates")


def resolve_repo_root(value: str | os.PathLike[str]) -> Path:
    return resolve_configured_repo_root(value)


def load_yaml_file(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def rejected_candidate_entry_ids(repo_root: Path) -> set[str]:
    path = history_events_path(repo_root)
    if not path.exists():
        return set()

    rejected_ids: set[str] = set()
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict):
                continue
            event_type = str(payload.get("event_type", "") or "").strip().lower()
            if event_type != "candidate-rejected":
                continue
            target = payload.get("target", {}) if isinstance(payload.get("target"), dict) else {}
            context = payload.get("context", {}) if isinstance(payload.get("context"), dict) else {}
            entry_id = str(target.get("entry_id") or context.get("entry_id") or "").strip()
            if entry_id:
                rejected_ids.add(entry_id)
    return rejected_ids


def load_entries(repo_root: Path, scopes: Iterable[str] = DEFAULT_SCOPES) -> list[Entry]:
    entries: list[Entry] = []
    kb_root = repo_root / "kb"
    active_scopes = tuple(scopes)
    rejected_candidates = rejected_candidate_entry_ids(repo_root) if "candidates" in active_scopes else set()
    for scope in active_scopes:
        target = kb_root / scope
        if not target.exists():
            continue
        for path in sorted(target.rglob("*.yaml")):
            data = load_yaml_file(path)
            entry_id = str(data.get("id", "") or "").strip()
            if scope == "candidates" and entry_id and entry_id in rejected_candidates:
                continue
            entries.append(Entry(path=path, data=data))
    return entries


def write_yaml_file(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, allow_unicode=True, sort_keys=False)


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def history_events_path(repo_root: Path) -> Path:
    return repo_root / "kb" / "history" / "events.jsonl"


def append_timeline_event(repo_root: Path, payload: dict[str, Any]) -> Path:
    path = history_events_path(repo_root)
    append_jsonl(path, payload)
    return path


def candidate_dir(repo_root: Path) -> Path:
    path = repo_root / "kb" / "candidates"
    path.mkdir(parents=True, exist_ok=True)
    return path
