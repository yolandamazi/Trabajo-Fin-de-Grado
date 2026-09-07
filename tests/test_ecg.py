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
        """Verifica que read_edf_all_channels recupere señales, metadatos y anotaciones respetando magnitudes."""
        test_edf = os.path.join(self.temp_dir.name, "test_ecg_read.edf")

        # 3000 muestras a 1000 Hz (3 segundos)
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

        # 1. Exportar a archivo temporal
        EDFExporter.export_unified_edf(test_edf, signals, headers, annotations)

        # 2. Leer con el método oficial read_edf_all_channels
        read_signals, meta, read_ann = self.processor.read_edf_all_channels(test_edf)

        # 3. Validar número de canales y muestras
        self.assertEqual(len(read_signals), 2)
        self.assertEqual(len(read_signals[0]), 3000)
        self.assertIsInstance(meta, dict)

        # 4. Verificar dimensiones preservadas (mV y uV)
        self.assertEqual(meta['headers'][0]['dimension'], 'mV')
        self.assertEqual(meta['headers'][1]['dimension'], 'uV')

        # 5. Verificar anotaciones TAL recuperadas
        self.assertEqual(len(read_ann), 1)
        first_desc = read_ann[0]['description'] if isinstance(read_ann[0], dict) else read_ann[0][-1]
        self.assertEqual(first_desc, 't0')


if __name__ == '__main__':
    unittest.main()