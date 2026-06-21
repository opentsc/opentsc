# OpenTSC Schema Template

Use this as `opentsc/_schema.md`. Register fields before writing them.

| Field | Applies to | Type | Meaning | First used | Notes |
|---|---|---|---|---|---|
| `id` | all entities | string | Immutable internal ID | genesis | Required |
| `type` | all entities | enum | person/org/operation/role | genesis | Required |
| `names.real` | person | string | Real name if known | genesis | Not ID |
| `names.aliases[]` | person/org | list | Alias/account references | genesis | Each item has status |
| `trust.*` | person/org | object | User-defined trust dimensions | doctrine | Must include reviewed date |
| `tags` | all entities | list | Lightweight retrieval tags | genesis | Avoid using as relationship truth |
| `*_est` | any | varies | Estimated, not confirmed | genesis | Keep suffix for uncertainty |

## Registration rule

Before a plugin writes a new field, add:

```markdown
| `<field>` | <entity/type> | <type> | <meaning> | YYYY-MM-DD | <constraints> |
```
