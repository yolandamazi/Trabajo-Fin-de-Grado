import unittest
import numpy as np
import os
import tempfile
import pyedflib
from src.modules.edf_converter import EDFExporter

class TestEDFExporter(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_export_annotations(self):
        """Comprueba que las anotaciones de eventos se escriben correctamente en la cabecera EDF+."""
        out_path = os.path.join(self.temp_dir.name, "export_test.edf")
        
        # 1500 muestras a 500 Hz = 3 segundos de duración total
        signals = [np.ones(1500), np.zeros(1500)]
        headers = [
            {'label': 'ECG', 'sample_rate': 500, 'dimension': 'mV'},
            {'label': 'EMG1', 'sample_rate': 500, 'dimension': 'uV'}
        ]
        annotations = [
            {'onset': 0.1, 'duration': 0.0, 'description': 't0'},
            {'onset': 1.2, 'duration': 0.0, 'description': 't1'}
        ]

        EDFExporter.export_unified_edf(out_path, signals, headers, annotations)

        f = pyedflib.EdfReader(out_path)
        raw_ann = f.readAnnotations()
        f.close()

        onsets, durations, descriptions = raw_ann
        self.assertEqual(len(onsets), 2)
        self.assertAlmostEqual(onsets[0], 0.1, places=2)
        self.assertEqual(descriptions[0].strip(), 't0')
        self.assertAlmostEqual(onsets[1], 1.2, places=2)
        self.assertEqual(descriptions[1].strip(), 't1')

if __name__ == '__main__':
    unittest.main()