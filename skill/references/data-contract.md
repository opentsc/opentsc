# OpenTSC v1.0 Data Contract

This module defines storage shape and invariants. Implementations may choose language/tooling, but must preserve this contract.

## Canonical directory layout (v1.0 Soul/Shell/World)

```text
opentsc/
├── soul/                           # Portable, exportable (Law 2)
│   ├── _genesis.md                 # Write-once (Law 1)
│   ├── _rule_codex.md              # Three-layer rules (Law 7)
│   ├── _judgment_codex.md          # Scoring/trust/skill definitions (Law 7)
│   ├── _schema.md                  # Field ontology (K5)
│   ├── events/YYYY-MM/evt_*.md     # Event graph nodes (Law 4)
│   │   └── _index.jsonl            # Reverse index: entity→events
│   └── calibration/YYYY-MM/        # Prediction outcomes (Law 8)
├── shell/                          # Replaceable container
│   ├── kernel/                     # K1-K8 config docs
│   ├── modules/_registry.md        # Module progressive disclosure index
│   ├── professions/*.md            # Profession contract definitions
│   └── genesis_engine/templates/   # Self-creation templates
├── world/                          # Entity model (Law 3)
│   ├── players/p_*/profile.md      # Player entities
│   ├── npcs/humans/p_*/profile.md  # Human NPC entities (uncontrollable)
│   ├── npcs/agents/a_*/profile.md  # Agent NPC entities (controllable)
│   ├── orgs/o_*/profile.md         # Organization entities
│   ├── operations/op_*/profile.md  # Operation entities
│   └── roles/                      # Role assignments
├── raw/                            # Raw materials with manifest+hash
├── inbox/                          # Draft candidates (Law 6)
├── knowledge/{facts,methods,principles}/
├── actions/{proposed,active,waiting,done,dropped}/
├── relations/edges.jsonl
├── reports/YYYY-MM/
├── archive/
└── ledger/
```

**Iron rule**: `soul/` and `shell/` are physically separated. Exporting `soul/` = exporting the soul. It can be injected into any compliant new shell to revive (Law 2).

## Event contract (v1.0 — independent nodes)

Each event is a standalone file `soul/events/YYYY-MM/evt_*.md`:

```yaml
---
id: evt_0a1f
date: 2026-06-01
admiralty: B2
source: "会议逐字稿 #5"
raw: raw_2026-06-01_call5
status: active
links: [p_carol, p_eve, op_001]
caused_by: []
causes: [evt_0a23]
judgment_triggered: [p_carol.trust, p_carol.skills.client_psych]
---

Carol 在与 Eve 通话中主动提及团队成立仅3个月
```

Events link to multiple entities (not trapped in one). Causal edges connect events.

## Entity contract (v1.0 — three-layer attributes)

```yaml
---
id: p_1c2e
type: human_npc
names:
  real: Grace
  aliases: [{value: "Grace_X", platform: x, status: confirmed}]
professions: [operator]
base:
  execution_ceiling: {value: 0.7, confidence: 0.5, provenance: [evt_a1], reviewed: 2026-05, decay: 0.02}
  resilience: {value: 0.5, confidence: 0.4, provenance: [evt_b3], reviewed: 2026-05, decay: 0.02}
  reliability: {value: 0.4, confidence: 0.6, provenance: [evt_d1, evt_d2], reviewed: 2026-06, decay: 0.02}
skills:
  - {id: client_psych, level: 3, prereq_met: true, leveled_by: [evt_c1, evt_c9]}
states:
  - {tag: "已读不回·可靠性存疑", kind: debuff, expires: 2026-06-08, on_repeat: solidify, source: evt_d2}
trust: {reviewed: 2026-06-01}
source_mode: inferred
tags: []
---
```

### AttributeClaim format

Every base attribute is a probability statement with evidence:

```yaml
dimension_name:
  value: 0.72           # Current estimate (0-1)
  confidence: 0.6       # How certain this estimate is
  provenance: [evt_0a1] # Which events led to this
  reviewed: 2026-06-01  # Last update date
  decay: 0.03           # Confidence loss per month without new evidence
  source_admiralty: B2   # Average evidence quality
```

**Invariant 8**: Attributes can only be written by K7 (judgment engine) from events. No direct writes.

## Relationship edge contract

```text
[现|历] <relationship_type> →→ <target_id>: <display> · <role> · <time_range> · confidence:<level>
```

Relationships are directional, time-aware, evidence-backed. Trust, mobilizability, and cost are edge attributes, not node fields.

## Core invariants (v1.0)

1. Every entity has exactly one immutable `id`; path anchors use IDs, not names.
2. Event streams are append-only; modifications append corrections; deletions are soft.
3. Events require Admiralty rating and source.
4. Advisor outputs require due date and reasoning chain before being staged for calibration.
5. New fields must be registered in `_schema.md` before use.
6. Modules use the kernel bus and must not directly mutate identity or event internals.
7. Automatic extraction goes to `inbox/` first (Law 6).
8. **Attributes only written by K7 from events, never directly** (Law 9).
9. **Evaluation dimensions read from judgment_codex at runtime, never hardcoded** (Law 7).
10. **Genesis engine outputs require validation gate + player approval** (Law 11).
11. Operation completion/abandonment is user-declared only; closing triggers mandatory review.
12. `soul/` can be independently exported and is self-consistent: from soul/ alone, all current attributes can be re-derived (Law 2 revival precondition).
