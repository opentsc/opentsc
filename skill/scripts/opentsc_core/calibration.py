from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

from .common import DUE_RE, STATUS_RE, read_text, today, write_text


def due_predictions(root: Path, on_or_before: str | None = None) -> list[dict[str, str]]:
    cutoff = dt.date.fromisoformat(on_or_before) if on_or_before else dt.date.today()
    results: list[dict[str, str]] = []
    feedback = root / "feedback"
    if not feedback.exists():
        return results
    for path in feedback.glob("**/*.md"):
        text = read_text(path)
        due_match = DUE_RE.search(text)
        if not due_match:
            continue
        due_date = dt.date.fromisoformat(due_match.group(1))
        status_match = STATUS_RE.search(text)
        status = status_match.group(1) if status_match else "open"
        if status in {"fulfilled", "closed"}:
            continue
        if due_date <= cutoff:
            title = _first_heading(text) or path.stem
            context = _frontmatter_value(text, "context") or ""
            results.append({"id": path.stem, "due": due_date.isoformat(), "status": status, "context": context, "title": title, "path": str(path)})
    return sorted(results, key=lambda x: (x["due"], x["id"]))


def calibrate(root: Path, pred_id: str, result: str, note: str = "") -> Path:
    if result not in {"correct", "wrong", "partial"}:
        raise ValueError("result must be correct|wrong|partial")
    path = _find_prediction(root, pred_id)
    text = read_text(path)
    text = re.sub(r"^status:\s*\w+\s*$", "status: fulfilled", text, count=1, flags=re.MULTILINE)
    block = f"\n## Calibration outcome\n\n- fulfilled: {today()}\n- result: {result}\n- note: {note or 'TODO(user)'}\n"
    if "## Calibration outcome" in text:
        text = re.sub(r"\n## Calibration outcome\n[\s\S]*$", block, text)
    else:
        text = text.rstrip() + block
    write_text(path, text)
    return path


def accuracy(root: Path) -> dict[str, str | int | float]:
    feedback = root / "feedback"
    total = correct = wrong = partial = open_count = 0
    if feedback.exists():
        for path in feedback.glob("**/*.md"):
            text = read_text(path)
            if "kind:" not in text:
                continue
            total += 1
            result = re.search(r"^- result:\s*(\w+)\s*$", text, re.MULTILINE)
            if result:
                value = result.group(1)
                correct += value == "correct"
                wrong += value == "wrong"
                partial += value == "partial"
            else:
                open_count += 1
    score = (correct + partial * 0.5) / (correct + wrong + partial) if (correct + wrong + partial) else 0.0
    return {"total": total, "correct": correct, "wrong": wrong, "partial": partial, "open": open_count, "accuracy": round(score, 3)}


def _find_prediction(root: Path, pred_id: str) -> Path:
    matches = []
    for path in (root / "feedback").glob("**/*.md"):
        text = read_text(path)
        if path.stem == pred_id or path.stem.startswith(pred_id) or pred_id in text:
            matches.append(path)
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise FileNotFoundError(f"prediction id is ambiguous: {pred_id}; matches: {', '.join(p.stem for p in matches)}")
    raise FileNotFoundError(f"prediction not found: {pred_id}")


def _first_heading(text: str) -> str | None:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


def _frontmatter_value(text: str, key: str) -> str | None:
    match = re.search(rf"^{re.escape(key)}:\s*(.+?)\s*$", text, re.MULTILINE)
    return match.group(1).strip() if match else None
