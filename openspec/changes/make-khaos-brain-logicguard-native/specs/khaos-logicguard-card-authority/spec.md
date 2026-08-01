## ADDED Requirements

### Requirement: Every current card is an exact LogicGuard model projection
The system SHALL treat a card as current knowledge only when it binds to one exact canonical LogicGuard model revision, ArgumentBlock, and root claim node, and the card's projection digest matches a deterministic projection of that exact authority.

#### Scenario: Valid exact binding
- **WHEN** a card names a current projection schema, model id, revision id, block id, root node id, scope, and projection digest that match the scoped model store
- **THEN** the system may admit the card to lifecycle-eligible indexing and SHALL return the exact binding in retrieval receipts

#### Scenario: Missing or mismatched authority
- **WHEN** the model, exact revision, block, root node, scope, or recomputed projection digest is missing or mismatched
- **THEN** the system SHALL visibly reject the card from the active index and SHALL NOT substitute a model head, YAML semantics, alias, or fallback reader

### Requirement: Predictive experience is represented as an ArgumentBlock
Each canonical predictive unit MUST contain one root ArgumentBlock whose root claim represents the predicted outcome and whose declared members represent the available context/premise, action/method, warrant, evidence/provenance, assumption, rebuttal, qualifier, and limitation roles. Missing roles MUST remain explicit diagnostics or gaps and MUST NOT be fabricated.

#### Scenario: Rich supported experience
- **WHEN** an observation provides context, an action, a result, a licensing reason, and independent evidence
- **THEN** the model SHALL represent those meanings with typed nodes and edges inside the ArgumentBlock and SHALL preserve typed provenance on evidentiary nodes

#### Scenario: Sparse legacy experience
- **WHEN** a legacy card has only `if`, `action`, `predict`, and `use` text with no grounded evidence or warrant
- **THEN** migration SHALL create only licensed context/method/claim content, record missing support roles as gaps, and SHALL NOT relabel AI-authored text as independent evidence

### Requirement: Foreground intake records observations while Sleep alone publishes candidates
Ordinary task postflight and feedback SHALL append bounded structured history only.
The normal-runtime launcher MUST NOT expose a command or script that writes a
candidate card directly. Sleep SHALL be the sole owner that admits an observation
or upgrades a residual raw candidate into current card, model, mesh, projection,
and active-index authority.

#### Scenario: A task suggests a new candidate
- **WHEN** foreground feedback records `new-candidate` as its suggested action
- **THEN** it SHALL append one observation and matching terminal receipt, SHALL leave candidate/model/mesh/index authority byte-for-byte unchanged, and SHALL defer admission to Sleep

#### Scenario: A retired or external writer left a raw candidate
- **WHEN** Sleep freezes a batch containing a candidate without the current projection schema or exact LogicGuard binding
- **THEN** Sleep SHALL either upgrade and publish it through one complete model-first generation or leave the prior generation authoritative with a visible blocked disposition; foreground retrieval SHALL NOT read the raw YAML as fallback

#### Scenario: A raw candidate carries ambiguous partial current authority
- **WHEN** a schema-less candidate declares any current projection binding field, or declares an unsupported projection schema
- **THEN** Sleep SHALL block visibly without guessing the missing binding, publishing a partial generation, or enabling a compatibility reader

#### Scenario: A pre-fix open batch omitted the residual raw candidate
- **WHEN** an immutable Sleep batch was frozen before raw-candidate inventory existed and remains open when the exact residual is discovered
- **THEN** one resumed Sleep owner MAY bind that exact path and content to the open batch, SHALL record `legacy_plan_omission_repaired`, and SHALL atomically upgrade it or preserve the prior generation; a newly frozen batch MUST represent the residual as an ordinary batch work item

#### Scenario: A caller invokes the retired direct candidate command
- **WHEN** a caller requests `capture-candidate` or the removed candidate-writer script
- **THEN** the current launcher SHALL reject the command visibly and SHALL direct current integrations to structured feedback rather than preserve an alias

