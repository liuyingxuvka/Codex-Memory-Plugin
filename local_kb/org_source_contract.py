"""Current-only contract for organization card exchange sources.

The organization checkout publishes complete, immutable card bundles.  Normal
readers validate this contract and never translate legacy cards or manufacture
missing reasoning fields.  Legacy input is handled only by ``org_migration``.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Iterable, Mapping
from uuid import uuid4

from local_kb.logicguard_models import (
    commit_card_model,
    commit_scope_mesh,
    json_safe,
    open_mesh_store,
    read_foreign_argument_context,
)
from local_kb.model_projection import CARD_PROJECTION_SCHEMA_VERSION, projection_digest
from local_kb.store import load_yaml_file, write_yaml_file


ORG_SOURCE_SCHEMA_VERSION = 2
ORG_SOURCE_CATALOG_SCHEMA = "khaos-brain.organization-card-catalog.v1"
ORG_SOURCE_BUNDLE_SCHEMA = "khaos-brain.organization-logicguard-bundle.v1"
ORG_SOURCE_BUILDER = {
    "name": "khaos-brain.organization-source-builder",
    "version": 2,
    "text_digest_policy": "utf8-lf-v1",
    "card_projection_schema": CARD_PROJECTION_SCHEMA_VERSION,
    "bundle_schema": ORG_SOURCE_BUNDLE_SCHEMA,
}
CATALOG_RELATIVE_PATH = "kb/organization_catalog.json"
BUNDLE_ROOT_RELATIVE_PATH = "kb/logicguard/bundles"
CURRENT_CARD_STATUSES = frozenset({"trusted", "candidate", "deprecated", "rejected"})
ACTIVE_CARD_STATUSES = frozenset({"trusted", "candidate"})
REQUIRED_BINDING_FIELDS = (
    "authority_scope",
    "logicguard_model_id",
    "logicguard_node_id",
    "logicguard_block_id",
    "logicguard_revision_id",
    "logicguard_mesh_id",
    "logicguard_mesh_revision_id",
)


def authoring_card_from_projection(projection: Mapping[str, Any]) -> dict[str, Any]:
    """Remove transport binding fields before a current source is rebuilt."""

    card = dict(projection)
    for field in (
        "projection_schema_version",
        "projection_digest",
        "authority_generation_id",
        "logicguard_open_role_gaps",
        *REQUIRED_BINDING_FIELDS,
    ):
        card.pop(field, None)
    return card


def canonical_digest(value: Any, *, prefix: bool = False) -> str:
    digest = hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()
    return f"sha256:{digest}" if prefix else digest


def file_sha256(path: Path) -> str:
    """Hash generated text with one portable UTF-8/LF byte representation."""

    text = Path(path).read_bytes().decode("utf-8")
    portable = text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    return hashlib.sha256(portable).hexdigest()


def _safe_segment(value: Any, fallback: str = "card") -> str:
    text = "".join(char if char.isalnum() or char in "._-" else "-" for char in str(value or "").strip())
    return text.strip(".-")[:120] or fallback


def _safe_relative(value: Any) -> str:
    text = str(value or "").strip().replace("\\", "/")
    path = Path(text)
    if not text or path.is_absolute() or ".." in path.parts:
        return ""
    return "/".join(part for part in path.parts if part not in {"", "."})


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(json_safe(dict(payload)), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def catalog_digest(payload: Mapping[str, Any]) -> str:
    return "sha256:" + canonical_digest({key: value for key, value in payload.items() if key != "catalog_digest"})


def bundle_digest(payload: Mapping[str, Any]) -> str:
    return "sha256:" + canonical_digest({key: value for key, value in payload.items() if key != "bundle_digest"})


def current_source_manifest(organization_id: str) -> dict[str, Any]:
    return {
        "kind": "khaos-organization-kb",
        "schema_version": ORG_SOURCE_SCHEMA_VERSION,
        "organization_id": str(organization_id),
        "kb": {
            "main_path": "kb/main",
            "imports_path": "kb/imports",
            "catalog_path": CATALOG_RELATIVE_PATH,
            "bundle_root": BUNDLE_ROOT_RELATIVE_PATH,
            "projection_schema": CARD_PROJECTION_SCHEMA_VERSION,
            "bundle_schema": ORG_SOURCE_BUNDLE_SCHEMA,
        },
        "skills": {
            "registry_path": "skills/registry.yaml",
            "candidates_path": "skills/candidates",
        },
    }


def _build_bundle(
    card: Mapping[str, Any],
    *,
    organization_id: str,
    source_generation_id: str,
    source_reference: str,
) -> dict[str, Any]:
    scope = str(card.get("scope") or "public").strip().lower()
    if scope == "candidate":
        scope = "candidates"
    if scope not in {"public", "private", "candidates"}:
        scope = "public"
    with tempfile.TemporaryDirectory(prefix="khaos-org-source-") as temporary:
        temp_root = Path(temporary)
        model_commit = commit_card_model(
            temp_root,
            card,
            authority_scope=scope,
            expected_revision=None,
            idempotency_key=f"org-source:{organization_id}:{card['id']}:{source_generation_id}",
            actor="khaos-brain.organization-source-builder",
            source_reference=source_reference,
        )
        mesh_commit = commit_scope_mesh(
            temp_root,
            authority_scope=scope,
            model_bindings=[model_commit.binding],
            expected_revision=None,
            idempotency_key=f"org-source-mesh:{organization_id}:{card['id']}:{source_generation_id}",
            actor="khaos-brain.organization-source-builder",
        )
        binding = mesh_commit.bindings[0]
        mesh_payload = open_mesh_store(temp_root, scope).get(
            mesh_commit.mesh_id, mesh_commit.mesh_revision_id
        ).to_dict()
        model_payload = dict(model_commit.model_payload)
        projection = dict(card)
        projection.update(binding.to_dict())
        projection.update(
            {
                "projection_schema_version": CARD_PROJECTION_SCHEMA_VERSION,
                "authority_generation_id": source_generation_id,
                "logicguard_open_role_gaps": list(
                    model_payload.get("model", {}).get("open_role_gaps", [])
                    if isinstance(model_payload.get("model"), dict)
                    else []
                ),
            }
        )
        projection["projection_digest"] = projection_digest(projection)
        body = {
            "schema_version": ORG_SOURCE_BUNDLE_SCHEMA,
            "organization_id": organization_id,
            "entry_id": str(card["id"]),
            "generation_id": source_generation_id,
            "builder_identity": ORG_SOURCE_BUILDER,
            "binding": binding.to_dict(),
            "model": model_payload,
            "mesh": mesh_payload,
            "projection": projection,
            "model_digest": str(model_commit.content_digest),
            "mesh_digest": str(mesh_commit.content_digest),
            "projection_digest": str(projection["projection_digest"]),
        }
        body["bundle_digest"] = bundle_digest(body)
        return body


def materialize_current_source(
    root: Path,
    *,
    organization_id: str,
    cards: Iterable[tuple[str, Mapping[str, Any]]],
    source_commit: str = "",
    tombstones: Iterable[Mapping[str, Any]] = (),
    dispositions: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Publish complete current source artifacts into an empty/staged root."""

    root = Path(root)
    normalized: list[tuple[str, dict[str, Any]]] = []
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    for raw_path, raw_card in cards:
        path = _safe_relative(raw_path)
        # YAML timestamps and other scalar extensions must be frozen into the
        # same JSON-safe representation used by portable bundles.  Otherwise
        # a valid legacy card can build an in-memory model but fail while its
        # projection is written, forcing the whole upgrade to roll back.
        card = json_safe(dict(raw_card))
        entry_id = str(card.get("id") or "").strip()
        status = str(card.get("status") or "").strip().lower()
        if not path.startswith("kb/main/") or not path.endswith(('.yaml', '.yml')):
            raise ValueError(f"current organization card path must be under kb/main: {raw_path}")
        if not entry_id or entry_id in seen_ids:
            raise ValueError(f"current organization card id is missing or duplicated: {entry_id or '?'}")
        if path in seen_paths:
            raise ValueError(f"current organization card path is duplicated: {path}")
        if status not in CURRENT_CARD_STATUSES:
            raise ValueError(f"unsupported current organization card status for {entry_id}: {status}")
        if "legacy_upgrade" in card:
            raise ValueError(f"legacy_upgrade metadata is forbidden in current card {entry_id}")
        seen_ids.add(entry_id)
        seen_paths.add(path)
        normalized.append((path, card))
    normalized.sort(key=lambda item: (str(item[1]["id"]), item[0]))
    source_generation_id = "org-source-" + canonical_digest(
        {
            "organization_id": organization_id,
            "source_commit": source_commit,
            "builder_identity": ORG_SOURCE_BUILDER,
            "cards": [{"path": path, "card": card} for path, card in normalized],
            "tombstones": list(tombstones),
        }
    )
    rows: list[dict[str, Any]] = []
    for source_path, card in normalized:
        entry_id = str(card["id"])
        bundle = _build_bundle(
            card,
            organization_id=organization_id,
            source_generation_id=source_generation_id,
            source_reference=f"{source_commit}:{source_path}",
        )
        token = _safe_segment(entry_id)
        bundle_root = Path(BUNDLE_ROOT_RELATIVE_PATH) / token
        paths = {
            "model_path": (bundle_root / "model.json").as_posix(),
            "mesh_path": (bundle_root / "mesh.json").as_posix(),
            "projection_path": (bundle_root / "projection.json").as_posix(),
            "bundle_path": (bundle_root / "bundle.json").as_posix(),
        }
        write_yaml_file(root / source_path, bundle["projection"])
        _write_json(root / paths["model_path"], bundle["model"])
        _write_json(root / paths["mesh_path"], bundle["mesh"])
        _write_json(root / paths["projection_path"], bundle["projection"])
        _write_json(root / paths["bundle_path"], bundle)
        rows.append(
            {
                "entry_id": entry_id,
                "source_path": source_path,
                "lifecycle_status": str(card["status"]),
                "active": str(card["status"]) in ACTIVE_CARD_STATUSES,
                "source_sha256": file_sha256(root / source_path),
                "projection_sha256": file_sha256(root / paths["projection_path"]),
                "projection_digest": bundle["projection_digest"],
                "model_digest": bundle["model_digest"],
                "mesh_digest": bundle["mesh_digest"],
                "bundle_digest": bundle["bundle_digest"],
                "binding": bundle["binding"],
                **paths,
            }
        )
    catalog: dict[str, Any] = {
        "schema_version": ORG_SOURCE_CATALOG_SCHEMA,
        "organization_id": organization_id,
        "source_generation_id": source_generation_id,
        "source_commit": source_commit,
        "builder_identity": ORG_SOURCE_BUILDER,
        "cards": rows,
        "tombstones": [dict(item) for item in tombstones],
        "migration_dispositions": [dict(item) for item in dispositions],
    }
    catalog["catalog_digest"] = catalog_digest(catalog)
    _write_json(root / CATALOG_RELATIVE_PATH, catalog)
    write_yaml_file(root / "khaos_org_kb.yaml", current_source_manifest(organization_id))
    (root / "kb" / "imports").mkdir(parents=True, exist_ok=True)
    (root / "skills" / "candidates").mkdir(parents=True, exist_ok=True)
    (root / "kb" / "imports" / ".gitkeep").touch(exist_ok=True)
    (root / "skills" / "candidates" / ".gitkeep").touch(exist_ok=True)
    if not (root / "skills" / "registry.yaml").exists():
        write_yaml_file(root / "skills" / "registry.yaml", {"skills": []})
    return catalog


