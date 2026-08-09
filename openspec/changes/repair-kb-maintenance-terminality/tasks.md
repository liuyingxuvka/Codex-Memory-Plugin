## 1. Baseline and authority

- [ ] 1.1 Create an isolated implementation worktree from the selected current source and record branch, source SHA, v0.8.3 tag/release SHA, peer-owned dirty-file hashes, installed projection hashes, automation TOML hashes, current index/authority generations, and the two failed run IDs.
- [ ] 1.2 Run FlowGuard model-system audit, existing-model preflight, and affected commitment lookup; record the blocked authority fingerprints and bind the repair to the existing maintenance/lifecycle owners without creating a duplicate public path.
- [ ] 1.3 Reconcile the existing OpenSpec completed changes and write a typed drift note for the missing terminal/recovery evidence; keep historical changes immutable and use this change as the current implementation owner.

## 2. Supervised ownership and terminal states

- [ ] 2.1 Add a single owner identity record containing run ID, command fingerprint, PID/start time, process-group or Job Object identity, source/tool/schema identity, and predecessor authority.
- [ ] 2.2 Implement Windows descendant-tree supervision with a Job Object or equivalent owner-loss cleanup, plus explicit `interrupted`, `failed`, and `cleanup_unconfirmed` terminal receipts.
- [ ] 2.3 Enforce host timeout greater than owner timeout greater than native timeout, and expose the persisted values through canonical JSON and install checks.
- [ ] 2.4 Add exact recovery guards for live owner, mismatched run ID, PID reuse, missing process start time, and nonzero descendant count.
- [ ] 2.5 Add focused process-control tests for external wrapper termination, child/grandchild cleanup, terminal disconnect, recovery refusal, and idempotent cleanup.

## 3. Resumable deadlines and frozen plans

- [ ] 3.1 Implement a shared deadline context for soft, stall, native, owner, host, commit, Dream/contribution, receipt, and cleanup budgets.
- [ ] 3.2 Check the deadline before/after every item and every post-item phase, including model staging, index staging, Dream admission, contribution admission, and terminal receipt construction.
- [ ] 3.3 Persist Sleep frozen batch plans, per-item checkpoints, `progress_saved`, and settled-but-unpublished recovery state.
- [ ] 3.4 Persist Organization frozen candidate/phase plans, 11 checkpoint identities, deferred arrivals, and exact action packet status.
- [ ] 3.5 Add deadline and recovery tests for soft stop, no-progress stall, final-item boundary, post-processing boundary, resume, and duplicate action prevention.

## 4. Atomic generation publication

- [ ] 4.1 Stage model, mesh, projection, active index, lifecycle acknowledgements, watermark, and manifest as one content-addressed candidate generation.
- [ ] 4.2 Validate candidates directly by explicit generation identity without switching the current pointer first.
- [ ] 4.3 Implement one fenced compare-and-swap that activates the aggregate pointer last and binds all component digests.
- [ ] 4.4 Add operation journaling and idempotent recovery for crashes before pointer CAS and after pointer CAS.
- [ ] 4.5 Repair settled-but-unpublished Sleep batches through the operation journal instead of creating replacement batches.
- [ ] 4.6 Add crash injection after every staging, pointer, projection, receipt, and watermark barrier; assert readers see only complete old/new generations.

## 5. Short writer window and contention

- [ ] 5.1 Move scanning, AI review, network access, model generation, similarity work, and large serialization outside the global writer.
- [ ] 5.2 Keep the writer window limited to predecessor/fence validation, bounded CAS commit, and immediate release.
- [ ] 5.3 Add fencing epoch/predecessor digest checks and typed CAS-conflict reopen conditions.
- [ ] 5.4 Add Sleep/Organization concurrent planning and serialized commit tests, including a stuck reader/analysis phase.

## 6. Compact evidence and payload contracts

- [ ] 6.1 Split complete stdout/stderr, gap ledgers, diagnostics, and Dream fingerprints into immutable content-addressed sidecars.
- [ ] 6.2 Reduce native and cycle receipts to schema/run/status/counts/fingerprint envelopes with sidecar references and bounded captured diagnostics.
- [ ] 6.3 Add payload tests for valid, missing, empty, unknown member, wrong type, stale schema, path mismatch, digest mismatch, partial write, and producer/consumer mismatch.
- [ ] 6.4 Add receipt scaling fixtures and enforce bounded envelope size/parse/hash budgets without introducing legacy readers.

