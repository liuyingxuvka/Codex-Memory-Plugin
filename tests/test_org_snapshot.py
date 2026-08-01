from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from local_kb.org_snapshot import load_current_organization_snapshot, stage_organization_snapshot
from local_kb.org_source_contract import materialize_current_source
from local_kb.store import load_current_organization_entries, write_yaml_file
from tests.org_helpers import base_card


class OrganizationSnapshotTests(unittest.TestCase):
    def _current_source(self, root: Path) -> Path:
        org = root / "org"
        materialize_current_source(
            org,
            organization_id="sandbox",
            cards=[
                ("kb/main/a.yaml", base_card("a", "A", "Use A.")),
                ("kb/main/candidate.yaml", base_card("candidate", "Candidate", "Use candidate.", status="candidate")),
                ("kb/main/rejected.yaml", base_card("rejected", "Rejected", "Do not use.", status="rejected")),
            ],
        )
        return org

    def test_snapshot_copies_exact_current_active_bundles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            org = self._current_source(root)
            result = stage_organization_snapshot(root, org, "sandbox", source_repo="remote", source_commit="commit-1")
            snapshot = load_current_organization_snapshot(root, "sandbox")
            entries = load_current_organization_entries(root, "sandbox")

        self.assertTrue(result["ok"], result)
        self.assertTrue(snapshot["ok"], snapshot)
        self.assertEqual(result["active_entry_ids"], ["a", "candidate"])
        self.assertEqual({entry.data["id"] for entry in entries}, {"a", "candidate"})
        self.assertEqual(snapshot["schema_version"], 3)
        self.assertTrue(all(row["bundle_digest"] for row in snapshot["manifest"]["cards"]))

    def test_raw_legacy_card_is_rejected_by_normal_snapshot_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            org = root / "org"
            write_yaml_file(org / "kb" / "main" / "legacy.yaml", base_card("legacy", "Legacy", "Use."))
            result = stage_organization_snapshot(root, org, "sandbox")

        self.assertFalse(result["ok"])
        self.assertIn("exact current source contract", " ".join(result["errors"]))

    def test_unchanged_source_reuses_content_addressed_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            org = self._current_source(root)
            first = stage_organization_snapshot(root, org, "sandbox", source_commit="commit-1")
            second = stage_organization_snapshot(root, org, "sandbox", source_commit="commit-1")

        self.assertTrue(first["ok"], first)
        self.assertTrue(second["ok"], second)
        self.assertEqual(first["generation_id"], second["generation_id"])
        self.assertEqual(second["status"], "reused")

    def test_invalid_changed_source_does_not_replace_previous_pointer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            org = self._current_source(root)
            first = stage_organization_snapshot(root, org, "sandbox", source_commit="commit-1")
            pointer_before = load_current_organization_snapshot(root, "sandbox")
            (org / "kb" / "main" / "a.yaml").write_text("id: [broken\n", encoding="utf-8")
            second = stage_organization_snapshot(root, org, "sandbox", source_commit="commit-2")
            pointer_after = load_current_organization_snapshot(root, "sandbox")

        self.assertTrue(first["ok"], first)
        self.assertFalse(second["ok"])
        self.assertEqual(pointer_after["generation_id"], pointer_before["generation_id"])
        self.assertEqual(pointer_after["source_commit"], "commit-1")

    def test_pointer_cas_rejects_a_stale_expected_predecessor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            org = self._current_source(root)
            first = stage_organization_snapshot(root, org, "sandbox", source_commit="commit-1")
            conflict = stage_organization_snapshot(
                root,
                org,
                "sandbox",
                source_commit="commit-1",
                expected_pointer_digest="sha256:stale",
            )

        self.assertTrue(first["ok"], first)
        self.assertFalse(conflict["ok"])
        self.assertEqual(conflict["status"], "pointer-conflict")

    def test_existing_content_addressed_generation_is_never_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            org = self._current_source(root)
            first = stage_organization_snapshot(root, org, "sandbox", source_commit="commit-1")
            generation = Path(first["generation_root"])
            bundle = next((generation / "logicguard" / "b").glob("*.json"))
            bundle.write_text("{}\n", encoding="utf-8")
            second = stage_organization_snapshot(root, org, "sandbox", source_commit="commit-1")

        self.assertFalse(second["ok"])
        self.assertEqual(second["status"], "immutable-generation-conflict")


if __name__ == "__main__":
    unittest.main()
