#!/usr/bin/env python3
"""Private progress API. Only loopback; put HTTPS reverse proxy in front."""
import argparse
import hmac
import json
import re
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from review import ensure_reviews_table

LESSON_ID = re.compile(r'^\d{4}-\d{2}-\d{2}(?:-db)?$')


def make_server(host: str, port: int, lesson_dir: Path, db_path: Path, token: str):
    if not token or len(token) < 8:
        raise ValueError('token is required')
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db_path)) as db, db:
        db.execute('CREATE TABLE IF NOT EXISTS submissions (id INTEGER PRIMARY KEY, lesson_id TEXT NOT NULL, answers TEXT NOT NULL, choice_score INTEGER NOT NULL, choice_total INTEGER NOT NULL, open_status TEXT NOT NULL, created_at TEXT NOT NULL)')
        ensure_reviews_table(db)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            # Don't log request content or Authorization headers.
            super().log_message(fmt, *args)

        def respond(self, code, body):
            payload = json.dumps(body, ensure_ascii=False).encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(payload)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(payload)

        def authorized(self):
            header = self.headers.get('Authorization', '')
            return hmac.compare_digest(header, 'Bearer ' + token)

        def do_GET(self):
            if self.path == '/api/health':
                return self.respond(200, {'ok': True})
            if self.path != '/api/progress':
                return self.respond(404, {'error': 'not found'})
            if not self.authorized():
                return self.respond(401, {'error': 'unauthorized'})
            with closing(sqlite3.connect(db_path)) as db, db:
                rows = db.execute('''SELECT s.id, s.lesson_id, s.answers, s.choice_score, s.choice_total,
                    s.open_status, s.created_at, r.open_score, r.open_total,
                    r.overall_percent, r.feedback, r.scores, r.reviewed_at
                    FROM submissions s LEFT JOIN reviews r ON r.submission_id=s.id
                    ORDER BY s.id DESC LIMIT 200''').fetchall()
            return self.respond(200, {'submissions': [dict(id=r[0], lesson_id=r[1], answers=json.loads(r[2]), choice_score=r[3], choice_total=r[4], open_status=r[5], created_at=r[6], open_score=r[7], open_total=r[8], overall_percent=r[9], review_feedback=r[10], open_scores=json.loads(r[11]) if r[11] else None, reviewed_at=r[12]) for r in rows]})

        def do_POST(self):
            if self.path != '/api/submissions':
                return self.respond(404, {'error': 'not found'})
            if not self.authorized():
                return self.respond(401, {'error': 'unauthorized'})
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if length < 2 or length > 16384:
                    raise ValueError('invalid payload length')
                data = json.loads(self.rfile.read(length))
                lesson_id, answers = data['lesson_id'], data['answers']
                if not isinstance(lesson_id, str) or not LESSON_ID.fullmatch(lesson_id) or not isinstance(answers, dict):
                    raise ValueError('invalid lesson or answers')
                path = lesson_dir / f'{lesson_id}.json'
                lesson = json.loads(path.read_text(encoding='utf-8'))
                questions = {q['id']: q for q in lesson['questions']}
                if lesson['id'] != lesson_id or set(answers) != set(questions):
                    raise ValueError('unknown questions')
                for qid, answer in answers.items():
                    q = questions[qid]
                    if not isinstance(answer, str) or len(answer) > 8000:
                        raise ValueError('invalid answer length')
                    if q['type'] == 'choice' and answer not in [str(i) for i in range(len(q['options']))] + ['']:
                        raise ValueError('invalid choice')
                choice = [q for q in questions.values() if q['type'] == 'choice']
                score = sum(answers[q['id']] == str(q['answer']) for q in choice)
                created_at = datetime.now(timezone.utc).isoformat(timespec='seconds')
                with closing(sqlite3.connect(db_path)) as db, db:
                    cur = db.execute('INSERT INTO submissions (lesson_id,answers,choice_score,choice_total,open_status,created_at) VALUES (?,?,?,?,?,?)', (lesson_id, json.dumps(answers, ensure_ascii=False), score, len(choice), 'pending', created_at))
                    submission_id = cur.lastrowid
                return self.respond(201, dict(id=submission_id, lesson_id=lesson_id, choice_score=score, choice_total=len(choice), open_status='pending', created_at=created_at))
            except (ValueError, KeyError, TypeError, json.JSONDecodeError, FileNotFoundError):
                return self.respond(400, {'error': 'invalid submission'})

    return ThreadingHTTPServer((host, port), Handler)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--lessons', type=Path, required=True)
    parser.add_argument('--db', type=Path, required=True)
    parser.add_argument('--token-file', type=Path, required=True)
    args = parser.parse_args()
    secret = args.token_file.read_text(encoding='ascii').strip()
    make_server(args.host, args.port, args.lessons, args.db, secret).serve_forever()
