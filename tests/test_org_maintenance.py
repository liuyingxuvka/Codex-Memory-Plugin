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
            self._source(
                root,
                [("kb/main/system/skills/skill-card.yaml", base_card("skill-card", "Unique skill card", "A unique exchange card."))],
            )
            report = build_organization_maintenance_report(root)

        self.assertTrue(report["cleanup"]["card_decision_checkpoint"]["complete"], report)
        decisions = report["cleanup"]["card_decision_checkpoint"]["decisions"]
        self.assertEqual({item["entry_id"] for item in decisions}, {"skill-card"})
        self.assertEqual(report["main_active_count"], 1)
        checkpoints = report["cleanup"]["checkpoints"]
        self.assertEqual(
            set(checkpoints),
            {
                "card_surface",
                "candidate_intake",
                "content_hash",
                "merge",
                "split",
                "card_decisions",
                "skill_safety",
                "skill_bundle_version",
                "decision_apply",
                "post_apply",
                "github_merge_readiness",
            },
        )
        self.assertTrue(all(item["complete"] for item in checkpoints.values()), checkpoints)

    def test_report_keeps_imports_separate_from_download_surface(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._source(root)
            write_yaml_file(root / "kb" / "imports" / "alice" / "incoming.yaml", base_card("incoming", "Incoming", "Review.", status="candidate"))
            report = build_organization_maintenance_report(root)

        self.assertEqual(report["layout_policy"]["exchange_surface_path"], "kb/main")
        self.assertEqual(report["layout_policy"]["local_download_excluded_paths"], ["kb/imports"])
        self.assertEqual(report["imports_count"], 1)
        self.assertTrue(report["cleanup"]["candidate_intake_checkpoint"]["complete"])
        self.assertEqual(report["cleanup"]["candidate_intake_checkpoint"]["imports_count"], 1)

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
        self.assertTrue(report["cleanup"]["merge_checkpoint"]["complete"], report)
        self.assertTrue(report["cleanup"]["split_checkpoint"]["complete"], report)
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
        self.assertTrue(report["cleanup"]["decision_apply_checkpoint"]["complete"])
        self.assertTrue(report["cleanup"]["post_apply_checkpoint"]["complete"])
        self.assertTrue(report["cleanup"]["post_apply_checkpoint"]["ok"])

    def test_review_selects_only_non_overlapping_merge_packets_per_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cards: list[tuple[str, dict]] = []
            for entry_id, title in (("left", "Same route"), ("middle", "Same route!"), ("right", "Same route?")):
                card = base_card(entry_id, title, "Use the same route.", status="candidate", confidence=0.7)
                card["evidence"] = ["shared-evidence"]
                cards.append((f"kb/main/{entry_id}.yaml", card))
            self._source(root, cards)

            report = build_organization_maintenance_report(root, apply_reviewed_cleanup=True)
            merge_decisions = [
                row
                for row in report["cleanup"]["review"]["decisions"]
                if row["action_type"] == "merge-cards"
            ]
            exact = report["cleanup"]["exact_selected_apply"]

        selected = [row for row in merge_decisions if row["decision"] == "selected-for-apply"]
        deferred = [row for row in merge_decisions if row["decision"] == "blocked_evidence"]
        self.assertEqual(len(selected), 1, merge_decisions)
        self.assertEqual(len(deferred), 2, merge_decisions)
        self.assertTrue(all("next source generation" in row["reason"] for row in deferred), deferred)
        self.assertTrue(exact["exact"], exact)
        self.assertEqual(exact["selected_action_ids"], exact["applied_action_ids"])

    def test_skill_bundle_checkpoint_exposes_latest_lineage_and_fork_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cards: list[tuple[str, dict]] = []
            for entry_id, author, version, digest in (
                ("older", "author-a", "2026-01-01T00:00:00Z", "a" * 64),
                ("latest", "author-a", "2026-03-01T00:00:00Z", "c" * 64),
                ("fork", "author-b", "2026-04-01T00:00:00Z", "b" * 64),
            ):
                card = base_card(entry_id, f"{entry_id} Skill card", "Keep the bundle lineage.", status="candidate")
                card["organization_proposal"] = {
                    "skill_dependencies": [
                        {
                            "id": "demo-skill",
                            "sharing_mode": "card-bound-bundle",
                            "bundle_id": "shared-lineage",
                            "content_hash": f"sha256:{digest}",
                            "version_time": version,
                            "original_author": author,
                            "readonly_when_imported": True,
                            "update_policy": "original_author_only",
                            "bundle_path": "skills/shared-lineage/demo-skill",
                        }
                    ]
                }
                cards.append((f"kb/main/candidates/{entry_id}.yaml", card))
            self._source(root, cards)
            report = build_organization_maintenance_report(root)
            checkpoint = report["cleanup"]["skill_bundle_version_checkpoint"]

        self.assertFalse(checkpoint["passed"], checkpoint)
        self.assertTrue(checkpoint["forked_versions"], checkpoint)
        self.assertEqual(checkpoint["forked_versions"][0]["original_author"], "author-b")
        self.assertIn("skill-bundle-fork-required", [
            action["action_type"] for action in report["cleanup"]["proposal"]["actions"]
        ])


if __name__ == "__main__":
    unittest.main()
