# Repository expectations

## Bootstrap

- If the user asks to install, enable, deploy, bootstrap, or set up this predictive KB system on any machine, your default first action is to run `python scripts/install_codex_kb.py --json` from the repository root.
- Immediately after installation, run `python scripts/install_codex_kb.py --check --json` and confirm the install is healthy before doing anything else.
- Treat the installer as idempotent. If the system may already be installed, rerun the installer anyway rather than asking the user to verify it manually.
- If this repository was moved to a new path or re-cloned, rerun the installer from the new clone so the Codex-side manifest points at the current KB root.
- The installed global preflight skill must enable implicit invocation, remind Codex to add phase-change KB checkpoints during long mixed tasks, and remind Codex to record KB postflight observations after meaningful work, including skill/plugin and subagent/delegation usage lessons when they materially affect task outcomes. Treat missing behavior as an installation defect and fix it.
- The installer must also refresh the repository-managed `kb-sleep-maintenance`, `kb-dream-pass`, `kb-organization-contribute`, `kb-organization-maintenance`, and `khaos-brain-update` skills under `$CODEX_HOME/skills`; these skills are explicit maintenance, organization, or update entry points and should not enable broad implicit invocation. `khaos-brain-update` is manual-only and has no automation binding.
- The installer must refresh exactly two scheduled composite automations under `$CODEX_HOME/automations`: `KB Sleep` owns the local Sleep-then-Dream cycle, and organization maintenance owns snapshot refresh, shared maintenance, and contribution. `kb-dream-pass` and `kb-organization-contribute` remain callable child Skills, not scheduled owners. The installer must permanently retire the exact legacy `kb-architect-pass` Skill, `kb-architect` automation, `khaos-brain-system-update` automation, and the former standalone Dream/contribution schedules on fresh installs and upgrades, without touching similarly named user assets.
- Every install or upgrade must run the versioned Chaos Brain maintenance migration, settle old lifecycle debt, archive retention-required cold evidence, prune only receipt-covered derivations, rescan for late reintroduced and Windows extended-length managed files, settle observations admitted by concurrent AI work through bounded post-commit receipts, rebuild the active index, preserve every surviving automation's user pause state, and remain rollbackable until current aggregate validation passes.
- Chaos Brain has zero normal-runtime compatibility and zero normal-runtime fallback. Exact retired formats may be read only by their versioned upgrade owner, which must rewrite or replace them directly, remove their old authority, prove zero residuals, and otherwise roll back while both retained composite automations remain paused. An incompatible residual is an unfinished upgrade-AI work item: derive one evidence-bound direct-to-current disposition and retry inside the rollbackable upgrade instead of adding a product reader. Missing current authority must fail visibly; never add a dual reader/writer, alias, alternate launcher/model, or silent downgrade.
- The installer must also write or refresh a repository-managed global defaults block under `$CODEX_HOME/AGENTS.md` so other machines inherit the strongest available session-wide KB preflight and postflight rules, not only the implicit skill layer.
- The install check must expose a structured machine-install checklist that explicitly verifies the global skill files, implicit invocation, phase-change KB checkpoint wording, postflight reminder wording, mistake-first highest-priority postflight wording, skill/plugin and subagent/delegation signal wording, managed global AGENTS block, repo-managed maintenance/organization/update skills, all repo-managed automations, and the final `strong_session_defaults` readiness signal.

## Start here

- Read `PROJECT_SPEC.md` before making architectural changes.
- Treat `PROJECT_SPEC.md` as the authoritative v0.1 design brief.
- Keep `AGENTS.md` short; put detailed design rationale in `PROJECT_SPEC.md`.

## Purpose

This repository stores a local predictive knowledge library that Codex can consult before solving tasks.

## GitHub publish default

