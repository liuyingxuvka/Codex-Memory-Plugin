from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from local_kb.org_snapshot import load_current_organization_snapshot, stage_organization_snapshot
from local_kb.store import load_current_organization_entries, write_yaml_file


class OrganizationSnapshotTests(unittest.TestCase):
    def _card(self, path: Path, entry_id: str, status: str = "trusted") -> None:
        write_yaml_file(
            path,
            {
                "id": entry_id,
                "title": entry_id,
                "type": "model",
                "scope": "public",
                "status": status,
                "confidence": 0.8,
                "domain_path": ["organization", "snapshot"],
                "tags": ["organization"],
                "trigger_keywords": ["snapshot"],
                "if": {"notes": "snapshot input"},
                "action": {"description": "use"},
                "predict": {"expected_result": "usable"},
                "use": {"guidance": "direct read-only use"},
            },
        )

    def test_snapshot_contains_exact_active_ids_and_is_readable_without_mirror_scan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            org = root / "org"
            self._card(org / "kb" / "main" / "a.yaml", "a")
            self._card(org / "kb" / "main" / "candidate.yaml", "candidate", status="candidate")
            self._card(org / "kb" / "main" / "rejected.yaml", "rejected", status="rejected")

            result = stage_organization_snapshot(
                root,
                org,
                "sandbox",
                source_repo="remote",
                source_commit="commit-1",
            )
            self.assertTrue(result["ok"], result)
            self.assertEqual(result["active_entry_ids"], ["a", "candidate"])
            snapshot = load_current_organization_snapshot(root, "sandbox")
            self.assertTrue(snapshot["ok"], snapshot)
            entries = load_current_organization_entries(root, "sandbox")
            row = snapshot["manifest"]["cards"][0]

        self.assertEqual([entry.data["id"] for entry in entries], ["a", "candidate"])
        self.assertTrue(all(entry.source["foreign_state"] == "eligible_external" for entry in entries))
        self.assertEqual(snapshot["schema_version"], 2)
        self.assertTrue(row["bundle_digest"])
        self.assertTrue(row["binding"]["logicguard_model_id"])
        self.assertEqual(entries[0].data["projection_schema_version"], "khaos-brain.card-projection.v1")
        self.assertTrue(entries[0].source["logicguard_bundle"]["model_path"])

    def test_legacy_card_is_structurally_upgraded_without_fabricating_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            org = root / "org"
            write_yaml_file(
                org / "kb" / "main" / "legacy.yaml",
                {"id": "legacy", "title": "Legacy", "status": "trusted", "action": "use carefully"},
            )
            result = stage_organization_snapshot(root, org, "sandbox")
            self.assertTrue(result["ok"], result)
            entries = load_current_organization_entries(root, "sandbox")

        upgraded = entries[0].data
        self.assertEqual(upgraded["id"], "legacy")
        self.assertIn("expected_result", upgraded["predict"])
        self.assertTrue(upgraded["legacy_upgrade"]["structural_defaults_applied"])
        self.assertFalse(upgraded["legacy_upgrade"]["evidence_fabricated"])
        self.assertIn("evidence", upgraded["logicguard_open_role_gaps"])

    def test_duplicate_ids_receive_deterministic_legacy_ids_and_both_survive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            org = root / "org"
            self._card(org / "kb" / "main" / "a.yaml", "same")
            self._card(org / "kb" / "main" / "b.yaml", "same")
            result = stage_organization_snapshot(root, org, "sandbox")
            self.assertTrue(result["ok"], result)
            entries = load_current_organization_entries(root, "sandbox")
            snapshot = load_current_organization_snapshot(root, "sandbox")

            self.assertEqual(len(entries), 2)
            self.assertEqual(entries[0].data["id"], "same")
            self.assertTrue(entries[1].data["id"].startswith("same-legacy-"))
            self.assertEqual(entries[1].data["legacy_upgrade"]["duplicate_of"], "same")
            duplicate_row = next(row for row in snapshot["manifest"]["cards"] if row.get("duplicate_of"))
            self.assertEqual(entries[1].data["id"], duplicate_row["entry_id"])
            self.assertEqual(entries[1].data["id"], entries[1].source["logicguard_bundle"]["entry_id"])

    def test_malformed_active_card_does_not_replace_previous_complete_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            org = root / "org"
            card = org / "kb" / "main" / "a.yaml"
            self._card(card, "a")
            first = stage_organization_snapshot(root, org, "sandbox", source_commit="commit-1")
            self.assertTrue(first["ok"], first)
            pointer_before = load_current_organization_snapshot(root, "sandbox")
            card.write_text("id: [broken\n", encoding="utf-8")
            second = stage_organization_snapshot(root, org, "sandbox", source_commit="commit-2")
            pointer_after = load_current_organization_snapshot(root, "sandbox")

        self.assertFalse(second["ok"])
        self.assertEqual(pointer_after["generation_id"], pointer_before["generation_id"])
        self.assertEqual(pointer_after["source_commit"], pointer_before["source_commit"])


if __name__ == "__main__":
    unittest.main()
