from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from local_kb.card_ids import installation_identity_path, installation_short_label, new_card_id


class CardIdTests(unittest.TestCase):
    def test_new_card_id_uses_time_author_or_installation_and_random_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)

            self.assertEqual(
                new_card_id(
                    repo_root,
                    prefix="cand",
                    generated_at="2026-04-24T01:02:03+00:00",
                    author_hint="Alice Smith",
                    random_code="abc123",
                ),
                "cand-20260424T010203Z-alice-smith-abc123",
            )
            self.assertFalse(installation_identity_path(repo_root).exists())

            install_short = installation_short_label(repo_root)
            installation_id = json.loads(installation_identity_path(repo_root).read_text(encoding="utf-8"))[
                "local_installation_id"
            ]
            self.assertTrue(install_short.startswith("inst"))
            self.assertEqual(install_short, "inst" + installation_id.replace("-", "")[:8])

            generated = new_card_id(
                repo_root,
                prefix="card",
                generated_at="2026-04-24T01:02:03Z",
                random_code="def456",
            )
            self.assertEqual(generated, f"card-20260424T010203Z-{install_short}-def456")


if __name__ == "__main__":
    unittest.main()