- When the user asks to update or sync GitHub for this repository, default to a **release audit** first, not to an automatic version bump.
- Inspect `VERSION`, visible README versioning, git tags, GitHub Release state, and the commit currently targeted by the latest tag together before publishing.
- Only create a new version when there is a **release-worthy public delta** since the last tagged commit. Do not mint a new version for history-only KB changes, private-card churn, release-note wording edits, or other same-commit repair work.
- If an existing tag or Release already points at the intended source commit, repair or reuse that release state instead of creating another version number for the same commit.
- Create the release commit first, then create the tag, then verify the tag target, then push branch and tag, then create or update the GitHub Release. Do not create the commit and tag in parallel.
- Do not move an existing tag unless the user explicitly asks for it.
- Keep detailed release rules in `docs/release_policy.md`.

## How to use the library

- Run `python scripts/install_codex_kb.py` once per machine to install the global Codex preflight skill and launcher.
- When the task is machine setup for this system, do not wait for extra confirmation or extra explanation. Run the installer and check commands as the default bootstrap path.
- When a task may depend on user preference, recurring workflow, domain heuristics, or prior lessons, invoke `$local-kb-retrieve` first.
- For long mixed tasks, rerun retrieval at phase-change KB checkpoints before substantially different work begins, such as switching from analysis to code edits, packaging, privacy-sensitive handling, organization-KB work, automation changes, GitHub push/tag/release, or public publication. Do not rerun retrieval for repeated same-type subtasks.
- Infer a primary conceptual route before retrieval. Do not rely on flat keywords alone when a route is apparent.
- Treat KB entries as bounded context, not unquestionable truth.
- Prefer entries with `status: trusted`.
- If an entry conflicts with direct user instructions in the current conversation, follow the current user instruction.

## Update rules

- Do not write directly into `kb/public/` or `kb/private/` from an active task thread.
- In the current implementation, new lessons should normally land in `kb/candidates/` or structured history first. Treat trusted-scope rewrites and promotions as maintenance work, not as default inline edits.
- New lessons should first be proposed into `kb/candidates/`.
- Keep private data out of commits unless the user explicitly wants it versioned.
- Do not add embeddings, vector databases, MCP services, or subagent orchestration in v0.1 unless explicitly requested.

## Validation

- Before changing retrieval logic, run a quick manual search test.
- Keep the skill description narrow so it does not trigger on trivial tasks.
- Keep scoring logic explainable and easy to inspect.

<!-- BEGIN MANAGED SKILLGUARD PROJECT RULES -->
## SkillGuard project maintenance

This repository contains skills maintained with SkillGuard. For non-trivial skill maintenance, validation, installation, synchronization, or release work, use SkillGuard by default.

Canonical SkillGuard repository: https://github.com/liuyingxuvka/SkillGuard

Managed skills:
- `.agents/skills/kb-dream-pass` — native owner=`kb-dream-pass`, route evidence=`.agents/skills/kb-dream-pass/SKILL.md`; the target skill keeps domain-route, judgment, action, and native-check authority.
- `.agents/skills/kb-organization-contribute` — native owner=`kb-organization-contribute`, route evidence=`.agents/skills/kb-organization-contribute/SKILL.md`; the target skill keeps domain-route, judgment, action, and native-check authority.
- `.agents/skills/kb-organization-maintenance` — native owner=`kb-organization-maintenance`, route evidence=`.agents/skills/kb-organization-maintenance/SKILL.md`; the target skill keeps domain-route, judgment, action, and native-check authority.
- `.agents/skills/kb-sleep-maintenance` — native owner=`kb-sleep-maintenance`, route evidence=`.agents/skills/kb-sleep-maintenance/SKILL.md`; the target skill keeps domain-route, judgment, action, and native-check authority.
- `.agents/skills/khaos-brain-update` — native owner=`khaos-brain-update`, route evidence=`.agents/skills/khaos-brain-update/SKILL.md`; the target skill keeps domain-route, judgment, action, and native-check authority.

Required maintenance handoff:

