import json
import tempfile
import unittest
from pathlib import Path
from build import build


class BuildSecurityTest(unittest.TestCase):
    def test_rejects_non_https_resource_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'lesson.json'
            path.write_text(json.dumps({'id': '2026-10-26', 'title': 'x', 'track': 'x', 'duration': '1', 'objective': 'x', 'sections': [], 'resources': [{'label': 'link', 'url': 'javascript:alert(1)', 'note': ''}], 'questions': []}))
            with self.assertRaises(ValueError):
                build(path)


if __name__ == '__main__': unittest.main()
