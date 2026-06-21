---
name: opentsc
description: "OpenTSC v2.0: Soul/Shell architecture for interpersonal intelligence. Local, offline-first, with event graphs, judgment engine (K7), self-creation (K8), three-layer attributes, calibrated predictions, 11 VSM professions, and a pluggable zvec memory index (semantic search, identity resolution, jieba segmentation, emotion scoring) that runs with zero extra deps. Transforms implicit social judgment into explicit, queryable, auditable, evolving intelligence."
---

# OpenTSC v2.0 Skill — Soul/Shell Architecture

Use this skill when the user wants to design, build, review, or operate **OpenTSC**: a single-user, local/offline-first interpersonal intelligence system derived from the TSC doctrine.

OpenTSC turns implicit social judgment into explicit, queryable, auditable, evolving structure. It is a private intelligence and operations system — a personal war room — not a CRM.

## The Twelve Laws (non-negotiable)

### Existence
1. **Genesis immutable** — a TSC's reason for existence is set once, never changed.
2. **Soul/Shell separation** — law+memory (soul) survives shell replacement. Export soul/ = export the TSC.
3. **Identity by ID** — stable IDs, never name-anchored paths.

### Perception
4. **Append-only events** — intelligence is a stream; current state is derived.
5. **Evidence before judgment** — Admiralty rating + source on every event; reasoning chain + due date on every prediction.
6. **Draft before registry** — auto-extraction → inbox/; formal entry needs user confirmation.

### Judgment
7. **Dual codex** — rule codex (what's allowed) + judgment codex (what's good/trustworthy/worth mobilizing).
8. **Reality calibrates, not comfort** — prediction outcomes drive learning; comfort feedback is recorded but never tunes generation.
9. **Attributes from events, not hand-filled** — K7 derives attributes via judgment_codex. No direct writes.

### Evolution
10. **Grow only where needed** — minimum viable structure; new agents/skills only on proven gaps.
11. **Four-fold self-creation** — rules, agents, goals, boundaries can all self-generate through governed processes.
12. **Recursive isomorphism** — person/team/org/ecosystem use the same cycle and attribute ontology.

If an instruction conflicts with these laws, stop and ask.

## Architecture

```
Soul (portable)          Shell (replaceable)        World (entities)
├── _genesis.md          ├── kernel/ (K1-K8)        ├── players/
├── _rule_codex.md       ├── modules/ (Agent Skills) ├── npcs/humans/
├── _judgment_codex.md   ├── professions/ (11 VSM)  ├── npcs/agents/
├── _schema.md           └── genesis_engine/        ├── orgs/
├── events/ (graph)                                 └── operations/
└── calibration/
```

## Key Capabilities (v1.0)

### Event Graph (K3)
Events are independent nodes in `soul/events/`, linked to multiple entities and to each other via causal edges. Query by entity, date, admiralty. Compute full neighborhood graphs.

### Judgment Engine (K7) — core innovation
When an event arrives, K7 reads `judgment_codex` and auto-derives attribute patches. Three-layer attributes:
- **Base** (innate, slow-changing): execution_ceiling, learning_speed, resilience, reliability, autonomy
- **Skills** (event-driven levels): negotiation Lv.3, client_psych Lv.5, etc.
- **States** (temporary buff/debuff with expiry): "已读不回·可靠性存疑" debuff, 7-day countdown

Every attribute is an `AttributeClaim`: {value, confidence, provenance, reviewed, decay, source_admiralty}.

### Direct Comparison
`judgment-compare p_alice p_bob negotiation` → answers "who is stronger" without re-reading all history.

### Self-Creation Engine (K8)
Detects VSM capability gaps, generates Agent Skill drafts, validates against laws, requires player approval to activate.

### 11 Professions (VSM-complete)
founder, commander, sentinel, ingestor, distiller, oracle, herald, coordinator, operator, steward, recruiter.

### Calibration Loop
Predictions with due dates → outcome tracking → hit rate stats → judgment codex self-iteration.

## Memory & Determinism (v2.0)

The vault markdown is the **source of truth**; a derived, rebuildable **zvec
memory index** (under `soul/.index/`) gives semantic search, hybrid retrieval,
and identity resolution. Everything is **pluggable** and degrades gracefully:

- **Embedding backend** (`lite` | `local` | `api`) and **emotion backend**
  (`lexicon` | `model` | `llm`) are chosen in `soul/_config.yaml`. The core
  runs with **zero extra dependencies** — `lite` hashing vectors, a built-in
  emotion lexicon, and a regex segmenter are always available; jieba / snownlp /
  zvec / on-device models are opt-in (see `requirements.txt`).
- **Semantic recall** replaces full-vault re-reads: `index-search`,
  `identity-resolve` (kills hash-id sprawl and name drift), `index-sync`.
- **Deterministic precompute** replaces token-burning LLM scans:
  `emotion-score`, `text-segment`, `actions-stale`. Compute facts in Python;
  spend the LLM only on judgment.

## The CLI-first mandate (non-negotiable)

