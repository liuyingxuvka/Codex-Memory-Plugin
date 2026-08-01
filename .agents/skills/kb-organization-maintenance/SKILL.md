---
name: kb-organization-maintenance
description: Run the repository-managed Khaos Brain organization maintenance cycle. Use only when a user or automation explicitly asks to inspect, review, or maintain a validated organization KB repository and this machine has opted into organization maintenance; this is the organization exchange cycle, not ordinary local KB Sleep.
---

# KB Organization Maintenance

Run one organization maintenance cycle for this predictive KB repository: maintain the shared repository, contribute eligible local cards, and refresh a complete local snapshot for direct read-only retrieval.

The organization KB is a shared exchange layer, not a central truth layer. Treat
organization maintenance as Sleep for the shared exchange surface: it can
maintain `main` cards and imported card content when the evidence supports
the decision. Local machines still decide how strongly to rely on organization
cards. Normal retrieval uses the synchronized snapshot directly; it never
auto-adopts a card, publishes a local model, or installs a card-bound Skill.

The shared card remains an exchange projection. Organization maintenance owns
the organization repository's review state, not any machine's local LogicGuard
model or ModelMesh. A receiving machine searches and uses the synchronized card
directly; only later outcome evidence may cause local Sleep to reinforce,
dampen, suppress, or derive a new local candidate. Similarity or co-use never
creates a local canonical mesh edge automatically.

Use `kb/imports` as the sole incoming lane and `kb/main` as the sole organization
exchange surface. Retired `kb/trusted` or `kb/candidates` roots are upgrade-only
input and must make daily maintenance fail visibly. Local download/search reads
organization cards only from `kb/main`, never from `kb/imports` or an old root.

## Authority

Work from the repository root. Treat these files as authoritative before stateful organization maintenance:

- PROJECT_SPEC.md
- docs/maintenance_agent_worldview.md
- docs/organization_mode_plan.md
- .agents/skills/local-kb-retrieve/SKILL.md
- `organization-review` guidance, when available. This is a judgment aid, not an apply gate.

Current user instructions still override repository files.

## Execution Contract

