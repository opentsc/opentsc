<div align="center">

# OpenTSC

**A private, offline memory for the people, projects, and decisions you juggle — that also keeps score of whether your judgment was right.**

🌐 **English** · [中文](README.zh-CN.md)

by **dashen** (「AI 最严厉的父亲」) · [dashen.wang](https://dashen.wang) · [@dashen_wang](https://x.com/dashen_wang)

[![License: AGPL v3](https://img.shields.io/badge/code-AGPL--3.0-blue.svg)](LICENSE) · ![version](https://img.shields.io/badge/version-v2.1.0-green.svg) · [Commercial license](LICENSING.md) · [Whitepaper (the "soul") →](https://github.com/opentsc/tsc)

[Changelog](CHANGELOG.md) · [Migrate v1→v2](MIGRATION.md) · [Usage guide](docs/usage.md)

</div>

---

## What is this, in plain words?

You deal with a lot of people and moving parts. Your notes are scattered, your memory is unreliable, and you rarely check whether your gut calls actually pan out. OpenTSC fixes that:

- 📝 **You jot down what happened** — "Carol delivered the quote on time", "Dave keeps stalling on the GPU order."
- 🗂️ **It organizes everything into a searchable memory** — every fact tagged with where it came from and how trustworthy it is.
- 💬 **You ask plain questions** — *Who reliably delivers? Have I dealt with a situation like this before? What am I still waiting on, and from whom?*
- 🎯 **You log predictions; it later tells you your hit rate** — so your judgment actually improves over time instead of quietly drifting.
- 🔒 **Everything stays on your own computer.** Offline-first, single-user, no cloud, no account.

It is **not** a CRM (it's about judgment and operations, not storing contacts) and **not** a social network. Think of it as a **second brain for your working relationships and operations** — one that holds you accountable to reality.

## What can you actually do with it?

| You want to… | Plain-language ask → it runs |
|---|---|
| Record something that happened, with evidence | "log that Carol delivered on time" → `event-add` |
| Find people or situations by **meaning**, not keywords | "who's reliable on delivery?" → `index-search` |
| Avoid creating a duplicate record of the same person | "is there already a Mike?" → `identity-resolve` |
| See what's gone stale or overdue | "what's rotting in my to-do list?" → `actions-stale` |
| Score your own predictions over time | `stage-prediction` → `calibrate` → `accuracy` |
| Spot patterns in your own notes | "who's been negative lately?" → `index-mood` |

> Examples use placeholder names (Carol, Dave…). **OpenTSC ships with zero real data.** Use it responsibly and only on information you're allowed to hold — see [SECURITY.md](SECURITY.md).

## How it works (30 seconds)

OpenTSC is a **skill for AI coding agents** (Claude Code, and others) plus a **Python command-line tool**. You talk to it in plain language through your agent; it stores everything as plain Markdown files **you own**, and builds a fast, semantic search index on top.

```bash
python skill/scripts/opentsc.py --root my-vault init
python skill/scripts/opentsc.py --root my-vault event-add B2 "Carol delivered the quote on time" "meeting note" --link p_carol
python skill/scripts/opentsc.py --root my-vault index-search "who is reliable" --kind entity
```

Optional power-ups (all opt-in — the core runs with zero extra installs): Chinese word segmentation (jieba), emotion scoring (lexicon / local model / LLM), and a vector memory index (zvec). See the [usage guide](docs/usage.md).

## Quick start

1. Drop `skill/` into your project as `.claude/skills/opentsc/`, or call `skill/scripts/opentsc.py` directly.
2. (Optional) `pip install jieba snownlp zvec` and copy `skill/templates/_config.yaml` to `<vault>/soul/_config.yaml` to turn on the memory engine.
3. Read the [usage guide](docs/usage.md). Upgrading from v1.0? See [MIGRATION.md](MIGRATION.md) — your data needs no changes.

## The bigger idea (for the curious)

OpenTSC is the **"shell"** of a concept called **TSC — the Thin-Shell Company**: how *one person* can run a large, self-evolving operation with AI agents. The one idea worth knowing:

> Keep your **judgment and memory** (the "soul") separate from whatever software, team, or AI model happens to run it (the "shell") — so it survives any tool change. Export the soul, and you've exported the whole thing.

The full doctrine lives in the [whitepaper / "soul" repo](https://github.com/opentsc/tsc). The mapping from each principle to the code that implements it is in [SKILL.md](skill/SKILL.md).

## License

- **Code**: [AGPL-3.0](LICENSE) for the community; a [commercial license](LICENSING.md) is available for closed-source use.
- **Name & brand**: OpenTSC™ / TSC™ are trademarks — see [TRADEMARK.md](TRADEMARK.md).
- Contributions: see [CONTRIBUTING.md](CONTRIBUTING.md) (includes a CLA).

---

<div align="center">
OpenTSC · created by dashen「AI 最严厉的父亲」· <a href="https://dashen.wang">dashen.wang</a> · <a href="https://x.com/dashen_wang">@dashen_wang</a>
</div>
