from __future__ import annotations

import tempfile
import unittest
import json
from pathlib import Path
from unittest.mock import patch

from local_kb.search import render_search_payload, search_multi_source_entries
from local_kb.search import search_multi_source_result
from local_kb.calibration import plan_foreign_calibration
from local_kb.lifecycle import (
    RETRIEVAL_RECEIPT_SCHEMA,
    build_foreign_calibration_event,
    commit_lifecycle_event,
    foreign_calibration_current_path,
    lifecycle_events_path,
    record_outcome_receipt,
    record_retrieval_interaction,
    retrieval_receipts_path,
)
from local_kb.store import history_events_path
from local_kb.org_snapshot import stage_organization_snapshot
from local_kb.org_source_contract import materialize_current_source
from local_kb.store import load_yaml_file, write_yaml_file
from local_kb.ui_data import (
    build_card_detail_payload,
    build_route_view_payload,
    build_search_payload,
    build_skill_registry_payload,
    build_source_view_payload,
)
from tests.current_runtime_helpers import activate_current_kb_runtime


class MultiSourceSearchTests(unittest.TestCase):
    def _stage_snapshot(self, root: Path, org: Path) -> dict:
        cards = [
            (path.relative_to(org).as_posix(), load_yaml_file(path))
            for path in sorted((org / "kb" / "main").rglob("*.yaml"))
        ]
        materialize_current_source(org, organization_id="sandbox", cards=cards)
        return stage_organization_snapshot(root, org, "sandbox")

    def _write_card(
        self,
        path: Path,
        entry_id: str,
        title: str,
        route: list[str],
        *,
        status: str = "trusted",
        retrieval_eligible: bool = False,
    ) -> None:
        write_yaml_file(
            path,
            {
                "id": entry_id,
                "title": title,
                "type": "model",
                "scope": "public",
                "status": status,
                "retrieval_eligible": retrieval_eligible,
                "confidence": 0.9,
                "domain_path": route,
                "tags": ["shared", "organization"],
                "trigger_keywords": ["shared", "organization"],
                "required_skills": ["demo-skill"],
                "if": {"notes": "Shared search test scenario."},
                "action": {"description": "Use the shared test card."},
                "predict": {"expected_result": "The shared test card is found."},
                "use": {"guidance": "Use this card for multi-source search tests."},
            },
        )

    def test_multi_source_search_globally_ranks_local_and_organization_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            org = root / "org"
            self._write_card(root / "kb" / "public" / "local.yaml", "local-card", "Local shared card", ["shared"])
            self._write_card(org / "kb" / "main" / "org.yaml", "org-card", "Organization shared card", ["shared"])
            activate_current_kb_runtime(root)
            self.assertTrue(self._stage_snapshot(root, org)["ok"])

            results = search_multi_source_entries(
                root,
                query="shared organization",
                path_hint="shared",
                top_k=5,
                organization_sources=[{"path": str(org), "organization_id": "sandbox", "repo_url": "https://example.invalid/org.git"}],
            )
            payload = render_search_payload(results, root)
            receipts = [
                json.loads(line)
                for line in retrieval_receipts_path(root).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        self.assertEqual([item["id"] for item in payload], ["org-card", "local-card"])
        self.assertGreater(payload[0]["score"], payload[1]["score"])
        self.assertEqual(payload[1]["source_info"]["label"], "local/public")
        self.assertEqual(payload[1]["source_label"], "local/public")
        self.assertEqual(payload[0]["source_info"]["label"], "org/sandbox/trusted")
        self.assertEqual(payload[0]["source_label"], "org/sandbox/trusted")
        self.assertEqual(payload[0]["author_label"], "sandbox")
        self.assertTrue(payload[0]["source_info"]["read_only"])
        self.assertTrue(payload[0]["read_only"])
        self.assertEqual(len(receipts), 1)
        self.assertEqual(receipts[0]["schema_version"], RETRIEVAL_RECEIPT_SCHEMA)
        self.assertEqual(
            {item["source_kind"] for item in receipts[0]["returned_results"]},
            {"local", "organization"},
        )
        self.assertTrue(all(item["result_ref"] for item in receipts[0]["returned_results"]))

    def test_local_search_does_not_read_foreign_calibration_or_replay_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_card(
                root / "kb" / "public" / "local.yaml",
                "local-card",
                "Local shared card",
                ["shared"],
            )
            activate_current_kb_runtime(root)
            foreign_calibration_current_path(root).unlink(missing_ok=True)

            with (
                patch(
                    "local_kb.lifecycle.load_current_foreign_calibration",
                    side_effect=AssertionError("foreign calibration read"),
                ),
                patch(
                    "local_kb.lifecycle.replay_lifecycle",
                    side_effect=AssertionError("full lifecycle replay"),
                ),
            ):
                result = search_multi_source_result(
                    root,
                    query="shared",
                    organization_sources=[],
                    record_receipt=False,
                )

        self.assertEqual([entry.data["id"] for entry in result["results"]], ["local-card"])

    def test_organization_search_reads_compact_current_calibration_without_replay(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            org = root / "org"
            self._write_card(
                org / "kb" / "main" / "org.yaml",
                "org-card",
                "Organization shared card",
                ["shared"],
            )
            activate_current_kb_runtime(root)
            self.assertTrue(foreign_calibration_current_path(root).is_file())
            self.assertTrue(self._stage_snapshot(root, org)["ok"])

            with patch(
                "local_kb.lifecycle.replay_lifecycle",
                side_effect=AssertionError("full lifecycle replay"),
            ):
                result = search_multi_source_result(
                    root,
                    query="shared organization",
                    organization_sources=[
                        {"path": str(org), "organization_id": "sandbox"}
                    ],
                    record_receipt=False,
                )

        self.assertEqual([entry.data["id"] for entry in result["results"]], ["org-card"])

    def test_organization_search_fails_visibly_when_calibration_projection_is_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            org = root / "org"
            self._write_card(
                org / "kb" / "main" / "org.yaml",
                "org-card",
                "Organization shared card",
                ["shared"],
            )
            activate_current_kb_runtime(root)
            self.assertTrue(self._stage_snapshot(root, org)["ok"])
            projection = json.loads(
                foreign_calibration_current_path(root).read_text(encoding="utf-8")
            )
            event = {
                "schema_version": 1,
                "lifecycle_event_id": "test-stale-projection",
                "sequence": int(projection["source_last_sequence"]) + 1,
                "event_type": "observation-admitted",
                "item_id": "observation-stale-projection",
                "idempotency_key": "observation-stale-projection",
                "source_event": {},
                "source_fingerprint": "test",
                "evidence": [],
            }
            with lifecycle_events_path(root).open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")

            with self.assertRaisesRegex(RuntimeError, "source-event-file-stale"):
                search_multi_source_result(
                    root,
                    query="shared organization",
                    organization_sources=[
                        {"path": str(org), "organization_id": "sandbox"}
                    ],
                    record_receipt=False,
                )

    def test_ui_search_payload_can_include_organization_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            org = root / "org"
            self._write_card(org / "kb" / "main" / "org.yaml", "org-card", "Organization shared card", ["shared"])
            activate_current_kb_runtime(root)
            self.assertTrue(self._stage_snapshot(root, org)["ok"])

            payload = build_search_payload(
                root,
                query="shared organization",
                route_hint="shared",
                organization_sources=[{"path": str(org), "organization_id": "sandbox"}],
            )

        self.assertEqual(payload["results"][0]["id"], "org-card")
        self.assertEqual(payload["results"][0]["source_info"]["kind"], "organization")

    def test_same_id_conflict_keeps_local_primary_and_foreign_alternative_visible(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            org = root / "org"
            self._write_card(
                root / "kb" / "public" / "same.yaml",
                "same-card",
                "Local primary wording",
                ["shared"],
            )
            self._write_card(
                org / "kb" / "main" / "same.yaml",
                "same-card",
                "Organization alternative wording",
                ["shared"],
            )
            activate_current_kb_runtime(root)
            self.assertTrue(self._stage_snapshot(root, org)["ok"])
            results = search_multi_source_entries(
                root,
                query="shared organization",
                organization_sources=[
                    {"path": str(org), "organization_id": "sandbox"}
                ],
            )

        self.assertEqual([item.data["id"] for item in results], ["same-card", "same-card"])
        self.assertEqual(
            [item.source["source_kind"] for item in results],
            ["local", "organization"],
        )
        self.assertEqual(results[0].source["source_conflict"]["role"], "primary")
        self.assertEqual(results[1].source["source_conflict"]["role"], "alternative")

    def test_foreign_outcome_is_exact_and_sleep_calibration_controls_later_ranking(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            org = root / "org"
            self._write_card(
                org / "kb" / "main" / "org.yaml",
                "org-card",
                "Organization shared card",
                ["shared"],
            )
            activate_current_kb_runtime(root)
            self.assertTrue(self._stage_snapshot(root, org)["ok"])
            source = {"path": str(org), "organization_id": "sandbox"}
            first = search_multi_source_result(
                root,
                query="shared organization",
                organization_sources=[source],
            )
            result_ref = first["retrieval_receipt"]["returned_results"][0]["result_ref"]
            request_id = first["retrieval_receipt"]["request_id"]
            for interaction in ("viewed", "selected", "used"):
                record_retrieval_interaction(
                    root,
                    request_id=request_id,
                    result_refs=[result_ref],
                    interaction=interaction,
                    event_id=f"test:org-card:{interaction}",
                    actor="pytest",
                )
            outcome = record_outcome_receipt(
                root,
                request_id=request_id,
                used_result_refs=[result_ref],
                outcome="misleading",
                evidence_kind="validation",
                evidence_ref="pytest:foreign-regression",
                verified=True,
            )
            self.assertEqual(outcome["used_results"][0]["source_id"], "sandbox")
            observation = next(
                row
                for row in (
                    json.loads(line)
                    for line in history_events_path(root).read_text(encoding="utf-8").splitlines()
                    if line.strip()
                )
                if str(row.get("event_id") or "").startswith("foreign-outcome:")
            )
            plan = plan_foreign_calibration(observation)[0]
            self.assertEqual(plan["disposition"], "suppress")
            commit_lifecycle_event(
                root,
                build_foreign_calibration_event(
                    observation,
                    run_id="sleep-test",
                    plan=plan,
                ),
            )
            after = search_multi_source_entries(
                root,
                query="shared organization",
                organization_sources=[source],
                record_receipt=False,
            )
            self.assertEqual(after, [])

    def test_normal_runtime_blocks_any_obsolete_organization_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            org = root / "org"
            self._write_card(
                org / "kb" / "main" / "current.yaml",
                "current-card",
                "Current organization card",
                ["shared"],
            )
            self._write_card(
                org / "kb" / "trusted" / "obsolete.yaml",
                "obsolete-card",
                "Obsolete organization card",
                ["shared"],
            )
            activate_current_kb_runtime(root)
            snapshot = stage_organization_snapshot(root, org, "sandbox")
            self.assertFalse(snapshot["ok"])
            payload = build_search_payload(
                root,
                query="organization card",
                organization_sources=[{"path": str(org), "organization_id": "sandbox"}],
            )
            self.assertEqual(payload["results"], [])
            self.assertEqual(payload["organization_status"][0]["status"], "unavailable")

    def test_organization_reads_only_main_active_statuses_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            org = root / "org"
            self._write_card(org / "kb" / "main" / "trusted.yaml", "trusted-card", "Organization trusted card", ["shared"])
            self._write_card(
                org / "kb" / "main" / "candidate.yaml",
                "candidate-card",
                "Organization candidate card",
                ["shared"],
                status="candidate",
                retrieval_eligible=True,
            )
            rejected = {
                "id": "rejected-card",
                "title": "Organization rejected card",
                "type": "model",
                "scope": "public",
                "status": "rejected",
                "confidence": 0.1,
                "domain_path": ["shared"],
                "tags": ["shared"],
                "trigger_keywords": ["shared"],
                "if": {"notes": "Rejected organization material."},
                "action": {"description": "Do not use."},
                "predict": {"expected_result": "It is filtered."},
                "use": {"guidance": "Filtered."},
            }
            write_yaml_file(org / "kb" / "main" / "rejected.yaml", rejected)
            self._write_card(org / "kb" / "imports" / "import.yaml", "import-card", "Organization import card", ["shared"])
            activate_current_kb_runtime(root)
            self.assertTrue(self._stage_snapshot(root, org)["ok"])

            payload = build_search_payload(
                root,
                query="Organization",
                route_hint="shared",
                organization_sources=[{"path": str(org), "organization_id": "sandbox"}],
            )
            result_ids = {item["id"] for item in payload["results"]}

        self.assertIn("trusted-card", result_ids)
        self.assertIn("candidate-card", result_ids)
        self.assertNotIn("rejected-card", result_ids)
        self.assertNotIn("import-card", result_ids)

    def test_untrusted_organization_candidate_is_visible_without_leaking_local_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            org = root / "org"
            self._write_card(
                root / "kb" / "candidates" / "local.yaml",
                "local-ineligible",
                "Local boundary candidate signal",
                ["shared"],
                status="candidate",
                retrieval_eligible=False,
            )
            self._write_card(
                org / "kb" / "main" / "org.yaml",
                "organization-untrusted",
                "Organization boundary candidate signal",
                ["shared"],
                status="candidate",
                retrieval_eligible=False,
            )
            activate_current_kb_runtime(root)
            self.assertTrue(self._stage_snapshot(root, org)["ok"])

            payload = render_search_payload(
                search_multi_source_entries(
                    root,
                    query="boundary candidate signal",
                    path_hint="shared",
                    top_k=5,
                    organization_sources=[
                        {"path": str(org), "organization_id": "sandbox"}
                    ],
                ),
                root,
            )

        self.assertEqual([item["id"] for item in payload], ["organization-untrusted"])
        self.assertEqual(payload[0]["trust_label"], "untrusted-candidate")
        self.assertTrue(payload[0]["source_info"]["read_only"])

    def test_route_and_source_views_include_organization_sources_when_connected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            org = root / "org"
            self._write_card(root / "kb" / "public" / "local.yaml", "local-card", "Local shared card", ["shared"])
            self._write_card(org / "kb" / "main" / "org.yaml", "org-card", "Organization shared card", ["shared"])
            sources = [{"path": str(org), "organization_id": "sandbox"}]
            activate_current_kb_runtime(root)
            self.assertTrue(self._stage_snapshot(root, org)["ok"])

            route_payload = build_route_view_payload(root, route="shared", organization_sources=sources)
            local_payload = build_source_view_payload(root, "local", organization_sources=sources)
            organization_payload = build_source_view_payload(root, "organization", organization_sources=sources)

        self.assertEqual([item["id"] for item in route_payload["deck"]], ["local-card", "org-card"])
        self.assertEqual([item["id"] for item in local_payload["deck"]], ["local-card"])
        self.assertEqual([item["id"] for item in organization_payload["deck"]], ["org-card"])

    def test_card_detail_payload_can_resolve_organization_search_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            org = root / "org"
            self._write_card(org / "kb" / "main" / "org.yaml", "org-card", "Organization shared card", ["shared"])
            activate_current_kb_runtime(root)
            self.assertTrue(self._stage_snapshot(root, org)["ok"])
            search_payload = build_search_payload(
                root,
                query="shared organization",
                route_hint="shared",
                organization_sources=[{"path": str(org), "organization_id": "sandbox"}],
            )

            detail = build_card_detail_payload(
                root,
                "org-card",
                organization_sources=[{"path": str(org), "organization_id": "sandbox"}],
                source_info=search_payload["results"][0]["source_info"],
            )

        self.assertIsNotNone(detail)
        assert detail is not None
        self.assertEqual(detail["id"], "org-card")
        self.assertEqual(detail["source_label"], "org/sandbox/trusted")
        self.assertTrue(detail["read_only"])
        self.assertEqual(detail["recent_history"], [])

    def test_card_detail_payload_prefers_organization_source_info_over_same_id_local_copy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            org = root / "org"
            self._write_card(root / "kb" / "candidates" / "adopted" / "sandbox" / "org-card.yaml", "org-card", "Local adopted copy", ["shared"])
            self._write_card(org / "kb" / "main" / "org.yaml", "org-card", "Organization shared card", ["shared"])
            activate_current_kb_runtime(root)
            self.assertTrue(self._stage_snapshot(root, org)["ok"])
            search_payload = build_search_payload(
                root,
                query="shared organization",
                route_hint="shared",
                organization_sources=[{"path": str(org), "organization_id": "sandbox"}],
            )
            organization_summary = next(
                item for item in search_payload["results"] if item["source_info"]["kind"] == "organization"
            )

            detail = build_card_detail_payload(
                root,
                "org-card",
                organization_sources=[{"path": str(org), "organization_id": "sandbox"}],
                source_info=organization_summary["source_info"],
            )

        self.assertIsNotNone(detail)
        assert detail is not None
        self.assertEqual(detail["title"], "Organization shared card")
        self.assertEqual(detail["source_info"]["kind"], "organization")
        self.assertEqual(detail["source_label"], "org/sandbox/trusted")
        self.assertTrue(detail["read_only"])

    def test_card_detail_payload_annotates_organization_skill_dependencies(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            org = root / "org"
            self._write_card(org / "kb" / "main" / "org.yaml", "org-card", "Organization shared card", ["shared"])
            write_yaml_file(
                org / "skills" / "registry.yaml",
                {
                    "skills": [
                        {
                            "id": "demo-skill",
                            "status": "approved",
                            "version": "1.0.0",
                            "source_repo": "https://example.invalid/skills.git",
                            "content_hash": "sha256:" + "a" * 64,
                        }
                    ]
                },
            )
            sources = [{"path": str(org), "organization_id": "sandbox"}]
            activate_current_kb_runtime(root)
            self.assertTrue(self._stage_snapshot(root, org)["ok"])

            detail = build_card_detail_payload(
                root,
                "org-card",
                organization_sources=sources,
                local_policy_allows_skill_auto_install=True,
            )
            registry = build_skill_registry_payload(sources, local_policy_allows_auto_install=True)

        self.assertIsNotNone(detail)
        assert detail is not None
        self.assertEqual(detail["skill_dependencies"][0]["registry_status"], "approved")
        self.assertTrue(detail["skill_dependencies"][0]["auto_install"]["eligible"])
        self.assertEqual(registry["counts"]["approved"], 1)
        self.assertTrue(registry["skills"][0]["auto_install"]["eligible"])


if __name__ == "__main__":
    unittest.main()
