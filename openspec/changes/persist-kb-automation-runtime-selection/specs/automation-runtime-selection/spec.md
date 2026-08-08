## Purpose

This capability makes the model and reasoning selection for each scheduled composite automation explicit, durable, provider-validated, and visible in both installed automation files and native terminal receipts.

## ADDED Requirements

### Requirement: Scheduled composite automations SHALL persist explicit runtime selections

The installer MUST persist an exact model and reasoning-effort selection for `KB Sleep` and organization maintenance. A refresh or reinstall MUST preserve those selections instead of recomputing a different strongest-available model from global defaults.

#### Scenario: Both composite owners are installed
- **WHEN** the repository installer refreshes the scheduled automation specs
- **THEN** both specs contain `gpt-5.6-luna` and `max`, and the install check reports the same exact selections for both owners

#### Scenario: Installer runs again after a successful setup
- **WHEN** an idempotent install/check is repeated with unchanged provider metadata
- **THEN** the two runtime selections remain byte- and value-equivalent and no Sol/xhigh downgrade is emitted

### Requirement: Explicit runtime selections SHALL fail closed when unavailable

The installer and automation runner MUST validate an explicit model against current provider metadata and the requested reasoning effort against the selected model's declared modes. If either is unavailable, the operation MUST return a typed failure and MUST NOT silently substitute another model, effort, alias, or alternate launcher.

#### Scenario: Luna is unavailable
- **WHEN** provider metadata does not expose `gpt-5.6-luna`
- **THEN** installation or execution fails with an unavailable-runtime result and leaves the previous valid automation specs untouched

#### Scenario: Luna exists but max is unsupported
- **WHEN** the selected provider exposes Luna but not `max`
- **THEN** the operation fails with an unsupported-reasoning result rather than choosing `xhigh` or another lower mode

### Requirement: Native receipts SHALL expose exact runtime identity

Every scheduled composite native receipt MUST include the selected model, reasoning effort, provider identity/revision when available, selection policy, and a digest of the persisted automation runtime configuration. A receipt lacking these fields is not reusable as execution evidence for the requested Luna/max claim.

#### Scenario: A Luna/max automation executes
- **WHEN** the Sleep or organization wrapper reaches a terminal state
- **THEN** its immutable native receipt binds the exact Luna/max selection to the run identity and covered automation inputs

#### Scenario: A legacy receipt predates explicit runtime evidence
- **WHEN** a prior successful receipt does not contain exact runtime fields
- **THEN** it remains historical context only and cannot prove that the new Luna/max configuration executed
