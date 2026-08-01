## Why

Khaos Brain currently treats each YAML card as an independent predictive record and uses `related_cards` as a shallow link. That shape cannot make evidence, warrants, assumptions, rebuttals, boundaries, and model-level gaps first-class, so Sleep can reorganize files but cannot reliably consolidate a knowledge model, and Dream can test retrieval examples but cannot validate the whole reasoning structure.

LogicGuard now provides immutable single-model revisions, revision-pinned ModelMesh, structural evaluation, sparse simulation, source provenance, and graph projection. Khaos Brain should therefore move its authority below the card layer: every card becomes a projection of a canonical LogicGuard ArgumentBlock, Sleep maintains the model mesh, Dream tests that mesh, and retrieval navigates the resulting model rather than a flat card list.

## What Changes

- **BREAKING** Replace standalone YAML card semantics with canonical LogicGuard model authority. A current card is valid only when it binds to one exact model revision, ArgumentBlock, and root claim node and its projection digest matches that authority.
- Keep `if`, `action`, `predict`, and `use` as human-readable projection fields only. Normal runtime MUST NOT treat them, `related_cards`, or legacy aliases as independent knowledge authority.
- Represent each predictive experience as a small LogicGuard model containing declared context/premise, action or method, predicted claim, warrant, evidence/provenance, assumptions, rebuttals, qualifiers, and limitations as available. Missing roles remain explicit model gaps rather than invented content.
- Make Sleep the only Khaos Brain maintenance owner that may commit canonical model and ModelMesh revisions. Sleep groups nodes through mesh memberships and grounded cross-model edges, evaluates support gaps, and publishes card projections plus the active index only after the exact model revision commits.
- Make Dream read one exact mesh revision, run bounded counterexample, missing-evidence, missing-warrant, rebuttal, boundary, and fragility experiments, and emit immutable experiment evidence plus an idempotent typed handoff to Sleep. Dream MUST NOT mutate canonical models, card projections, or the active index.
- Make foreground retrieval fail closed on a current model-bound active index, return exact card/node bindings, and expand through a bounded revision-pinned model neighborhood. Remove normal-runtime flat YAML scan and `related_cards` fallback paths.
- Add a graph-first desktop projection that explains the selected claim, local support/rebuttal/boundary nodes, model membership, revision, and open gaps without exposing private-scope nodes on public surfaces.
- **BREAKING** Add a versioned, resumable, rollbackable direct-to-current migration that consumes old YAML authority only inside the upgrade transaction, creates canonical LogicGuard models and meshes, rewrites YAML as projections, proves zero old-authority residuals, and otherwise rolls back while maintenance automations remain paused.
- Partition canonical model and mesh stores by privacy scope. Cross-scope canonical edges are forbidden; multi-scope retrieval merges separately authorized results without materializing a mixed authority graph.
- Update Sleep, Dream, retrieval, update, and organization Skills/prompts; the installer; README; PROJECT_SPEC; UI copy; validation models; and source-only author contracts so the dependency on ResearchGuard's `researchguard.logic` member and the consumer boundary are explicit.
- **BREAKING** Replace task-time organization-card/lazy-bundle download and human adoption with a complete, validated local organization snapshot. Ordinary retrieval may automatically use a relevant cached organization card as foreign, read-only context; only actual use outcomes may be handed to Sleep for local assimilation.
- Keep exactly two scheduled owners: one local maintenance cycle whose internal phases are Sleep then Dream (or Sleep-only resume when a frozen batch must be continued), and one organization cycle whose first phase synchronizes the complete active-card snapshot before organization maintenance and contribution phases. Neither cycle becomes a second canonical model publisher.
- Synchronize the clean installed projections, repository source identity, FlowGuard adoption record, and local Git identity only after the stable source snapshot and terminal validation evidence are frozen; preserve unrelated peer changes and keep skipped or blocked evidence visible.
- **BREAKING** Make multi-source retrieval one globally ranked, content-deduplicated result set and one durable receipt. Local authority wins an exact duplicate or an explicit conflict, but source ordering alone MUST NOT hide a better-matching organization card.
- Separate `viewed`, `selected`, `used`, and `outcome_recorded`. Only an actual task use may create a foreign-card use event, and that event plus its outcome MUST bind the exact combined retrieval receipt, organization snapshot, bundle, and LogicGuard revision before Sleep may calibrate local use.
- Upgrade legacy organization-source cards directly to the current portable card and LogicGuard-bundle contract in the organization maintenance transaction. Snapshot-time structural wrapping is not a permanent compatibility route. Merge and split actions MUST have reversible apply packets or an evidence-bound executable reopen condition.
- Keep the local and organization scheduled owners operationally independent. They retain separate cycle leases and failure domains and share only the exact global write lease around overlapping durable mutations; one owner's blocker MUST NOT automatically mark the other owner `not_run`.
- Replace run-id-only cycle reuse with immutable schema-v3 receipts bound to normalized request, source/tool identities, pinned generations, child receipt digests, and terminal status. A stale, partial, blocked, timed-out, or input-mismatched receipt is never reusable.
- Make final Model-Test Alignment and TestMesh consume the current terminal child receipts and node inventory. A `frozen_not_run` planning artifact may be valid planning evidence but MUST block readiness rather than being projected as a passed execution check.

