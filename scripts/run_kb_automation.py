#!/usr/bin/env python3
"""Run one target-owned KB maintenance automation to a native terminal."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
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
from local_kb.process_control import run_with_timeout_cleanup  # noqa: E402


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
    cleanup: dict[str, object] = {}
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
            completed = run_with_timeout_cleanup(
                command,
                cwd=repo_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
                timeout=native_timeout,
            )
            exit_code = completed.returncode
            stdout = completed.stdout
            stderr = completed.stderr
        except subprocess.TimeoutExpired as exc:
            exit_code = 124
            stdout = str(exc.stdout or "")
            stderr = str(exc.stderr or "")
            cleanup = dict(getattr(exc, "cleanup_receipt", {}) or {})
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
