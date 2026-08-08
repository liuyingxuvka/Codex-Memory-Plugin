## Why

The live composite automations were edited to request `gpt-5.6-luna` with maximum reasoning, but the repository installer still regenerates them from a strongest-available resolver that may select another model or an unsupported lower reasoning label. A reinstall can silently undo the user's explicit runtime choice, so the requested Luna/max execution is not durable or auditable.

## What Changes

- Add validated, per-automation runtime selections for the two scheduled composite owners.
- Persist `gpt-5.6-luna` and `max` for both `KB Sleep` and organization maintenance through installer refreshes.
- Validate the requested model and reasoning effort against current provider metadata and fail visibly when the requested runtime is unavailable; do not silently downgrade.
- Extend canonical reasoning-order handling to support `max` and other provider-declared strongest modes without treating a resolver fallback as success.
- Emit the selected model, reasoning effort, provider identity, and configuration fingerprint in automation specs and native receipts.
- Add install/check and runtime regression coverage for persistence, rejection, and exact selection.

## Capabilities

### New Capabilities

- `automation-runtime-selection`: Persist and validate exact per-automation model and reasoning choices across installation and execution.

### Modified Capabilities

- `kb-runtime-assurance`: Native automation receipts must expose the exact selected runtime and reject an unavailable explicit selection.

## Impact

Affected code includes `local_kb/install.py`, automation payload generation, runtime resolution/receipt code, installer and automation tests, repository-managed automation templates, and local installed automation files. This does not change ordinary retrieval model authority.
