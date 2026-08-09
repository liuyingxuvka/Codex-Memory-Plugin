## Purpose

This capability provides a safe, deterministic rehearsal of the organization-maintenance AI workflow so release decisions use evidence from the real maintenance and contribution facades without touching the configured mirror, remote repository, local authority, or installed Skills.

## ADDED Requirements

### Requirement: The rehearsal SHALL execute the real organization workflow in an isolated disposable source

The rehearsal MUST construct or select a disposable organization checkout, make any synthetic dirty asset explicit, and run the current organization maintenance and contribution owners through one pinned source context. It MUST NOT invoke the scheduled automation wrapper, push, open or mutate a remote pull request, install a Skill, or publish local LogicGuard authority.

#### Scenario: Dirty mirror with deep bundle paths
- **WHEN** the rehearsal source contains an unrelated dirty asset and a deeply nested current LogicGuard bundle path
- **THEN** source preparation succeeds in a clean disposable worktree, the dirty asset remains unchanged in the configured source, and no Windows path error is hidden or converted into a success fallback

#### Scenario: Clean or unavailable source
- **WHEN** the configured source is clean or no validated organization source is available
- **THEN** the rehearsal records the clean fast path or a typed no-op/blocker and never mutates a configured source or invents a production success receipt

### Requirement: The rehearsal SHALL expose and validate every organization maintenance checkpoint

The terminal rehearsal report MUST carry complete, machine-evaluable results for settings participation, source/manifest/catalog validation, card-surface mapping, candidate intake, content-hash duplicate handling, merge decisions, split decisions, card decisions, Skill safety, Skill bundle version selection, exact selected apply, post-apply validation, snapshot compare-and-swap, contribution, GitHub merge readiness, and postflight. A checkpoint with no applicable items MUST still be represented as a complete zero-count result.

#### Scenario: No-change organization exchange
- **WHEN** the real facades find no selected action after reviewing all current main cards, imports, and Skill registry entries
- **THEN** the rehearsal succeeds with typed keep/empty decisions, an exact empty selected/apply set, a valid reused-or-new immutable snapshot, no manufactured branch/PR, and explicit not-applicable merge readiness

#### Scenario: Reviewed changes are selected
- **WHEN** the rehearsal selects one or more card, merge, split, or Skill actions
- **THEN** the report proves each selected packet id was applied exactly once, post-apply validation and rollback inventory passed, the effective source returned to its base state, and branch/PR/push evidence is present or explicitly blocked by the requested no-remote mode

### Requirement: Release readiness SHALL consume a successful rehearsal without treating it as a production run

The release process MUST require a current successful rehearsal report whose source, toolchain, checkpoint inventory, and repository identities match the pending release. The rehearsal MUST remain distinct from the native scheduled wrapper receipt; a rehearsal alone MUST NOT claim that the scheduled organization automation completed.

#### Scenario: Rehearsal failure
- **WHEN** any required checkpoint is missing, incomplete, inconsistent, or leaves a descendant worktree/process unconfirmed
- **THEN** release readiness is blocked with the exact failing checkpoint and executable repair condition, and no new tag, GitHub release, or push is performed

#### Scenario: Rehearsal success
- **WHEN** all required checkpoint results and immutable sandbox cleanup evidence are current and valid
- **THEN** the release gate may proceed to normal frozen-source validation while preserving the old release tag and keeping the scheduled wrapper as a separate future execution claim
