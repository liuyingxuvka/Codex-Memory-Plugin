## Purpose

This capability keeps organization maintenance and contribution operational when the configured mirror contains unrelated parallel edits, while preserving the mirror as user-owned work and recording exact source and cleanup evidence.

## ADDED Requirements

### Requirement: Organization maintenance SHALL select an isolated clean worktree

When the validated organization source is a Git checkout, the maintenance cycle MUST execute all source synchronization, schema validation, card maintenance, contribution, commit, push, and merge-readiness operations in a clean worktree. A dirty configured mirror MUST NOT be overwritten, reset, checked out, or silently treated as a clean source.

#### Scenario: Configured mirror is dirty with an unrelated tracked edit
- **WHEN** the organization settings are validated and the configured mirror has a tracked change outside the organization KB lanes
- **THEN** the cycle creates a clean per-run worktree from the mirror's current committed base, runs the cycle there, and leaves the configured mirror's status and bytes unchanged

#### Scenario: Configured mirror is already clean
- **WHEN** the validated mirror is a clean checkout on the requested base branch
- **THEN** the cycle MAY use that checkout as its source fast path, but records the same source commit, branch, dirty-state, and worktree identity fields as the isolated path

#### Scenario: Configured mirror cannot provide a clean base
- **WHEN** the configured path is missing, not a Git checkout, or cannot create a clean worktree
- **THEN** the cycle fails visibly with a typed source-preparation error and does not mutate organization cards, imports, branches, or the configured mirror

### Requirement: Worktree lifecycle and Git identity SHALL be receipt-bound

The terminal native receipt MUST identify the configured mirror path, effective worktree path, source HEAD, base branch, worktree HEAD, dirty-state observation, cleanup disposition, and whether every descendant process and worktree operation was confirmed. A successfully completed disposable worktree MUST be removed only after all child phases and postflight evidence are durable; a failed or interrupted worktree MUST remain discoverable for recovery.

#### Scenario: Isolated cycle completes without changes
- **WHEN** maintenance and contribution finish with an exact no-change decision set
- **THEN** the receipt is successful, the disposable worktree cleanup is confirmed, no branch or PR is manufactured, and the configured mirror remains unchanged

#### Scenario: Isolated cycle fails after creating a worktree
- **WHEN** a sync, schema, card decision, push, or postflight check fails
- **THEN** the receipt is failed or blocked, records the worktree path and failure boundary, and does not claim cleanup or reuse the failed worktree as a successful source

### Requirement: Organization exchange boundaries SHALL remain unchanged by isolation

Worktree isolation MUST preserve the organization repository's manifest, `kb/main`, `kb/imports`, LogicGuard bundle, Skill registry, privacy, exact-action, and GitHub readiness gates. It MUST NOT copy assets or adopt organization cards into local Sleep authority merely because they are present in the worktree.

#### Scenario: Organization contains non-semantic asset changes
- **WHEN** a README or image asset is changed in the configured mirror but no organization KB lane is changed
- **THEN** the cycle ignores the asset for card decisions, does not restore or publish it, and still validates the organization KB surface in the clean worktree
