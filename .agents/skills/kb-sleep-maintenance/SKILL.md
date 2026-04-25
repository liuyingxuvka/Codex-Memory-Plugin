---
name: kb-sleep-maintenance
description: Run the repository-managed local KB Sleep maintenance pass. Use only when a user or automation explicitly asks for KB Sleep, sleep maintenance, local KB consolidation, or the scheduled KB Sleep automation; do not use for ordinary task preflight or active-task KB writes.
---

# KB Sleep Maintenance

Run one dedicated Sleep maintenance pass for this predictive KB repository.

## Authority

Work from the repository root. Treat these files as authoritative and read them before stateful maintenance:

- `PROJECT_SPEC.md`
- `docs/maintenance_runbook.md`
- `.agents/skills/local-kb-retrieve/MAINTENANCE_PROMPT.md`

Current user instructions still override repository files.

## Execution Contract

1. Write a visible execution plan before the first stateful command, with checkpoint statuses.
2. Run the sleep self-preflight search against `system/knowledge-library/maintenance`.
3. Inspect taxonomy, route gaps, route navigation when needed, and proposal-mode consolidation output.
4. Run the mandatory similar-card merge checkpoint. Inspect cards surfaced by maintenance output for overlapping scenario, action, prediction, route, or evidence. Decide whether to merge, propose a merge, or skip application with a concrete reason.
5. Run the mandatory overloaded-card split checkpoint. Inspect recurrent, broad, or `split_review_suggestion` cards and decide whether each one is still a hub card, should move toward a split proposal, or should skip application with a concrete reason.
6. Run the organization Skill bundle consolidation checkpoint. For imported read-only organization Skills, group by `bundle_id`, keep only the latest approved version by `version_time`, preserve source-card references, and keep all local cards pointing at the same `bundle_id`.
7. Do not skip the merge, split, or Skill bundle consolidation checkpoint itself. It is acceptable to skip applying a merge, split, or Skill replacement when evidence, safety, tooling, or scope is insufficient, but the inspection and recorded decision must still happen.
8. Prefer functional, reusable domain paths over project-name route roots when reviewing candidates.
9. Continue through every safe checkpoint instead of stopping after a short proposal.
10. Apply only clearly eligible low-risk lanes supported by current tooling: new-candidates, related-cards, cross-index, AI-authored semantic-review, and AI-authored zh-CN i18n.
11. Limit semantic-review to at most 3 trusted-card modifications per run.
12. Run zh-CN display translation cleanup after candidate/card creation or semantic text changes.
13. Keep taxonomy rewrites proposal-only unless current tooling cleanly supports the exact change.
14. Inspect rollback artifacts when needed.
15. Attempt supported low-risk repairs and rerun the relevant validation when a command exposes a fixable issue.
16. Run a final sleep postflight check.
17. Append one structured maintenance observation when the pass exposed a reusable lesson, route gap, card weakness, merge signal, split signal, Skill bundle update, or process hazard.
18. Stop after that final observation. Do not immediately consolidate the observation just written.

## Report

Report the run id, checkpoint status, self-preflight entries, observation counts reviewed, candidates created, route adjustments or concerns, similar-card merge checkpoint decisions, overloaded-card split checkpoint decisions, organization Skill bundle consolidation decisions, semantic-review decisions applied or skipped, translations updated or still missing, validations run, repaired or proposal-only issues, maintenance decisions, postflight observation status, undeclared taxonomy gaps, hub-vs-overloaded card reviews, and next proposal-only targets.
