from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _bootstrap_repo_imports() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


_bootstrap_repo_imports()

from local_kb.cli_output import print_json  # noqa: E402
from local_kb.config import resolve_repo_root  # noqa: E402
from local_kb.org_simulation import run_organization_rehearsal  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Rehearse organization maintenance AI behavior in a disposable source without publishing."
    )
    parser.add_argument("--repo-root", default="auto")
    parser.add_argument("--run-id", default="organization-rehearsal")
    parser.add_argument("--json", action="store_true", help="Emit the canonical JSON envelope (the default).")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = run_organization_rehearsal(
        resolve_repo_root(args.repo_root),
        run_id=args.run_id,
    )
    print_json(result)
    if result.get("ok") is not True:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
