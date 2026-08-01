## ADDED Requirements

### Requirement: Sleep is the sole canonical model maintenance owner
The existing Sleep entrypoint SHALL remain the only Khaos Brain maintenance route allowed to create or revise card LogicModels, ModelMesh revisions, card projections, and the resulting active-index generation. LogicGuard supplies model semantics and stores but MUST NOT become a second scheduler or lifecycle decision owner.

#### Scenario: Sleep processes a selected lifecycle delta
- **WHEN** the lifecycle owner supplies a bounded selected delta and the maintenance lane is acquired
- **THEN** Sleep SHALL produce a model change plan, commit it model-first, publish verified projections/index, and advance its watermark only after the complete generation validates

#### Scenario: Another route attempts a canonical write
- **WHEN** Dream, retrieval, UI, organization visibility, or an unowned helper attempts to commit model/mesh authority or publish projections
- **THEN** the operation SHALL be rejected and SHALL NOT advance lifecycle, mesh, projection, index, or watermark state

### Requirement: Sleep consolidates small models through ModelMesh
Sleep SHALL organize exact card-model revisions into larger logical structures by revision-pinned registry entries, memberships, and provenance-qualified cross-model edges. It SHALL preserve child model identities rather than copy nodes into one giant model.

#### Scenario: Two cards form a grounded higher-order model
- **WHEN** two exact card nodes have an evidence-backed support, contradiction, refinement, dependency, or shared-model relation
- **THEN** Sleep SHALL add the exact qualified nodes to a ModelMesh revision through memberships and/or a typed cross-model edge with admissible provenance

#### Scenario: AI suggests an ungrounded relationship
- **WHEN** an AI inference or legacy `related_cards` value proposes a relationship without admissible non-AI-only provenance
- **THEN** Sleep SHALL retain it as a gap or candidate for evidence and SHALL NOT commit it as a canonical cross-model edge

### Requirement: Sleep evaluates model completeness before strengthening knowledge
For every affected important claim, Sleep SHALL inspect missing evidence, warrant, assumption, opposition, boundary, scope, duplicate-support, and stale-revision diagnostics and SHALL record a bounded disposition before promotion or confidence strengthening.

#### Scenario: Important claim lacks a warrant and counterexample coverage
- **WHEN** an affected claim is otherwise retrievable but LogicGuard diagnostics expose missing warrant and opposition roles
- **THEN** Sleep SHALL keep those gaps visible, avoid broad promotion, and record the next evidence or Dream-validation action

#### Scenario: No material model change
- **WHEN** the selected evidence fingerprint, exact model revisions, diagnostics, and decisions equal a prior closed Sleep input
- **THEN** Sleep SHALL emit an idempotent no-delta receipt without new model, mesh, projection, index, or history writes

### Requirement: Dream validates one exact mesh revision without mutation authority
Dream SHALL pin an exact mesh revision and may run bounded evidence removal, rebuttal activation, edge removal, model-pin replacement, missing-role, or fragility experiments. Dream MUST write only experiment artifacts, simulation receipts, and typed idempotent Sleep handoffs.

#### Scenario: Counterexample weakens an important claim
- **WHEN** a bounded simulation on the pinned mesh shows that removing one evidence contribution or activating a rebuttal materially changes an important claim
- **THEN** Dream SHALL record the exact perturbation and result and emit one typed handoff for Sleep to review

#### Scenario: Dream attempts direct improvement
- **WHEN** an experiment indicates a missing evidence node, warrant, edge, or boundary
- **THEN** Dream SHALL NOT add or edit canonical authority or YAML and SHALL route the evidence and proposed action only through the Sleep handoff contract

### Requirement: Dream work is convergent and evidence-fingerprinted
Dream SHALL derive a stable fingerprint from the exact mesh revision, selected roots, perturbation plan, evidence inputs, and relevant toolchain identity. An already closed identical fingerprint MUST NOT rerun or write duplicate evidence.

#### Scenario: Identical dream input repeats
- **WHEN** the exact mesh revision and all decision-relevant experiment inputs match a prior terminal closure
- **THEN** Dream SHALL return no-delta and SHALL NOT write a new experiment, simulation receipt, handoff, or history row

