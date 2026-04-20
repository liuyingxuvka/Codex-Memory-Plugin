# Project Specification: Local Predictive Knowledge Library for Codex

## Status

This document is the authoritative implementation brief for Codex in this repository.

Implement **v0.1 only**. Optimize for clarity, maintainability, and explicit review. Do not jump ahead to vector databases, autonomous memory growth, embeddings, MCP services, or subagent orchestration unless a later task explicitly asks for them.

## 1. Objective

Build a **local, file-based predictive knowledge library** that Codex can consult before solving tasks.

The library is meant to store reusable local experience in a structured way. It is not a general encyclopedia and not a hidden global memory. Its role is narrower:

- preserve reusable patterns
- preserve user-specific preferences when appropriate
- preserve domain heuristics and lessons learned
- help Codex predict likely outcomes under known contexts
- help Codex choose better actions before answering or editing code

The first version should be simple enough that a human can inspect every file, understand every score, and review every update.

## 2. Core Concept

### 2.1 Each entry is a local predictive model card

Every knowledge entry in this repository should be treated as a **bounded predictive model**, not merely a loose note and not a universal truth.

A model card answers the following questions:

1. **In what scenario does this apply?**
2. **What action, input, or condition is under consideration?**
3. **What result is expected or likely?**
4. **What should Codex do with that prediction?**
5. **How confident are we, and where did this come from?**

This means even a preference can be expressed predictively.

Example:

- Scenario: work email drafting
- Action/input: no language explicitly requested
- Predicted result: English is the preferred output
- Operational use: draft in English unless the user overrides it

Likewise, a debugging heuristic can also be predictive.

Example:

- Scenario: behavior changed after dependency upgrade
- Action/input: skip release notes and start deep debugging immediately
- Predicted result: investigation cost likely increases and obvious causes may be missed
- Operational use: check version, changelog, and release notes first

### 2.2 Local, partial, and conditional

Each model card is intentionally **local** and **conditional**. It is not meant to cover every situation.

A card should only claim what it can justify within a defined scope. A card may include case splits when outcomes differ across conditions.

### 2.3 Human-auditable over clever

The system should remain understandable without hidden model behavior. If a human cannot explain why a card was retrieved or why it was trusted, the design is too opaque for v0.1.

## 3. Design Principles

1. **Local-first**  
   The first implementation runs entirely on local files.

2. **Path-first retrieval**  
   Retrieval should not depend on flat keyword matching alone. It should first locate the relevant direction of thought.

3. **Predictive representation**  
   Store expectation structures, not only descriptive notes.

4. **Multi-index memory palace**  
   Entries should be reachable through a main route and additional cross routes.

5. **Candidate-first updates**  
   New experience should land in `kb/candidates/` first, never directly in trusted stores unless explicitly requested.

6. **Public/private separation**  
   User-specific or sensitive knowledge stays private by default.

7. **No hidden automation in v0.1**  
   No automatic promotion, no silent write-back, no agent self-expansion.

8. **Simple scoring**  
   Use explainable scoring heuristics instead of opaque retrieval models.

## 4. Retrieval Philosophy: Hierarchical Navigation Before Keyword Matching

The user intent for this project is not “search by isolated keywords only.” The intended behavior is closer to a **memory palace with multiple indexes**.

Codex should first determine the **direction** of the task, then progressively narrow to a sub-direction.

### 4.1 Main route

Each entry should have a `domain_path`, for example:

- `work / reporting / ppt`
- `engineering / debugging / version-change`
- `work / communication / email`
- `research / literature / summarization`

This is the primary route through which the entry should be found.

### 4.2 Cross routes

Each entry may also define `cross_index`, for example:

- `design/presentation/aesthetics`
- `communication/slides/visual-quality`
- `troubleshooting/dependency/regression`

These routes let one entry be discoverable from several conceptual directions without duplicating the file.

### 4.3 Retrieval order

The retrieval logic for v0.1 should follow this order:

1. Infer the **primary route** from the current task.
2. Infer up to **three secondary routes**.
3. Search for entries whose `domain_path` matches the primary route prefix.
4. Expand to entries whose `cross_index` overlaps with the primary or secondary routes.
5. Apply lexical matching on title, tags, trigger keywords, and body.
6. Re-rank by confidence and trust status.

