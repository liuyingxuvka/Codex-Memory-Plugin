"""Immutable content-addressed local snapshots of current organization cards."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
from typing import Any, Mapping
from uuid import uuid4

from local_kb.logicguard_models import read_foreign_argument_context
from local_kb.org_source_contract import (
    ACTIVE_CARD_STATUSES,
    ORG_SOURCE_BUILDER,
    bundle_digest,
    canonical_digest,
    file_sha256,
    load_current_catalog,
)
from local_kb.org_sources import validate_organization_repo
from local_kb.store import load_yaml_file


SNAPSHOT_SCHEMA_VERSION = 3
SNAPSHOT_ROOT = Path(".local") / "organization_snapshots"
SNAPSHOT_BUILDER = {
    "name": "khaos-brain.organization-snapshot-builder",
    "version": 3,
    "source_builder": ORG_SOURCE_BUILDER,
}


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
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _manifest_digest(manifest: Mapping[str, Any]) -> str:
    return "sha256:" + canonical_digest({key: value for key, value in manifest.items() if key not in {"manifest_digest", "created_at"}})


def _pointer_digest(pointer: Mapping[str, Any]) -> str:
    if not pointer:
        return ""
    return "sha256:" + canonical_digest({key: value for key, value in pointer.items() if key not in {"pointer_digest", "activated_at"}})


def _validate_generation(generation_root: Path, manifest: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    cards = manifest.get("cards") if isinstance(manifest.get("cards"), list) else []
    ids: set[str] = set()
    paths: set[str] = set()
    for row in cards:
        if not isinstance(row, Mapping):
            errors.append("snapshot card manifest row is not an object")
            continue
        entry_id = str(row.get("entry_id") or "")
        source_path = str(row.get("source_path") or row.get("path") or "")
        if not entry_id or entry_id in ids:
            errors.append(f"snapshot card id is missing or duplicated: {entry_id or '?'}")
        if not source_path or source_path in paths:
            errors.append(f"snapshot source path is missing or duplicated: {source_path or '?'}")
        ids.add(entry_id)
        paths.add(source_path)
        for field in ("object_path", "model_path", "mesh_path", "projection_path", "bundle_path"):
            relative = str(row.get(field) or "")
            target = generation_root / relative
            if not relative or not target.is_file():
                errors.append(f"snapshot card {entry_id or '?'} lacks {field}")
        object_path = generation_root / str(row.get("object_path") or "")
        projection_path = generation_root / str(row.get("projection_path") or "")
        bundle_path = generation_root / str(row.get("bundle_path") or "")
        if object_path.is_file() and file_sha256(object_path) != str(row.get("sha256") or ""):
            errors.append(f"snapshot card {entry_id or '?'} projection object digest mismatch")
        if projection_path.is_file() and object_path.is_file():
            if _read_json(projection_path) != load_yaml_file(object_path):
                errors.append(f"snapshot card {entry_id or '?'} projection copies differ")
        if bundle_path.is_file():
            bundle = _read_json(bundle_path)
            if str(bundle.get("bundle_digest") or "") != bundle_digest(bundle):
                errors.append(f"snapshot card {entry_id or '?'} bundle digest mismatch")
            if str(bundle.get("bundle_digest") or "") != str(row.get("bundle_digest") or ""):
                errors.append(f"snapshot card {entry_id or '?'} bundle differs from manifest")
            try:
                read_foreign_argument_context(bundle, expected_binding=row.get("binding") or {})
            except Exception as exc:
                errors.append(f"snapshot card {entry_id or '?'} bundle invalid: {type(exc).__name__}: {exc}")
    if int(manifest.get("active_count") or 0) != len(cards):
        errors.append("snapshot active_count differs from card manifest")
    if list(manifest.get("active_entry_ids") or []) != [str(row.get("entry_id") or "") for row in cards if isinstance(row, Mapping)]:
        errors.append("snapshot active_entry_ids differ from exact card order")
    return errors


def load_current_organization_snapshot(repo_root: Path, organization_id: str) -> dict[str, Any]:
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
    if str(pointer.get("pointer_digest") or "") != _pointer_digest(pointer):
        return {"ok": False, "status": "incomplete-current-snapshot", "errors": ["snapshot pointer digest mismatch"]}
    generation_id = str(pointer.get("generation_id") or "")
    generation_root = snapshot_root(repo_root, organization_id) / "generations" / generation_id
    manifest_path = generation_root / "snapshot_manifest.json"
    manifest = _read_json(manifest_path)
    errors: list[str] = []
    if manifest.get("schema_version") != SNAPSHOT_SCHEMA_VERSION:
        errors.append("current snapshot manifest is missing or invalid")
    if str(manifest.get("generation_id") or "") != generation_id:
        errors.append("snapshot manifest generation differs from pointer")
    if str(manifest.get("manifest_digest") or "") != _manifest_digest(manifest):
        errors.append("snapshot manifest digest mismatch")
    if str(pointer.get("manifest_digest") or "") != str(manifest.get("manifest_digest") or ""):
        errors.append("snapshot pointer does not match its manifest")
    if list(pointer.get("active_entry_ids") or []) != list(manifest.get("active_entry_ids") or []):
        errors.append("snapshot pointer active identities differ from manifest")
    if int(pointer.get("active_count") or 0) != int(manifest.get("active_count") or 0):
        errors.append("snapshot pointer active count differs from manifest")
    if generation_root.is_dir():
        errors.extend(_validate_generation(generation_root, manifest))
    else:
        errors.append("current snapshot generation directory is missing")
    if errors:
        return {
            "ok": False,
            "status": "incomplete-current-snapshot",
            "organization_id": str(organization_id),
            "generation_id": generation_id,
            "pointer_path": str(pointer_path),
            "errors": errors,
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


def stage_organization_snapshot(
    repo_root: Path,
    org_root: Path,
    organization_id: str,
    *,
    source_repo: str = "",
    source_commit: str = "",
    expected_pointer_digest: str | None = None,
) -> dict[str, Any]:
    """Copy one exact current catalog generation and activate it with CAS."""

    repo_root = Path(repo_root)
    org_root = Path(org_root)
    organization_id = str(organization_id or "").strip()
    validation = validate_organization_repo(org_root)
    if not organization_id or not validation.get("ok") or str(validation.get("organization_id") or "") != organization_id:
        return {
            "ok": False,
            "status": "blocked",
            "organization_id": organization_id,
            "errors": ["organization source is not the exact current source contract", *(validation.get("errors") or [])],
        }
    catalog = load_current_catalog(org_root)
    rows = [
        dict(row)
        for row in (catalog.get("cards") or [])
        if isinstance(row, Mapping) and bool(row.get("active"))
    ]
    rows.sort(key=lambda row: str(row.get("entry_id") or ""))
    identity = {
        "organization_id": organization_id,
        "source_commit": str(source_commit or ""),
        "source_generation_id": str(catalog.get("source_generation_id") or ""),
        "source_catalog_digest": str(catalog.get("catalog_digest") or ""),
        "builder_identity": SNAPSHOT_BUILDER,
        "active_bundles": [
            {
                "entry_id": row.get("entry_id"),
                "source_path": row.get("source_path"),
                "bundle_digest": row.get("bundle_digest"),
                "projection_sha256": row.get("projection_sha256"),
            }
            for row in rows
        ],
    }
    content_identity_digest = "sha256:" + canonical_digest(identity)
    generation_id = "snapshot-" + content_identity_digest.removeprefix("sha256:")[:24]
    root = snapshot_root(repo_root, organization_id)
    generation_root = root / "generations" / generation_id
    pointer_path = snapshot_pointer_path(repo_root, organization_id)
    initial_pointer = _read_json(pointer_path)
    initial_digest = _pointer_digest(initial_pointer)
    if expected_pointer_digest is not None and expected_pointer_digest != initial_digest:
        return {"ok": False, "status": "pointer-conflict", "errors": ["snapshot predecessor pointer differs from caller expectation"]}
    predecessor_digest = initial_digest
    manifest_rows: list[dict[str, Any]] = []
    staging = root / "staging" / uuid4().hex
    manifest: dict[str, Any]
    try:
        if not generation_root.exists():
            staging.mkdir(parents=True, exist_ok=False)
            for row in rows:
                entry_id = str(row["entry_id"])
                token = _safe_segment(entry_id, "card")
                short_token = hashlib.sha256(entry_id.encode("utf-8")).hexdigest()[:16]
                object_path = f"objects/{short_token}.yaml"
                source_path = str(row["source_path"])
                destination_paths = {
                    "object_path": object_path,
                    "model_path": f"logicguard/m/{short_token}.json",
                    "mesh_path": f"logicguard/x/{short_token}.json",
                    "projection_path": f"logicguard/p/{short_token}.json",
                    "bundle_path": f"logicguard/b/{short_token}.json",
                }
                source_fields = {
                    "object_path": source_path,
                    "model_path": str(row["model_path"]),
                    "mesh_path": str(row["mesh_path"]),
                    "projection_path": str(row["projection_path"]),
                    "bundle_path": str(row["bundle_path"]),
                }
                for field, destination in destination_paths.items():
                    source = org_root / source_fields[field]
                    target = staging / destination
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
                materialized = staging / source_path
                materialized.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(org_root / source_path, materialized)
                manifest_rows.append({**row, "path": source_path, **destination_paths, "sha256": row["source_sha256"]})
            if (org_root / "skills").exists():
                shutil.copytree(org_root / "skills", staging / "skills", dirs_exist_ok=True)
            manifest = {
                "schema_version": SNAPSHOT_SCHEMA_VERSION,
                **identity,
                "content_identity_digest": content_identity_digest,
                "generation_id": generation_id,
                "predecessor_pointer_digest": predecessor_digest,
                "active_identity_digest": "sha256:" + canonical_digest([row["entry_id"] for row in manifest_rows]),
                "active_count": len(manifest_rows),
                "active_entry_ids": [str(row["entry_id"]) for row in manifest_rows],
                "cards": manifest_rows,
                "source_repo": str(source_repo or ""),
                "created_at": _now(),
            }
            manifest["manifest_digest"] = _manifest_digest(manifest)
            (staging / "snapshot_manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            generation_root.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.replace(staging, generation_root)
            except OSError:
                if not generation_root.exists():
                    raise
                shutil.rmtree(staging, ignore_errors=True)
        manifest = _read_json(generation_root / "snapshot_manifest.json")
        generation_errors = _validate_generation(generation_root, manifest)
        if generation_errors or str(manifest.get("generation_id") or "") != generation_id or str(manifest.get("manifest_digest") or "") != _manifest_digest(manifest):
            return {"ok": False, "status": "immutable-generation-conflict", "generation_id": generation_id, "errors": generation_errors or ["existing generation content differs"]}
        current_pointer = _read_json(pointer_path)
        current_digest = _pointer_digest(current_pointer)
        if current_digest != predecessor_digest and str(current_pointer.get("generation_id") or "") != generation_id:
            return {"ok": False, "status": "pointer-conflict", "generation_id": generation_id, "errors": ["snapshot pointer changed before activation"]}
        pointer = {
            "schema_version": SNAPSHOT_SCHEMA_VERSION,
            "organization_id": organization_id,
            "generation_id": generation_id,
            "source_repo": str(source_repo or ""),
            "source_commit": str(source_commit or ""),
            "source_generation_id": str(catalog.get("source_generation_id") or ""),
            "source_catalog_digest": str(catalog.get("catalog_digest") or ""),
            "builder_identity_digest": "sha256:" + canonical_digest(SNAPSHOT_BUILDER),
            "predecessor_pointer_digest": predecessor_digest,
            "manifest_digest": str(manifest["manifest_digest"]),
            "active_count": len(rows),
            "active_entry_ids": [str(row["entry_id"]) for row in rows],
            "activated_at": _now(),
        }
        pointer["pointer_digest"] = _pointer_digest(pointer)
        pointer_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = pointer_path.with_name(f".{pointer_path.name}.{uuid4().hex}.tmp")
        temporary.write_text(json.dumps(pointer, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        latest = _read_json(pointer_path)
        if _pointer_digest(latest) != current_digest and str(latest.get("generation_id") or "") != generation_id:
            temporary.unlink(missing_ok=True)
            return {"ok": False, "status": "pointer-conflict", "generation_id": generation_id, "errors": ["snapshot pointer changed during activation"]}
        os.replace(temporary, pointer_path)
    except Exception as exc:
        shutil.rmtree(staging, ignore_errors=True)
        return {"ok": False, "status": "blocked", "organization_id": organization_id, "generation_id": generation_id, "errors": [f"snapshot activation failed: {type(exc).__name__}: {exc}"]}
    return {
        "ok": True,
        "status": "reused" if str(initial_pointer.get("generation_id") or "") == generation_id else "activated",
        **pointer,
        "generation_root": str(generation_root),
        "manifest_path": str(generation_root / "snapshot_manifest.json"),
        "pointer_path": str(pointer_path),
    }