## 7. Organization editorial and Skill safety

- [ ] 7.1 Build the frozen Organization candidate packet containing source/catalog/card/import/LogicGuard/Skill/guidance identities and exact candidate IDs.
- [ ] 7.2 Route the packet through pinned `gpt-5.6-luna` with `reasoning_effort=max` and define the typed decision schema; record provider/model/reasoning and input/output digests.
- [ ] 7.3 Implement deterministic decision validation for completeness, action IDs, evidence binding, privacy boundaries, reversible merge/split packets, and source drift.
- [ ] 7.4 Implement card-bound Skill grouping by bundle ID, original-author validation, SHA-256 content hash, version time, fork classification, and latest-approved selection.
- [ ] 7.5 Apply only exact selected packet IDs and add idempotent rollback/post-apply checks; keep no-change runs branch/PR-free.
- [ ] 7.6 Add nonempty import, duplicate, merge, split, privacy, Skill fork, guidance-unavailable, model-failure, and snapshot-CAS fixtures.

## 8. FlowGuard/OpenSpec/SkillGuard evidence

- [ ] 8.1 Build/update the FlowGuard model for owner lifecycle, deadline branches, pointer-last publication, recovery, contention, and Organization editorial review.
- [ ] 8.2 Run model-test alignment for every transition and payload obligation, with one primary contract, positive evidence, per-failure evidence, oracle, and replay evidence.
- [ ] 8.3 Repair the current ModelRevisionSet against the live source only after runtime changes stabilize; activate it by CAS and rerun affected FlowGuard checks.
- [ ] 8.4 Add `python -m flowguard project-audit --root . --json` as a GitHub CI gate and add a stale-authority negative test.
- [ ] 8.5 If managed Skill sources change, freeze each SkillGuard maintenance unit separately, run every declared native check once, audit clean consumer projections, and do not share receipts across units.
- [ ] 8.6 Validate this OpenSpec change strictly and keep every completed task backed by current evidence rather than a historical checkbox.

## 9. Verification, installation, and real maintenance acceptance

- [ ] 9.1 Run affected unit, process-control, crash-matrix, contention, payload, scale, and Organization semantic tests; fix failures before the next gate.
- [ ] 9.2 Freeze source/toolchain/impact identities and run exactly one explicit full repository validation owner; confirm zero descendants before accepting its receipt.
- [ ] 9.3 Run `python scripts/install_codex_kb.py --json` and `python scripts/install_codex_kb.py --check --json`; read back both persisted automation TOMLs and verify ACTIVE/Luna/max parity.
- [ ] 9.4 Use the exact recovery path to settle the named 2026-08-09 interrupted Sleep state without fabricating success or manually deleting locks.
- [ ] 9.5 Run exactly one top-level Sleep wrapper with a host timeout greater than the owner timeout and wait for its original execution identity to reach terminal status.
- [ ] 9.6 Verify Sleep publication, Dream read-only completion, pointer/index/watermark identity, frozen decisions, cleanup evidence, and postflight.
- [ ] 9.7 After Sleep reaches valid terminal success, run exactly one top-level Organization wrapper and verify all required checkpoints, contribution/snapshot, Skill/privacy decisions, post-apply state, GitHub readiness, cleanup, and postflight.

## 10. Release and handoff

- [ ] 10.1 Run release audit across VERSION, README, main SHA, tags, GitHub Release, installed projection, and the two real maintenance receipts.
- [ ] 10.2 Bump only the patch component to v0.8.4, create the release commit, push branch, merge with all CI gates, and verify the exact main SHA.
- [ ] 10.3 Create and push the v0.8.4 tag at the verified main SHA, wait for tag CI, and create/update the GitHub Release without moving v0.8.3.
- [ ] 10.4 Run final KB postflight with one durable event ID, record the interruption/atomic-publication lesson, and report source/install/model/Git/tag/release identities separately.
