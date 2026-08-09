## Context

The native organization owners already separate settings, source sync, maintenance, contribution, snapshot, and receipt concerns. The prior failure occurred before those owners could run because a dirty configured mirror was used as the checkout and Git could not materialize a deeply nested bundle path. Existing focused tests cover individual contracts, while the formal two-maintenance FlowGuard model explicitly leaves native child lifecycle and Git receipts to their own evidence. The rehearsal therefore needs to compose the existing facades in a disposable machine/source pair and validate the native payload rather than creating a second maintenance implementation.

## Goals / Non-Goals

**Goals:**

- Exercise the real maintenance/contribution cycle with an isolated dirty source and representative decision data.
- Make every required checkpoint explicit, including zero-item checkpoints, so a lower-capability model can inspect one compact result.
- Keep source, remote, local LogicGuard authority, installed Skills, and scheduled-run receipts outside the mutation boundary.
- Bind rehearsal success to source/toolchain/checkpoint identities for a later release gate.

**Non-Goals:**

- Do not add a production fallback for a failed scheduled run or change the exact-once wrapper contract.
- Do not replace organization Sleep judgment, contribution policy, organization-review guidance, or native GitHub checks.
- Do not publish a release, move an existing tag, or claim scheduled-run completion from rehearsal evidence.

## Decisions

1. **Use the real cycle facade with a disposable machine and source.** The rehearsal will create a local clone/fixture from the configured organization source, introduce only a synthetic unrelated asset edit, and invoke `run_organization_cycle(..., push=False)` once. This preserves the actual phase ordering and writer/lease behavior while making remote mutation impossible. A hand-written mock workflow was rejected because it would not catch the prior worktree/path failure.

2. **Add named checkpoint projections to the native maintenance report.** The existing proposal/check logic already computes most facts, but several were only implicit in counts or action types. The report will project card-surface, candidate-intake, content-hash, split, Skill-version, exact-apply, and post-apply results with `complete`, counts, ids, and errors. Zero-item cases use explicit complete empty arrays rather than omitted fields.

3. **Validate semantics at the rehearsal boundary.** The rehearsal runner will check settings admission, source preservation, worktree isolation/cleanup, manifest/catalog identity, every checkpoint, snapshot validity, contribution reuse, and postflight. It will return a structured failed envelope naming the first failing checkpoint and repair condition; it will not write a release receipt or retry a failed native wrapper.

4. **Keep formal model and native receipts separate.** The existing FlowGuard two-maintenance model remains the process/state oracle, while native cycle receipts remain the source of Git, snapshot, and postflight evidence. The rehearsal report records both identities but never aliases one as the other.

## Risks / Trade-offs

- [Risk] A disposable clone can drift from the configured source while the rehearsal runs. → Record source HEAD/catalog/toolchain fingerprints before execution and fail if the post-run source identity differs.
- [Risk] Synthetic fixtures can omit a production edge. → Reuse current organization source data when available, retain focused native tests for merge/split/Skill/version/privacy cases, and require the real formal model to pass separately.
- [Risk] A no-change run could hide missing checks. → Require explicit complete zero-count checkpoint objects and validate their field shapes.
- [Risk] A failed rehearsal can leave a temporary worktree. → Retain it only for evidence during the run, verify cleanup/process termination, and report cleanup failure as a release blocker.

## Migration Plan

1. Add the checkpoint projections and deterministic rehearsal runner.
2. Add unit/integration tests for no-change, selected-action, dirty-asset, long-path, and missing-checkpoint failures.
3. Run focused tests, FlowGuard model/conformance checks, and the rehearsal against the current organization source without invoking the scheduled wrapper.
4. Install/check the current projections, freeze source/toolchain/rehearsal identities, then run the normal aggregate release gate. Only after all gates pass may a new patch release be prepared; the existing `v0.8.2` tag remains immutable.