### 4.4 Why this matters

This structure is important because many useful entries do not share the same surface words. A flat keyword search can miss conceptually related entries, while a route-based search can preserve conceptual structure.

## 5. v0.1 Scope

### 5.1 In scope

- YAML-based local storage
- public / private / candidate separation
- hierarchical `domain_path`
- `cross_index` support
- explainable scoring
- one retrieval skill
- one candidate-capture script
- example entries
- small evaluation cases
- documentation for Codex

### 5.2 Explicitly out of scope for v0.1

- embeddings or vector search
- external databases
- automatic trust promotion
- background memory growth
- hidden autonomous write-back
- MCP-backed knowledge services
- default subagent workflows
- probabilistic calibration infrastructure
- graph databases

Subagents are available in current Codex releases, but they are more expensive and only run when explicitly requested. They are not needed for this first version.

## 6. Repository Architecture

The repository should be organized so the file system itself supports the conceptual hierarchy.

```text
.
├─ AGENTS.md
├─ PROJECT_SPEC.md
├─ README.md
├─ .agents/
│  └─ skills/
│     └─ local-kb-retrieve/
│        ├─ SKILL.md
│        ├─ agents/openai.yaml
│        └─ scripts/
│           ├─ kb_search.py
│           └─ kb_capture_candidate.py
├─ kb/
│  ├─ public/
│  ├─ private/
│  └─ candidates/
├─ schemas/
│  └─ kb_entry.example.yaml
└─ tests/
   └─ eval_cases.yaml
```

Codex currently discovers repository skills from `.agents/skills/...`, and a skill is a directory containing `SKILL.md` plus optional scripts and metadata.

## 7. Knowledge Entry Schema

### 7.1 Required fields for v0.1

Each entry should support the following structure:

- `id`: stable identifier
- `title`: short readable title
- `type`: `model`, `preference`, `heuristic`, or `fact`
- `scope`: `public` or `private`
- `domain_path`: ordered list representing the main conceptual route
- `cross_index`: additional conceptual routes
- `tags`: lightweight retrieval hints
- `trigger_keywords`: lexical triggers
- `if`: applicability notes / conditions
- `action`: what action or input is being evaluated
- `predict`: expected result and optional case splits
- `use`: how Codex should apply the prediction
- `confidence`: 0 to 1
- `source`: origin metadata
- `status`: `candidate`, `trusted`, or `deprecated`
- `updated_at`: ISO date

### 7.2 Schema interpretation

A card is operational, not merely descriptive.

- `if` defines the situation
- `action` defines what is being attempted or observed
- `predict` defines the expected result
- `use` defines what Codex should do because of that prediction

This keeps the knowledge unit useful for action selection.

## 8. Retrieval Algorithm for v0.1

The implementation should remain intentionally simple.

### 8.1 Inputs

The search tool should accept:

- `--query`: free-text task summary
- `--path-hint`: optional route hint such as `work/reporting/ppt`
- `--top-k`: result count

### 8.2 Scoring components

The search score should combine:

- `domain_path` prefix match
- `domain_path` token overlap
- `cross_index` token overlap
- title match
- tag match
- trigger keyword match
- body match
- confidence bonus
- trusted / deprecated status bonus or penalty

A simple explainable formula is preferred. For example:

```text
score =
  8 * path_prefix_len
+ 5 * domain_path_overlap
+ 4 * cross_index_overlap
+ 3 * title_match
+ 5 * tag_match
+ 4 * trigger_match
+ 1 * body_match
+ 2 * confidence
+ trusted_bonus
- deprecated_penalty
```

The exact constants can be adjusted, but the logic should remain easy to inspect.

### 8.3 Retrieval behavior

- If `path-hint` exists, use it strongly.
- If no path hint exists, fall back to lexical search.
- Always return a small ranked list.
- Prefer `trusted` over `candidate` when relevance is similar.
- Never treat retrieval as certainty.

## 9. Skill Behavior

The repository should provide one initial skill: `local-kb-retrieve`.

The skill should do the following:

