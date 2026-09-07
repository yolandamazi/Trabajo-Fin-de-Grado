import os
import tempfile
import unittest
import numpy as np
import pandas as pd
from src.modules.emg_module import EMGProcessor


class TestEMGProcessor(unittest.TestCase):

    def setUp(self):
        # Corrección: EMGProcessor.__init__() ya no toma el parámetro 'fs'
        self.processor = EMGProcessor()
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_load_emg_from_csv(self):
        """Verifica la carga de EMG desde CSV, extracción de Fs real, detección de unidades y preservación de escala."""
        csv_path = os.path.join(self.temp_dir.name, "test_emg.csv")

        # Generar CSV sintético con vector de tiempo y 2 canales con unidades distintas en la cabecera
        df = pd.DataFrame({
            'Time [s]': np.linspace(0, 1, 1000),
            'EMG_Biceps [V]': np.sin(np.linspace(0, 10, 1000)),
            'EMG_Triceps [mV]': np.cos(np.linspace(0, 10, 1000))
        })
        df.to_csv(csv_path, index=False)

        # Cargar archivo con read_file
        signals, meta = self.processor.read_file(csv_path)

        # 1. Validar tipos de datos y dimensiones (2 canales x 1000 muestras)
        self.assertIsInstance(signals, np.ndarray)
        self.assertIsInstance(meta, dict)
        self.assertEqual(signals.shape, (2, 1000))

        # 2. Validar cálculo automático de Fs a partir del delta de tiempo (~1000 Hz)
        self.assertAlmostEqual(meta['fs'], 1000.0, delta=1.0)

        # 3. Validar detección automática de unidades (V y mV) por expresiones regulares
        self.assertEqual(meta['units'], ['V', 'mV'])
        self.assertEqual(meta['headers'][0]['dimension'], 'V')
        self.assertEqual(meta['headers'][1]['dimension'], 'mV')

        # 4. Validar que la amplitud de la señal no ha sido escalada/multiplicada artificialmente
        self.assertAlmostEqual(signals[0][0], df['EMG_Biceps [V]'].iloc[0], places=5)
        self.assertAlmostEqual(signals[1][0], df['EMG_Triceps [mV]'].iloc[0], places=5)

    def test_empty_or_invalid_file(self):
        """Comprueba el comportamiento defensivo ante archivos con datos no numéricos o corruptos."""
        invalid_path = os.path.join(self.temp_dir.name, "corrupt.csv")
        with open(invalid_path, 'w', encoding='utf-8') as f:
            f.write("header1,header2\ntexto1,texto2\n")

        # Forzar la conversión a numérico para validar que falla de forma controlada ante datos corruptos
        with self.assertRaises((ValueError, TypeError)):
            signals, _ = self.processor.read_file(invalid_path)
            signals.astype(np.float64)


if __name__ == '__main__':
    unittest.main()