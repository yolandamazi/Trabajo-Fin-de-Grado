import os
import tempfile
import unittest
import numpy as np
from src.modules.ecg_module import ECGProcessor
from src.modules.edf_converter import EDFExporter


class TestECGProcessor(unittest.TestCase):

    def setUp(self):
        self.processor = ECGProcessor()
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_read_edf_all_channels_success(self):
        """Verifica que read_edf_all_channels recupere señales, metadatos y anotaciones bajo el esquema estricto."""
        test_edf = os.path.join(self.temp_dir.name, "test_ecg_read.edf")

        ecg = np.sin(np.linspace(0, 10, 3000))
        emg1 = np.cos(np.linspace(0, 10, 3000))

        signals = [ecg, emg1]
        headers = [
            {'label': 'ECG', 'sample_rate': 1000, 'dimension': 'mV'},
            {'label': 'EMG_1', 'sample_rate': 1000, 'dimension': 'uV'}
        ]
        annotations = [
            {'onset': 0.5, 'duration': 0.0, 'description': 't0'}
        ]

        EDFExporter.export_unified_edf(test_edf, signals, headers, annotations)
        read_signals, meta, read_ann = self.processor.read_edf_all_channels(test_edf)

        self.assertEqual(len(read_signals), 2)
        self.assertEqual(len(read_signals[0]), 3000)
        self.assertIsInstance(meta, dict)

        self.assertEqual(meta['headers'][0]['dimension'], 'mV')
        self.assertEqual(meta['headers'][1]['dimension'], 'uV')

        self.assertEqual(len(read_ann), 1)
        first_desc = read_ann[0]['description'] if isinstance(read_ann[0], dict) else read_ann[0][-1]
        self.assertEqual(first_desc, 't0')

    def test_exporter_missing_dimension_raises_error(self):
        """Verifica que el exportador falle de manera estricta (fail-fast) si falta la dimensión en un canal."""
        test_edf = os.path.join(self.temp_dir.name, "test_ecg_fail.edf")
        ecg = np.sin(np.linspace(0, 10, 1000))

        signals = [ecg]
        headers = [
            {'label': 'ECG', 'sample_rate': 1000, 'dimension': ''}  # Dimensión vacía
        ]

        with self.assertRaises(ValueError):
            EDFExporter.export_unified_edf(test_edf, signals, headers)

    def test_exporter_missing_fs_raises_error(self):
        """Verifica que el exportador falle si falta la frecuencia de muestreo."""
        test_edf = os.path.join(self.temp_dir.name, "test_ecg_fail_fs.edf")
        ecg = np.sin(np.linspace(0, 10, 1000))

        signals = [ecg]
        headers = [
            {'label': 'ECG', 'sample_rate': 0, 'dimension': 'mV'}  # Fs inválida
        ]

        with self.assertRaises(ValueError):
            EDFExporter.export_unified_edf(test_edf, signals, headers)


if __name__ == '__main__':
    unittest.main()