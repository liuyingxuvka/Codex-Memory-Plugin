from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from local_kb.org_automation import run_organization_contribution, run_organization_maintenance
from local_kb.settings import ORGANIZATION_MODE, save_desktop_settings
from local_kb.store import write_yaml_file


class OrganizationAutomationTests(unittest.TestCase):
    def _write_org_repo(self, root: Path) -> None:
        write_yaml_file(
            root / "khaos_org_kb.yaml",
            {
                "kind": "khaos-organization-kb",
                "schema_version": 1,
                "organization_id": "sandbox",
                "kb": {
                    "trusted_path": "kb/trusted",
                    "candidates_path": "kb/candidates",
                    "imports_path": "kb/imports",
                },
                "skills": {
                    "registry_path": "skills/registry.yaml",
                    "candidates_path": "skills/candidates",
                },
            },
        )
        write_yaml_file(root / "kb" / "trusted" / "trusted.yaml", {"id": "trusted", "status": "trusted"})
        write_yaml_file(root / "kb" / "candidates" / "candidate.yaml", {"id": "candidate", "status": "candidate"})
        (root / "kb" / "imports").mkdir(parents=True)
        write_yaml_file(root / "skills" / "registry.yaml", {"skills": [{"id": "org.demo", "status": "approved"}]})
        (root / "skills" / "candidates").mkdir(parents=True)

    def _write_local_card(self, root: Path, entry_id: str = "share-model") -> None:
        write_yaml_file(
            root / "kb" / "public" / f"{entry_id}.yaml",
            {
                "id": entry_id,
                "title": "Shareable model",
                "type": "model",
                "scope": "public",
                "status": "trusted",
                "confidence": 0.82,
                "domain_path": ["system", "knowledge-library", "organization"],
                "tags": ["organization", "sharing"],
                "trigger_keywords": ["organization", "outbox"],
                "if": {"notes": "A reusable organization KB contribution is useful."},
                "action": {"description": "Export it through the organization outbox."},
                "predict": {"expected_result": "Other machines can reuse the model."},
                "use": {"guidance": "Keep private details out of the shared proposal."},
            },
        )

    def _save_organization_settings(
        self,
        repo_root: Path,
        org_root: Path,
        *,
        maintenance_requested: bool = False,
    ) -> None:
        save_desktop_settings(
            repo_root,
            {
                "mode": ORGANIZATION_MODE,
                "organization": {
                    "repo_url": str(org_root),
                    "local_mirror_path": str(org_root),
                    "organization_id": "sandbox",
                    "validated": True,
                    "validation_status": "valid",
                    "organization_maintenance_requested": maintenance_requested,
                },
            },
        )

    def test_contribution_noops_without_valid_organization_settings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_organization_contribution(Path(tmp), record_postflight=False)

        self.assertTrue(result["ok"], result)
        self.assertTrue(result["skipped"], result)
        self.assertFalse(result["settings_gate"]["available"])
        self.assertEqual(result["preflight"], {})
        self.assertFalse(result["postflight_recorded"])

    def test_automation_scripts_noop_successfully_without_settings(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            local_root = Path(tmp)
            outbox = subprocess.run(
                [
                    sys.executable,
                    str(repo_root / "scripts" / "kb_org_outbox.py"),
                    "--repo-root",
                    str(local_root),
                    "--automation",
                    "--no-postflight",
                ],
                cwd=repo_root,
                check=False,
                capture_output=True,
                text=True,
            )
            maintainer = subprocess.run(
                [
                    sys.executable,
                    str(repo_root / "scripts" / "kb_org_maintainer.py"),
                    "--repo-root",
                    str(local_root),
                    "--automation",
                    "--no-postflight",
                ],
                cwd=repo_root,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(outbox.returncode, 0, outbox.stderr)
        self.assertEqual(maintainer.returncode, 0, maintainer.stderr)
        self.assertTrue(json.loads(outbox.stdout)["skipped"])
        self.assertTrue(json.loads(maintainer.stdout)["skipped"])

    def test_contribution_dry_run_uses_valid_settings_and_hash_gated_outbox(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            org = root / "org"
            repo = root / "repo"
            self._write_org_repo(org)
            self._write_local_card(repo)
            self._save_organization_settings(repo, org)

            result = run_organization_contribution(repo, dry_run=True, record_postflight=False)

        self.assertTrue(result["ok"], result)
        self.assertFalse(result["skipped"], result)
        self.assertTrue(result["settings_gate"]["available"])
        self.assertEqual(result["organization_id"], "sandbox")
        self.assertEqual(result["outbox"]["created_count"], 1)
        self.assertEqual(result["outbox"]["skipped_count"], 0)
        self.assertFalse((repo / "kb" / "outbox").exists())
        self.assertFalse(result["postflight_recorded"])

    def test_maintenance_noops_until_participation_is_requested(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            org = root / "org"
            repo = root / "repo"
            self._write_org_repo(org)
            self._save_organization_settings(repo, org, maintenance_requested=False)

            result = run_organization_maintenance(repo, record_postflight=False)

        self.assertTrue(result["ok"], result)
        self.assertTrue(result["skipped"], result)
        self.assertFalse(result["settings_gate"]["available"])
        self.assertFalse(result["participation"]["available"])

    def test_maintenance_runs_when_participation_is_requested(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            org = root / "org"
            repo = root / "repo"
            self._write_org_repo(org)
            self._save_organization_settings(repo, org, maintenance_requested=True)
            skill_dir = repo / ".agents" / "skills" / "organization-review"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "---\nname: organization-review\ndescription: Review organization KB proposals.\n---\n",
                encoding="utf-8",
            )

            result = run_organization_maintenance(repo, record_postflight=False)

        self.assertTrue(result["ok"], result)
        self.assertFalse(result["skipped"], result)
        self.assertTrue(result["settings_gate"]["available"])
        self.assertTrue(result["participation"]["available"])
        self.assertEqual(result["organization_id"], "sandbox")
        self.assertEqual(result["report"]["candidate_count"], 1)
        self.assertTrue(result["report"]["organization_review_skill"]["installed"])
        self.assertIn("review-organization-candidates", result["report"]["recommendations"])
        self.assertFalse(result["postflight_recorded"])


if __name__ == "__main__":
    unittest.main()
