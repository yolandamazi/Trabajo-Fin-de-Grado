import unittest
import numpy as np
import os
import tempfile
from src.modules.ecg_module import ECGProcessor
from src.modules.edf_converter import EDFExporter

class TestECGProcessorUnified(unittest.TestCase):

    def setUp(self):
        self.processor = ECGProcessor()
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_read_unified_edf_success(self):
        """Verifica que read_unified_edf desempaquete correctamente y recupere marcas dentro de la duración."""
        test_edf = os.path.join(self.temp_dir.name, "test_unified.edf")
        
        # 3000 muestras a 1000 Hz = 3 segundos de duración total
        ecg = np.sin(np.linspace(0, 10, 3000))
        emg1 = np.cos(np.linspace(0, 10, 3000))
        emg2 = np.sin(np.linspace(0, 10, 3000)) * 0.5
        
        signals = [ecg, emg1, emg2]
        headers = [
            {'label': 'ECG', 'sample_rate': 1000, 'dimension': 'mV'},
            {'label': 'EMG_1', 'sample_rate': 1000, 'dimension': 'uV'},
            {'label': 'EMG_2', 'sample_rate': 1000, 'dimension': 'uV'}
        ]
        annotations = [
            {'onset': 0.5, 'duration': 0.0, 'description': 't0'},
            {'onset': 2.5, 'duration': 0.0, 'description': 't1'}
        ]

        EDFExporter.export_unified_edf(test_edf, signals, headers, annotations)

        ecg_sig, emg_sigs, meta = self.processor.read_unified_edf(test_edf)

        self.assertIsInstance(ecg_sig, np.ndarray)
        self.assertIsInstance(emg_sigs, np.ndarray)
        self.assertIsInstance(meta, dict)

        self.assertEqual(len(ecg_sig), 3000)
        self.assertEqual(emg_sigs.shape, (2, 3000))

        self.assertIn('annotations', meta)
        read_ann = meta['annotations']
        self.assertEqual(len(read_ann), 2)
        self.assertEqual(read_ann[0]['description'], 't0')
        self.assertAlmostEqual(read_ann[0]['onset'], 0.5, places=2)

    def test_read_unified_edf_inhomogeneous_channels(self):
        """Verifica que con canales EMG heterogéneos en tamaño, emg_signals devuelva np.array([])."""
        test_edf = os.path.join(self.temp_dir.name, "test_inhomogeneous.edf")

        ecg = np.zeros(1000)
        emg1 = np.zeros(500)
        emg2 = np.zeros(300)  # Dos canales EMG con distintas longitudes

        signals = [ecg, emg1, emg2]
        headers = [
            {'label': 'ECG', 'sample_rate': 1000, 'dimension': 'mV'},
            {'label': 'EMG_1', 'sample_rate': 500, 'dimension': 'uV'},
            {'label': 'EMG_2', 'sample_rate': 300, 'dimension': 'uV'}
        ]

        EDFExporter.export_unified_edf(test_edf, signals, headers, annotations=[])

        ecg_sig, emg_sigs, meta = self.processor.read_unified_edf(test_edf)

        self.assertEqual(len(ecg_sig), 1000)
        self.assertEqual(emg_sigs.size, 0)

if __name__ == '__main__':
    unittest.main()