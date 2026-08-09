"""Safe rehearsal of the real organization maintenance/contribution owners.

This module is deliberately separate from the scheduled automation wrapper.  It
uses a disposable machine and source checkout, disables remote publication, and
returns a structured rehearsal envelope rather than a native scheduled receipt.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from local_kb.logicguard_models import authority_generation_pointer_path
from local_kb.maintenance_standard import (
    CURRENT_HISTORY_SCHEMA_VERSION,
    CURRENT_MAINTENANCE_STANDARD_VERSION,
    write_maintenance_state,
)
from local_kb.model_maintenance import publish_sleep_model_generation
from local_kb.org_cycle import run_organization_cycle
from local_kb.org_sources import _run_git
from local_kb.settings import (
    ORGANIZATION_MODE,
    load_desktop_settings,
    maintenance_participation_status_from_settings,
    organization_sources_from_settings,
    save_desktop_settings,
)


REHEARSAL_SCHEMA = "khaos-brain.organization-maintenance-rehearsal.v1"
REHEARSAL_RECEIPT_SCHEMA = "khaos-brain.organization-maintenance-rehearsal-receipt.v1"
REHEARSAL_EVIDENCE_DIR = Path(".local") / "assurance" / "organization-rehearsal"
REQUIRED_CHECKPOINTS = (
    "card_surface",
    "candidate_intake",
    "content_hash",
    "merge",
    "split",
    "card_decisions",
    "skill_safety",
    "skill_bundle_version",
    "decision_apply",
    "post_apply",
    "github_merge_readiness",
)


def _native_filesystem_path(path: Path) -> Path:
    """Return a path that can be removed even when a rehearsal is deep."""

    if os.name != "nt":
        return Path(path)
    raw = str(Path(path).resolve())
    if raw.startswith("\\\\?\\"):
        return Path(raw)
    if raw.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + raw.lstrip("\\"))
    return Path("\\\\?\\" + raw)


class _RehearsalDirectory:
    """Temporary directory with extended-length cleanup on Windows."""

    def __init__(self) -> None:
        self.path: Path | None = None
        self.cleanup: dict[str, Any] = {
            "attempted": False,
            "ok": True,
            "status": "not_started",
        }

    def __enter__(self) -> Path:
        self.path = Path(tempfile.mkdtemp(prefix="kb-org-rehearsal-"))
        return self.path

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> bool:
        if self.path is not None:
            native = _native_filesystem_path(self.path)
            self.cleanup = {
                "attempted": True,
                "path": str(self.path),
                "native_path": str(native),
                "ok": True,
                "status": "already-removed",
            }
            try:
                if native.exists():
                    shutil.rmtree(native, ignore_errors=False)
                    self.cleanup["status"] = "removed"
            except Exception as cleanup_error:  # pragma: no cover - platform-specific
                self.cleanup.update(
                    {
                        "ok": False,
                        "status": "cleanup-failed",
                        "error": f"{type(cleanup_error).__name__}: {cleanup_error}",
                    }
                )
        return False


def _digest_file(path: Path) -> str:
    digest = hashlib.sha256()
    if not path.exists() or not path.is_file():
        return ""
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_status(root: Path) -> str:
    result = _run_git(["status", "--porcelain=v1", "--untracked-files=all"], cwd=root)
    return result.stdout if result.returncode == 0 else f"<git-status-error>{result.stderr.strip()}"


def _git_head(root: Path) -> str:
    result = _run_git(["rev-parse", "HEAD"], cwd=root)
    return result.stdout.strip() if result.returncode == 0 else ""


def _canonical_digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _source_contract_digest(root: Path) -> str:
    """Hash only organization exchange inputs, not README/assets presentation files."""

    root = Path(root).resolve()
    paths: list[Path] = []
    for candidate in (
        root / "khaos_org_kb.yaml",
        root / "kb" / "organization_catalog.json",
        root / "kb" / "manifest.json",
        root / "kb" / "logicguard" / "manifest.json",
    ):
        if candidate.is_file():
            paths.append(candidate)
    for subtree in (
        root / "kb" / "main",
        root / "kb" / "imports",
        root / "kb" / "logicguard" / "bundles",
        root / "kb" / "skills",
    ):
        if subtree.is_dir():
            paths.extend(path for path in subtree.rglob("*") if path.is_file())
    rows = []
    for path in sorted(set(paths)):
        rows.append(
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": _digest_file(path),
            }
        )
    return _canonical_digest(rows)


def _git_worktree_registry(root: Path) -> str:
    result = _run_git(["worktree", "list", "--porcelain"], cwd=root)
    return result.stdout if result.returncode == 0 else f"<git-worktree-error>{result.stderr.strip()}"


def _remote_ref_snapshot(root: Path) -> dict[str, Any]:
    result = _run_git(["ls-remote", "--heads", "--tags", "origin"], cwd=root)
    if result.returncode != 0:
        return {"ok": False, "error": result.stderr.strip() or result.stdout.strip()}
    lines = sorted(line.strip() for line in result.stdout.splitlines() if line.strip())
    return {"ok": True, "refs": lines, "digest": _canonical_digest(lines)}


def _automation_run_inventory(repo_root: Path) -> list[str]:
    root = Path(repo_root) / ".local" / "automation-runs" / "kb-organization-maintenance"
    if not root.is_dir():
        return []
    return sorted(path.name for path in root.iterdir() if path.is_dir())


def _repository_identity(repo_root: Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    tracked = _run_git(
        ["ls-files", "--cached", "--others", "--exclude-standard"], cwd=root
    )
    rows = []
    if tracked.returncode == 0:
        for relative in sorted(set(line.strip() for line in tracked.stdout.splitlines() if line.strip())):
            if relative.startswith(".local/") or relative.endswith("/__pycache__"):
                continue
            path = root / relative
            if path.is_file():
                rows.append({"path": relative.replace("\\", "/"), "sha256": _digest_file(path)})
    else:
        for path in sorted(root.rglob("*")):
            if not path.is_file() or ".git" in path.parts or ".local" in path.parts:
                continue
            rows.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "sha256": _digest_file(path),
                }
            )
    status = _git_status(root)
    return {
        "root": str(root),
        "head": _git_head(root),
        "status": status,
        "tree_digest": _canonical_digest(rows),
        "source_file_count": len(rows),
    }


def _toolchain_identity(repo_root: Path) -> dict[str, Any]:
    git = _run_git(["--version"], cwd=repo_root)
    try:
        import flowguard  # type: ignore

        flowguard_version = str(importlib.metadata.version("flowguard"))
        flowguard_schema = str(getattr(flowguard, "SCHEMA_VERSION", ""))
    except Exception as error:  # pragma: no cover - optional package metadata
        flowguard_version = ""
        flowguard_schema = f"unavailable:{type(error).__name__}"
    return {
        "python": os.sys.version,
        "git": git.stdout.strip() or git.stderr.strip(),
        "flowguard_package_version": flowguard_version,
        "flowguard_schema_version": flowguard_schema,
    }


def _runner_identity(repo_root: Path) -> dict[str, Any]:
    """Identify the exact rehearsal implementation used for this receipt."""

    root = Path(repo_root).resolve()
    files = (
        root / "local_kb" / "org_simulation.py",
        root / "scripts" / "simulate_kb_organization_maintenance.py",
        root / "local_kb" / "org_cycle.py",
        root / "local_kb" / "org_maintenance.py",
        root / "local_kb" / "org_automation.py",
        root / "local_kb" / "org_sources.py",
    )
    rows = []
    for path in files:
        relative = path.relative_to(root).as_posix()
        rows.append({"path": relative, "sha256": _digest_file(path)})
    return {
        "files": rows,
        "digest": f"sha256:{_canonical_digest(rows)}",
    }


def _authority_identity(repo_root: Path) -> dict[str, Any]:
    pointer = authority_generation_pointer_path(Path(repo_root))
    return {
        "path": str(pointer),
        "exists": pointer.is_file(),
        "sha256": _digest_file(pointer),
    }


def _configured_source_identity(source_root: Path) -> dict[str, Any]:
    root = Path(source_root).resolve()
    return {
        "path": str(root),
        "head": _git_head(root),
        "status": _git_status(root),
        "branch": _run_git(["branch", "--show-current"], cwd=root).stdout.strip(),
        "manifest_catalog_digest": _source_contract_digest(root),
        "worktree_registry": _git_worktree_registry(root),
        "remote_refs": _remote_ref_snapshot(root),
    }


def _clone_source(source_root: Path, destination: Path, *, expected_head: str = "") -> dict[str, Any]:
    """Clone committed source bytes without importing the configured working tree."""

    source_root = Path(source_root).resolve()
    if (source_root / ".git").exists():
        clone = _run_git(
            ["clone", "--local", "--no-checkout", str(source_root), str(destination)]
        )
        if clone.returncode != 0:
            return {"ok": False, "errors": [clone.stderr.strip() or clone.stdout.strip()]}
        ref = str(expected_head or "HEAD")
        ref_check = _run_git(["rev-parse", "--verify", ref], cwd=destination)
        if ref_check.returncode != 0:
            return {
                "ok": False,
                "errors": [f"disposable clone cannot resolve frozen source head: {ref}"],
            }
        checkout = _run_git(
            ["-c", "core.longpaths=true", "checkout", "--detach", ref], cwd=destination
        )
        if checkout.returncode != 0:
            return {"ok": False, "errors": [checkout.stderr.strip() or checkout.stdout.strip()]}
        cloned_head = _git_head(destination)
        if expected_head and cloned_head != expected_head:
            return {
                "ok": False,
                "errors": [f"disposable clone head mismatch: expected {expected_head}, got {cloned_head}"],
            }
        return {"ok": True, "mode": "git-clone", "source_head": cloned_head}

    if not source_root.exists() or not source_root.is_dir():
        return {"ok": False, "errors": [f"organization source path does not exist: {source_root}"]}
    shutil.copytree(source_root, destination)
    return {"ok": True, "mode": "directory-copy", "source_head": ""}


def _bootstrap_machine(machine_root: Path, settings: dict[str, Any]) -> dict[str, Any]:
    machine_root.mkdir(parents=True, exist_ok=True)
    save_desktop_settings(machine_root, settings)
    for scope in ("public", "private", "candidates"):
        (machine_root / "kb" / scope).mkdir(parents=True, exist_ok=True)
    authority = publish_sleep_model_generation(
        machine_root,
        reason="organization-maintenance-rehearsal-bootstrap",
    )
    if not authority.get("ok"):
        return {"ok": False, "errors": [f"failed to bootstrap disposable local authority: {authority}"]}
    write_maintenance_state(
        machine_root,
        {
            "maintenance_standard_version": CURRENT_MAINTENANCE_STANDARD_VERSION,
            "history_schema_version": CURRENT_HISTORY_SCHEMA_VERSION,
            "phase": "committed",
            "committed": True,
            "migration_id": "organization-maintenance-rehearsal-bootstrap",
        },
    )
    return {"ok": True, "authority_pointer": authority_generation_pointer_path(machine_root)}


def _failure(checkpoint: str, reason: str, *, evidence: Any = None) -> dict[str, Any]:
    return {
        "checkpoint": checkpoint,
        "reason": reason,
        "evidence": evidence if evidence is not None else {},
        "reopen_condition": f"Repair {checkpoint} and rerun the rehearsal from a fresh disposable source.",
    }


def _rehearsal_receipt_root(repo_root: Path) -> Path:
    return Path(repo_root).resolve() / REHEARSAL_EVIDENCE_DIR


def persist_rehearsal_receipt(repo_root: Path, result: dict[str, Any]) -> dict[str, Any]:
    """Write one content-addressed generation and advance its pointer."""

    root = _rehearsal_receipt_root(repo_root)
    generations = root / "receipts"
    generations.mkdir(parents=True, exist_ok=True)
    payload = dict(result)
    payload["receipt_schema"] = REHEARSAL_RECEIPT_SCHEMA
    payload.pop("receipt_digest", None)
    digest = _canonical_digest(payload)
    payload["receipt_digest"] = f"sha256:{digest}"
    generation_path = generations / f"{digest}.json"
    pointer_path = root / "current.json"
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, default=str) + "\n"
    generation_path.write_text(encoded, encoding="utf-8")
    pointer_path.write_text(encoded, encoding="utf-8")
    return {
        "receipt_schema": REHEARSAL_RECEIPT_SCHEMA,
        "receipt_digest": payload["receipt_digest"],
        "generation_path": str(generation_path),
        "pointer_path": str(pointer_path),
    }


def verify_rehearsal_receipt(
    repo_root: Path,
    *,
    receipt_path: Path | None = None,
) -> dict[str, Any]:
    """Verify the current rehearsal receipt against live source/toolchain identities."""

    path = Path(receipt_path or (_rehearsal_receipt_root(repo_root) / "current.json")).resolve()
    if not path.is_file():
        return {"ok": False, "status": "missing", "reason": "identity-bound rehearsal receipt is missing", "path": str(path)}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as error:
        return {"ok": False, "status": "invalid", "reason": f"receipt JSON unreadable: {type(error).__name__}", "path": str(path)}
    if not isinstance(payload, dict):
        return {"ok": False, "status": "invalid", "reason": "receipt root must be an object", "path": str(path)}
    recorded_digest = str(payload.get("receipt_digest") or "")
    body = dict(payload)
    body.pop("receipt_digest", None)
    expected_digest = f"sha256:{_canonical_digest(body)}"
    if recorded_digest != expected_digest:
        return {"ok": False, "status": "invalid", "reason": "receipt digest mismatch", "path": str(path)}
    if payload.get("receipt_schema") != REHEARSAL_RECEIPT_SCHEMA:
        return {"ok": False, "status": "invalid", "reason": "receipt schema is not current", "path": str(path)}
    if payload.get("ok") is not True or payload.get("status") != "completed":
        return {"ok": False, "status": "failed", "reason": "receipt is not a completed rehearsal", "path": str(path), "receipt_digest": recorded_digest}
    if payload.get("production_receipt") is not False:
        return {"ok": False, "status": "invalid", "reason": "rehearsal must remain distinct from production receipt", "path": str(path)}
    validation = payload.get("validation") if isinstance(payload.get("validation"), dict) else {}
    cleanup = payload.get("cleanup") if isinstance(payload.get("cleanup"), dict) else {}
    if validation.get("checkpoint") != "complete" or cleanup.get("ok") is not True:
        return {"ok": False, "status": "failed", "reason": "rehearsal validation or temporary cleanup is incomplete", "path": str(path), "receipt_digest": recorded_digest}
    identity = payload.get("repository") if isinstance(payload.get("repository"), dict) else {}
    live_identity = _repository_identity(repo_root)
    if identity.get("head") != live_identity.get("head") or identity.get("status") != live_identity.get("status") or identity.get("tree_digest") != live_identity.get("tree_digest"):
        return {"ok": False, "status": "stale", "reason": "rehearsal repository identity no longer matches", "path": str(path), "receipt_digest": recorded_digest, "live_repository": live_identity}
    source = payload.get("source") if isinstance(payload.get("source"), dict) else {}
    configured_before = source.get("configured_before") if isinstance(source.get("configured_before"), dict) else {}
    configured_path = Path(str(configured_before.get("path") or ""))
    if not configured_path.exists():
        return {"ok": False, "status": "stale", "reason": "configured source disappeared", "path": str(path), "receipt_digest": recorded_digest}
    live_source = _configured_source_identity(configured_path)
    if live_source != configured_before:
        return {"ok": False, "status": "stale", "reason": "configured source identity changed after rehearsal", "path": str(path), "receipt_digest": recorded_digest, "live_source": live_source}
    toolchain = payload.get("toolchain") if isinstance(payload.get("toolchain"), dict) else {}
    if toolchain != _toolchain_identity(Path(repo_root)):
        return {"ok": False, "status": "stale", "reason": "rehearsal toolchain identity changed", "path": str(path), "receipt_digest": recorded_digest}
    runner = payload.get("runner") if isinstance(payload.get("runner"), dict) else {}
    if runner != _runner_identity(Path(repo_root)):
        return {"ok": False, "status": "stale", "reason": "rehearsal runner identity changed", "path": str(path), "receipt_digest": recorded_digest}
    remote = payload.get("remote_mutation") if isinstance(payload.get("remote_mutation"), dict) else {}
    audit = remote.get("audit") if isinstance(remote.get("audit"), dict) else {}
    if (
        remote.get("push_requested") is not False
        or remote.get("push_observed") is not False
        or remote.get("remote_refs_unchanged") is not True
        or remote.get("production_wrapper_invoked") is not False
        or remote.get("new_wrapper_runs")
        or audit.get("remote_refs") != "before-after-ls-remote"
        or audit.get("wrapper_runs") != "before-after-run-inventory"
    ):
        return {"ok": False, "status": "unsafe", "reason": "rehearsal remote or wrapper audit is not clean", "path": str(path), "receipt_digest": recorded_digest}
    return {"ok": True, "status": "verified", "path": str(path), "receipt_digest": recorded_digest, "repository": live_identity, "source": live_source}


def _validate_cycle(
    cycle: dict[str, Any],
    *,
    source_clone: Path,
    source_status_before: str,
    source_head_before: str,
    authority_digest_before: str,
) -> dict[str, Any]:
    if cycle.get("ok") is not True or cycle.get("status") != "completed":
        return _failure("cycle-terminal", "real organization cycle did not reach completed", evidence={"status": cycle.get("status"), "reason": cycle.get("reason")})

    maintenance = cycle.get("maintenance") if isinstance(cycle.get("maintenance"), dict) else {}
    contribution = cycle.get("contribution") if isinstance(cycle.get("contribution"), dict) else {}
    report = maintenance.get("report") if isinstance(maintenance.get("report"), dict) else {}
    cleanup = report.get("cleanup") if isinstance(report.get("cleanup"), dict) else {}
    checkpoints = cleanup.get("checkpoints") if isinstance(cleanup.get("checkpoints"), dict) else {}
    for name in REQUIRED_CHECKPOINTS:
        checkpoint = checkpoints.get(name)
        if not isinstance(checkpoint, dict):
            return _failure(name, "required checkpoint projection is missing", evidence={"available": sorted(checkpoints)})
        if checkpoint.get("complete") is not True:
            return _failure(name, "required checkpoint is incomplete", evidence=checkpoint)
        if name == "decision_apply" and checkpoint.get("exact") is not True:
            return _failure(name, "selected action ids do not exactly match applied action ids", evidence=checkpoint)
        if name == "post_apply" and checkpoint.get("ok") is not True:
            return _failure(name, "post-apply validation did not pass", evidence=checkpoint)
        if name in {"skill_safety", "skill_bundle_version"} and checkpoint.get("passed") is not True:
            return _failure(name, "Skill safety/version policy is not approved", evidence=checkpoint)
        if name == "card_surface" and int(checkpoint.get("privacy_risk_count") or 0) > 0:
            return _failure(name, "privacy boundary reported risk", evidence=checkpoint)

    maintenance_sync = maintenance.get("sync") if isinstance(maintenance.get("sync"), dict) else {}
    contribution_sync = contribution.get("sync") if isinstance(contribution.get("sync"), dict) else {}
    base_checkout = maintenance_sync.get("base_checkout")
    if not isinstance(base_checkout, dict) or base_checkout.get("ok") is not True:
        return _failure("long-path-checkout", "isolated organization base checkout did not pass", evidence=base_checkout)
    worktree = maintenance_sync.get("worktree")
    if not isinstance(worktree, dict) or str(worktree.get("mode") or "") != "isolated":
        return _failure("worktree-isolation", "maintenance did not use an isolated source worktree", evidence=worktree)
    worktree_cleanup = maintenance_sync.get("worktree_cleanup")
    if not isinstance(worktree_cleanup, dict) or worktree_cleanup.get("ok") is not True or worktree_cleanup.get("retained") is True:
        return _failure("worktree-cleanup", "disposable worktree cleanup was not confirmed", evidence=worktree_cleanup)
    effective_maintenance = str((maintenance_sync.get("worktree") or {}).get("effective_path") or (maintenance_sync.get("worktree") or {}).get("worktree_path") or "")
    effective_contribution = str((contribution_sync.get("worktree") or {}).get("effective_path") or (contribution_sync.get("worktree") or {}).get("worktree_path") or "")
    if effective_maintenance and effective_contribution and effective_maintenance != effective_contribution:
        return _failure("pinned-sync-context", "contribution did not reuse the maintenance effective source", evidence={"maintenance": effective_maintenance, "contribution": effective_contribution})

    snapshot = cycle.get("snapshot") if isinstance(cycle.get("snapshot"), dict) else {}
    if snapshot.get("ok") is not True or int(snapshot.get("schema_version") or 0) != 3 or not snapshot.get("generation_id"):
        return _failure("snapshot-cas", "immutable organization snapshot is not current and schema-3 complete", evidence=snapshot)
    if contribution.get("ok") is not True or cycle.get("postflight_recorded") is not True:
        return _failure("contribution-postflight", "contribution or structured postflight did not close", evidence={"contribution": contribution.get("ok"), "postflight": cycle.get("postflight_recorded")})

    status_after = _git_status(source_clone)
    head_after = _git_head(source_clone)
    if status_after != source_status_before or head_after != source_head_before:
        return _failure("source-preservation", "configured rehearsal source changed", evidence={"before": source_status_before, "after": status_after, "head_before": source_head_before, "head_after": head_after})
    pointer = authority_generation_pointer_path(Path(str((cycle.get("cycle_receipt_path") or ""))).parents[3]) if cycle.get("cycle_receipt_path") else None
    authority_after = _digest_file(pointer) if pointer else ""
    if authority_digest_before and authority_after and authority_after != authority_digest_before:
        return _failure("local-authority-boundary", "organization rehearsal changed local LogicGuard authority", evidence={"before": authority_digest_before, "after": authority_after})
    return {"checkpoint": "complete", "reason": "all rehearsal checks passed", "reopen_condition": "none"}


def run_organization_rehearsal(
    repo_root: Path,
    *,
    run_id: str = "",
) -> dict[str, Any]:
    """Run the real organization cycle safely without invoking the scheduled wrapper."""

    repo_root = Path(repo_root).resolve()
    settings = load_desktop_settings(repo_root)
    participation = maintenance_participation_status_from_settings(settings)
    sources = organization_sources_from_settings(settings)
    if not participation.get("available") or not sources:
        reason = str(participation.get("reason") or "organization mode is not connected to a validated repository")
        return {
            "schema_version": REHEARSAL_SCHEMA,
            "ok": True,
            "status": "not_applicable",
            "production_receipt": False,
            "reason": reason,
            "settings_gate": participation,
            "checkpoints": {},
        }

    source = sources[0]
    configured_source = Path(str(source.get("path") or "")).resolve()
    if not configured_source.exists():
        return {"schema_version": REHEARSAL_SCHEMA, "ok": False, "status": "failed", "production_receipt": False, "failure": _failure("source-preparation", "configured organization source is missing")}

    resolved_run_id = str(run_id or "organization-rehearsal")
    repository_before = _repository_identity(repo_root)
    configured_before = _configured_source_identity(configured_source)
    authority_before = _authority_identity(repo_root)
    wrapper_runs_before = _automation_run_inventory(repo_root)
    remote_refs_before = configured_before.get("remote_refs")
    result: dict[str, Any] = {
        "schema_version": REHEARSAL_SCHEMA,
        "ok": False,
        "status": "failed",
        "production_receipt": False,
        "run_id": resolved_run_id,
        "source": {
            "configured_path": str(configured_source),
            "configured_before": configured_before,
        },
        "repository": repository_before,
        "authority_before": authority_before,
        "settings_gate": participation,
        "toolchain": _toolchain_identity(repo_root),
        "runner": _runner_identity(repo_root),
        "checkpoint_inventory": {
            "required": list(REQUIRED_CHECKPOINTS),
            "sha256": _canonical_digest(list(REQUIRED_CHECKPOINTS)),
        },
    }
    rehearsal_dir = _RehearsalDirectory()
    with rehearsal_dir as temp_root:
        source_clone = temp_root / "organization-source"
        cloned = _clone_source(
            configured_source,
            source_clone,
            expected_head=str(configured_before.get("head") or ""),
        )
        if not cloned.get("ok"):
            result["validation"] = _failure("source-preparation", "disposable organization source could not be created", evidence=cloned)
        else:
            dirty_asset = source_clone / "assets" / "readme-hero" / "hero.png"
            if dirty_asset.exists():
                dirty_asset_digest = _digest_file(dirty_asset)
                dirty_asset.unlink()
                dirty_asset_action = "delete-existing-asset"
            else:
                dirty_asset = source_clone / ".rehearsal" / "unrelated-asset.txt"
                dirty_asset.parent.mkdir(parents=True, exist_ok=True)
                dirty_asset.write_text("synthetic unrelated asset edit\n", encoding="utf-8")
                dirty_asset_digest = _digest_file(dirty_asset)
                dirty_asset_action = "create-unrelated-asset"
            source_status_before = _git_status(source_clone)
            source_head_before = _git_head(source_clone)

            machine_root = temp_root / "machine"
            machine_settings = {
                "mode": ORGANIZATION_MODE,
                "organization": {
                    "repo_url": str(source.get("repo_url") or ""),
                    "local_mirror_path": str(source_clone),
                    "organization_id": str(source.get("organization_id") or "sandbox"),
                    "validated": True,
                    "validation_status": "valid",
                    "organization_maintenance_requested": True,
                },
            }
            bootstrap = _bootstrap_machine(machine_root, machine_settings)
            if not bootstrap.get("ok"):
                result["validation"] = _failure("local-authority-boundary", "disposable machine bootstrap failed", evidence=bootstrap)
            else:
                authority_digest_before = _digest_file(Path(str(bootstrap.get("authority_pointer") or "")))

                # This is the sole allowed rehearsal owner call.  The scheduled
                # wrapper is intentionally never imported or invoked here.
                cycle = run_organization_cycle(machine_root, run_id=resolved_run_id, push=False)
                validation = _validate_cycle(
                    cycle,
                    source_clone=source_clone,
                    source_status_before=source_status_before,
                    source_head_before=source_head_before,
                    authority_digest_before=authority_digest_before,
                )
                result.update(
                    {
                        "ok": bool(validation.get("checkpoint") == "complete"),
                        "status": "completed" if validation.get("checkpoint") == "complete" else "failed",
                        "source": {
                            **result["source"],
                            "disposable_path": str(source_clone),
                            "head": source_head_before,
                            "dirty_status": source_status_before,
                            "dirty_asset_action": dirty_asset_action,
                            "dirty_asset_sha256": dirty_asset_digest,
                        },
                        "cycle": cycle,
                        "checkpoints": ((cycle.get("maintenance") or {}).get("report") or {}).get("cleanup", {}).get("checkpoints", {}),
                        "validation": validation,
                    }
                )
    cleanup = dict(rehearsal_dir.cleanup)
    configured_after = _configured_source_identity(configured_source)
    authority_after = _authority_identity(repo_root)
    wrapper_runs_after = _automation_run_inventory(repo_root)
    remote_refs_after = configured_after.get("remote_refs")
    source_unchanged = configured_before == configured_after
    authority_unchanged = authority_before == authority_after
    remote_unchanged = remote_refs_before == remote_refs_after
    wrapper_delta = sorted(set(wrapper_runs_after) - set(wrapper_runs_before))
    result.setdefault("source", {})
    result["source"].update(
        {
            "configured_after": configured_after,
            "configured_unchanged": source_unchanged,
            "configured_authority_unchanged": authority_unchanged,
        }
    )
    result["authority_after"] = authority_after
    result["cleanup"] = cleanup
    result["remote_mutation"] = {
        "push_requested": False,
        "push_observed": not remote_unchanged,
        "remote_refs_before": remote_refs_before,
        "remote_refs_after": remote_refs_after,
        "remote_refs_unchanged": remote_unchanged,
        "production_wrapper_invoked": bool(wrapper_delta),
        "new_wrapper_runs": wrapper_delta,
        "wrapper_runs_before": wrapper_runs_before,
        "wrapper_runs_after": wrapper_runs_after,
        "audit": {
            "remote_refs": "before-after-ls-remote",
            "wrapper_runs": "before-after-run-inventory",
        },
    }
    if result.get("ok") is True and not source_unchanged:
        result["ok"] = False
        result["status"] = "failed"
        result["validation"] = _failure("configured-source-preservation", "configured organization source identity changed during rehearsal", evidence={"before": configured_before, "after": configured_after})
    elif result.get("ok") is True and not authority_unchanged:
        result["ok"] = False
        result["status"] = "failed"
        result["validation"] = _failure("local-authority-preservation", "real local LogicGuard authority changed during rehearsal", evidence={"before": authority_before, "after": authority_after})
    elif result.get("ok") is True and not remote_unchanged:
        result["ok"] = False
        result["status"] = "failed"
        result["validation"] = _failure("remote-mutation-boundary", "remote organization refs changed during no-push rehearsal", evidence={"before": remote_refs_before, "after": remote_refs_after})
    elif result.get("ok") is True and wrapper_delta:
        result["ok"] = False
        result["status"] = "failed"
        result["validation"] = _failure("scheduled-wrapper-boundary", "scheduled organization wrapper created a run during rehearsal", evidence=wrapper_delta)
    elif result.get("ok") is True and cleanup.get("ok") is not True:
        result["ok"] = False
        result["status"] = "failed"
        result["validation"] = _failure("temporary-cleanup", "rehearsal temporary directory cleanup was not confirmed", evidence=cleanup)
    result["repository_after"] = _repository_identity(repo_root)
    result["repository_unchanged"] = result["repository"] == result["repository_after"]
    if result.get("ok") is True and not result["repository_unchanged"]:
        result["ok"] = False
        result["status"] = "failed"
        result["validation"] = _failure("repository-preservation", "repository source identity changed during rehearsal", evidence={"before": result["repository"], "after": result["repository_after"]})
    receipt = persist_rehearsal_receipt(repo_root, result)
    result["receipt"] = receipt
    # The persisted digest covers the result before the receipt pointer itself;
    # callers can use the returned receipt metadata to locate the immutable copy.
    return result


def print_rehearsal_json(result: dict[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, default=str)