1. Read the target skill's `SKILL.md` and its native route/check contracts before editing.
2. Use SkillGuard to inventory, run every target-declared check, reconcile exact receipts, and close non-trivial skill changes.
3. Preserve the target's sole current native route and exact declared checks; SkillGuard never supplies a target-domain route.
4. Never let SkillGuard replace target-owned domain judgment, simulation, search, modeling, actions, or checks.
5. Do not claim complete use from contract presence alone; require a current declared-check execution receipt.
6. If SkillGuard is unavailable or this block/manifest is missing, stale, duplicated, or invalid, report the maintenance result as blocked instead of silently bypassing it.

Validation execution ownership:

- policy_id: `skillguard.validation_execution_ownership.current`
- Creating, updating, directly rewriting a non-current target, compiling its consumer projection, or releasing a maintained skill requires author-side SkillGuard maintenance supervision; no migration or compatibility route exists.
- Covered skill maintenance uses direct current replacement. Do not add a compatibility reader, fallback, migration or upgrade command, converter, alias, renewal path, dual manifest, or parallel authority. An ordinary software historical reader is allowed only when an explicit requirement names the old document/data/interface and FlowGuard records its bounded owner and claim boundary.
- Ordinary use of an already-installed skill for its domain work does not start SkillGuard maintenance or validation.
- SkillGuard supervises one source Skill at a time: its exact promises, target-owned checks, positive fixture, named shallow gap, affected-only revalidation, and clean consumer projection. The target Skill retains its domain actions, judgment, native-check authority, and runtime closure.
- Before multi-skill maintenance starts, freeze one task-level boundary plan in the existing verification contract or TestMesh: list each target as a separate single-member unit with its own exact checks, obligations, evidence domain, dependencies, and execution owner. Missing, duplicate, cyclic, or semantically overlapping ownership blocks execution.
- A receipt belongs only to the unit that produced it. Another Skill neither consumes nor projects that receipt as its own proof. If two units appear to need the same test or evidence, repair the ownership boundary instead of introducing receipt sharing.
- Compile the complete maintained inventory into exact content components before validation. A change invalidates only owners and projections that explicitly consume its changed component; an unmapped or ambiguous file blocks instead of falling back to run-all.
- Treat maintained test, code, contract, configuration, toolchain, and policy changes as freshness inputs only through those exact component edges. Reports, receipts, progress logs, checkboxes, and other runtime outputs are evidence outputs and must not refresh source authority or trigger their own validation.
- Installation consumes only the clean target-owned consumer projection. Source-only contracts, `.skillguard`, tests, fixtures, models, notes, author receipts, SkillGuard commands/imports, and router material never enter an installed Skill. Installed currentness is target-native and never calls SkillGuard.
- Treat `--resume` as an execution command that may run missing owners; it is never a read-only receipt audit, and a receipt consumer must not invoke it.
- A repository-level full regression may run once under one explicit aggregate owner after source and tool identities are frozen. Its result is repository evidence only; it does not replace or get shared as any target Skill's native proof.
- After any launcher timeout, cancellation, or interruption, confirm the entire descendant process tree count is zero before accepting evidence or starting another owner; `cleanup-unconfirmed` results are invalid and non-reusable.
- Never use a Windows Scheduled Task, background resume, or unattended retry script to run full validation or resume a mutable worktree.

Portable audit command: `python <installed-skillguard>/scripts/skillguard.py project-audit --root .`

This managed block is a routing and maintenance contract. It is not runtime, test, release, or future-behavior proof.
<!-- END MANAGED SKILLGUARD PROJECT RULES -->


<!-- BEGIN FLOWGUARD PROJECT RULES -->

<!-- flowguard-rule:project.scope -->

## FlowGuard Project Rules

This project uses FlowGuard for non-trivial maintenance, feature work, bug
fixes, refactors, tests, release work, project upgrades, and evidence-sensitive
process changes.

<!-- flowguard-rule:project.repository -->

FlowGuard repository:
https://github.com/liuyingxuvka/FlowGuard

<!-- flowguard-rule:skill_suite.agent_surface -->

