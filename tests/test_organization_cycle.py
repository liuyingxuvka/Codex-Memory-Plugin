from __future__ import annotations

import tempfile
import unittest
import json
from pathlib import Path
from unittest.mock import patch

from local_kb.maintenance_lanes import CYCLE_RECEIPT_SCHEMA, validate_cycle_receipt_v3
from local_kb.org_cycle import run_organization_cycle
from local_kb.settings import ORGANIZATION_MODE, save_desktop_settings
from tests.org_helpers import activate_current_kb_runtime, connect_profile_to_org, init_git_repo, write_valid_org_repo


class OrganizationCycleTests(unittest.TestCase):
    def test_cycle_serializes_maintenance_contribution_and_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            org = root / "org"
            machine = root / "machine"
            write_valid_org_repo(org, include_sandbox_cards=True)
            init_git_repo(org)
            connection, _sources = connect_profile_to_org(machine, org)
            settings = dict(connection["settings"])
            settings["organization_maintenance_requested"] = True
            save_desktop_settings(machine, {"mode": ORGANIZATION_MODE, "organization": settings})
            activate_current_kb_runtime(machine)

            result = run_organization_cycle(machine, run_id="organization-cycle-test", push=False)

        self.assertTrue(result["ok"], result)
        self.assertEqual(result["status"], "completed")
        self.assertTrue(result["maintenance"]["ok"])
        self.assertTrue(result["contribution"]["ok"])
        self.assertTrue(result["snapshot"]["ok"])
        self.assertTrue(result["postflight_recorded"])

    def test_not_applicable_maintenance_does_not_run_contribution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            maintenance = {
                "ok": True,
                "skipped": True,
                "run_id": "org-na-maintenance",
                "reason": "organization participation is not requested",
                "terminal_gate": {
                    "evaluated": True,
                    "applicable": False,
                },
            }
            with (
                patch(
                    "local_kb.org_cycle.run_organization_maintenance",
                    return_value=maintenance,
                ),
                patch("local_kb.org_cycle.run_organization_contribution") as contribution,
            ):
                result = run_organization_cycle(root, run_id="org-na", push=False)

            self.assertTrue(result["ok"])
            self.assertTrue(result["skipped"])
            self.assertEqual(result["status"], "not_applicable")
            self.assertEqual(result["contribution"]["status"], "not_run")
            self.assertEqual(
                result["contribution"]["reason"], "prerequisite-not-applicable"
            )
            contribution.assert_not_called()

    def test_failed_maintenance_marks_contribution_not_run_and_cycle_failed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            maintenance = {
                "ok": False,
                "skipped": False,
                "run_id": "org-fail-maintenance",
                "status": "failed",
                "reason": "snapshot-invalid",
            }
            with (
                patch(
                    "local_kb.org_cycle.run_organization_maintenance",
                    return_value=maintenance,
                ),
                patch("local_kb.org_cycle.run_organization_contribution") as contribution,
            ):
                result = run_organization_cycle(root, run_id="org-fail", push=False)

            self.assertFalse(result["ok"])
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["contribution"]["status"], "not_run")
            self.assertEqual(result["contribution"]["reason"], "predecessor-failed")
            contribution.assert_not_called()

    def test_blocked_maintenance_marks_contribution_not_run_and_cycle_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            maintenance = {
                "ok": False,
                "skipped": False,
                "run_id": "org-blocked-maintenance",
                "status": "blocked",
                "reason": "writer-unavailable",
            }
            with (
                patch(
                    "local_kb.org_cycle.run_organization_maintenance",
                    return_value=maintenance,
                ),
                patch("local_kb.org_cycle.run_organization_contribution") as contribution,
            ):
                result = run_organization_cycle(
                    root, run_id="org-blocked", push=False
                )

            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["contribution"]["reason"], "predecessor-blocked")
            contribution.assert_not_called()

    def test_contribution_failure_is_not_promoted_to_completed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            maintenance = {
                "ok": True,
                "skipped": False,
                "run_id": "org-contrib-fail-maintenance",
                "sync": {},
            }
            contribution = {
                "ok": False,
                "skipped": False,
                "run_id": "org-contrib-fail-contribute",
                "status": "failed",
                "reason": "outbox-failed",
            }
            with (
                patch(
                    "local_kb.org_cycle.run_organization_maintenance",
                    return_value=maintenance,
                ),
                patch(
                    "local_kb.org_cycle.run_organization_contribution",
                    return_value=contribution,
                ),
                patch(
                    "local_kb.org_cycle.record_observation",
                    return_value=root / "postflight.jsonl",
                ),
            ):
                result = run_organization_cycle(
                    root, run_id="org-contrib-fail", push=False
                )

            self.assertFalse(result["ok"])
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["contribution"]["status"], "failed")

    def test_blocked_or_late_not_applicable_contribution_blocks_cycle(self) -> None:
        for child_status, skipped, terminal_gate, reason in (
            ("blocked", False, {}, "outbox-writer-unavailable"),
            ("", True, {"applicable": False}, "settings-changed"),
        ):
            with self.subTest(child_status=child_status or "not_applicable"), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                maintenance = {
                    "ok": True,
                    "skipped": False,
                    "run_id": "org-child-block-maintenance",
                    "sync": {},
                }
                contribution = {
                    "ok": False if not skipped else True,
                    "skipped": skipped,
                    "run_id": "org-child-block-contribute",
                    "status": child_status,
                    "reason": reason,
                    "terminal_gate": terminal_gate,
                }
                with (
                    patch(
                        "local_kb.org_cycle.run_organization_maintenance",
                        return_value=maintenance,
                    ),
                    patch(
                        "local_kb.org_cycle.run_organization_contribution",
                        return_value=contribution,
                    ),
                    patch(
                        "local_kb.org_cycle.record_observation",
                        return_value=root / "postflight.jsonl",
                    ),
                ):
                    result = run_organization_cycle(
                        root,
                        run_id=f"org-child-{child_status or 'not-applicable'}",
                        push=False,
                    )

                self.assertFalse(result["ok"])
                self.assertEqual(result["status"], "blocked")

    def test_cycle_receipt_v3_reuses_only_exact_current_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            maintenance = {
                "ok": True,
                "skipped": False,
                "run_id": "org-reuse-maintenance",
                "sync": {"snapshot": {"ok": True, "generation_id": "snapshot-1"}},
            }
            contribution = {
                "ok": True,
                "skipped": False,
                "run_id": "org-reuse-contribute",
                "sync": {"snapshot": {"ok": True, "generation_id": "snapshot-1"}},
            }
            with (
                patch(
                    "local_kb.org_cycle.run_organization_maintenance",
                    return_value=maintenance,
                ) as maintenance_runner,
                patch(
                    "local_kb.org_cycle.run_organization_contribution",
                    return_value=contribution,
                ) as contribution_runner,
                patch(
                    "local_kb.org_cycle.record_observation",
                    return_value=root / "postflight.jsonl",
                ),
            ):
                first = run_organization_cycle(root, run_id="org-reuse", push=False)
                second = run_organization_cycle(root, run_id="org-reuse", push=False)

            self.assertFalse(first["idempotent_reuse"])
            self.assertTrue(second["idempotent_reuse"])
            self.assertEqual(maintenance_runner.call_count, 1)
            self.assertEqual(contribution_runner.call_count, 1)
            receipt_path = Path(first["cycle_receipt_path"])
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(receipt["schema_version"], CYCLE_RECEIPT_SCHEMA)
            self.assertTrue(validate_cycle_receipt_v3(receipt)["ok"])
            self.assertNotIn("lease_token", json.dumps(receipt))
            self.assertNotIn("delegation_token", json.dumps(receipt))

    def test_same_run_request_change_blocks_without_rerun(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            maintenance = {
                "ok": True,
                "skipped": True,
                "run_id": "org-request-maintenance",
                "reason": "not configured",
                "terminal_gate": {"applicable": False},
            }
            with patch(
                "local_kb.org_cycle.run_organization_maintenance",
                return_value=maintenance,
            ) as maintenance_runner:
                run_organization_cycle(root, run_id="org-request", push=False)
                changed = run_organization_cycle(
                    root, run_id="org-request", push=True
                )

            self.assertEqual(changed["status"], "blocked")
            self.assertIn(
                "receipt-request-mismatch", changed["receipt_validation"]["issues"]
            )
            self.assertEqual(maintenance_runner.call_count, 1)


if __name__ == "__main__":
    unittest.main()
