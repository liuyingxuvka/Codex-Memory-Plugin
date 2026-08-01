"""One-time, rollbackable upgrade into the sole organization source contract."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any, Mapping
from uuid import uuid4

from local_kb.common import utc_now_iso
from local_kb.org_source_contract import (
    ORG_SOURCE_BUILDER,
    ORG_SOURCE_SCHEMA_VERSION,
    authoring_card_from_projection,
    canonical_digest,
    load_current_catalog,
    materialize_current_source,
)
from local_kb.store import load_yaml_file


ORG_LAYOUT_MIGRATION_ID = "organization-source-direct-to-schema2-v2"
ORG_BUILDER_MIGRATION_ID = "organization-source-builder-v2-portable-text-digest-v1"
RETIRED_ORG_SOURCE_BUILDER_V1 = {
    "name": "khaos-brain.organization-source-builder",
    "version": 1,
    "card_projection_schema": "khaos-brain.card-projection.v1",
    "bundle_schema": "khaos-brain.organization-logicguard-bundle.v1",
}
CURRENT_MAIN_PATH = "kb/main"
CURRENT_IMPORTS_PATH = "kb/imports"
OBSOLETE_ROOTS = ("kb/trusted", "kb/candidates")
OBSOLETE_MANIFEST_FIELDS = ("trusted_path", "candidates_path")


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _metadata_root(repo_root: Path) -> Path:
    return repo_root / ".git" if (repo_root / ".git").is_dir() else repo_root / ".khaos-brain-migrations"


def _migration_receipt_path(repo_root: Path, migration_id: str = ORG_LAYOUT_MIGRATION_ID) -> Path:
    return _metadata_root(repo_root) / "khaos-brain-migrations" / f"{migration_id}.json"


def _snapshot_root(repo_root: Path, run_id: str) -> Path:
    return _metadata_root(repo_root) / "khaos-brain-migration-backups" / run_id


def _native_filesystem_path(path: Path) -> Path:
    """Return a Windows extended-length path without changing receipt identity."""

    if os.name != "nt":
        return path
    raw = str(path.resolve())
    if raw.startswith("\\\\?\\"):
        return Path(raw)
    if raw.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + raw.lstrip("\\"))
    return Path("\\\\?\\" + raw)


def _copy_backup(repo_root: Path, backup: Path) -> None:
    native_backup = _native_filesystem_path(backup)
    native_backup.mkdir(parents=True, exist_ok=False)
    if (repo_root / "kb").exists():
        shutil.copytree(
            _native_filesystem_path(repo_root / "kb"),
            _native_filesystem_path(backup / "kb"),
        )
    if (repo_root / "khaos_org_kb.yaml").is_file():
        shutil.copy2(
            _native_filesystem_path(repo_root / "khaos_org_kb.yaml"),
            _native_filesystem_path(backup / "khaos_org_kb.yaml"),
        )


def _restore_backup(repo_root: Path, backup: Path) -> None:
    kb_root = repo_root / "kb"
    if kb_root.exists():
        shutil.rmtree(_native_filesystem_path(kb_root))
    native_backup_kb = _native_filesystem_path(backup / "kb")
    if native_backup_kb.exists():
        shutil.copytree(native_backup_kb, _native_filesystem_path(kb_root))
    manifest = backup / "khaos_org_kb.yaml"
    native_manifest = _native_filesystem_path(manifest)
    if native_manifest.is_file():
        shutil.copy2(native_manifest, _native_filesystem_path(repo_root / "khaos_org_kb.yaml"))


def _legacy_sources(repo_root: Path, manifest: Mapping[str, Any]) -> list[tuple[str, Path]]:
    kb = manifest.get("kb") if isinstance(manifest.get("kb"), Mapping) else {}
    roots: list[tuple[str, Path]] = []
    if str(kb.get("main_path") or "") == CURRENT_MAIN_PATH:
        roots.append(("main", repo_root / CURRENT_MAIN_PATH))
    if str(kb.get("trusted_path") or "") == "kb/trusted":
        roots.append(("trusted", repo_root / "kb" / "trusted"))
    if str(kb.get("candidates_path") or "") == "kb/candidates":
        roots.append(("candidates", repo_root / "kb" / "candidates"))
    rows: list[tuple[str, Path]] = []
    for lane, root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.yaml")):
            if lane == "main":
                target = path.relative_to(repo_root).as_posix()
            else:
                target = (Path(CURRENT_MAIN_PATH) / lane / path.relative_to(root)).as_posix()
            rows.append((target, path))
    return rows


def _normalize_string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _normalize_legacy_card(payload: Mapping[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Translate only declared legacy meaning; never manufacture support."""

    card = dict(payload)
    gaps: list[str] = []
    status = str(card.get("status") or "candidate").strip().lower()
    card["status"] = "trusted" if status == "approved" else status
    card.setdefault("type", "model")
    card.setdefault("scope", "public")
    card["domain_path"] = _normalize_string_list(card.get("domain_path"))
    for field in ("cross_index", "related_cards", "tags", "trigger_keywords"):
        card[field] = _normalize_string_list(card.get(field))
    for field, key in (("if", "notes"), ("action", "description"), ("predict", "expected_result"), ("use", "guidance")):
        value = card.get(field)
        if isinstance(value, Mapping):
            card[field] = dict(value)
        elif str(value or "").strip():
            card[field] = {key: str(value).strip()}
        else:
            card[field] = {}
            gaps.append(field)
    if not str(card.get("id") or "").strip():
        gaps.append("id")
    if not str(card.get("title") or "").strip():
        gaps.append("title")
    if not str((card.get("predict") or {}).get("expected_result") or "").strip():
        gaps.append("predict.expected_result")
    if not str((card.get("action") or {}).get("description") or "").strip():
        gaps.append("action.description")
    card.pop("legacy_upgrade", None)
    return card, sorted(set(gaps))


