## Why

The organization maintenance wrapper currently treats the configured mirror as its mutable checkout and fails closed whenever any unrelated tracked file is dirty. A parallel agent's intentional `assets/readme-hero/hero.png` deletion therefore prevents the shared-card exchange cycle even though that asset is outside the organization KB contract. Maintenance needs a clean, disposable worktree that preserves the configured mirror and leaves unrelated parallel edits untouched.

## What Changes

- Create a per-cycle clean Git worktree from the configured organization mirror when the mirror is dirty.
- Run fetch, validation, maintenance, contribution, commit, push, and merge-readiness checks in that isolated worktree.
- Keep the configured mirror and its dirty files unchanged; record the source mirror, worktree path, cleanup state, and exact Git identities in the receipt.
- Remove only a successfully completed disposable worktree; retain a failed worktree for evidence and recovery.
- Treat a clean configured mirror as an eligible fast path while preserving the same receipt fields.

## Capabilities

### New Capabilities

- `organization-maintenance-worktree-isolation`: Isolate organization maintenance from unrelated local checkout changes while preserving exact Git and receipt ownership.

### Modified Capabilities

None.

## Impact

Affected code includes `local_kb/org_sources.py`, `local_kb/org_automation.py`, `local_kb/org_cycle.py`, organization automation receipts, and organization-maintenance tests. The configured desktop settings path remains the user's source mirror; no organization card is adopted into local truth.
