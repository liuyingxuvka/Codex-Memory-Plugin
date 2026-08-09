## Why

The 2026-08-09 Sleep run was interrupted by its outer owner before the native deadline and left no terminal receipt; Organization then correctly failed closed on the unproven global-writer cleanup. The system needs a bounded, resumable, atomic maintenance contract before another scheduled run or public release can be treated as successful.

## What Changes

- Add a single interruption-safe execution contract for local Sleep/Dream and independent Organization maintenance, including typed terminal states, checkpoint persistence, descendant cleanup evidence, and exact recovery of settled-but-unpublished work.
- Replace pointer-before-index publication with one staged, validated generation whose aggregate current pointer is activated last by compare-and-swap.
- Move expensive analysis, model work, network work, and large receipt construction outside the global writer window; retain a short fenced commit window.
- Add layered soft, stall, native, owner, and host deadlines. A soft boundary saves progress; a hard boundary terminates the complete process tree and emits a terminal failure receipt.
- Compact cycle/native receipts into content-addressed artifacts with bounded terminal envelopes while preserving complete diagnostics as immutable sidecars.
- Add Organization frozen-plan checkpoints, resume rules, exact action packet idempotency, and an explicit Luna/max typed-review boundary guarded by deterministic validation.
- Add fault-injection, contention, payload, scale, and semantic Organization regression coverage, plus a FlowGuard CI authority gate.
- Synchronize the clean installed projections and the two persisted Luna/max automations only after source and evidence identities are frozen; publish the repaired public runtime as v0.8.4 without moving v0.8.3.

## Capabilities

### New Capabilities

- `resumable-kb-maintenance`: Bounded Sleep/Dream and Organization execution with interruption-safe ownership, checkpoints, recovery, and typed terminal evidence.
- `atomic-kb-publication`: Staged content-addressed KB generations with pointer-last activation and fenced short writer commits.
- `organization-editorial-review`: Frozen Organization candidate packets, pinned Luna/max typed review, Skill/privacy validation, and exact action application.

### Modified Capabilities

<!-- Existing capability requirements are unchanged by name; the new capabilities define the repaired contract. -->

## Impact

Affected runtime areas include `scripts/run_kb_automation.py`, `local_kb/automation_contracts.py`, `local_kb/process_control.py`, `local_kb/local_cycle.py`, `local_kb/org_cycle.py`, lifecycle/model/index publication, Organization maintenance and contribution, receipt serialization, tests, FlowGuard project evidence, managed Skill projections, installation state, and GitHub release gates. Existing peer-owned files and unrelated assets remain outside the change boundary.
