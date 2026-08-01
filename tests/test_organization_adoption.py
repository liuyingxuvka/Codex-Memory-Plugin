from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import local_kb.adoption as adoption
from local_kb.adoption import card_exchange_hash
from local_kb.org_snapshot import stage_organization_snapshot
from local_kb.org_source_contract import materialize_current_source
from local_kb.search import render_search_payload, search_multi_source_entries
from tests.current_runtime_helpers import activate_current_kb_runtime


def organization_card() -> dict:
    return {
        "id": "org-card",
        "title": "Organization shared card",
        "type": "model",
        "scope": "public",
        "status": "trusted",
        "confidence": 0.9,
        "domain_path": ["shared", "organization"],
        "tags": ["shared", "organization"],
        "trigger_keywords": ["shared", "organization"],
        "required_skills": ["demo-skill"],
        "if": {"notes": "A shared organization scenario."},
        "action": {"description": "Use the foreign card directly."},
        "predict": {"expected_result": "No local adopted card is created."},
        "use": {"guidance": "Keep foreign authority read-only."},
    }


class OrganizationAdoptionTests(unittest.TestCase):
    def _stage(self, root: Path, org: Path) -> None:
        materialize_current_source(
            org,
            organization_id="sandbox",
            cards=[("kb/main/trusted/org-card.yaml", organization_card())],
        )
        result = stage_organization_snapshot(root, org, "sandbox")
        self.assertTrue(result["ok"], result)

    def test_foreign_card_is_used_directly_without_local_adoption_or_skill_install(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            org = root / "org"
            activate_current_kb_runtime(root)
            self._stage(root, org)

            results = search_multi_source_entries(
                root,
                query="shared organization",
                path_hint="shared/organization",
                organization_sources=[
                    {"path": str(org), "organization_id": "sandbox"}
                ],
            )
            payload = render_search_payload(results, root)

            self.assertEqual([item["id"] for item in payload], ["org-card"])
            self.assertEqual(payload[0]["source_kind"], "organization")
            self.assertTrue(payload[0]["read_only"])
            self.assertTrue(payload[0]["result_ref"])
            self.assertFalse((root / "kb" / "candidates" / "adopted").exists())
            self.assertFalse((root / ".agents" / "skills" / "imported").exists())

    def test_removed_adoption_and_skill_install_paths_have_no_runtime_entrypoint(self) -> None:
        self.assertFalse(hasattr(adoption, "adopt_organization_entry"))
        self.assertFalse(hasattr(adoption, "adopt_organization_entry_by_source_info"))
        self.assertFalse(hasattr(adoption, "adopt_entry_skill_bundles"))

    def test_retired_adoption_metadata_has_no_normal_hash_compatibility(self) -> None:
        payload = organization_card()
        retired = {
            **payload,
            "organization_adoption": {
                "source_content_hash": "retired",
                "state": "clean",
            },
        }

        self.assertNotEqual(card_exchange_hash(payload), card_exchange_hash(retired))


if __name__ == "__main__":
    unittest.main()
