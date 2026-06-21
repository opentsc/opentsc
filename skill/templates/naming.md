# OpenTSC Naming Contract

Strict names prevent vault drift. Agents must follow these rules.

## Entity IDs

| Entity | Prefix | Example | Active path |
|---|---|---|---|
| person | `p_` | `p_0f3a9b` | `people/p_0f3a9b.md` or `people/p_0f3a9b/profile.md` |
| organization | `o_` | `o_tl001` | `orgs/o_tl001/profile.md` |
| operation | `op_` | `op_tl001` | `operations/op_tl001/profile.md` |
| action | `act_YYYYMMDD_` | `act_20260531_ab12cd` | `actions/<status>/act_YYYYMMDD_ab12cd-title.md` |
| raw material | `raw_YYYYMMDD_` | `raw_20260531_ab12cd` | `raw/YYYY/MM/raw_YYYYMMDD_ab12cd-title.ext` |
| draft | `draft_<type>_YYYYMMDD_` | `draft_events_20260531_ab12cd` | `inbox/<type>/draft_<type>_YYYYMMDD_ab12cd.md` |
| prediction | `pred_` | `pred_ab12cd34` | `feedback/YYYY-MM/pred_ab12cd34.md` |
| knowledge | `kg_YYYYMMDD_` | `kg_20260531_ab12cd` | `knowledge/<layer>/kg_YYYYMMDD_ab12cd-title.md` |

## File-name rules

- Paths anchor on IDs, not names.
- Human titles may appear after the ID as a slug: `<id>-<slug>.md`.
- Slugs are optional and disposable; IDs are authoritative.
- Use lowercase ASCII for generated slugs where possible; preserve Chinese titles only after the ID when useful.
- Never rename an entity ID to match a person/org name.

## Required root files

```text
_doctrine.md
_schema.md
_filing.md
_naming.md
```

## Required root directories

```text
people/
orgs/
operations/
roles/
actions/proposed/
actions/active/
actions/waiting/
actions/done/
actions/dropped/
intake/dropbox/
intake/processing/
intake/rejected/
raw/
inbox/events/
inbox/entities/
inbox/relations/
inbox/knowledge/
inbox/actions/
inbox/conflicts/
relations/
knowledge/facts/
knowledge/methods/
knowledge/principles/
knowledge/sources/pdf/
knowledge/sources/md/
knowledge/sources/webclips/
reports/
feedback/
contacts/
archive/entities/
archive/raw/
archive/inbox/
archive/reports/
ledger/
```

## Upgrade rule

After installing or updating the skill, run:

```bash
opentsc upgrade
```

This creates missing directories, root contract files, ledgers, indexes, and checks naming drift without deleting user data.
