## Context

The current source-sync helper calls a dirty-state gate before fetch/pull and returns a generic failure. The cycle then passes the maintenance source to contribution through a pinned sync context, so the effective worktree must live until both child phases finish.

## Goals / Non-Goals

**Goals:**

- Preserve the configured mirror as an untouched user/parallel-agent checkout.
- Provide one effective source path to maintenance and contribution.
- Bind worktree preparation and cleanup to the existing immutable cycle and native receipts.
- Keep the clean-mirror fast path and current GitHub/organization gates.

**Non-Goals:**

- Do not restore, stage, commit, or publish unrelated assets.
- Do not redesign organization card policy, snapshot adoption, or local Sleep ownership.
- Do not add a second organization source authority or fallback reader.

## Decisions

1. **Create a per-run worktree from the configured mirror's committed HEAD.** This is local, deterministic, and preserves the exact remote/source identity without copying the dirty working tree. A clone fallback is not added; inability to create the worktree is a visible failure.
2. **Carry an explicit `worktree` record in the sync context.** The maintenance phase returns the effective source and worktree record; the contribution phase reuses it rather than syncing a second path.
3. **Defer cleanup to the cycle owner.** The composite cycle removes a disposable worktree only after contribution and postflight. A standalone maintenance call cleans up only after its own postflight; failures retain the path for evidence.
4. **Keep Git gate semantics on the effective worktree.** The existing base-branch, manifest, exact changed-file, push, and merge-readiness checks remain the native owners.

## Risks / Trade-offs

- [Risk] A failed run leaves disposable worktrees on disk. → Record an explicit retention reason and expose a later maintenance cleanup action; never delete before the receipt is durable.
- [Risk] A source mirror's HEAD can be behind its remote. → Fetch/pull the clean worktree before validation and record both source-base and effective HEAD.
- [Risk] Worktree creation is unavailable on a non-Git source. → Preserve the existing non-Git validation path and fail only when a dirty Git checkout cannot be isolated.

## Migration Plan

1. Add preparation/cleanup helpers and sync-context fields.
2. Route both organization child facades through the same effective worktree.
3. Add dirty-mirror, clean-fast-path, failure-retention, and cycle-reuse tests.
4. Run the top-level organization wrapper once after task acceptance and inspect the immutable receipt.

