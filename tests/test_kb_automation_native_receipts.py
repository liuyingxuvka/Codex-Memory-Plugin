from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from local_kb.automation_contracts import (
    AGGREGATE_ASSURANCE_TIMEOUT_SECONDS,
    AUTOMATION_COMPLETION_CONTRACTS,
    PRE_RESTORE_ASSURANCE_TIMEOUT_SECONDS,
    SLEEP_CYCLE_NATIVE_TIMEOUT_SECONDS,
    SLEEP_CYCLE_OWNER_TIMEOUT_SECONDS,
    SLEEP_NATIVE_SOFT_DEADLINE_SECONDS,
    obligation_id,
)
from local_kb.automation_runtime import (
    _real_artifact_issues,
    _sleep_downstream_not_run,
    build_fixture_payload,
    build_native_receipt,
    evaluate_native_payload,
    validate_native_receipt,
    write_native_receipt,
)
from tests.current_runtime_helpers import activate_current_kb_runtime
from local_kb.lifecycle import run_incremental_sleep
from scripts.run_kb_automation import native_command, run_automation


def _sleep_batch_digest(value: object) -> str:
    canonical = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _refresh_sleep_batch_head(payload: dict[str, object]) -> None:
    checkpoint = payload["batch_checkpoint"]
    payload["batch_head"] = {
        **payload["batch_head"],
        "plan_digest": _sleep_batch_digest(payload["batch_plan"]),
        "checkpoint_digest": _sleep_batch_digest(checkpoint),
        "checkpoint_revision": checkpoint["revision"],
        "settled": checkpoint["settled"],
        "updated_at": checkpoint["updated_at"],
    }


