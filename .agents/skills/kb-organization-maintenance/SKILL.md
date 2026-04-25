---
name: kb-organization-maintenance
description: Run the repository-managed Khaos Brain organization maintenance pass. Use only when a user or automation explicitly asks to inspect, review, or maintain a validated organization KB repository and this machine has opted into organization maintenance; this is the organization-level Sleep-like maintenance flow, not ordinary local KB Sleep.
---

# KB Organization Maintenance

Run one organization-level Sleep-like maintenance pass for this predictive KB repository.

## Authority

Work from the repository root. Treat these files and Skills as authoritative before stateful organization maintenance:

- `PROJECT_SPEC.md`
- `docs/organization_mode_plan.md`
- `.agents/skills/local-kb-retrieve/SKILL.md`
- `$organization-review`

Current user instructions still override repository files.

## Execution Contract

1. Use `scripts/kb_org_maintainer.py --automation` as the entry point.
2. The entry point must first read `.local/khaos_brain_desktop_settings.json`.
3. If organization mode is not validated or this machine has not opted into organization maintenance, exit successfully with a no-op result.
4. Run KB preflight against `system/knowledge-library/organization` before inspecting organization candidates.
5. Validate the organization manifest, expected paths, imports lane, candidates lane, trusted lane, Skill registry, and current Git state before proposing changes.
6. Run the organization candidate intake checkpoint. Review new imports and candidates for reusable scenario, action, prediction, confidence, route, provenance, and public sharing value.
7. Run the organization content-hash checkpoint. Use content hashes for duplicate analysis across trusted cards, candidates, imports, prior accepted uploads, and current proposals. Duplicate entry ids alone are not a maintenance blocker.
8. Run the mandatory organization similar-card merge checkpoint. Inspect overlapping organization cards by scenario, action, prediction, route, evidence, and content hash. Decide whether to merge, propose a merge, supersede, or skip application with a concrete reason.
9. Run the mandatory organization overloaded-card split checkpoint. Inspect broad, recurrent, or multi-branch organization cards and decide whether each is still a useful hub, should move toward a split proposal, or should skip application with a concrete reason.
10. Run the organization candidate decision checkpoint. For each reviewed card bundle, decide whether to approve/promote, reject with reason, keep as candidate, supersede, deprecate, merge, or split. Do not skip the decision checkpoint itself.
11. Apply the `$organization-review` contract to card candidates, card-and-Skill bundles, Skill registry changes, privacy boundaries, and GitHub auto-merge readiness.
12. Run the organization Skill safety checkpoint. For every declared Skill dependency or Skill candidate, check card evidence, public usefulness, privacy boundaries, install risk, `bundle_id`, `sha256:` content hash, fallback behavior, read-only import behavior, and status.
13. Run the organization Skill bundle version checkpoint. Group Skill bundles by `bundle_id`; approve only original-author updates on the same bundle, treat non-author changes as forks with new `bundle_id`, and select the latest approved version by `version_time` for organization distribution.
14. Treat `candidate`, `approved`, and `rejected` as the first-pass Skill review states. Do not auto-install or recommend auto-install for candidate, rejected, unknown, unpinned, or non-hash-verified Skills.
15. Prefer candidate/import paths for automatic maintenance. Treat trusted cards, registry changes, policy changes, organization-review changes, and approved-Skill registry changes as higher risk.
16. Run the GitHub merge-readiness checkpoint. Confirm changed paths, low-risk lane eligibility, required checks, rollback story, and whether the PR should be auto-merge eligible or remain review-only.
17. Do not skip the merge, split, candidate-decision, Skill-safety, Skill-bundle-version, or GitHub-readiness checkpoints. It is acceptable to skip applying a change when evidence, safety, tooling, permissions, or scope is insufficient, but the inspection and recorded decision must still happen.
18. Run KB postflight after a non-skipped maintenance pass and record the result as structured history.

## Report

Report the settings gate result, participation status, preflight entry ids, organization manifest status, candidate/import counts, content-hash duplicate decisions, organization merge checkpoint decisions, organization split checkpoint decisions, candidate approval/rejection decisions, Skill dependency decisions, Skill bundle version decisions, GitHub merge-readiness result, organization-review availability, recommendations, postflight record path, and any errors.
