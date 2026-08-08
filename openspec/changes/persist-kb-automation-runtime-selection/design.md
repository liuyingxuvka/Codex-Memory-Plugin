## Context

The installer currently resolves one global strongest-available model and an ordered effort list that ends at `xhigh`. Automation payload generation then writes that global result into both scheduled owners. The desktop automation files already accept model and reasoning fields, so the missing boundary is durable source configuration and validation, not a new launcher.

## Goals / Non-Goals

**Goals:**

- Add a canonical per-automation runtime policy with explicit model and reasoning fields.
- Validate provider/model/effort identity before writing or running a schedule.
- Preserve exact selections through install, check, and native receipt generation.
- Keep the existing strongest-available resolver only for non-explicit legacy/manual callers, never as a fallback for these two owners.

**Non-Goals:**

- Do not change ordinary retrieval model selection or LogicGuard authority.
- Do not add aliases, dual launchers, silent downgrade, or compatibility readers.
- Do not claim a Luna/max run until a new receipt carries the exact fields.

## Decisions

1. **Use a repository-managed runtime policy keyed by automation id.** `kb-sleep` and `kb-org-maintenance` each receive explicit `model` and `reasoning_effort` values in the automation spec source, with a configuration fingerprint included in the payload.
2. **Validate against provider metadata at render and check time.** Add `max` to the canonical effort vocabulary only when metadata declares it; explicit choices never pass through ranking to a weaker choice.
3. **Keep source and installed projections separate.** The source policy is part of the installer fingerprint; the installed TOML is a deterministic projection and the check compares both values and digests.
4. **Bind runtime evidence in the wrapper receipt.** The top-level launcher passes the resolved selection into the native child receipt and validation rejects missing or mismatched runtime fields.

## Risks / Trade-offs

- [Risk] Provider metadata may not expose Luna/max on a machine. → Fail visibly before replacing installed schedules and report the exact unavailable field.
- [Risk] Existing tests assume only xhigh is strongest. → Update the explicit vocabulary and add provider-matrix fixtures while preserving legacy non-explicit ranking behavior.
- [Risk] A user edits an installed TOML manually. → Install check reports drift; it does not silently repair a runtime claim without a new validated projection.

## Migration Plan

1. Add policy constants/schema and validation helpers.
2. Render both scheduled owners from the explicit policy and extend install/check receipts.
3. Add native runtime fields and tests for persistence, unavailable model/effort, and exact receipts.
4. Run installer and check; inspect both installed TOML files before any release.

