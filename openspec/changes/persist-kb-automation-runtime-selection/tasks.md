## 1. Runtime policy

- [x] 1.1 Define the canonical per-automation runtime policy for `kb-sleep` and `kb-org-maintenance`, including explicit Luna/max values and a stable configuration digest.
- [x] 1.2 Add provider metadata validation for explicit model and reasoning selections, including `max`, with typed unavailable-model and unsupported-effort failures.
- [x] 1.3 Thread the selected runtime through automation payload generation without applying strongest-available fallback to explicit owners.

## 2. Installer and receipt projection

- [x] 2.1 Render both scheduled TOML specs from the explicit policy and preserve existing pause/schedule state.
- [x] 2.2 Extend install/check output to compare source policy, installed projection, provider identity, and exact Luna/max values.
- [x] 2.3 Add native wrapper/runtime receipt fields and reject missing or mismatched runtime evidence.

## 3. Regression and installation

- [x] 3.1 Add tests for idempotent persistence, unavailable model, unsupported max, manual drift, and exact receipt identity.
- [x] 3.2 Run the installer and `--check --json`, then verify both installed automation files and the two live schedules.
