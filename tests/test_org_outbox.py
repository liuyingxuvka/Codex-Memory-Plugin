from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from local_kb.adoption import card_exchange_hash, record_exchange_hash
from local_kb.org_outbox import build_organization_outbox
from local_kb.store import load_yaml_file, write_yaml_file
from tests.current_runtime_helpers import activate_current_kb_runtime


class OrganizationOutboxTests(unittest.TestCase):
    def _card(self, entry_id: str, card_type: str = "model", scope: str = "public") -> dict:
        return {
            "id": entry_id,
            "title": f"{entry_id} title",
            "type": card_type,
            "scope": scope,
            "status": "trusted",
            "confidence": 0.8,
            "domain_path": ["shared"],
            "tags": ["shared"],
            "trigger_keywords": ["shared"],
            "if": {"notes": "Shareable scenario."},
            "action": {"description": "Use card."},
            "predict": {"expected_result": "Card helps."},
            "use": {"guidance": "Share only when eligible."},
        }

    def test_outbox_exports_only_current_shareable_local_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_yaml_file(root / "kb" / "public" / "model.yaml", self._card("share-model"))
            duplicate = self._card("share-model-duplicate")
            duplicate["title"] = "share-model title"
            write_yaml_file(root / "kb" / "public" / "z-model-copy.yaml", duplicate)
            write_yaml_file(root / "kb" / "public" / "preference.yaml", self._card("skip-pref", card_type="preference"))
            write_yaml_file(root / "kb" / "private" / "private.yaml", self._card("skip-private", scope="private"))
            retired = self._card("retired-adopted")
            retired["organization_adoption"] = {"state": "diverged"}
            write_yaml_file(root / "kb" / "public" / "retired.yaml", retired)
            activate_current_kb_runtime(root)

            result = build_organization_outbox(root, organization_id="sandbox")
            created_ids = [item["entry_id"] for item in result["created"]]
            outbox_files = sorted((root / "kb" / "outbox" / "organization" / "sandbox").glob("*.yaml"))
            payloads = [load_yaml_file(path) for path in outbox_files]

        self.assertTrue(result["ok"])
        self.assertEqual(created_ids, ["share-model"])
        self.assertEqual(len(payloads), 1)
        self.assertTrue(all(payload["status"] == "candidate" for payload in payloads))
        self.assertEqual(
            payloads[0]["organization_proposal"]["proposal_kind"],
            "local-card",
        )
        self.assertTrue(all(payload["organization_proposal"]["content_hash"] for payload in payloads))
        skipped = {item["entry_id"]: item["reasons"] for item in result["skipped"]}
        self.assertIn("duplicate content hash already exported", skipped["share-model-duplicate"])
        self.assertIn("card type is not shareable", skipped["skip-pref"])
        self.assertIn("card scope is not public", skipped["skip-private"])
        self.assertIn(
            "retired organization_adoption metadata requires direct upgrade",
            skipped["retired-adopted"],
        )

    def test_outbox_dry_run_does_not_write_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_yaml_file(root / "kb" / "public" / "model.yaml", self._card("share-model"))
            activate_current_kb_runtime(root)

            result = build_organization_outbox(root, organization_id="sandbox", dry_run=True)

            self.assertTrue(result["ok"])
            self.assertEqual(result["created_count"], 1)
            self.assertFalse((root / "kb" / "outbox").exists())

    def test_outbox_blocks_machine_specific_payloads_before_materialization(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            secret = self._card("secret-card")
            secret["action"] = {
                "description": "Never publish this machine-bound payload.",
                "api_key": "sk-abcdefghijklmnopqrstuvwxyz123456",
                "workspace": r"C:\Users\alice\private-workspace",
                "machine_id": "machine-123",
            }
            write_yaml_file(root / "kb" / "public" / "secret.yaml", secret)
            activate_current_kb_runtime(root)

            result = build_organization_outbox(root, organization_id="sandbox")

        self.assertTrue(result["ok"], result)
        self.assertEqual(result["created_count"], 0)
        self.assertEqual(result["privacy_checkpoint"]["reviewed_count"], 1)
        self.assertEqual(result["privacy_checkpoint"]["blocked_sensitive_count"], 1)
        self.assertFalse((root / "kb" / "outbox").exists())
        reasons = result["skipped"][0]["reasons"]
        self.assertTrue(any("secret" in reason.lower() for reason in reasons), reasons)
        self.assertTrue(any("local machine path" in reason.lower() for reason in reasons), reasons)
        self.assertTrue(any("machine identifier" in reason.lower() for reason in reasons), reasons)

    def test_retired_adoption_metadata_is_not_a_normal_outbox_reader(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            retired = self._card("retired-local-source")
            retired["organization_adoption"] = {
                "source_repo": r"C:\Users\alice\org-clone",
                "state": "diverged",
            }
            write_yaml_file(root / "kb" / "public" / "retired.yaml", retired)
            activate_current_kb_runtime(root)

            result = build_organization_outbox(root, organization_id="sandbox")

        self.assertTrue(result["ok"], result)
        self.assertEqual(result["created_count"], 0, result)
        self.assertFalse((root / "kb" / "outbox").exists())
        self.assertIn(
            "retired organization_adoption metadata requires direct upgrade",
            result["skipped"][0]["reasons"],
        )

    def test_outbox_blocks_skill_dependency_without_usefulness_outcome_and_unavailable_guidance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            card = self._card("incomplete-skill-card")
            card["required_skills"] = ["demo-skill"]
            card["use"] = {"guidance": "The Skill may help."}
            write_yaml_file(root / "kb" / "public" / "incomplete.yaml", card)
            activate_current_kb_runtime(root)

            result = build_organization_outbox(root, organization_id="sandbox")

        self.assertTrue(result["ok"], result)
        self.assertEqual(result["created_count"], 0)
        checkpoint = result["skill_bundle_checkpoint"]
        self.assertEqual(checkpoint["dependency_evidence_reviewed_count"], 1)
        self.assertEqual(checkpoint["dependency_evidence_blocked_count"], 1)
        reasons = result["skipped"][0]["reasons"]
        self.assertTrue(any("unavailable-skill-guidance" in reason for reason in reasons), reasons)

    def test_outbox_skips_hashes_already_exported_or_present_in_organization(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            org = root / "org"
            write_yaml_file(root / "kb" / "public" / "model.yaml", self._card("share-model"))
            write_yaml_file(org / "kb" / "main" / "existing.yaml", self._card("existing-org"))
            write_yaml_file(org / "kb" / "imports" / "alice" / "existing-import.yaml", self._card("existing-import"))
            local_duplicate = self._card("local-duplicate")
            local_duplicate["title"] = "existing-org title"
            write_yaml_file(root / "kb" / "public" / "local-duplicate.yaml", local_duplicate)
            import_duplicate = self._card("import-duplicate")
            import_duplicate["title"] = "existing-import title"
            write_yaml_file(root / "kb" / "public" / "import-duplicate.yaml", import_duplicate)
            sources = [{"path": str(org), "organization_id": "sandbox"}]
            activate_current_kb_runtime(root)

            first = build_organization_outbox(root, organization_id="sandbox", organization_sources=sources)
            record_exchange_hash(
                root,
                first["created"][0]["content_hash"],
                direction="uploaded",
                organization_id="sandbox",
                source_path=first["created"][0]["source_path"],
                entry_id=first["created"][0]["entry_id"],
            )
            second = build_organization_outbox(root, organization_id="sandbox", organization_sources=sources)

        self.assertEqual([item["entry_id"] for item in first["created"]], ["share-model"])
        first_skipped = {item["entry_id"]: item["reasons"] for item in first["skipped"]}
        self.assertIn("content hash already exists in organization repository", first_skipped["local-duplicate"])
        self.assertIn("content hash already exists in organization repository", first_skipped["import-duplicate"])
        self.assertEqual(second["created_count"], 0)
        second_skipped = {item["entry_id"]: item["reasons"] for item in second["skipped"]}
        self.assertIn("content hash was already exchanged with organization", second_skipped["share-model"])

    def test_retired_download_ledger_status_is_not_runtime_dedupe_authority(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            downloaded = self._card("previously-downloaded")
            write_yaml_file(root / "kb" / "public" / "downloaded.yaml", downloaded)
            record_exchange_hash(
                root,
                card_exchange_hash(downloaded),
                direction="downloaded",
                organization_id="sandbox",
                source_path="kb/trusted/previously-downloaded.yaml",
                entry_id="previously-downloaded",
            )
            activate_current_kb_runtime(root)

            result = build_organization_outbox(root, organization_id="sandbox")

        self.assertEqual(result["created_count"], 1)
        self.assertEqual(result["created"][0]["entry_id"], "previously-downloaded")


if __name__ == "__main__":
    unittest.main()