#### Scenario: Model evidence changes
- **WHEN** a bound model/mesh revision or decision-relevant evidence changes
- **THEN** Dream MAY reopen the opportunity under a new fingerprint while preserving the prior immutable closure

### Requirement: Dream persists a bounded opportunity projection
Dream SHALL preserve the exact identity of the full evaluated opportunity
inventory as a count, digest, and stable fingerprint set, but SHALL NOT persist
an unbounded copy of every source action or task summary. The durable
opportunity artifact SHALL contain at most 64 ranked, selected, or prior-closure
examples, every source action SHALL use digest-bound bounded evidence samples,
and executable selection SHALL remain capped at four experiments.

#### Scenario: Historical evidence produces thousands of opportunities
- **WHEN** the current Dream scan evaluates more than 64 route, taxonomy, or card-validation opportunities
- **THEN** the report SHALL name the full count and inventory digest, `opportunities.json` SHALL record no more than 64 deterministic examples, omitted count SHALL reconcile exactly, and selected experiments SHALL still come from the full ranked inventory

#### Scenario: A source action contains many events and task summaries
- **WHEN** one consolidation action contains an arbitrarily large event-id or task-summary list
- **THEN** Dream SHALL fingerprint exact counts and digests, retain only bounded display samples, and SHALL NOT duplicate the complete lists into every opportunity record

### Requirement: One local maintenance task composes Dream and Sleep phases
The scheduler SHALL expose one local maintenance owner with permission-separated Sleep and Dream phases. A fresh cycle SHALL run the existing Sleep publisher first and then run bounded Dream only after Sleep reaches a clean terminal; a cycle with an open frozen Sleep batch SHALL resume Sleep and explicitly defer Dream for that trigger. Dream SHALL never become a second canonical publisher.

#### Scenario: Fresh local cycle
- **WHEN** no open frozen Sleep batch exists and the local maintenance lease is acquired
- **THEN** the cycle SHALL pin one local generation, run the existing Sleep publisher to a clean terminal state, then run Dream read-only against the published exact generation and seal valid handoffs only for a later Sleep batch

#### Scenario: Resume an open Sleep batch
- **WHEN** a previous Sleep run left a resumable frozen batch
- **THEN** the cycle SHALL resume that exact batch, mark Dream deferred, and SHALL NOT attach new Dream opportunities to the frozen batch

#### Scenario: Dream phase fails or times out
- **WHEN** Dream has an ordinary bounded experiment failure or a hard timeout whose descendants are confirmed cleaned up
- **THEN** the cycle SHALL keep the failure visible, reject unsealed handoffs, and preserve the already-completed Sleep publication; cleanup uncertainty SHALL block later local descendants without changing organization-cycle eligibility

#### Scenario: Atomic Sleep publication consumes most of the former hard timeout
- **WHEN** Sleep reaches a clean durable terminal after a long atomic model/index publication and Dream remains eligible
- **THEN** the combined local owner SHALL retain enough route-specific hard-timeout headroom for bounded Dream, while the enclosing owner remains strictly larger; expiry SHALL still fail visibly and require zero descendants rather than inferring success from the completed Sleep child

### Requirement: Local and organization cycles have independent failure domains
The local and organization scheduled owners SHALL keep separate outer leases,
requests, receipts, and terminal states. They SHALL share only an owner-token
global write lease around overlapping durable mutations. A local-cycle blocker
MUST NOT automatically mark organization work not run, and an organization-cycle
blocker MUST NOT invalidate a clean local cycle.

#### Scenario: Local Sleep is blocked before publication
- **WHEN** the organization cycle has an otherwise valid independent request
- **THEN** the organization cycle SHALL remain eligible to run and SHALL acquire the global write lease only for its own mutation phases

#### Scenario: Both cycles reach a write phase
- **WHEN** one cycle already owns the live global writer token
- **THEN** the other SHALL wait or return a visible bounded contention disposition and SHALL NOT steal the token, overlap the write, or falsify completion
