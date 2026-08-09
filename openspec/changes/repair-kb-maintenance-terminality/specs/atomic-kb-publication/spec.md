## Purpose

This capability guarantees that the canonical KB authority, index, projections, lifecycle state, and watermark advance as one validated content-addressed generation.

## ADDED Requirements

### Requirement: Publication is pointer-last and generation-complete

The system MUST stage and validate the model, mesh, projection, active index, lifecycle acknowledgements, watermark, and manifest before changing the aggregate current pointer. The aggregate pointer MUST be the final authority mutation and MUST bind all component digests.

#### Scenario: Crash before pointer activation
- **WHEN** a process terminates after any staging write but before the pointer CAS
- **THEN** readers MUST continue to use the previous complete generation and the staged candidate MUST remain non-current and recoverable or discardable by its immutable operation record.

#### Scenario: Crash after pointer activation
- **WHEN** a process terminates after the pointer CAS but before a projection or receipt write
- **THEN** recovery MUST finish the same operation idempotently from the committed generation; readers MUST never observe a new pointer with an old active index.

### Requirement: Commit uses a fenced short writer window

The system MUST perform predecessor validation and pointer CAS under one exclusive fencing token and MUST release the global writer immediately after the bounded commit. Long analysis, network, AI review, staging, and receipt serialization MUST occur outside that window.

#### Scenario: Stale writer
- **WHEN** a writer's predecessor digest or fencing epoch differs from the current authority
- **THEN** its CAS MUST fail with a typed blocked result and an executable reopen condition, without an automatic retry inside the lock.

### Requirement: Current payloads are content-addressed and schema-validated

Every current generation, receipt envelope, and referenced sidecar MUST declare its schema, producer, source/tool identity, required members, canonical digest, and terminal status. Missing, partial, wrong-type, stale-schema, path-mismatch, or fingerprint-mismatch payloads MUST fail visibly.

#### Scenario: Partial receipt write
- **WHEN** a terminal receipt path exists but its digest or required members do not validate
- **THEN** the run MUST remain non-terminal for success and MUST expose a typed receipt/payload failure.

#### Scenario: Large diagnostic sidecar
- **WHEN** a run produces large gap or diagnostic data
- **THEN** the complete data MUST be stored as an immutable content-addressed sidecar and the native/cycle terminal envelope MUST reference it without duplicating the full payload.
