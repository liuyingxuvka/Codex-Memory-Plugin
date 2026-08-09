#!/usr/bin/env python3
"""Run one target-owned KB maintenance automation to a native terminal."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tomllib
from uuid import uuid4


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from local_kb.automation_contracts import (  # noqa: E402
    AGGREGATE_ASSURANCE_TIMEOUT_SECONDS,
    AUTOMATION_COMPLETION_CONTRACTS,
    PRE_RESTORE_ASSURANCE_TIMEOUT_SECONDS,
    SLEEP_NATIVE_SOFT_DEADLINE_SECONDS,
    native_timeout_seconds,
    owner_timeout_seconds,
)
from local_kb.automation_runtime import (  # noqa: E402
    RUNTIME_WRAPPER_SCHEMA,
    automation_run_root,
    build_native_receipt,
    validate_native_receipt,
    write_native_receipt,
)
from local_kb.cli_output import print_json  # noqa: E402
from local_kb.config import default_codex_home, resolve_repo_root  # noqa: E402
from local_kb.install import resolve_explicit_automation_runtime  # noqa: E402
from local_kb.maintenance_lanes import (  # noqa: E402
    recover_global_write_lease_after_cleanup,
)
from local_kb.process_control import process_tree_pids, run_with_timeout_cleanup  # noqa: E402
from local_kb.maintenance_lanes import process_owner_is_alive  # noqa: E402


SUPPORTED_SKILLS = (
    "kb-sleep-maintenance",
    "kb-dream-pass",
    "kb-organization-contribute",
    "kb-organization-maintenance",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_id(skill_id: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return f"native-{skill_id}-{stamp}-{uuid4().hex[:8]}"


def native_command(skill_id: str, *, repo_root: Path, run_id: str) -> list[str]:
    commands = {
        "kb-sleep-maintenance": [
            sys.executable,
            ".agents/skills/local-kb-retrieve/scripts/kb_sleep.py",
            "--repo-root",
            str(repo_root),
            "--run-id",
            run_id,
            "--soft-deadline-seconds",
            str(SLEEP_NATIVE_SOFT_DEADLINE_SECONDS),
            "--json",
        ],
        "kb-dream-pass": [
            sys.executable,
            ".agents/skills/local-kb-retrieve/scripts/kb_dream.py",
            "--repo-root",
            str(repo_root),
            "--run-id",
            run_id,
            "--json",
        ],
        "kb-organization-contribute": [
            sys.executable,
            "scripts/kb_org_outbox.py",
            "--repo-root",
            str(repo_root),
            "--automation",
            "--run-id",
            run_id,
        ],
        "kb-organization-maintenance": [
            sys.executable,
            "scripts/kb_org_maintainer.py",
            "--repo-root",
            str(repo_root),
            "--automation",
            "--cycle",
            "--run-id",
            run_id,
        ],
    }
    return commands[skill_id]


def _parse_payload(stdout: str) -> dict:
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


OWNER_MANIFEST_SCHEMA = "khaos-brain.automation-owner-manifest.v1"


def _write_owner_manifest(path: Path, payload: dict[str, object]) -> dict[str, object]:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)
    return payload


def _read_owner_manifest(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return dict(payload) if isinstance(payload, dict) else {}


def _reconcile_abandoned_owner_manifests(
    skill_id: str,
    *,
    repo_root: Path,
) -> list[dict[str, object]]:
    """Recover only owners with durable job supervision and zero descendants.

    A wrapper can be terminated before it writes a native receipt.  The
    manifest makes that gap visible.  Automatic lease recovery is intentionally
    narrower than ordinary lock acquisition: Windows Job Object supervision
    must have been attached, the recorded wrapper and every captured process
    must be gone, and the lease run id must match exactly.
    """

    automation_root = Path(repo_root) / ".local" / "automation-runs"
    # A failed Sleep owner can leave the shared global writer lease that blocks
    # the next Organization owner.  Reconciliation therefore scans every
    # target-owned manifest before the current owner attempts acquisition; it
    # never adopts a live owner and never loosens the exact run-id/zero-tree
    # cleanup proof.
    skill_roots = [skill_id, *(item for item in SUPPORTED_SKILLS if item != skill_id)]
    outcomes: list[dict[str, object]] = []
    manifest_paths = [
        path
        for candidate_skill in skill_roots
        for path in (automation_root / candidate_skill).glob("*/owner-manifest.json")
    ]
    for manifest_path in sorted(manifest_paths):
        manifest = _read_owner_manifest(manifest_path)
        if not manifest or manifest.get("status") != "running":
            continue
        run_id = str(manifest.get("run_id") or "")
        owner_pid = int(manifest.get("wrapper_pid") or 0)
        supervision = manifest.get("job_object_supervision")
        supervision = supervision if isinstance(supervision, dict) else {}
        captured = [
            int(item)
            for item in supervision.get("captured_process_ids", [])
            if str(item).isdigit()
        ]
        if not run_id or owner_pid <= 0 or process_owner_is_alive(owner_pid):
            continue
        descendant_pids = [pid for pid in captured if process_owner_is_alive(pid)]
        if supervision.get("status") != "attached" or descendant_pids:
            outcome = {
                "run_id": run_id,
                "source_skill_id": str(manifest.get("skill_id") or ""),
                "requested_skill_id": skill_id,
                "status": "abandoned-unverified",
                "reason": "owner-supervision-or-descendant-cleanup-unverified",
                "manifest_path": str(manifest_path),
                "remaining_process_ids": descendant_pids,
            }
            manifest.update({"status": "abandoned-unverified", "reconciled_at": _utc_now(), "outcome": outcome})
            _write_owner_manifest(manifest_path, manifest)
            outcomes.append(outcome)
            continue
        cleanup = {
            "cleanup_confirmed": True,
            "remaining_process_count": 0,
            "remaining_process_ids": [],
            "captured_process_ids": captured,
            "captured_process_count": len(captured),
            "root_pid": owner_pid,
            "recovery_basis": "windows-job-object-kill-on-close",
        }
        recovery = recover_global_write_lease_after_cleanup(
            repo_root,
            expected_root_owner_run_id=run_id,
            cleanup_evidence=cleanup,
        )
        outcome = {
            "run_id": run_id,
            "source_skill_id": str(manifest.get("skill_id") or ""),
            "requested_skill_id": skill_id,
            "status": "abandoned-recovered" if recovery.get("ok") else "abandoned-unverified",
            "manifest_path": str(manifest_path),
            "cleanup": cleanup,
            "global_writer_recovery": recovery,
        }
        manifest.update({"status": outcome["status"], "reconciled_at": _utc_now(), "outcome": outcome})
        _write_owner_manifest(manifest_path, manifest)
        outcomes.append(outcome)
    return outcomes


def _installed_runtime(
    skill_id: str,
    *,
    codex_home: Path,
) -> dict[str, object]:
    """Read the exact installed runtime projection for scheduled owners."""

    automation_id = str(
        AUTOMATION_COMPLETION_CONTRACTS.get(skill_id, {}).get("automation_id") or ""
    ).strip()
    if not automation_id:
        return {"required": False, "ok": True, "status": "not_applicable"}
    path = Path(codex_home) / "automations" / automation_id / "automation.toml"
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return {
            "required": True,
            "ok": False,
            "status": "unavailable",
            "path": str(path),
            "reason": f"installed-runtime-unreadable:{type(exc).__name__}",
        }
    model = str(payload.get("model") or "").strip()
    effort = str(payload.get("reasoning_effort") or "").strip()
    if not model or not effort:
        return {
            "required": True,
            "ok": False,
            "status": "invalid",
            "path": str(path),
            "reason": "installed-runtime-missing-model-or-reasoning-effort",
        }
    if automation_id in {"kb-sleep", "kb-org-maintenance"}:
        try:
            provider_runtime = resolve_explicit_automation_runtime(
                automation_id,
                codex_home,
            )
        except RuntimeError as exc:
            return {
                "required": True,
                "ok": False,
                "status": "invalid",
                "path": str(path),
                "reason": f"provider-runtime-unavailable:{exc}",
            }
        if (
            model != provider_runtime.get("model")
            or effort != provider_runtime.get("reasoning_effort")
        ):
            return {
                "required": True,
                "ok": False,
                "status": "drifted",
                "path": str(path),
                "model": model,
                "reasoning_effort": effort,
                "expected_model": provider_runtime.get("model"),
                "expected_reasoning_effort": provider_runtime.get("reasoning_effort"),
                "reason": "installed-runtime-does-not-match-explicit-provider-selection",
            }
        return {
            "required": True,
            "ok": True,
            "status": "current",
            "path": str(path),
            "model": model,
            "reasoning_effort": effort,
            "selection_policy": provider_runtime.get("selection_policy"),
            "provider": provider_runtime.get("provider"),
            "provider_revision": provider_runtime.get("provider_revision"),
            "models_cache_digest": provider_runtime.get("models_cache_digest"),
            "runtime_config_digest": provider_runtime.get("runtime_config_digest"),
        }
    return {
        "required": True,
        "ok": True,
        "status": "current",
        "path": str(path),
        "model": model,
        "reasoning_effort": effort,
    }


def run_automation(
    skill_id: str,
    *,
    repo_root: Path,
    codex_home: Path,
    scheduler_or_trigger_id: str = "",
) -> dict:
    run_id = _run_id(skill_id)
    run_root = automation_run_root(repo_root, skill_id, run_id)
    command = native_command(skill_id, repo_root=repo_root, run_id=run_id)
    native_timeout = native_timeout_seconds(skill_id)
    owner_timeout = owner_timeout_seconds(skill_id)
    started_at = _utc_now()
    owner_manifest_path = run_root / "owner-manifest.json"
    owner_recovery = _reconcile_abandoned_owner_manifests(
        skill_id,
        repo_root=repo_root,
    )
    owner_manifest: dict[str, object] = {
        "schema_version": OWNER_MANIFEST_SCHEMA,
        "status": "running",
        "run_id": run_id,
        "skill_id": skill_id,
        "wrapper_pid": os.getpid(),
        "command": [str(item) for item in command],
        "native_timeout_seconds": native_timeout,
        "owner_timeout_seconds": owner_timeout,
        "started_at": started_at,
        "owner_recovery_before_start": owner_recovery,
    }
    _write_owner_manifest(owner_manifest_path, owner_manifest)
    cleanup: dict[str, object] = {}
    global_writer_recovery: dict[str, object] = {}
    runtime = _installed_runtime(skill_id, codex_home=codex_home)
    if runtime.get("required") and runtime.get("ok") is not True:
        exit_code = 78
        stdout = json.dumps(
            {
                "run_id": run_id,
                "status": "failed",
                "final_run_state": "failed",
                "reason": "automation-runtime-selection-invalid",
                "runtime": runtime,
            },
            ensure_ascii=False,
        )
        stderr = str(runtime.get("reason") or "automation-runtime-selection-invalid")
    else:
        try:
            def _record_started(supervision: dict[str, object]) -> None:
                owner_manifest.update(
                    {
                        "child_pid": supervision.get("root_pid"),
                        "job_object_supervision": supervision,
                    }
                )
                _write_owner_manifest(owner_manifest_path, owner_manifest)

            completed = run_with_timeout_cleanup(
                command,
                cwd=repo_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
                timeout=native_timeout,
                started_callback=_record_started,
            )
            exit_code = completed.returncode
            stdout = completed.stdout
            stderr = completed.stderr
            owner_manifest.update(
                {
                    "status": "completed",
                    "finished_at": _utc_now(),
                    "returncode": exit_code,
                    "job_object_supervision": getattr(
                        completed, "job_object_supervision", {}
                    ),
                }
            )
        except subprocess.TimeoutExpired as exc:
            exit_code = 124
            stdout = str(exc.stdout or "")
            stderr = str(exc.stderr or "")
            cleanup = dict(getattr(exc, "cleanup_receipt", {}) or {})
            global_writer_recovery = recover_global_write_lease_after_cleanup(
                repo_root,
                expected_root_owner_run_id=run_id,
                cleanup_evidence=cleanup,
            )
            owner_manifest.update(
                {
                    "status": "timed-out",
                    "finished_at": _utc_now(),
                    "returncode": 124,
                    "timeout_cleanup": cleanup,
                    "global_writer_recovery": global_writer_recovery,
                }
            )
        finally:
            _write_owner_manifest(owner_manifest_path, owner_manifest)
    if owner_manifest.get("status") == "running":
        owner_manifest.update(
            {
                "status": "failed-before-native-start",
                "finished_at": _utc_now(),
                "returncode": exit_code,
            }
        )
        _write_owner_manifest(owner_manifest_path, owner_manifest)
    payload = _parse_payload(stdout)
    payload.setdefault("runtime", runtime)
    if skill_id == "kb-sleep-maintenance" and exit_code == 124:
        payload.update(
            {
                "run_id": run_id,
                "final_run_state": "failed",
                "reason": "sleep-native-hard-timeout",
                "downstream_stages": {
                    stage_id: {
                        "status": "not_run",
                        "reason": "sleep-native-hard-timeout",
                    }
                    for stage_id in ("dream",)
                },
            }
        )
    if exit_code == 124:
        payload["global_writer_recovery"] = global_writer_recovery
    payload["_owner_timeout_policy"] = {
        "soft_deadline_seconds": (
            SLEEP_NATIVE_SOFT_DEADLINE_SECONDS
            if skill_id == "kb-sleep-maintenance"
            else 0
        ),
        "native_timeout_seconds": native_timeout,
        "owner_timeout_seconds": owner_timeout,
        "aggregate_timeout_seconds": AGGREGATE_ASSURANCE_TIMEOUT_SECONDS,
        "installer_timeout_seconds": PRE_RESTORE_ASSURANCE_TIMEOUT_SECONDS,
        "timed_out": exit_code == 124,
        "cleanup_confirmed": (
            cleanup.get("cleanup_confirmed") is True if exit_code == 124 else True
        ),
        "remaining_process_count": int(cleanup.get("remaining_process_count") or 0),
    }
    receipt = build_native_receipt(
        skill_id,
        run_id=run_id,
        command=command,
        native_payload=payload,
        exit_code=exit_code,
        started_at=started_at,
        finished_at=_utc_now(),
    )
    receipt_path = write_native_receipt(run_root / "native-receipt.json", receipt)
    validation = validate_native_receipt(
        receipt_path,
        skill_id=skill_id,
        expected_run_id=run_id,
        expected_receipt_hash=str(receipt.get("receipt_hash") or ""),
    )
    terminal = str(receipt.get("terminal_status") or "failed")
    result = {
        "schema_version": RUNTIME_WRAPPER_SCHEMA,
        "ok": validation.get("ok") is True,
        "status": terminal if validation.get("ok") is True else "failed",
        "skill_id": skill_id,
        "automation_id": AUTOMATION_COMPLETION_CONTRACTS[skill_id]["automation_id"],
        "execution_kind": AUTOMATION_COMPLETION_CONTRACTS[skill_id]["execution_kind"],
        "scheduler_or_trigger_id": (
            scheduler_or_trigger_id
            or str(AUTOMATION_COMPLETION_CONTRACTS[skill_id]["automation_id"])
        ),
        "run_id": run_id,
        "runtime": runtime,
        "native_receipt_path": str(receipt_path),
        "native_receipt_hash": receipt.get("receipt_hash"),
        "native_receipt_validation": validation,
        "native_exit_code": exit_code,
        "native_stderr_tail": stderr[-3000:],
        "timeout_cleanup": cleanup,
        "global_writer_recovery": global_writer_recovery,
        "owner_recovery_before_start": owner_recovery,
        "owner_manifest_path": str(owner_manifest_path),
        "issues": [
            *list(receipt.get("evaluation_issues", [])),
            *list(validation.get("issues", [])),
        ],
        "claim_boundary": (
            "This target-owned wrapper proves only the captured native terminal and "
            "the skill's own obligation evidence for this exact run."
        ),
    }
    run_root.mkdir(parents=True, exist_ok=True)
    report_path = run_root / "execution-result.json"
    report_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    result["execution_result_path"] = str(report_path)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skill", required=True, choices=SUPPORTED_SKILLS)
    parser.add_argument("--repo-root", default="auto")
    parser.add_argument("--codex-home", default="")
    parser.add_argument("--scheduler-or-trigger-id", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    codex_home = (
        Path(args.codex_home).expanduser().resolve()
        if args.codex_home
        else default_codex_home()
    )
    repo_root = resolve_repo_root(args.repo_root, cwd=REPO_ROOT, codex_home=codex_home)
    result = run_automation(
        args.skill,
        repo_root=repo_root,
        codex_home=codex_home,
        scheduler_or_trigger_id=args.scheduler_or_trigger_id,
    )
    print_json(result, sort_keys=True)
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
