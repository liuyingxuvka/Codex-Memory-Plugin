#!/usr/bin/env python3
"""Search the local predictive knowledge base."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


SCRIPT_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(SCRIPT_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_REPO_ROOT))

from local_kb.cli_output import print_json, print_text
from local_kb.search import (
    format_search_output,
    render_search_envelope,
    search_multi_source_result,
)
from local_kb.settings import load_desktop_settings, organization_sources_from_settings
from local_kb.store import resolve_repo_root


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default="auto")
    parser.add_argument("--query", required=True)
    parser.add_argument("--route-hint", dest="route_hint", default="")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    repo_root = resolve_repo_root(args.repo_root)
    settings = load_desktop_settings(repo_root)
    organization_sources = organization_sources_from_settings(settings)
    multi = search_multi_source_result(
        repo_root,
        query=args.query,
        path_hint=args.route_hint,
        top_k=args.top_k,
        organization_sources=organization_sources,
        record_receipt=True,
    )
    envelope = render_search_envelope(multi, repo_root)

    if args.json:
        print_json(envelope)
        return

    print_text(
        format_search_output(
            envelope["results"],
            path_hint=args.route_hint,
            organization_status=envelope["organization_status"],
        )
    )


if __name__ == "__main__":
    main()
