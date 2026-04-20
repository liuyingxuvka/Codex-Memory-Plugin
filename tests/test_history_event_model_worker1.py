from __future__ import annotations

import unittest

from local_kb.feedback import build_observation
from local_kb.history import build_history_event


class HistoryEventModelTests(unittest.TestCase):
    def test_observation_uses_canonical_event_shape(self) -> None:
        event = build_observation(
            task_summary="Run a KB recall before repository work",
            route_hint="system/knowledge-library/retrieval",
            entry_ids="model-004",
            hit_quality="hit",
            outcome="Relevant prior workflow guidance was surfaced before work began",
            scenario="When repository work may depend on prior workflow conventions or stored lessons",
            action_taken="Run a lightweight KB scan before starting the main task",
            observed_result="Relevant local models were surfaced early and avoidable re-derivation dropped",
            previous_action="Start the task without any KB scan and rely on memory",
            previous_result="Relevant local constraints stayed hidden until later correction",
            revised_action="Add a lightweight KB scan before substantive work begins",
            revised_result="Relevant prior workflow guidance surfaced before the main implementation path",
            operational_use="Prefer a quick KB recall before non-trivial repository work",
            reuse_judgment="Looks reusable across repository tasks that may depend on prior lessons",
            suggested_action="update-card",
            exposed_gap=True,
            source_kind="task",
            agent_name="worker-1",
            thread_ref="thread-123",
            project_ref="job-hunter",
            workspace_root="C:/repos/job-hunter",
        )

        self.assertEqual(event["event_type"], "observation")
        self.assertEqual(set(event), {"event_id", "event_type", "created_at", "source", "target", "rationale", "context"})
        self.assertEqual(event["source"]["agent"], "worker-1")
        self.assertEqual(event["source"]["thread_ref"], "thread-123")
        self.assertEqual(event["source"]["project_ref"], "job-hunter")
        self.assertEqual(event["source"]["workspace_root"], "C:/repos/job-hunter")
        self.assertEqual(event["target"]["kind"], "task-observation")
        self.assertEqual(event["target"]["entry_ids"], ["model-004"])
        self.assertEqual(event["context"]["hit_quality"], "hit")
        self.assertTrue(event["context"]["exposed_gap"])
        self.assertEqual(
            event["context"]["predictive_observation"]["scenario"],
            "When repository work may depend on prior workflow conventions or stored lessons",
        )
        self.assertEqual(
            event["context"]["predictive_observation"]["action_taken"],
            "Run a lightweight KB scan before starting the main task",
        )
        self.assertEqual(
            event["context"]["predictive_observation"]["observed_result"],
            "Relevant local models were surfaced early and avoidable re-derivation dropped",
        )
        self.assertEqual(
            event["context"]["predictive_observation"]["contrastive_evidence"]["previous_action"],
            "Start the task without any KB scan and rely on memory",
        )
        self.assertEqual(
            event["context"]["predictive_observation"]["contrastive_evidence"]["previous_result"],
            "Relevant local constraints stayed hidden until later correction",
        )
        self.assertEqual(
            event["context"]["predictive_observation"]["contrastive_evidence"]["revised_action"],
            "Add a lightweight KB scan before substantive work begins",
        )
        self.assertEqual(
            event["context"]["predictive_observation"]["contrastive_evidence"]["revised_result"],
            "Relevant prior workflow guidance surfaced before the main implementation path",
        )
        self.assertIn("next=update-card", event["rationale"])

    def test_base_builder_preserves_empty_rationale_and_context_shape(self) -> None:
        event = build_history_event(
            "candidate-created",
            source={"kind": "manual-entry", "agent": "kb-capture"},
            target={"kind": "candidate-entry", "entry_id": "cand-1"},
        )

        self.assertEqual(event["rationale"], "")
        self.assertEqual(event["context"], {})
        self.assertEqual(event["target"]["entry_id"], "cand-1")


if __name__ == "__main__":
    unittest.main()
