#!/usr/bin/env python3
"""Build a self-contained offline lesson from a reviewed JSON lesson."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def build(lesson_file: Path) -> Path:
    lesson = json.loads(lesson_file.read_text(encoding="utf-8"))
    required = {"id", "title", "track", "duration", "objective", "sections", "resources", "questions"}
    missing = required - lesson.keys()
    if missing:
        raise ValueError(f"Missing fields: {', '.join(sorted(missing))}")
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}(?:-db)?', lesson["id"]):
        raise ValueError("id must be a date or date-db")
    for resource in lesson["resources"]:
        if not isinstance(resource.get("url"), str) or not resource["url"].startswith("https://"):
            raise ValueError("Resource URLs must use HTTPS")
    for section in lesson["sections"]:
        for block in section.get("blocks", []):
            if block.get("type") != "diagram":
                continue
            nodes, edges = block.get("nodes"), block.get("edges")
            if not isinstance(block.get("caption"), str) or not block["caption"].strip() or not isinstance(nodes, list) or len(nodes) < 2 or not isinstance(edges, list) or not edges:
                raise ValueError("diagram needs caption, nodes and edges")
            positions, coordinates = {}, set()
            for node in nodes:
                if not isinstance(node, dict) or not isinstance(node.get("id"), str) or not node["id"] or node["id"] in positions or not isinstance(node.get("label"), str) or not node["label"].strip():
                    raise ValueError("diagram node needs unique id and label")
                x, y = node.get("x"), node.get("y")
                if type(x) is not int or x not in (-1, 0, 1) or type(y) is not int or y < 0 or (x, y) in coordinates:
                    raise ValueError("diagram coordinate must be unique grid cell")
                positions[node["id"]] = y
                coordinates.add((x, y))
            for edge in edges:
                if not isinstance(edge, dict) or edge.get("from") not in positions or edge.get("to") not in positions or positions[edge["from"]] >= positions[edge["to"]]:
                    raise ValueError("diagram edge must connect existing nodes forward")
                if "label" in edge and not isinstance(edge["label"], str):
                    raise ValueError("diagram edge label must be text")
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
