from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Mapping

from local_kb.store import load_yaml_file


ORG_KB_MANIFEST = "khaos_org_kb.yaml"
ORG_KB_KIND = "khaos-organization-kb"
SUPPORTED_SCHEMA_VERSION = 2
ORG_MAIN_ACTIVE_STATUSES = {"trusted", "candidate"}
ORG_TARGET_LAYOUT = "main-imports"
ORG_RECOMMENDED_MAIN_PATH = "kb/main"
ORG_RECOMMENDED_IMPORTS_PATH = "kb/imports"


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _as_relative_path(value: Any) -> str:
    text = str(value or "").strip().replace("\\", "/")
    if not text or text.startswith("/") or re.match(r"^[A-Za-z]:", text):
        return ""
    parts = [part for part in text.split("/") if part not in {"", "."}]
    if any(part == ".." for part in parts):
        return ""
    return "/".join(parts)


def _yaml_status_counts(path: Path) -> tuple[int, dict[str, int]]:
    if not path.exists():
        return 0, {}
    total = 0
    status_counts: dict[str, int] = {}
    for card_path in path.rglob("*.yaml"):
        total += 1
        try:
            card = load_yaml_file(card_path)
        except Exception:
            continue
        if not isinstance(card, dict):
            continue
        status = str(card.get("status") or "").strip().lower()
        if status:
            status_counts[status] = status_counts.get(status, 0) + 1
    return total, status_counts


def _git_executable() -> str:
    discovered = shutil.which("git") or shutil.which("git.cmd")
    if discovered:
        return discovered
    bundled = Path.home() / "AppData" / "Local" / "OpenAI" / "Codex" / "bin" / "git.cmd"
    if bundled.exists():
        return str(bundled)
    return "git"


