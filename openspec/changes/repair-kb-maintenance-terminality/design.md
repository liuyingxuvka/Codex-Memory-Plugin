## Context

The scheduled Sleep and Organization owners are active with `gpt-5.6-luna` and `max` reasoning, but the outer caller can terminate a wrapper before its declared native/owner deadlines. The current Sleep publication can expose a new authority pointer before the matching active index is ready, and the global writer spans analysis and receipt construction. Organization is independent in policy but is blocked when the previous owner cannot prove descendant cleanup. Existing happy-path rehearsals do not cover interruption, contention, non-empty action branches, or current FlowGuard authority.

## Goals / Non-Goals

**Goals:**

- Make every interruption produce a visible, immutable terminal or `cleanup_unconfirmed` result tied to the original run identity.
- Make long work resumable without silently skipping settled-but-unpublished batches or duplicating action packets.
- Ensure readers see only a complete old or complete new generation, with pointer-last activation.
- Keep global writer ownership exclusive but short, fenced, and independent from long analysis.
- Keep hard safety ceilings while allowing adaptive batch sizing and sufficient outer-owner headroom.
- Make Organization editorial decisions reproducible, typed, privacy-safe, Skill-safe, and bound to a frozen packet and pinned Luna/max review.
- Produce compact terminal envelopes and separately verifiable immutable diagnostics.
- Preserve peer changes, synchronize the installed projections, and close a release gate for v0.8.4.

**Non-Goals:**

- Removing all time limits or allowing an unbounded scheduled process.
- Moving or rewriting the existing v0.8.3 tag or release.
- Making Hero or other unrelated assets part of Organization semantics.
- Adding legacy readers, aliases, dual writers, silent fallback, or compatibility success paths.
- Sharing SkillGuard receipts between maintenance units or making SkillGuard a runtime dependency.
- Running real maintenance wrappers concurrently or as unattended background retries.

## Decisions

### 1. One supervised owner per run

The wrapper records run identity before spawning its child and binds the process tree to a Windows Job Object or equivalent supervisor. The owner/host deadline is strictly greater than the native deadline and includes cleanup/receipt transport margin. An external interruption becomes `interrupted`, `failed`, or `cleanup_unconfirmed`; it is never inferred as success.

### 2. Resumable slices instead of infinite cycles

Soft deadlines stop admitting new work and persist a frozen checkpoint as `progress_saved`. Stall detection requires checkpoint progress, not heartbeat alone. The next scheduled owner resumes the same frozen plan and defers new arrivals. The recovery path explicitly handles a settled-but-unpublished batch.

### 3. Immutable staging and pointer-last CAS

Models, meshes, projections, index, lifecycle acknowledgements, watermark, and manifest are staged as one content-addressed generation. A validator checks the candidate directly. One fenced compare-and-swap activates the aggregate pointer last. Runtime projections and receipts are derived from that generation; they are not independent authority.

### 4. Short writer window

Scanning, AI review, network access, model construction, similarity work, and large artifact serialization occur outside the global writer. The writer is acquired only to revalidate the predecessor, perform the bounded CAS/commit, and release. A stale fencing token returns a typed blocked result with an executable reopen condition.

### 5. Compact immutable evidence

Complete streams and large diagnostics remain content-addressed sidecars. Native and cycle receipts contain only schema, run/source/tool identity, terminal state, counts, and sidecar references. No current reader depends on old receipt shapes.

### 6. Deterministic safety around Luna editorial review

Organization creates a frozen candidate packet, sends it to the pinned Luna/max provider for a typed review, then validates every decision against card hashes, LogicGuard bundles, privacy boundaries, Skill bundle author/version/hash rules, and exact action IDs. Model failure or drift fails closed; deterministic approval is not a fallback.

### 7. Evidence and release ordering

OpenSpec and FlowGuard authority are repaired after source changes stabilize. Affected checks run first; one final full owner runs after source/toolchain/impact identities freeze. Installation is verified separately from source, Git, tag, and GitHub Release identities. v0.8.4 is created only after real sequential Sleep/Dream and Organization wrapper receipts pass.

## Risks / Trade-offs

- [Longer wall-clock cycles] → Use frozen slices, adaptive batch sizing, and resume rather than removing hard ceilings.
- [More staging artifacts] → Content-address them, use compact receipts, and retain only receipt-covered derivations under the existing retention policy.
- [Provider/model drift] → Bind provider/model/reasoning and packet digests into the review receipt; reject drift.
- [Peer changes in the shared worktree] → Use an isolated implementation worktree and compare hashes before integration; never reset or overwrite peer paths.
- [FlowGuard repair invalidates old evidence] → Forward-build one current ModelRevisionSet and rerun only affected owners before the final gate.

## Migration Plan

1. Freeze the isolated worktree baseline and create the OpenSpec/FlowGuard implementation identities.
2. Implement owner supervision, typed interruption/recovery, pointer-last publication, short writer windows, compact receipts, and Organization checkpoints/review.
3. Recover the named 2026-08-09 interrupted state only through the new exact recovery path; never fabricate a success receipt.
4. Run affected tests, fault matrices, scale tests, FlowGuard/SkillGuard checks, and one frozen full gate.
5. Run the installer and install check, read back both automation TOMLs, then run one top-level Sleep wrapper and one top-level Organization wrapper sequentially.
6. Commit, merge, tag, push, and publish v0.8.4. If any gate fails, leave v0.8.3 untouched and record a typed blocker.
