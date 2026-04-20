from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


KB_ROOT_ENV_VAR = "CODEX_PREDICTIVE_KB_ROOT"
CODEX_HOME_ENV_VAR = "CODEX_HOME"
INSTALL_STATE_SUBPATH = Path("predictive-kb") / "install.json"
REPO_MARKERS = (
    Path("AGENTS.md"),
    Path("PROJECT_SPEC.md"),
    Path("kb") / "taxonomy.yaml",
    Path(".agents") / "skills" / "local-kb-retrieve" / "SKILL.md",
)


def default_codex_home() -> Path:
    raw = os.environ.get(CODEX_HOME_ENV_VAR, "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return (Path.home() / ".codex").resolve()


def install_state_path(codex_home: Path | None = None) -> Path:
    home = codex_home or default_codex_home()
    return home / INSTALL_STATE_SUBPATH


def load_install_state(codex_home: Path | None = None) -> dict[str, Any]:
    path = install_state_path(codex_home)
    if not path.exists():
        return {}

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    return payload if isinstance(payload, dict) else {}


def save_install_state(payload: dict[str, Any], codex_home: Path | None = None) -> Path:
    path = install_state_path(codex_home)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def is_repo_root(path: Path) -> bool:
    resolved = path.expanduser().resolve()
    return all((resolved / marker).exists() for marker in REPO_MARKERS)


def normalize_repo_root(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    if not is_repo_root(resolved):
        raise FileNotFoundError(
            "The predictive KB repo root must contain AGENTS.md, PROJECT_SPEC.md, "
            "kb/taxonomy.yaml, and .agents/skills/local-kb-retrieve/SKILL.md. "
            f"Received: {resolved}"
        )
    return resolved


def discover_repo_root(start: Path | None = None) -> Path | None:
    current = (start or Path.cwd()).expanduser().resolve()
    for candidate in [current, *current.parents]:
        if is_repo_root(candidate):
            return candidate
    return None


def env_repo_root() -> Path | None:
    env_value = os.environ.get(KB_ROOT_ENV_VAR, "").strip()
    if env_value:
        try:
            return normalize_repo_root(Path(env_value))
        except FileNotFoundError:
            return None
    return None


def manifest_repo_root(codex_home: Path | None = None) -> Path | None:
    state = load_install_state(codex_home)
    manifest_root = str(state.get("repo_root", "") or "").strip()
    if manifest_root:
        try:
            return normalize_repo_root(Path(manifest_root))
        except FileNotFoundError:
            return None

    return None


def configured_repo_root(codex_home: Path | None = None) -> Path | None:
    return env_repo_root() or manifest_repo_root(codex_home)


def resolve_repo_root(
    value: str | os.PathLike[str] | None = None,
    *,
    cwd: Path | None = None,
    codex_home: Path | None = None,
) -> Path:
    raw_value = ""
    if value is not None:
        raw_value = os.fspath(value).strip()

    if raw_value and raw_value.lower() not in {"auto", "configured", "default"}:
        return Path(raw_value).expanduser().resolve()

    env_override = env_repo_root()
    if env_override is not None:
        return env_override

    discovered = discover_repo_root(cwd)
    if discovered is not None:
        return discovered

    manifest_root = manifest_repo_root(codex_home)
    if manifest_root is not None:
        return manifest_root

    raise FileNotFoundError(
        "Unable to resolve the predictive KB repo root. "
        "Pass --repo-root, set CODEX_PREDICTIVE_KB_ROOT, or run scripts/install_codex_kb.py."
    )
