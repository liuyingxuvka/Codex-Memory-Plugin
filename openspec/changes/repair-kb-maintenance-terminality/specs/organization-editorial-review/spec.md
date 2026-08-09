## Purpose

This capability makes Organization card and card-bound Skill decisions reproducible, privacy-safe, and explicitly tied to a frozen packet and the configured Luna/max reviewer.

## ADDED Requirements

### Requirement: Organization review consumes a frozen candidate packet

Before any editorial decision, Organization MUST freeze source, catalog, card, import, LogicGuard bundle, Skill bundle, guidance, and candidate identities in one packet. The review result MUST bind the packet digest, provider/model, reasoning setting, guidance digest, and typed decisions.

#### Scenario: Source or catalog drift
- **WHEN** the source commit, catalog identity, card hash, or Skill bundle hash changes after packet freeze
- **THEN** the review MUST be rejected as stale and MUST NOT apply any selected action.

#### Scenario: Guidance unavailable
- **WHEN** organization-review guidance is not installed or cannot be loaded
- **THEN** the receipt MUST report guidance unavailable, while deterministic privacy, hash, identity, and action validation still runs; guidance absence MUST NOT be silently hidden.

### Requirement: Luna decisions are typed and deterministically validated

The pinned Luna/max reviewer MUST return a typed decision for every candidate. A deterministic validator MUST reject unknown action IDs, missing candidates, unsupported decision types, hallucinated evidence, privacy violations, non-reversible merge/split packets, and any decision that is not bound to the frozen packet.

#### Scenario: Valid keep or apply decision
- **WHEN** Luna returns a complete typed decision set whose evidence and action IDs match the frozen packet
- **THEN** Organization MAY construct the exact selected apply packet and continue to post-apply validation.

#### Scenario: Incomplete or hallucinated decision
- **WHEN** Luna omits a candidate or references a card/action/evidence ID absent from the packet
- **THEN** Organization MUST fail closed and MUST NOT fall back to deterministic auto-approval.

### Requirement: Card-bound Skill bundles enforce author, hash, and version rules

Organization MUST group Skill updates by `bundle_id`, accept only original-author updates on the same bundle with SHA-256 `content_hash` and `version_time`, treat non-author changes as forks, and select the latest approved version by `version_time`. Candidate, rejected, unknown, unpinned, or non-hash-verified Skills MUST NOT be auto-installed.

#### Scenario: Original-author update
- **WHEN** an original author submits a same-bundle update with valid hash and version time
- **THEN** it MAY be approved and distributed only after the complete Skill safety checks pass.

#### Scenario: Non-author fork
- **WHEN** a non-author changes content under an existing bundle ID
- **THEN** it MUST be classified as a fork and MUST NOT be installed or distributed as the original bundle.

### Requirement: Exact selected actions control side effects

Only exact selected packet IDs from the validated decision set MAY be applied. Merge and split actions MUST be reversible or typed blocked with an executable reopen condition. No-change Organization MUST remain a successful no-op without manufacturing a branch or pull request.

#### Scenario: No-change pass
- **WHEN** all candidates receive typed keep/reject decisions and the selected set is empty
- **THEN** Organization MUST emit a completed no-change receipt and MUST NOT create a branch, push, or pull request.

#### Scenario: Reversible merge
- **WHEN** a validated merge action is selected
- **THEN** the apply packet MUST contain exact source IDs, target identity, rollback data, and a post-apply check before any GitHub side effect.
