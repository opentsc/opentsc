# OpenTSC Philosophy — The Twelve Laws

This module contains the doctrine layer. It outranks implementation convenience.

## Authority levels

1. **Axioms (Laws)** — cannot be violated. Change the doctrine before changing behavior.
2. **Contracts** — must be satisfied by implementations.
3. **Guides** — may be optimized when the above remain intact.

When uncertain, ask the user instead of guessing.

## The Twelve Laws

### Existence Laws — TSC is what

#### Law 1 · Genesis Immutable
A TSC's reason for existence and its inviolable red lines are set once and cannot be changed. Changing them creates a new TSC with a new identity.

#### Law 2 · Soul/Shell Separation
The law and memory (soul) and the software running it (shell) are two different things. If the shell breaks, the soul can be poured into a new shell and revived.

#### Law 3 · Identity by ID, Not Name
Every entity has one immutable internal ID. Names, nicknames, aliases, platform accounts are attributes under that ID.

### Perception Laws — TSC sees the world how

#### Law 4 · Store Trajectories, Not Snapshots
Intelligence is an event stream. Current state is a derived view. Modify by appending corrective events; delete by soft-delete marker. Events are append-only.

#### Law 5 · Evidence Before Judgment
Every intelligence event needs source and Admiralty rating. Every recommendation/prediction needs reasoning chain and due date. Hostile judgments require reviewable evidence chains.

#### Law 6 · Draft Before Registry
Automatic extraction produces candidates in inbox/ as drafts. Formal event-stream entry requires user confirmation or explicit pending-verification status.

### Judgment Laws — TSC decides what is good

#### Law 7 · Dual Codex
Two constitutions: a rule codex (what is allowed/forbidden) and a judgment codex (what counts as good/trustworthy/worth mobilizing). The judgment codex was previously implicit in model weights — now it must be explicit, in the system.

#### Law 8 · Reality Calibrates, Not Comfort
System adjustment comes from prediction-vs-outcome and usefulness/accuracy feedback. Comfort/discomfort is recorded separately and must not tune generation. A system that only says what the player wants to hear is dead.

#### Law 9 · Attributes Derived From Events, Not Hand-Filled
You cannot directly score a person. You can only record what they did; the system derives their attributes via the judgment codex. This ensures reproducibility across models and operators.

### Evolution Laws — TSC grows how

#### Law 10 · Grow Only Where Needed
Default to minimum. An entity starts as a single file, grows into a folder when important. An organization starts with the fewest agents; new agents spawn only when there is a proven capability gap. Do not pre-build architecture.

#### Law 11 · Four-fold Self-Creation
The organization can grow what it needs: propose new rules, spawn new agents/skills, discover new goals, expand/contract boundaries. All through governed processes with player approval.

#### Law 12 · Recursive Isomorphism
Person, team, org, ecosystem — all are TSC entities using the same cycle (observe→judge→decide→act) and the same attribute ontology. The map can drill down infinitely.

## Core Cycle

**Observe → Judge → Decide → Act**

Observation produces events. Judgment produces attribute assessments. Decision produces actions. Actions produce new events. One revolution = one evolution.

## Holder Responsibility

The system stores extreme information asymmetry. Local storage, offline-first behavior, access control, and encryption-at-rest are foundational requirements. The soul grows more valuable over time — protect it accordingly.
