## ADDED Requirements

### Requirement: Foreground retrieval uses only a current model-bound active index
Routine retrieval SHALL load a compact current active-index authority whose every record contains a validated exact card/model/node/mesh binding. It MUST fail visibly when the index or bound authority is unavailable, stale, malformed, or scope-incompatible and MUST NOT scan YAML or use `related_cards` as a fallback.

#### Scenario: Current indexed query
- **WHEN** a query matches one or more current eligible model-bound records
- **THEN** retrieval SHALL rank projections and return exact model/node/revision/mesh identifiers plus a bounded current neighborhood receipt

#### Scenario: Missing current model authority
- **WHEN** the index exists but a bound exact model or mesh revision cannot be loaded or verified
- **THEN** retrieval SHALL return a visible unavailable/failure result, exclude the affected record, and SHALL NOT reinterpret YAML as authority

### Requirement: Exact card or node lookup expands through the model
An exact card id, model id, or qualified node id lookup SHALL identify the bound root and materialize a deterministic bounded neighborhood containing relevant support, warrant, assumption, rebuttal, qualifier, limitation, membership, and cross-model relations from the exact mesh revision.

#### Scenario: Exact card id is requested
- **WHEN** the caller requests an indexed card id
- **THEN** retrieval SHALL return the card projection and its exact root-centered model neighborhood within declared hop/node/edge budgets

#### Scenario: Neighborhood exceeds the budget
- **WHEN** the reachable exact graph is larger than the configured budget
- **THEN** retrieval SHALL return a deterministic truncated neighborhood with excluded/frontier diagnostics and SHALL NOT silently traverse an unbounded graph

### Requirement: Retrieval ranking remains explainable and lifecycle-safe
Ranking SHALL combine the existing route/status/confidence policy with model-native signals such as exact node match, role, distance, support/opposition state, importance, and scope, while rejected, merged, superseded, retired, parked, malformed, or stale-bound records have zero exposure.

Foreground retrieval MUST NOT replay the complete lifecycle history. A local-only
query SHALL read no foreign-calibration state. A query with eligible organization
results SHALL read one compact current foreign-calibration projection whose digest,
source event count, last sequence, and event-file identity were published by Sleep or
the versioned upgrade. Missing, malformed, or stale projection authority SHALL block
foreign calibration visibly without a replay, repair, or alternate-reader fallback.

#### Scenario: Related node is surfaced
- **WHEN** a non-root node is included because it supports, contradicts, qualifies, or shares a higher-order model with the exact result
- **THEN** the receipt SHALL name the relation, distance, exact qualified node, and score contribution

#### Scenario: Ineligible related model exists
- **WHEN** a mesh neighbor belongs to an ineligible lifecycle entry or unauthorized scope
- **THEN** it SHALL be excluded before ranking and SHALL contribute neither text nor score to the returned result

#### Scenario: Local-only query runs against a very large lifecycle history
- **WHEN** the query has no eligible organization result
- **THEN** retrieval SHALL not read the foreign-calibration projection and SHALL not replay lifecycle history

#### Scenario: Foreign calibration projection is stale
- **WHEN** the lifecycle event-file identity no longer matches the compact foreign-calibration projection
- **THEN** organization retrieval SHALL fail visibly and SHALL NOT replay history, repair the projection, or return uncalibrated foreign results

### Requirement: Desktop detail is a graph-first projection of one current authority
The desktop UI SHALL show the selected card together with one recommended bounded model graph and on-demand details for revision, support, warrant, assumptions, rebuttals, limitations, memberships, and open gaps. UI text SHALL be localized display projection; machine ids and receipts remain canonical.

#### Scenario: User opens a model-bound card
- **WHEN** the selected card and exact mesh revision validate
- **THEN** the UI SHALL render its familiar prediction summary and the same exact bounded graph returned by the retrieval view model

#### Scenario: Binding becomes stale while viewing
- **WHEN** the selected projection or mesh binding is no longer current
- **THEN** the UI SHALL show a visible stale/unavailable state and SHALL NOT retain a misleading graph from a different revision

### Requirement: Model-native retrieval meets bounded performance budgets
The system SHALL define and verify budgets for active-index load, exact binding verification, exact-card lookup, and bounded neighborhood materialization on representative current-card and scale fixtures.

#### Scenario: Representative local knowledge base
- **WHEN** the performance suite runs on the declared representative fixture and environment
- **THEN** P95 retrieval and neighborhood materialization SHALL remain within the frozen budget and memory cap recorded by the verification contract

#### Scenario: Multiple exact nodes are read from one generation
- **WHEN** a process reads different model-bound cards from the same authority generation and privacy scope
- **THEN** it MAY reuse one pinned read-only model/mesh store session keyed by the exact authority pointer digest, and a changed digest SHALL open a new session before another context is returned

### Requirement: Ordinary retrieval uses the local organization snapshot without network side effects
Routine task retrieval SHALL search the current local canonical authority and the current validated organization snapshot as separate sources. It SHALL NOT fetch a card, bundle, or mirror content over the network on a cache miss, and every organization result SHALL remain explicitly foreign and read-only.

#### Scenario: Relevant organization card is already synchronized
- **WHEN** a task query matches an applicable active card in the current local organization snapshot
- **THEN** retrieval SHALL return it automatically with its organization generation, card revision, LogicGuard binding, freshness status, and source label, without a user adoption action

#### Scenario: No current organization snapshot exists
- **WHEN** a task requests organization context but no complete validated snapshot has ever been activated
- **THEN** retrieval SHALL keep working for local knowledge and SHALL return organization context as unavailable rather than attempting a lazy download

#### Scenario: Local and foreign cards conflict
- **WHEN** a foreign organization card conflicts with a current local canonical card for the same task boundary
- **THEN** retrieval SHALL preserve the local canonical authority, expose the foreign card only as a bounded alternative or conflict warning, and SHALL record no silent overwrite

### Requirement: Multi-source ranking and receipts are globally consistent
All validated local and organization candidates SHALL enter one deterministic
deduplication and ranking pass. Exact content duplicates SHALL collapse to the
current local authority, while distinct organization cards MUST remain able to
outrank weaker local matches. One call SHALL persist one combined receipt whose
ordered rows exactly equal the rows returned to CLI, UI, and AI callers.

#### Scenario: Local candidates fill top-k before merge
- **WHEN** a distinct organization card has a higher final score than one or more local candidates
- **THEN** the organization card SHALL appear in the final top-k and SHALL NOT be hidden by source concatenation order

#### Scenario: Outcome refers to a foreign result
- **WHEN** the caller records actual use or an outcome for a foreign result
- **THEN** validation SHALL resolve its source-qualified result reference in the combined receipt and verify the exact snapshot, bundle, and LogicGuard binding

### Requirement: Viewing, selection, use, and outcome are separate exact events
Opening a detail surface SHALL record at most `viewed`; it MUST NOT imply that a
task selected or used the card. `used` requires an actual task-consumption call,
and `outcome_recorded` requires a declared result class and the exact prior use.
Duplicate event keys SHALL reuse the original terminal receipt without duplicate
history or exchange-ledger writes.

#### Scenario: User opens and closes an organization card
- **WHEN** no task consumes the card
- **THEN** no `used`, outcome, local adoption, model publication, or Skill installation side effect SHALL occur

#### Scenario: Task uses an organization card and later reports failure
- **WHEN** both calls bind the same combined receipt and source-qualified result
- **THEN** the next Sleep batch SHALL see exact foreign evidence and may dampen, suppress, localize, propose an organization update, or record no delta without mutating the foreign card
