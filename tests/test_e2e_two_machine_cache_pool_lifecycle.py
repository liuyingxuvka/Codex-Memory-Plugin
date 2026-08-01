from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from local_kb.lifecycle import record_outcome_receipt, record_retrieval_interaction
from local_kb.ui_data import build_search_payload
from tests.org_helpers import connect_profile_to_org, init_git_repo, write_valid_org_repo


class TwoMachineCachePoolLifecycleE2ETests(unittest.TestCase):
    def test_machine_b_uses_skill_bound_org_card_without_copy_or_install(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            org_repo = root / "org-source"
            machine_a = root / "machine-a"
            machine_b = root / "machine-b"
            write_valid_org_repo(org_repo, include_sandbox_cards=True)
            init_git_repo(org_repo)

            connect_a, _sources_a = connect_profile_to_org(machine_a, org_repo)
            connect_b, sources_b = connect_profile_to_org(machine_b, org_repo)
            payload = build_search_payload(
                machine_b,
                "id:sandbox-unique-skill",
                organization_sources=sources_b,
            )
            org_summary = next(
                item
                for item in payload["results"]
                if item["source_info"]["kind"] == "organization"
            )
            record_retrieval_interaction(
                machine_b,
                request_id=org_summary["retrieval_request_id"],
                result_refs=[org_summary["result_ref"]],
                interaction="used",
                event_id="test:machine-b:skill-card:used",
                actor="machine-b",
            )
            outcome = record_outcome_receipt(
                machine_b,
                request_id=org_summary["retrieval_request_id"],
                used_result_refs=[org_summary["result_ref"]],
                outcome="success",
                evidence_kind="task",
                evidence_ref="machine-b:task",
            )
            installed_skill_files = sorted(
                (machine_b / ".local" / "organization_skills").rglob("SKILL.md")
            )
            has_adopted_copy = (machine_b / "kb" / "candidates" / "adopted").exists()

        self.assertTrue(connect_a["ok"], connect_a)
        self.assertTrue(connect_b["ok"], connect_b)
        self.assertEqual(org_summary["id"], "sandbox-unique-skill")
        self.assertEqual(org_summary["source_info"]["scope"], "candidate")
        self.assertEqual(outcome["used_results"][0]["source_kind"], "organization")
        self.assertEqual(len(installed_skill_files), 0)
        self.assertFalse(has_adopted_copy)


if __name__ == "__main__":
    unittest.main()
