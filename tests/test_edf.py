import os
import tempfile
import unittest
import numpy as np
import pyedflib
from src.modules.edf_converter import EDFExporter

class TestEDFExporter(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_export_signals_and_dimensions(self):
        """Verifica que las magnitudes físicas (mV vs uV) y las frecuencias de muestreo se conserven intactas al exportar."""
        out_path = os.path.join(self.temp_dir.name, "export_signals_test.edf")

        # 1 segundo completo para coincidir con el bloque de registro de pyedflib
        ecg_data = np.full(256, 0.5, dtype=np.float64)
        emg_data = np.full(1000, 25.0, dtype=np.float64)

        signals = [ecg_data, emg_data]
        headers = [
            {'label': 'ECG_I', 'sample_rate': 256, 'dimension': 'mV'},
            {'label': 'EMG_BICEPS', 'sample_rate': 1000, 'dimension': 'uV'}
        ]

        # Exportar
        EDFExporter.export_unified_edf(out_path, signals, headers, annotations=[])

        # Leer y verificar
        f = pyedflib.EdfReader(out_path)
        try:
            self.assertEqual(f.signals_in_file, 2)

            # Validar canal ECG (mV)
            self.assertEqual(f.getLabel(0).strip(), 'ECG_I')
            self.assertEqual(f.getPhysicalDimension(0).strip(), 'mV')
            self.assertEqual(f.getSampleFrequency(0), 256)
            np.testing.assert_array_almost_equal(f.readSignal(0), ecg_data, decimal=2)

            # Validar canal EMG (uV)
            self.assertEqual(f.getLabel(1).strip(), 'EMG_BICEPS')
            self.assertEqual(f.getPhysicalDimension(1).strip(), 'uV')
            self.assertEqual(f.getSampleFrequency(1), 1000)
            np.testing.assert_array_almost_equal(f.readSignal(1), emg_data, decimal=2)
        finally:
            # Garantiza el cierre del descriptor en Windows aunque falle un assert
            f.close()
            
    def test_export_missing_dimension_raises_error(self):
      """Verifica que el exportador falle de forma estricta si algún canal carece de dimensión."""
      out_path = os.path.join(self.temp_dir.name, "fail_dim.edf")
      signals = [np.full(100, 1.0)]
      headers = [{"label": "CH1", "sample_rate": 256, "dimension": ""}]

      with self.assertRaises(ValueError):
        EDFExporter.export_unified_edf(out_path, signals, headers)

    def test_export_missing_fs_raises_error(self):
      """Verifica que el exportador falle si la frecuencia de muestreo es nula o inválida."""
      out_path = os.path.join(self.temp_dir.name, "fail_fs.edf")
      signals = [np.full(100, 1.0)]
      headers = [{"label": "CH1", "sample_rate": 0, "dimension": "mV"}]

      with self.assertRaises(ValueError):
        EDFExporter.export_unified_edf(out_path, signals, headers)


if __name__ == '__main__':
    unittest.main()