1. Summarize the task in one short sentence.
2. Infer one primary `domain_path` and up to three alternative conceptual routes.
3. Run the local search script with both a path hint and a textual query.
4. Review the top results.
5. Prefer entries with stronger path alignment, `trusted` status, and higher confidence.
6. Use retrieved entries as bounded context.
7. State which entry ids influenced the answer.
8. If a reusable new lesson emerges, write only to `kb/candidates/` unless explicitly instructed otherwise.

Skills are the reusable workflow layer in Codex, while plugins are the installable distribution unit. This is the right reason to keep the workflow local first and package later only when stable.

## 10. Update and Governance Rules

### 10.1 Promotion policy

All new knowledge should enter `kb/candidates/` first.

Promotion to `kb/public/` or `kb/private/` should require explicit review.

### 10.2 Conflict handling

Priority order:

1. direct user instruction in the current conversation
2. explicit repository instructions
3. trusted KB entry
4. candidate KB entry

### 10.3 Privacy

- user-specific preferences go to `private`
- general engineering heuristics may go to `public`
- private content should stay out of public commits by default

### 10.4 Deprecation

Entries should never be silently deleted when they become weak or obsolete. Prefer `status: deprecated` with an updated note if needed.

## 11. Implementation Plan for Codex

Codex should treat the following as the implementation sequence.

### Phase 1 — Align the schema with the predictive model concept

Tasks:

1. Update `schemas/kb_entry.example.yaml`.
2. Update sample entries so they use `domain_path`, `cross_index`, `action`, `predict`, and `use`.
3. Keep backward compatibility where practical.

### Phase 2 — Refactor retrieval toward hierarchical routing

Tasks:

1. Update `kb_search.py` to accept `--path-hint`.
2. Add scoring for `domain_path` and `cross_index`.
3. Improve rendering so results show:
   - id
   - title
   - domain path
   - predicted result
   - operational guidance
   - score
4. Keep the logic file-based and deterministic.

### Phase 3 — Refactor candidate capture

Tasks:

1. Update `kb_capture_candidate.py` so it can write predictive model fields.
2. Support `domain_path`, `cross_index`, `action`, `expected_result`, and `guidance`.
3. Continue writing to `kb/candidates/` only.

### Phase 4 — Update the skill and repository guidance

Tasks:

1. Update `SKILL.md` to instruct path-first retrieval.
2. Keep `AGENTS.md` short and routing-focused.
3. Ensure `AGENTS.md` tells Codex to read this specification before architectural changes.

Codex reads `AGENTS.md` before work and merges project guidance by directory depth, so repository-level instructions should stay small and stable while deeper documents carry the full plan.

### Phase 5 — Add minimal evaluation coverage

Tasks:

1. Expand `tests/eval_cases.yaml`.
2. Include route-based examples, not only keyword examples.
3. Verify that relevant entries rank near the top for representative tasks.

## 12. Definition of Done for v0.1

The first version is done when all of the following are true:

- repository contains the predictive schema documentation
- repository contains at least two example model cards
- search script supports `--path-hint`
- search output exposes domain path, predicted result, and guidance
- capture script can write predictive candidate entries
- skill instructions reflect route-first retrieval
- `AGENTS.md` points Codex to this design brief
- evaluation cases exist for at least a few representative tasks
- no embeddings, no autonomous promotion, no external services are required

## 13. GitHub Publication Plan

Do not publish immediately.

First stabilize locally.

Only after local usage confirms the structure is helpful should the repository be prepared for sharing. At that point:

1. remove or exclude private examples
2. keep only public examples and generic templates
3. add a concise public README
4. document the schema and workflow clearly
5. include a small evaluation set
6. keep the project opinionated but narrow

The shared repository should distribute the **workflow and schema**, not private memory.

## 14. Non-Goals and Anti-Patterns

Do not let the first version drift into these patterns:

- a generic note-taking pile
- a hidden memory system that rewrites itself
- a vector-search project before there is enough data
- a graph database project before there is enough operational value
- a fully autonomous self-belief system
- a tool that treats weak hypotheses as durable truth

## 15. Operational Reminder for Codex

When modifying this repository:

- prefer the simplest working implementation
- preserve human readability
- make scoring explainable
- do not silently introduce heavy dependencies
- do not expand scope beyond v0.1
- keep changes incremental and reviewable

The purpose of this repository is not to simulate a perfect mind. The purpose is to build a practical local scaffold that helps Codex retrieve reusable predictive experience in a controlled way.
