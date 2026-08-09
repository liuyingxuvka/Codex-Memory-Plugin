from __future__ import annotations

import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from local_kb.maintenance_lanes import (
    acquire_cycle_lease,
    acquire_global_write_lease,
    acquire_lane_lock,
    build_lane_guard,
    delegate_global_write_lease,
    heartbeat_global_write_lease,
    lane_lock_group,
    read_global_write_lease,
    read_lane_lock,
    read_lane_status,
    recover_global_write_lease_after_cleanup,
    reconcile_stale_lane_statuses,
    release_cycle_lease,
    release_delegated_write_lease,
    release_global_write_lease,
    release_lane_lock,
    validate_global_write_delegation,
    write_lane_status,
)


class MaintenanceLaneLockTests(unittest.TestCase):
    def test_local_and_organization_task_leases_are_independent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            local = acquire_cycle_lease(
                repo_root,
                cycle_kind="local-maintenance-cycle",
                run_id="local-1",
            )
            organization = acquire_cycle_lease(
                repo_root,
                cycle_kind="organization-maintenance-cycle",
                run_id="org-1",
            )

            self.assertTrue(local["acquired"])
            self.assertTrue(organization["acquired"])
            self.assertNotEqual(local["group"], organization["group"])
            self.assertTrue(
                release_cycle_lease(
                    repo_root,
                    cycle_kind="local-maintenance-cycle",
                    run_id="local-1",
                )["released"]
            )
            self.assertTrue(
                release_cycle_lease(
                    repo_root,
                    cycle_kind="organization-maintenance-cycle",
                    run_id="org-1",
                )["released"]
            )

    def test_same_task_run_is_not_reentrant_from_another_thread(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            first = acquire_cycle_lease(
                repo_root,
                cycle_kind="local-maintenance-cycle",
                run_id="same-run",
            )
            observed: list[dict] = []

            def contend() -> None:
                observed.append(
                    acquire_cycle_lease(
                        repo_root,
                        cycle_kind="local-maintenance-cycle",
                        run_id="same-run",
                    )
                )

            thread = threading.Thread(target=contend)
            thread.start()
            thread.join(timeout=5)

            self.assertTrue(first["acquired"])
            self.assertEqual(len(observed), 1)
            self.assertFalse(observed[0]["acquired"])
            release_cycle_lease(
                repo_root,
                cycle_kind="local-maintenance-cycle",
                run_id="same-run",
            )

    def test_global_writer_serializes_independent_tasks_and_delegates_exactly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            local = acquire_global_write_lease(
                repo_root,
                cycle_kind="local-maintenance-cycle",
                run_id="local-1",
                scope="sleep",
                wait=False,
            )
            organization = acquire_global_write_lease(
                repo_root,
                cycle_kind="organization-maintenance-cycle",
                run_id="org-1",
                scope="organization-maintenance",
                wait=True,
                max_wait_seconds=0,
            )

            self.assertTrue(local["acquired"])
            self.assertFalse(organization["acquired"])
            self.assertEqual(organization["reason"], "global-writer-active")
            delegation = delegate_global_write_lease(
                repo_root,
                lease_id=local["lease_id"],
                lease_token=local["lease_token"],
                child_phase_id="sleep",
                child_run_id="local-1",
                scope="sleep",
            )
            self.assertTrue(delegation["ok"])
            heartbeats: list[dict] = []
            heartbeat_thread = threading.Thread(
                target=lambda: heartbeats.append(
                    heartbeat_global_write_lease(
                        repo_root,
                        lease_id=local["lease_id"],
                        lease_token=local["lease_token"],
                    )
                )
            )
            heartbeat_thread.start()
            heartbeat_thread.join(timeout=5)
            self.assertEqual(len(heartbeats), 1)
            self.assertTrue(heartbeats[0]["ok"])
            self.assertTrue(
                validate_global_write_delegation(
                    repo_root,
                    lease_id=local["lease_id"],
                    child_phase_id="sleep",
                    child_run_id="local-1",
                    delegation_token=delegation["delegation_token"],
                )["ok"]
            )
            self.assertFalse(
                validate_global_write_delegation(
                    repo_root,
                    lease_id=local["lease_id"],
                    child_phase_id="sleep",
                    child_run_id="local-1",
                    delegation_token="wrong-token",
                )["ok"]
            )
            self.assertFalse(
                release_global_write_lease(
                    repo_root,
                    lease_id=local["lease_id"],
                    lease_token=delegation["delegation_token"],
                )["released"]
            )
            self.assertFalse(
                release_global_write_lease(
                    repo_root,
                    lease_id=local["lease_id"],
                    lease_token=local["lease_token"],
                )["released"]
            )
            self.assertTrue(
                release_delegated_write_lease(
                    repo_root,
                    lease_id=local["lease_id"],
                    lease_token=local["lease_token"],
                    child_phase_id="sleep",
                    child_run_id="local-1",
                    delegation_token=delegation["delegation_token"],
                )["ok"]
            )
            self.assertTrue(
                release_global_write_lease(
                    repo_root,
                    lease_id=local["lease_id"],
                    lease_token=local["lease_token"],
                )["released"]
            )
            next_owner = acquire_global_write_lease(
                repo_root,
                cycle_kind="organization-maintenance-cycle",
                run_id="org-1",
                scope="organization-maintenance",
                wait=False,
            )
            self.assertTrue(next_owner["acquired"])
            self.assertNotEqual(local["lease_id"], next_owner["lease_id"])
            self.assertTrue(
                release_global_write_lease(
                    repo_root,
                    lease_id=next_owner["lease_id"],
                    lease_token=next_owner["lease_token"],
                )["released"]
            )

    def test_expired_global_writer_requires_explicit_cleanup_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            first = acquire_global_write_lease(
                repo_root,
                cycle_kind="local-maintenance-cycle",
                run_id="local-1",
                scope="sleep",
                wait=False,
            )
            self.assertTrue(first["acquired"])
            with patch(
                "local_kb.maintenance_lanes._global_lease_expired",
                return_value=True,
            ):
                blocked = acquire_global_write_lease(
                    repo_root,
                    cycle_kind="organization-maintenance-cycle",
                    run_id="org-1",
                    scope="organization-maintenance",
                    wait=False,
                )
                recovered = acquire_global_write_lease(
                    repo_root,
                    cycle_kind="organization-maintenance-cycle",
                    run_id="org-1",
                    scope="organization-maintenance",
                    wait=False,
                    cleanup_evidence={
                        "cleanup_confirmed": True,
                        "remaining_process_count": 0,
                    },
                )

            self.assertFalse(blocked["acquired"])
            self.assertEqual(blocked["reason"], "cleanup-confirmation-required")
            self.assertTrue(recovered["acquired"])
            self.assertEqual(
                read_global_write_lease(repo_root)["root_owner_run_id"], "org-1"
            )
            release_global_write_lease(
                repo_root,
                lease_id=recovered["lease_id"],
                lease_token=recovered["lease_token"],
            )

    def test_timeout_cleanup_recovers_only_the_matching_dead_global_writer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            first = acquire_global_write_lease(
                repo_root,
                cycle_kind="local-maintenance-cycle",
                run_id="timed-out-sleep",
                scope="sleep",
                wait=False,
            )
            self.assertTrue(first["acquired"])
            with patch(
                "local_kb.maintenance_lanes.process_owner_is_alive",
                return_value=False,
            ):
                recovered = recover_global_write_lease_after_cleanup(
                    repo_root,
                    expected_root_owner_run_id="timed-out-sleep",
                    cleanup_evidence={
                        "cleanup_confirmed": True,
                        "remaining_process_count": 0,
                    },
                )

            self.assertTrue(recovered["ok"])
            self.assertEqual(recovered["status"], "recovered")
            self.assertEqual(read_global_write_lease(repo_root), {})

    def test_timeout_cleanup_does_not_remove_another_owner_lease(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            first = acquire_global_write_lease(
                repo_root,
                cycle_kind="local-maintenance-cycle",
                run_id="other-run",
                scope="sleep",
                wait=False,
            )
            self.assertTrue(first["acquired"])
            with patch(
                "local_kb.maintenance_lanes.process_owner_is_alive",
                return_value=False,
            ):
                blocked = recover_global_write_lease_after_cleanup(
                    repo_root,
                    expected_root_owner_run_id="timed-out-sleep",
                    cleanup_evidence={
                        "cleanup_confirmed": True,
                        "remaining_process_count": 0,
                    },
                )

            self.assertFalse(blocked["ok"])
            self.assertEqual(blocked["reason"], "global-writer-owner-mismatch")
            release_global_write_lease(
                repo_root,
                lease_id=first["lease_id"],
                lease_token=first["lease_token"],
            )

    def test_local_maintenance_lanes_share_one_waiting_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)

            first = acquire_lane_lock(repo_root, "kb-sleep", run_id="sleep-1", poll_seconds=0)
            second = acquire_lane_lock(repo_root, "kb-dream", run_id="dream-1", wait=False, poll_seconds=0)

            self.assertTrue(first["acquired"])
            self.assertFalse(second["acquired"])
            self.assertEqual(second["blocked_by"]["lane"], "kb-sleep")
            self.assertEqual(build_lane_guard(repo_root, "kb-dream")["blocking_lanes"], ["kb-sleep"])

            released = release_lane_lock(repo_root, "kb-sleep", run_id="sleep-1")
            self.assertTrue(released["released"])
            self.assertEqual(read_lane_lock(repo_root, "local-maintenance"), {})

    def test_organization_lanes_share_a_separate_waiting_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)

            org = acquire_lane_lock(repo_root, "kb-org-contribute", run_id="contrib-1", poll_seconds=0)
            local = acquire_lane_lock(repo_root, "kb-dream", run_id="dream-1", wait=False, poll_seconds=0)
            blocked_org = acquire_lane_lock(
                repo_root,
                "kb-org-maintenance",
                run_id="maint-1",
                wait=False,
                poll_seconds=0,
            )

            self.assertEqual(lane_lock_group("kb-org-maintenance"), "organization-maintenance")
            self.assertTrue(org["acquired"])
            self.assertTrue(local["acquired"])
            self.assertFalse(blocked_org["acquired"])
            self.assertEqual(blocked_org["blocked_by"]["lane"], "kb-org-contribute")

    def test_stale_lane_lock_is_recovered(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)

            acquire_lane_lock(repo_root, "kb-sleep", run_id="sleep-1", poll_seconds=0)
            recovered = acquire_lane_lock(
                repo_root,
                "kb-dream",
                run_id="dream-1",
                poll_seconds=0,
                stale_after_seconds=0,
            )

            self.assertTrue(recovered["acquired"])
            self.assertEqual(recovered["lane"], "kb-dream")

    def test_fresh_lane_lock_with_dead_owner_is_recovered_immediately(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)

            acquire_lane_lock(repo_root, "kb-sleep", run_id="dead-sleep", poll_seconds=0)
            with patch(
                "local_kb.maintenance_lanes.process_owner_is_alive",
                return_value=False,
            ):
                recovered = acquire_lane_lock(
                    repo_root,
                    "kb-dream",
                    run_id="dream-after-crash",
                    wait=False,
                    poll_seconds=0,
                )

            self.assertTrue(recovered["acquired"])
            self.assertTrue(recovered["recovered"])
            self.assertEqual(recovered["recovery_reason"], "dead-owner")
            self.assertEqual(recovered["recovered_lock"]["run_id"], "dead-sleep")

    def test_running_status_without_lock_is_reconciled_as_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            write_lane_status(repo_root, "kb-org-contribute", "running", run_id="old-org-run")

            reconciled = reconcile_stale_lane_statuses(repo_root, lanes=("kb-org-contribute",))
            status = read_lane_status(repo_root, "kb-org-contribute")

        self.assertEqual(len(reconciled), 1)
        self.assertEqual(status["status"], "stale")
        self.assertEqual(status["run_id"], "old-org-run")
        self.assertIn("without an active lane lock", status["note"])

    def test_dream_releases_lock_and_marks_failed_on_exception(self) -> None:
        from local_kb.dream import run_dream_maintenance

        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)

            with patch("local_kb.dream.build_dream_guard", side_effect=RuntimeError("boom")):
                with self.assertRaises(RuntimeError):
                    run_dream_maintenance(repo_root, run_id="dream-fail")

            self.assertEqual(read_lane_lock(repo_root, "local-maintenance"), {})
            self.assertEqual(read_lane_status(repo_root, "kb-dream")["status"], "failed")

    def test_organization_contribute_releases_lock_and_marks_failed_on_exception(self) -> None:
        from local_kb.org_automation import run_organization_contribution

        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            source = {"path": str(repo_root / "org"), "organization_id": "sandbox", "repo_url": ""}
            settings = {"mode": "organization", "organization": {"validated": True}}

            with (
                patch("local_kb.org_automation._first_organization_source", return_value=(source, [source], settings)),
                patch("local_kb.org_automation._sync_first_organization_source", side_effect=RuntimeError("boom")),
            ):
                with self.assertRaises(RuntimeError):
                    run_organization_contribution(repo_root)

            self.assertEqual(read_lane_lock(repo_root, "organization-maintenance"), {})
            self.assertEqual(read_lane_status(repo_root, "kb-org-contribute")["status"], "failed")

    def test_organization_maintenance_releases_lock_and_marks_failed_on_exception(self) -> None:
        from local_kb.org_automation import run_organization_maintenance

        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            source = {"path": str(repo_root / "org"), "organization_id": "sandbox", "repo_url": ""}

            with (
                patch("local_kb.org_automation.load_desktop_settings", return_value={"mode": "organization"}),
                patch(
                    "local_kb.org_automation.maintenance_participation_status_from_settings",
                    return_value={"available": True, "requested": True},
                ),
                patch("local_kb.org_automation.organization_sources_from_settings", return_value=[source]),
                patch("local_kb.org_automation._sync_first_organization_source", side_effect=RuntimeError("boom")),
            ):
                with self.assertRaises(RuntimeError):
                    run_organization_maintenance(repo_root)

            self.assertEqual(read_lane_lock(repo_root, "organization-maintenance"), {})
            self.assertEqual(read_lane_status(repo_root, "kb-org-maintenance")["status"], "failed")


if __name__ == "__main__":
    unittest.main()
