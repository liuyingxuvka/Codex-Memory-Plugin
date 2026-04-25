from __future__ import annotations

import unittest

from local_kb.github_repo_config import (
    build_branch_protection_payload,
    configure_github_org_kb_repository,
    parse_github_owner_repo,
)


class GitHubRepoConfigTests(unittest.TestCase):
    def test_parse_github_owner_repo_supports_https_and_ssh(self) -> None:
        self.assertEqual(
            parse_github_owner_repo("https://github.com/example-org/khaos-org-kb-sandbox.git"),
            ("example-org", "khaos-org-kb-sandbox"),
        )
        self.assertEqual(
            parse_github_owner_repo("git@github.com:example-org/khaos-org-kb-sandbox.git"),
            ("example-org", "khaos-org-kb-sandbox"),
        )

    def test_branch_protection_payload_requires_expected_check_context(self) -> None:
        payload = build_branch_protection_payload(["organization-kb-checks"])

        self.assertEqual(payload["required_status_checks"]["contexts"], ["organization-kb-checks"])
        self.assertTrue(payload["required_status_checks"]["strict"])
        self.assertFalse(payload["allow_force_pushes"])
        self.assertFalse(payload["allow_deletions"])

    def test_configure_github_repo_dry_run_builds_expected_api_steps(self) -> None:
        result = configure_github_org_kb_repository(
            "https://github.com/example-org/khaos-org-kb-sandbox.git",
            token="",
            dry_run=True,
        )

        self.assertTrue(result["ok"], result)
        self.assertEqual(result["owner"], "example-org")
        self.assertEqual(result["repo"], "khaos-org-kb-sandbox")
        self.assertEqual([step["name"] for step in result["steps"]], ["enable-auto-merge", "protect-default-branch"])


if __name__ == "__main__":
    unittest.main()
