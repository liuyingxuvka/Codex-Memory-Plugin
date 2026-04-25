---
name: kb-organization-contribute
description: Run the repository-managed Khaos Brain organization contribution pass. Use only when a user or automation explicitly asks to export local shareable KB cards into a validated organization repository; no-op in personal mode or unvalidated organization settings.
---

# KB Organization Contribute

Run one organization contribution pass for this predictive KB repository.

## Authority

Work from the repository root. Treat these files as authoritative before stateful contribution work:

- `PROJECT_SPEC.md`
- `docs/organization_mode_plan.md`
- `.agents/skills/local-kb-retrieve/SKILL.md`

Current user instructions still override repository files.

## Execution Contract

1. Use `scripts/kb_org_outbox.py --automation` as the entry point.
2. The entry point must first read `.local/khaos_brain_desktop_settings.json`.
3. If organization mode is not connected to a validated organization repository, exit successfully with a no-op result.
4. Run KB preflight against `system/knowledge-library/organization` before exporting any proposals.
5. Export only shareable model or heuristic cards with public scope and useful organization-level guidance.
6. Do not export private cards, personal preferences, credentials, raw local paths, or raw machine identifiers.
7. Use content hashes for duplicate prevention across current local cards, prior downloads, prior uploads, current organization cards, and current organization imports.
8. Put eligible local cards into the organization outbox or import proposal path; leave merge approval to the organization repository and GitHub checks.
9. When a card depends on a local Skill, upload it as a card-bound Skill bundle with `bundle_id`, `content_hash`, `version_time`, `original_author`, `readonly_when_imported: true`, and `update_policy: original_author_only`.
10. If several local cards point at the same `bundle_id`, upload the local latest version for that bundle, not an older card-carried copy.
11. Include Skill dependencies only when card evidence explains when the Skill is useful, what outcome it predicts, and what fallback exists.
12. Run KB postflight after a non-skipped contribution pass and record the result as structured history.

## Report

Report the settings gate result, preflight entry ids, created/skipped proposal counts, content-hash duplicate decisions, card-bound Skill bundle ids and version hashes, branch or import proposal status, push or PR URL if attempted, postflight record path, and any errors.
