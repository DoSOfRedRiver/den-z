import json
import sqlite3
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from backend import make_server
from review import save_review


class BackendTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / 'lessons').mkdir()
        (self.root / 'lessons' / '2026-10-26.json').write_text(json.dumps({
            'id': '2026-10-26', 'title': 'Тест', 'questions': [
                {'id': 'q1', 'type': 'choice', 'options': ['A', 'B'], 'answer': 1},
                {'id': 'q2', 'type': 'text', 'prompt': 'Explain'}]
        }), encoding='utf-8')
        self.server = make_server('127.0.0.1', 0, self.root / 'lessons', self.root / 'progress.sqlite', 'secret-test')
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = 'http://127.0.0.1:' + str(self.server.server_port)

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(); self.tmp.cleanup()

    def request(self, method, path, data=None, token=None):
        headers = {'Content-Type': 'application/json'}
        if token is not None:
            headers['Authorization'] = 'Bearer ' + token
        payload = json.dumps(data).encode() if data is not None else None
        req = urllib.request.Request(self.base + path, payload, headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=3) as r:
                return r.status, json.load(r)
        except urllib.error.HTTPError as e:
            with e:
                return e.code, json.load(e)

    def test_authorized_submissions_persist_and_return_history(self):
        payload = {'lesson_id': '2026-10-26', 'answers': {'q1': '1', 'q2': 'Аргумент'}}
        status, saved = self.request('POST', '/api/submissions', payload, 'secret-test')
        self.assertEqual(status, 201)
        self.assertEqual(saved['choice_score'], 1)
        self.assertEqual(saved['choice_total'], 1)
        self.assertEqual(saved['open_status'], 'pending')
        status, history = self.request('GET', '/api/progress', token='secret-test')
        self.assertEqual(status, 200)
        self.assertEqual(history['submissions'][0]['answers']['q2'], 'Аргумент')
        self.assertEqual(history['submissions'][0]['lesson_id'], '2026-10-26')

    def test_review_is_scored_and_visible_only_to_owner(self):
        lesson_path = self.root / 'lessons' / '2026-10-26.json'
        lesson = json.loads(lesson_path.read_text())
        lesson['questions'][1]['rubric'] = 'Объяснить причину'
        lesson_path.write_text(json.dumps(lesson))
        status, saved = self.request('POST', '/api/submissions',
            {'lesson_id':'2026-10-26','answers':{'q1':'1','q2':'Аргумент'}}, 'secret-test')
        self.assertEqual(status, 201)
        review = save_review(self.root / 'progress.sqlite', self.root / 'lessons',
            saved['id'], {'q2':(3,4)}, 'Не описана граница гарантии.')
        self.assertEqual(review['overall_percent'], 81.25)
        owner = self.request('GET', '/api/progress', token='secret-test')[1]['submissions'][0]
        self.assertEqual(owner['open_status'], 'reviewed')
        self.assertEqual(owner['open_score'], 3)
        self.assertEqual(owner['open_total'], 4)
        self.assertEqual(owner['overall_percent'], 81.25)
        self.assertIn('граница', owner['review_feedback'])
        self.assertEqual(self.request('GET','/api/progress')[0],401)
        with sqlite3.connect(self.root / 'progress.sqlite') as db:
            self.assertEqual(db.execute('select answers from submissions where id=?',(saved['id'],)).fetchone()[0],json.dumps({'q1':'1','q2':'Аргумент'},ensure_ascii=False))
        with self.assertRaisesRegex(ValueError,'reviewed'):
            save_review(self.root / 'progress.sqlite', self.root / 'lessons', saved['id'], {'q2':(3,4)}, 'Duplicate')

    def test_token_required_for_results(self):
        for method, path, body in [('GET', '/api/progress', None), ('POST', '/api/submissions', {'lesson_id': '2026-10-26', 'answers': {}})]:
            self.assertEqual(self.request(method, path, body)[0], 401)
            self.assertEqual(self.request(method, path, body, 'wrong')[0], 401)

    def test_db_track_submission_uses_distinct_lesson_id(self):
        (self.root / 'lessons' / '2026-10-26-db.json').write_text(json.dumps({
            'id': '2026-10-26-db', 'title': 'БД', 'questions': [
                {'id': 'q1', 'type': 'choice', 'options': ['A', 'B'], 'answer': 0}
            ]}), encoding='utf-8')
        status, saved = self.request('POST', '/api/submissions',
            {'lesson_id': '2026-10-26-db', 'answers': {'q1': '0'}}, 'secret-test')
        self.assertEqual(status, 201)
        self.assertEqual(saved['lesson_id'], '2026-10-26-db')

    def test_reject_unknown_lesson_and_invalid_answer(self):
        for body in [
            {'lesson_id': '../token', 'answers': {'q1': '1'}},
            {'lesson_id': '2026-10-26', 'answers': {'q1': '7'}},
            {'lesson_id': '2026-10-26', 'answers': {'q2': 'a' * 12000}},
        ]:
            self.assertEqual(self.request('POST', '/api/submissions', body, 'secret-test')[0], 400)
        self.assertEqual(self.request('GET', '/api/progress', token='secret-test')[1]['submissions'], [])


if __name__ == '__main__':
    unittest.main()
