from __future__ import annotations

from typing import Any


AUTHOR_KEYS = (
    "author",
    "created_by",
    "uploaded_by",
    "github_user",
    "github_account",
    "user",
    "agent",
)


def _first_text(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _source_payloads(data: dict[str, Any]) -> list[dict[str, Any]]:
    source = data.get("source")
    if isinstance(source, dict):
        return [source]
    if isinstance(source, list):
        return [item for item in source if isinstance(item, dict)]
    return []


def author_label_for_entry(data: dict[str, Any], source_info: dict[str, Any]) -> str:
    for payload in [data, *_source_payloads(data)]:
        for key in AUTHOR_KEYS:
            text = _first_text(payload.get(key))
            if text:
                return text
    return _first_text(
        source_info.get("author"),
        source_info.get("github_user"),
        source_info.get("organization_id"),
        source_info.get("source_id"),
        "local",
    )


def source_label_for_entry(source_info: dict[str, Any]) -> str:
    kind = _first_text(source_info.get("kind"), "local")
    scope = _first_text(source_info.get("scope"), "unknown")
    if kind == "organization":
        organization_id = _first_text(source_info.get("organization_id"), source_info.get("source_id"), "org")
        return f"org/{organization_id}/{scope}"
    if kind == "local":
        return f"local/{scope}"
    return _first_text(source_info.get("label"), f"{kind}/{scope}")


def card_source_summary(data: dict[str, Any], source_info: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_label": source_label_for_entry(source_info),
        "author_label": author_label_for_entry(data, source_info),
        "read_only": bool(source_info.get("read_only")),
    }
