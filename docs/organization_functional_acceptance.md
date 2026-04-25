# Organization Functional Acceptance Plan

This document defines the functional acceptance plan for Khaos Brain
organization mode. It is intentionally test-first: before broad cleanup or
module reshaping, each important behavior should have an executable test or an
explicit manual verification checklist.

## Acceptance Strategy

Use three validation layers:

1. Unit and module tests keep small rules stable.
2. End-to-end tests simulate realistic user and repository flows with temporary
   local directories.
3. Manual UI checks confirm the desktop experience is understandable and does
   not expose technical metadata in the wrong place.

Do not start large structural cleanup until the end-to-end acceptance suite
locks the intended behavior. Small local fixes are allowed while adding tests.
Large design problems should be recorded in a validation report before
architecture changes are made.

## Core Functional Areas

### 1. Personal Mode Baseline

Purpose: organization mode must not damage the single-user local KB workflow.

Acceptance checks:

- A fresh or default settings file opens in personal mode.
- Missing organization settings do not show organization sources or organization
  navigation.
- Local search returns local cards only.
- Local route, status, type, and source filters still work.
- Local card detail opens and shows if/action/predict/use sections.
- Language switching does not change canonical card content or hide data.
- Cards with Skill dependencies show a compact cover badge and detail still
  shows the exact dependency list.

Recommended tests:

- `tests/test_e2e_personal_mode.py`
- Existing supporting tests: `test_kb_desktop_ui.py`,
  `test_desktop_settings.py`, `test_search_rejected_candidates.py`.

### 2. Organization Source Connection

Purpose: organization mode should activate only after a valid organization KB
source is configured and mirrored.

Acceptance checks:

- A repository without `khaos_org_kb.yaml` is rejected.
- A repository with invalid kind, schema, or missing required KB paths is
  rejected.
- A valid local or Git-backed organization repo is mirrored and validated.
- Existing mirrors are synchronized into the local organization cache before
  organization browsing uses them.
- GitHub identity discovery and maintainer controls are gated behind validated
  organization mode.
- Switching back to personal mode removes organization search and browsing
  sources without deleting local KB data.

Recommended tests:

- `tests/test_e2e_organization_connection.py`
- Existing supporting tests: `test_org_sources.py`,
  `test_desktop_settings.py`, `test_org_automation.py`.

### 3. Multi-Source Search And Read-Only Browsing

Purpose: local and organization cards should appear in one usable browsing
surface with clear source labels.

Organization browsing uses synchronized local mirrors as the organization
cache pool. Runtime search should read that local cache, not reach out to the
remote repository for every query.

Acceptance checks:

- Local results rank before organization results for equal relevance.
- Organization cards are marked read-only.
- Source labels distinguish local public/private/candidate from organization
  trusted/candidate cards.
- Author display falls back clearly when organization author metadata is absent.
- Exact same-hash organization cards are hidden when the content already exists
  locally.
- Same card id with different content hash can surface as a new organization
  version.

Recommended tests:

- `tests/test_e2e_multi_source_browsing.py`
- Existing supporting tests: `test_multi_source_search.py`,
  `test_organization_adoption.py`.

### 4. Organization Card Adoption On Use

Purpose: an organization card becomes local maintenance material only after it
is actually used.

Acceptance checks:

- Merely viewing or searching an organization card does not create a local
  adopted copy.
- Using an organization card creates one adopted candidate if its exchange hash
  is new locally.
- If the same exchange hash already exists locally, no duplicate adopted file
  is created.
- Reusing the same organization card updates local usage metadata rather than
  creating another copy.
- Deleting a local adopted copy does not make the same downloaded hash reappear
  as new organization content.
- A later organization card with a different exchange hash can surface again.

Recommended tests:

- `tests/test_e2e_organization_adoption.py`
- Existing supporting tests: `test_organization_adoption.py`.

### 5. Card-Bound Skill Bundle Lifecycle

Purpose: Skills should follow cards, but Skill identity and deduplication should
remain stable across machines.

Acceptance checks:

- A local card that depends on a local Skill exports a card-bound Skill bundle
  in the organization outbox.
- The bundle records `bundle_id`, `content_hash`, `version_time`,
  `original_author`, read-only import behavior, and update policy.
- Multiple local cards pointing to the same `bundle_id` export the local latest
  version, not an older card-carried copy.
- An organization card with a card-bound Skill bundle installs that bundle into
  local organization Skill storage when the card is adopted.
- Local imported organization Skill storage keeps only the latest approved
  version per `bundle_id`.
- Duplicate Skill names or ids do not define identity.
- Approved Skill auto-install requires an approved status, pinned version or
  version time, pinned sha256 content hash, and local policy permission.
- Candidate, rejected, unknown, or unpinned Skills are not silently installed.

Recommended tests:

- `tests/test_e2e_skill_bundle_lifecycle.py`
- Existing supporting tests: `test_skill_sharing.py`,
  `test_organization_adoption.py`, `test_org_checks.py`.

### 6. Local-To-Organization Contribution Flow

Purpose: local machines should contribute only reusable public knowledge and
avoid duplicate exchange payloads.

Acceptance checks:

