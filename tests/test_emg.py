import unittest
import numpy as np
import os
import tempfile
import pandas as pd
from src.modules.emg_module import EMGProcessor

class TestEMGProcessor(unittest.TestCase):

    def setUp(self):
        self.processor = EMGProcessor(fs=1000.0)
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_load_emg_from_csv(self):
        """Verifica la carga de señales EMG desde un fichero CSV usando read_file."""
        csv_path = os.path.join(self.temp_dir.name, "test_emg.csv")

        # Generar CSV sintético con tiempo y 2 canales
        df = pd.DataFrame({
            'Time': np.linspace(0, 1, 1000),
            'EMG_Biceps': np.sin(np.linspace(0, 10, 1000)),
            'EMG_Triceps': np.cos(np.linspace(0, 10, 1000))
        })
        df.to_csv(csv_path, index=False)

        # Usar el método real read_file
        signals, meta = self.processor.read_file(csv_path)

        # Validar tipo y dimensiones (shape: canales x muestras)
        self.assertIsInstance(signals, np.ndarray)
        self.assertIsInstance(meta, dict)
        self.assertGreater(signals.shape[0], 0)  # Al menos 1 canal numérico extraído
        self.assertEqual(signals.shape[1], 1000)  # 1000 muestras
        self.assertEqual(meta['fs'], 1000.0)

    def test_empty_or_invalid_file(self):
        """Comprueba que un CSV sin columnas numéricas lance ValueError."""
        invalid_path = os.path.join(self.temp_dir.name, "corrupt.csv")
        with open(invalid_path, 'w') as f:
            f.write("header1,header2\ntexto1,texto2\n")

        with self.assertRaises(ValueError):
            self.processor.read_file(invalid_path)

if __name__ == '__main__':
    unittest.main()