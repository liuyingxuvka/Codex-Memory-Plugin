from __future__ import annotations

import tempfile
import subprocess
import unittest
import json
from pathlib import Path
from unittest.mock import patch

from local_kb.org_simulation import (
    REQUIRED_CHECKPOINTS,
    _configured_source_identity,
    _canonical_digest,
    _repository_identity,
    _runner_identity,
    _toolchain_identity,
    _validate_cycle,
    persist_rehearsal_receipt,
    verify_rehearsal_receipt,
)


class OrganizationRehearsalValidationTests(unittest.TestCase):
    def _cycle(self) -> dict:
        checkpoints = {
            "card_surface": {"complete": True, "privacy_risk_count": 0},
            "candidate_intake": {"complete": True},
            "content_hash": {"complete": True},
            "merge": {"complete": True},
            "split": {"complete": True},
            "card_decisions": {"complete": True},
            "skill_safety": {"complete": True, "passed": True},
            "skill_bundle_version": {"complete": True, "passed": True},
            "decision_apply": {"complete": True, "exact": True},
            "post_apply": {"complete": True, "ok": True},
            "github_merge_readiness": {"complete": True},
        }
        self.assertEqual(set(checkpoints), set(REQUIRED_CHECKPOINTS))
        return {
            "ok": True,
            "status": "completed",
            "maintenance": {
                "report": {"cleanup": {"checkpoints": checkpoints}},
                "sync": {
                    "base_checkout": {"ok": True},
                    "worktree": {"mode": "isolated", "effective_path": ""},
                    "worktree_cleanup": {"ok": True, "retained": False},
                },
            },
            "contribution": {"ok": True, "sync": {}},
            "snapshot": {"ok": True, "schema_version": 3, "generation_id": "snapshot-test"},
            "postflight_recorded": True,
            "cycle_receipt_path": "",
        }

    def _validate(self, cycle: dict) -> dict:
        with tempfile.TemporaryDirectory() as tmp, patch(
            "local_kb.org_simulation._git_status", return_value=""
        ), patch("local_kb.org_simulation._git_head", return_value=""):
            return _validate_cycle(
                cycle,
                source_clone=Path(tmp),
                source_status_before="",
                source_head_before="",
                authority_digest_before="",
            )

    def test_missing_checkpoint_has_reopen_condition(self) -> None:
        cycle = self._cycle()
        cycle["maintenance"]["report"]["cleanup"]["checkpoints"].pop("card_surface")
        result = self._validate(cycle)
        self.assertEqual(result["checkpoint"], "card_surface")
        self.assertIn("rerun", result["reopen_condition"])

    def test_selected_apply_mismatch_blocks_rehearsal(self) -> None:
        cycle = self._cycle()
        cycle["maintenance"]["report"]["cleanup"]["checkpoints"]["decision_apply"]["exact"] = False
        result = self._validate(cycle)
        self.assertEqual(result["checkpoint"], "decision_apply")

    def test_stale_snapshot_blocks_rehearsal(self) -> None:
        cycle = self._cycle()
        cycle["snapshot"] = {"ok": False, "status": "pointer-conflict"}
        result = self._validate(cycle)
        self.assertEqual(result["checkpoint"], "snapshot-cas")

    def test_unsafe_skill_and_privacy_evidence_blocks_rehearsal(self) -> None:
        cycle = self._cycle()
        cycle["maintenance"]["report"]["cleanup"]["checkpoints"]["skill_safety"]["passed"] = False
        result = self._validate(cycle)
        self.assertEqual(result["checkpoint"], "skill_safety")

        cycle = self._cycle()
        cycle["maintenance"]["report"]["cleanup"]["checkpoints"]["card_surface"]["privacy_risk_count"] = 1
        result = self._validate(cycle)
        self.assertEqual(result["checkpoint"], "card_surface")

    def test_long_path_checkout_failure_is_visible(self) -> None:
        cycle = self._cycle()
        cycle["maintenance"]["sync"]["base_checkout"]["ok"] = False
        result = self._validate(cycle)
        self.assertEqual(result["checkpoint"], "long-path-checkout")

    def test_identity_bound_receipt_verifies_then_blocks_on_repository_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            source.mkdir()
            (source / "khaos_org_kb.yaml").write_text("schema_version: 2\n", encoding="utf-8")
            subprocess.run(["git", "init"], cwd=source, check=True, capture_output=True)
            subprocess.run(["git", "add", "."], cwd=source, check=True, capture_output=True)
            subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "seed"],
                cwd=source,
                check=True,
                capture_output=True,
            )
            result = {
                "schema_version": "khaos-brain.organization-maintenance-rehearsal.v1",
                "ok": True,
                "status": "completed",
                "production_receipt": False,
                "repository": _repository_identity(root),
                "source": {"configured_before": _configured_source_identity(source)},
                "toolchain": _toolchain_identity(root),
                "runner": _runner_identity(root),
                "validation": {"checkpoint": "complete"},
                "cleanup": {"ok": True},
                "remote_mutation": {
                    "push_requested": False,
                    "push_observed": False,
                    "remote_refs_unchanged": True,
                    "production_wrapper_invoked": False,
                    "new_wrapper_runs": [],
                    "audit": {
                        "remote_refs": "before-after-ls-remote",
                        "wrapper_runs": "before-after-run-inventory",
                    },
                },
            }
            persist_rehearsal_receipt(root, result)
            self.assertTrue(verify_rehearsal_receipt(root)["ok"])

            (root / "drift.txt").write_text("changed\n", encoding="utf-8")
            drifted = verify_rehearsal_receipt(root)

        self.assertFalse(drifted["ok"])
        self.assertEqual(drifted["status"], "stale")

    def test_receipt_blocks_when_runner_or_remote_audit_is_tampered(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            source.mkdir()
            (source / "khaos_org_kb.yaml").write_text("schema_version: 2\n", encoding="utf-8")
            subprocess.run(["git", "init"], cwd=source, check=True, capture_output=True)
            subprocess.run(["git", "add", "."], cwd=source, check=True, capture_output=True)
            subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "seed"],
                cwd=source,
                check=True,
                capture_output=True,
            )
            result = {
                "schema_version": "khaos-brain.organization-maintenance-rehearsal.v1",
                "ok": True,
                "status": "completed",
                "production_receipt": False,
                "repository": _repository_identity(root),
                "source": {"configured_before": _configured_source_identity(source)},
                "toolchain": _toolchain_identity(root),
                "runner": _runner_identity(root),
                "validation": {"checkpoint": "complete"},
                "cleanup": {"ok": True},
                "remote_mutation": {
                    "push_requested": False,
                    "push_observed": False,
                    "remote_refs_unchanged": True,
                    "production_wrapper_invoked": False,
                    "new_wrapper_runs": [],
                    "audit": {
                        "remote_refs": "before-after-ls-remote",
                        "wrapper_runs": "before-after-run-inventory",
                    },
                },
            }
            persist_rehearsal_receipt(root, result)
            payload = json.loads((root / ".local" / "assurance" / "organization-rehearsal" / "current.json").read_text(encoding="utf-8"))
            payload["runner"]["digest"] = "sha256:tampered"
            payload["receipt_digest"] = f"sha256:{_canonical_digest({key: value for key, value in payload.items() if key != 'receipt_digest'})}"
            (root / ".local" / "assurance" / "organization-rehearsal" / "current.json").write_text(json.dumps(payload), encoding="utf-8")
            tampered = verify_rehearsal_receipt(root)
            self.assertFalse(tampered["ok"])
            self.assertEqual(tampered["status"], "stale")


if __name__ == "__main__":
    unittest.main()
