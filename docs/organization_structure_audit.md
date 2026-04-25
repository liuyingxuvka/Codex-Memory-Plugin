# Organization Mode Structure Audit

This audit records structure and capability gaps found while starting the
organization-mode functional acceptance pass. It distinguishes small safe fixes
from larger architecture work that should not be hidden inside test cleanup.

## Current State

Organization mode is now covered by a mixture of module tests and local e2e
tests. Existing tests cover source validation, multi-source search, adoption,
outbox generation, contribution branch preparation, organization checks,
Skill bundle sharing, automation gates, and a two-profile local organization
flow. The newer two-machine cache-pool lifecycle test covers the intended
sync model: machines search a synchronized local organization mirror/cache, not
the remote repository directly.

The main gap is not raw test count. The main gap is that the tests were not yet
organized as a named functional acceptance suite, and organization maintenance
cleanup is still mostly a check/report workflow rather than an apply workflow.

## Module Boundary Findings

### `local_kb/org_sources.py`

Current role: validate, clone, fetch, and connect organization repositories.

Assessment: boundary is reasonable. Keep as the source/mirror layer.
The local mirror is the organization cache pool used by browsing and search.
Existing mirrors must be updated when the source repository changes; a fetch
that does not update the worktree is not enough for cache synchronization.

Low-risk cleanup:

- add shared test helpers for valid/invalid organization repos;
- keep validation messages stable so UI and e2e tests can assert them.

### `local_kb/adoption.py`

Current role: use-on-hash adoption, exchange ledger, local adopted copies, and
card-bound Skill bundle import on organization card use.

Assessment: functionality is coherent, but the file now owns both card
adoption and imported Skill side effects.

Possible future split:

- keep card hash/adoption ledger in `adoption.py`;
- move organization Skill import-on-adoption orchestration into a small
  `org_skill_adoption.py` or `skill_sharing.py` facade if this grows.

Not blocking current acceptance.

### `local_kb/org_outbox.py`

Current role: filter local cards for organization contribution, dedupe by
exchange hash, create candidate payloads, and attach card-bound Skill bundles.

Assessment: boundary is acceptable for now, but Skill materialization makes the
module more than card-only export.

Future cleanup:

- extract outbox fixture/helper code in tests;
- keep Skill bundle materialization in `skill_sharing.py`, called by outbox.

### `local_kb/org_contribution.py`

Current role: copy generated outbox files into organization repo imports,
create branches, commit, and optionally push.

Assessment: boundary is clear. It now correctly copies nested Skill bundle
files, not only top-level YAML proposals.

Low-risk cleanup:

- add e2e assertion that nested bundle files survive contribution branch copy.

### `local_kb/org_checks.py`

Current role: validate organization repo safety, path policy, privacy, Skill
registry pinning, card duplicate hashes, and low-risk auto-merge eligibility.

Assessment: strong check/report layer. It should remain non-mutating.

Important boundary:

- duplicate hash detection is a blocker/report, not cleanup;
- duplicate Skill `id` is now a warning handle collision, not an identity
  failure;
- Skill identity belongs to `bundle_id + content_hash + version_time`.

### `local_kb/org_maintenance.py`

Current role: build a maintenance report from validation, checks, outbox count,
candidate count, skill registry count, review-skill availability, and cleanup
signals.

Assessment: currently a report/intake layer plus cleanup proposal summary. It
does not itself merge cards, delete cards, reject weak cards, or promote
candidates; those actions live in `org_cleanup.py`.

New explicit signals:

- duplicate content hash count;
- organization check summary;
- cleanup proposal action count and counts by action type;
- planned cleanup capabilities:
  - similar-card merge apply: planned;
  - weak-card rejection apply: available through `org_cleanup.py`;
  - candidate delete apply: available only when explicitly allowed;
  - Skill bundle cleanup apply: partial.

Large follow-up:

- continue expanding `org_cleanup.py` instead of overloading this report
  function.

### `local_kb/skill_sharing.py`

Current role: dependency extraction, local Skill lookup, card-bound bundle
metadata, outbox Skill bundle materialization, imported Skill bundle storage,
bundle consolidation, registry loading, auto-install eligibility, source
checkout, install, and UI dependency annotation.

Assessment: this file is now broad. It is the clearest future split candidate.

Possible target modules:

- `skill_dependencies.py`: dependency extraction and annotation payload shape.
- `skill_bundles.py`: `bundle_id`, version selection, imported bundle storage,
  bundle consolidation.
- `skill_registry.py`: organization registry load, validation normalization,
  by-id/by-bundle indexes.
- `skill_install.py`: approved Skill checkout/hash/install policy.

Do not split yet unless acceptance tests are stable, because this module is
central to card-bound Skill behavior.

### `local_kb/desktop_app.py`

Current role: complete Tk desktop UI, settings, organization panel, card board,
card detail, source filters, and display helpers.

Assessment: file is large, but recent UI changes are localized and covered by
tests. Splitting now would be higher risk than value unless a UI regression
requires it.

Possible future split:

- `desktop_text.py`: UI text and display label helpers;
- `desktop_cards.py`: card rendering helpers;
- `desktop_settings.py`: settings dialog;
- `desktop_organization.py`: organization status panel.

Not blocking current functional acceptance.

## Organization Maintenance Cleanup Gap

