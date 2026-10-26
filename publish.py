#!/usr/bin/env python3
"""Build public static lessons for GitHub Pages; never include private progress."""
import html
import json
from pathlib import Path
from build import build

ROOT = Path(__file__).resolve().parent
LESSONS = sorted((ROOT / "lessons").glob("????-??-??.json"))
if not LESSONS:
    raise SystemExit("No lessons")
site = ROOT / "docs"
(site / "lessons").mkdir(parents=True, exist_ok=True)
ids = []
for lesson_path in LESSONS:
    lesson = json.loads(lesson_path.read_text(encoding="utf-8"))
    ids.append((lesson["id"], lesson["title"]))
def with_archive(rendered: str, prefix: str) -> str:
    links = "".join(
        f'<li><a href="{prefix}lessons/{html.escape(lesson_id, quote=True)}.html">{html.escape(lesson_id)} · {html.escape(title)}</a></li>'
        for lesson_id, title in reversed(ids)
    )
    archive = f'<section aria-label="Архив"><h2>Архив выпусков</h2><ul>{links}</ul></section>'
    return rendered.replace('<footer class="note"', archive + '<footer class="note"', 1)

latest = None
for lesson_path in LESSONS:
    lesson_id = lesson_path.stem
    rendered = build(lesson_path).read_text(encoding="utf-8")
    # Archive contains lesson data only; no score, user answer or private metadata.
    (site / "lessons" / f"{lesson_id}.html").write_text(with_archive(rendered, '../'), encoding="utf-8")
    latest = rendered
(site / "index.html").write_text(with_archive(latest, ''), encoding="utf-8")
(site / ".nojekyll").write_text("", encoding="utf-8")
print(f"Built {len(ids)} public lessons; latest={ids[-1][0]}")