## Capabilities

### New Capabilities

- `khaos-logicguard-card-authority`: Canonical per-card LogicGuard models, ArgumentBlock shape, exact card projection bindings, atomic model-first writes, provenance, and privacy partitioning.
- `khaos-logicguard-model-maintenance`: Sleep-owned ModelMesh consolidation and Dream-owned revision-pinned validation/handoff without duplicate mutation authority.
- `khaos-logicguard-retrieval`: Model-bound active indexing, exact-node retrieval, bounded graph navigation, explainable UI projection, and fail-closed no-fallback behavior.
- `khaos-logicguard-migration`: Direct-to-current migration from legacy card authority, zero residuals, concurrency control, resumability, rollback, and installer integration.
- `khaos-logicguard-assurance`: Executable FlowGuard ownership model, model/code/test alignment, disjoint target-owned evidence, ResearchGuard logic dependency checks, clean consumer projection, performance/privacy gates, and documentation parity.

### Modified Capabilities

<!-- The overlapping lifecycle and Sleep/Dream capabilities currently exist only in active, unarchived changes. This change records explicit reconciliation dependencies instead of pretending those drafts are archived canonical specs. -->

## Impact

- Core modules: `local_kb.store`, `local_kb.active_index`, `local_kb.search`, `local_kb.lifecycle`, `local_kb.dream`, `local_kb.maintenance_migration`, desktop view models, and new LogicGuard model/projection/maintenance adapters.
- Persistent state: scoped LogicGuard model stores, scoped ModelMesh stores, model evaluation/simulation receipts, YAML card projections, active-index records, migration journal/backup, and Sleep/Dream receipts.
- Public contracts: current card projection schema, retrieval result payloads, desktop detail/graph surfaces, maintenance receipts, installer checklist, and upgrade readiness.
- Dependencies: the public ResearchGuard package must be pinned to one exact current source identity and its `researchguard.logic` member must expose the required P0/P1 APIs, current schemas, and fingerprints. The retired standalone LogicGuard package is not installed or consulted. FlowGuard and official OpenSpec remain external assurance/process owners. SkillGuard is used only for source-side maintenance of the repository's own skills and is not a product-runtime authority.
- Compatibility: no normal-runtime dual reader, alias, fallback search, alternate model, or silent downgrade is permitted. Legacy card authority is bounded upgrade input only.
- Organization exchange: active organization cards and their exact LogicGuard bundles are materialized into a local foreign snapshot with atomic pointer replacement. Snapshot presence never means local adoption, and executable Skill payloads are not installed merely because a card was synchronized.
