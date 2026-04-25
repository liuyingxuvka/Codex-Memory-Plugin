from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from local_kb.org_sources import validate_organization_repo


TEMPLATE_ROOT = Path(__file__).resolve().parents[1] / "templates" / "github"
WORKFLOW_TARGETS = {
    "org-kb-checks.yml": ".github/workflows/org-kb-checks.yml",
    "org-kb-auto-merge.yml": ".github/workflows/org-kb-auto-merge.yml",
    "org_kb_check.py": ".github/scripts/org_kb_check.py",
}


def install_github_automation_templates(
    org_root: Path,
    *,
    template_root: Path | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    org_root = Path(org_root)
    validation = validate_organization_repo(org_root)
    if not validation.get("ok"):
        return {
            "ok": False,
            "errors": validation.get("errors") or ["invalid organization repository"],
            "installed": [],
            "skipped": [],
        }

    active_template_root = Path(template_root) if template_root is not None else TEMPLATE_ROOT
    installed: list[str] = []
    skipped: list[str] = []
    errors: list[str] = []

    for template_name, target_relative in WORKFLOW_TARGETS.items():
        source = active_template_root / template_name
        target = org_root / target_relative
        if not source.exists():
            errors.append(f"missing GitHub automation template: {source}")
            continue
        if target.exists() and not overwrite:
            skipped.append(target_relative)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        installed.append(target_relative)

    return {
        "ok": not errors,
        "errors": errors,
        "installed": installed,
        "skipped": skipped,
        "organization_id": validation.get("organization_id"),
    }
