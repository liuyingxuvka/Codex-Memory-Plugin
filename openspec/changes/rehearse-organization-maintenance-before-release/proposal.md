## Why

The previous organization run failed before it reached any card decision because a dirty mirror exposed a Windows long-path checkout failure. A successful unit-test suite and a formal model are not enough to establish that the AI-facing organization workflow can actually traverse its settings, source, decision, snapshot, contribution, and merge-readiness boundaries. We need a safe, non-publishing rehearsal that runs the real facades against an isolated disposable source before any release claim.

## What Changes

- Add an explicit organization-maintenance rehearsal command that never invokes the scheduled wrapper, pushes, opens a PR, mutates the configured mirror, installs a Skill, or advances local authority.
- Build the rehearsal from a disposable organization checkout with an unrelated dirty asset and representative card/import/Skill cases, then run the real maintenance and contribution facades through one pinned sync context.
- Emit named checkpoint results for the card-surface map, candidate intake, content-hash duplicate handling, merge/split decisions, card decisions, Skill safety, Skill bundle version selection, exact apply, post-apply validation, snapshot CAS, contribution, and GitHub merge readiness.
- Fail the rehearsal when a required checkpoint is missing, incomplete, or inconsistent with the native receipt, and keep the configured mirror and remote state unchanged.
- Make the release process consume a current successful rehearsal result before a new patch release is prepared.

## Capabilities

### New Capabilities

- `organization-maintenance-rehearsal`: Deterministic, isolated AI-behavior rehearsal and checkpoint report for organization maintenance before release.

### Modified Capabilities

None. The rehearsal consumes the existing worktree-isolation contract as a test boundary; it does not change that capability's production semantics.

## Impact

Affected code includes a new simulation entry point, organization maintenance reporting/checkpoint assembly, focused integration tests, OpenSpec/FlowGuard evidence, and release-gate documentation. The production scheduled wrapper, configured organization mirror, GitHub repository, local LogicGuard authority, and installed Skill projections remain outside the rehearsal mutation boundary.