def _canonical_duplicate(rows: list[dict[str, Any]], old_id: str) -> dict[str, Any]:
    status_rank = {"trusted": 0, "candidate": 1, "deprecated": 2, "rejected": 3}
    return sorted(
        rows,
        key=lambda row: (
            0 if Path(str(row["source_path"])).stem == old_id else 1,
            status_rank.get(str(row["card"].get("status") or ""), 9),
            -float(row["card"].get("confidence") or 0.0),
            str(row["source_path"]),
        ),
    )[0]


def _prepare_cards(repo_root: Path, manifest: Mapping[str, Any]) -> tuple[list[tuple[str, dict[str, Any]]], list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    candidates: list[dict[str, Any]] = []
    errors: list[str] = []
    for target_path, source in _legacy_sources(repo_root, manifest):
        relative = source.relative_to(repo_root).as_posix()
        try:
            raw = load_yaml_file(source)
        except Exception as exc:
            errors.append(f"{relative}: failed to parse: {type(exc).__name__}: {exc}")
            continue
        if not isinstance(raw, Mapping):
            errors.append(f"{relative}: card must be a mapping")
            continue
        card, gaps = _normalize_legacy_card(raw)
        if "id" in gaps or "title" in gaps or "predict.expected_result" in gaps or "action.description" in gaps:
            errors.append(f"{relative}: cannot upgrade without declared id, title, action, and prediction")
            continue
        candidates.append(
            {
                "source_path": relative,
                "target_path": target_path,
                "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "old_id": str(card["id"]),
                "card": card,
                "gaps": gaps,
                "semantic_digest": canonical_digest(card),
            }
        )
    output: list[tuple[str, dict[str, Any]]] = []
    dispositions: list[dict[str, Any]] = []
    tombstones: list[dict[str, Any]] = []
    by_id: dict[str, list[dict[str, Any]]] = {}
    for row in candidates:
        by_id.setdefault(str(row["old_id"]), []).append(row)
    for old_id, duplicates in sorted(by_id.items()):
        canonical = _canonical_duplicate(duplicates, old_id)
        semantic_seen: dict[str, str] = {}
        for row in sorted(duplicates, key=lambda item: str(item["source_path"])):
            if row is canonical:
                assigned = old_id
                disposition = "preserved"
            elif row["semantic_digest"] in semantic_seen or row["semantic_digest"] == canonical["semantic_digest"]:
                retained = semantic_seen.get(row["semantic_digest"], old_id)
                tombstones.append(
                    {
                        "source_path": row["source_path"],
                        "old_entry_id": old_id,
                        "disposition": "retired_exact_duplicate",
                        "retained_entry_id": retained,
                        "source_sha256": row["source_sha256"],
                    }
                )
                dispositions.append(dict(tombstones[-1]))
                continue
            else:
                assigned = f"{old_id}--dup-{row['semantic_digest'][:12]}"
                disposition = "renamed"
            semantic_seen[row["semantic_digest"]] = assigned
            card = dict(row["card"])
            card["id"] = assigned
            if len(duplicates) > 1 and card.get("related_cards"):
                card["organization_migration_gaps"] = [
                    {
                        "kind": "ambiguous-legacy-related-id",
                        "old_entry_id": old_id,
                        "resolution": "unresolved",
                    }
                ]
            target_path = str(row["target_path"])
            if assigned != old_id:
                target = Path(target_path)
                target_path = (target.parent / f"{assigned}.yaml").as_posix()
            output.append((target_path, card))
            dispositions.append(
                {
                    "source_path": row["source_path"],
                    "source_sha256": row["source_sha256"],
                    "old_entry_id": old_id,
                    "assigned_entry_id": assigned,
                    "target_path": target_path,
                    "disposition": disposition,
                    "open_structural_gaps": row["gaps"],
                }
            )
    return output, dispositions, tombstones, errors


def migrate_organization_repo_to_current(repo_root: Path) -> dict[str, Any]:
    """Upgrade the exact retired layout/builder directly to the sole current source."""

    from local_kb.org_sources import _run_git, current_git_commit, validate_organization_repo

    repo_root = Path(repo_root)
    manifest_path = repo_root / "khaos_org_kb.yaml"
    if not manifest_path.is_file():
        return {"ok": False, "status": "blocked", "error": "missing organization manifest"}
    manifest = load_yaml_file(manifest_path)
    if not isinstance(manifest, Mapping):
        return {"ok": False, "status": "blocked", "error": "organization manifest must be a mapping"}
    schema_version = manifest.get("schema_version")
    if schema_version not in {1, ORG_SOURCE_SCHEMA_VERSION}:
        return {"ok": False, "status": "blocked", "error": "organization source schema is neither retired schema 1 nor current schema 2"}
    git_repo = (repo_root / ".git").is_dir()
    source_commit = current_git_commit(repo_root) if git_repo else ""
    if git_repo:
        status = _run_git(["status", "--porcelain"], cwd=repo_root)
        if status.returncode != 0 or status.stdout.strip():
            return {"ok": False, "status": "blocked", "error": "organization repository must be clean before one-time migration"}
    migration_id = ORG_LAYOUT_MIGRATION_ID
    commit_message = "Upgrade organization KB to schema 2"
    if schema_version == ORG_SOURCE_SCHEMA_VERSION:
        validation = validate_organization_repo(repo_root)
        if validation.get("ok"):
            return {
                "ok": True,
                "status": "no_delta",
                "migration_id": ORG_BUILDER_MIGRATION_ID,
                "validation": validation,
                "error": "",
            }
        catalog = load_current_catalog(repo_root)
        if catalog.get("builder_identity") != RETIRED_ORG_SOURCE_BUILDER_V1:
            return {
                "ok": False,
                "status": "blocked",
                "migration_id": ORG_BUILDER_MIGRATION_ID,
                "validation": validation,
                "error": "current-layout source is not the exact retired builder-v1 upgrade input",
            }
        cards = []
        builder_errors: list[str] = []
        for row in catalog.get("cards") or []:
            if not isinstance(row, Mapping):
                builder_errors.append("retired builder catalog row is not an object")
                continue
            source_path = str(row.get("source_path") or "").replace("\\", "/")
            source_file = repo_root / source_path
            if not source_path.startswith("kb/main/") or not source_file.is_file():
                builder_errors.append(f"retired builder source path is missing or unsafe: {source_path or '?'}")
                continue
            projection = load_yaml_file(source_file)
            if not isinstance(projection, Mapping) or str(projection.get("id") or "") != str(row.get("entry_id") or ""):
                builder_errors.append(f"retired builder card identity mismatch: {source_path}")
                continue
            cards.append((source_path, authoring_card_from_projection(projection)))
        if builder_errors or len(cards) != len(catalog.get("cards") or []):
            return {
                "ok": False,
                "status": "blocked",
                "migration_id": ORG_BUILDER_MIGRATION_ID,
                "validation": validation,
                "error": "; ".join(builder_errors or ["retired builder inventory is incomplete"]),
            }
        dispositions = [dict(item) for item in catalog.get("migration_dispositions") or [] if isinstance(item, Mapping)]
        tombstones = [dict(item) for item in catalog.get("tombstones") or [] if isinstance(item, Mapping)]
        migration_id = ORG_BUILDER_MIGRATION_ID
        commit_message = "Upgrade organization source builder to portable digest v2"
    else:
        cards, dispositions, tombstones, errors = _prepare_cards(repo_root, manifest)
        if errors:
            return {"ok": False, "status": "blocked", "error": "; ".join(errors), "dispositions": dispositions}
    organization_id = str(manifest.get("organization_id") or "").strip()
    if not organization_id:
        return {"ok": False, "status": "blocked", "error": "organization_id is required"}
    run_id = f"{utc_now_iso().replace(':', '').replace('-', '')}-{uuid4().hex[:8]}"
    backup = _snapshot_root(repo_root, run_id)
    _copy_backup(repo_root, backup)
    try:
        with tempfile.TemporaryDirectory(prefix="khaos-org-upgrade-") as temporary:
            staged = Path(temporary)
            materialize_current_source(
                staged,
                organization_id=organization_id,
                cards=cards,
                source_commit=source_commit,
                tombstones=tombstones,
                dispositions=dispositions,
            )
            if (repo_root / "skills").exists():
                shutil.copytree(repo_root / "skills", staged / "skills", dirs_exist_ok=True)
            if (repo_root / CURRENT_IMPORTS_PATH).exists():
                shutil.copytree(repo_root / CURRENT_IMPORTS_PATH, staged / CURRENT_IMPORTS_PATH, dirs_exist_ok=True)
            if (repo_root / "kb").exists():
                shutil.rmtree(repo_root / "kb")
            shutil.copytree(staged / "kb", repo_root / "kb")
            shutil.copy2(staged / "khaos_org_kb.yaml", manifest_path)
        validation = validate_organization_repo(repo_root)
        if not validation.get("ok"):
            raise RuntimeError("; ".join(validation.get("errors") or ["current source validation failed"]))
        target_commit = source_commit
        if git_repo:
            add = _run_git(["add", "--", "khaos_org_kb.yaml", "kb"], cwd=repo_root)
            if add.returncode != 0:
                raise RuntimeError(add.stderr.strip() or add.stdout.strip() or "git add failed")
            commit = _run_git(
                ["-c", "user.name=Chaos Brain Upgrade", "-c", "user.email=chaos-brain-upgrade@local.invalid", "commit", "-m", commit_message],
                cwd=repo_root,
            )
            if commit.returncode != 0:
                raise RuntimeError(commit.stderr.strip() or commit.stdout.strip() or "migration commit failed")
            target_commit = current_git_commit(repo_root)
        receipt = {
            "schema_version": 2,
            "migration_id": migration_id,
            "status": "committed",
            "migrated_at": utc_now_iso(),
            "source_commit": source_commit,
            "target_commit": target_commit,
            "input_count": len(dispositions),
            "output_count": len(cards),
            "dispositions": dispositions,
            "tombstones": tombstones,
            "rollback_snapshot": str(backup),
            "validation_ok": True,
        }
        _atomic_write_json(_migration_receipt_path(repo_root, migration_id), receipt)
        return {"ok": True, "status": "committed", "migration_id": migration_id, "receipt": receipt}
    except Exception as exc:
        _restore_backup(repo_root, backup)
        return {
            "ok": False,
            "status": "rolled_back",
            "migration_id": migration_id,
            "error": f"{type(exc).__name__}: {exc}",
            "rollback_snapshot": str(backup),
        }
