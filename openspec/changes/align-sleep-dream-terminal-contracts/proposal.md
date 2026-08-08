## Why

The latest successful Sleep/Dream receipt proves the batch and four Dream experiments completed, but the contract still disagrees on convergence semantics, Dream writer ownership, generation binding, typed perturbation accounting, postflight inclusion, and stale lane-status evidence. These mismatches allow a green run to overclaim terminal completeness and make the requested Sleep/Dream behavior difficult to verify.

## What Changes

- Define one terminal contract for closing backlog, convergence, and Dream admission so `backlog_growing` is not confused with unresolved closing work.
- Bind Dream handoffs and their receipt to the parent cycle identity, delegated writer token, and pinned LogicGuard generation.
- Require exact typed disposition accounting for each planned Dream perturbation (`performed`, `not_applicable`, or `blocked`).
- Include postflight status and current lane-status evidence in the immutable cycle receipt, with stale state visible as a blocker rather than silently reused.
- Expand source/prompt/contract fingerprints to cover every managed Sleep/Dream artifact that can change the terminal contract.
- Add regression fixtures for success, no-closing-work backlog growth, missing writer token, generation mismatch, typed-set mismatch, and stale postflight evidence.

## Capabilities

### New Capabilities

- `sleep-dream-terminal-contract`: Define and validate the exact terminal evidence required for a Sleep-then-Dream cycle.

### Modified Capabilities

- `kb-sleep-dream-convergence`: Convergence and Dream admission must use the new typed terminal contract.

## Impact

Affected code includes `local_kb/local_cycle.py`, `local_kb/dream.py`, `local_kb/automation_contracts.py`, cycle/native receipt builders, Sleep/Dream prompts and maintenance contracts, lane-status/history writers, and the related test suites. Sleep remains the sole canonical LogicGuard publisher; Dream remains immutable simulation plus typed handoff.