def _write_explicit_automation_runtime(codex_home: Path) -> None:
    """Provide the current provider authority required by scheduled-owner tests."""

    codex_home.mkdir(parents=True, exist_ok=True)
    (codex_home / "models_cache.json").write_text(
        json.dumps(
            {
                "models": [
                    {
                        "slug": "gpt-5.6-luna",
                        "supported_reasoning_levels": [{"effort": "max"}],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    for automation_id in ("kb-sleep", "kb-org-maintenance"):
        path = codex_home / "automations" / automation_id / "automation.toml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            'model = "gpt-5.6-luna"\nreasoning_effort = "max"\n',
            encoding="utf-8",
        )


def test_sleep_downstream_gate_is_local_only() -> None:
    reason = "sleep-progress-saved"
    local_only = {
        "downstream_stages": {
            "dream": {"status": "not_run", "reason": reason},
        }
    }
    cross_task = {
        "downstream_stages": {
            "dream": {"status": "not_run", "reason": reason},
            "organization-cycle": {"status": "not_run", "reason": reason},
        }
    }

    assert _sleep_downstream_not_run(local_only, reason=reason)
    assert not _sleep_downstream_not_run(cross_task, reason=reason)


def _assert_only_gate_performed(
    skill_id: str,
    evidence: dict[str, dict[str, object]],
    gate_suffix: str,
) -> None:
    gate_id = obligation_id(skill_id, gate_suffix)
    performed = {
        item_id
        for item_id, row in evidence.items()
        if row.get("outcome") == "performed"
    }
    assert performed == {gate_id}
    for item_id, row in evidence.items():
        if item_id == gate_id:
            continue
        assert row["outcome"] == "not_applicable"
        assert row["applicability"]["evaluated"] is True
        assert row["applicability"]["applicable"] is False
        assert row["non_mutation"]["proven"] is True
        assert row["non_mutation"]["mutation_performed"] is False
        assert row["non_mutation"]["gate_facts_hash"]
        assert row["terminal_gate"]["evaluated"] is True
        assert row["terminal_gate"]["applicable"] is False
        assert row["terminal_gate"]["mutation_performed"] is False


def test_real_sleep_receipt_requires_exact_lock_owner_and_release() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        payload = run_incremental_sleep(Path(tmp), run_id="sleep-native-lock")
        payload["lifecycle_review"].pop("ok", None)

        current = evaluate_native_payload(
            "kb-sleep-maintenance",
            payload,
            exit_code=0,
            expected_run_id="sleep-native-lock",
        )
        assert current["ok"], current

        wrong_owner = {
            **payload,
            "lane_lock": {**payload["lane_lock"], "run_id": "another-run"},
        }
        wrong_owner_result = evaluate_native_payload(
            "kb-sleep-maintenance",
            wrong_owner,
            exit_code=0,
            expected_run_id="sleep-native-lock",
        )
        assert not wrong_owner_result["ok"]
        assert not wrong_owner_result["evidence"][
            obligation_id("kb-sleep-maintenance", "lane-delta-intake")
        ]["ok"]

        unreleased = {
            **payload,
            "lock_release": {**payload["lock_release"], "released": False},
        }
        unreleased_result = evaluate_native_payload(
            "kb-sleep-maintenance",
            unreleased,
            exit_code=0,
            expected_run_id="sleep-native-lock",
        )
        assert not unreleased_result["ok"]
        assert not unreleased_result["evidence"][
            obligation_id("kb-sleep-maintenance", "index-watermark-commit")
        ]["ok"]
        assert not unreleased_result["evidence"][
            obligation_id("kb-sleep-maintenance", "failure-fail-closed")
        ]["ok"]


def _progress_saved_sleep_payload() -> dict[str, object]:
    payload = build_fixture_payload(
        "kb-sleep-maintenance",
        run_id="sleep-progress-saved",
    )
    payload["final_run_state"] = "progress_saved"
    payload["reason"] = "sleep-progress-saved"
    payload["output_watermark"] = payload["input_watermark"]
    payload["completed_this_attempt"] = 1
    payload["blocked_this_attempt"] = 0
    payload["closing_remaining"] = 1
    payload["net_reduction"] = 0
    payload["convergence_status"] = "backlog_growing"
    payload["batch_checkpoint"] = {
        **payload["batch_checkpoint"],
        "revision": 1,
        "state": "in_progress",
        "settled": False,
        "completed_item_ids": ["fixture-item-prior"],
        "blocked_item_ids": [],
        "pending_item_ids": ["fixture-item-new"],
        "completed_count": 1,
        "blocked_count": 0,
        "pending_count": 1,
        "processed_count": 1,
        "closing_remaining_count": 1,
        "net_reduction": 1,
        "remainder_delta_from_prior": 0,
        "remainder_trend": "flat",
        "no_reduction_streak": 1,
        "backlog_growing": False,
    }
    payload["downstream_stages"] = {
        stage_id: {
            "status": "not_run",
            "reason": "sleep-progress-saved",
        }
        for stage_id in (
        "dream",
        )
    }
    _refresh_sleep_batch_head(payload)
    return payload


def test_sleep_progress_saved_receipt_binds_frozen_batch_and_local_dream_gate() -> None:
    payload = _progress_saved_sleep_payload()

    result = evaluate_native_payload(
        "kb-sleep-maintenance",
        payload,
        exit_code=0,
        expected_run_id="sleep-progress-saved",
    )

    assert result["ok"], result
    assert result["terminal_status"] == "progress_saved"
    assert result["evidence"][
        obligation_id("kb-sleep-maintenance", "frozen-batch-plan")
    ]["outcome"] == "performed"
    assert result["evidence"][
        obligation_id("kb-sleep-maintenance", "progress-checkpoint")
    ]["outcome"] == "performed"
    assert result["evidence"][
        obligation_id("kb-sleep-maintenance", "atomic-model-generation")
    ]["outcome"] == "not_run"
    assert result["evidence"][
        obligation_id("kb-sleep-maintenance", "downstream-not-run")
    ]["ok"] is True


def test_sleep_progress_saved_receipt_rejects_remaining_mismatch() -> None:
    payload = _progress_saved_sleep_payload()
    payload["closing_remaining"] = 2

    result = evaluate_native_payload(
        "kb-sleep-maintenance",
        payload,
        exit_code=0,
        expected_run_id="sleep-progress-saved",
    )

    assert not result["ok"]
    assert not result["evidence"][
        obligation_id("kb-sleep-maintenance", "remaining-reconciliation")
    ]["ok"]


def test_sleep_progress_saved_receipt_rejects_expanded_frozen_batch() -> None:
    payload = _progress_saved_sleep_payload()
    payload["batch_plan"]["eligible_item_ids"].append("later-arrival")

    result = evaluate_native_payload(
        "kb-sleep-maintenance",
        payload,
        exit_code=0,
        expected_run_id="sleep-progress-saved",
    )

    assert not result["ok"]
    assert not result["evidence"][
        obligation_id("kb-sleep-maintenance", "frozen-batch-plan")
    ]["ok"]


def test_sleep_progress_saved_receipt_rejects_downstream_stage_that_ran() -> None:
    payload = _progress_saved_sleep_payload()
    payload = copy.deepcopy(payload)
    payload["downstream_stages"]["dream"] = {
        "status": "completed",
        "reason": "",
    }

    result = evaluate_native_payload(
        "kb-sleep-maintenance",
        payload,
        exit_code=0,
        expected_run_id="sleep-progress-saved",
    )

    assert not result["ok"]
    assert not result["evidence"][
        obligation_id("kb-sleep-maintenance", "downstream-not-run")
    ]["ok"]
    assert not result["evidence"][
        obligation_id("kb-sleep-maintenance", "failure-fail-closed")
    ]["ok"]


def test_sleep_completed_with_blocks_gates_only_local_dream() -> None:
    payload = build_fixture_payload(
        "kb-sleep-maintenance",
        run_id="sleep-completed-with-blocks",
    )
    payload["final_run_state"] = "completed_with_blocks"
    payload["completed_this_attempt"] = 1
    payload["blocked_this_attempt"] = 1
    payload["convergence_status"] = "settled"
    payload["batch_checkpoint"] = {
        **payload["batch_checkpoint"],
        "state": "settled_with_blocks",
        "completed_item_ids": ["fixture-item-prior"],
        "blocked_item_ids": ["fixture-item-new"],
        "completed_count": 1,
        "blocked_count": 1,
        "processed_count": 2,
    }
    payload["blocked_items"] = [
        {
            "item_id": "fixture-item-new",
            "owner": "kb-sleep",
            "reopen_condition": "qualifying-input-arrives",
        }
    ]
    payload["downstream_stages"] = {
        stage_id: {
            "status": "not_run",
            "reason": "sleep-completed-with-blocks",
        }
        for stage_id in (
        "dream",
        )
    }
    _refresh_sleep_batch_head(payload)

    result = evaluate_native_payload(
        "kb-sleep-maintenance",
        payload,
        exit_code=0,
        expected_run_id="sleep-completed-with-blocks",
    )

    assert result["ok"], result
    assert result["terminal_status"] == "completed_with_blocks"
    assert result["evidence"][
        obligation_id("kb-sleep-maintenance", "atomic-model-generation")
    ]["ok"] is True
    assert result["evidence"][
        obligation_id("kb-sleep-maintenance", "downstream-not-run")
    ]["outcome"] == "performed"


def test_sleep_progress_saved_is_a_valid_unfinished_native_terminal() -> None:
    payload = _progress_saved_sleep_payload()
    receipt = build_native_receipt(
        "kb-sleep-maintenance",
        run_id="sleep-progress-saved",
        command=["fixture", "positive", "kb-sleep-maintenance"],
        native_payload=payload,
        exit_code=0,
        started_at="2026-07-22T00:00:00+00:00",
        finished_at="2026-07-22T00:01:00+00:00",
        fixture="positive",
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = write_native_receipt(Path(tmp) / "native-receipt.json", receipt)
        validation = validate_native_receipt(
            path,
            skill_id="kb-sleep-maintenance",
            expected_run_id="sleep-progress-saved",
            expected_receipt_hash=receipt["receipt_hash"],
            allow_fixture=True,
        )

    assert receipt["terminal_status"] == "progress_saved"
    assert validation["ok"], validation


def test_sleep_wrapper_binds_the_cooperative_deadline_once() -> None:
    command = native_command(
        "kb-sleep-maintenance",
        repo_root=Path("C:/fixture-kb"),
        run_id="sleep-deadline",
    )

    assert command.count("--soft-deadline-seconds") == 1
    index = command.index("--soft-deadline-seconds")
    assert command[index + 1] == str(SLEEP_NATIVE_SOFT_DEADLINE_SECONDS)


def test_sleep_wrapper_uses_cycle_budget_and_declares_the_complete_timeout_tree() -> None:
    completed = subprocess.CompletedProcess(args=["sleep-native"], returncode=1, stdout="{}", stderr="")
    with tempfile.TemporaryDirectory() as tmp, patch(
        "scripts.run_kb_automation.run_with_timeout_cleanup",
        return_value=completed,
    ) as owner:
        root = Path(tmp)
        _write_explicit_automation_runtime(root / ".codex")
        result = run_automation(
            "kb-sleep-maintenance",
            repo_root=root,
            codex_home=root / ".codex",
        )
        receipt = json.loads(Path(result["native_receipt_path"]).read_text(encoding="utf-8"))

    assert owner.call_args.kwargs["timeout"] == SLEEP_CYCLE_NATIVE_TIMEOUT_SECONDS
    assert receipt["native_payload"]["_owner_timeout_policy"] == {
        "soft_deadline_seconds": SLEEP_NATIVE_SOFT_DEADLINE_SECONDS,
        "native_timeout_seconds": SLEEP_CYCLE_NATIVE_TIMEOUT_SECONDS,
        "owner_timeout_seconds": SLEEP_CYCLE_OWNER_TIMEOUT_SECONDS,
        "aggregate_timeout_seconds": AGGREGATE_ASSURANCE_TIMEOUT_SECONDS,
        "installer_timeout_seconds": PRE_RESTORE_ASSURANCE_TIMEOUT_SECONDS,
        "timed_out": False,
        "cleanup_confirmed": True,
        "remaining_process_count": 0,
    }


def test_sleep_hard_timeout_records_local_dream_as_not_run() -> None:
    timeout = subprocess.TimeoutExpired(
        cmd=["sleep-native"],
        timeout=900,
        output="",
        stderr="",
    )
    timeout.cleanup_receipt = {
        "cleanup_confirmed": True,
        "remaining_process_count": 0,
    }
    with tempfile.TemporaryDirectory() as tmp, patch(
        "scripts.run_kb_automation.run_with_timeout_cleanup",
        side_effect=timeout,
    ):
        root = Path(tmp)
        _write_explicit_automation_runtime(root / ".codex")
        result = run_automation(
            "kb-sleep-maintenance",
            repo_root=root,
            codex_home=root / ".codex",
        )
        receipt = json.loads(
            Path(result["native_receipt_path"]).read_text(encoding="utf-8")
        )

    assert result["status"] == "failed"
    assert result["native_exit_code"] == 124
    assert result["timeout_cleanup"]["cleanup_confirmed"] is True
    assert receipt["native_payload"]["downstream_stages"] == {
        stage_id: {
            "status": "not_run",
            "reason": "sleep-native-hard-timeout",
        }
        for stage_id in (
            "dream",
        )
    }


def test_sleep_native_entrypoint_accepts_cooperative_deadline_and_emits_canonical_json() -> None:
    repo = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory() as tmp:
        activate_current_kb_runtime(Path(tmp))
        completed = subprocess.run(
            [
                sys.executable,
                str(repo / ".agents/skills/local-kb-retrieve/scripts/kb_sleep.py"),
                "--repo-root",
                tmp,
                "--run-id",
                "sleep-entrypoint-deadline",
                "--soft-deadline-seconds",
                str(SLEEP_NATIVE_SOFT_DEADLINE_SECONDS),
                "--json",
            ],
            cwd=repo,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
            timeout=30,
        )
        payload = json.loads(completed.stdout)

    assert completed.returncode == 0, completed.stderr
    assert payload["run_id"] == "sleep-entrypoint-deadline"
    assert payload["final_run_state"] in {"completed", "progress_saved"}
    assert set(payload["batch_head"]) == {
        "schema_version",
        "generation",
        "batch_id",
        "plan_ref",
        "plan_digest",
        "checkpoint_ref",
        "checkpoint_digest",
        "checkpoint_revision",
        "settled",
        "updated_at",
    }
    assert "progress saved" not in completed.stdout.lower()


def test_sleep_wrapper_accepts_outer_writer_evidence_not_present_in_inner_sleep_receipt() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        run_dir = (
            root
            / ".local"
            / "automation-runs"
            / "kb-sleep-maintenance"
            / "receipt-layering"
        )
        run_dir.mkdir(parents=True)
        native_receipt = run_dir / "sleep-native.json"
        native_receipt.write_text(
            json.dumps(
                {
                    "run_id": "receipt-layering",
                    "status": "completed",
                    "ok": True,
                    "input_watermark": 4,
                    "output_watermark": 4,
                }
            ),
            encoding="utf-8",
        )
        outer_payload = {
            "run_id": "receipt-layering",
            "status": "completed",
            "ok": True,
            "input_watermark": 4,
            "output_watermark": 4,
            "receipt_path": str(native_receipt),
            "global_writer": {"owner": "kb-sleep-maintenance"},
            "idempotent_reuse": False,
            "local_cycle": {},
        }

        issues = _real_artifact_issues(
            "kb-sleep-maintenance",
            outer_payload,
            receipt_path=run_dir / "wrapper-receipt.json",
        )

    assert issues == []


def test_organization_contribution_noop_performs_only_settings_gate() -> None:
    skill_id = "kb-organization-contribute"
    reason = "organization mode is not connected to a validated repository"
    payload = {
        "ok": True,
        "skipped": True,
        "run_id": "org-contribute-noop",
        "reason": reason,
        "settings_gate": {"available": False, "organization_validated": False},
        "terminal_gate": {
            "gate_id": "organization-settings",
            "evaluated": True,
            "applicable": False,
            "reason": reason,
        },
    }

    result = evaluate_native_payload(skill_id, payload, exit_code=0)

    assert result["ok"], result
    assert result["terminal_status"] == "no-op"
    _assert_only_gate_performed(
        skill_id,
        result["evidence"],
        "settings-noop-gate",
    )
    assert result["evidence"][obligation_id(skill_id, "lane-failure-recovery")][
        "outcome"
    ] == "not_applicable"


def test_organization_maintenance_noop_performs_only_participation_gate() -> None:
    skill_id = "kb-organization-maintenance"
    reason = "organization maintenance participation is not requested"
    payload = {
        "ok": True,
        "skipped": True,
        "run_id": "org-maintenance-noop",
        "reason": reason,
        "settings_gate": {"available": False, "organization_validated": True},
        "participation": {"available": False, "reason": reason},
        "terminal_gate": {
            "gate_id": "organization-maintenance-participation",
            "evaluated": True,
            "applicable": False,
            "reason": reason,
        },
    }

    result = evaluate_native_payload(skill_id, payload, exit_code=0)

    assert result["ok"], result
    _assert_only_gate_performed(
        skill_id,
        result["evidence"],
        "settings-participation-gate",
    )


def test_all_legal_update_noops_perform_only_manual_gate() -> None:
    skill_id = "khaos-brain-update"
    for reason in ("no-update",):
        payload = {
            "ok": True,
            "status": "no-op",
            "run_id": f"update-{reason}",
            "reason": reason,
            "manual_check": {"ok": True, "apply_ready": False, "reason": reason},
            "terminal_gate": {
                "gate_id": "manual-update-check",
                "evaluated": True,
                "applicable": False,
                "reason": reason,
            },
        }

        result = evaluate_native_payload(skill_id, payload, exit_code=0)

        assert result["ok"], (reason, result)
        assert set(result["evidence"]) == {
            obligation_id(skill_id, str(row["suffix"]))
            for row in AUTOMATION_COMPLETION_CONTRACTS[skill_id]["obligations"]
            if str(row["suffix"]) != "depth-calibration"
            and str(row.get("evidence_source") or "native-receipt")
            == "native-receipt"
        }
        _assert_only_gate_performed(
            skill_id,
            result["evidence"],
            "authorization-system-check",
        )


def test_update_operational_blockers_cannot_close_as_successful_noops() -> None:
    skill_id = "khaos-brain-update"
    for reason in (
        "already-upgrading",
        "previous-update-failed",
        "concurrent-update",
    ):
        payload = {
            "ok": True,
            "status": "no-op",
            "run_id": f"update-{reason}",
            "reason": reason,
            "manual_check": {"ok": True, "apply_ready": False, "reason": reason},
            "terminal_gate": {
                "gate_id": "manual-update-check",
                "evaluated": True,
                "applicable": False,
                "reason": reason,
            },
        }

        result = evaluate_native_payload(skill_id, payload, exit_code=0)

        assert not result["ok"], (reason, result)
        assert result["terminal_status"] == "failed"


def test_contribution_receipt_rejects_materialization_or_privacy_drift() -> None:
    skill_id = "kb-organization-contribute"
    payload = build_fixture_payload(skill_id, run_id="contribution-materialization")
    current = evaluate_native_payload(skill_id, payload, exit_code=0)
    assert current["ok"], current

    payload["branch"]["pre_push_readback"]["manifest_hash"] = "drifted"
    payload["branch"]["organization_check"]["checks"]["privacy_scan"]["ok"] = False
    drifted = evaluate_native_payload(skill_id, payload, exit_code=0)

    assert not drifted["ok"]
    assert not drifted["evidence"][
        obligation_id(skill_id, "branch-pr-auto-merge")
    ]["ok"]


def test_contribution_without_pending_proposals_proves_branch_not_applicable() -> None:
    skill_id = "kb-organization-contribute"
    payload = build_fixture_payload(skill_id, run_id="contribution-no-pending")
    payload["outbox"]["pending_count"] = 0
    payload["branch"] = {"attempted": False}

    result = evaluate_native_payload(skill_id, payload, exit_code=0)

    assert result["ok"], result
    evidence = result["evidence"][
        obligation_id(skill_id, "branch-pr-auto-merge")
    ]
    assert evidence["outcome"] == "not_applicable"
    assert evidence["source_fields"] == [
        "outbox.pending_count",
        "branch.attempted",
    ]
    assert evidence["applicability"]["gate_id"] == (
        "organization-pending-proposals"
    )
    assert evidence["non_mutation"]["proven"] is True
    assert evidence["terminal_gate"]["run_id"] == "contribution-no-pending"


def test_maintenance_receipt_rejects_materialization_readback_drift() -> None:
    skill_id = "kb-organization-maintenance"
    payload = build_fixture_payload(skill_id, run_id="maintenance-materialization")
    current = evaluate_native_payload(skill_id, payload, exit_code=0)
    assert current["ok"], current

    payload["maintenance_branch"]["pre_push_readback"]["file_sha256"] = {
        "kb/imports/fixture/card.yaml": "changed-after-check"
    }
    drifted = evaluate_native_payload(skill_id, payload, exit_code=0)

    assert not drifted["ok"]
    assert not drifted["evidence"][
        obligation_id(skill_id, "postapply-merge-readiness")
    ]["ok"]


def test_maintenance_without_selected_actions_uses_only_applicable_readiness_sources() -> None:
    skill_id = "kb-organization-maintenance"
    payload = build_fixture_payload(skill_id, run_id="maintenance-no-selection")
    cleanup = payload["report"]["cleanup"]
    cleanup["review"]["selected_action_ids"] = []
    cleanup["apply"] = {
        "attempted": False,
        "ok": True,
        "applied_action_ids": [],
    }
    cleanup["exact_selected_apply"] = {
        "complete": True,
        "exact": True,
        "selected_action_ids": [],
        "applied_action_ids": [],
    }
    cleanup["github_merge_readiness"] = {
        "complete": True,
        "eligible": False,
        "label": "org-kb:auto-merge",
        "blockers": ["no-selected-actions"],
    }
    payload["maintenance_branch"] = {"attempted": False}

    result = evaluate_native_payload(skill_id, payload, exit_code=0)

    assert result["ok"], result
    evidence = result["evidence"][
        obligation_id(skill_id, "postapply-merge-readiness")
    ]
    assert evidence["outcome"] == "performed"
    assert evidence["source_fields"] == [
        "report.cleanup.post_apply_check",
        "report.cleanup.github_merge_readiness",
        "maintenance_branch",
    ]
