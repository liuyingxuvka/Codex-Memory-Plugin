## 1. Terminal convergence

- [x] 1.1 Add a single terminal-convergence helper that computes counts and classifies settled, reduced, no-convergence, growth, and blocked states without conflating zero closing backlog with growth.
- [x] 1.2 Replace the Dream gate with an explicit admission record requiring frozen-batch settlement, no safety blockers, pinned generation, and a declared writer/commit-window policy.
- [x] 1.3 Update Sleep/Dream prompts and automation-contract markers to describe the same terminal contract and downstream admission rule.

## 2. Dream identity and exact perturbation coverage

- [x] 2.1 Add parent cycle, delegated writer/phase, and top-level LogicGuard generation binding to Dream receipts and typed Sleep handoffs.
- [x] 2.2 Define the finite perturbation registry and validate exact typed dispositions (`performed`, `not_applicable`, `blocked`) with reasons/oracles.
- [x] 2.3 Add legacy-input disposition and fail-closed validation for missing or mismatched generation/writer identities.

## 3. Postflight and evidence freshness

- [x] 3.1 Extend local cycle receipts with postflight path/status, current lane-status identity, and complete managed-contract source digest coverage.
- [x] 3.2 Add tests for backlog growth with zero closing work, blocked Dream admission, generation mismatch, missing writer token, perturbation-set mismatch, stale lane/postflight, and successful four-experiment Dream evidence.

## 4. Acceptance

- [x] 4.1 Run the focused Sleep/Dream contract and native-receipt suites.
- [x] 4.2 Run one fresh Sleep-then-Dream wrapper after runtime/install changes and validate the immutable cycle receipt end to end.
