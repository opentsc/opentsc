from __future__ import annotations

import datetime as dt
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

SKILL_ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = SKILL_ROOT / "templates"

ENTITY_ID_RE = re.compile(r"^[a-z]+_[A-Za-z0-9][A-Za-z0-9_-]*$")
ADMIRALTY_RE = re.compile(r"^[A-F][1-6]$")
ID_RE = re.compile(r"^id:\s*([a-z]+_[A-Za-z0-9][A-Za-z0-9_-]*)\s*$", re.MULTILINE)
TYPE_RE = re.compile(r"^type:\s*(\w+)\s*$", re.MULTILINE)
STATUS_RE = re.compile(r"^status:\s*([\w-]+)\s*$", re.MULTILINE)
DUE_RE = re.compile(r"^due:\s*(\d{4}-\d{2}-\d{2})\s*$", re.MULTILINE)
REASONING_RE = re.compile(r"^## Reasoning chain\s*$", re.MULTILINE)
EVENT_RE = re.compile(r"^-\s*\d{4}-\d{2}-\d{2}\s*·\s*[A-F][1-6]\s*·\s*.+?·〔来源:\s*.+?〕")
EVENT_MISSING_RATING_RE = re.compile(r"^-\s*\d{4}-\d{2}-\d{2}\s*·(?!\s*[A-F][1-6]\s*·).+")

VAULT_DIRS_LEGACY = [
    "people",
    "orgs",
    "operations",
    "roles",
    "intake/dropbox",
    "intake/processing",
    "intake/rejected",
    "raw",
    "inbox/events",
    "inbox/entities",
    "inbox/relations",
    "inbox/knowledge",
    "inbox/actions",
    "inbox/intel_gaps",
    "inbox/breakthroughs",
    "inbox/conflicts",
    "knowledge/facts",
    "knowledge/methods",
    "knowledge/principles",
    "knowledge/sources/pdf",
    "knowledge/sources/md",
    "knowledge/sources/webclips",
    "knowledge/sources/books",
    "knowledge/sources/reports",
    "skills/registry",
    "reports",
    "feedback",
    "contacts",
    "relations",
    "actions/proposed",
    "actions/active",
    "actions/waiting",
    "actions/done",
    "actions/dropped",
    "archive/entities",
    "archive/raw",
    "archive/inbox",
    "archive/reports",
    "ledger",
]

VAULT_DIRS_V1 = [
    # Soul — portable, exportable
    "soul",
    "soul/events",
    "soul/calibration",
    # Shell — replaceable container
    "shell",
    "shell/kernel",
    "shell/modules",
    "shell/professions",
    "shell/genesis_engine",
    "shell/genesis_engine/templates",
    # World — entity model
    "world",
    "world/players",
    "world/npcs",
    "world/npcs/humans",
    "world/npcs/agents",
    "world/orgs",
    "world/operations",
    "world/roles",
    # Operational
    "raw",
    "inbox/events",
    "inbox/entities",
    "inbox/relations",
    "inbox/knowledge",
    "inbox/actions",
    "inbox/intel_gaps",
    "inbox/breakthroughs",
    "inbox/conflicts",
    "intake/dropbox",
    "intake/processing",
    "intake/rejected",
    "knowledge/facts",
    "knowledge/methods",
    "knowledge/principles",
    "knowledge/sources/pdf",
    "knowledge/sources/md",
    "knowledge/sources/webclips",
    "knowledge/sources/books",
    "knowledge/sources/reports",
    "skills/registry",
    "reports",
    "contacts",
    "relations",
    "actions/proposed",
    "actions/active",
    "actions/waiting",
    "actions/done",
    "actions/dropped",
    "archive/entities",
    "archive/raw",
    "archive/inbox",
    "archive/reports",
    "ledger",
]

VAULT_DIRS = VAULT_DIRS_V1


def today() -> str:
    return dt.date.today().isoformat()


