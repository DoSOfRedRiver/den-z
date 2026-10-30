"""Record one human review of an already saved lesson attempt."""
import hashlib
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path


def ensure_reviews_table(db):
    db.execute('''CREATE TABLE IF NOT EXISTS reviews (
        submission_id INTEGER PRIMARY KEY REFERENCES submissions(id),
        scores TEXT NOT NULL, open_score INTEGER NOT NULL, open_total INTEGER NOT NULL,
        overall_percent REAL NOT NULL, feedback TEXT NOT NULL,
        lesson_sha256 TEXT NOT NULL, reviewed_at TEXT NOT NULL
    )''')


def save_review(db_path: Path, lesson_dir: Path, submission_id: int,
                scores: dict, feedback: str) -> dict:
    if not isinstance(feedback, str) or not feedback.strip():
        raise ValueError('review feedback required')
    with closing(sqlite3.connect(db_path)) as db, db:
        db.execute('BEGIN IMMEDIATE')
        ensure_reviews_table(db)
        row = db.execute('SELECT lesson_id, answers, choice_score, choice_total, open_status '
                         'FROM submissions WHERE id=?', (submission_id,)).fetchone()
        if not row:
            raise ValueError('submission not found')
        lesson_id, answers_json, choice_score, choice_total, status = row
        if status != 'pending' or db.execute('SELECT 1 FROM reviews WHERE submission_id=?',
                                             (submission_id,)).fetchone():
            raise ValueError('submission already reviewed')
        lesson_bytes = (Path(lesson_dir) / (lesson_id + '.json')).read_bytes()
        lesson = json.loads(lesson_bytes)
        questions = [q for q in lesson['questions'] if q['type'] == 'text']
        if lesson['id'] != lesson_id or set(scores) != {q['id'] for q in questions}:
            raise ValueError('scores must cover every open question')
        answers = json.loads(answers_json)
        if set(answers) != {q['id'] for q in lesson['questions']}:
            raise ValueError('lesson version does not match submission')
        if choice_total != sum(q['type'] == 'choice' for q in lesson['questions']):
            raise ValueError('choice total differs from lesson version')
        for score, maximum in scores.values():
            if (type(score) is not int or type(maximum) is not int or maximum <= 0
                    or not 0 <= score <= maximum):
                raise ValueError('invalid open score')
        open_score = sum(v[0] for v in scores.values())
        open_total = sum(v[1] for v in scores.values())
        overall = round(100 * (0.25 * choice_score / choice_total
                               + 0.75 * open_score / open_total), 2)
        reviewed_at = datetime.now(timezone.utc).isoformat(timespec='seconds')
        db.execute('INSERT INTO reviews VALUES (?,?,?,?,?,?,?,?)',
                   (submission_id, json.dumps(scores, ensure_ascii=False), open_score,
                    open_total, overall, feedback.strip(), hashlib.sha256(lesson_bytes).hexdigest(),
                    reviewed_at))
        db.execute("UPDATE submissions SET open_status='reviewed' WHERE id=? AND open_status='pending'",
                   (submission_id,))
        return {'open_score': open_score, 'open_total': open_total,
                'overall_percent': overall, 'review_feedback': feedback.strip(),
                'lesson_sha256': hashlib.sha256(lesson_bytes).hexdigest(),
                'reviewed_at': reviewed_at}
