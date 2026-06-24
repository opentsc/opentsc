# Installing OpenTSC

> **Requirements: Python 3.10–3.14.** The optional `zvec` index ships no wheels
> for Python 3.9 or earlier — and macOS's system Python is 3.9. If you're on
> macOS (or hit `externally-managed-environment` / PEP 668), use **uv** below.

## Quick install (uv — recommended, cross-platform)

[uv](https://docs.astral.sh/uv/) downloads a suitable Python, sidesteps PEP 668,
and manages the virtualenv for you — one path that works on macOS/Linux/Windows:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh        # install uv
uv venv ~/.venvs/opentsc --python 3.11                 # get a 3.11 interpreter
source ~/.venvs/opentsc/bin/activate                   # (Windows: .venv\Scripts\activate)
uv pip install jieba snownlp zvec                       # Tier 1 backends
```

Then run:

```bash
python skill/scripts/opentsc.py --root my-vault init
python skill/scripts/opentsc.py --root my-vault index-stats   # backend=lite, available=true
```

## Plain venv (if you already have Python 3.10+)

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r skill/requirements.txt
```

## Backends by tier — install only what you turn on

The **core runs with zero extra installs** (`lite` embedding + built-in
`lexicon` emotion + regex segmenter). Heavier backends are opt-in; pick a tier,
then set it in `<vault>/soul/_config.yaml` (template: `skill/templates/_config.yaml`).

| Tier | Install | Unlocks |
|---|---|---|
| **0 — core** | *(nothing)* | `lite` vectors, built-in emotion lexicon, regex segmentation. Everything works. |
| **1 — recommended** | `pip install jieba snownlp zvec` | jieba segmentation, snownlp lexicon, the **zvec semantic memory index** (`index-build/search`, `identity-resolve`). |
| **2 — local embeddings** | `+ pip install sentence-transformers` | `embedding_backend: local` (e.g. BAAI/bge-small-zh) — higher-quality semantic search, fully offline. |
| **3 — model emotion / LLM** | `+ pip install transformers` | `emotion_backend: model`; or `emotion_backend: hybrid/llm` with a command (see `scripts/emotion_llm_example.py`). |

## Installing as a Claude Code / Hermes skill

This repo's **`skill/`** subdirectory is the skill — not the repo root. After
cloning, copy that subdirectory into your skills folder:

```bash
git clone https://github.com/opentsc/opentsc
cp -r opentsc/skill ~/.hermes/skills/opentsc        # or ~/.claude/skills/opentsc
```

(`README.md`, `docs/`, `demo/`, `CHANGELOG.md` etc. stay in the repo; they are
not part of the installed skill.)

## Common errors

| Symptom | Cause → fix |
|---|---|
| `No matching distribution found for zvec` | Python ≤ 3.9 → use uv / a 3.10+ venv (above). |
| `error: externally-managed-environment` | PEP 668 (system Python) → use a venv or uv; don't `pip install` into system Python. |
| `unrecognized arguments: --root .` | (fixed in v2.1) `--root` now works before *or* after the subcommand. Update the skill. |
| `index-*` says "zvec is not installed" | You're on Tier 0 → `pip install zvec` (Tier 1), or just use the non-index commands. |
