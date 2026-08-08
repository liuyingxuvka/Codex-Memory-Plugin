## Context

The local cycle currently admits Dream when `_sleep_status` is `completed`, while lifecycle convergence uses a separate `backlog_growing` calculation. Dream receipts contain nested authority generation data but the durable handoff shape lacks a top-level generation binding, and the current cycle marks Dream as read-only without a delegated writer identity. Prompt and automation-contract digests do not cover every artifact that controls the terminal claim.

## Goals / Non-Goals

**Goals:**

- Make the Sleep convergence calculation and Dream admission rule explicit and testable.
- Carry parent/cycle/writer/generation identity through Dream handoffs and receipts.
- Make the bounded perturbation set exact and typed.
- Include postflight/lane evidence and complete contract fingerprints in the immutable cycle receipt.

**Non-Goals:**

- Do not make Dream a canonical LogicGuard publisher.
- Do not let Dream write cards, candidates, confidence, or canonical model authority.
- Do not redesign Sleep prioritization or the organization exchange layer.

## Decisions

1. **Separate convergence classification from downstream admission.** Sleep calculates counts and a truthful status; the cycle uses an explicit `dream_admission` object requiring settled frozen work, no blockers, current generation, and valid writer/phase identity where a commit window exists.
2. **Promote generation binding to the handoff top level.** Keep nested provenance for compatibility with current artifacts but validate the top-level id and full binding against the Dream run pin.
3. **Use a canonical perturbation registry.** The registry defines the finite planned kinds and the allowed terminal dispositions; receipt validation compares exact set equality and rejects duplicates/unknowns.
4. **Fingerprint all terminal-contract inputs.** Extend source-component identity to include Sleep/Dream prompts, automation contract definitions, and relevant policy files, so a changed contract invalidates old cycle evidence.
5. **Record postflight/lane evidence in the cycle owner.** Child receipts remain immutable; the cycle receipt records the postflight result and the lane-status identity rather than inventing a child success.

## Risks / Trade-offs

- [Risk] Existing handoffs lack top-level generation fields. → Treat them as legacy pending inputs and require a direct current-format normalization by Sleep before acknowledgement; do not add a normal-runtime fallback reader.
- [Risk] Requiring writer identity could make a read-only Dream over-constrained. → Define the commit window explicitly; read-only simulation may carry `not_required` only when the receipt proves no write path was entered.
- [Risk] More contract files increase invalidation frequency. → Fingerprint only managed artifacts that directly control terminal claims and expose the exact changed component in the blocker.

## Migration Plan

1. Add terminal contract validators and exact perturbation registry.
2. Update lifecycle, local-cycle, Dream handoff, prompt, and receipt builders.
3. Add success, growth, missing-identity, generation-mismatch, typed-set, and stale-postflight tests.
4. Run one fresh Sleep/Dream wrapper and verify the new immutable cycle receipt.

