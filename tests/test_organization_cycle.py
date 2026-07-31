from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from local_kb.org_cycle import run_organization_cycle
from local_kb.settings import ORGANIZATION_MODE, save_desktop_settings
from tests.org_helpers import activate_current_kb_runtime, connect_profile_to_org, init_git_repo, write_valid_org_repo


class OrganizationCycleTests(unittest.TestCase):
    def test_cycle_serializes_maintenance_contribution_and_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            org = root / "org"
            machine = root / "machine"
            write_valid_org_repo(org, include_sandbox_cards=True)
            init_git_repo(org)
            connection, _sources = connect_profile_to_org(machine, org)
            settings = dict(connection["settings"])
            settings["organization_maintenance_requested"] = True
            save_desktop_settings(machine, {"mode": ORGANIZATION_MODE, "organization": settings})
            activate_current_kb_runtime(machine)

            result = run_organization_cycle(machine, run_id="organization-cycle-test", push=False)

        self.assertTrue(result["ok"], result)
        self.assertEqual(result["status"], "completed")
        self.assertTrue(result["maintenance"]["ok"])
        self.assertTrue(result["contribution"]["ok"])
        self.assertTrue(result["snapshot"]["ok"])
        self.assertTrue(result["postflight_recorded"])


if __name__ == "__main__":
    unittest.main()
