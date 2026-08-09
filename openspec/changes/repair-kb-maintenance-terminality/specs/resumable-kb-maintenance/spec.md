## Purpose

This capability makes long-running local Sleep/Dream and independent Organization maintenance bounded, resumable, interruption-safe, and explicitly verifiable across scheduled runs.

## ADDED Requirements

### Requirement: Every run has a supervised terminal lifecycle

The system MUST persist a unique run identity and process-tree owner before starting mutable work. A normal, completed, progress-saved, blocked, failed, interrupted, or cleanup-unconfirmed run MUST produce one immutable terminal envelope tied to that identity.

#### Scenario: External owner interruption
- **WHEN** an outer caller disconnects or terminates the wrapper before the child reaches its native deadline
- **THEN** the supervisor MUST either complete the same run or terminate the complete descendant tree and publish `interrupted`, `failed`, or `cleanup_unconfirmed` evidence; absence of a receipt MUST NOT be interpreted as success.

#### Scenario: PID reuse or mismatched recovery
- **WHEN** a recovery request names a run whose owner identity does not match the recorded process start and fencing identity
- **THEN** recovery MUST refuse to touch the lease or process and return a typed blocked result.

### Requirement: Soft limits save progress and hard limits preserve safety

The system MUST distinguish soft, stall, native hard, owner, and host deadlines. A soft boundary MUST stop admitting new work and persist a resumable checkpoint; a stall boundary MUST require real checkpoint progress; a hard boundary MUST terminate the complete process tree and record cleanup facts.

#### Scenario: Soft boundary before publication
- **WHEN** remaining time is insufficient for the complete commit, postflight, and terminal receipt
- **THEN** the system MUST return `progress_saved`, keep the prior current generation active, and mark Dream or Organization contribution as `not_run`.

#### Scenario: Heartbeat without progress
- **WHEN** heartbeats continue but no checkpoint or observed output progress occurs for the stall interval
- **THEN** the system MUST classify the run as stalled and enter bounded cleanup rather than treating heartbeat as proof of useful work.

### Requirement: Frozen plans resume without duplication or loss

Sleep and Organization MUST persist their frozen input plan, per-item/phase checkpoints, predecessor fingerprints, and pending work. A later run MUST resume an unsettled or settled-but-unpublished plan before admitting new work and MUST preserve exact action packet idempotency.

#### Scenario: Settled but unpublished Sleep batch
- **WHEN** all items are settled but the generation pointer and terminal receipt were not published
- **THEN** the next authorized run MUST resume publication for that batch or emit a typed blocked/recovery condition; it MUST NOT silently skip the batch and create a replacement plan.

#### Scenario: Organization action packet replay
- **WHEN** a resumed Organization plan encounters an action packet that was already applied under the same frozen identity
- **THEN** the system MUST recognize the exact packet and perform no duplicate side effect.

### Requirement: Organization and Sleep have independent scheduled ownership

Organization maintenance MUST remain an independent scheduled owner. It MAY wait for a short fenced commit window, but MUST NOT depend on completion of Sleep analysis, Dream, or an unbounded global writer lease.

#### Scenario: Concurrent read-only planning
- **WHEN** Sleep and Organization begin planning at the same time
- **THEN** both MAY perform read-only staging concurrently, while their bounded commit windows serialize through the writer fence.

#### Scenario: Unproven previous cleanup
- **WHEN** the previous owner has no zero-descendant cleanup evidence
- **THEN** Organization MUST fail closed with a visible cleanup blocker and MUST NOT steal or manually delete the previous lease.
