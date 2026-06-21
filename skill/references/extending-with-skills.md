# Extending OpenTSC — data-source skills live outside the core

OpenTSC core is deliberately **data-source-agnostic**. It knows about soul,
shell, world, events, judgment, the memory index, and the CLI — and nothing
about where intelligence comes from. WeChat, email, meeting transcripts,
X/Twitter, CRM exports: **none of these belong in the core.** They are
*user-built extension skills* that feed the core through a narrow, audited
intake contract.

This keeps the portable core small and law-abiding, and keeps the
privacy-sensitive collectors (which vary per person and per jurisdiction)
where they belong — with the user, opt-in, replaceable.

## The intake contract

A data-source skill MUST feed the core only through the CLI, never by writing
vault files itself:

| Step | Command | Rule |
|---|---|---|
| 1. Land raw material | `opentsc store-raw <file>` / `opentsc ingest <path>` | Keep the original; every claim traces back to it (Law 5). |
| 2. Propose, don't assert | `opentsc draft-inbox-event …` | Auto-extraction lands in inbox/ as a draft (Law 6). |
| 3. Formalize on confirmation | `opentsc event-add <admiralty> <content> <source> --link <id>` | Needs an Admiralty rating + source on every event (Law 5). |
| 4. Resolve identity, don't guess | `opentsc identity-resolve "<name>"` | Ask the index for the nearest existing entity before creating a new one — this is what prevents hash-id sprawl and "马克思 vs 马斯克" drift (Law 3). |
| 5. Refresh memory | `opentsc index-sync` | The index is derived; sync after a batch. |

A data-source skill therefore **never** parses or writes YAML frontmatter,
never invents IDs, and never bypasses the draft→confirm gate. If it goes
through the CLI, the twelve laws hold automatically.

## Sketch: a `wechat-source` user skill

```
your-vault/.claude/skills/wechat-source/
  SKILL.md          # "when the user drops a WeChat export, do the following"
  pull.py           # read your own chat export → text records (your format)
```

Its SKILL.md, in spirit:

> 1. For each new message batch, write the raw file with `store-raw`.
> 2. For each candidate signal, `emotion-score` the text and `text-segment`
>    it for keywords (deterministic — no LLM needed for this).
> 3. Resolve the speaker with `identity-resolve`; create the entity only if no
>    close match exists.
> 4. Land an inbox draft; let the user confirm before `event-add`.
> 5. `index-sync` at the end.

The core never learns it was WeChat. Swap in `email-source`,
`transcript-source`, or `x-source` against the same contract.

## Privacy & consent (non-negotiable)

Collectors operate on real people. Before building one:

- Only ingest data you are authorized to hold.
- Do not profile or surveil people without consent.
- Comply with local law (PIPL / GDPR / …). See [SECURITY.md](../SECURITY.md).

The core ships **no** collectors precisely so these decisions stay explicit and
local to you — never bundled, never on by default.