### Requirement: Sleep freezes raw-candidate repair as explicit upgrade work
Sleep MUST inventory schema-less, unbound candidate files under the candidate
authority root before ordinary candidate catalog loading. Each admitted residual
MUST have one deterministic work identity and one exact path/content digest. The
repair loader MAY omit only those exact replacing paths while proving every
remaining projection still matches the current generation manifest.

#### Scenario: A new Sleep batch sees one raw candidate
- **WHEN** Sleep inventories one schema-less, unbound `status=candidate` file before freezing the batch
- **THEN** the frozen plan SHALL contain one deterministic raw-candidate-upgrade item and terminal success SHALL name its path, digest, batch binding, and current projection generation

#### Scenario: Repair publication fails
- **WHEN** model construction, projection validation, compare-and-swap publication, or final index validation fails for the raw-candidate upgrade
- **THEN** the previous complete generation SHALL remain authoritative, the raw file SHALL remain excluded from retrieval, and the receipt SHALL expose the failed repair without a retry reader or partial success claim

### Requirement: Projection fields have no independent semantic authority
The human-readable `if`, `action`, `predict`, `use`, and derived neighbor fields SHALL be generated from the bound model revision. Normal runtime MUST NOT accept edits to those fields as a canonical knowledge change or use `related_cards` as an independent relationship source.

#### Scenario: Projection text is edited without a model revision
- **WHEN** YAML display text changes while the bound model revision and projection digest remain unchanged
- **THEN** projection validation SHALL fail and retrieval SHALL exclude the card until Sleep commits a canonical model revision and regenerates the projection

#### Scenario: Legacy related card list survives in input
- **WHEN** a normal-runtime card contains `related_cards` values that are absent from its exact mesh neighborhood
- **THEN** the system SHALL ignore them as authority, report a projection mismatch or retired-field residual, and SHALL NOT create graph edges from them

### Requirement: Knowledge publication is model first and atomic
Every knowledge-changing operation SHALL commit and validate canonical model and affected mesh revisions before it publishes card projections and the active index. A partial or conflicting operation MUST leave the prior complete generation authoritative.

#### Scenario: Successful model-first publication
- **WHEN** Sleep commits the expected model and mesh revisions and all projections validate
- **THEN** the system SHALL publish those projections and one active-index generation whose receipt binds every exact revision and digest

#### Scenario: Compare-and-swap conflict
- **WHEN** a model or mesh head differs from the expected revision during commit
- **THEN** the system SHALL publish no new projection or index generation, preserve the concurrent authority, and return a retryable conflict with no silent overwrite

### Requirement: Canonical authority is partitioned by privacy scope
Public, private, and candidate model/mesh authority SHALL use separate scoped stores. A scoped mesh MUST NOT contain a model, node, edge, provenance value, path, or digest from another scope, and public projections MUST be free of private material.

#### Scenario: Public graph requests a private node
- **WHEN** a public mesh proposal or public projection references a private model or node
- **THEN** validation SHALL block the commit and SHALL identify the cross-scope reference without serializing private content into public evidence

#### Scenario: Authorized local multi-scope search
- **WHEN** a local caller is authorized to search public and private scopes
- **THEN** the retrieval facade SHALL query each scoped authority separately and merge display results without persisting a mixed-scope canonical mesh

### Requirement: Organization cards are synchronized as foreign, complete snapshots
An organization-enabled machine SHALL materialize the exact active organization card set and each card's exact LogicGuard binding into one immutable local snapshot per pinned organization generation. Snapshot presence SHALL NOT create local canonical authority, an adopted overlay, or an executable Skill installation.

#### Scenario: Complete organization generation is activated
- **WHEN** the organization cycle has staged every catalog-declared active card, revision, and LogicGuard bundle and all identity and digest checks pass
- **THEN** it SHALL atomically activate the snapshot as a read-only `foreign/organization` source and SHALL expose the generation, source commit, and exact active identity set in its receipt

