---
name: opentsc
description: "OpenTSC v1.0: Soul/Shell architecture for interpersonal intelligence. A local, offline-first system with event graphs, judgment engine (K7), self-creation (K8), three-layer attributes, calibrated predictions, and 11 VSM professions. Transforms implicit social judgment into explicit, queryable, auditable, evolving intelligence."
---

# OpenTSC v1.0 Skill — Soul/Shell Architecture

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

## Skill workflow

When working on OpenTSC:

1. **Classify the request.** Is it soul, shell, world, event, judgment, profession, genesis, or legacy operation?
2. **Load only the needed reference module.** Keep context small and modular.
3. **Preserve laws first.** Refuse shortcuts that bypass stable IDs, append-only events, evidence ratings, feedback due dates, or user confirmation gates.
4. **Use v1 commands for v1 vaults.** Check `is_v1_vault(root)` and route accordingly.
5. **Make drafts explicit.** Automatic extraction → inbox/; formal entry requires user confirmation.
6. **Return auditable outputs.** Include IDs, source references, reasoning chains, confidence, and next decisions.

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
  - `vault.py`, `entities.py`, `relations.py`, `query.py`, `actions.py`, `calibration.py`, `filing.py`, `sources.py`, `contacts.py`, `conflicts.py`, `report.py`, `validate.py`, `upgrade.py`, `skills.py` — legacy modules (enhanced for v1.0 compat)
- `references/philosophy.md` — Twelve Laws
- `references/data-contract.md` — soul/shell/world layout, event graph schema, AttributeClaim
- `references/kernel.md` — K1-K8 responsibilities and API
- `references/plugins.md` — module families and contracts
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