def load_current_catalog(root: Path) -> dict[str, Any]:
    path = Path(root) / CATALOG_RELATIVE_PATH
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def validate_current_source(root: Path, manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the exact current catalog and every portable LogicGuard bundle."""

    root = Path(root)
    errors: list[str] = []
    kb = manifest.get("kb") if isinstance(manifest.get("kb"), Mapping) else {}
    expected_kb = current_source_manifest(str(manifest.get("organization_id") or ""))["kb"]
    for field, expected in expected_kb.items():
        if kb.get(field) != expected:
            errors.append(f"kb.{field} must be exactly {expected}")
    catalog = load_current_catalog(root)
    if catalog.get("schema_version") != ORG_SOURCE_CATALOG_SCHEMA:
        errors.append("organization card catalog schema is missing or unsupported")
    if str(catalog.get("organization_id") or "") != str(manifest.get("organization_id") or ""):
        errors.append("organization card catalog organization_id mismatch")
    if str(catalog.get("catalog_digest") or "") != catalog_digest(catalog):
        errors.append("organization card catalog digest mismatch")
    if catalog.get("builder_identity") != ORG_SOURCE_BUILDER:
        errors.append("organization card catalog builder identity is unsupported")
    rows = catalog.get("cards") if isinstance(catalog.get("cards"), list) else []
    ids: set[str] = set()
    paths: set[str] = set()
    active_ids: list[str] = []
    catalog_paths: set[str] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            errors.append("organization catalog card row must be an object")
            continue
        entry_id = str(row.get("entry_id") or "").strip()
        source_path = _safe_relative(row.get("source_path"))
        status = str(row.get("lifecycle_status") or "").strip().lower()
        if not entry_id or entry_id in ids:
            errors.append(f"organization catalog card id is missing or duplicated: {entry_id or '?'}")
        if not source_path.startswith("kb/main/") or source_path in paths:
            errors.append(f"organization catalog source path is invalid or duplicated: {source_path or '?'}")
        ids.add(entry_id)
        paths.add(source_path)
        catalog_paths.add(source_path)
        if status not in CURRENT_CARD_STATUSES:
            errors.append(f"organization catalog card {entry_id or '?'} has unsupported status: {status}")
        if bool(row.get("active")) != (status in ACTIVE_CARD_STATUSES):
            errors.append(f"organization catalog card {entry_id or '?'} active flag disagrees with lifecycle status")
        if bool(row.get("active")):
            active_ids.append(entry_id)
        source_file = root / source_path
        if not source_file.is_file():
            errors.append(f"organization catalog card source is missing: {source_path}")
            continue
        if file_sha256(source_file) != str(row.get("source_sha256") or ""):
            errors.append(f"organization catalog card source digest mismatch: {source_path}")
        try:
            projection = load_yaml_file(source_file)
        except Exception as exc:
            errors.append(f"organization card projection cannot be parsed: {source_path}: {type(exc).__name__}: {exc}")
            continue
        if not isinstance(projection, dict):
            errors.append(f"organization card projection is not a mapping: {source_path}")
            continue
        if "legacy_upgrade" in projection:
            errors.append(f"legacy metadata is forbidden in current organization card: {source_path}")
        if str(projection.get("id") or "") != entry_id or str(projection.get("status") or "").lower() != status:
            errors.append(f"organization card identity/status differs from catalog: {source_path}")
        if str(projection.get("projection_schema_version") or "") != CARD_PROJECTION_SCHEMA_VERSION:
            errors.append(f"organization card is a raw legacy card, not a current projection: {source_path}")
        if str(projection.get("projection_digest") or "") != projection_digest(projection):
            errors.append(f"organization card projection digest mismatch: {source_path}")
        artifact_paths: dict[str, Path] = {}
        for field in ("model_path", "mesh_path", "projection_path", "bundle_path"):
            relative = _safe_relative(row.get(field))
            artifact_paths[field] = root / relative
            if not relative.startswith(BUNDLE_ROOT_RELATIVE_PATH + "/") or not artifact_paths[field].is_file():
                errors.append(f"organization card {entry_id or '?'} has missing or unsafe {field}")
        if not all(path.is_file() for path in artifact_paths.values()):
            continue
        bundle = _read_json(artifact_paths["bundle_path"])
        packaged_projection = _read_json(artifact_paths["projection_path"])
        if bundle.get("projection") != packaged_projection or packaged_projection != projection:
            errors.append(f"organization card {entry_id or '?'} projection copies differ")
        if str(bundle.get("bundle_digest") or "") != bundle_digest(bundle):
            errors.append(f"organization card {entry_id or '?'} bundle digest mismatch")
        for field in ("bundle_digest", "model_digest", "mesh_digest", "projection_digest"):
            if str(bundle.get(field) or "") != str(row.get(field) or ""):
                errors.append(f"organization card {entry_id or '?'} {field} differs from catalog")
        if bundle.get("binding") != row.get("binding"):
            errors.append(f"organization card {entry_id or '?'} binding differs from catalog")
        if any(not str((row.get("binding") or {}).get(field) or "") for field in REQUIRED_BINDING_FIELDS):
            errors.append(f"organization card {entry_id or '?'} lacks an exact model binding")
        if str(bundle.get("generation_id") or "") != str(catalog.get("source_generation_id") or ""):
            errors.append(f"organization card {entry_id or '?'} bundle generation differs from catalog")
        try:
            read_foreign_argument_context(bundle, expected_binding=row.get("binding") or {})
        except Exception as exc:
            errors.append(f"organization card {entry_id or '?'} LogicGuard bundle is invalid: {type(exc).__name__}: {exc}")
    actual_paths = {
        path.relative_to(root).as_posix()
        for path in (root / "kb" / "main").rglob("*.yaml")
        if path.is_file()
    } if (root / "kb" / "main").is_dir() else set()
    missing = sorted(catalog_paths - actual_paths)
    extra = sorted(actual_paths - catalog_paths)
    if missing:
        errors.append(f"organization catalog omits required files on disk: {missing}")
    if extra:
        errors.append(f"organization exchange surface contains uncataloged cards: {extra}")
    return {
        "ok": not errors,
        "errors": errors,
        "catalog": catalog,
        "card_count": len(rows),
        "active_count": len(active_ids),
        "active_entry_ids": active_ids,
        "status_counts": {
            status: sum(1 for row in rows if isinstance(row, Mapping) and str(row.get("lifecycle_status") or "") == status)
            for status in sorted(CURRENT_CARD_STATUSES)
        },
    }
