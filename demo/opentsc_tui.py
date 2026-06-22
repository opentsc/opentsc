#!/usr/bin/env python3
"""OpenTSC — Intelligence Cockpit (TUI demo).

A keyboard-driven terminal cockpit over an OpenTSC vault, in the spirit of
opencode / oh-my-openagent: a left rail of entities, a detail pane with
event-derived attribute bars, states, and the evidence timeline, plus a
semantic-ish search box.

This is a DEMO. It reads the seeded demo/demo-vault (run `python demo/seed.py`
first). It talks to the real opentsc_core — the attribute bars are what the K7
judgment engine actually derived from events, not mock data.

Run:  python demo/opentsc_tui.py
Keys: ↑/↓ pick · / search · r reload · q quit
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "skill" / "scripts"))

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    DataTable, Footer, Header, Input, Label, ListItem, ListView, Static,
)

from opentsc_core.common import scan_entities, parse_frontmatter, read_text
from opentsc_core import events as events_mod

VAULT = HERE / "demo-vault"
BASE_DIMS = ["execution_ceiling", "learning_speed", "resilience", "reliability", "autonomy"]


def _claim_value(claim) -> float:
    if isinstance(claim, dict):
        try:
            return float(claim.get("value", 0.5))
        except (TypeError, ValueError):
            return 0.5
    return 0.5


def _bar(value: float, width: int = 14) -> str:
    fill = max(0, min(width, round(value * width)))
    return "█" * fill + "░" * (width - fill)


def _mood_glyph(avg: float) -> str:
    # attributes start at 0.5; small deviations are already meaningful signal.
    if avg >= 0.51:
        return "▲"   # rising
    if avg <= 0.49:
        return "▼"   # falling
    return "■"       # steady


class Vault:
    """Thin read layer over an OpenTSC vault via opentsc_core."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def entities(self) -> list[dict]:
        out = []
        if not self.root.exists():
            return out
        for eid, ref in scan_entities(self.root).items():
            if eid.startswith("evt_") or "events" in ref.path.parts:
                continue
            if "world" not in ref.path.parts:
                continue
            fm = parse_frontmatter(read_text(ref.path))
            names = fm.get("names")
            name = names.get("real") if isinstance(names, dict) else fm.get("name", eid)
            base = fm.get("base", {}) if isinstance(fm.get("base"), dict) else {}
            vals = [_claim_value(base.get(d)) for d in BASE_DIMS if d in base] or [0.5]
            tags = fm.get("tags", [])
            out.append({
                "id": eid, "name": str(name or eid), "base": base,
                "tags": tags if isinstance(tags, list) else [],
                "states": fm.get("states", []) if isinstance(fm.get("states"), list) else [],
                "avg": sum(vals) / len(vals),
            })
        return sorted(out, key=lambda e: e["avg"], reverse=True)

    def timeline(self, eid: str) -> list[dict]:
        try:
            return events_mod.timeline(self.root, entity=eid, limit=50)
        except Exception:
            return []


