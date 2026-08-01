from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any

import yaml


CURRENT_SOURCE_SCHEMA_VERSION = 2
CURRENT_CATALOG_SCHEMA = "khaos-brain.organization-card-catalog.v1"
CURRENT_BUNDLE_SCHEMA = "khaos-brain.organization-logicguard-bundle.v1"
CURRENT_PROJECTION_SCHEMA = "khaos-brain.card-projection.v1"
CURRENT_SOURCE_BUILDER = {
    "name": "khaos-brain.organization-source-builder",
    "version": 2,
    "text_digest_policy": "utf8-lf-v1",
    "card_projection_schema": CURRENT_PROJECTION_SCHEMA,
    "bundle_schema": CURRENT_BUNDLE_SCHEMA,
}
CATALOG_PATH = "kb/organization_catalog.json"
BUNDLE_ROOT = "kb/logicguard/bundles"
LOW_RISK_PREFIXES = ("kb/imports/", "skills/candidates/")
MAINTENANCE_PREFIXES = ("kb/main/", f"{BUNDLE_ROOT}/")
MAINTENANCE_EXACT_PATHS = {
    "maintenance/cleanup_audit.jsonl",
    CATALOG_PATH,
    "khaos_org_kb.yaml",
}
SKILL_REVIEW_STATES = {"candidate", "approved", "rejected"}
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bghp_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"(?im)^\s*(password|secret|api[_-]?key|access[_-]?token)\s*:\s*['\"]?[^'\"\s][^'\"]*"),
)
LOCAL_PATH_PATTERNS = (
    re.compile(r"[A-Za-z]:\\Users\\"),
    re.compile(r"/Users/[^/\s]+/"),
    re.compile(r"/home/[^/\s]+/"),
    re.compile(r"\.codex[\\/]+"),
    re.compile(r"AppData\\"),
)
RAW_MACHINE_KEYS = {"hardware_id", "hardware_fingerprint", "machine_id", "device_id", "local_installation_id"}


def print_machine_json(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=True, indent=2))


def normalize_changed_file(value: str) -> str:
    text = str(value or "").strip().replace("\\", "/")
    while text.startswith("./"):
        text = text[2:]
    if not text or text.startswith("/") or re.match(r"^[A-Za-z]:", text):
        return ""
    parts = PurePosixPath(text).parts
    if any(part in {"", ".", ".."} for part in parts):
        return ""
    return "/".join(parts)


