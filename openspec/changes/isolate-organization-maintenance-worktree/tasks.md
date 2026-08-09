## 1. Source preparation

- [x] 1.1 Add a deterministic Git worktree-preparation helper that records configured mirror status, committed base, effective path, and failure reason without mutating the mirror.
- [x] 1.2 Make organization source sync use the helper before base-branch checkout, fetch, migration, and manifest validation; preserve the clean-mirror fast path.
- [x] 1.3 Carry the effective source and worktree record through the maintenance-to-contribution sync context.

## 2. Lifecycle and receipts

- [x] 2.1 Add cycle-owned cleanup that removes only a successful disposable worktree after contribution and postflight, and retains failed worktrees with an explicit reason.
- [x] 2.2 Add source/worktree/cleanup fields to native organization and composite-cycle receipts and keep exact GitHub readiness fields intact.
- [x] 2.3 Add tests for dirty mirror isolation, clean fast path, non-Git/missing-base failure, failed-worktree retention, and contribution reuse.

## 3. Acceptance

- [x] 3.1 Run organization automation contract and source-sync tests with a synthetic dirty asset edit.
- [x] 3.2 After all source, rehearsal, install, and FlowGuard gates are current, run the top-level organization wrapper exactly once and validate its immutable receipt, snapshot, postflight, cleanup/worktree registry, and Git state. Do not retry the old failed run or invoke the child entrypoint.

> The original wrapper run remains immutable as a failed preflight receipt (`Filename too long`). The repaired run used an isolated disposable worktree, completed all organization checkpoints, created and validated the snapshot, completed contribution/postflight, removed the worktree, and left the configured mirror's unrelated hero deletion untouched.
