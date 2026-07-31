"""Immutable local snapshots of the organization card exchange surface.

The organization repository is a transport and maintenance source.  Normal
retrieval reads the last complete snapshot produced by organization
maintenance; it never walks a mutable checkout or fetches the network.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
from typing import Any
from uuid import uuid4

from local_kb.store import load_yaml_file


SNAPSHOT_SCHEMA_VERSION = 1
SNAPSHOT_ROOT = Path(".local") / "organization_snapshots"
ACTIVE_CARD_STATUSES = frozenset({"trusted", "candidate"})


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _safe_segment(value: str, fallback: str = "org") -> str:
    text = "".join(char if char.isalnum() or char in "._-" else "-" for char in str(value or "").strip())
    return text.strip(".-") or fallback


def snapshot_root(repo_root: Path, organization_id: str) -> Path:
    return Path(repo_root) / SNAPSHOT_ROOT / _safe_segment(organization_id)


def snapshot_pointer_path(repo_root: Path, organization_id: str) -> Path:
    return snapshot_root(repo_root, organization_id) / "current.json"


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def load_current_organization_snapshot(repo_root: Path, organization_id: str) -> dict[str, Any]:
    """Return the current pointer only when its generation is complete."""

    pointer_path = snapshot_pointer_path(repo_root, organization_id)
    pointer = _read_json(pointer_path)
    if pointer.get("schema_version") != SNAPSHOT_SCHEMA_VERSION:
        return {
            "ok": False,
            "status": "missing-current-snapshot",
            "organization_id": str(organization_id),
            "pointer_path": str(pointer_path),
            "errors": ["organization snapshot pointer is missing or has an unsupported schema"],
        }
    generation_id = str(pointer.get("generation_id") or "").strip()
    if not generation_id:
        return {"ok": False, "status": "missing-current-snapshot", "errors": ["snapshot generation id is missing"]}
    generation_root = snapshot_root(repo_root, organization_id) / "generations" / generation_id
    manifest_path = generation_root / "snapshot_manifest.json"
    manifest = _read_json(manifest_path)
    if manifest.get("schema_version") != SNAPSHOT_SCHEMA_VERSION:
        return {
            "ok": False,
            "status": "incomplete-current-snapshot",
            "organization_id": str(organization_id),
            "generation_id": generation_id,
            "pointer_path": str(pointer_path),
            "errors": ["current snapshot manifest is missing or invalid"],
        }
    if not generation_root.is_dir():
        return {
            "ok": False,
            "status": "incomplete-current-snapshot",
            "organization_id": str(organization_id),
            "generation_id": generation_id,
            "pointer_path": str(pointer_path),
            "errors": ["current snapshot generation directory is missing"],
        }
    manifest_digest = _manifest_digest(manifest)
    if str(pointer.get("manifest_digest") or "") != manifest_digest:
        return {
            "ok": False,
            "status": "incomplete-current-snapshot",
            "organization_id": str(organization_id),
            "generation_id": generation_id,
            "pointer_path": str(pointer_path),
            "errors": ["snapshot pointer does not match its manifest"],
        }
    return {
        "ok": True,
        "status": "current",
        **pointer,
        "manifest": manifest,
        "generation_root": str(generation_root),
        "manifest_path": str(manifest_path),
        "pointer_path": str(pointer_path),
    }


def _manifest_digest(manifest: dict[str, Any]) -> str:
    body = {
        key: value
        for key, value in manifest.items()
        if key not in {"manifest_digest", "created_at", "generation_id"}
    }
    return hashlib.sha256(
        json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_tree_if_present(source: Path, target: Path) -> None:
    if not source.exists():
        return
    if source.is_dir():
        shutil.copytree(source, target, dirs_exist_ok=True)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def _active_card_rows(org_root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    cards_root = Path(org_root) / "kb" / "main"
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    seen_ids: set[str] = set()
    if not cards_root.is_dir():
        return [], ["organization exchange surface kb/main is missing"]
    for source_path in sorted(cards_root.rglob("*.yaml")):
        relative = source_path.relative_to(org_root).as_posix()
        try:
            payload = load_yaml_file(source_path)
        except Exception as exc:
            errors.append(f"malformed organization card {relative}: {type(exc).__name__}: {exc}")
            continue
        if not isinstance(payload, dict):
            errors.append(f"organization card {relative} is not a mapping")
            continue
        status = str(payload.get("status") or "").strip().lower()
        if status not in ACTIVE_CARD_STATUSES:
            continue
        entry_id = str(payload.get("id") or "").strip()
        if not entry_id:
            errors.append(f"active organization card {relative} has no id")
            continue
        if entry_id in seen_ids:
            errors.append(f"duplicate active organization card id: {entry_id}")
            continue
        seen_ids.add(entry_id)
        content_hash = _sha256(source_path)
        rows.append(
            {
                "entry_id": entry_id,
                "path": relative,
                "status": status,
                "sha256": content_hash,
                "bytes": source_path.stat().st_size,
                "object_path": f"objects/{content_hash}.yaml",
            }
        )
    return rows, errors


def stage_organization_snapshot(
    repo_root: Path,
    org_root: Path,
    organization_id: str,
    *,
    source_repo: str = "",
    source_commit: str = "",
) -> dict[str, Any]:
    """Stage and atomically activate a complete organization card snapshot."""

    repo_root = Path(repo_root)
    org_root = Path(org_root)
    organization_id = str(organization_id or "").strip()
    if not organization_id:
        return {"ok": False, "status": "blocked", "errors": ["organization_id is required"]}
    rows, errors = _active_card_rows(org_root)
    if errors:
        return {
            "ok": False,
            "status": "blocked",
            "organization_id": organization_id,
            "active_count": len(rows),
            "active_entry_ids": [str(row["entry_id"]) for row in rows],
            "errors": errors,
        }
    body = {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "organization_id": organization_id,
        "source_repo": str(source_repo or ""),
        "source_commit": str(source_commit or ""),
        "cards": rows,
    }
    manifest_digest = _manifest_digest(body)
    generation_id = "snapshot-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + manifest_digest[:12]
    root = snapshot_root(repo_root, organization_id)
    staging_root = root / "staging" / f"{generation_id}-{uuid4().hex[:8]}"
    generation_root = root / "generations" / generation_id
    try:
        staging_root.mkdir(parents=True, exist_ok=False)
        objects_root = staging_root / "objects"
        objects_root.mkdir(parents=True, exist_ok=True)
        for row in rows:
            source_path = org_root / str(row["path"])
            object_target = objects_root / f"{row['sha256']}.yaml"
            object_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, object_target)
            materialized = staging_root / str(row["path"])
            materialized.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(object_target, materialized)
        _copy_tree_if_present(org_root / "skills", staging_root / "skills")
        manifest = {**body, "created_at": _now(), "generation_id": generation_id, "manifest_digest": manifest_digest}
        (staging_root / "snapshot_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        generation_root.parent.mkdir(parents=True, exist_ok=True)
        if generation_root.exists():
            shutil.rmtree(generation_root)
        os.replace(staging_root, generation_root)
        pointer = {
            "schema_version": SNAPSHOT_SCHEMA_VERSION,
            "organization_id": organization_id,
            "generation_id": generation_id,
            "source_repo": str(source_repo or ""),
            "source_commit": str(source_commit or ""),
            "manifest_digest": manifest_digest,
            "active_count": len(rows),
            "active_entry_ids": [str(row["entry_id"]) for row in rows],
            "activated_at": _now(),
        }
        pointer_path = snapshot_pointer_path(repo_root, organization_id)
        pointer_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_pointer = pointer_path.with_suffix(".json.tmp")
        temporary_pointer.write_text(
            json.dumps(pointer, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary_pointer, pointer_path)
    except Exception as exc:
        shutil.rmtree(staging_root, ignore_errors=True)
        return {
            "ok": False,
            "status": "blocked",
            "organization_id": organization_id,
            "generation_id": generation_id,
            "errors": [f"snapshot activation failed: {type(exc).__name__}: {exc}"],
        }
    return {
        "ok": True,
        "status": "activated",
        **pointer,
        "generation_root": str(generation_root),
        "manifest_path": str(generation_root / "snapshot_manifest.json"),
        "pointer_path": str(pointer_path),
    }
