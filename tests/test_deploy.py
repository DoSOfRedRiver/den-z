import tempfile
import unittest
from pathlib import Path
from deploy import publish_local


class DeployTest(unittest.TestCase):
    def test_local_publish_copies_only_public_site_and_lesson_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            publish_local(dest)
            self.assertIn('Проектируем сокращатель ссылок', (dest / 'www' / 'index.html').read_text())
            self.assertTrue((dest / 'lessons' / '2026-10-26.json').is_file())
            self.assertFalse((dest / 'www' / 'backend.py').exists())
            self.assertFalse((dest / 'www' / 'token').exists())


if __name__ == '__main__': unittest.main()
