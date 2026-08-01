from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from local_kb.org_github_automation import install_github_automation_templates
from local_kb.store import write_yaml_file
from tests.org_helpers import write_valid_org_repo


class OrganizationGitHubAutomationTests(unittest.TestCase):
    def _write_org_repo(self, root: Path) -> None:
        write_valid_org_repo(root, include_sandbox_cards=False)

    def test_installs_github_workflow_templates_into_valid_org_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_org_repo(root)

            result = install_github_automation_templates(root)
            checks = (root / ".github" / "workflows" / "org-kb-checks.yml").read_text(encoding="utf-8")
            auto_merge = (root / ".github" / "workflows" / "org-kb-auto-merge.yml").read_text(encoding="utf-8")
            script = (root / ".github" / "scripts" / "org_kb_check.py").read_text(encoding="utf-8")

        self.assertTrue(result["ok"], result)
        self.assertEqual(
            sorted(result["installed"]),
            [
                ".github/scripts/org_kb_check.py",
                ".github/workflows/org-kb-auto-merge.yml",
                ".github/workflows/org-kb-checks.yml",
            ],
        )
        self.assertIn(".github/scripts/org_kb_check.py", checks)
        self.assertIn("org-kb:auto-merge", auto_merge)
        self.assertIn("SKILL_REVIEW_STATES", script)
        self.assertIn("CURRENT_SOURCE_SCHEMA_VERSION = 2", script)
        self.assertIn('BUNDLE_ROOT = "kb/logicguard/bundles"', script)
        self.assertIn('"text_digest_policy": "utf8-lf-v1"', script)

    def test_does_not_overwrite_existing_workflow_without_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_org_repo(root)
            target = root / ".github" / "workflows" / "org-kb-checks.yml"
            target.parent.mkdir(parents=True)
            target.write_text("custom\n", encoding="utf-8")

            result = install_github_automation_templates(root)
            text = target.read_text(encoding="utf-8")

        self.assertTrue(result["ok"], result)
        self.assertIn(".github/workflows/org-kb-checks.yml", result["skipped"])
        self.assertEqual(text, "custom\n")

    def test_installed_checker_rejects_obsolete_organization_roots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_org_repo(root)
            install_github_automation_templates(root)
            write_yaml_file(
                root / "kb" / "trusted" / "obsolete.yaml",
                {"id": "obsolete", "status": "trusted"},
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    str(root / ".github" / "scripts" / "org_kb_check.py"),
                    "--org-root",
                    str(root),
                ],
                cwd=root,
                check=False,
                capture_output=True,
                text=True,
            )
            payload = json.loads(completed.stdout)

        self.assertEqual(completed.returncode, 2)
        self.assertFalse(payload["ok"])
        self.assertTrue(
            any("obsolete organization roots" in item for item in payload["errors"]),
            payload,
        )

    def test_installed_checker_accepts_complete_schema2_maintenance_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_org_repo(root)
            install_github_automation_templates(root)
            audit = root / "maintenance" / "cleanup_audit.jsonl"
            audit.parent.mkdir(parents=True)
            audit.write_text('{"status":"applied"}\n', encoding="utf-8")
            catalog = json.loads(
                (root / "kb" / "organization_catalog.json").read_text(encoding="utf-8")
            )
            row = catalog["cards"][0]
            changed = [
                row["source_path"],
                row["model_path"],
                row["mesh_path"],
                row["projection_path"],
                row["bundle_path"],
                "kb/organization_catalog.json",
                "khaos_org_kb.yaml",
                "maintenance/cleanup_audit.jsonl",
            ]
            changed_file = root / "changed-files.txt"
            changed_file.write_text("\n".join(changed) + "\n", encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    str(root / ".github" / "scripts" / "org_kb_check.py"),
                    "--org-root",
                    str(root),
                    "--changed-files-file",
                    str(changed_file),
                    "--enforce-low-risk",
                    "--allow-maintenance-main",
                ],
                cwd=root,
                check=False,
                capture_output=True,
                text=True,
            )
            payload = json.loads(completed.stdout)

        self.assertEqual(completed.returncode, 0, payload)
        self.assertTrue(payload["ok"], payload)
        self.assertTrue(payload["auto_merge_eligible"], payload)

    def test_installed_checker_accepts_catalog_digest_after_lf_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_org_repo(root)
            install_github_automation_templates(root)
            catalog = json.loads(
                (root / "kb" / "organization_catalog.json").read_text(encoding="utf-8")
            )
            source = root / catalog["cards"][0]["source_path"]
            source.write_bytes(source.read_bytes().replace(b"\r\n", b"\n"))

            completed = subprocess.run(
                [
                    sys.executable,
                    str(root / ".github" / "scripts" / "org_kb_check.py"),
                    "--org-root",
                    str(root),
                ],
                cwd=root,
                check=False,
                capture_output=True,
                text=True,
            )
            payload = json.loads(completed.stdout)

        self.assertEqual(completed.returncode, 0, payload)
        self.assertTrue(payload["ok"], payload)

    def test_installed_checker_rejects_missing_logicguard_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_org_repo(root)
            install_github_automation_templates(root)
            catalog = json.loads(
                (root / "kb" / "organization_catalog.json").read_text(encoding="utf-8")
            )
            (root / catalog["cards"][0]["bundle_path"]).unlink()

            completed = subprocess.run(
                [
                    sys.executable,
                    str(root / ".github" / "scripts" / "org_kb_check.py"),
                    "--org-root",
                    str(root),
                ],
                cwd=root,
                check=False,
                capture_output=True,
                text=True,
            )
            payload = json.loads(completed.stdout)

        self.assertEqual(completed.returncode, 2)
        self.assertFalse(payload["ok"])
        self.assertTrue(
            any("missing or unsafe bundle_path" in item for item in payload["errors"]),
            payload,
        )


if __name__ == "__main__":
    unittest.main()
