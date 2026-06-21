# OpenTSC v0.4 → v1.0 Migration Notes

## Migration command

```bash
python scripts/opentsc.py --root <vault_path> migrate
```

Always backup first: `cp -r <vault> <vault>_backup_v04`

## Post-migration validation (recommended three-step)

```bash
python scripts/opentsc.py --root <vault> upgrade
python scripts/opentsc.py --root <vault> naming-audit
python scripts/opentsc.py --root <vault> validate --check-conflicts
```

## Known migration artifacts

### 1. Action status mismatch
Files in `actions/done/` may have `status: active` in frontmatter instead of `status: done`. Same for `dropped/` having `status: cancelled`. Fix with sed:
```bash
cd actions/done && sed -i 's/^status: active$/status: done/' *.md
cd actions/dropped && sed -i 's/^status: cancelled$/status: dropped/' *.md
```

### 2. Alias conflict false positives (FIXED in conflicts.py)
Original `_alias_conflicts()` used `re.findall(r"value:\s*(.+?)\s*$", text, re.MULTILINE)` which matched ALL `value:` fields including base attributes (reliability: 0.5, confidence: medium, etc.), not just alias values. Fixed to parse only the `names.aliases` block in frontmatter. Fix is in `scripts/opentsc_core/conflicts.py`.

### 3. Operations with wrong ID prefixes
Some files created by actions or knowledge entries may end up in `world/operations/` with non-op_ prefixes (act_, k_, demo-). The `upgrade` command typically handles this automatically.

## What migrate does

- Creates `soul/`, `shell/`, `world/` directory skeleton
- Moves `people/` → `world/npcs/humans/` with upgraded person format (three-layer attributes: base/skills/states)
- Moves `orgs/` → `world/orgs/`
- Moves `operations/` → `world/operations/`
- Extracts inline timeline events → `soul/events/` as independent nodes
- From `_doctrine.md` generates `_genesis.md` + `_rule_codex.md` + `_judgment_codex.md` seeds
- Moves `feedback/` → `soul/calibration/`
- Initializes 11 VSM professions
- Writes migration manifest to `ledger/migration_v04_v10.json`
- All original data preserved (old directories kept)