The user specifically asked whether organization maintenance can merge,
delete, downgrade, or reject organization cards.

Current true state:

- exact duplicate content hashes are detected and block low-risk auto-merge;
- maintenance reports now surface duplicate-hash cleanup signals;
- `org_cleanup.py` now produces deterministic cleanup proposals for duplicate
  cards, weak cards, trusted low-confidence cards, high-confidence promotion
  review, similar-title merge review, stale delete review, and card-bound Skill
  version selection;
- cleanup apply supports audited confidence/status changes, duplicate marking,
  and deletion when explicitly allowed;
- similar-card merge, overloaded-card split, trusted rewrite, and candidate
  promotion remain proposal/review only;
- local semantic review can apply some actions to a local KB, such as rewrite,
  promote, demote, deprecate, and confidence adjustment;
- semantic review merge/split decisions are currently proposal-only;
- imported organization Skill bundle cleanup is implemented locally and keeps
  the latest version per `bundle_id`;
- organization registry-level Skill cleanup is still check/index oriented.

Recommended future shape:

1. Continue using `local_kb/org_cleanup.py` as the organization cleanup
   planning and apply module.
2. It produces a deterministic proposal object before mutation. Trusted
   files and deletions are allowed later, but only through proposal, audit, and
   Git-check guarded apply.
3. Proposal types should include:
   - duplicate-hash rejection or consolidation;
   - similar-card merge proposal;
   - weak-card reject/deprecate proposal;
   - overloaded-card split proposal;
   - supersede/deprecate proposal;
   - confidence adjustment proposal;
   - trusted-card rewrite, score, merge, split, or delete proposal;
   - Skill bundle latest-version and approval-state proposal.
4. Add a separate apply path in phases:
   - first, low-risk candidate/import confidence and status adjustments;
   - then trusted confidence/status/rewrite/merge/split when checks and audit
     are stable;
   - finally deletion with tombstone or audit records.
5. GitHub checks should continue to guard final merge.

## Test Structure Findings

Current coverage is broad but unevenly named. Recommended additions:

- `tests/test_e2e_organization_connection.py`
- `tests/test_e2e_multi_source_browsing.py`
- `tests/test_e2e_organization_adoption.py`
- `tests/test_e2e_skill_bundle_lifecycle.py`
- `tests/test_e2e_org_contribution_flow.py`
- `tests/test_e2e_organization_maintenance_cleanup.py`
- `tests/test_e2e_org_cli_flow.py`

Already added in this pass:

- `tests/test_e2e_organization_connection.py`
- `tests/test_e2e_multi_source_browsing.py`
- `tests/test_e2e_organization_maintenance_cleanup.py`
- `tests/test_e2e_skill_bundle_contribution_flow.py`
- `tests/test_e2e_two_machine_cache_pool_lifecycle.py`
- `tests/test_org_cleanup.py`

Recommended helper extraction:

- `tests/org_helpers.py` now contains the shared valid org repo fixture, card
  fixture, git helper, local Skill fixture, organization connection helper, and
  organization outbox-to-candidate publisher.
- it includes a stable four-card organization sandbox fixture:
  - two cards designed to overlap with local cards for hash/similarity tests;
  - two organization-only cards for cache, adoption, and Skill lifecycle tests.

Future helper cleanup:

- migrate older e2e tests onto `tests/org_helpers.py` gradually;
- add a JSON script runner helper when CLI e2e coverage is added.

Do not extract helpers prematurely before the first few e2e tests settle.

## Immediate Low-Risk Cleanup Done

- Added functional acceptance plan documentation.
- Added e2e tests for validated organization connection and personal-mode
  fallback.
- Added e2e tests for settings-sourced multi-source browsing, same-hash hiding,
  and different-hash organization resurfacing.
- Added e2e tests for outbox -> organization import branch contribution with
  nested card-bound Skill bundle files preserved and low-risk checks passing.
- Added e2e tests for two-machine organization cache-pool sync, adoption,
  Skill import, and diverged feedback export.
- Added `tests/org_helpers.py` with the four-card sandbox fixture.
- Added `local_kb/org_cleanup.py` proposal/apply first version with confidence
  adjustment, status adjustment, duplicate marking, guarded deletion, merge
  review, and Skill version-selection proposals.
- Shortened card-bound Skill bundle organization paths to avoid Windows mirror
  sync failures from long filenames.
- Updated existing organization mirrors to `fetch` and then `pull --ff-only`
  so the local cache worktree actually updates.
- Added organization maintenance cleanup signals to the maintenance report.
- Added e2e tests for duplicate hash report-only behavior and imported Skill
  bundle latest-version cleanup.
- Kept organization card cleanup apply as planned rather than pretending it is
  implemented.

## Next Recommended Steps

1. Add CLI e2e coverage for organization configure/check/contribute/maintain
   scripts.
2. Expand `org_cleanup.py` with merge/split proposal payloads that include the
   proposed merged or split card bodies, not only action markers.
3. Add trusted rewrite apply behind explicit `allow_trusted` and GitHub check
   gates.
4. Add tombstone handling for deletion if hard delete needs a local audit file
   beyond Git history.
5. Migrate older tests to `tests/org_helpers.py` where it reduces duplication.
6. Only after the e2e suite is stable, consider splitting `skill_sharing.py` and
   `desktop_app.py`.