**Scope first — this does NOT make the agent robotic.** Understanding the
user's natural-language intent is, and remains, the agent's job: read the
request, infer what is meant, then route to the right command(s). The mandate
governs *execution*, not *understanding*. Use **`index-search`** as your
semantic recall — turn a fuzzy human ask ("谁最近在交付上靠谱？") into a
query against the index instead of a brittle keyword scan, and **fall back to
reading specific files only when no command fits**. Free-text intake stays
LLM-driven (`capture-actions`, `draft-inbox-event`, `suggest-actions`).

What the mandate forbids is wasting the LLM on *mechanical* work a command
already does. The agent **must not** hand-read or hand-write vault files for
anything a command covers. Reading every markdown file to count, find, segment,
score sentiment, or resolve a name is both a token furnace and the root cause
of drift (wrong counts, `马克思` vs `马斯克`, corrupted YAML). Instead:

- **Never hand-write YAML frontmatter** — always go through the CLI writers.
- **Never re-scan the vault to find or count** — use `index-search`,
  `actions`, `actions-stale`, `timeline`, `due`.
- **Never guess identity** — use `identity-resolve` before creating an entity.
- **Data sources (WeChat, email, transcripts) are not core** — they are
  user-built skills that feed the CLI. See `references/extending-with-skills.md`.

## Skill workflow

When working on OpenTSC:

1. **Classify the request.** Is it soul, shell, world, event, judgment, profession, genesis, or legacy operation?
2. **Load only the needed reference module.** Keep context small and modular.
3. **Preserve laws first.** Refuse shortcuts that bypass stable IDs, append-only events, evidence ratings, feedback due dates, or user confirmation gates.
4. **Prefer a command over reading files.** If a CLI command can answer it deterministically, call it — do not re-scan the vault (CLI-first mandate above).
5. **Use v1 commands for v1 vaults.** Check `is_v1_vault(root)` and route accordingly.
6. **Make drafts explicit.** Automatic extraction → inbox/; formal entry requires user confirmation.
7. **Return auditable outputs.** Include IDs, source references, reasoning chains, confidence, and next decisions.

## Module map

- `scripts/opentsc.py` — CLI with v1.0 commands (soul-*, world-*, event-*, judgment-*, profession-*, genesis-*, schema-*) + full legacy backward compat
- `scripts/opentsc_core/` — modular Python implementation:
  - `soul.py` — genesis, codex, export/import
  - `events.py` — K3 event graph engine
  - `judgment.py` — K7 judgment engine (core innovation)
  - `world.py` — entity creation (players, NPCs, orgs, operations)
  - `identity.py` — K1 ID service, aliases, dedup
  - `professions.py` — 11 VSM profession definitions
  - `genesis_engine.py` — K8 self-creation engine
  - `schema_mgr.py` — K5 field ontology
  - `migrate.py` — v0.4 → v1.0 vault migration
  - `common.py` — shared utilities, path helpers, YAML frontmatter
  - **v2.0** `config.py` — pluggable backend selection (embedding/emotion)
  - **v2.0** `text.py` — jieba segmentation + keywords (regex fallback)
  - **v2.0** `emotion.py` — pluggable sentiment (lexicon/model/llm)
  - **v2.0** `embedding.py` — pluggable vectors (lite/local/api)
  - **v2.0** `index.py` — zvec memory index (markdown stays source of truth)
  - `vault.py`, `entities.py`, `relations.py`, `query.py`, `actions.py`, `calibration.py`, `filing.py`, `sources.py`, `contacts.py`, `conflicts.py`, `report.py`, `validate.py`, `upgrade.py`, `skills.py` — legacy modules (enhanced for v1.0 compat)
- `references/philosophy.md` — Twelve Laws
- `references/data-contract.md` — soul/shell/world layout, event graph schema, AttributeClaim
- `references/kernel.md` — K1-K8 responsibilities and API
- `references/plugins.md` — module families and contracts
- `references/extending-with-skills.md` — how data-source skills (WeChat, email, …) feed the core
- `requirements.txt` — optional dependencies per backend
- `templates/` — person_v1, event, profession, genesis_seed, judgment_codex_seed, rule_codex_seed, + legacy templates

## CLI command groups

```
soul-init, soul-export, soul-import, soul-genesis, soul-codex, soul-amend
world-new-player, world-new-npc, world-new-org, world-new-operation
event-add, event-link, event-cause, event-read, event-timeline, event-neighborhood
judgment-attribute, judgment-compare, judgment-explain, judgment-decay, judgment-clean-states
profession-list, profession-gaps, profession-assign, profession-init
genesis-detect-gaps, genesis-spawn, genesis-validate, genesis-register, genesis-sunset
schema-list, schema-register, schema-validate
migrate
index-build, index-sync, index-search, identity-resolve, index-stats   (v2.0 memory)
emotion-score, text-segment, actions-stale, config-show                (v2.0 deterministic)
+ all legacy commands (init, new-person, add-event, query, who-can, link, etc.)
```

## Default output style

For design or implementation answers:

```markdown
## Classification
<soul | shell | world | event | judgment | profession | genesis | legacy>

## Applicable laws
- ...

## Minimal design
- ...

## Extension points
- ...

## User decisions needed
- ...
```

For generated OpenTSC records, never invent missing evidence. Use `TODO(user)` for facts the user must supply.
