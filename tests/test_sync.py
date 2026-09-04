import unittest
from src.modules.sync_module import SyncModule

class TestSyncModule(unittest.TestCase):

    def test_adjust_annotations_positive_offset(self):
        """Verifica que un offset positivo desplace las marcas según la lógica (onset - offset)."""
        annotations = [
            {'onset': 10.0, 'duration': 0.0, 'description': 't0'},
            {'onset': 25.5, 'duration': 1.0, 'description': 't1'}
        ]
        offset_sec = 2.5

        adjusted = SyncModule.adjust_annotations(annotations, offset_sec)

        self.assertEqual(len(adjusted), 2)
        # 10.0 - 2.5 = 7.5
        self.assertAlmostEqual(adjusted[0]['onset'], 7.5, places=2)
        self.assertAlmostEqual(adjusted[1]['onset'], 23.0, places=2)
        self.assertEqual(adjusted[0]['description'], 't0')

if __name__ == '__main__':
    unittest.main()