#!/usr/bin/env python3
"""Build a self-contained offline lesson from a reviewed JSON lesson."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def build(lesson_file: Path) -> Path:
    lesson = json.loads(lesson_file.read_text(encoding="utf-8"))
    required = {"id", "title", "track", "duration", "objective", "sections", "resources", "questions"}
    missing = required - lesson.keys()
    if missing:
        raise ValueError(f"Missing fields: {', '.join(sorted(missing))}")
    if not lesson["id"] or any(c not in "0123456789-" for c in lesson["id"]):
        raise ValueError("id must be an ISO-like date")
    ids = set()
    for q in lesson["questions"]:
        if q["id"] in ids or not q["id"].isalnum():
            raise ValueError("Question IDs must be unique alphanumeric strings")
        ids.add(q["id"])
        if q["type"] == "choice" and (not q["options"] or not isinstance(q["answer"], int) or not 0 <= q["answer"] < len(q["options"])):
            raise ValueError("Choice questions need a valid answer index")
        if q["type"] not in ("choice", "text"):
            raise ValueError("Unsupported question type")
    payload = json.dumps(lesson, ensure_ascii=False).replace("<", "\\u003c")
    template = (ROOT / "template.html").read_text(encoding="utf-8")
    if template.count("__LESSON_JSON__") != 1:
        raise ValueError("Expected exactly one lesson placeholder")
    out = ROOT / "out" / f"День Z — {lesson['id']}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(template.replace("__LESSON_JSON__", payload), encoding="utf-8")
    return out


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 build.py lessons/YYYY-MM-DD.json")
    print(build(Path(sys.argv[1]).resolve()))
