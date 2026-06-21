# Person Profile Enrichment Workflow

When the user provides new intel about a person (verbal description, background paragraph, meeting transcript excerpt, or any structured/unstructured text about a person in the vault), follow this workflow to produce a calibrated, comprehensive profile update.

## Step-by-step

### 1. Read existing profile
`read_file` the person's current `profile.md`. Note:
- Which base attributes are still at default (0.5)
- Which skills are still at level 1 or missing
- Which dimensions (age, education, location, contact, social) are TODO
- What the current narrative/侧写 says

### 2. Search session history
`session_search` for the person's name, aliases, and key topics. Pull recent mentions from past sessions to catch intel that was discussed but never written to the profile.

### 3. Search vault mentions
`search_files` across the vault for the person's name/ID in actions, events, raw transcripts, and references. This catches:
- Actions assigned to or mentioning them
- Raw transcripts where they spoke
- Cross-references in other people's profiles

### 4. Extract structured facts from new intel
Parse the user's input for:
- **Hard facts**: education, location, company, job title, age, phone, social accounts
- **Achievement claims**: "built 30+ websites", "10K followers in 10 days" — flag whether these are verifiable or self-reported
- **Skill indicators**: "data science background", "cross-border e-commerce", "AI content generation"
- **Strategic direction**: "currently focused on X", "committed to Y"
- **Relationship signals**: "core member of X team", "long-term based in Y"

### 5. Determine attribute recalibration
For each base attribute, decide if the new evidence warrants a change:

| Attribute | What moves it UP | What moves it DOWN |
|-----------|-----------------|-------------------|
| execution_ceiling | Verified deliverables (30+ websites, fast growth) | Missed deadlines, incomplete work |
| learning_speed | Evidence of skill breadth/depth increasing over time | No new skills learned |
| reliability | Corroborated claims, Alice explicit rating | Contradicted claims, identity fraud |
| autonomy | Independent projects, self-directed work | Only acts on explicit instruction |
| resilience | Handles pressure/adversity well | Avoids conflict, disappears under stress |

**Key rule**: Confidence should increase when multiple independent sources agree. A single user-provided paragraph is one source.

### 6. Level skills appropriately
- **Level 1**: Claimed, no evidence (default for new entries)
- **Level 2**: Some evidence, but limited or self-reported only
- **Level 3**: Multiple evidence points, or one very strong verified piece
- **Level 4**: Extensive verified track record with quantifiable results
- **Level 5**: Industry-recognized expertise

New intel often introduces NEW skills that weren't in the profile at all. Add them.

### 7. Write the updated profile
Key structural rules:
- **Education field**: Use the actual school+major, not just "TODO"
- **Location**: Use actual city/country
- **Tags**: Add new capability tags (e.g., "NUS数据科学", "跨境出海")
- **Professions**: Add new roles beyond the original narrow ones
- **人物侧写**: Rewrite or extend the narrative section. This is the most value-dense part — it synthesizes all evidence into a human-readable assessment
- **Intelligence timeline**: Add dated entries for all new facts, with proper source attribution

### 8. Report changes to user
Output a concise table showing:
- What changed (field, old value → new value)
- New skills added
- Key narrative updates
- Current completeness assessment

## Pitfalls

### Over-claiming from self-reported text
The user may paste someone's self-introduction or bio. These are **self-reported** and should be marked as such in provenance. Verify where possible:
- "NUS data science" → can be verified via LinkedIn or NUS alumni directory
- "30+ websites" → ask for URLs or check portfolio
- "10K followers in 10 days" → check the X account directly

Self-reported claims are still valid intel (Admiralty B-level), but should not alone move reliability above 0.85.

### Missing new skill dimensions
When the user gives a rich paragraph, it's easy to only update the obvious fields (education, location) and miss the implicit skills. For example, "公开透明地记录整个出海全流程" implies content creation ability and brand-building mindset — these should become skills.

### Forgetting to update the narrative
The 人物侧写 section is the most-read part of the profile. If you only update frontmatter fields but leave the old narrative, the profile feels inconsistent. Always rewrite or extend the narrative after a significant update.
