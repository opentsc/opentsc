# OpenTSC v1.0 Core Workflows

Each workflow is an end-to-end composition of kernel services (K1-K8) and modules. Workflows are acceptance tests for whether OpenTSC is alive.

## 1. Event → Judgment → Attribute Update (v1.0 核心循环)

**Trigger:** new intelligence arrives (meeting notes, observation, report).

Pipeline:

1. Create event node in `soul/events/` via K3 with Admiralty rating, source, and entity links.
2. K7 judgment engine reads `judgment_codex` and auto-derives attribute patches:
   - Base attribute adjustments (execution_ceiling, reliability, etc.)
   - Skill level upgrades (if upgrade trigger matched)
   - Buff/debuff application (if state rule pattern matched)
3. Record which attributes were triggered in event's `judgment_triggered` field.
4. Entity files updated with new AttributeClaim values (provenance traces back to event).

Constraint: attributes only written by K7, never directly (Law 9).

## 2. Task → Actor Matching (enhanced with K7)

**Trigger:** user says they need to do something.

Pipeline:

1. Decompose the task into required capability dimensions.
2. Query K7 `compare()` and `attribute()` across entities — no re-reading event history.
3. Factor in relationship edges: mobilizability, cost, trust.
4. Return ranked candidates with reasoning, confidence levels, and tradeoffs.
5. Stage prediction through K4 with due date.

Constraint: return a candidate set, not a single magic answer.

## 3. Heterogeneous Intake

**Trigger:** user supplies meeting notes, chat logs, files, or other material.

Pipeline:

1. Save raw material under `raw/` with manifest and hash.
2. Extract entities through K1, candidate events through collector modules.
3. Fan out one source into candidate events, entities, relations, knowledge, intel gaps, breakthroughs, and action drafts.
4. Place all candidates under `inbox/`.
5. User chooses accept / pending verification / discard.
6. Accepted events become nodes in `soul/events/` via K3, triggering K7 judgment.

Constraint: extraction is draft, not fact (Law 6).

## 4. Relation → Action Matrix

**Trigger:** user asks for relationship summary or action allocation.

Pipeline:

1. Derive relationships from event graph: pull entity neighborhood via K3.
2. Use K7 attributes for capability matching.
3. Preserve direction, trajectory, confidence, and evidence chain.
4. Under the user's goal, map relation types to action types.
5. Stage matrix through K4.

Constraint: adversarial labels need reviewable evidence (Law 5).

## 5. Intel → Knowledge

**Trigger:** intake or review reveals a reusable pattern.

Pipeline:

1. Split concrete facts from reusable patterns.
2. Draft a knowledge granule with trigger condition, source event IDs, sample size, and confidence.
3. User confirms before it enters `knowledge/`.
4. Calibration adjusts confidence by later outcomes.

Constraint: no overgeneralization from a single observation.

## 6. Deadline → Plan → Close → Review

**Trigger:** user states a goal with deadline.

Pipeline:

1. Draft subtask breakdown, dependencies, critical path, candidate resources (using K7 attributes for matching).
2. User approves; operation becomes active in `world/operations/`.
3. Track progress as events in `soul/events/`, linked to operation.
4. User manually marks complete/abandoned.
5. Mandatory closeout review: update participant evidence, candidate knowledge, calibration.

Constraint: plan is a draft; completion is user-declared (Invariant 11).

## 7. Startup Briefing (enhanced)

**Trigger:** agent/session start.

Pipeline:

1. Read: upcoming deadlines, due predictions, new events, conflicts.
2. Check active debuffs across entities.
3. Check stale attributes (low confidence from decay).
4. Check profession gaps (VSM coverage).
5. **Include at least one uncomfortable item** when present (Law 8).
6. Sort, limit, output only (read-only).

Constraint: trigger-based, not AI intuition. Must not suppress uncomfortable items.

## 8. Prediction → Calibration → Codex Iteration

**Trigger:** prediction reaches due date.

Pipeline:

1. K4 surfaces due predictions on session.idle.
2. User or evidence provides outcome: correct / wrong / partial.
3. K4 records outcome and updates hit rate by context/dimension.
4. If a dimension's hit rate falls below threshold, auto-propose amendment to `judgment_codex` via `codex.proposeAmendment` (Law 7 self-iteration).
5. Player reviews and approves/rejects amendment.

Constraint: only useful/accurate feedback drives codex changes, never comfort (Law 8).

## 9. Gap Detection → Self-Creation (v1.0 新增)

**Trigger:** profession gaps detected, or capability repeatedly missing.

Pipeline:

1. K8 genesis engine runs `detectGaps()` against VSM required professions.
2. Domain gaps detected from soul genesis environment (e.g., trading TSC needs risk_officer).
3. For each gap: generate Agent Skill draft (SKILL.md) using genesis templates.
4. K8 validates draft against laws (no hardcoded dimensions, no direct attribute writes, etc.).
5. Draft placed in `inbox/` for player review.
6. Player approves → K8 registers module in `shell/modules/`.

Constraint: nothing activates without player approval (Invariant 10).

## 10. Soul Export → Revival (v1.0 新增)

**Trigger:** shell needs replacement (new software, new model, migration).

Pipeline:

1. `soul-export` copies entire `soul/` directory to target location.
2. Export manifest records: genesis exists, event count, calibration count.
3. New shell initialized: `init` creates fresh `shell/` and `world/`.
4. `soul-import` loads the exported soul into the new shell.
5. K7 re-derives all attributes from event stream + judgment_codex.
6. Verify: all current attributes match pre-export values.

Constraint: soul must be self-consistent — from soul/ alone, all attributes can be re-derived (Invariant 12).

## 11. Contacts → Resolved Entities (enhanced)

**Trigger:** user imports vCard/CSV contacts.

Pipeline:

1. Create light nodes in `world/npcs/humans/` for contacts.
2. Auto-merge only strong identifier matches (phone/email).
3. Weak matches → K1 `suggest_merges()`.
4. Suspected account/person links marked `suspected` until user confirms.
5. Confirmed entities get default base attributes (0.5, low confidence) — K7 will refine as events arrive.

Constraint: weak matches never auto-merge.
