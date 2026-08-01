from __future__ import annotations

from datetime import datetime, timezone
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from local_kb.org_migration import (
    ORG_BUILDER_MIGRATION_ID,
    RETIRED_ORG_SOURCE_BUILDER_V1,
    _copy_backup,
    _native_filesystem_path,
    _snapshot_root,
    migrate_organization_repo_to_current,
)
from local_kb.org_source_contract import ORG_SOURCE_BUILDER, load_current_catalog, materialize_current_source
from local_kb.org_sources import (
    _run_git,
    clone_or_fetch_organization_repo,
    connect_organization_source,
    default_org_mirror_path,
    guess_organization_source_id,
    validate_organization_repo,
)
from local_kb.store import load_organization_entries, load_yaml_file, write_yaml_file
from tests.org_helpers import base_card, write_legacy_org_repo, write_valid_org_repo


class OrganizationSourceTests(unittest.TestCase):
    def _write_valid_org_repo(self, root: Path) -> None:
        materialize_current_source(
            root,
            organization_id="sandbox",
            cards=[
                ("kb/main/model.yaml", base_card("model", "Model", "Use model.")),
                ("kb/main/candidate.yaml", base_card("candidate", "Candidate", "Use candidate.", status="candidate")),
            ],
        )
        write_yaml_file(root / "skills" / "registry.yaml", {"skills": [{"id": "org.demo", "status": "approved", "version": "1", "content_hash": "sha256:" + "1" * 64}]})

    def test_validate_accepts_only_complete_schema2_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_valid_org_repo(root)
            result = validate_organization_repo(root)

        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(result["schema_version"], 2)
        self.assertEqual(result["main_count"], 2)
        self.assertEqual(result["main_active_count"], 2)
        self.assertEqual(result["trusted_count"], 1)
        self.assertEqual(result["candidate_count"], 1)
        self.assertTrue(result["source_generation_id"])

    def test_source_digest_is_portable_across_windows_and_linux_newlines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_valid_org_repo(root)
            catalog = load_current_catalog(root)
            source = root / catalog["cards"][0]["source_path"]
            source.write_bytes(source.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
            windows = validate_organization_repo(root)
            source.write_bytes(source.read_bytes().replace(b"\r\n", b"\n"))
            linux = validate_organization_repo(root)

        self.assertEqual(ORG_SOURCE_BUILDER["text_digest_policy"], "utf8-lf-v1")
        self.assertTrue(windows["ok"], windows["errors"])
        self.assertTrue(linux["ok"], linux["errors"])

    def test_normal_runtime_rejects_raw_schema1_and_uncataloged_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_legacy_org_repo(root)
            legacy = validate_organization_repo(root)
            write_valid_org_repo(root / "current")
            write_yaml_file(root / "current" / "kb" / "main" / "extra.yaml", base_card("extra", "Extra", "Use."))
            uncataloged = validate_organization_repo(root / "current")

        self.assertFalse(legacy["ok"])
        self.assertTrue(any("schema_version" in item or "obsolete" in item for item in legacy["errors"]))
        self.assertFalse(uncataloged["ok"])
        self.assertTrue(any("uncataloged" in item for item in uncataloged["errors"]))

    def test_download_surface_reads_main_and_excludes_imports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            materialize_current_source(root, organization_id="sandbox", cards=[("kb/main/main.yaml", base_card("main", "Main", "Use."))])
            write_yaml_file(root / "kb" / "imports" / "alice" / "import.yaml", base_card("import", "Import", "Review.", status="candidate"))
            validation = validate_organization_repo(root)
            entries = load_organization_entries(root, "sandbox")

        self.assertTrue(validation["ok"], validation["errors"])
        self.assertEqual(validation["imports_count"], 1)
        self.assertEqual([entry.data["id"] for entry in entries], ["main"])

    def test_migration_builds_current_bundles_and_removes_legacy_authority(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_legacy_org_repo(root)
            result = migrate_organization_repo_to_current(root)
            validation = validate_organization_repo(root)
            obsolete_missing = not (root / "kb" / "trusted").exists() and not (root / "kb" / "candidates").exists()
            catalog_exists = (root / "kb" / "organization_catalog.json").is_file()
            no_legacy_metadata = all("legacy_upgrade" not in load_yaml_file(root / row["source_path"]) for row in load_current_catalog(root)["cards"])

        self.assertTrue(result["ok"], result)
        self.assertTrue(validation["ok"], validation["errors"])
        self.assertTrue(obsolete_missing)
        self.assertTrue(catalog_exists)
        self.assertTrue(no_legacy_metadata)

    def test_migration_directly_rebuilds_exact_retired_builder_v1(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch(
                "local_kb.org_source_contract.ORG_SOURCE_BUILDER",
                RETIRED_ORG_SOURCE_BUILDER_V1,
            ):
                materialize_current_source(
                    root,
                    organization_id="sandbox",
                    cards=[("kb/main/model.yaml", base_card("model", "Model", "Use model."))],
                )
            before = validate_organization_repo(root)

            result = migrate_organization_repo_to_current(root)
            after = validate_organization_repo(root)
            catalog = load_current_catalog(root)

        self.assertFalse(before["ok"])
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["migration_id"], ORG_BUILDER_MIGRATION_ID)
        self.assertTrue(after["ok"], after["errors"])
        self.assertEqual(catalog["builder_identity"], ORG_SOURCE_BUILDER)

    def test_migration_freezes_yaml_timestamps_into_portable_bundle_scalars(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_legacy_org_repo(root)
            legacy_path = root / "kb" / "trusted" / "overlap-scan.yaml"
            legacy_card = load_yaml_file(legacy_path)
            legacy_card["updated_at"] = datetime(2026, 7, 31, 12, 0, tzinfo=timezone.utc)
            write_yaml_file(legacy_path, legacy_card)

            result = migrate_organization_repo_to_current(root)
            validation = validate_organization_repo(root)
            migrated = load_yaml_file(root / "kb" / "main" / "trusted" / "overlap-scan.yaml")

        self.assertTrue(result["ok"], result)
        self.assertTrue(validation["ok"], validation["errors"])
        self.assertIsInstance(migrated["updated_at"], str)

    def test_migration_duplicate_ids_are_deterministic_and_exact_duplicates_retire(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_legacy_org_repo(root, include_sandbox_cards=False)
            (root / "kb" / "trusted" / "seed.yaml").unlink()
            first = base_card("same", "Same", "Use same.")
            second = base_card("same", "Different", "Use differently.", status="candidate")
            write_yaml_file(root / "kb" / "trusted" / "same.yaml", first)
            write_yaml_file(root / "kb" / "candidates" / "different.yaml", second)
            write_yaml_file(root / "kb" / "candidates" / "exact.yaml", first)
            result = migrate_organization_repo_to_current(root)
            catalog = load_current_catalog(root)

        self.assertTrue(result["ok"], result)
        ids = [row["entry_id"] for row in catalog["cards"]]
        self.assertIn("same", ids)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(any(item.startswith("same--dup-") for item in ids))
        self.assertTrue(any(item["disposition"] == "retired_exact_duplicate" for item in catalog["tombstones"]))

    def test_migration_rolls_back_owned_tree_when_current_validation_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_legacy_org_repo(root)
            with patch("local_kb.org_sources.validate_organization_repo", return_value={"ok": False, "errors": ["forced"]}):
                result = migrate_organization_repo_to_current(root)
            restored = load_yaml_file(root / "khaos_org_kb.yaml")
            trusted_restored = (root / "kb" / "trusted").exists()

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "rolled_back")
        self.assertEqual(restored["schema_version"], 1)
        self.assertTrue(trusted_restored)

    def test_migration_backup_supports_windows_extended_length_card_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            try:
                relative_parent = Path("kb") / "main" / "system" / "knowledge-library" / "maintenance"
                while len(str(root / relative_parent / "long-card.yaml")) < 220:
                    relative_parent /= "nested-card-domain"
                source = root / relative_parent / "long-card.yaml"
                source.parent.mkdir(parents=True)
                source.write_text("id: long-card\n", encoding="utf-8")
                (root / "khaos_org_kb.yaml").write_text("schema_version: 1\n", encoding="utf-8")
                backup = _snapshot_root(root, "20260731T233518+0000-8a052469")
                target = backup / source.relative_to(root)

                self.assertLess(len(str(source)), 260)
                self.assertGreater(len(str(target)), 260)
                _copy_backup(root, backup)

                self.assertEqual(
                    _native_filesystem_path(target).read_text(encoding="utf-8"),
                    "id: long-card\n",
                )
            finally:
                if root.exists():
                    shutil.rmtree(_native_filesystem_path(root))

    def test_clone_and_connect_support_current_local_git_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            mirror = root / "mirror"
            profile = root / "profile"
            self._write_valid_org_repo(source)
            self.assertEqual(0, _run_git(["init"], cwd=source).returncode)
            self.assertEqual(0, _run_git(["add", "."], cwd=source).returncode)
            self.assertEqual(0, _run_git(["-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "seed"], cwd=source).returncode)
            clone = clone_or_fetch_organization_repo(str(source), mirror)
            connected = connect_organization_source(profile, str(source))
            mirror_valid = validate_organization_repo(mirror)["ok"]

        self.assertTrue(clone["ok"], clone)
        self.assertTrue(mirror_valid)
        self.assertTrue(connected["ok"], connected)
        self.assertEqual(connected["settings"]["organization_id"], "sandbox")

    def test_paths_and_missing_manifest(self) -> None:
        self.assertEqual(default_org_mirror_path(Path("repo"), "acme/org kb").as_posix(), "repo/.local/organization_sources/acme-org-kb")
        self.assertEqual(guess_organization_source_id("https://github.com/acme/khaos-org-kb-sandbox.git"), "khaos-org-kb-sandbox")
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(validate_organization_repo(Path(tmp))["ok"])


if __name__ == "__main__":
    unittest.main()