#### Scenario: Snapshot is incomplete or mismatched
- **WHEN** any active card, bundle, revision, digest, or expected identity is missing or mismatched
- **THEN** the cycle SHALL leave the previous complete snapshot pointer unchanged, SHALL report the sync failure visibly, and SHALL NOT mix old and new card bytes

#### Scenario: Synchronized card is used in a task
- **WHEN** local retrieval selects an applicable foreign organization card
- **THEN** it SHALL make the card available directly as read-only task context, record its foreign generation/binding, and SHALL defer any permanent localization decision to a later Sleep observation

### Requirement: Organization source cards cut over directly to the current portable contract
The versioned organization maintenance upgrade SHALL replace legacy source-card
authority with current deterministic projections and validated portable
LogicGuard bundles. Snapshot construction MAY reuse content-addressed current
bundles but MUST NOT keep a normal-runtime legacy wrapper or invent missing
support. Duplicate source ids SHALL receive one evidence-bound direct disposition
before current source activation.

#### Scenario: Legacy organization source contains sparse and duplicate cards
- **WHEN** the upgrade freezes the complete source inventory
- **THEN** it SHALL preserve each card's provenance and explicit gaps, assign stable unique current identities, publish one complete upgraded source generation, and prove zero unresolved legacy identity authority

#### Scenario: Merge or split is warranted
- **WHEN** review evidence satisfies an exact merge or split action contract
- **THEN** organization maintenance SHALL apply one reversible packet with old/new identity mapping, model/mesh reconstruction, rollback inventory, and current post-apply validation

#### Scenario: Ready merge or split packets overlap in one source generation
- **WHEN** two or more individually ready packets read or write any of the same materialized card paths
- **THEN** organization maintenance SHALL select a deterministic maximal non-overlapping packet set, SHALL defer each conflicting packet with a concrete next-generation reopen reason, and SHALL apply every selected id exactly once

#### Scenario: Maintenance removes or replaces materialized cards
- **WHEN** an accepted action deletes, merges, splits, moves, or replaces a card and its bound projection, model, mesh, or bundle
- **THEN** the publication inventory SHALL include the union of pre-apply and post-apply materialized paths, SHALL commit and verify every deletion and survivor, SHALL restore the configured base branch with a clean mirror, and SHALL leave every prior card identity with an exact audited disposition even when the active count changes

#### Scenario: Remote organization gate receives a current maintenance packet
- **WHEN** a reviewed maintenance PR contains source schema 2 cards, their exact LogicGuard model, mesh, projection, and bundle files, the current catalog and manifest, and the cleanup audit
- **THEN** the installed GitHub checker SHALL validate that same current contract, SHALL reject missing or mismatched packet members, and SHALL license automatic merge only after the remote check succeeds; local maintenance success or an auto-merge label alone SHALL NOT claim organization-main adoption

#### Scenario: The same generated packet crosses operating-system checkouts
- **WHEN** the organization source is materialized in a Windows worktree with CRLF text and GitHub checks out the same Git content with LF text
- **THEN** the catalog and remote checker SHALL use the declared UTF-8/LF-normalized text-digest policy, both checkouts SHALL identify the same projection content, and all semantic, binding, bundle, and exact-inventory checks SHALL remain required

#### Scenario: Automatic organization maintenance does not depend on human approval
- **GIVEN** the organization repository requires pull requests and the current `organization-kb-checks` status context
- **WHEN** a maintenance PR carries the gated automatic-merge label and the remote content check succeeds
- **THEN** the branch policy SHALL require zero approving reviews, the workflow SHALL merge without a human click, and administrator bypass, force push, or direct unreviewed adoption SHALL remain forbidden

#### Scenario: An import carries a card-bound Skill bundle
- **WHEN** an organization proposal contains nested Skill content and bundle metadata below the contributor import lane
- **THEN** card validation SHALL inspect only the proposal card as a card, SHALL keep the nested metadata under path, privacy, hash, author, version, and dependency checks, and SHALL NOT reject Skill metadata merely because it has no card id