FlowGuard agent skill suite:
- Primary agent surface: the current clean consumer projection under
  `$CODEX_HOME/skills/`; default entry is
  `$CODEX_HOME/skills/flowguard/SKILL.md`.
- A project reads this block plus selected sibling guidance; it does not copy the FlowGuard suite into its local tree.
- The Python package/CLI is executable check support, not the AI-agent skill installation surface.

<!-- flowguard-rule:project.record_locations -->

Project FlowGuard record:
- Manifest: `.flowguard/project.toml`
- Machine log: `.flowguard/adoption_log.jsonl`
- Human log: `docs/flowguard_adoption_log.md`

<!-- flowguard-rule:project.rendered_versions -->

Current adoption record:
- FlowGuard check-engine version: `0.68.0`
- FlowGuard schema version: `1.0`

<!-- flowguard-rule:project.preflight_version_gate -->

Before non-trivial work, verify the real engine/schema/version and run
`python -m flowguard project-audit --root .`. Compare it with `.flowguard/project.toml`.
If installed is newer, run `project-upgrade` with artifact/model/test upgrade scanning
and revalidate affected evidence; if installed is older, connect the current
engine before claiming confidence.

<!-- flowguard-rule:runtime.latest_schema_first -->

FlowGuard runtime guidance is latest-schema-first: old artifacts may be
detected and upgraded at project/tool boundaries, but normal route logic should
not keep long-lived old branches for obsolete fields, aliases, or wrappers.

<!-- flowguard-rule:model_system.authority -->

Only the content-addressed `observed_implementation` snapshot selected by
the sole project head is current. Targets/experiments stay isolated; discovery
or green candidate checks grant no authority. Missing/invalid authority or
required coverage blocks broad confidence.

<!-- flowguard-rule:model_system.revision_transaction -->

Replace model authority only through one accepted `ModelRevisionSet` bound
to the exact base, candidate, affected closure, changes, and current owner
evidence. Persist records before the pointer. Rollback restores/compensates real
effects and revalidates the old snapshot; irreversible effects use forward repair.

<!-- flowguard-rule:lifecycle.default_replacement -->

Default replacement means dispose the old path, old field, alias, wrapper, or
alternate success path. Delete, block, migrate, delegate, repair, replace, or
scope it out with a concrete reason; do not leave it as a second successful
route.

<!-- flowguard-rule:behavior.commitment_ledger -->

Broad behavior claims use BehaviorCommitmentLedger: independently inventory
admitted external promises, give each source one modeled/delegated/scoped
disposition, one plane/actor and one primary model owner, and send
`path_sensitive=true` rows to Primary Path Authority. Helpers are not
automatically commitments.

<!-- flowguard-rule:behavior.plane_partitioning -->

Classify each commitment as `product_runtime`, `agent_operation`, or
`development_process`. A lightweight existing-model/commitment lookup selects
a bounded same-plane owner closure; typed related-plane context never transfers
ownership. Model Miss creates a gap only when that plane has no matching promise.

<!-- flowguard-rule:behavior.commitment_ledger_modes -->

Declare ledger mode before coverage work. Only `bootstrap_ledger` and
`coverage_gap_backfill` use broad history discovery; add/change/remove/miss
work stays on the affected commitment, owner, cases, and evidence closure.

<!-- flowguard-rule:lifecycle.field_mesh -->

Field-bearing work uses FieldLifecycleMesh. High-level models keep
behavior-bearing fields; leaf inventory accounts every field's owner,
readers/writers, projection, lifecycle, evidence, and old-field disposition.

<!-- flowguard-rule:evidence.ui_and_payload -->

UI runnable claims and file/work-package claims need current UI click-through
or artifact-payload evidence gates before broad done/release confidence.

<!-- flowguard-rule:behavior.primary_path_authority -->

Path-sensitive commitments need one Primary Path Authority, visible primary
failure, no automatic alternate success, and current exhaustion/test/risk evidence.

<!-- flowguard-rule:behavior.exact_intent_reuse -->

