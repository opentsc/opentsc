from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from .common import read_text, stable_suffix, today, write_text
from .vault import append_jsonl, new_person

PHONE_RE = re.compile(r"\D+")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_phone(value: str) -> str:
    return PHONE_RE.sub("", value or "")


def normalize_email(value: str) -> str:
    return (value or "").strip().lower()


def import_contacts_csv(root: Path, csv_path: Path, name_col: str = "name", phone_col: str = "phone", email_col: str = "email") -> dict[str, int]:
    root = root.resolve()
    existing = _index_contacts(root)
    created = 0
    strong_matches = 0
    weak_suggestions = 0
    suggestions_path = root / "contacts" / "merge-suggestions.jsonl"
    import_log = root / "contacts" / "import-log.jsonl"

    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get(name_col) or row.get("Name") or row.get("姓名") or "").strip()
            phone = normalize_phone(row.get(phone_col) or row.get("Phone") or row.get("电话") or "")
            email = normalize_email(row.get(email_col) or row.get("Email") or row.get("邮箱") or "")
            if not name and not phone and not email:
                continue
            strong_key = email or phone
            if strong_key and strong_key in existing:
                strong_matches += 1
                append_jsonl(import_log, {"date": today(), "action": "strong_match_existing", "entity": existing[strong_key], "name": name, "phone": phone, "email": email})
                continue
            weak = _weak_name_matches(root, name) if name else []
            if weak:
                weak_suggestions += 1
                append_jsonl(suggestions_path, {"date": today(), "reason": "similar_name", "candidate_name": name, "matches": weak, "phone": phone, "email": email, "status": "needs_user_confirmation"})
            entity_id = f"p_{stable_suffix(name + phone + email, 8)}"
            path = new_person(root, name or f"contact-{entity_id}", entity_id=entity_id, aliases=[], tags=["contact_import"])
            _append_contact_fields(path, phone, email)
            created += 1
            if email:
                existing[email] = entity_id
            if phone:
                existing[phone] = entity_id
            append_jsonl(import_log, {"date": today(), "action": "created_light_node", "entity": entity_id, "name": name, "phone": phone, "email": email})
    return {"created": created, "strong_matches": strong_matches, "weak_suggestions": weak_suggestions}


def _index_contacts(root: Path) -> dict[str, str]:
    index: dict[str, str] = {}
    for path in (root / "people").glob("**/*.md"):
        text = read_text(path)
        id_match = re.search(r"^id:\s*(p_[\w-]+)", text, re.MULTILINE)
        if not id_match:
            continue
        entity_id = id_match.group(1)
        for email in re.findall(r"email:\s*([^\s]+)", text):
            norm = normalize_email(email)
            if norm:
                index[norm] = entity_id
        for phone in re.findall(r"phone:\s*([^\s]+)", text):
            norm = normalize_phone(phone)
            if norm:
                index[norm] = entity_id
    return index


def _weak_name_matches(root: Path, name: str) -> list[dict[str, str]]:
    matches: list[dict[str, str]] = []
    if not name:
        return matches
    for path in (root / "people").glob("**/*.md"):
        text = read_text(path)
        id_match = re.search(r"^id:\s*(p_[\w-]+)", text, re.MULTILINE)
        real_match = re.search(r"^\s*real:\s*(.+?)\s*$", text, re.MULTILINE)
        if not id_match or not real_match:
            continue
        existing = real_match.group(1).strip()
        if existing == name or (len(name) >= 2 and name in existing) or (len(existing) >= 2 and existing in name):
            matches.append({"entity": id_match.group(1), "name": existing, "path": str(path)})
    return matches


def _append_contact_fields(path: Path, phone: str, email: str) -> None:
    text = read_text(path)
    block = "\ncontact:\n"
    if phone:
        block += f"  phone: {phone}\n"
    if email:
        block += f"  email: {email}\n"
    if "tags:" in text:
        text = text.replace("tags:", block + "tags:", 1)
    else:
        text = text.replace("---\n\n", block + "---\n\n", 1)
    write_text(path, text)
