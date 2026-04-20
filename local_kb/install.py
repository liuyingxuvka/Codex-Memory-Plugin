from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from local_kb.common import utc_now_iso
from local_kb.config import (
    KB_ROOT_ENV_VAR,
    default_codex_home,
    install_state_path,
    is_repo_root,
    load_install_state,
    save_install_state,
)


GLOBAL_SKILL_NAME = "predictive-kb-preflight"
GLOBAL_SKILL_ROOT = Path("skills") / GLOBAL_SKILL_NAME
TEMPLATE_ROOT = Path("templates") / GLOBAL_SKILL_NAME


def global_skill_dir(codex_home: Path | None = None) -> Path:
    home = codex_home or default_codex_home()
    return home / GLOBAL_SKILL_ROOT


def _render_template(text: str, replacements: dict[str, str]) -> str:
    rendered = text
    for key, value in replacements.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)
    return rendered


def _read_template(repo_root: Path, relative_path: str | Path) -> str:
    path = repo_root / TEMPLATE_ROOT / relative_path
    return path.read_text(encoding="utf-8")


def install_codex_integration(repo_root: Path, codex_home: Path | None = None) -> dict[str, Any]:
    home = codex_home or default_codex_home()
    skill_dir = global_skill_dir(home)
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "agents").mkdir(parents=True, exist_ok=True)

    launcher_path = skill_dir / "kb_launch.py"
    skill_path = skill_dir / "SKILL.md"
    openai_path = skill_dir / "agents" / "openai.yaml"

    replacements = {
        "KB_ROOT": str(repo_root),
        "LAUNCHER_PATH": str(launcher_path),
        "ENV_VAR_NAME": KB_ROOT_ENV_VAR,
    }

    skill_path.write_text(
        _render_template(_read_template(repo_root, "SKILL.md.template"), replacements),
        encoding="utf-8",
    )
    launcher_path.write_text(_read_template(repo_root, "kb_launch.py"), encoding="utf-8")
    openai_path.write_text(_read_template(repo_root, Path("agents") / "openai.yaml"), encoding="utf-8")

    manifest = {
        "repo_root": str(repo_root),
        "codex_home": str(home),
        "skill_name": GLOBAL_SKILL_NAME,
        "skill_dir": str(skill_dir),
        "skill_path": str(skill_path),
        "launcher_path": str(launcher_path),
        "openai_path": str(openai_path),
        "env_var_name": KB_ROOT_ENV_VAR,
        "installed_at": utc_now_iso(),
    }
    manifest_path = save_install_state(manifest, home)
    manifest["install_state_path"] = str(manifest_path)
    return manifest


def build_installation_check(
    repo_root: Path | None = None,
    codex_home: Path | None = None,
) -> dict[str, Any]:
    home = codex_home or default_codex_home()
    skill_dir = global_skill_dir(home)
    skill_path = skill_dir / "SKILL.md"
    launcher_path = skill_dir / "kb_launch.py"
    openai_path = skill_dir / "agents" / "openai.yaml"
    manifest = load_install_state(home)
    manifest_root_raw = str(manifest.get("repo_root", "") or "").strip()
    env_value = os.environ.get(KB_ROOT_ENV_VAR, "").strip()

    issues: list[str] = []
    warnings: list[str] = []

    resolved_manifest_root = ""
    if manifest_root_raw:
        manifest_path = Path(manifest_root_raw).expanduser().resolve()
        resolved_manifest_root = str(manifest_path)
        if not is_repo_root(manifest_path):
            issues.append(f"Manifest repo root is missing or invalid: {manifest_path}")
    else:
        issues.append("Install manifest does not define repo_root.")

    requested_repo_root = ""
    if repo_root is not None:
        requested_repo_root = str(repo_root)
        if not is_repo_root(repo_root):
            issues.append(f"Requested repo root is missing required KB markers: {repo_root}")
        elif resolved_manifest_root and resolved_manifest_root != requested_repo_root:
            warnings.append(
                "Requested repo root differs from the installed manifest path. "
                "Run the installer again if this clone should become the active KB root."
            )

    if not skill_path.exists():
        issues.append(f"Global skill file is missing: {skill_path}")
    if not launcher_path.exists():
        issues.append(f"Launcher file is missing: {launcher_path}")
    if not openai_path.exists():
        issues.append(f"Global skill openai.yaml is missing: {openai_path}")
        openai_text = ""
    else:
        try:
            openai_text = openai_path.read_text(encoding="utf-8")
        except OSError as exc:
            issues.append(f"Global skill openai.yaml could not be read: {exc}")
            openai_text = ""

    if openai_text and "allow_implicit_invocation: true" not in openai_text:
        issues.append(
            "Global skill openai.yaml does not enable implicit invocation. "
            "Re-run the installer so the installed global preflight skill can trigger automatically."
        )
    if openai_text and "record a KB follow-up observation" not in openai_text:
        warnings.append(
            "Global skill default_prompt does not contain the expected KB postflight reminder. "
            "Re-run the installer to refresh the installed prompt."
        )

    return {
        "ok": not issues,
        "repo_root": requested_repo_root,
        "manifest_repo_root": resolved_manifest_root,
        "codex_home": str(home),
        "skill_dir": str(skill_dir),
        "skill_path": str(skill_path),
        "launcher_path": str(launcher_path),
        "openai_path": str(openai_path),
        "install_state_path": str(install_state_path(home)),
        "env_var_name": KB_ROOT_ENV_VAR,
        "env_var_value": env_value,
        "issues": issues,
        "warnings": warnings,
    }
