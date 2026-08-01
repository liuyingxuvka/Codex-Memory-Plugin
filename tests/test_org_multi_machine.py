from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from local_kb.lifecycle import (
    outcome_receipts_path,
    record_outcome_receipt,
    record_retrieval_interaction,
    retrieval_receipts_path,
)
from local_kb.ui_data import build_search_payload
from tests.org_helpers import (
    connect_profile_to_org,
    init_git_repo,
    write_valid_org_repo,
)


class OrganizationMultiMachineTests(unittest.TestCase):
    def test_two_profiles_share_foreign_authority_but_keep_use_outcomes_local(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            org_source = root / "org-source"
            profile_a = root / "profile-a"
            profile_b = root / "profile-b"
            write_valid_org_repo(org_source, include_sandbox_cards=True)
            init_git_repo(org_source)
            connect_a, sources_a = connect_profile_to_org(profile_a, org_source)
            connect_b, sources_b = connect_profile_to_org(profile_b, org_source)

            payload_a = build_search_payload(
                profile_a,
                "Repository tasks scan local KB first",
                organization_sources=sources_a,
            )
            payload_b = build_search_payload(
                profile_b,
                "Repository tasks scan local KB first",
                organization_sources=sources_b,
            )
            result_a = payload_a["results"][0]
            result_b = payload_b["results"][0]
            for profile, result, suffix in (
                (profile_a, result_a, "a"),
                (profile_b, result_b, "b"),
            ):
                record_retrieval_interaction(
                    profile,
                    request_id=result["retrieval_request_id"],
                    result_refs=[result["result_ref"]],
                    interaction="used",
                    event_id=f"test:multi-machine:{suffix}:used",
                    actor=f"profile-{suffix}",
                )
                record_outcome_receipt(
                    profile,
                    request_id=result["retrieval_request_id"],
                    used_result_refs=[result["result_ref"]],
                    outcome="success" if suffix == "a" else "rework",
                    evidence_kind="task",
                    evidence_ref=f"profile-{suffix}:task",
                )

            a_receipts = outcome_receipts_path(profile_a).read_text(encoding="utf-8")
            b_receipts = outcome_receipts_path(profile_b).read_text(encoding="utf-8")
            a_has_retrieval_receipt = retrieval_receipts_path(profile_a).is_file()
            b_has_retrieval_receipt = retrieval_receipts_path(profile_b).is_file()
            a_has_adopted = (profile_a / "kb" / "candidates" / "adopted").exists()
            b_has_adopted = (profile_b / "kb" / "candidates" / "adopted").exists()

        self.assertTrue(connect_a["ok"], connect_a)
        self.assertTrue(connect_b["ok"], connect_b)
        self.assertEqual(result_a["knowledge_ref"], result_b["knowledge_ref"])
        self.assertEqual(result_a["source_kind"], "organization")
        self.assertEqual(result_b["source_kind"], "organization")
        self.assertIn('"outcome":"success"', a_receipts)
        self.assertNotIn('"outcome":"rework"', a_receipts)
        self.assertIn('"outcome":"rework"', b_receipts)
        self.assertNotIn('"outcome":"success"', b_receipts)
        self.assertTrue(a_has_retrieval_receipt)
        self.assertTrue(b_has_retrieval_receipt)
        self.assertFalse(a_has_adopted)
        self.assertFalse(b_has_adopted)


if __name__ == "__main__":
    unittest.main()
