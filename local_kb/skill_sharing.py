from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from local_kb.card_ids import installation_short_label, new_card_id
from local_kb.common import utc_now_iso
from local_kb.store import write_yaml_file
from local_kb.store import yaml


SKILL_REVIEW_STATES = {"candidate", "approved", "rejected"}
LOCAL_SKILL_BUNDLE_STATE_ROOT = Path(".local") / "skill_bundles" / "local"
IMPORTED_SKILL_BUNDLE_ROOT = Path(".local") / "organization_skills"
SKILL_BUNDLE_UPDATE_POLICY = "original_author_only"
DEPENDENCY_PASSTHROUGH_KEYS = {
    "bundle_id",
    "bundle_path",
    "bundle_metadata_path",
    "content_hash",
    "local_name",
    "name",
    "original_author",
    "readonly_when_imported",
    "sharing_mode",
    "status",
    "update_policy",
    "version_time",
}


def _dependency_id(value: Any) -> str:
    if isinstance(value, dict):
        for key in ("id", "name", "skill", "ref"):
            text = str(value.get(key) or "").strip()
            if text:
                return text
        return ""
    return str(value or "").strip()


def _collect_dependency_items(value: Any, requirement: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if isinstance(value, dict):
        for key, nested_requirement in (("required", "required"), ("recommended", "recommended"), ("optional", "optional")):
            if key in value:
                items.extend(_collect_dependency_items(value.get(key), nested_requirement))
        direct_id = _dependency_id(value)
        if direct_id:
            item: dict[str, Any] = {"id": direct_id, "requirement": str(value.get("requirement") or requirement)}
            for key in DEPENDENCY_PASSTHROUGH_KEYS:
                if key in value and value.get(key) is not None:
                    item[key] = value.get(key)
            items.append(item)
        return items
    if isinstance(value, list):
        for item in value:
            items.extend(_collect_dependency_items(item, requirement))
        return items
    direct_id = _dependency_id(value)
    if direct_id:
        items.append({"id": direct_id, "requirement": requirement})
    return items


def _entry_dependency_items(entry_data: dict[str, Any]) -> list[dict[str, Any]]:
    collected: list[dict[str, Any]] = []
    for key, requirement in (
        ("required_skills", "required"),
        ("recommended_skills", "recommended"),
        ("skill_dependencies", "required"),
        ("skills", "required"),
    ):
        if key in entry_data:
            collected.extend(_collect_dependency_items(entry_data.get(key), requirement))
    proposal = entry_data.get("organization_proposal") if isinstance(entry_data.get("organization_proposal"), dict) else {}
    if "skill_dependencies" in proposal:
        collected.extend(_collect_dependency_items(proposal.get("skill_dependencies"), "required"))
    return collected


def _has_value(value: Any) -> bool:
    return value is not None and value != ""


def extract_skill_dependencies(entry_data: dict[str, Any]) -> list[dict[str, Any]]:
    collected = _entry_dependency_items(entry_data)

    by_id: dict[str, dict[str, Any]] = {}
    rank = {"required": 0, "recommended": 1, "optional": 2}
    for item in collected:
        skill_id = str(item["id"]).strip()
        if not skill_id:
            continue
        requirement = item.get("requirement") or "required"
        candidate = {key: value for key, value in item.items() if _has_value(value)}
        candidate["id"] = skill_id
        candidate["requirement"] = requirement
        existing = by_id.get(skill_id)
        if existing is None or rank.get(requirement, 9) < rank.get(existing.get("requirement", ""), 9):
            merged = dict(existing or {})
            merged.update(candidate)
            by_id[skill_id] = merged
        else:
            for key, value in candidate.items():
                existing.setdefault(key, value)
    return list(by_id.values())


def extract_card_bound_skill_bundle_dependencies(entry_data: dict[str, Any]) -> list[dict[str, Any]]:
    dependencies: list[dict[str, Any]] = []
    for item in _entry_dependency_items(entry_data):
        if not isinstance(item, dict):
            continue
        sharing_mode = str(item.get("sharing_mode") or "").strip()
        bundle_id = str(item.get("bundle_id") or "").strip()
        bundle_path = str(item.get("bundle_path") or "").strip()
        if sharing_mode == "card-bound-bundle" or (bundle_id and bundle_path):
            dependencies.append(item)
    return dependencies


def _skill_search_roots(repo_root: Path, codex_home: Path | None = None) -> list[Path]:
    roots = [repo_root / ".agents" / "skills"]
    if codex_home is None:
        env_home = os.environ.get("CODEX_HOME", "").strip()
        codex_home = Path(env_home) if env_home else Path.home() / ".codex"
    roots.append(codex_home / "skills")
    return roots


def _read_skill_frontmatter(skill_path: Path) -> dict[str, Any]:
    text = skill_path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    payload = yaml.safe_load(parts[1]) or {}
    return payload if isinstance(payload, dict) else {}


def _safe_segment(value: Any, *, fallback: str = "item") -> str:
    safe = "".join(char if char.isalnum() or char in {"-", "_", "."} else "-" for char in str(value or ""))
    safe = safe.strip(".-")
    return safe[:120] or fallback


def _safe_hash_segment(value: Any) -> str:
    text = str(value or "").strip()
    if text.startswith("sha256:"):
        text = "sha256-" + text.removeprefix("sha256:")
    return _safe_segment(text, fallback="hash")


def _compact_bundle_version_segment(version_time: Any, content_hash: Any) -> str:
    time_text = "".join(char for char in str(version_time or "") if char.isalnum())[:16] or "version"
    digest = hashlib.sha256(f"{version_time}|{content_hash}".encode("utf-8")).hexdigest()[:12]
    return _safe_segment(f"{time_text}-{digest}", fallback="version")


def _parse_bundle_version_time(value: Any) -> str:
    text = str(value or "").strip()
    return text or utc_now_iso()


def _latest_version(versions: list[dict[str, Any]]) -> dict[str, Any]:
    if not versions:
        return {}
    return sorted(
        versions,
        key=lambda item: (
            _parse_bundle_version_time(item.get("version_time") or item.get("exported_at")),
            str(item.get("content_hash") or ""),
        ),
    )[-1]


def local_skill_bundle_state_path(repo_root: Path, local_skill_ref: str) -> Path:
    return Path(repo_root) / LOCAL_SKILL_BUNDLE_STATE_ROOT / f"{_safe_segment(local_skill_ref, fallback='skill')}.yaml"


def imported_skill_bundle_root(repo_root: Path) -> Path:
    return Path(repo_root) / IMPORTED_SKILL_BUNDLE_ROOT


def imported_skill_bundle_dir(repo_root: Path, bundle_id: str) -> Path:
    return imported_skill_bundle_root(repo_root) / _safe_segment(bundle_id, fallback="bundle")


def _read_yaml_mapping(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return payload if isinstance(payload, dict) else {}


def local_contributor_identity(repo_root: Path) -> str:
    return installation_short_label(repo_root)


def load_or_create_local_skill_bundle(
    repo_root: Path,
    local_skill_ref: str,
    *,
    content_hash: str = "",
    version_time: str = "",
    persist: bool = True,
) -> dict[str, Any]:
    """Return stable local card-bound Skill bundle metadata for a local Skill.

    The bundle id is a lineage identifier. Content hashes identify exact
    versions under that lineage.
    """

    repo_root = Path(repo_root)
    local_skill_ref = str(local_skill_ref or "").strip()
    path = local_skill_bundle_state_path(repo_root, local_skill_ref)
    metadata = _read_yaml_mapping(path)
    now = version_time or utc_now_iso()
    if not metadata.get("bundle_id"):
        metadata["bundle_id"] = new_card_id(
            repo_root,
            prefix="skill-bundle",
            generated_at=now,
            author_hint=local_contributor_identity(repo_root),
        )
    metadata["local_name"] = str(metadata.get("local_name") or local_skill_ref).strip()
    metadata["original_author"] = str(metadata.get("original_author") or local_contributor_identity(repo_root)).strip()
    metadata["created_at"] = str(metadata.get("created_at") or now)
    metadata["readonly_when_imported"] = True
    metadata["update_policy"] = SKILL_BUNDLE_UPDATE_POLICY
    versions = metadata.get("versions") if isinstance(metadata.get("versions"), list) else []
    normalized_versions = [item for item in versions if isinstance(item, dict)]
    if content_hash:
        existing = next(
            (item for item in normalized_versions if str(item.get("content_hash") or "") == content_hash),
            None,
        )
        if existing is None:
            normalized_versions.append(
                {
                    "content_hash": content_hash,
                    "version_time": now,
                    "source": "local-author",
                }
            )
        else:
            existing["version_time"] = str(existing.get("version_time") or now)
    metadata["versions"] = sorted(
        normalized_versions,
        key=lambda item: (
            _parse_bundle_version_time(item.get("version_time")),
            str(item.get("content_hash") or ""),
        ),
    )
    metadata["latest_version"] = _latest_version(metadata["versions"])
    if persist:
        write_yaml_file(path, metadata)
    return metadata


def find_local_skill_metadata(repo_root: Path, skill_id: str, codex_home: Path | None = None) -> dict[str, Any] | None:
    for root in _skill_search_roots(repo_root, codex_home=codex_home):
        skill_path = root / skill_id / "SKILL.md"
        if not skill_path.exists():
            continue
        metadata = _read_skill_frontmatter(skill_path)
        skill_dir = skill_path.parent
        return {
            "id": skill_id,
            "status": "installed",
            "name": str(metadata.get("name") or skill_id),
            "description": str(metadata.get("description") or ""),
            "local_path_hint": str(skill_path.relative_to(repo_root)) if skill_path.is_relative_to(repo_root) else "",
            "_source_dir": str(skill_dir),
        }
    return None


def build_card_skill_dependency_manifest(
    repo_root: Path,
    entry_data: dict[str, Any],
    *,
    codex_home: Path | None = None,
    persist_bundle_metadata: bool = True,
) -> list[dict[str, Any]]:
    manifest: list[dict[str, Any]] = []
    for dependency in extract_skill_dependencies(entry_data):
        skill_id = dependency["id"]
        metadata = find_local_skill_metadata(repo_root, skill_id, codex_home=codex_home)
        if metadata is None:
            metadata = {
                "id": skill_id,
                "status": "missing",
                "name": skill_id,
                "description": "",
                "local_path_hint": "",
            }
            manifest.append(
                {
                    **metadata,
                    "requirement": dependency.get("requirement") or "required",
                    "sharing_mode": "missing",
                }
            )
            continue

        source_dir = Path(str(metadata.get("_source_dir") or ""))
        content_hash = skill_directory_content_hash(source_dir)
        bundle_metadata = load_or_create_local_skill_bundle(
            repo_root,
            skill_id,
            content_hash=content_hash,
            persist=persist_bundle_metadata,
        )
        latest_version = bundle_metadata.get("latest_version") if isinstance(bundle_metadata.get("latest_version"), dict) else {}
        version_time = str(latest_version.get("version_time") or utc_now_iso())
        manifest.append(
            {
                **metadata,
                "requirement": dependency.get("requirement") or "required",
                "sharing_mode": "card-bound-bundle",
                "bundle_id": str(bundle_metadata.get("bundle_id") or ""),
                "local_name": str(bundle_metadata.get("local_name") or skill_id),
                "original_author": str(bundle_metadata.get("original_author") or local_contributor_identity(repo_root)),
                "content_hash": content_hash,
                "version_time": version_time,
                "readonly_when_imported": True,
                "update_policy": SKILL_BUNDLE_UPDATE_POLICY,
            }
        )
    return manifest


def _public_dependency_payload(dependency: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in dependency.items() if not str(key).startswith("_")}


def materialize_skill_bundle_dependencies(
    dependencies: list[dict[str, Any]],
    outbox_dir: Path,
    *,
    dry_run: bool = False,
) -> list[dict[str, Any]]:
    materialized: list[dict[str, Any]] = []
    outbox_dir = Path(outbox_dir)
    for dependency in dependencies:
        payload = _public_dependency_payload(dependency)
        if dependency.get("sharing_mode") != "card-bound-bundle":
            materialized.append(payload)
            continue

        source_dir = Path(str(dependency.get("_source_dir") or ""))
        bundle_id = str(dependency.get("bundle_id") or "").strip()
        version_time = str(dependency.get("version_time") or "").strip()
        content_hash = str(dependency.get("content_hash") or "").strip()
        bundle_root = (
            outbox_dir
            / "skills"
            / _safe_segment(bundle_id, fallback="bundle")
            / _compact_bundle_version_segment(version_time, content_hash)
        )
        skill_target = bundle_root / "skill"
        metadata_target = bundle_root / "metadata.yaml"
        payload["bundle_path"] = skill_target.relative_to(outbox_dir).as_posix()
        payload["bundle_metadata_path"] = metadata_target.relative_to(outbox_dir).as_posix()
        if not dry_run:
            if not source_dir.exists():
                payload["sharing_mode"] = "missing"
                payload["status"] = "missing"
            else:
                if skill_target.exists():
                    shutil.rmtree(skill_target)
                skill_target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(
                    source_dir,
                    skill_target,
                    ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
                )
                write_yaml_file(
                    metadata_target,
                    {
                        "bundle_id": bundle_id,
                        "local_name": payload.get("local_name") or payload.get("id"),
                        "original_author": payload.get("original_author"),
                        "content_hash": content_hash,
                        "version_time": version_time,
                        "readonly_when_imported": True,
                        "update_policy": SKILL_BUNDLE_UPDATE_POLICY,
                        "source_skill_id": payload.get("id"),
                        "source_skill_name": payload.get("name"),
                    },
                )
        materialized.append(payload)
    return materialized


def normalize_skill_bundle_dependency(dependency: dict[str, Any]) -> dict[str, Any]:
    bundle_id = str(dependency.get("bundle_id") or dependency.get("id") or "").strip()
    version_time = str(dependency.get("version_time") or dependency.get("exported_at") or "").strip()
    content_hash = str(dependency.get("content_hash") or "").strip()
    return {
        "bundle_id": bundle_id,
        "id": str(dependency.get("id") or bundle_id).strip(),
        "local_name": str(dependency.get("local_name") or dependency.get("name") or dependency.get("id") or "").strip(),
        "name": str(dependency.get("name") or dependency.get("local_name") or dependency.get("id") or "").strip(),
        "requirement": str(dependency.get("requirement") or "required").strip(),
        "content_hash": content_hash,
        "version_time": version_time,
        "original_author": str(dependency.get("original_author") or "").strip(),
        "readonly_when_imported": bool(dependency.get("readonly_when_imported", True)),
        "update_policy": str(dependency.get("update_policy") or SKILL_BUNDLE_UPDATE_POLICY).strip(),
        "status": str(dependency.get("status") or "").strip(),
        "sharing_mode": str(dependency.get("sharing_mode") or "").strip(),
    }


def select_latest_skill_bundle_versions(dependencies: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_bundle: dict[str, list[dict[str, Any]]] = {}
    for dependency in dependencies:
        item = normalize_skill_bundle_dependency(dependency)
        bundle_id = item["bundle_id"]
        if not bundle_id:
            continue
        by_bundle.setdefault(bundle_id, []).append(item)
    return {bundle_id: _latest_version(items) for bundle_id, items in by_bundle.items()}


def install_imported_skill_bundle_version(
    repo_root: Path,
    dependency: dict[str, Any],
    source_skill_dir: Path,
    *,
    source_card_id: str = "",
    status: str = "approved",
    dry_run: bool = False,
) -> dict[str, Any]:
    item = normalize_skill_bundle_dependency(dependency)
    bundle_id = item["bundle_id"]
    if not bundle_id:
        return {"ok": False, "errors": ["bundle_id is required"], "status": "missing_bundle_id"}
    source_skill_dir = Path(source_skill_dir)
    if not source_skill_dir.exists():
        return {"ok": False, "bundle_id": bundle_id, "errors": [f"Skill source does not exist: {source_skill_dir}"], "status": "missing_source"}

    observed_hash = skill_directory_content_hash(source_skill_dir)
    if item["content_hash"] and item["content_hash"] != observed_hash:
        return {
            "ok": False,
            "bundle_id": bundle_id,
            "errors": [f"Skill bundle content_hash mismatch: expected {item['content_hash']}, observed {observed_hash}"],
            "status": "hash_mismatch",
        }
    content_hash = item["content_hash"] or observed_hash
    version_time = item["version_time"] or utc_now_iso()
    bundle_dir = imported_skill_bundle_dir(Path(repo_root), bundle_id)
    version_dir = bundle_dir / "versions" / _safe_segment(version_time, fallback="version") / _safe_hash_segment(content_hash)
    skill_target = version_dir / "skill"
    metadata_path = version_dir / "metadata.yaml"
    if not dry_run:
        if skill_target.exists():
            shutil.rmtree(skill_target)
        skill_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_skill_dir, skill_target, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
        source_cards = [source_card_id] if source_card_id else []
        write_yaml_file(
            metadata_path,
            {
                **item,
                "content_hash": content_hash,
                "version_time": version_time,
                "status": status,
                "readonly": True,
                "source_cards": source_cards,
            },
        )
    return {
        "ok": True,
        "bundle_id": bundle_id,
        "content_hash": content_hash,
        "version_time": version_time,
        "path": str(version_dir),
        "dry_run": dry_run,
    }


def consolidate_imported_skill_bundles(repo_root: Path, *, dry_run: bool = False) -> dict[str, Any]:
    root = imported_skill_bundle_root(Path(repo_root))
    bundles: dict[str, list[dict[str, Any]]] = {}
    if root.exists():
        for metadata_path in sorted(root.glob("*/versions/*/*/metadata.yaml")):
            payload = _read_yaml_mapping(metadata_path)
            item = normalize_skill_bundle_dependency(payload)
            bundle_id = item["bundle_id"] or metadata_path.parents[3].name
            if not bundle_id:
                continue
            item["metadata_path"] = str(metadata_path)
            item["version_dir"] = str(metadata_path.parent)
            item["status"] = str(payload.get("status") or item.get("status") or "approved")
            item["source_cards"] = payload.get("source_cards") if isinstance(payload.get("source_cards"), list) else []
            bundles.setdefault(bundle_id, []).append(item)

    kept: list[dict[str, Any]] = []
    removed: list[dict[str, Any]] = []
    for bundle_id, versions in bundles.items():
        approved = [item for item in versions if str(item.get("status") or "").lower() in {"approved", "installed", ""}]
        candidates = approved or versions
        latest = _latest_version(candidates)
        if not latest:
            continue
        kept.append(latest)
        latest_dir = Path(str(latest.get("version_dir") or ""))
        for item in versions:
            version_dir = Path(str(item.get("version_dir") or ""))
            if version_dir == latest_dir:
                continue
            removed.append(item)
            if not dry_run and version_dir.exists():
                shutil.rmtree(version_dir)
        if not dry_run:
            bundle_metadata_path = imported_skill_bundle_dir(Path(repo_root), bundle_id) / "metadata.yaml"
            write_yaml_file(
                bundle_metadata_path,
                {
                    "bundle_id": bundle_id,
                    "latest_version": {
                        key: latest.get(key)
                        for key in (
                            "content_hash",
                            "version_time",
                            "original_author",
                            "local_name",
                            "name",
                            "status",
                            "update_policy",
                        )
                        if latest.get(key) not in {None, ""}
                    },
                    "readonly": True,
                    "source_cards": sorted({str(card) for item in versions for card in item.get("source_cards", []) if str(card).strip()}),
                },
            )
    return {
        "ok": True,
        "dry_run": dry_run,
        "bundle_count": len(bundles),
        "kept_count": len(kept),
        "removed_count": len(removed),
        "kept": kept,
        "removed": removed,
    }


def normalize_skill_registry_item(item: dict[str, Any]) -> dict[str, Any]:
    skill_id = str(item.get("id") or item.get("name") or "").strip()
    status = str(item.get("status") or "").strip().lower()
    return {
        "id": skill_id,
        "name": str(item.get("name") or skill_id).strip(),
        "bundle_id": str(item.get("bundle_id") or "").strip(),
        "status": status,
        "version": str(item.get("version") or "").strip(),
        "version_time": str(item.get("version_time") or "").strip(),
        "owner": str(item.get("owner") or "").strip(),
        "original_author": str(item.get("original_author") or item.get("owner") or "").strip(),
        "submitted_by": str(item.get("submitted_by") or "").strip(),
        "source_repo": str(item.get("source_repo") or "").strip(),
        "source_path": str(item.get("source_path") or "").strip(),
        "content_hash": str(item.get("content_hash") or "").strip(),
        "description": str(item.get("description") or "").strip(),
        "readonly_when_imported": bool(item.get("readonly_when_imported", True)),
        "update_policy": str(item.get("update_policy") or SKILL_BUNDLE_UPDATE_POLICY).strip(),
    }


def load_organization_skill_registry(org_root: Path, registry_path: str = "skills/registry.yaml") -> dict[str, Any]:
    path = Path(org_root) / registry_path
    if not path.exists():
        return {"ok": False, "errors": [f"skills registry does not exist: {registry_path}"], "skills": [], "by_id": {}, "by_bundle_id": {}}

    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict) or not isinstance(payload.get("skills"), list):
        return {"ok": False, "errors": ["skills registry must contain a skills list"], "skills": [], "by_id": {}, "by_bundle_id": {}}

    errors: list[str] = []
    skills: list[dict[str, Any]] = []
    by_id: dict[str, dict[str, Any]] = {}
    versions_by_bundle: dict[str, list[dict[str, Any]]] = {}
    for index, raw_item in enumerate(payload["skills"]):
        if not isinstance(raw_item, dict):
            errors.append(f"skills[{index}] must be a mapping")
            continue
        item = normalize_skill_registry_item(raw_item)
        skill_id = item["id"]
        if not skill_id:
            errors.append(f"skills[{index}] is missing id")
            continue
        if item["status"] not in SKILL_REVIEW_STATES:
            errors.append(f"skill {skill_id} has invalid status: {item['status']}")
        if item["status"] == "approved":
            if not item["version"] and not item["version_time"]:
                errors.append(f"approved skill {skill_id} must pin version")
            if not item["content_hash"].startswith("sha256:"):
                errors.append(f"approved skill {skill_id} must pin sha256 content_hash")
        skills.append(item)
        by_id.setdefault(skill_id, item)
        bundle_id = str(item.get("bundle_id") or "").strip()
        if bundle_id:
            versions_by_bundle.setdefault(bundle_id, []).append(item)

    by_bundle_id = {bundle_id: _latest_version(items) for bundle_id, items in versions_by_bundle.items()}
    return {"ok": not errors, "errors": errors, "skills": skills, "by_id": by_id, "by_bundle_id": by_bundle_id}


def skill_auto_install_eligibility(skill: dict[str, Any], *, local_policy_allows: bool) -> dict[str, Any]:
    reasons: list[str] = []
    if not local_policy_allows:
        reasons.append("local policy does not allow automatic organization Skill installation")
    if str(skill.get("status") or "").strip().lower() != "approved":
        reasons.append("Skill is not approved")
    if not str(skill.get("version") or skill.get("version_time") or "").strip():
        reasons.append("Skill version is not pinned")
    if not str(skill.get("content_hash") or "").strip().startswith("sha256:"):
        reasons.append("Skill content_hash is not sha256 pinned")
    if not str(skill.get("source_repo") or "").strip():
        reasons.append("Skill source_repo is missing")
    return {
        "eligible": not reasons,
        "reasons": reasons,
        "skill_id": str(skill.get("id") or skill.get("name") or "").strip(),
    }


def skill_directory_content_hash(skill_dir: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(Path(skill_dir).rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(skill_dir)
        if any(part in {".git", "__pycache__"} for part in relative.parts):
            continue
        if path.suffix == ".pyc":
            continue
        digest.update(relative.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def _safe_cache_name(value: str) -> str:
    safe = "".join(char if char.isalnum() or char in {"-", "_", "."} else "-" for char in value)
    safe = safe.strip(".-")
    return safe[:80] or "organization-skill"


def _run_git(args: list[str], *, cwd: Path | None = None) -> tuple[bool, str]:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=str(cwd) if cwd is not None else None,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        return False, str(exc)
    output = (completed.stdout + completed.stderr).strip()
    return completed.returncode == 0, output


def _checkout_skill_source(skill: dict[str, Any], cache_root: Path) -> tuple[Path | None, str]:
    source_repo = str(skill.get("source_repo") or "").strip()
    version = str(skill.get("version") or skill.get("version_time") or "").strip()
    local_source = Path(source_repo) if source_repo else Path()
    if source_repo and local_source.exists():
        return local_source, ""

    cache_root.mkdir(parents=True, exist_ok=True)
    checkout_dir = cache_root / _safe_cache_name(f"{skill.get('id')}-{version}")
    if checkout_dir.exists():
        ok, output = _run_git(["fetch", "--tags", "--prune"], cwd=checkout_dir)
        if not ok:
            return None, f"failed to fetch Skill source: {output}"
    else:
        ok, output = _run_git(["clone", source_repo, str(checkout_dir)])
        if not ok:
            return None, f"failed to clone Skill source: {output}"
    ok, output = _run_git(["checkout", version], cwd=checkout_dir)
    if not ok:
        return None, f"failed to checkout Skill version {version}: {output}"
    return checkout_dir, ""


def _resolve_skill_source_dir(checkout_root: Path, skill: dict[str, Any]) -> Path | None:
    source_path = str(skill.get("source_path") or "").strip()
    skill_id = str(skill.get("id") or "").strip()
    candidates = []
    if source_path:
        candidates.append(checkout_root / source_path)
    if skill_id:
        candidates.append(checkout_root / skill_id)
    candidates.append(checkout_root)
    for candidate in candidates:
        if (candidate / "SKILL.md").exists():
            return candidate
    return None


def resolve_skill_bundle_source_dir(
    org_root: Path,
    source_info: dict[str, Any],
    dependency: dict[str, Any],
) -> Path | None:
    bundle_path = str(dependency.get("bundle_path") or "").strip()
    if not bundle_path:
        return None
    bundle_relative = Path(bundle_path)
    candidates: list[Path] = []
    if bundle_relative.is_absolute():
        candidates.append(bundle_relative)
    else:
        source_relative = Path(str(source_info.get("path") or ""))
        if source_relative.parts:
            candidates.append(Path(org_root) / source_relative.parent / bundle_relative)
        candidates.append(Path(org_root) / bundle_relative)
    for candidate in candidates:
        if (candidate / "SKILL.md").exists():
            return candidate
    return None


def install_approved_organization_skill(
    skill: dict[str, Any],
    *,
    codex_home: Path | None = None,
    cache_root: Path | None = None,
    local_policy_allows: bool = False,
    replace_existing: bool = False,
) -> dict[str, Any]:
    normalized = normalize_skill_registry_item(skill)
    eligibility = skill_auto_install_eligibility(normalized, local_policy_allows=local_policy_allows)
    if not eligibility["eligible"]:
        return {
            "ok": False,
            "skill_id": normalized["id"],
            "status": "not_eligible",
            "errors": eligibility["reasons"],
        }

    home = codex_home or Path(os.environ.get("CODEX_HOME", "") or Path.home() / ".codex")
    cache = cache_root or home / ".cache" / "organization-skills"
    checkout_root, checkout_error = _checkout_skill_source(normalized, cache)
    if checkout_root is None:
        return {"ok": False, "skill_id": normalized["id"], "status": "source_error", "errors": [checkout_error]}

    source_dir = _resolve_skill_source_dir(checkout_root, normalized)
    if source_dir is None:
        return {
            "ok": False,
            "skill_id": normalized["id"],
            "status": "missing_skill",
            "errors": ["Skill source does not contain SKILL.md at source_path, skill id path, or repo root"],
        }

    observed_hash = skill_directory_content_hash(source_dir)
    expected_hash = normalized["content_hash"]
    if observed_hash != expected_hash:
        return {
            "ok": False,
            "skill_id": normalized["id"],
            "status": "hash_mismatch",
            "errors": [f"Skill content_hash mismatch: expected {expected_hash}, observed {observed_hash}"],
        }

    install_name = normalized["bundle_id"] or normalized["id"]
    install_dir = home / "skills" / _safe_segment(install_name, fallback=normalized["id"] or "organization-skill")
    if install_dir.exists():
        installed_hash = skill_directory_content_hash(install_dir)
        if installed_hash == expected_hash:
            return {
                "ok": True,
                "skill_id": normalized["id"],
                "bundle_id": normalized["bundle_id"],
                "status": "already_installed",
                "install_path": str(install_dir),
                "content_hash": installed_hash,
            }
        if not replace_existing:
            return {
                "ok": False,
                "skill_id": normalized["id"],
                "status": "existing_version_conflict",
                "errors": ["A different local Skill version already exists; replacement was not allowed"],
            }
        shutil.rmtree(install_dir)

    install_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_dir, install_dir, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
    installed_hash = skill_directory_content_hash(install_dir)
    return {
        "ok": True,
        "skill_id": normalized["id"],
        "bundle_id": normalized["bundle_id"],
        "status": "installed",
        "install_path": str(install_dir),
        "content_hash": installed_hash,
    }


def annotate_dependencies_with_registry_status(
    dependencies: list[dict[str, Any]],
    registry: dict[str, Any],
    *,
    local_policy_allows_auto_install: bool = False,
) -> list[dict[str, Any]]:
    by_id = registry.get("by_id") if isinstance(registry.get("by_id"), dict) else {}
    by_bundle_id = registry.get("by_bundle_id") if isinstance(registry.get("by_bundle_id"), dict) else {}
    annotated: list[dict[str, Any]] = []
    for dependency in dependencies:
        skill_id = str(dependency.get("id") or "").strip()
        bundle_id = str(dependency.get("bundle_id") or "").strip()
        registry_item = by_bundle_id.get(bundle_id) if bundle_id and isinstance(by_bundle_id.get(bundle_id), dict) else None
        if registry_item is None:
            registry_item = by_id.get(skill_id) if isinstance(by_id.get(skill_id), dict) else None
        if registry_item is None:
            annotated.append(
                {
                    **dependency,
                    "registry_status": "missing",
                    "auto_install": {"eligible": False, "reasons": ["Skill is missing from organization registry"], "skill_id": skill_id},
                }
            )
            continue
        annotated.append(
                {
                    **dependency,
                    "registry_status": registry_item.get("status"),
                    "registry_version": registry_item.get("version") or registry_item.get("version_time"),
                    "auto_install": skill_auto_install_eligibility(
                    registry_item,
                    local_policy_allows=local_policy_allows_auto_install,
                ),
            }
        )
    return annotated
