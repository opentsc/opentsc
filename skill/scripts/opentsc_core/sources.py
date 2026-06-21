from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path

from .common import now_iso, read_text, sanitize_filename, stable_suffix, today, write_text, year_month_parts
from .vault import append_jsonl

TEXT_EXTS = {".md", ".txt", ".csv", ".json", ".yaml", ".yml"}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def create_source_package(root: Path, source_path: Path, material_type: str = "battle_report", source: str = "user", source_date: str | None = None, title: str | None = None, move: bool = False, extract: bool = True) -> dict[str, str]:
    if not source_path.exists():
        raise FileNotFoundError(source_path)
    y, m = year_month_parts()
    file_hash = sha256_file(source_path)
    raw_id = f"raw_{today().replace('-', '')}_{file_hash[:8]}"
    package_dir = root / "raw" / y / m / f"{raw_id}-{sanitize_filename(title or source_path.stem, 50)}"
    package_dir.mkdir(parents=True, exist_ok=True)
    original = package_dir / f"original{source_path.suffix or '.dat'}"
    if move:
        shutil.move(str(source_path), str(original))
        action = "move_source_package_original"
    else:
        shutil.copy2(source_path, original)
        action = "copy_source_package_original"
    content = _extract_text(original)
    extracted = package_dir / "extracted_text.md"
    write_text(extracted, content)
    manifest = {
        "raw_id": raw_id,
        "title": title or source_path.stem,
        "material_type": material_type,
        "source": source,
        "source_date": source_date or "TODO(user)",
        "original_path": str(source_path),
        "stored_original": str(original),
        "extracted_text": str(extracted),
        "sha256": file_hash,
        "file_size": original.stat().st_size,
        "ingested_at": now_iso(),
        "created_at": now_iso(),
        "status": "processed" if extract else "raw_only",
    }
    write_text(package_dir / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    write_text(package_dir / "metadata.yaml", _metadata_yaml(manifest))
    append_jsonl(root / "ledger" / "file-moves.jsonl", {"at": now_iso(), "from": str(source_path), "to": str(original), "reason": action, "raw_id": raw_id, "sha256": file_hash})
    generated = {}
    if extract:
        generated = create_source_candidates(root, raw_id, manifest["title"], content, material_type)
        manifest["generated"] = {k: str(v) for k, v in generated.items()}
        write_text(package_dir / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    append_jsonl(root / "ledger" / "processing-runs.jsonl", {"at": now_iso(), "action": "source_package_ingest", "raw_id": raw_id, "package": str(package_dir), "generated": manifest.get("generated", {})})
    return {"raw_id": raw_id, "package": str(package_dir), "original": str(original), "manifest": str(package_dir / "manifest.json"), **{k: str(v) for k, v in generated.items()}}


def create_source_candidates(root: Path, raw_id: str, title: str, content: str, material_type: str) -> dict[str, Path]:
    suffix = stable_suffix(raw_id + content, 8)
    base_fm = f"raw: {raw_id}\nsource_title: {title}\nmaterial_type: {material_type}\ncreated_at: {now_iso()}\nstatus: draft"
    people = _extract_people(content)
    orgs = _extract_orgs(content)
    paths = {
        "events": root / "inbox" / "events" / f"draft_events_{today().replace('-', '')}_{suffix}.md",
        "entities": root / "inbox" / "entities" / f"draft_entities_{today().replace('-', '')}_{suffix}.md",
        "relations": root / "inbox" / "relations" / f"draft_relations_{today().replace('-', '')}_{suffix}.md",
        "knowledge": root / "inbox" / "knowledge" / f"draft_knowledge_{today().replace('-', '')}_{suffix}.md",
        "intel_gaps": root / "inbox" / "intel_gaps" / f"draft_gaps_{today().replace('-', '')}_{suffix}.md",
        "breakthroughs": root / "inbox" / "breakthroughs" / f"draft_breakthroughs_{today().replace('-', '')}_{suffix}.md",
        "actions": root / "inbox" / "actions" / f"draft_actions_from_source_{today().replace('-', '')}_{suffix}.md",
    }
    write_text(paths["events"], f"---\ntype: inbox_event_batch\n{base_fm}\n---\n\n# Candidate events\n\n- TODO(entity_id) · B6 · TODO(extracted event from {title}) · source:{raw_id}\n\n## Source excerpt\n\n{content[:1200]}\n")
    write_text(paths["entities"], f"---\ntype: inbox_entity_batch\n{base_fm}\n---\n\n# Candidate entities\n\n## People-like mentions\n" + "".join(f"- {p}\n" for p in people[:80]) + "\n## Org-like mentions\n" + "".join(f"- {o}\n" for o in orgs[:80]))
    write_text(paths["relations"], f"---\ntype: inbox_relation_batch\n{base_fm}\n---\n\n# Candidate free-form relations\n\n用户怎么说就怎么记录关系类型，不写死枚举；使用时让 AI 判断关系定位、强度、风险和行动含义。\n\n- TODO(source_id) TODO(user_relation_phrase) TODO(target_id) · confidence: low · evidence:{raw_id}\n\n## Examples\n\n- p_a 夫妻 p_b\n- p_a 仇人 p_b\n- p_a 兄弟死党 p_b\n- p_a 引荐 p_b\n")
    write_text(paths["knowledge"], f"---\ntype: inbox_knowledge_batch\nlayer: methods\nsample_size: 1\n{base_fm}\n---\n\n# Candidate knowledge\n\n- TODO(granule): extracted from {raw_id}; keep only if user confirms.\n")
    write_text(paths["intel_gaps"], f"---\ntype: inbox_intel_gap_batch\n{base_fm}\n---\n\n# Intelligence gaps\n\n- TODO: 哪些关键关系未确认？\n- TODO: 哪些情绪变化可能是突破口？\n- TODO: 哪个事件缺少 A/B 级证据？\n- TODO: 谁是引荐人/影响者/阻碍者？\n")
    write_text(paths["breakthroughs"], f"---\ntype: inbox_breakthrough_batch\n{base_fm}\n---\n\n# Relationship / Emotion / Event Breakthroughs\n\n## Relationship openings\n- TODO: 可借谁引荐谁？谁和谁关系紧密/敌对/夫妻/死党/利益绑定？\n\n## Emotion openings\n- TODO: 材料里谁焦虑、犹豫、抗拒、兴奋、急迫？这意味着什么行动窗口？\n\n## Event openings\n- TODO: 哪个事件可以作为见面、电话、调查、报价或复盘的切入点？\n")
    write_text(paths["actions"], f"---\ntype: inbox_action_batch\n{base_fm}\n---\n\n# Draft Actions from Source\n\n## 1. 核实关键关系\n\n- action_type: verify_claim\n- due: TODO(YYYY-MM-DD)\n- operation: TODO(optional)\n- target_entities: TODO(user)\n- expected_output: 更新 relations/edges.jsonl 或人物 timeline\n- status: draft\n\n## 2. 安排情报收集\n\n- action_type: intel_collection\n- due: TODO(YYYY-MM-DD)\n- operation: TODO(optional)\n- target_entities: TODO(user)\n- expected_output: 新 raw material + source list\n- status: draft\n")
    return paths


def list_sources(root: Path, month: str | None = None, material_type: str | None = None) -> list[dict[str, str]]:
    rows = []
    for manifest in (root / "raw").glob("**/manifest.json"):
        data = json.loads(read_text(manifest))
        if month and not data.get("ingested_at", "").startswith(month):
            continue
        if material_type and data.get("material_type") != material_type:
            continue
        rows.append({"raw_id": data.get("raw_id", ""), "title": data.get("title", ""), "type": data.get("material_type", ""), "ingested_at": data.get("ingested_at", ""), "package": str(manifest.parent)})
    return sorted(rows, key=lambda r: r.get("ingested_at", ""))


def source_info(root: Path, raw_id: str) -> dict:
    manifest = _find_manifest(root, raw_id)
    return json.loads(read_text(manifest))


def source_derived(root: Path, raw_id: str) -> dict[str, list[str]]:
    out = {"inbox": [], "knowledge": [], "events": [], "actions": []}
    for folder in ["inbox", "knowledge", "people", "orgs", "operations", "actions"]:
        base = root / folder
        if not base.exists():
            continue
        for path in base.glob("**/*.md"):
            text = read_text(path)
            if raw_id in text:
                key = "inbox" if folder == "inbox" else "knowledge" if folder == "knowledge" else "actions" if folder == "actions" else "events"
                out[key].append(str(path))
    return out


def source_audit(root: Path) -> list[str]:
    issues = []
    seen_hashes = {}
    for manifest in (root / "raw").glob("**/manifest.json"):
        data = json.loads(read_text(manifest))
        raw_id = data.get("raw_id", manifest.parent.name)
        original = Path(data.get("stored_original", ""))
        if not original.exists():
            issues.append(f"missing stored original for {raw_id}: {original}")
        if not data.get("sha256"):
            issues.append(f"missing sha256 for {raw_id}")
        elif data["sha256"] in seen_hashes:
            issues.append(f"duplicate source hash {data['sha256']}: {seen_hashes[data['sha256']]} and {raw_id}")
        else:
            seen_hashes[data["sha256"]] = raw_id
        if not data.get("generated"):
            issues.append(f"source has no generated candidates: {raw_id}")
    return issues


def _find_manifest(root: Path, raw_id: str) -> Path:
    matches = list((root / "raw").glob(f"**/{raw_id}*/manifest.json"))
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValueError(f"ambiguous raw id: {raw_id}")
    raise FileNotFoundError(f"source not found: {raw_id}")


def _extract_text(path: Path) -> str:
    if path.suffix.lower() in TEXT_EXTS:
        return read_text(path)
    return f"[binary/source file preserved at {path.name}; text extraction TODO]\n"


def _metadata_yaml(data: dict) -> str:
    return "\n".join(f"{k}: {v}" for k, v in data.items() if k != "generated") + "\n"


def _extract_people(content: str) -> list[str]:
    return sorted(set(re.findall(r"[A-Z][a-zA-Z]{2,}|[一-鿿]{2,4}", content)))


def _extract_orgs(content: str) -> list[str]:
    tokens = re.findall(r"[A-Z][A-Za-z0-9& ]{2,}(?:Team|Capital|Studio|Inc|LLC|机构|公司|团队|项目)", content)
    return sorted(set(t.strip() for t in tokens))
