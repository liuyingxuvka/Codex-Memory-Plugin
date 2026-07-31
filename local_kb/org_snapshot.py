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
import tempfile
from typing import Any, Mapping
from uuid import uuid4

from local_kb.store import load_yaml_file, write_yaml_file


SNAPSHOT_SCHEMA_VERSION = 2
SNAPSHOT_ROOT = Path(".local") / "organization_snapshots"
ACTIVE_CARD_STATUSES = frozenset({"trusted", "candidate"})
LOGICGUARD_BUNDLE_SCHEMA = "khaos-brain.organization-logicguard-bundle.v1"


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
    bundle_errors: list[str] = []
    cards = manifest.get("cards") if isinstance(manifest.get("cards"), list) else []
    for row in cards:
        if not isinstance(row, dict):
            bundle_errors.append("snapshot card manifest row is not an object")
            continue
        for field in ("model_path", "mesh_path", "projection_path", "bundle_digest", "binding"):
            if not row.get(field):
                bundle_errors.append(f"snapshot card {row.get('entry_id') or '?'} lacks {field}")
        for field in ("model_path", "mesh_path", "projection_path", "object_path"):
            path = generation_root / str(row.get(field) or "")
            if not path.is_file():
                bundle_errors.append(f"snapshot card {row.get('entry_id') or '?'} bundle file is missing: {field}")
        object_path = generation_root / str(row.get("object_path") or "")
        expected_object_digest = str(row.get("sha256") or row.get("projection_sha256") or "")
        if object_path.is_file() and expected_object_digest and _sha256(object_path) != expected_object_digest:
            bundle_errors.append(f"snapshot card {row.get('entry_id') or '?'} projection object digest mismatch")
        if all((generation_root / str(row.get(field) or "")).is_file() for field in ("model_path", "mesh_path", "projection_path")):
            try:
                model_payload = _read_json(generation_root / str(row["model_path"]))
                mesh_payload = _read_json(generation_root / str(row["mesh_path"]))
                projection_payload = _read_json(generation_root / str(row["projection_path"]))
                binding = row.get("binding") if isinstance(row.get("binding"), dict) else {}
                expected_bundle_digest = _logicguard_bundle_digest(
                    organization_id=str(manifest.get("organization_id") or organization_id),
                    entry_id=str(row.get("entry_id") or ""),
                    generation_id=generation_id,
                    binding=binding,
                    model=model_payload,
                    mesh=mesh_payload,
                    projection=projection_payload,
                )
                if expected_bundle_digest != str(row.get("bundle_digest") or ""):
                    bundle_errors.append(f"snapshot card {row.get('entry_id') or '?'} bundle digest mismatch")
                mesh_digest = str(row.get("mesh_digest") or "")
                if mesh_digest and str(mesh_payload.get("content_digest") or "") != mesh_digest:
                    bundle_errors.append(f"snapshot card {row.get('entry_id') or '?'} mesh digest mismatch")
                model_digest = str(row.get("model_digest") or "")
                model_registry = mesh_payload.get("registry") if isinstance(mesh_payload.get("registry"), list) else []
                if model_digest and not any(
                    isinstance(item, dict)
                    and str(item.get("content_digest") or "") == model_digest
                    and isinstance(item.get("model_ref"), dict)
                    and str(item["model_ref"].get("model_id") or "") == str(binding.get("logicguard_model_id") or "")
                    and str(item["model_ref"].get("revision") or "") == str(binding.get("logicguard_revision_id") or "")
                    for item in model_registry
                ):
                    bundle_errors.append(f"snapshot card {row.get('entry_id') or '?'} model digest is not pinned by its mesh")
                if str(projection_payload.get("projection_digest") or "") != str(row.get("projection_digest") or ""):
                    bundle_errors.append(f"snapshot card {row.get('entry_id') or '?'} projection digest mismatch")
                binding_fields = ("authority_scope", "logicguard_model_id", "logicguard_node_id", "logicguard_block_id", "logicguard_revision_id", "logicguard_mesh_id", "logicguard_mesh_revision_id")
                projection_binding = {key: projection_payload.get(key) for key in binding_fields}
                manifest_binding = {key: binding.get(key) for key in binding_fields}
                if projection_binding != manifest_binding:
                    bundle_errors.append(f"snapshot card {row.get('entry_id') or '?'} projection binding mismatch")
                if str(mesh_payload.get("mesh_id") or "") != str(binding.get("logicguard_mesh_id") or "") or str(mesh_payload.get("revision") or "") != str(binding.get("logicguard_mesh_revision_id") or ""):
                    bundle_errors.append(f"snapshot card {row.get('entry_id') or '?'} mesh binding mismatch")
            except Exception as exc:
                bundle_errors.append(f"snapshot card {row.get('entry_id') or '?'} bundle parse failed: {type(exc).__name__}: {exc}")
    if bundle_errors:
        return {
            "ok": False,
            "status": "incomplete-current-snapshot",
            "organization_id": str(organization_id),
            "generation_id": generation_id,
            "pointer_path": str(pointer_path),
            "errors": bundle_errors,
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


def _canonical_digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _logicguard_bundle_digest(
    *,
    organization_id: str,
    entry_id: str,
    generation_id: str,
    binding: Mapping[str, Any],
    model: Mapping[str, Any],
    mesh: Mapping[str, Any],
    projection: Mapping[str, Any],
) -> str:
    """Return the digest over the exact portable bundle payload."""

    return "sha256:" + _canonical_digest(
        {
            "schema_version": LOGICGUARD_BUNDLE_SCHEMA,
            "organization_id": str(organization_id),
            "entry_id": str(entry_id),
            "generation_id": str(generation_id),
            "binding": _json_safe(binding),
            "model": _json_safe(model),
            "mesh": _json_safe(mesh),
            "projection": _json_safe(projection),
        }
    )


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, (tuple, list, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _upgrade_legacy_card(card: dict[str, Any], *, source_path: str, source_hash: str, duplicate_of: str = "") -> dict[str, Any]:
    """Normalize a legacy organization card without inventing factual evidence.

    The upgrade fills only structural fields needed by the current card/model
    contract.  Missing evidence, warrants, assumptions, rebuttals, and
    boundaries remain explicit LogicGuard gaps in the generated bundle.
    """

    value = dict(card)
    original_id = str(value.get("id") or "").strip()
    if duplicate_of:
        value["id"] = f"{original_id}-legacy-{source_hash[:8]}"
    else:
        value["id"] = original_id
    value.setdefault("title", value["id"])
    value.setdefault("type", "model")
    value.setdefault("scope", "public")
    value.setdefault("status", "candidate")
    try:
        value["confidence"] = float(value.get("confidence", 0.5))
    except (TypeError, ValueError):
        value["confidence"] = 0.5
    value["domain_path"] = _string_list(value.get("domain_path")) or ["organization"]
    value["cross_index"] = _string_list(value.get("cross_index"))
    value["related_cards"] = _string_list(value.get("related_cards"))
    value["tags"] = _string_list(value.get("tags"))
    value["trigger_keywords"] = _string_list(value.get("trigger_keywords"))
    if not isinstance(value.get("if"), dict):
        value["if"] = {"notes": "Use when the current task matches this card's route and conditions."}
    else:
        value["if"] = dict(value["if"])
        value["if"].setdefault("notes", "Use when the current task matches this card's route and conditions.")
    if not isinstance(value.get("action"), dict):
        legacy_action = value.get("then") or value.get("action") or value.get("use") or "Apply the card guidance."
        value["action"] = {"description": str(legacy_action)}
    else:
        value["action"] = dict(value["action"])
        value["action"].setdefault("description", "Apply the card guidance.")
    if not isinstance(value.get("predict"), dict):
        value["predict"] = {}
    else:
        value["predict"] = dict(value["predict"])
    if not str(value["predict"].get("expected_result") or "").strip():
        legacy_result = value.get("then") or value.get("expected_result") or value["action"].get("description") or value["title"]
        value["predict"]["expected_result"] = str(legacy_result).strip()
    if not isinstance(value.get("use"), dict):
        value["use"] = {"guidance": str(value["action"].get("description") or "Use this card when its condition matches.")}
    else:
        value["use"] = dict(value["use"])
        value["use"].setdefault("guidance", str(value["action"].get("description") or "Use this card when its condition matches."))
    upgrade = value.get("legacy_upgrade") if isinstance(value.get("legacy_upgrade"), dict) else {}
    upgrade.update({
        "schema": "organization-card-upgrade.v1",
        "source_path": source_path,
        "source_sha256": source_hash,
        "duplicate_of": duplicate_of,
        "structural_defaults_applied": True,
        "evidence_fabricated": False,
    })
    value["legacy_upgrade"] = upgrade
    return value


def _build_logicguard_bundle(
    card: dict[str, Any],
    *,
    organization_id: str,
    source_reference: str,
    generation_id: str,
) -> dict[str, Any]:
    """Build a portable current LogicGuard model/mesh/projection bundle.

    The bundle is built in an isolated temporary store and copied into the
    immutable organization generation.  It never becomes local authority.
    """

    from local_kb.logicguard_models import commit_card_model, commit_scope_mesh, open_mesh_store
    from local_kb.model_projection import projection_digest

    scope = str(card.get("scope") or "public").strip().lower()
    if scope == "candidate":
        scope = "candidates"
    if scope not in {"public", "private", "candidates"}:
        scope = "public"
    with tempfile.TemporaryDirectory(prefix="khaos-org-bundle-") as tmp:
        temp_root = Path(tmp)
        model_commit = commit_card_model(
            temp_root,
            card,
            authority_scope=scope,
            expected_revision=None,
            idempotency_key=f"organization:{organization_id}:{card['id']}:{generation_id}",
            actor="khaos-brain.organization-snapshot",
            source_reference=source_reference,
        )
        mesh_commit = commit_scope_mesh(
            temp_root,
            authority_scope=scope,
            model_bindings=[model_commit.binding],
            expected_revision=None,
            idempotency_key=f"organization-mesh:{organization_id}:{scope}:{generation_id}",
            actor="khaos-brain.organization-snapshot",
        )
        binding = mesh_commit.bindings[0]
        mesh_store = open_mesh_store(temp_root, scope)
        mesh_snapshot = mesh_store.get(mesh_commit.mesh_id, mesh_commit.mesh_revision_id)
        model_payload = dict(model_commit.model_payload)
        mesh_payload = mesh_snapshot.to_dict()
        projection = dict(card)
        projection.update(binding.to_dict())
        projection.update({
            "projection_schema_version": "khaos-brain.card-projection.v1",
            "authority_generation_id": generation_id,
            "related_cards": [],
            "logicguard_open_role_gaps": list(
                model_payload.get("model", {}).get("open_role_gaps", [])
                if isinstance(model_payload.get("model"), dict)
                else []
            ),
        })
        projection["projection_digest"] = projection_digest(projection)
        bundle_body = _json_safe({
            "schema_version": LOGICGUARD_BUNDLE_SCHEMA,
            "organization_id": organization_id,
            "entry_id": str(card["id"]),
            "generation_id": generation_id,
            "binding": binding.to_dict(),
            "model": model_payload,
            "mesh": mesh_payload,
            "projection": projection,
        })
        bundle_digest = _logicguard_bundle_digest(
            organization_id=organization_id,
            entry_id=str(card["id"]),
            generation_id=generation_id,
            binding=binding.to_dict(),
            model=bundle_body["model"],
            mesh=bundle_body["mesh"],
            projection=bundle_body["projection"],
        )
        return {
            "schema_version": LOGICGUARD_BUNDLE_SCHEMA,
            "binding": binding.to_dict(),
            "model": _json_safe(model_payload),
            "mesh": _json_safe(mesh_payload),
            "projection": _json_safe(projection),
            "model_digest": str(model_commit.content_digest),
            "mesh_digest": str(mesh_commit.content_digest),
            "projection_digest": str(projection["projection_digest"]),
            "bundle_digest": bundle_digest,
        }


def _copy_tree_if_present(source: Path, target: Path) -> None:
    if not source.exists():
        return
    if source.is_dir():
        shutil.copytree(source, target, dirs_exist_ok=True)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def _materialize_snapshot_skill_bundles(
    org_root: Path,
    staging_root: Path,
    card: dict[str, Any],
    *,
    entry_id: str,
) -> list[str]:
    """Copy card-bound Skill bundles to short, generation-local paths.

    Organization outboxes intentionally keep their human-readable bundle
    version path under ``kb/main/skills``.  On Windows that path can exceed
    MAX_PATH once nested inside a local snapshot generation.  The immutable
    snapshot is a transport projection, so it may use a deterministic short
    path; the card dependency is rewritten before its LogicGuard bundle is
    built and the source checkout remains untouched.
    """

    errors: list[str] = []
    proposal = card.get("organization_proposal")
    dependencies = proposal.get("skill_dependencies") if isinstance(proposal, dict) else None
    if not isinstance(dependencies, list):
        return errors
    for index, dependency in enumerate(dependencies):
        if not isinstance(dependency, dict):
            continue
        bundle_path = str(dependency.get("bundle_path") or "").strip().replace("\\", "/")
        if not bundle_path:
            continue
        relative = Path(bundle_path)
        if relative.is_absolute() or ".." in relative.parts:
            errors.append(f"{entry_id}: Skill bundle path is not a safe relative path: {bundle_path}")
            continue
        source_dir = org_root / "kb" / "main" / relative
        if not (source_dir / "SKILL.md").is_file():
            # Keep the dependency visible in the portable card, but do not
            # silently claim that an unavailable bundle was transferred.
            errors.append(f"{entry_id}: Skill bundle source is missing: {bundle_path}")
            continue
        content_hash = str(dependency.get("content_hash") or "")
        token = hashlib.sha256(
            f"{entry_id}|{index}|{bundle_path}|{content_hash}".encode("utf-8")
        ).hexdigest()[:16]
        alias_root = Path("skills") / "card-bundles" / token
        alias_skill = alias_root / "skill"
        target_skill = staging_root / alias_skill
        target_skill.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copytree(
                source_dir,
                target_skill,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc", "*.pyo"),
            )
            metadata_source = source_dir.parent / "metadata.yaml"
            if metadata_source.is_file():
                metadata_target = staging_root / alias_root / "metadata.yaml"
                metadata_target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(metadata_source, metadata_target)
        except OSError as exc:
            errors.append(f"{entry_id}: Skill bundle snapshot copy failed for {bundle_path}: {type(exc).__name__}: {exc}")
            shutil.rmtree(target_skill, ignore_errors=True)
            continue
        dependency["bundle_path"] = alias_skill.as_posix()
        dependency["bundle_metadata_path"] = (alias_root / "metadata.yaml").as_posix()
    return errors


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
        content_hash = _sha256(source_path)
        duplicate_of = entry_id if entry_id in seen_ids else ""
        if duplicate_of:
            # Preserve both cards under deterministic identities.  The
            # duplicate relationship remains visible in legacy_upgrade and
            # the organization maintenance report can later merge them.
            duplicate_suffix = hashlib.sha256(f"{relative}:{content_hash}".encode("utf-8")).hexdigest()[:8]
            entry_id = f"{entry_id}-legacy-{duplicate_suffix}"
        seen_ids.add(entry_id)
        rows.append(
            {
                "entry_id": entry_id,
                "path": relative,
                "status": status,
                "source_sha256": content_hash,
                "bytes": source_path.stat().st_size,
                "duplicate_of": duplicate_of,
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
    obsolete_roots = [
        str(relative).replace("/", "\\")
        for relative in ("kb/trusted", "kb/candidates")
        if (org_root / relative).exists()
    ]
    if obsolete_roots:
        return {
            "ok": False,
            "status": "blocked",
            "organization_id": organization_id,
            "errors": ["Organization KB has obsolete runtime roots: " + ", ".join(obsolete_roots)],
        }
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
    generation_id = "snapshot-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + _canonical_digest({"organization_id": organization_id, "source_commit": source_commit, "cards": rows})[:12]
    generation_root = snapshot_root(repo_root, organization_id) / "generations" / generation_id
    body = {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "organization_id": organization_id,
        "source_repo": str(source_repo or ""),
        "source_commit": str(source_commit or ""),
        "generation_id": generation_id,
        "cards": rows,
    }
    manifest_digest = _manifest_digest(body)
    root = snapshot_root(repo_root, organization_id)
    staging_root = root / "staging" / f"{generation_id}-{uuid4().hex[:8]}"
    bundles: dict[str, dict[str, Any]] = {}
    try:
        staging_root.mkdir(parents=True, exist_ok=False)
        objects_root = staging_root / "objects"
        objects_root.mkdir(parents=True, exist_ok=True)
        logicguard_root = staging_root / "logicguard"
        for row in rows:
            source_path = org_root / str(row["path"])
            source_hash = str(row.get("source_sha256") or "")
            raw_card = load_yaml_file(source_path)
            upgraded = _upgrade_legacy_card(
                raw_card,
                source_path=str(row["path"]),
                source_hash=source_hash,
                duplicate_of=str(row.get("duplicate_of") or ""),
            )
            # The manifest identity is the transport identity.  Keep the
            # upgraded card, bundle entry, and lookup key byte-for-byte
            # aligned even when a legacy source contained duplicate ids.
            upgraded["id"] = str(row["entry_id"])
            if isinstance(upgraded.get("legacy_upgrade"), dict):
                upgraded["legacy_upgrade"]["assigned_id"] = str(row["entry_id"])
            skill_errors = _materialize_snapshot_skill_bundles(
                org_root,
                staging_root,
                upgraded,
                entry_id=str(row["entry_id"]),
            )
            if skill_errors:
                raise RuntimeError("; ".join(skill_errors))
            bundle = _build_logicguard_bundle(
                upgraded,
                organization_id=organization_id,
                source_reference=f"{source_repo}@{source_commit}:{row['path']}",
                generation_id=generation_id,
            )
            safe_id = _safe_segment(str(row["entry_id"]))
            model_path = f"logicguard/models/{safe_id}.json"
            mesh_path = f"logicguard/meshes/{safe_id}.json"
            projection_path = f"logicguard/projections/{safe_id}.json"
            row.update(
                {
                    "object_path": f"objects/{safe_id}.yaml",
                    "model_path": model_path,
                    "mesh_path": mesh_path,
                    "projection_path": projection_path,
                    "model_digest": bundle["model_digest"],
                    "mesh_digest": bundle["mesh_digest"],
                    "projection_digest": bundle["projection_digest"],
                    "bundle_digest": bundle["bundle_digest"],
                    "binding": dict(bundle["binding"]),
                }
            )
            bundles[str(row["entry_id"])] = bundle
            object_target = objects_root / f"{safe_id}.yaml"
            object_target.parent.mkdir(parents=True, exist_ok=True)
            write_yaml_file(object_target, bundle["projection"])
            row["sha256"] = _sha256(object_target)
            row["projection_sha256"] = row["sha256"]
            row["bytes"] = object_target.stat().st_size
            materialized = staging_root / str(row["path"])
            materialized.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(object_target, materialized)
            for relative, payload in (
                (model_path, bundle["model"]),
                (mesh_path, bundle["mesh"]),
                (projection_path, bundle["projection"]),
            ):
                target = staging_root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        _copy_tree_if_present(org_root / "skills", staging_root / "skills")
        # Recompute the manifest after bundle metadata has been attached.
        body["cards"] = rows
        manifest_digest = _manifest_digest(body)
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
