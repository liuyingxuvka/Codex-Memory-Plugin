from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from local_kb.local_cycle import run_local_maintenance_cycle
from tests.current_runtime_helpers import activate_current_kb_runtime


class LocalMaintenanceCycleTests(unittest.TestCase):
    def test_sleep_and_dream_share_one_cycle_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            activate_current_kb_runtime(root)
            result = run_local_maintenance_cycle(
                root,
                run_id="local-cycle-test",
                max_observations=0,
                soft_deadline_seconds=5,
            )

            cycle = result["local_cycle"]
            cycle_path = Path(str(cycle["cycle_receipt_path"]))
            self.assertTrue(cycle_path.is_file())
            self.assertEqual(cycle["sequence"], ["sleep", "dream"])
            self.assertEqual(cycle["mode"], "fresh_cycle")
            self.assertEqual(cycle["status"], "completed")
            self.assertEqual(cycle["dream"]["status"], "completed")
            self.assertEqual(result["final_run_state"], "completed")


if __name__ == "__main__":
    unittest.main()
