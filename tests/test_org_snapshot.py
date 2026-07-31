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

        self.assertEqual([entry.data["id"] for entry in entries], ["a", "candidate"])
        self.assertTrue(all(entry.source["foreign_state"] == "eligible_external" for entry in entries))

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
