## Purpose

This capability defines the terminal evidence for one Sleep-then-Dream cycle so backlog growth, Dream admission, immutable generation binding, typed experiment coverage, and postflight status are all unambiguous and machine-verifiable.

## ADDED Requirements

### Requirement: Sleep SHALL publish one explicit terminal convergence classification

The Sleep receipt MUST report opening actionable backlog, newly eligible work, terminal dispositions, explicitly parked work, closing actionable backlog, and a deterministic `convergence_status`. `backlog_growing` MUST mean that closing backlog is not lower than opening backlog after admitted work is counted; zero closing backlog MUST be represented as settled/no-op rather than growth. Dream admission MUST be gated by frozen-batch settlement and safety blockers, not by the growth label alone.

#### Scenario: New work arrives but all actionable work closes
- **WHEN** newly eligible items are admitted and the frozen batch settles with closing backlog zero
- **THEN** Sleep reports the settled terminal classification and the cycle may run Dream if no safety blocker exists

#### Scenario: Actionable backlog remains after the batch
- **WHEN** closing backlog is greater than or equal to opening backlog and unresolved actionable work remains
- **THEN** Sleep reports `backlog_growing` or `no_convergence` with the exact remainder and Dream admission is still decided by the explicit safety gate

### Requirement: Dream handoffs SHALL bind parent cycle, writer, and LogicGuard generation

Every Dream handoff and Dream terminal receipt MUST carry the parent cycle identity, delegated writer token/phase identity used for any commit window, the pinned LogicGuard generation id, model revision, root block, and mesh revision. A missing or mismatched identity MUST block acknowledgement or reuse.

#### Scenario: Dream emits a typed handoff
- **WHEN** an experiment produces a model-gap result for Sleep
- **THEN** the handoff contains the parent cycle id, generation id, full LogicGuard binding, typed disposition, and stable idempotency key

#### Scenario: Handoff generation differs from current pinned authority
- **WHEN** a Dream handoff is replayed against a different generation
- **THEN** the handoff remains pending or blocked and no Sleep acknowledgement is written

### Requirement: Dream planned perturbations SHALL have exact typed disposition coverage

The Dream receipt MUST enumerate every planned perturbation kind with one terminal disposition of `performed`, `not_applicable`, or `blocked`, together with an oracle/result reference or a bounded reason. Missing, duplicate, or unknown kinds MUST make the receipt non-terminal.

#### Scenario: All applicable perturbations run
- **WHEN** Dream executes the bounded experiment suite for an immutable generation
- **THEN** the receipt contains exactly one typed disposition for every planned kind and the performed entries bind evidence

#### Scenario: A perturbation is unsafe or unsupported
- **WHEN** a planned perturbation cannot run safely
- **THEN** it is recorded as `not_applicable` or `blocked` with a typed reason and is not silently omitted

### Requirement: Cycle terminal evidence SHALL include postflight and current lane status

The immutable cycle receipt MUST include postflight disposition/path (or an explicit skipped reason for a no-op), current lane-status evidence, and the source/prompt/automation-contract digests used for the cycle. A stale, missing, or unverified postflight/lane record MUST be visible as a blocker and MUST NOT be presented as a complete success.

#### Scenario: Sleep and Dream complete normally
- **WHEN** both phases reach terminal states
- **THEN** the cycle receipt binds current postflight and lane-status evidence and the full managed-contract fingerprint set

#### Scenario: Postflight writer is interrupted
- **WHEN** postflight cannot produce a terminal receipt
- **THEN** the cycle remains incomplete or blocked, preserves the phase evidence, and does not claim perfect Sleep/Dream completion