1. Use `scripts/kb_org_maintainer.py --automation --cycle` as the entry point. It serializes the existing organization maintenance and contribution facades; do not schedule either child separately.
2. The entry point must first read .local/khaos_brain_desktop_settings.json.
3. If organization mode is not validated or this machine has not opted into organization maintenance, exit successfully with a no-op result.
4. Run KB preflight against system/knowledge-library/organization before inspecting organization candidates.
5. Pin the exact source commit. If the source is an upgradeable old managed format, run the versioned direct-to-current source upgrader transaction before ordinary validation; normal maintenance has no legacy reader. Validate schema-2 manifest, exact catalog identity set, `kb/imports`, `kb/main`, portable LogicGuard bundles, absence of retired roots/fields, Skill registry, and Git state. After synchronization, copy the verified source bundles into one content-addressed immutable snapshot and move its pointer only by compare-and-swap.
6. Read the shared maintenance-agent worldview and apply the exchange-layer Sleep model: organization `main` cards are maintainable content, not untouchable central truth.
7. Run the organization card-surface map checkpoint. Summarize `main` trusted/candidate/rejected/deprecated counts plus import counts; low-confidence main trusted cards; duplicate/similar cards; stale rejected/deprecated cards; Skill-linked cards; retired-layout residual count; and privacy/Skill risks before applying anything. A nonzero retired-layout residual is a blocker, not a readable surface.
8. Run the organization candidate intake checkpoint. Review new imports for reusable scenario, action, prediction, confidence, route, provenance, and public sharing value; reviewed imports can move into `main` as `candidate` or `trusted`.
9. Run the organization content-hash checkpoint. Use content hashes for duplicate analysis across `main`, imports, prior accepted uploads, and current proposals. The source upgrader assigns a stable new identity to every non-identical duplicate and records exact duplicates as catalog tombstones; ordinary snapshot code must reject duplicate current identities.
10. Run the mandatory organization similar-card merge checkpoint. Inspect overlapping cards by scenario, action, prediction, route, evidence, and content hash. A proposed merge must either produce a digest-bound reversible apply packet with explicit field ownership, or close as `keep_separate`/`blocked_evidence` with a machine-evaluable reopen condition. Generic permanent watch is not a terminal.
11. Run the mandatory organization overloaded-card split checkpoint. Use LogicGuard node roles and boundaries rather than list length. A proposed split must either produce a reversible apply packet, or close as `keep_single`/`blocked_evidence` with an executable reopen condition. Legitimate alternatives under one root claim are not automatically an overloaded card.
12. Run the organization card decision checkpoint. For each reviewed card bundle, including `main` cards, decide whether to keep, approve/promote, reject with reason, rewrite, adjust confidence, supersede, deprecate, merge, or split. Do not skip the decision checkpoint itself.
13. Apply the organization maintenance worldview to card candidates, `main` card changes, card-and-Skill bundles, Skill registry changes, privacy boundaries, and GitHub auto-merge readiness. Use `organization-review` as a review lens when available, but do not block direct Sleep-style maintenance because the local Skill is absent.
14. Run the organization Skill safety checkpoint. For every declared Skill dependency or Skill candidate, check card evidence, public usefulness, privacy boundaries, install risk, `bundle_id`, `sha256:` content hash, current `unavailable_skill_guidance`, read-only import behavior, and status.
15. Run the organization Skill bundle version checkpoint. Group Skill bundles by `bundle_id`; approve only original-author updates on the same bundle, treat non-author changes as forks with new `bundle_id`, and select the latest approved version by `version_time` for organization distribution.
16. Treat `candidate`, `approved`, and `rejected` as Skill-bundle review states only. Card lifecycle states are exactly `trusted`, `candidate`, `deprecated`, and `rejected`. Never auto-install a card-bound Skill during snapshot, retrieval, selection, or use.
17. Build an organization Sleep decision set over the cleanup proposal. Every merge/split action must close as ready packet, keep-separate/keep-single, or typed blocked evidence with a reopen predicate.
18. Apply only exact selected packet ids through the source publication transaction. Every card/status/confidence/merge/split change rebuilds the affected bundle and catalog and has an exact rollback inventory. Missing `organization-review` guidance is not a blocker.
19. Run the post-apply organization check after selected actions are applied, and keep the audit path for rollback.
20. Commit and push applied maintenance changes to a maintenance branch, open the PR when the repository is on GitHub, apply `org-kb:auto-merge` only for reviewed main/imports changes with audit evidence, then restore the local mirror to the organization base branch so later sync or contribution work does not continue on an old maintenance branch.
21. Run the GitHub merge-readiness checkpoint. Confirm changed paths, low-risk import eligibility or reviewed-maintenance eligibility, required checks, rollback story, and whether the PR should be auto-merge eligible or remain review-only.
22. Do not skip the merge, split, card-decision, Skill-safety, Skill-bundle-version, decision-apply, post-apply, maintenance-branch, or GitHub-readiness checkpoints. It is acceptable to skip applying a change when evidence, safety, tooling, permissions, or scope is insufficient, but the inspection and recorded decision must still happen.
23. Run the single cycle postflight after a non-skipped pass and record the result as structured history. A failed snapshot activation is a visible cycle failure; retrieval must continue using the previous complete snapshot.

## Report

Report the settings gate result, participation status, preflight entry ids, organization manifest status, current-layout policy, retired-layout residual count, card-surface map, `main` status counts and import counts, main-card maintenance decisions, content-hash duplicate decisions, organization merge checkpoint decisions, organization split checkpoint decisions, card approval/rejection/rewrite/deprecation decisions, Sleep decision counts, selected action ids, apply result, post-apply check result, maintenance branch, PR, push, and auto-merge-label result, Skill dependency decisions, Skill bundle version decisions, GitHub merge-readiness result, organization-review guidance availability, recommendations, postflight record path, and any errors.

## Native completion boundary

For a scheduled run, intake, planning, or proposal-only output is incomplete. Run `python scripts/run_kb_automation.py --skill kb-organization-maintenance --json`. The target-owned wrapper invokes `scripts/kb_org_maintainer.py --automation --cycle` once and accepts only its immutable cycle receipt for that exact run. A settings-gated no-op counts only when the native gate receipt proves it terminal. Fixture or capability evidence cannot replace the concrete scheduled run.

Ordinary use is self-contained and does not read an author-maintenance contract, external receipt, router, or installed maintenance tool. Author-side checks may validate organization maintenance before distribution but never participate in a scheduled maintenance run.
