# External Document Generation — Code Patterns

Reference for programmatically editing Word (.docx) documents with `python-docx` when generating proposals, pitch decks, or team introduction documents from OpenTSC vault data.

## Setup

```python
from docx import Document
from docx.oxml.ns import qn
from lxml import etree
from copy import deepcopy
```

## Inspect document structure

Always start by listing all paragraphs with index, style name, and text preview:

```python
doc = Document('proposal.docx')
for i, p in enumerate(doc.paragraphs):
    sname = p.style.name if p.style else 'None'
    print(f'{i:3d} | {sname:30s} | {p.text[:120]}')
```

This maps insertion points for later operations.

## Insert paragraphs at a specific position

```python
def insert_paragraph_after(doc, after_idx, text, style_name='ListParagraph', bold=False, font_size=None):
    """Insert a new paragraph after doc.paragraphs[after_idx]."""
    target_para = doc.paragraphs[after_idx]
    target_element = target_para._element
    parent = target_element.getparent()
    
    # Clone an existing paragraph to inherit document-level formatting
    new_p = deepcopy(doc.paragraphs[5]._element)  # pick any normal paragraph as template
    for r in new_p.findall(qn('w:r')):
        new_p.remove(r)
    
    # Create run with text
    new_run = etree.SubElement(new_p, qn('w:r'))
    run_props = etree.SubElement(new_run, qn('w:rPr'))
    if bold:
        etree.SubElement(run_props, qn('w:b'))
    if font_size:
        sz = etree.SubElement(run_props, qn('w:sz'))
        sz.set(qn('w:val'), str(font_size * 2))  # half-points: 12pt = '24'
        sz_cs = etree.SubElement(run_props, qn('w:szCs'))
        sz_cs.set(qn('w:val'), str(font_size * 2))
    
    new_text = etree.SubElement(new_run, qn('w:t'))
    new_text.text = text
    new_text.set(qn('xml:space'), 'preserve')
    
    # Set paragraph style
    pPr = new_p.find(qn('w:pPr'))
    if pPr is None:
        pPr = etree.SubElement(new_p, qn('w:pPr'))
        new_p.insert(0, pPr)
    style_elem = pPr.find(qn('w:pStyle'))
    if style_elem is None:
        style_elem = etree.SubElement(pPr, qn('w:pStyle'))
    style_elem.set(qn('w:val'), style_name)
    
    # Insert after target
    all_children = list(parent)
    target_pos = all_children.index(target_element)
    parent.insert(target_pos + 1, new_p)
```

### Inserting multiple paragraphs in order

When inserting N paragraphs after index `after_idx`, each subsequent insert shifts later elements. Compute position relative to the original target each time:

```python
# Insert 3 paragraphs after index 14
target_element = doc.paragraphs[14]._element
parent = target_element.getparent()
base_idx = list(parent).index(target_element)

for i, (style, text) in enumerate(entries):
    # Create paragraph element (see above)
    parent.insert(base_idx + 1 + i, new_p)
```

## Update existing paragraph text

To replace the text of an existing paragraph (e.g., updating Dave's title):

```python
for p in doc.paragraphs:
    if 'Dave Wayne' in p.text and '澳洲博士' in p.text:
        for run in p.runs:
            if 'Dave Wayne' in run.text:
                run.text = "Dave Wayne——QUT博士，AusHSI外聘咨询顾问，AI系统方向。"
                break
        break
```

## Reading tables

```python
for table in doc.tables:
    print('--- TABLE ---')
    for row in table.rows:
        print(' | '.join(cell.text for c in row.cells))
```

## Save and verify

```python
output_path = 'proposal_updated.docx'
doc.save(output_path)

# Verify by re-reading
doc2 = Document(output_path)
for i, p in enumerate(doc2.paragraphs):
    if any(kw in p.text for kw in ['Bob', '东云', 'Hanqing', 'Dave']):
        print(f'{i:3d} | {p.text[:100]}')
```

## Key pitfalls

1. **`p.style` can be None** — always guard: `p.style.name if p.style else 'None'`
2. **Style names are Word-locale-dependent** — Chinese Word may use localized style names. Inspect existing paragraphs first to see what style names the document actually uses.
3. **Never overwrite the original** — always save to a new filename with `_updated` or `_v2` suffix.
4. **Table cells** — `table.rows[i].cells` gives cells; `cell.text` is read/write but replacing complex cell content requires the same run-level manipulation as paragraphs.
5. **python-docx must be installed** — `pip install python-docx` if not already present. Wrap in try/except with auto-install.