def load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return payload if isinstance(payload, dict) else {}


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def canonical_digest(payload: dict[str, Any], *, excluded_key: str) -> str:
    body = {key: value for key, value in payload.items() if key != excluded_key}
    encoded = json.dumps(
        body,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def file_sha256(path: Path) -> str:
    text = path.read_bytes().decode("utf-8")
    portable = text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    return hashlib.sha256(portable).hexdigest()


def append_machine_key_errors(payload: Any, errors: list[str], path_label: str, key_path: str = "") -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            next_key = f"{key_path}.{key}" if key_path else str(key)
            if str(key) in RAW_MACHINE_KEYS and str(value or "").strip():
                errors.append(f"{path_label}: raw machine identifier is not allowed at {next_key}")
            append_machine_key_errors(value, errors, path_label, next_key)
    elif isinstance(payload, list):
        for index, item in enumerate(payload):
            append_machine_key_errors(item, errors, path_label, f"{key_path}[{index}]")


def check_manifest(root: Path) -> list[str]:
    errors: list[str] = []
    manifest_path = root / "khaos_org_kb.yaml"
    if not manifest_path.exists():
        return ["missing organization KB manifest: khaos_org_kb.yaml"]
    manifest = load_yaml(manifest_path)
    if manifest.get("kind") != "khaos-organization-kb":
        errors.append("manifest kind must be khaos-organization-kb")
    if manifest.get("schema_version") != CURRENT_SOURCE_SCHEMA_VERSION:
        errors.append(f"schema_version must be {CURRENT_SOURCE_SCHEMA_VERSION}")
    if not str(manifest.get("organization_id") or "").strip():
        errors.append("organization_id is required")
    kb = manifest.get("kb") if isinstance(manifest.get("kb"), dict) else {}
    main_path = str(kb.get("main_path") or "").strip()
    imports_path = str(kb.get("imports_path") or "").strip()
    if main_path != "kb/main":
        errors.append("kb.main_path must be exactly kb/main")
    if imports_path != "kb/imports":
        errors.append("kb.imports_path must be exactly kb/imports")
    expected_kb = {
        "catalog_path": CATALOG_PATH,
        "bundle_root": BUNDLE_ROOT,
        "projection_schema": CURRENT_PROJECTION_SCHEMA,
        "bundle_schema": CURRENT_BUNDLE_SCHEMA,
    }
    for field, expected in expected_kb.items():
        if kb.get(field) != expected:
            errors.append(f"kb.{field} must be exactly {expected}")
    obsolete_roots = [
        relative
        for relative in ("kb/trusted", "kb/candidates")
        if (root / relative).exists()
    ]
    if obsolete_roots:
        errors.append(
            "obsolete organization roots are forbidden: " + ", ".join(obsolete_roots)
        )
    card_paths = ("kb/main", "kb/imports")
    for relative in (*card_paths, "skills/candidates"):
        if not relative:
            continue
        if not (root / relative).exists():
            errors.append(f"required path does not exist: {relative}")
    if not (root / "skills" / "registry.yaml").exists():
        errors.append("skills registry does not exist: skills/registry.yaml")
    return errors


def check_catalog(root: Path, manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    catalog = load_json(root / CATALOG_PATH)
    organization_id = str(manifest.get("organization_id") or "")
    if catalog.get("schema_version") != CURRENT_CATALOG_SCHEMA:
        return ["organization card catalog schema is missing or unsupported"]
    if str(catalog.get("organization_id") or "") != organization_id:
        errors.append("organization card catalog organization_id mismatch")
    if str(catalog.get("catalog_digest") or "") != canonical_digest(
        catalog, excluded_key="catalog_digest"
    ):
        errors.append("organization card catalog digest mismatch")
    if catalog.get("builder_identity") != CURRENT_SOURCE_BUILDER:
        errors.append("organization card catalog builder identity is unsupported")
    rows = catalog.get("cards") if isinstance(catalog.get("cards"), list) else []
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    source_generation_id = str(catalog.get("source_generation_id") or "")
    for row in rows:
        if not isinstance(row, dict):
            errors.append("organization catalog card row must be an object")
            continue
        entry_id = str(row.get("entry_id") or "").strip()
        source_path = normalize_changed_file(str(row.get("source_path") or ""))
        if not entry_id or entry_id in seen_ids:
            errors.append(f"organization catalog card id is missing or duplicated: {entry_id or '?'}")
        if not source_path.startswith("kb/main/") or source_path in seen_paths:
            errors.append(f"organization catalog source path is invalid or duplicated: {source_path or '?'}")
        seen_ids.add(entry_id)
        seen_paths.add(source_path)
        source_file = root / source_path
        if not source_file.is_file():
            errors.append(f"organization catalog card source is missing: {source_path}")
            continue
        if file_sha256(source_file) != str(row.get("source_sha256") or ""):
            errors.append(f"organization catalog card source digest mismatch: {source_path}")
        source_projection = load_yaml(source_file)
        if str(source_projection.get("id") or "") != entry_id:
            errors.append(f"organization card identity differs from catalog: {source_path}")
        if str(source_projection.get("projection_schema_version") or "") != CURRENT_PROJECTION_SCHEMA:
            errors.append(f"organization card is not a current projection: {source_path}")
        artifacts: dict[str, Path] = {}
        for field in ("model_path", "mesh_path", "projection_path", "bundle_path"):
            relative = normalize_changed_file(str(row.get(field) or ""))
            path = root / relative
            artifacts[field] = path
            if not relative.startswith(f"{BUNDLE_ROOT}/") or not path.is_file():
                errors.append(f"organization card {entry_id or '?'} has missing or unsafe {field}")
        if not all(path.is_file() for path in artifacts.values()):
            continue
        packaged_projection = load_json(artifacts["projection_path"])
        bundle = load_json(artifacts["bundle_path"])
        if bundle.get("schema_version") != CURRENT_BUNDLE_SCHEMA:
            errors.append(f"organization card {entry_id or '?'} bundle schema is unsupported")
        if bundle.get("builder_identity") != CURRENT_SOURCE_BUILDER:
            errors.append(f"organization card {entry_id or '?'} bundle builder identity is unsupported")
        if str(bundle.get("organization_id") or "") != organization_id:
            errors.append(f"organization card {entry_id or '?'} bundle organization_id mismatch")
        if str(bundle.get("entry_id") or "") != entry_id:
            errors.append(f"organization card {entry_id or '?'} bundle entry_id mismatch")
        if str(bundle.get("generation_id") or "") != source_generation_id:
            errors.append(f"organization card {entry_id or '?'} bundle generation differs from catalog")
        if str(bundle.get("bundle_digest") or "") != canonical_digest(
            bundle, excluded_key="bundle_digest"
        ):
            errors.append(f"organization card {entry_id or '?'} bundle digest mismatch")
        if bundle.get("projection") != packaged_projection or packaged_projection != source_projection:
            errors.append(f"organization card {entry_id or '?'} projection copies differ")
        for field in ("bundle_digest", "model_digest", "mesh_digest", "projection_digest"):
            if str(bundle.get(field) or "") != str(row.get(field) or ""):
                errors.append(f"organization card {entry_id or '?'} {field} differs from catalog")
        if bundle.get("binding") != row.get("binding"):
            errors.append(f"organization card {entry_id or '?'} binding differs from catalog")
    actual_paths = {
        path.relative_to(root).as_posix()
        for suffix in ("*.yaml", "*.yml")
        for path in (root / "kb" / "main").rglob(suffix)
        if path.is_file()
    } if (root / "kb" / "main").is_dir() else set()
    if seen_paths != actual_paths:
        errors.append(
            "organization catalog identity set differs from kb/main: "
            f"missing={sorted(actual_paths - seen_paths)} extra={sorted(seen_paths - actual_paths)}"
        )
    return errors


def check_paths(changed_files: list[str], enforce_low_risk: bool, *, allow_maintenance_main: bool = False) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    blockers: list[str] = []
    has_maintenance_audit = "maintenance/cleanup_audit.jsonl" in changed_files
    outside = []
    for path in changed_files:
        if path.startswith(LOW_RISK_PREFIXES):
            continue
        if allow_maintenance_main and has_maintenance_audit and path.startswith(MAINTENANCE_PREFIXES):
            continue
        if allow_maintenance_main and has_maintenance_audit and path in MAINTENANCE_EXACT_PATHS:
            continue
        outside.append(path)
    if outside:
        blockers.append("changed files are not all low-risk paths")
        if enforce_low_risk:
            errors.extend(f"path is not eligible for low-risk auto-merge: {path}" for path in outside)
    if not changed_files:
        blockers.append("changed files are not all low-risk paths")
    return errors, blockers


def scan_content(root: Path, changed_files: list[str]) -> list[str]:
    errors: list[str] = []
    files = changed_files or [
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and ".git" not in path.parts and path.suffix.lower() in {".yaml", ".yml", ".md", ".json", ".txt"}
    ]
    for relative in files:
        path = root / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if any(pattern.search(text) for pattern in SECRET_PATTERNS):
            errors.append(f"{relative}: possible secret or credential pattern")
        if any(pattern.search(text) for pattern in LOCAL_PATH_PATTERNS):
            errors.append(f"{relative}: local machine path is not allowed")
        if path.suffix.lower() in {".yaml", ".yml"}:
            append_machine_key_errors(load_yaml(path), errors, relative)
    return errors


def check_skill_registry(root: Path) -> list[str]:
    errors: list[str] = []
    payload = load_yaml(root / "skills" / "registry.yaml")
    skills = payload.get("skills")
    if not isinstance(skills, list):
        return ["skills registry must contain a skills list"]
    seen: set[str] = set()
    for index, item in enumerate(skills):
        if not isinstance(item, dict):
            errors.append(f"skills[{index}] must be a mapping")
            continue
        skill_id = str(item.get("id") or item.get("name") or "").strip()
        status = str(item.get("status") or "").strip()
        if not skill_id:
            errors.append(f"skills[{index}] is missing id")
            continue
        if skill_id in seen:
            errors.append(f"duplicate skill id: {skill_id}")
        seen.add(skill_id)
        if status not in SKILL_REVIEW_STATES:
            errors.append(f"skill {skill_id} has invalid status: {status}")
        if status == "approved":
            if not str(item.get("version") or "").strip():
                errors.append(f"approved skill {skill_id} must pin version")
            if not str(item.get("content_hash") or "").startswith("sha256:"):
                errors.append(f"approved skill {skill_id} must pin sha256 content_hash")
    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--org-root", default=".")
    parser.add_argument("--changed-files-file", default="")
    parser.add_argument("--enforce-low-risk", action="store_true")
    parser.add_argument("--allow-maintenance-main", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    root = Path(args.org_root)
    changed_files = []
    if args.changed_files_file:
        changed_files = [
            path
            for path in (normalize_changed_file(line) for line in Path(args.changed_files_file).read_text(encoding="utf-8").splitlines())
            if path
        ]
    manifest_path = root / "khaos_org_kb.yaml"
    manifest = load_yaml(manifest_path) if manifest_path.exists() else {}
    path_errors, blockers = check_paths(
        changed_files,
        args.enforce_low_risk,
        allow_maintenance_main=args.allow_maintenance_main,
    )
    errors = [
        *check_manifest(root),
        *check_catalog(root, manifest),
        *path_errors,
        *scan_content(root, changed_files),
        *check_skill_registry(root),
    ]
    result = {
        "ok": not errors,
        "auto_merge_eligible": bool(changed_files) and not errors and not blockers,
        "errors": errors,
        "auto_merge_blockers": blockers,
        "changed_files": changed_files,
    }
    print_machine_json(result)
    if errors:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
