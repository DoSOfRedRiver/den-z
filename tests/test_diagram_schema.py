import json
import tempfile
import unittest
from pathlib import Path

from build import build


class DiagramSchemaTests(unittest.TestCase):
    def setUp(self):
        self.lesson = json.loads(Path('lessons/2026-10-29.json').read_text())
        self.diagram = next(b for s in self.lesson['sections'] for b in s.get('blocks', []) if b['type'] == 'diagram')

    def check_invalid(self, message):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'lesson.json'
            source.write_text(json.dumps(self.lesson))
            with self.assertRaisesRegex(ValueError, message):
                build(source)

    def test_edges_must_reference_existing_nodes(self):
        self.diagram['edges'][0]['to'] = 'missing'
        self.check_invalid('diagram edge')

    def test_nodes_must_have_distinct_coordinates(self):
        self.diagram['nodes'][1]['y'] = self.diagram['nodes'][0]['y']
        self.check_invalid('diagram coordinate')

    def test_edges_must_go_forward(self):
        self.diagram['edges'][0]['from'], self.diagram['edges'][0]['to'] = self.diagram['edges'][0]['to'], self.diagram['edges'][0]['from']
        self.check_invalid('diagram edge')


if __name__ == '__main__':
    unittest.main()