def _run_git(args: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            [_git_executable(), *args],
            cwd=str(cwd) if cwd is not None else None,
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        return subprocess.CompletedProcess(args=[_git_executable(), *args], returncode=127, stdout="", stderr=str(exc))


def current_git_commit(repo_path: Path) -> str:
    result = _run_git(["rev-parse", "HEAD"], cwd=repo_path)
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def default_org_mirror_path(repo_root: Path, organization_id: str) -> Path:
    safe_id = re.sub(r"[^A-Za-z0-9_.-]+", "-", organization_id.strip()).strip("-")
    if not safe_id:
        safe_id = "org"
    return repo_root / ".local" / "organization_sources" / safe_id


def _git_branch(repo_path: Path) -> str:
    result = _run_git(["branch", "--show-current"], cwd=repo_path)
    return result.stdout.strip() if result.returncode == 0 else ""


def prepare_organization_worktree(
    repo_root: Path,
    source_root: Path,
    *,
    organization_id: str,
    run_id: str,
    base_branch: str = "main",
) -> dict[str, Any]:
    """Prepare one effective organization source without touching a dirty mirror."""

    repo_root = Path(repo_root).resolve()
    source_root = Path(source_root).resolve()
    record: dict[str, Any] = {
        "mode": "direct",
        "configured_path": str(source_root),
        "worktree_path": str(source_root),
        "worktree_root": "",
        "base_branch": str(base_branch or "main"),
        "source_head": current_git_commit(source_root),
        "dirty_entries": [],
        "dirty_scope": "repository",
        "created": False,
        "cleanup_required": False,
    }
    if not source_root.exists():
        return {**record, "ok": False, "status": "missing-source", "errors": [f"organization source path does not exist: {source_root}"]}
    if not (source_root / ".git").exists():
        record["status"] = "non-git-source"
        record["dirty_scope"] = "not-applicable"
        return {**record, "ok": True}

    status = _run_git(
        ["status", "--porcelain=v1", "--untracked-files=all"], cwd=source_root
    )
    if status.returncode != 0:
        return {
            **record,
            "ok": False,
            "status": "source-status-failed",
            "errors": [status.stderr.strip() or status.stdout.strip()],
        }
    dirty_entries = [line for line in status.stdout.splitlines() if line.strip()]
    record["dirty_entries"] = dirty_entries
    record["source_branch"] = _git_branch(source_root)
    if not dirty_entries:
        record["status"] = "clean-fast-path"
        return {**record, "ok": True}

    safe_org = re.sub(r"[^A-Za-z0-9_.-]+", "-", str(organization_id or "org")).strip("-") or "org"
    safe_run = re.sub(r"[^A-Za-z0-9_.-]+", "-", str(run_id or "run")).strip("-") or "run"
    worktree_root = (repo_root / ".local" / "organization_sources" / "worktrees").resolve()
    record["worktree_root"] = str(worktree_root)
    # Keep the disposable checkout path short.  Organization repositories can
    # contain deeply nested LogicGuard bundle names, and the full native run
    # id would push an otherwise valid checkout over Windows' legacy path
    # limit.  The original run id remains in the receipt; this directory name
    # is only a collision-resistant filesystem handle.
    run_handle = hashlib.sha256(safe_run.encode("utf-8")).hexdigest()[:12]
    record["worktree_handle"] = f"{safe_org[:24]}-{run_handle}"
    worktree_path = (worktree_root / record["worktree_handle"]).resolve()
    if worktree_path == source_root or source_root in worktree_path.parents:
        return {
            **record,
            "ok": False,
            "status": "unsafe-worktree-path",
            "errors": ["isolated organization worktree must not be inside the configured mirror"],
        }
    if worktree_path.exists():
        return {
            **record,
            "ok": False,
            "status": "worktree-path-exists",
            "errors": [f"isolated organization worktree path already exists: {worktree_path}"],
        }

    base_ref = f"refs/remotes/origin/{str(base_branch or 'main').strip() or 'main'}"
    ref_check = _run_git(["rev-parse", "--verify", base_ref], cwd=source_root)
    if ref_check.returncode != 0:
        base_ref = f"refs/heads/{str(base_branch or 'main').strip() or 'main'}"
        ref_check = _run_git(["rev-parse", "--verify", base_ref], cwd=source_root)
    if ref_check.returncode != 0:
        return {
            **record,
            "ok": False,
            "status": "base-ref-unavailable",
            "errors": [f"organization base ref unavailable: {base_branch}"],
        }
    base_commit = _run_git(["rev-parse", base_ref], cwd=source_root).stdout.strip()
    worktree_path.parent.mkdir(parents=True, exist_ok=True)
    add = _run_git(
        [
            "-c",
            "core.longpaths=true",
            "worktree",
            "add",
            "--detach",
            str(worktree_path),
            base_ref,
        ],
        cwd=source_root,
    )
    if add.returncode != 0:
        return {
            **record,
            "ok": False,
            "status": "worktree-create-failed",
            "base_ref": base_ref,
            "base_commit": base_commit,
            "errors": [add.stderr.strip() or add.stdout.strip()],
        }
    clean = _run_git(
        ["status", "--porcelain=v1", "--untracked-files=all"], cwd=worktree_path
    )
    if clean.returncode != 0 or clean.stdout.strip():
        return {
            **record,
            "ok": False,
            "status": "worktree-not-clean",
            "base_ref": base_ref,
            "base_commit": base_commit,
            "worktree_path": str(worktree_path),
            "mode": "isolated",
            "created": True,
            "cleanup_required": True,
            "errors": [clean.stderr.strip() or clean.stdout.strip() or "isolated worktree has uncommitted changes"],
        }
    return {
        **record,
        "ok": True,
        "status": "isolated",
        "mode": "isolated",
        "worktree_path": str(worktree_path),
        "base_ref": base_ref,
        "base_commit": base_commit,
        "worktree_head": current_git_commit(worktree_path),
        "created": True,
        "cleanup_required": True,
    }


def cleanup_organization_worktree(
    worktree: Mapping[str, Any] | dict[str, Any] | None,
    *,
    success: bool,
) -> dict[str, Any]:
    """Remove only our exact disposable worktree after a successful cycle."""

    record = dict(worktree or {})
    if str(record.get("mode") or "") != "isolated":
        return {"attempted": False, "ok": True, "status": "not_applicable", "retained": False}
    configured = Path(str(record.get("configured_path") or "")).resolve()
    target = Path(str(record.get("worktree_path") or "")).resolve()
    allowed_root = Path(
        str(record.get("worktree_root") or (configured.parent / "worktrees"))
    ).resolve()
    if not target or target == configured or allowed_root not in target.parents:
        return {"attempted": False, "ok": False, "status": "unsafe-cleanup-path", "retained": True}
    if not success:
        return {"attempted": False, "ok": True, "status": "retained-after-failure", "retained": True, "path": str(target)}
    if not target.exists():
        return {"attempted": True, "ok": True, "status": "already-removed", "retained": False, "path": str(target)}
    status = _run_git(["status", "--porcelain=v1", "--untracked-files=all"], cwd=target)
    if status.returncode != 0 or status.stdout.strip():
        return {
            "attempted": False,
            "ok": False,
            "status": "retained-dirty",
            "retained": True,
            "path": str(target),
            "dirty_entries": [line for line in status.stdout.splitlines() if line.strip()],
        }
    removed = _run_git(["worktree", "remove", str(target)], cwd=configured)
    return {
        "attempted": True,
        "ok": removed.returncode == 0 and not target.exists(),
        "status": "removed" if removed.returncode == 0 and not target.exists() else "remove-failed",
        "retained": target.exists(),
        "path": str(target),
        "errors": [] if removed.returncode == 0 else [removed.stderr.strip() or removed.stdout.strip()],
    }


def guess_organization_source_id(repo_url: str) -> str:
    text = str(repo_url or "").strip().replace("\\", "/")
    if not text:
        return "org"
    text = text.rstrip("/")
    if text.endswith(".git"):
        text = text[:-4]
    candidate = text.rsplit("/", 1)[-1].strip()
    if ":" in candidate:
        candidate = candidate.rsplit(":", 1)[-1]
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", candidate).strip("-") or "org"


def clone_or_fetch_organization_repo(repo_url: str, local_path: Path) -> dict[str, Any]:
    repo_url = str(repo_url or "").strip()
    if not repo_url:
        return {"ok": False, "action": "none", "errors": ["missing repository URL"], "commit": ""}

    local_path = Path(local_path)
    if (local_path / ".git").exists():
        result = _run_git(["fetch", "--prune"], cwd=local_path)
        if result.returncode != 0:
            return {
                "ok": False,
                "action": "fetch",
                "errors": [result.stderr.strip() or result.stdout.strip()],
                "commit": current_git_commit(local_path),
            }
        update = _run_git(["pull", "--ff-only"], cwd=local_path)
        return {
            "ok": update.returncode == 0,
            "action": "fetch",
            "errors": [] if update.returncode == 0 else [update.stderr.strip() or update.stdout.strip()],
            "commit": current_git_commit(local_path),
        }

    if local_path.exists() and any(local_path.iterdir()):
        return {
            "ok": False,
            "action": "none",
            "errors": [f"local mirror path is not an empty directory: {local_path}"],
            "commit": "",
        }

    local_path.parent.mkdir(parents=True, exist_ok=True)
    result = _run_git(["clone", repo_url, str(local_path)])
    return {
        "ok": result.returncode == 0,
        "action": "clone",
        "errors": [] if result.returncode == 0 else [result.stderr.strip() or result.stdout.strip()],
        "commit": current_git_commit(local_path) if result.returncode == 0 else "",
    }


def connect_organization_source(
    repo_root: Path,
    repo_url: str,
    *,
    local_mirror_path: str | Path | None = None,
) -> dict[str, Any]:
    repo_url = str(repo_url or "").strip()
    now = utc_timestamp()
    if local_mirror_path:
        mirror_path = Path(local_mirror_path)
    else:
        mirror_path = default_org_mirror_path(Path(repo_root), guess_organization_source_id(repo_url))

    if not repo_url:
        settings = {
            "repo_url": "",
            "local_mirror_path": str(mirror_path),
            "organization_id": "",
            "validated": False,
            "validation_status": "not_configured",
            "validation_message": "Organization repository URL is required.",
            "last_validated_at": now,
            "last_sync_commit": "",
            "last_sync_at": "",
        }
        return {"ok": False, "settings": settings, "clone": {}, "validation": {}}

    clone_result = clone_or_fetch_organization_repo(repo_url, mirror_path)
    if not clone_result.get("ok"):
        settings = {
            "repo_url": repo_url,
            "local_mirror_path": str(mirror_path),
            "organization_id": "",
            "validated": False,
            "validation_status": "invalid",
            "validation_message": "; ".join(clone_result.get("errors") or ["Failed to clone or fetch organization repository."]),
            "last_validated_at": now,
            "last_sync_commit": "",
            "last_sync_at": "",
        }
        return {"ok": False, "settings": settings, "clone": clone_result, "validation": {}}

    from local_kb.org_migration import migrate_organization_repo_to_current

    migration = migrate_organization_repo_to_current(mirror_path)
    if not migration.get("ok"):
        migration_error = str(migration.get("error") or "Organization repository migration failed.")
        migration_status = "invalid" if migration_error == "missing organization manifest" else "migration_blocked"
        settings = {
            "repo_url": repo_url,
            "local_mirror_path": str(mirror_path),
            "organization_id": "",
            "validated": False,
            "validation_status": migration_status,
            "validation_message": migration_error,
            "last_validated_at": now,
            "last_sync_commit": "",
            "last_sync_at": "",
        }
        return {
            "ok": False,
            "settings": settings,
            "clone": clone_result,
            "migration": migration,
            "validation": {},
        }

    validation = validate_organization_repo(mirror_path)
    validation_ok = bool(validation.get("ok"))
    errors = validation.get("errors") or []
    commit = str(validation.get("commit") or clone_result.get("commit") or "")
    settings = {
        "repo_url": repo_url,
        "local_mirror_path": str(mirror_path),
        "organization_id": str(validation.get("organization_id") or ""),
        "validated": validation_ok,
        "validation_status": "valid" if validation_ok else "invalid",
        "validation_message": "Organization KB repository is valid." if validation_ok else "; ".join(errors),
        "last_validated_at": now,
        "last_sync_commit": commit if validation_ok else "",
        "last_sync_at": now if validation_ok else "",
    }
    snapshot: dict[str, Any] = {}
    if validation_ok:
        from local_kb.org_snapshot import stage_organization_snapshot

        snapshot = stage_organization_snapshot(
            Path(repo_root),
            mirror_path,
            str(settings.get("organization_id") or ""),
            source_repo=repo_url,
            source_commit=commit,
        )
        if snapshot.get("ok") is not True:
            settings["validated"] = False
            settings["validation_status"] = "snapshot_blocked"
            settings["validation_message"] = "; ".join(
                str(item) for item in snapshot.get("errors") or ["organization snapshot activation failed"]
            )
    return {
        "ok": bool(validation_ok and snapshot.get("ok", False)),
        "settings": settings,
        "clone": clone_result,
        "migration": migration,
        "validation": validation,
        "snapshot": snapshot,
    }


def validate_organization_repo(repo_path: Path) -> dict[str, Any]:
    repo_path = Path(repo_path)
    errors: list[str] = []
    manifest_path = repo_path / ORG_KB_MANIFEST

    if not repo_path.exists() or not repo_path.is_dir():
        return {
            "ok": False,
            "errors": [f"repository path does not exist: {repo_path}"],
            "repo_path": str(repo_path),
        }

    if not manifest_path.exists():
        return {
            "ok": False,
            "errors": [f"missing organization KB manifest: {ORG_KB_MANIFEST}"],
            "repo_path": str(repo_path),
        }

    try:
        manifest = load_yaml_file(manifest_path)
    except Exception as exc:  # pragma: no cover - defensive around malformed YAML parser errors
        return {
            "ok": False,
            "errors": [f"failed to read organization KB manifest: {exc}"],
            "repo_path": str(repo_path),
        }

    if not isinstance(manifest, dict):
        manifest = {}
        errors.append("manifest must be a mapping")

    if manifest.get("kind") != ORG_KB_KIND:
        errors.append(f"manifest kind must be {ORG_KB_KIND}")

    if manifest.get("schema_version") != SUPPORTED_SCHEMA_VERSION:
        errors.append(f"schema_version must be {SUPPORTED_SCHEMA_VERSION}")

    organization_id = str(manifest.get("organization_id") or "").strip()
    if not organization_id:
        errors.append("organization_id is required")

    kb = manifest.get("kb") if isinstance(manifest.get("kb"), dict) else {}
    skills = manifest.get("skills") if isinstance(manifest.get("skills"), dict) else {}

    if "trusted_path" in kb or "candidates_path" in kb:
        errors.append("obsolete kb.trusted_path/kb.candidates_path fields are forbidden; run the upgrade migration")

    main_path_text = _as_relative_path(kb.get("main_path"))
    imports_path_text = _as_relative_path(kb.get("imports_path"))
    registry_path_text = _as_relative_path(skills.get("registry_path"))
    skill_candidates_path_text = _as_relative_path(skills.get("candidates_path"))

    exact_paths = {
        "main_path": (main_path_text, ORG_RECOMMENDED_MAIN_PATH),
        "imports_path": (imports_path_text, ORG_RECOMMENDED_IMPORTS_PATH),
        "skills.registry_path": (registry_path_text, "skills/registry.yaml"),
        "skills.candidates_path": (skill_candidates_path_text, "skills/candidates"),
    }
    for label, (actual, expected) in exact_paths.items():
        if actual != expected:
            errors.append(f"{label} must be exactly {expected}")

    obsolete_roots = [relative for relative in ("kb/trusted", "kb/candidates") if (repo_path / relative).exists()]
    if obsolete_roots:
        errors.append("obsolete organization roots are forbidden: " + ", ".join(obsolete_roots))

    required_dirs = {
        "main_path": main_path_text,
        "imports_path": imports_path_text,
    }
    for label, relative in required_dirs.items():
        if not relative:
            errors.append(f"{label} must be a relative path")
            continue
        if not (repo_path / relative).is_dir():
            errors.append(f"{label} does not exist or is not a directory: {relative}")

    if skill_candidates_path_text and not (repo_path / skill_candidates_path_text).is_dir():
        errors.append(f"skill_candidates_path does not exist or is not a directory: {skill_candidates_path_text}")

    registry_skills: list[Any] = []
    if registry_path_text:
        registry_path = repo_path / registry_path_text
        if registry_path.exists():
            registry_payload = load_yaml_file(registry_path)
            if isinstance(registry_payload, dict) and isinstance(registry_payload.get("skills"), list):
                registry_skills = registry_payload["skills"]
            else:
                errors.append("skills registry must contain a skills list")
        else:
            errors.append(f"skills registry does not exist: {registry_path_text}")

    from local_kb.org_source_contract import validate_current_source

    contract = validate_current_source(repo_path, manifest)
    errors.extend(str(item) for item in contract.get("errors") or [])
    main_count = int(contract.get("card_count") or 0)
    main_active_count = int(contract.get("active_count") or 0)
    main_status_counts = dict(contract.get("status_counts") or {})
    trusted_count = int(main_status_counts.get("trusted", 0))
    candidate_count = int(main_status_counts.get("candidate", 0))
    imports_count = 0
    imports_status_counts: dict[str, int] = {}
    if imports_path_text:
        imports_count, imports_status_counts = _yaml_status_counts(repo_path / imports_path_text)

    return {
        "ok": not errors,
        "errors": errors,
        "repo_path": str(repo_path),
        "manifest_path": str(manifest_path),
        "organization_id": organization_id,
        "schema_version": manifest.get("schema_version"),
        "layout": ORG_TARGET_LAYOUT,
        "target_layout": ORG_TARGET_LAYOUT,
        "layout_message": "Organization repository uses the sole current kb/imports incoming lane and kb/main exchange surface.",
        "incoming_lane_path": imports_path_text,
        "exchange_surface_path": main_path_text,
        "local_download_primary_path": main_path_text,
        "local_download_paths": [main_path_text] if main_path_text else [],
        "local_download_excluded_paths": [imports_path_text] if imports_path_text else [],
        "main_path": main_path_text,
        "imports_path": imports_path_text,
        "skills_registry_path": registry_path_text,
        "skill_candidates_path": skill_candidates_path_text,
        "main_count": main_count,
        "main_active_count": main_active_count,
        "main_active_entry_ids": list(contract.get("active_entry_ids") or []),
        "source_generation_id": str((contract.get("catalog") or {}).get("source_generation_id") or ""),
        "source_catalog_digest": str((contract.get("catalog") or {}).get("catalog_digest") or ""),
        "main_status_counts": main_status_counts,
        "imports_count": imports_count,
        "imports_status_counts": imports_status_counts,
        "trusted_count": trusted_count,
        "candidate_count": candidate_count,
        "skill_count": len(registry_skills),
        "commit": current_git_commit(repo_path),
    }