- Public model and heuristic cards can be exported as organization candidates.
- Private cards, preference cards, user-specific cards, and clean adopted
  organization cards are skipped.
- The same exchange hash is exported at most once in one outbox.
- Hashes already exported from this installation are skipped.
- Hashes already present in the current organization repository are skipped.
- Outbox files can be copied into an organization repo import branch with nested
  Skill bundle files preserved.
- Low-risk import paths can pass organization checks.
- Protected trusted-card changes are blocked by low-risk checks.

Recommended tests:

- `tests/test_e2e_org_contribution_flow.py`
- Existing supporting tests: `test_org_outbox.py`,
  `test_org_contribution.py`, `test_org_checks.py`,
  `test_org_multi_machine.py`.

### 7. Organization Maintenance Cleanup

Purpose: organization maintenance must make the shared library cleaner, not only
validate file formats.

Acceptance checks:

- Exact duplicate card content hashes across trusted, candidate, and import
  paths are detected.
- A duplicate of local or organization trusted content is not promoted as a new
  organization experience.
- Weak or random candidate cards are marked as not recommended, rejected, or
  kept out of the trusted path.
- Similar candidate cards produce a merge proposal or a consolidated card
  proposal.
- Overloaded candidate cards produce a split proposal or an explicit
  skip-with-reason decision.
- Superseded cards are marked deprecated/superseded or folded into the stronger
  replacement.
- Trusted cards may receive confidence adjustments, status adjustments,
  rewrites, merges, splits, or deletion proposals when evidence supports the
  change.
- Deletion is allowed in the long-term organization maintenance model, but it
  must be proposal-driven, audited, and recoverable through Git history or a
  tombstone/audit record.
- Confidence adjustments are first-class maintenance actions. They should move
  gradually unless the evidence is strong enough for a larger status change.
- Merging cards preserves source evidence, authorship metadata, history, and
  Skill dependencies.
- If merged cards depend on the same Skill bundle, the merged result points at
  one latest approved bundle version.
- If a card is rejected, its unapproved card-bound Skill bundle is not promoted
  to approved.

Recommended tests:

- `tests/test_e2e_organization_maintenance_cleanup.py`
- Existing supporting tests: `test_org_checks.py`,
  `test_org_maintenance.py`, `test_kb_consolidate_apply_worker1.py`,
  `test_kb_semantic_review.py`.

## Multi-Machine Scenario

The main end-to-end scenario should simulate:

```text
tmp/
  org_repo/
  machine_a/
  machine_b/
```

Flow:

1. Create a valid organization KB repository.
2. Create machine A with a public reusable card and a local Skill.
3. Connect machine A and machine B to the organization repo.
4. Machine A exports an organization outbox item with the card-bound Skill
   bundle.
5. Copy the outbox into the organization repo import path.
6. Run organization checks.
7. Machine B searches organization content.
8. Machine B finds organization content from its synchronized local
   organization cache pool.
9. Machine B adopts one organization card only after use.
10. Machine B receives the card-bound Skill bundle locally.
11. Machine B modifies the adopted card into reusable feedback.
12. Machine B exports feedback only if the new exchange hash is not already
    known.
13. Organization maintenance detects duplicates, weak candidates, and merge
    opportunities before any promotion.

This scenario should stay local and deterministic. A live private GitHub
sandbox test can be run later as a manual or integration smoke test, but local
temporary repos should be the default automated acceptance path.

## Manual UI Acceptance

Manual checks should be run after the e2e tests pass:

- Settings dialog: personal/organization mode dropdowns are readable.
- Organization repo field is disabled in personal mode and enabled in
  organization mode.
- Organization validation status is clear.
- Main card board shows local/organization source labels clearly.
- Cards with Skill dependencies show a small `1 Skill` / `2 Skills` or
  `1 个技能` / `2 个技能` badge.
- Card detail shows exact Skill dependencies and registry/install status.
- Organization panel opens once, shows a loading state immediately, and does
  not open duplicate windows on repeated clicks.
- Chinese and English displays show corresponding information with no missing
  fields.
- Mouse wheel scrolling feels fast enough for dense card boards.

## Structure Review Gate

After the acceptance tests exist, run a structure review before refactoring.

Record findings in `docs/organization_structure_audit.md`.

Review areas:

- `local_kb/org_*` module boundaries.
- `local_kb/skill_sharing.py` size and responsibilities.
- `local_kb/desktop_app.py` UI responsibilities.
- repeated organization repository fixture setup in tests.
- reusable e2e test helpers.
- scripts that duplicate library behavior.

Only apply low-risk cleanup immediately. Larger changes should be listed with:

- problem;
- affected files;
- risk;
- proposed target shape;
- tests required before/after;
- whether the cleanup is blocking functional acceptance.

## Done Criteria

Organization mode is functionally accepted when:

- all existing unit/module tests pass;
- all new e2e acceptance tests pass;
- installer `--check --json` reports `ok: true`;
- manual UI checklist has been run and recorded;
- organization maintenance cleanup has deterministic coverage for duplicate,
  weak, similar, and Skill-linked candidates;
- structure audit exists and distinguishes small safe cleanup from larger
  architectural work.
