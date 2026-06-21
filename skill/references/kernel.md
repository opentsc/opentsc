# OpenTSC Kernel — K1–K8

The kernel is stable. It protects the twelve laws from plugin shortcuts.

## Kernel modules

| ID | Module | Responsibility | Guards |
|---|---|---|---|
| **K1** | Identity service | Allocate/resolve stable IDs; aliases; entity deduplication | Law 3 |
| **K2** | Data contract | Validate entity/event/relationship structure and directory shape | Laws 4, 10 |
| **K3** | Event stream | Append-only event graph: nodes + links + causal edges; reverse index; derived views | Law 4 |
| **K4** | Feedback contract | Require due date and reasoning chain for predictions; separate useful/accurate from comfortable | Law 8 |
| **K5** | Field ontology | Maintain `_schema.md`; register new fields; prevent drift | Laws 9, 10 |
| **K6** | Module bus | Register modules, inject kernel API, enforce read/write scopes and lifecycle | Laws 2, 11 |
| **K7** | **Judgment engine** ★ | On new event: read judgment_codex, auto-derive attribute patches, leave reasoning trace | **Law 9** |
| **K8** | **Self-creation registry** ★ | Accept genesis_engine drafts, validate against laws, register or reject, attach sunset | **Law 11** |

The kernel must not call module-specific behavior. Modules access data only through the kernel.

## Kernel API shape

```typescript
interface KernelAPI {
  identity: {                                              // K1
    resolve(nameOrId: string): EntityId
    create(type: EntityType, seed: unknown): EntityId
    suggestMerges(seed: unknown): MergeCandidate[]
    confirmAlias(id: EntityId, alias: AliasRef): void
  }
  events: {                                                // K3 + event graph
    append(event: IntelEvent): EventId                     // validated: must have admiralty + source
    link(eventId: EventId, targets: EntityId[]): void      // one event → many entities
    cause(from: EventId, to: EventId): void                // causal edge
    timeline(filter: GraphQuery): IntelEvent[]
    deriveView(id: EntityId): EntityView                   // current state = derived, not stored
    neighborhood(id: EntityId): EventGraph                 // all events + causal network for entity
  }
  judgment: {                                              // K7 ★
    onEvent(eventId: EventId): AttributePatch[]            // auto-derive via judgment_codex
    attribute(id: EntityId, dim: string): AttributeClaim   // {value, confidence, provenance, reviewed, decay}
    compare(idA: EntityId, idB: EntityId, dim: string): Comparison
    explain(id: EntityId, dim: string): ReasoningChain
  }
  feedback: {                                              // K4
    stage(prediction: Prediction): PredictionId            // must have due_date + reasoning_chain
    due(): Prediction[]
    fulfill(id: PredictionId, outcome: Outcome): void
    stats(filter?: FeedbackFilter): FeedbackStats
  }
  codex: {
    rule(): RuleCodex
    judgment(): JudgmentCodex
    proposeAmendment(target: "rule"|"judgment", change: Amendment): ProposalId
  }
  schema: { register(field: FieldDef): void; known(): FieldDef[] }   // K5
  genesis: {                                               // K8 ★
    detectGaps(): CapabilityGap[]
    spawn(spec: AgentSpec): DraftId                        // draft, needs player approval
    validate(draftId: DraftId): ValidationResult
    register(draftId: DraftId): ModuleRef                  // after approval
    sunset(ref: ModuleRef): void
  }
  bus: { register(module: ModuleManifest): void; invoke(ref: ModuleRef, ctx: Ctx): Promise<Result> }
}
```

## Kernel invariants (violation = error implementation)

1. Every entity has one immutable `id`; paths use IDs, not names.
2. Event stream append-only; corrections append, deletions soft-delete.
3. Events must have Admiralty rating and source.
4. Predictions must have due date and reasoning chain.
5. New fields registered in `_schema.md` before use.
6. Modules use bus; no direct entity/event mutation.
7. Auto-extraction → inbox/; formal entry needs confirmation.
8. **Attributes only written by K7 from events** (Law 9).
9. **Evaluation dimensions from judgment_codex, never hardcoded** (Law 7).
10. **Genesis outputs need validation gate + player approval** (Law 11).
11. Operation completion/abandonment = player-declared only; triggers mandatory review.
12. `soul/` is independently exportable and self-consistent.

## Kernel design rules

- Make validation reusable; every write path calls the same contract checks.
- Keep file IO behind kernel services so modules cannot bypass invariants.
- Store enough metadata for reversibility: merge source, dates, old paths, reasons.
- Treat all derived scores/views as cacheable outputs, not authoritative replacements for the event stream.