class OpenTSCCockpit(App):
    CSS = """
    Screen { background: $surface; }
    #search { dock: top; border: round $accent; margin: 0 1; }
    #body { height: 1fr; }
    #rail { width: 34; border: round $primary 40%; margin: 0 0 0 1; padding: 0 1; }
    #rail-title { color: $accent; text-style: bold; padding: 0 0 1 0; }
    #detail { border: round $primary 40%; margin: 0 1 0 1; padding: 0 1; }
    #ehead { color: $accent; text-style: bold; }
    #etags { color: $text-muted; padding: 0 0 1 0; }
    DataTable { height: auto; margin: 1 0; }
    #tl-title, #attr-title { color: $accent; text-style: bold; }
    #timeline { height: 1fr; }
    ListView { background: transparent; }
    ListItem { padding: 0 1; }
    """
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("/", "search", "Search"),
        ("r", "reload", "Reload"),
        ("escape", "unfocus", "Back"),
    ]
    TITLE = "OpenTSC"
    SUB_TITLE = "Intelligence Cockpit · demo"

    def __init__(self) -> None:
        super().__init__()
        self.vault = Vault(VAULT)
        self.all_entities: list[dict] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Input(placeholder="search people / events…  (press /)", id="search")
        with Horizontal(id="body"):
            with Vertical(id="rail"):
                yield Label("◤ ENTITIES ▸ by strength", id="rail-title")
                yield ListView(id="entities")
            with Vertical(id="detail"):
                yield Static("Select an entity", id="ehead")
                yield Static("", id="etags")
                yield Label("ATTRIBUTES — derived by K7 from events", id="attr-title")
                yield DataTable(id="attrs", cursor_type="none", zebra_stripes=True)
                yield Label("TIMELINE — evidence stream", id="tl-title")
                yield DataTable(id="timeline", cursor_type="row", zebra_stripes=True)
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#attrs", DataTable).add_columns("dimension", "level", "value", "conf")
        self.query_one("#timeline", DataTable).add_columns("date", "adm", "event")
        self.load()

    def load(self) -> None:
        self.all_entities = self.vault.entities()
        self._populate(self.all_entities)

    def _populate(self, entities: list[dict]) -> None:
        lv = self.query_one("#entities", ListView)
        lv.clear()
        if not entities:
            lv.append(ListItem(Label("(empty — run `python demo/seed.py`)")))
            return
        for e in entities:
            glyph = _mood_glyph(e["avg"])
            lv.append(ListItem(Label(f"{glyph} {e['name']:<10} {_bar(e['avg'], 10)}"), name=e["id"]))
        lv.index = 0

    def _entity_by_id(self, eid: str) -> dict | None:
        return next((e for e in self.all_entities if e["id"] == eid), None)

    def on_list_view_highlighted(self, msg: ListView.Highlighted) -> None:
        if msg.item is None or msg.item.name is None:
            return
        self._show(msg.item.name)

    def _show(self, eid: str) -> None:
        e = self._entity_by_id(eid)
        if not e:
            return
        self.query_one("#ehead", Static).update(f"{_mood_glyph(e['avg'])} {e['name']}  ·  {eid}")
        tags = "  ".join(f"#{t}" for t in e["tags"]) or "—"
        states = e.get("states") or []
        st = "   ⚑ " + ", ".join(str(s) for s in states[:3]) if states else ""
        self.query_one("#etags", Static).update(f"{tags}{st}")

        attrs = self.query_one("#attrs", DataTable)
        attrs.clear()
        for dim in BASE_DIMS:
            claim = e["base"].get(dim)
            if not isinstance(claim, dict):
                continue
            v = _claim_value(claim)
            conf = claim.get("confidence", "—")
            attrs.add_row(dim, _bar(v), f"{v:.2f}", str(conf))

        tl = self.query_one("#timeline", DataTable)
        tl.clear()
        for evt in reversed(self.vault.timeline(eid)):
            content = (evt.get("content", "") or "").replace("\n", " ")
            tl.add_row(evt.get("date", ""), evt.get("admiralty", ""), content[:80])

    # --- actions ---
    def action_search(self) -> None:
        self.query_one("#search", Input).focus()

    def action_unfocus(self) -> None:
        self.query_one("#entities", ListView).focus()

    def action_reload(self) -> None:
        self.query_one("#search", Input).value = ""
        self.load()

    def on_input_changed(self, msg: Input.Changed) -> None:
        q = msg.value.strip().lower()
        if not q:
            self._populate(self.all_entities)
            return
        # match name/tags, or any event content of the entity
        filtered = []
        for e in self.all_entities:
            hay = e["name"].lower() + " " + " ".join(e["tags"]).lower()
            if q in hay or any(q in (ev.get("content", "") or "").lower() for ev in self.vault.timeline(e["id"])):
                filtered.append(e)
        self._populate(filtered)


if __name__ == "__main__":
    OpenTSCCockpit().run()
