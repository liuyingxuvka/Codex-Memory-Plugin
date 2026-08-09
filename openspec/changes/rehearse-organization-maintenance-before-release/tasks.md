## 1. Checkpoint projections

- [x] 1.1 Add explicit complete checkpoint payloads for card-surface mapping, candidate intake, content-hash duplicate decisions, merge decisions, split decisions, card decisions, Skill safety, Skill bundle version selection, exact selected apply, post-apply validation, and GitHub readiness; represent zero-item cases with empty typed lists.
- [x] 1.2 Bind the native maintenance terminal `ok` decision to the new checkpoint completeness and preserve the existing exact-once, snapshot, branch, and postflight gates.
- [x] 1.3 Add focused report tests for no-action, duplicate/import, merge/split, and card-bound Skill version/fork cases, including missing/incomplete checkpoint rejection.

## 2. Isolated AI-behavior rehearsal

- [x] 2.1 Add a deterministic rehearsal runner that creates a disposable machine/source pair, uses the real organization cycle with `push=False`, and never calls the scheduled wrapper or remote mutation path.
- [x] 2.2 Seed the disposable rehearsal with the configured source's unrelated dirty asset and deep current LogicGuard path; exercise representative import, duplicate/similar/overloaded-card, and card-bound Skill version/fork cases through isolated focused fixtures so the configured source and local authority remain untouched.
- [x] 2.3 Validate source identity preservation, worktree isolation and cleanup, manifest/catalog/bundle/Skill/privacy checks, all checkpoint payloads, snapshot CAS, contribution sync reuse, and postflight in one structured rehearsal envelope.
- [x] 2.4 Add failure fixtures for long-path checkout, missing checkpoint, selected/apply mismatch, stale snapshot, and unsafe privacy/Skill data; assert the exact repair condition and no release-side effect.

## 3. FlowGuard, install, and release gate

- [x] 3.1 Extend the affected organization FlowGuard/adoption evidence with the rehearsal boundary, native-vs-formal receipt separation, the observed long-path miss repair, and an identity-bound source/toolchain/checkpoint receipt; keep the FlowGuard current-authority migration as a separate prerequisite rather than hand-editing its artifacts.
- [x] 3.2 Run focused organization tests, the two-maintenance FlowGuard model/conformance checks, and the deterministic rehearsal against the current configured source; fix every failure before proceeding.
- [x] 3.3 Run installer and install-check synchronization for both Luna/max composite automations and the repository-managed maintenance Skills; verify clean installed state without changing peer work. The rehearsal CLI and its receipt verifier remain source-only repository tools and are not installed as a consumer Skill.
- [x] 3.4 Freeze source/toolchain/rehearsal identities, run the aggregate release gate, audit immutable `v0.8.2`, and only then prepare the next patch release if a public delta remains.

## 4. Release-evidence hardening before final freeze

- [x] 4.1 Record the configured organization source path, exact HEAD, branch/status, manifest/catalog digest, worktree registry, and local LogicGuard authority pointer/digest before and after rehearsal; fail closed on any unexpected change.
- [x] 4.2 Persist one immutable, content-addressed rehearsal receipt bound to the pending repository source fingerprint, runner hash, checkpoint inventory, Python/Git/FlowGuard identities, source commit, settings gate, all eleven checkpoints, snapshot, contribution, postflight, cleanup, and verified no-wrapper/no-push evidence.
- [x] 4.3 Make the readiness gate consume that receipt directly; missing, stale, `not_applicable`, mismatched, or hard-coded no-remote evidence must block release.
- [x] 4.4 Bind the native `skill-safety-version` obligation directly to both Skill safety and Skill bundle-version checkpoint payloads, including author lineage, hash/version-time, fork rejection, and latest-approved selection, with negative fixtures.
- [x] 4.5 Confirm stale Git worktree registry entries are either absent or resolved by an exact-owned cleanup record; never prune an unrelated or unknown registration.