One exact user purpose has one intent, active commitment, and primary path.
Equivalent UI/API/CLI/adapter/wrapper surfaces delegate; they do not become
independent success implementations.

<!-- flowguard-rule:ui.product_language -->

UI Flow Structure owns product-wide language and complete rendered-surface
coverage. Full UI claims inventory every control, display, transition, overlay,
recovery path, and blindspot with stable identity, evidence, and disposition.

<!-- flowguard-rule:ui.content_admission -->

Classify UI content once as `user_visible`, `user_on_demand`, or `internal`.
On-demand needs reveal/return; internal diagnostics and routing stay hidden.

<!-- flowguard-rule:process.development_process_flow -->

Plans, staged/multi-skill work, sync, release, publish, and final process
claims enter `flowguard-development-process-flow`. It owns order/freshness,
preserves peer writes, delegates semantics, uses affected revalidation, and
reserves one full gate for frozen source. Conditional strategy selection runs
only for its declared triggers; progress is never completion evidence.

<!-- flowguard-rule:process.work_context_read_only -->

External specs/plans enter only through explicit project-bounded read-only
WorkContexts. Providers keep ownership; FlowGuard preserves identities,
fingerprints, and lanes, rejects fallback/write/execution authority, and admits
behavior sources only through explicit mappings. Zero providers is valid.

<!-- flowguard-rule:process.post_change_scan -->

After non-trivial work, let DevelopmentProcessFlow consume post-change scan signals:
changed artifacts, skips, stale evidence, open obligations, and split/reduction
pressure. Route each gap to its existing specialist owner.

<!-- flowguard-rule:claim.no_fake_adoption -->

Do not create a fake local FlowGuard replacement. Do not claim full FlowGuard
completion from an AGENTS/manifest/log update alone; executable model checks,
tests, replay, and closure evidence still need to be current for the claim.
Before model build/change, freeze this instance's task-specific failures and
boundary, then bind candidate plus native good/bad-per-failure/oracle/current
evidence. Reusable types are not fixed-purpose; no mode/fallback exists; only
FlowGuard-declared checks support completion claims.

<!-- END FLOWGUARD PROJECT RULES -->

<!-- BEGIN MANAGED SKILLGUARD AUTHOR RULES -->
## SkillGuard author maintenance

This repository is an explicit skill-authoring workspace. Use SkillGuard only while maintaining, validating, graduating, or releasing the managed source skills below.

Canonical SkillGuard repository: https://github.com/liuyingxuvka/SkillGuard

Managed skills:
- `.agents/skills/kb-dream-pass` — native owner=`kb-dream-pass`, maintenance unit=`unit:kb-dream-pass`, route evidence=`.agents/skills/kb-dream-pass/SKILL.md`; the target skill keeps domain-route, judgment, action, and native-check authority.
- `.agents/skills/kb-organization-contribute` — native owner=`kb-organization-contribute`, maintenance unit=`unit:kb-organization-contribute`, route evidence=`.agents/skills/kb-organization-contribute/SKILL.md`; the target skill keeps domain-route, judgment, action, and native-check authority.
- `.agents/skills/kb-organization-maintenance` — native owner=`kb-organization-maintenance`, maintenance unit=`unit:kb-organization-maintenance`, route evidence=`.agents/skills/kb-organization-maintenance/SKILL.md`; the target skill keeps domain-route, judgment, action, and native-check authority.
- `.agents/skills/kb-sleep-maintenance` — native owner=`kb-sleep-maintenance`, maintenance unit=`unit:kb-sleep-maintenance`, route evidence=`.agents/skills/kb-sleep-maintenance/SKILL.md`; the target skill keeps domain-route, judgment, action, and native-check authority.
- `.agents/skills/khaos-brain-update` — native owner=`khaos-brain-update`, maintenance unit=`unit:khaos-brain-update`, route evidence=`.agents/skills/khaos-brain-update/SKILL.md`; the target skill keeps domain-route, judgment, action, and native-check authority.

