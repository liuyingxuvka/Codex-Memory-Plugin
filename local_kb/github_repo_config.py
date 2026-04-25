from __future__ import annotations

import json
import re
import subprocess
import urllib.error
import urllib.request
from typing import Any

from local_kb.org_sources import _git_executable


def parse_github_owner_repo(repo_url: str) -> tuple[str, str]:
    text = str(repo_url or "").strip()
    if text.endswith(".git"):
        text = text[:-4]
    if text.startswith("git@github.com:"):
        text = text.removeprefix("git@github.com:")
    elif text.startswith("https://github.com/"):
        text = text.removeprefix("https://github.com/")
    else:
        match = re.search(r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/\s]+)", text)
        if not match:
            return "", ""
        return match.group("owner"), match.group("repo").removesuffix(".git")
    parts = [part for part in text.split("/") if part]
    if len(parts) < 2:
        return "", ""
    return parts[0], parts[1]


def build_branch_protection_payload(required_contexts: list[str]) -> dict[str, Any]:
    return {
        "required_status_checks": {
            "strict": True,
            "contexts": required_contexts,
        },
        "enforce_admins": False,
        "required_pull_request_reviews": None,
        "restrictions": None,
        "required_linear_history": False,
        "allow_force_pushes": False,
        "allow_deletions": False,
        "block_creations": False,
        "required_conversation_resolution": False,
        "lock_branch": False,
        "allow_fork_syncing": True,
    }


def github_token_from_git_credential() -> str:
    payload = "protocol=https\nhost=github.com\n\n"
    result = subprocess.run(
        [_git_executable(), "credential", "fill"],
        input=payload,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return ""
    values: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values.get("password", "")


def _github_json_request(method: str, url: str, token: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
            return {"ok": 200 <= response.status < 300, "status": response.status, "body": json.loads(raw) if raw else {}}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            body: Any = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            body = raw
        return {"ok": False, "status": exc.code, "body": body}
    except OSError as exc:
        return {"ok": False, "status": 0, "body": {"message": str(exc)}}


def configure_github_org_kb_repository(
    repo_url: str,
    *,
    token: str,
    branch: str = "main",
    required_contexts: list[str] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    owner, repo = parse_github_owner_repo(repo_url)
    if not owner or not repo:
        return {"ok": False, "errors": ["repo_url is not a GitHub repository URL"], "steps": []}
    if not token and not dry_run:
        return {"ok": False, "errors": ["GitHub token is required"], "steps": []}

    contexts = required_contexts or ["organization-kb-checks"]
    protection_payload = build_branch_protection_payload(contexts)
    steps = [
        {
            "name": "enable-auto-merge",
            "method": "PATCH",
            "url": f"https://api.github.com/repos/{owner}/{repo}",
            "payload": {"allow_auto_merge": True},
        },
        {
            "name": "protect-default-branch",
            "method": "PUT",
            "url": f"https://api.github.com/repos/{owner}/{repo}/branches/{branch}/protection",
            "payload": protection_payload,
        },
    ]
    if dry_run:
        return {"ok": True, "dry_run": True, "owner": owner, "repo": repo, "branch": branch, "steps": steps, "errors": []}

    results: list[dict[str, Any]] = []
    errors: list[str] = []
    for step in steps:
        result = _github_json_request(step["method"], step["url"], token, step["payload"])
        results.append({"name": step["name"], **result})
        if not result.get("ok"):
            message = result.get("body", {}).get("message") if isinstance(result.get("body"), dict) else result.get("body")
            errors.append(f"{step['name']} failed: {message or result.get('status')}")

    return {
        "ok": not errors,
        "dry_run": False,
        "owner": owner,
        "repo": repo,
        "branch": branch,
        "steps": results,
        "errors": errors,
    }
