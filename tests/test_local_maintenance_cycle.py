from __future__ import annotations

import tempfile
import unittest
import json
from pathlib import Path
from unittest.mock import patch

from local_kb.local_cycle import LOCAL_CYCLE_WORKFLOW_REVISION, run_local_maintenance_cycle
from local_kb.logicguard_models import load_authority_generation
from local_kb.maintenance_lanes import (
    CYCLE_RECEIPT_SCHEMA,
    CYCLE_OUTPUT_SIDECAR_SCHEMA,
    cycle_receipt_payload_digest,
    resolve_cycle_outputs,
    validate_cycle_receipt_v3,
    write_cycle_receipt_v3,
)
from tests.current_runtime_helpers import activate_current_kb_runtime


class LocalMaintenanceCycleTests(unittest.TestCase):
    @staticmethod
    def _completed_sleep(root: Path, run_id: str) -> dict[str, object]:
        activate_current_kb_runtime(root)
        authority = load_authority_generation(root)
        return {
            "ok": True,
            "run_id": run_id,
            "final_run_state": "completed",
            "batch_resumed": False,
            "blockers": [],
            "batch_checkpoint": {"settled": True},
            "generation_id": str(authority.get("generation_id") or ""),
            "pointer_digest": str(authority.get("pointer_digest") or ""),
        }

    def test_sleep_and_dream_share_one_cycle_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            activate_current_kb_runtime(root)
            result = run_local_maintenance_cycle(
                root,
                run_id="local-cycle-test",
                max_observations=0,
                soft_deadline_seconds=5,
            )

            cycle = result["local_cycle"]
            cycle_path = Path(str(cycle["cycle_receipt_path"]))
            self.assertTrue(cycle_path.is_file())
            self.assertEqual(cycle["sequence"], ["sleep", "dream"])
            self.assertEqual(cycle["mode"], "fresh_cycle")
            self.assertEqual(cycle["status"], "completed")
            self.assertEqual(cycle["dream"]["status"], "completed")
            self.assertEqual(cycle["postflight"]["status"], "completed")
            self.assertTrue(cycle["postflight"]["event_id"])
            self.assertTrue(Path(cycle["postflight"]["path"]).is_file())

    def test_large_cycle_outputs_use_digest_bound_sidecar_and_reject_tamper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            activate_current_kb_runtime(root)
            result = run_local_maintenance_cycle(
                root,
                run_id="local-cycle-sidecar-source",
                max_observations=0,
                soft_deadline_seconds=5,
            )
            source_path = Path(result["local_cycle"]["cycle_receipt_path"])
            source = json.loads(source_path.read_text(encoding="utf-8"))
            outputs, issues = resolve_cycle_outputs(source, receipt_path=source_path)
            self.assertFalse(issues)
            outputs["large_diagnostic"] = "x" * 300_000
            compact_path = (
                root
                / ("r" * 120)
                / "cycle-receipt.json"
            )
            write_cycle_receipt_v3(compact_path, {**source, "outputs": outputs})
            persisted = json.loads(compact_path.read_text(encoding="utf-8"))

            self.assertEqual(persisted["outputs"]["schema_version"], CYCLE_OUTPUT_SIDECAR_SCHEMA)
            sidecar = compact_path.parent / persisted["outputs"]["path"]
            self.assertTrue(sidecar.is_file())
            self.assertLess(len(str(sidecar)), 260)
            self.assertTrue(validate_cycle_receipt_v3(persisted, receipt_path=compact_path)["ok"])

            sidecar.write_text("{}\n", encoding="utf-8")
            self.assertFalse(validate_cycle_receipt_v3(persisted, receipt_path=compact_path)["ok"])
            self.assertEqual(result["final_run_state"], "completed")

    def test_local_cycle_postflight_is_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            activate_current_kb_runtime(root)
            result = run_local_maintenance_cycle(
                root,
                run_id="local-postflight",
                max_observations=0,
                soft_deadline_seconds=5,
            )
            postflight = result["local_cycle"]["postflight"]
            self.assertEqual(postflight["status"], "completed")
            self.assertEqual(postflight["event_id"], "sleep-dream-postflight:local-postflight")
            self.assertTrue(
                all(
                    row.get("status") not in {"running", "acquired"}
                    for row in postflight["lane_status"].values()
                    if row
                )
            )

    def test_cycle_validator_rejects_stale_postflight_and_lane_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sleep = self._completed_sleep(root, "local-stale-status")
            dream = {
                "ok": True,
                "run_id": "local-stale-status-dream",
                "status": "completed",
                "valuable_opportunity_count": 0,
            }
            with (
                patch("local_kb.local_cycle.run_incremental_sleep", return_value=sleep),
                patch("local_kb.local_cycle.run_dream_maintenance", return_value=dream),
            ):
                result = run_local_maintenance_cycle(root, run_id="local-stale-status")
            receipt = json.loads(
                Path(result["local_cycle"]["cycle_receipt_path"]).read_text(
                    encoding="utf-8"
                )
            )
            receipt["outputs"]["postflight"]["status"] = "running"
            receipt["outputs"]["lane_status"]["kb-dream"] = {
                "lane": "kb-dream",
                "status": "stale",
                "run_id": "local-stale-status-dream",
            }
            receipt["payload_digest"] = cycle_receipt_payload_digest(receipt)
            validation = validate_cycle_receipt_v3(receipt)
            self.assertFalse(validation["ok"])
            self.assertIn("receipt-local-postflight-stale", validation["issues"])
            self.assertIn("receipt-local-lane-status-stale:kb-dream", validation["issues"])

    def test_progress_saved_keeps_exact_status_and_does_not_run_dream(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sleep = {
                "ok": True,
                "run_id": "local-progress",
                "final_run_state": "progress_saved",
                "batch_resumed": True,
                "blockers": [],
            }
            with (
                patch("local_kb.local_cycle.run_incremental_sleep", return_value=sleep),
                patch("local_kb.local_cycle.run_dream_maintenance") as dream,
            ):
                result = run_local_maintenance_cycle(root, run_id="local-progress")

            self.assertEqual(result["status"], "progress_saved")
            self.assertEqual(result["final_run_state"], "progress_saved")
            self.assertEqual(result["local_cycle"]["dream"]["status"], "not_run")
            self.assertEqual(
                result["local_cycle"]["dream"]["reason"], "sleep-progress-saved"
            )
            dream.assert_not_called()

    def test_completed_with_blocks_is_not_promoted_to_completed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sleep = {
                "ok": True,
                "run_id": "local-blocks",
                "final_run_state": "completed_with_blocks",
                "batch_resumed": False,
                "blockers": ["item-1"],
            }
            with (
                patch("local_kb.local_cycle.run_incremental_sleep", return_value=sleep),
                patch("local_kb.local_cycle.run_dream_maintenance") as dream,
            ):
                result = run_local_maintenance_cycle(root, run_id="local-blocks")

            self.assertEqual(result["status"], "completed_with_blocks")
            self.assertEqual(result["final_run_state"], "completed_with_blocks")
            self.assertEqual(
                result["local_cycle"]["phases"][1]["reason_code"],
                "sleep-completed-with-blocks",
            )
            dream.assert_not_called()

    def test_dream_failure_fails_only_the_local_cycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sleep = self._completed_sleep(root, "local-dream-fail")
            dream = {
                "ok": False,
                "run_id": "local-dream-fail-dream",
                "status": "failed",
                "reason": "experiment-failed",
            }
            with (
                patch(
                    "local_kb.local_cycle.run_incremental_sleep",
                    return_value=sleep,
                ) as sleep_runner,
                patch("local_kb.local_cycle.run_dream_maintenance", return_value=dream),
            ):
                result = run_local_maintenance_cycle(root, run_id="local-dream-fail")

            self.assertFalse(result["ok"])
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["final_run_state"], "failed")
            writer_delegation = sleep_runner.call_args.kwargs["writer_delegation"]
            self.assertEqual(writer_delegation["child_phase_id"], "sleep")
            self.assertEqual(writer_delegation["child_run_id"], "local-dream-fail")
            self.assertTrue(writer_delegation["lease_id"])
            self.assertTrue(writer_delegation["delegation_token"])
            receipt = json.loads(
                Path(result["local_cycle"]["cycle_receipt_path"]).read_text(
                    encoding="utf-8"
                )
            )
            self.assertNotIn("organization", json.dumps(receipt).lower())
            self.assertEqual(receipt["phases"][1]["lease"]["mode"], "read-only")
            self.assertEqual(
                receipt["phases"][1]["lease"]["global_writer"],
                "not-required",
            )
            dream_writer_events = [
                item
                for item in receipt["write_lease_events"]
                if item.get("phase_id") == "dream"
            ]
            self.assertEqual(
                dream_writer_events,
                [
                    {
                        "event": "read-only-phase",
                        "phase_id": "dream",
                        "mode": "read-only",
                        "global_writer": "not-required",
                    }
                ],
            )

    def test_blocked_and_failed_sleep_keep_exact_cycle_status(self) -> None:
        for sleep_status, downstream_reason in (
            ("blocked", "predecessor-blocked"),
            ("failed", "predecessor-failed"),
        ):
            with self.subTest(sleep_status=sleep_status), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                sleep = {
                    "ok": False,
                    "run_id": f"local-{sleep_status}",
                    "final_run_state": sleep_status,
                    "status": sleep_status,
                    "reason": f"sleep-{sleep_status}",
                    "blockers": [],
                }
                with (
                    patch(
                        "local_kb.local_cycle.run_incremental_sleep",
                        return_value=sleep,
                    ),
                    patch("local_kb.local_cycle.run_dream_maintenance") as dream,
                ):
                    result = run_local_maintenance_cycle(
                        root, run_id=f"local-{sleep_status}"
                    )

                self.assertEqual(result["status"], sleep_status)
                self.assertEqual(
                    result["local_cycle"]["dream"]["reason"], downstream_reason
                )
                dream.assert_not_called()

    def test_blocked_dream_blocks_completed_sleep_cycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sleep = self._completed_sleep(root, "local-dream-blocked")
            dream = {
                "ok": False,
                "run_id": "local-dream-blocked-dream",
                "status": "blocked",
                "reason": "writer-unavailable",
            }
            with (
                patch("local_kb.local_cycle.run_incremental_sleep", return_value=sleep),
                patch("local_kb.local_cycle.run_dream_maintenance", return_value=dream),
            ):
                result = run_local_maintenance_cycle(
                    root, run_id="local-dream-blocked"
                )

            self.assertFalse(result["ok"])
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["local_cycle"]["phases"][1]["status"], "blocked")

    def test_cycle_receipt_v3_reuses_only_exact_current_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sleep = self._completed_sleep(root, "local-reuse")
            dream_result = {
                "ok": True,
                "run_id": "local-reuse-dream",
                "status": "completed",
                "valuable_opportunity_count": 0,
            }
            with (
                patch(
                    "local_kb.local_cycle.run_incremental_sleep",
                    return_value=sleep,
                ) as sleep_runner,
                patch(
                    "local_kb.local_cycle.run_dream_maintenance",
                    return_value=dream_result,
                ) as dream_runner,
            ):
                first = run_local_maintenance_cycle(root, run_id="local-reuse")
                second = run_local_maintenance_cycle(root, run_id="local-reuse")

            self.assertFalse(first["idempotent_reuse"])
            self.assertTrue(second["idempotent_reuse"])
            self.assertEqual(sleep_runner.call_count, 1)
            self.assertEqual(dream_runner.call_count, 1)
            receipt_path = Path(first["local_cycle"]["cycle_receipt_path"])
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(receipt["schema_version"], CYCLE_RECEIPT_SCHEMA)
            self.assertTrue(validate_cycle_receipt_v3(receipt)["ok"])
            self.assertNotIn("lease_token", json.dumps(receipt))
            self.assertNotIn("delegation_token", json.dumps(receipt))

    def test_same_run_request_change_or_tamper_blocks_without_rerun(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sleep = {
                "ok": True,
                "run_id": "local-conflict",
                "final_run_state": "progress_saved",
                "batch_resumed": False,
                "blockers": [],
            }
            with patch(
                "local_kb.local_cycle.run_incremental_sleep", return_value=sleep
            ) as sleep_runner:
                first = run_local_maintenance_cycle(
                    root, run_id="local-conflict", max_observations=1
                )
                changed_request = run_local_maintenance_cycle(
                    root, run_id="local-conflict", max_observations=2
                )
                receipt_path = Path(first["local_cycle"]["cycle_receipt_path"])
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                receipt["status"] = "completed"
                receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
                tampered = run_local_maintenance_cycle(
                    root, run_id="local-conflict", max_observations=1
                )

            self.assertEqual(changed_request["status"], "blocked")
            self.assertIn(
                "receipt-request-mismatch",
                changed_request["receipt_validation"]["issues"],
            )
            self.assertEqual(tampered["status"], "blocked")
            self.assertIn(
                "receipt-payload-digest-mismatch",
                tampered["receipt_validation"]["issues"],
            )
            self.assertEqual(sleep_runner.call_count, 1)

    def test_receipt_rejects_forged_workflow_and_status_matrix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sleep = {
                "ok": True,
                "run_id": "local-forged",
                "final_run_state": "progress_saved",
                "batch_resumed": False,
                "blockers": [],
            }
            with patch(
                "local_kb.local_cycle.run_incremental_sleep", return_value=sleep
            ):
                result = run_local_maintenance_cycle(root, run_id="local-forged")
            receipt = json.loads(
                Path(result["local_cycle"]["cycle_receipt_path"]).read_text(
                    encoding="utf-8"
                )
            )

            receipt["workflow_revision"] = "forged-workflow"
            receipt["status"] = "completed"
            receipt["payload_digest"] = cycle_receipt_payload_digest(receipt)
            validation = validate_cycle_receipt_v3(
                receipt,
                expected_workflow_revision=LOCAL_CYCLE_WORKFLOW_REVISION,
            )

            self.assertFalse(validation["ok"])
            self.assertIn("receipt-workflow-revision-mismatch", validation["issues"])
            self.assertIn("receipt-local-status-matrix-invalid", validation["issues"])

    def test_same_run_blocks_when_current_result_state_has_drifted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sleep = {
                "ok": True,
                "run_id": "local-drift",
                "final_run_state": "progress_saved",
                "batch_resumed": False,
                "blockers": [],
            }
            with patch(
                "local_kb.local_cycle.run_incremental_sleep", return_value=sleep
            ) as sleep_runner:
                run_local_maintenance_cycle(root, run_id="local-drift")
                history = root / "kb" / "history" / "events.jsonl"
                history.parent.mkdir(parents=True, exist_ok=True)
                history.write_text('{"event_id":"later"}\n', encoding="utf-8")
                drifted = run_local_maintenance_cycle(root, run_id="local-drift")

            self.assertEqual(drifted["status"], "blocked")
            self.assertIn(
                "receipt-current-state-mismatch",
                drifted["receipt_validation"]["issues"],
            )
            self.assertEqual(sleep_runner.call_count, 1)


if __name__ == "__main__":
    unittest.main()
