from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from local_kb.org_maintenance import build_organization_maintenance_report
from local_kb.org_source_contract import materialize_current_source
from local_kb.org_sources import validate_organization_repo
from local_kb.store import write_yaml_file
from tests.org_helpers import base_card


class OrganizationMaintenanceTests(unittest.TestCase):
    def _source(self, root: Path, cards: list[tuple[str, dict]] | None = None) -> None:
        materialize_current_source(
            root,
            organization_id="sandbox",
            cards=cards or [
                ("kb/main/system/skills/skill-card.yaml", base_card("skill-card", "Skill card", "Use skill card.")),
                ("kb/main/candidate.yaml", base_card("candidate", "Candidate", "Use candidate.", status="candidate", confidence=0.6)),
            ],
        )

    def test_report_uses_exact_catalog_identity_coverage_including_skills_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._source(root)
            report = build_organization_maintenance_report(root)

        self.assertTrue(report["cleanup"]["card_decision_checkpoint"]["complete"], report)
        decisions = report["cleanup"]["card_decision_checkpoint"]["decisions"]
        self.assertEqual({item["entry_id"] for item in decisions}, {"skill-card", "candidate"})
        self.assertEqual(report["main_active_count"], 2)

    def test_report_keeps_imports_separate_from_download_surface(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._source(root)
            write_yaml_file(root / "kb" / "imports" / "alice" / "incoming.yaml", base_card("incoming", "Incoming", "Review.", status="candidate"))
            report = build_organization_maintenance_report(root)

        self.assertEqual(report["layout_policy"]["exchange_surface_path"], "kb/main")
        self.assertEqual(report["layout_policy"]["local_download_excluded_paths"], ["kb/imports"])
        self.assertEqual(report["imports_count"], 1)

    def test_merge_candidates_have_terminal_packet_or_reopen_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            left = base_card("left", "Same", "Use the same.")
            right = base_card("right", "Same!", "Use the same.", status="candidate")
            self._source(root, [("kb/main/left.yaml", left), ("kb/main/right.yaml", right)])
            report = build_organization_maintenance_report(root)
            checkpoint = report["cleanup"]["merge_split_checkpoint"]
            actions = [item for item in report["cleanup"]["proposal"]["actions"] if item["action_type"] in {"merge-cards", "split-card"}]

        self.assertTrue(checkpoint["complete"], checkpoint)
        self.assertTrue(actions)
        self.assertTrue(all(item.get("apply_packet", {}).get("packet_digest") for item in actions))
        self.assertTrue(all(item.get("review_status") in {"ready", "blocked_evidence", "keep_separate", "keep_single"} for item in actions))
        self.assertTrue(all(item.get("apply_packet", {}).get("reopen", {}).get("predicate") for item in actions))

    def test_apply_rebuilds_current_source_and_applies_exact_selected_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            weak = base_card("weak", "Weak", "Reject.", status="candidate", confidence=0.2)
            strong = base_card("strong", "Strong", "Trust.", status="candidate", confidence=0.9)
            self._source(root, [("kb/main/weak.yaml", weak), ("kb/main/strong.yaml", strong)])
            report = build_organization_maintenance_report(root, apply_reviewed_cleanup=True)
            exact = report["cleanup"]["exact_selected_apply"]
            validation = validate_organization_repo(root)

        self.assertTrue(validation["ok"], validation["errors"])
        self.assertTrue(exact["exact"], exact)
        self.assertEqual(set(exact["selected_action_ids"]), set(exact["applied_action_ids"]))
        self.assertTrue(report["cleanup"]["post_apply_validation"]["ok"])


if __name__ == "__main__":
    unittest.main()