def now_iso() -> str:
    return dt.datetime.now().astimezone().replace(microsecond=0).isoformat()


def year_month_parts(date_text: str | None = None) -> tuple[str, str]:
    date_text = date_text or today()
    return date_text[:4], date_text[5:7]


def month() -> str:
    return dt.date.today().strftime("%Y-%m")


def stable_suffix(seed: str, length: int = 6) -> str:
    return hashlib.sha1(seed.encode("utf-8")).hexdigest()[:length]


def ensure_vault(root: Path) -> None:
    for rel in VAULT_DIRS:
        (root / rel).mkdir(parents=True, exist_ok=True)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def append_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(content)


def template(name: str) -> str:
    path = TEMPLATES / name
    if not path.exists():
        raise FileNotFoundError(f"missing template: {path}")
    return read_text(path)


def copy_template(name: str, target: Path) -> bool:
    if target.exists():
        return False
    write_text(target, template(name))
    return True


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem, suffix = path.stem, path.suffix
    for i in range(2, 10000):
        candidate = path.with_name(f"{stem}-{i}{suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"cannot find unique path for {path}")


def frontmatter(text: str) -> str:
    if not text.startswith("---\n"):
        return ""
    end = text.find("\n---", 4)
    return text[:end] if end != -1 else ""


def iter_markdown(root: Path, include_skill: bool = False) -> Iterable[Path]:
    skip = {".git"}
    if not include_skill:
        skip.add(".claude")
    for path in root.rglob("*.md"):
        if any(part in skip for part in path.parts):
            continue
        yield path


@dataclass(frozen=True)
class EntityRef:
    entity_id: str
    entity_type: str | None
    path: Path


def scan_entities(root: Path) -> dict[str, EntityRef]:
    entities: dict[str, EntityRef] = {}
    for path in iter_markdown(root):
        text = read_text(path)
        fm = frontmatter(text)
        if not fm:
            continue
        id_match = ID_RE.search(fm)
        if not id_match:
            continue
        type_match = TYPE_RE.search(fm)
        entity_id = id_match.group(1)
        entities[entity_id] = EntityRef(entity_id, type_match.group(1) if type_match else None, path)
    return entities


def resolve_entity_file(root: Path, entity: str) -> Path:
    candidates = [
        root / "people" / f"{entity}.md",
        root / "people" / entity / "profile.md",
        root / "operations" / entity / "profile.md",
        root / "operations" / f"{entity}.md",
        root / "orgs" / entity / "profile.md",
        root / "orgs" / f"{entity}.md",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    entities = scan_entities(root)
    if entity in entities:
        return entities[entity].path
    matches = list(root.glob(f"**/{entity}.md")) + list(root.glob(f"**/{entity}/profile.md"))
    if matches:
        return matches[0]
    raise FileNotFoundError(f"entity not found: {entity}")


def validate_entity_id(entity_id: str, prefix: str | None = None) -> None:
    if not ENTITY_ID_RE.match(entity_id):
        raise ValueError(f"invalid entity id: {entity_id}")
    if prefix and not entity_id.startswith(prefix):
        raise ValueError(f"entity id must start with {prefix}: {entity_id}")


def require_admiralty(value: str) -> None:
    if not ADMIRALTY_RE.match(value):
        raise ValueError("admiralty must match A1..F6")


def append_under_heading(path: Path, heading: str, line: str, fallback_heading: str | None = None) -> None:
    text = read_text(path)
    if heading in text:
        text = text.replace(heading, heading + "\n\n" + line, 1)
    elif fallback_heading and fallback_heading in text:
        text = text.replace(fallback_heading, fallback_heading + "\n\n" + line, 1)
    else:
        text = text.rstrip() + f"\n\n{heading}\n\n" + line
    write_text(path, text)


def sanitize_filename(value: str, max_len: int = 60) -> str:
    value = re.sub(r"[\\/:*?\"<>|\s]+", "-", value.strip())
    value = re.sub(r"-+", "-", value).strip("-")
    return (value or "untitled")[:max_len]


# --- v1.0 Soul/Shell/World path helpers ---

def soul_path(root: Path) -> Path:
    return root / "soul"


def shell_path(root: Path) -> Path:
    return root / "shell"


def world_path(root: Path) -> Path:
    return root / "world"


def is_v1_vault(root: Path) -> bool:
    return (root / "soul").is_dir() and (root / "shell").is_dir() and (root / "world").is_dir()


def is_legacy_vault(root: Path) -> bool:
    return (root / "people").is_dir() and not is_v1_vault(root)


def parse_frontmatter(text: str) -> dict:
    """Parse YAML-like frontmatter into a dict. Handles nested dicts and lists."""
    fm = frontmatter(text)
    if not fm:
        return {}
    lines = fm.split("\n")[1:]  # skip opening ---
    return _parse_yaml_lines(lines)


def _parse_yaml_lines(lines: list[str]) -> dict:
    result: dict = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.strip().startswith("#"):
            i += 1
            continue
        match = re.match(r"^(\s*)(\w[\w.-]*):\s*(.*)", line)
        if not match:
            i += 1
            continue
        indent = len(match.group(1))
        key = match.group(2)
        value_str = match.group(3).strip()
        if value_str.startswith("{") and value_str.endswith("}"):
            result[key] = _parse_inline_dict(value_str)
        elif value_str.startswith("[") and value_str.endswith("]"):
            result[key] = _parse_inline_list(value_str)
        elif value_str == "" or value_str == "|":
            child_lines = []
            j = i + 1
            while j < len(lines):
                if not lines[j].strip():
                    child_lines.append(lines[j])
                    j += 1
                    continue
                child_indent = len(lines[j]) - len(lines[j].lstrip())
                if child_indent <= indent:
                    break
                child_lines.append(lines[j])
                j += 1
            if child_lines and child_lines[0].strip().startswith("- "):
                result[key] = _parse_yaml_list_items(child_lines, indent)
            else:
                result[key] = _parse_yaml_lines(child_lines)
            i = j
            continue
        elif value_str == "null" or value_str == "~":
            result[key] = None
        elif value_str == "true":
            result[key] = True
        elif value_str == "false":
            result[key] = False
        elif re.match(r"^-?\d+$", value_str):
            result[key] = int(value_str)
        elif re.match(r"^-?\d+\.\d+$", value_str):
            result[key] = float(value_str)
        else:
            result[key] = value_str
        i += 1
    return result


def _parse_inline_dict(s: str) -> dict:
    s = s.strip()[1:-1].strip()
    if not s:
        return {}
    result = {}
    for part in re.split(r",\s*", s):
        if ":" in part:
            k, v = part.split(":", 1)
            k = k.strip()
            v = v.strip()
            if v == "null" or v == "~":
                result[k] = None
            elif v == "true":
                result[k] = True
            elif v == "false":
                result[k] = False
            elif re.match(r"^-?\d+$", v):
                result[k] = int(v)
            elif re.match(r"^-?\d+\.\d+$", v):
                result[k] = float(v)
            elif v.startswith("[") and v.endswith("]"):
                result[k] = _parse_inline_list(v)
            else:
                result[k] = v
    return result


def _parse_inline_list(s: str) -> list:
    s = s.strip()[1:-1].strip()
    if not s:
        return []
    items = []
    for item in re.split(r",\s*", s):
        item = item.strip()
        if not item:
            continue
        if re.match(r"^-?\d+$", item):
            items.append(int(item))
        elif re.match(r"^-?\d+\.\d+$", item):
            items.append(float(item))
        else:
            items.append(item)
    return items


def _parse_yaml_list_items(lines: list[str], parent_indent: int) -> list:
    items = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- "):
            val = stripped[2:].strip()
            if val.startswith("{") and val.endswith("}"):
                items.append(_parse_inline_dict(val))
            elif re.match(r"^-?\d+$", val):
                items.append(int(val))
            elif re.match(r"^-?\d+\.\d+$", val):
                items.append(float(val))
            else:
                items.append(val)
    return items


def write_frontmatter(data: dict, body: str = "") -> str:
    """Serialize a dict into YAML-like frontmatter + body."""
    lines = ["---"]
    _serialize_yaml(data, lines, indent=0)
    lines.append("---")
    if body:
        lines.append("")
        lines.append(body.rstrip())
    return "\n".join(lines) + "\n"


def _serialize_yaml(data: dict, lines: list[str], indent: int) -> None:
    prefix = "  " * indent
    for key, value in data.items():
        if value is None:
            lines.append(f"{prefix}{key}: null")
        elif isinstance(value, bool):
            lines.append(f"{prefix}{key}: {'true' if value else 'false'}")
        elif isinstance(value, (int, float)):
            lines.append(f"{prefix}{key}: {value}")
        elif isinstance(value, str):
            lines.append(f"{prefix}{key}: {value}")
        elif isinstance(value, list):
            if not value:
                lines.append(f"{prefix}{key}: []")
            elif all(isinstance(v, (str, int, float)) for v in value):
                items = ", ".join(str(v) for v in value)
                lines.append(f"{prefix}{key}: [{items}]")
            else:
                lines.append(f"{prefix}{key}:")
                for item in value:
                    if isinstance(item, dict):
                        lines.append(f"{prefix}  - {_inline_dict(item)}")
                    else:
                        lines.append(f"{prefix}  - {item}")
        elif isinstance(value, dict):
            if _is_attribute_claim(value):
                lines.append(f"{prefix}{key}: {_inline_dict(value)}")
            else:
                lines.append(f"{prefix}{key}:")
                _serialize_yaml(value, lines, indent + 1)


def _inline_dict(d: dict) -> str:
    parts = []
    for k, v in d.items():
        if isinstance(v, list):
            items = ", ".join(str(i) for i in v)
            parts.append(f"{k}: [{items}]")
        elif v is None:
            parts.append(f"{k}: null")
        elif isinstance(v, bool):
            parts.append(f"{k}: {'true' if v else 'false'}")
        else:
            parts.append(f"{k}: {v}")
    return "{" + ", ".join(parts) + "}"


def _is_attribute_claim(d: dict) -> bool:
    return "value" in d and "confidence" in d


def resolve_entity_in_world(root: Path, entity: str) -> Path:
    """Resolve entity file in v1 world/ directory structure."""
    candidates = [
        root / "world" / "players" / entity / "profile.md",
        root / "world" / "npcs" / "humans" / entity / "profile.md",
        root / "world" / "npcs" / "agents" / entity / "profile.md",
        root / "world" / "orgs" / entity / "profile.md",
        root / "world" / "operations" / entity / "profile.md",
        root / "world" / "players" / f"{entity}.md",
        root / "world" / "npcs" / "humans" / f"{entity}.md",
        root / "world" / "npcs" / "agents" / f"{entity}.md",
        root / "world" / "orgs" / f"{entity}.md",
        root / "world" / "operations" / f"{entity}.md",
    ]
    for c in candidates:
        if c.exists():
            return c
    for folder in [root / "world"]:
        for path in folder.rglob("*.md"):
            text = read_text(path)
            fm = frontmatter(text)
            if fm:
                m = ID_RE.search(fm)
                if m and m.group(1) == entity:
                    return path
    raise FileNotFoundError(f"entity not found in world/: {entity}")


def resolve_entity_any(root: Path, entity: str) -> Path:
    """Resolve entity in both v1 and legacy layouts."""
    if is_v1_vault(root):
        try:
            return resolve_entity_in_world(root, entity)
        except FileNotFoundError:
            pass
    return resolve_entity_file(root, entity)