Required maintenance handoff:

1. Read the target skill's `SKILL.md` and its native route/check contracts before editing.
2. Use SkillGuard to inventory, run every target-declared check, reconcile exact receipts, and close non-trivial skill changes.
3. Preserve the target's sole current native route and exact declared checks; SkillGuard never supplies a target-domain route.
4. Never let SkillGuard replace target-owned domain judgment, simulation, search, modeling, actions, or checks.
5. Do not claim complete use from contract presence alone; require a current declared-check execution receipt.
6. Never copy this block, the author manifest, contracts, receipts, router state, or Portfolio state into a graduated consumer skill or an ordinary business project.
7. If SkillGuard is unavailable or this block/manifest is missing, stale, duplicated, or invalid, report only author maintenance as blocked; ordinary consumer use remains independent.

Validation execution ownership:

- policy_id: `skillguard.validation_execution_ownership.current`
- Creating, updating, directly rewriting, installing/synchronizing, or releasing an explicitly registered maintained skill source requires SkillGuard author-side supervision; no migration or compatibility route exists.
- Covered skill maintenance uses direct current replacement. Do not add a compatibility reader, fallback, migration or upgrade command, converter, alias, renewal path, dual manifest, or parallel authority. An ordinary software historical reader is allowed only when an explicit requirement names the old document/data/interface and FlowGuard records its bounded owner and claim boundary.
- Ordinary use of an installed consumer skill for its domain work does not start SkillGuard maintenance or validation and must not require SkillGuard files, imports, commands, receipts, or router state.
- SkillGuard supervises the author-side frozen owner plan, receipts, affected-only revalidation, clean consumer projection, and closure; the target skill retains its domain actions, judgment, and native-check authority.
- Before validating one maintenance unit, freeze its unit id, member ids, exact semantic checks, evidence subjects, covered obligations/domains, dependency order, private receipt root, and exactly one execution owner per check; missing, duplicate, foreign-unit, or cyclic ownership blocks execution.
- Reuse one immutable terminal-success producer receipt only inside the same maintenance unit when unit, member, explicitly declared owner, request, inputs, dependencies, toolchain, and environment are all exact. Each semantic check keeps its own subject, domain, obligations, and projection identity. A different unit must execute and own its own evidence even when command text and inputs look identical.
- Consumer distributions contain no SkillGuard receipt reference or execution-owner projection. They run their target-owned checks directly when their own workflow requires them.
- Compile the complete maintained inventory into exact content components before validation. A change invalidates only owners and projections that explicitly consume its changed component; an unmapped or ambiguous file blocks instead of falling back to run-all.
- Treat maintained test, code, contract, configuration, toolchain, and policy changes as freshness inputs only through those exact component edges. Reports, receipts, progress logs, checkboxes, and other runtime outputs are evidence outputs and must not refresh source authority or trigger their own validation.
- Installation consumes only the frozen `projection:installation`; source-only tests, fixtures, models, and notes do not make an installation stale. A read-only installation currentness check never launches smoke or another validation owner.
- Treat `--resume` as an execution command that may run missing owners; it is never a read-only receipt audit, and a receipt consumer must not invoke it.
- Start exactly one final full validation for the maintenance unit only after its source, toolchain, and impact-plan identities are frozen, under one explicit execution owner. Other maintenance units and consumers do not consume that parent receipt.
- After any launcher timeout, cancellation, or interruption, confirm the entire descendant process tree count is zero before accepting evidence or starting another owner; `cleanup-unconfirmed` results are invalid and non-reusable.
- Never use a Windows Scheduled Task, background resume, or unattended retry script to run full validation or resume a mutable worktree.

Author audit command: `python <installed-skillguard>/scripts/skillguard.py maintainer-audit --root .`

This managed block is a routing and maintenance contract. It is not runtime, test, release, or future-behavior proof.
<!-- END MANAGED SKILLGUARD AUTHOR RULES -->
