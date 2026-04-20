from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import yaml

from local_kb.consolidate import consolidate_history


class ConsolidateApplyModeTests(unittest.TestCase):
    def test_apply_mode_creates_candidate_for_grouped_route_actions_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            history_path = repo_root / "kb" / "history" / "events.jsonl"
            history_path.parent.mkdir(parents=True, exist_ok=True)

            events = [
                {
                    "event_id": "obs-new-cand-1",
                    "event_type": "observation",
                    "created_at": "2026-04-19T08:09:00+00:00",
                    "source": {"kind": "task", "agent": "worker-1"},
                    "target": {
                        "kind": "task-observation",
                        "route_hint": ["work", "communication", "email"],
                        "task_summary": "Need reusable email preference guidance",
                    },
                    "rationale": "next=new-candidate",
                    "context": {"suggested_action": "new-candidate"},
                },
                {
                    "event_id": "obs-new-cand-2",
                    "event_type": "observation",
                    "created_at": "2026-04-19T08:12:00+00:00",
                    "source": {"kind": "task", "agent": "worker-1"},
                    "target": {
                        "kind": "task-observation",
                        "route_hint": ["work", "communication", "email"],
                        "task_summary": "Need default reply-language card for email work",
                    },
                    "rationale": "next=new-candidate",
                    "context": {"suggested_action": "new-candidate"},
                },
                {
                    "event_id": "obs-update-1",
                    "event_type": "observation",
                    "created_at": "2026-04-19T08:15:00+00:00",
                    "source": {"kind": "task", "agent": "worker-1"},
                    "target": {
                        "kind": "task-observation",
                        "entry_ids": ["model-release-notes-first"],
                        "route_hint": ["engineering", "debugging", "version-change"],
                        "task_summary": "Release notes card needs a confidence update",
                    },
                    "rationale": "next=update-card",
                    "context": {"suggested_action": "update-card", "hit_quality": "miss"},
                },
            ]
            with history_path.open("w", encoding="utf-8") as handle:
                for event in events:
                    handle.write(json.dumps(event) + "\n")

            result = consolidate_history(
                repo_root=repo_root,
                run_id="apply-20260419",
                apply_mode="new-candidates",
            )

            self.assertEqual(result["candidate_action_count"], 6)
            self.assertEqual(result["apply_mode"], "new-candidates")
            self.assertEqual(result["apply_summary"]["created_candidate_count"], 1)
            self.assertEqual(result["apply_summary"]["skipped_action_count"], 5)
            self.assertIn("snapshot_path", result["artifact_paths"])
            self.assertIn("proposal_path", result["artifact_paths"])
            self.assertIn("apply_path", result["artifact_paths"])

            created_candidate = result["apply_summary"]["created_candidates"][0]
            candidate_path = repo_root / created_candidate["entry_path"]
            self.assertTrue(candidate_path.exists())

            candidate_payload = yaml.safe_load(candidate_path.read_text(encoding="utf-8"))
            self.assertEqual(candidate_payload["status"], "candidate")
            self.assertEqual(candidate_payload["scope"], "private")
            self.assertEqual(candidate_payload["domain_path"], ["work", "communication", "email"])
            self.assertEqual(candidate_payload["source"][0]["run_id"], "apply-20260419")
            self.assertIn("auto-created scaffold", candidate_payload["use"]["guidance"])

            apply_payload = json.loads(
                (repo_root / result["artifact_paths"]["apply_path"]).read_text(encoding="utf-8")
            )
            self.assertEqual(apply_payload["created_candidate_count"], 1)
            self.assertEqual(
                sorted(item["action_type"] for item in apply_payload["skipped_actions"]),
                [
                    "review-confidence",
                    "review-cross-index",
                    "review-entry-update",
                    "review-observation-evidence",
                    "review-observation-evidence",
                ],
            )

            history_events = [
                json.loads(line)
                for line in history_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertEqual(len(history_events), 4)
            self.assertEqual(history_events[-1]["event_type"], "candidate-created")
            self.assertEqual(history_events[-1]["source"]["kind"], "consolidation-apply")
            self.assertEqual(
                history_events[-1]["context"]["action_key"],
                created_candidate["action_key"],
            )

    def test_apply_mode_skips_single_observation_route_group(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            history_path = repo_root / "kb" / "history" / "events.jsonl"
            history_path.parent.mkdir(parents=True, exist_ok=True)

            event = {
                "event_id": "obs-new-cand-1",
                "event_type": "observation",
                "created_at": "2026-04-19T08:09:00+00:00",
                "source": {"kind": "task", "agent": "worker-1"},
                "target": {
                    "kind": "task-observation",
                    "route_hint": ["work", "reporting", "ppt"],
                    "task_summary": "Need a reusable slide-outline card",
                },
                "rationale": "next=new-candidate",
                "context": {"suggested_action": "new-candidate"},
            }
            history_path.write_text(json.dumps(event) + "\n", encoding="utf-8")

            result = consolidate_history(
                repo_root=repo_root,
                run_id="apply-single",
                apply_mode="new-candidates",
            )

            self.assertEqual(result["candidate_action_count"], 2)
            self.assertEqual(result["apply_summary"]["created_candidate_count"], 0)
            self.assertEqual(result["apply_summary"]["skipped_action_count"], 2)
            self.assertFalse((repo_root / "kb" / "candidates").exists())
            candidate_action = next(action for action in result["actions"] if action["action_type"] == "consider-new-candidate")
            self.assertFalse(candidate_action["apply_eligibility"]["eligible"])
            self.assertIn("review-observation-evidence", [item["action_type"] for item in result["apply_summary"]["skipped_actions"]])

    def test_apply_mode_skips_broad_routes_even_when_grouped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            history_path = repo_root / "kb" / "history" / "events.jsonl"
            history_path.parent.mkdir(parents=True, exist_ok=True)

            events = [
                {
                    "event_id": "obs-broad-1",
                    "event_type": "observation",
                    "created_at": "2026-04-20T08:09:00+00:00",
                    "source": {"kind": "task", "agent": "worker-2"},
                    "target": {
                        "kind": "task-observation",
                        "route_hint": ["engineering"],
                        "task_summary": "Need a general engineering refactor card",
                    },
                    "rationale": "next=new-candidate",
                    "context": {"suggested_action": "new-candidate"},
                },
                {
                    "event_id": "obs-broad-2",
                    "event_type": "observation",
                    "created_at": "2026-04-20T08:10:00+00:00",
                    "source": {"kind": "task", "agent": "worker-2"},
                    "target": {
                        "kind": "task-observation",
                        "route_hint": ["engineering"],
                        "task_summary": "Need another engineering workflow card",
                    },
                    "rationale": "next=new-candidate",
                    "context": {"suggested_action": "new-candidate"},
                },
                {
                    "event_id": "obs-specific-1",
                    "event_type": "observation",
                    "created_at": "2026-04-20T08:11:00+00:00",
                    "source": {"kind": "task", "agent": "worker-2"},
                    "target": {
                        "kind": "task-observation",
                        "route_hint": ["engineering", "ui-state", "desktop-app"],
                        "task_summary": "Need a desktop UI-state recovery card",
                    },
                    "rationale": "next=new-candidate",
                    "context": {"suggested_action": "new-candidate"},
                },
                {
                    "event_id": "obs-specific-2",
                    "event_type": "observation",
                    "created_at": "2026-04-20T08:12:00+00:00",
                    "source": {"kind": "task", "agent": "worker-2"},
                    "target": {
                        "kind": "task-observation",
                        "route_hint": ["engineering", "ui-state", "desktop-app"],
                        "task_summary": "Need a second desktop UI-state recovery card",
                    },
                    "rationale": "next=new-candidate",
                    "context": {"suggested_action": "new-candidate"},
                },
            ]
            with history_path.open("w", encoding="utf-8") as handle:
                for event in events:
                    handle.write(json.dumps(event) + "\n")

            result = consolidate_history(
                repo_root=repo_root,
                run_id="apply-broad-route",
                apply_mode="new-candidates",
            )

            broad_action = next(
                action
                for action in result["actions"]
                if action["action_type"] == "consider-new-candidate"
                and action["target"]["ref"] == "engineering"
            )
            specific_action = next(
                action
                for action in result["actions"]
                if action["action_type"] == "consider-new-candidate"
                and action["target"]["ref"] == "engineering/ui-state/desktop-app"
            )

            self.assertFalse(broad_action["apply_eligibility"]["eligible"])
            self.assertIn("at least 3 segments", broad_action["apply_eligibility"]["reason"])
            self.assertTrue(specific_action["apply_eligibility"]["eligible"])
            self.assertEqual(result["apply_summary"]["created_candidate_count"], 1)
            self.assertEqual(
                result["apply_summary"]["created_candidates"][0]["action_key"],
                specific_action["action_key"],
            )

    def test_apply_mode_requires_route_depth_three_for_auto_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            history_path = repo_root / "kb" / "history" / "events.jsonl"
            history_path.parent.mkdir(parents=True, exist_ok=True)

            route_groups = [
                (
                    "broad-1",
                    ["engineering"],
                    [
                        "Need a reusable engineering guidance card",
                        "Engineering tasks keep surfacing the same missing heuristic",
                    ],
                ),
                (
                    "broad-2",
                    ["engineering", "agent-behavior"],
                    [
                        "Need a reusable agent-behavior guidance card",
                        "Agent behavior work still lacks a shared predictive model",
                    ],
                ),
                (
                    "specific",
                    ["engineering", "agent-behavior", "unittest"],
                    [
                        "Need a reusable unittest strategy card",
                        "Unittest planning work keeps exposing the same missing guidance",
                    ],
                ),
            ]

            events: list[dict[str, object]] = []
            for group_index, (group_name, route_hint, summaries) in enumerate(route_groups, start=1):
                for observation_index, task_summary in enumerate(summaries, start=1):
                    minute = (group_index - 1) * 2 + observation_index
                    events.append(
                        {
                            "event_id": f"{group_name}-{observation_index}",
                            "event_type": "observation",
                            "created_at": f"2026-04-19T08:{minute:02d}:00+00:00",
                            "source": {"kind": "task", "agent": "worker-1"},
                            "target": {
                                "kind": "task-observation",
                                "route_hint": route_hint,
                                "task_summary": task_summary,
                            },
                            "rationale": "next=new-candidate",
                            "context": {
                                "suggested_action": "new-candidate",
                                "predictive_observation": {
                                    "scenario": f"Repeated tasks keep routing through {' / '.join(route_hint)}.",
                                    "action_taken": "Record another new-candidate observation for the same route.",
                                    "observed_result": "The route still lacks a reusable predictive card.",
                                },
                            },
                        }
                    )

            with history_path.open("w", encoding="utf-8") as handle:
                for event in events:
                    handle.write(json.dumps(event) + "\n")

            result = consolidate_history(
                repo_root=repo_root,
                run_id="apply-depth",
                apply_mode="new-candidates",
            )

            self.assertEqual(result["candidate_action_count"], 3)
            self.assertEqual(result["apply_summary"]["created_candidate_count"], 1)
            self.assertEqual(result["apply_summary"]["skipped_action_count"], 2)

            actions_by_target = {
                action["target"]["ref"]: action
                for action in result["actions"]
                if action["action_type"] == "consider-new-candidate"
            }
            self.assertFalse(actions_by_target["engineering"]["apply_eligibility"]["eligible"])
            self.assertIn(
                "at least 3 segments",
                actions_by_target["engineering"]["apply_eligibility"]["reason"],
            )
            self.assertFalse(actions_by_target["engineering/agent-behavior"]["apply_eligibility"]["eligible"])
            self.assertIn(
                "at least 3 segments",
                actions_by_target["engineering/agent-behavior"]["apply_eligibility"]["reason"],
            )
            self.assertTrue(actions_by_target["engineering/agent-behavior/unittest"]["apply_eligibility"]["eligible"])

            skipped_targets = {
                item["target"]["ref"]
                for item in result["apply_summary"]["skipped_actions"]
                if item["action_type"] == "consider-new-candidate"
            }
            self.assertEqual(
                skipped_targets,
                {"engineering", "engineering/agent-behavior"},
            )

            created_candidate = result["apply_summary"]["created_candidates"][0]
            candidate_path = repo_root / created_candidate["entry_path"]
            self.assertTrue(candidate_path.exists())

            candidate_payload = yaml.safe_load(candidate_path.read_text(encoding="utf-8"))
            self.assertEqual(
                candidate_payload["domain_path"],
                ["engineering", "agent-behavior", "unittest"],
            )
            self.assertEqual(len(list((repo_root / "kb" / "candidates").glob("*.yaml"))), 1)


if __name__ == "__main__":
    unittest.main()
