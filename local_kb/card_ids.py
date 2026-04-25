from __future__ import annotations

import json
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


INSTALLATION_ID_RELATIVE_PATH = Path(".local") / "khaos_brain_installation.json"


def _safe_id_component(value: Any, *, fallback: str) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9_.-]+", "-", text).strip("-")
    return text or fallback


def _parse_time(value: Any) -> datetime:
    text = str(value or "").strip()
    if text:
        normalized = text.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def compact_utc_timestamp(value: Any = None) -> str:
    return _parse_time(value).strftime("%Y%m%dT%H%M%SZ")


def installation_identity_path(repo_root: Path) -> Path:
    return Path(repo_root) / INSTALLATION_ID_RELATIVE_PATH


def load_or_create_installation_id(repo_root: Path) -> str:
    path = installation_identity_path(repo_root)
    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {}
        if isinstance(payload, dict):
            installation_id = str(payload.get("local_installation_id") or "").strip()
            if installation_id:
                return installation_id

    installation_id = str(uuid4())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "local_installation_id": installation_id,
                "created_at": compact_utc_timestamp(),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return installation_id


def installation_short_label(repo_root: Path) -> str:
    compact = re.sub(r"[^a-fA-F0-9]+", "", load_or_create_installation_id(repo_root)).lower()
    return f"inst{(compact or 'local')[:8]}"


def new_card_id(
    repo_root: Path,
    *,
    prefix: str = "card",
    generated_at: Any = None,
    author_hint: str = "",
    random_code: str | None = None,
) -> str:
    safe_prefix = _safe_id_component(prefix, fallback="card")
    author_or_install = _safe_id_component(author_hint, fallback="")
    if not author_or_install:
        author_or_install = installation_short_label(repo_root)
    random_part = _safe_id_component(random_code or secrets.token_hex(3), fallback=secrets.token_hex(3))
    return f"{safe_prefix}-{compact_utc_timestamp(generated_at)}-{author_or_install}-{random_part}"
