# Organization Mode Structure Audit

## Current Ownership Map

Organization mode uses the existing modules, with their responsibilities
tightened around the current no-adoption flow.

| Boundary | Primary owner | Responsibility |
|---|---|---|
| Source contract | `local_kb/org_source_contract.py` | Current schema, catalog/card/bundle identities and validation rules |
| Source connect/upgrade | `local_kb/org_sources.py`, `local_kb/org_migration.py` | Clone/fetch, direct-to-current upgrade, rollback and zero residuals |
| Foreign snapshot | `local_kb/org_snapshot.py` | Complete content-addressed generation and atomic pointer publication |
| Combined retrieval | `local_kb/search.py` | One local+organization ranking and one result receipt |
| Interaction/outcome | `local_kb/calibration.py`, `local_kb/lifecycle.py` | Exact viewed/selected/used/outcome evidence and Sleep handoff |
| Organization decisions | `local_kb/org_cleanup.py`, `local_kb/org_maintenance.py` | Exact identity coverage, reversible merge/split, apply/reopen packets |
| Organization contribution | existing outbox/contribution modules | Privacy-gated current card packages only |
| Local task | `local_kb/local_cycle.py` | Sleep then Dream under one scheduled owner |
| Organization task | `local_kb/org_cycle.py` | Source/maintenance/contribution/snapshot under one scheduled owner |
| Write coordination | `local_kb/maintenance_lanes.py` | Independent task leases plus one global/delegated writer protocol |
| Terminal authority | `local_kb/automation_runtime.py` | Strict receipt-v3 identity, validation and reuse |
| Installation | `local_kb/install.py`, `local_kb/operator_activation.py` | Five maintained Skills classified as two scheduled, two child, one manual |

## Decisions

### Keep one retrieval owner

`local_kb/search.py` remains the single search owner. Organization search is not
a second search pipeline and local-first truncation is retired. Source adapters
may produce candidates, but one owner performs normalization, scoring, limiting,
result-reference creation, and receipt publication.

### Retire adoption as behavior

`local_kb/adoption.py` no longer owns local-copy creation or Skill installation.
Any retained code is inspection-only for retired metadata during direct upgrade
or explicit diagnostics. Normal runtime calls to the former adoption behavior
fail visibly.

### Preserve two outer cycle owners

Sleep and Dream are phases, not peer schedules. Organization maintenance and
contribution are phases, not peer schedules. The two outer tasks keep separate
leases and failure states. A small global writer protocol protects only shared
durable mutation, preventing a giant combined scheduler while still preventing
concurrent publication.

### Keep source upgrade separate from snapshot publication

Source upgrade owns the mutable checked-out organization tree and rollback.
Snapshot publication consumes a validated current tree and writes a new
immutable generation. It never repairs source data in place, deletes the prior
generation, or makes a partial generation current.

### Keep merge/split decision from apply

Cleanup/maintenance analysis produces stable decision identities and either an
apply packet or reopen contract. Apply consumes only selected complete packets.
This separation makes retry, audit, and rollback deterministic.

## Removed Structural Hazards

- No task-time network fetch from retrieval or UI.
- No local adopted-card authority and no adoption queue.
- No direct local model/index publication from organization use.
- No Skill installation because a card was synchronized or opened.
- No four independently scheduled KB maintenance tasks.
- No local-task error writing an organization-task `not_run` state.
- No run-id-only cycle receipt reuse.
- No equal-count substitution for exact active-card identity coverage.
- No normal-runtime reader for old organization schemas.
- No snapshot overwrite before complete validation.
- No similarity-only merge or size-only split.
- No planning-only Model-Test/TestMesh report projected as terminal success.

## Remaining Integration Checks

Before a release claim, integration must prove:

1. all new organization bundle/catalog paths are in the exact maintenance
   allowlist without broadening unrelated mutation;
2. current runtime static checks require the new source/snapshot/interaction and
   two-owner markers and forbid adoption/old receipt fields;
3. the five SkillGuard contracts match their actual scheduled/child/manual
   execution classes and exact evidence nodes;
4. ModelMesh and FieldLifecycleMesh name the snapshot, interaction, writer, and
   receipt fields now present in production;
5. one terminal readiness owner consumes current JUnit/model receipts rather
   than accepting a green planning artifact;
6. installer and operator activation receipts report exactly two scheduled
   owners, two composite children, and one explicit-user-only Skill;
7. installed Skills contain no author-side SkillGuard material and no retired
   adoption or task-time-fetch path;
8. real local and organization wrapper outcomes are reported without retry or
   status promotion.

## Architecture Boundary

This audit describes code ownership and observable contracts. It does not by
itself prove runtime success, organization remote permissions, installed-byte
parity, GitHub CI, tag identity, or release publication. Those require their
separate terminal receipts.
