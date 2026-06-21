# OpenTSC Filing Contract

This file defines where generated and user-supplied files belong. Agents must follow this before creating files.

## Time fields

Never conflate these:

- `created_at`: object/file creation time in OpenTSC.
- `updated_at`: last system write time.
- `ingested_at`: when source material entered OpenTSC.
- `source_date`: when the source claims the material happened/was published.
- `event_date`: when the intelligence event happened.
- `reviewed_at`: when the user reviewed a candidate.
- `archived_at`: when something left the active workspace.
- `calibrated_at`: when a prediction outcome was filled.

Use ISO 8601 with timezone for `*_at` fields.

## Placement rules

| Type | Entry | Active/formal location | Archive |
|---|---|---|---|
| User battle report / collected material | `intake/dropbox/` | `raw/YYYY/MM/` | `archive/raw/YYYY/MM/` |
| Candidate event | `inbox/events/` | entity timeline | `archive/inbox/YYYY/MM/` |
| Candidate entity | `inbox/entities/` | `people/`, `orgs/`, `operations/` | `archive/inbox/YYYY/MM/` |
| Candidate relation | `inbox/relations/` | `relations/edges.jsonl` + entity views | `archive/inbox/YYYY/MM/` |
| Candidate knowledge | `inbox/knowledge/` | `knowledge/facts|methods|principles/` | `archive/inbox/YYYY/MM/` |
| Conflict report | `inbox/conflicts/` | resolved by user action | `archive/inbox/YYYY/MM/` |
| Monthly/report artifact | generated | `reports/YYYY-MM/` | `archive/reports/` |
| Prediction/calibration | generated | `feedback/YYYY-MM/` | keep in place, status closed/fulfilled |
| File move / processing run | generated | `ledger/*.jsonl` | never archive |

## User dropbox workflow

1. User places files in `intake/dropbox/`.
2. `opentsc ingest` moves/copies material into `raw/YYYY/MM/` with a raw ID and timestamps.
3. Ingest creates typed candidates under `inbox/events`, `inbox/entities`, `inbox/relations`, and `inbox/knowledge`.
4. User/agent accepts or rejects candidates.
5. Accepted candidates become formal events/entities/relations/knowledge.
6. Rejected or consumed candidates move to `archive/inbox/YYYY/MM/`.
7. Every move is logged to `ledger/file-moves.jsonl`; every ingest run to `ledger/processing-runs.jsonl`.

## Knowledge source rules

PDF/long markdown/webclips are sources, not automatically actionable knowledge.

- Source files: `knowledge/sources/pdf|md|webclips/`
- Actionable granules: `knowledge/facts|methods|principles/`

A knowledge granule must cite source raw/material IDs and sample size.
