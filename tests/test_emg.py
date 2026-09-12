import os
import tempfile
import unittest
import numpy as np
import pandas as pd
from src.modules.emg_module import EMGProcessor


class TestEMGProcessor(unittest.TestCase):

    def setUp(self):
        self.processor = EMGProcessor()
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_load_emg_with_hpf_metadata(self):
        """Verifica la carga de EMG desde CSV junto con su archivo HPF asociado, validando Fs, unidades y metadatos estrictos."""
        base_path = os.path.join(self.temp_dir.name, "test_emg")
        csv_path = base_path + ".csv"
        hpf_path = base_path + ".hpf"

        # 1. Generar CSV sintético con vector de tiempo y 2 canales
        df = pd.DataFrame({
            'Time [s]': np.linspace(0, 1, 1000),
            'EMG_Biceps': np.sin(np.linspace(0, 10, 1000)),
            'EMG_Triceps': np.cos(np.linspace(0, 10, 1000))
        })
        df.to_csv(csv_path, index=False)

        # 2. Generar archivo HPF XML válido asociado (requisito estricto de metadatos)
        hpf_content = """<?xml version="1.0" encoding="utf-8"?>
        <Header>
            <StartTime>2026-06-06 12:00:00</StartTime>
            <PerChannelSampleRate>1000.0</PerChannelSampleRate>
            <ChannelInformation>
                <Name>EMG_Biceps</Name>
                <Unit>V</Unit>
            </ChannelInformation>
            <ChannelInformation>
                <Name>EMG_Triceps</Name>
                <Unit>mV</Unit>
            </ChannelInformation>
        </Header>
        """
        with open(hpf_path, 'w', encoding='utf-8') as f:
            f.write(hpf_content)

        # 3. Cargar archivo con read_file (vinculará automáticamente el HPF)
        signals, meta = self.processor.read_file(csv_path)

        # 4. Validar tipos de datos y dimensiones (2 canales x 1000 muestras)
        self.assertIsInstance(signals, np.ndarray)
        self.assertIsInstance(meta, dict)
        self.assertEqual(signals.shape, (2, 1000))

        # 5. Validar cálculo automático de Fs a partir del HPF (~1000 Hz)
        self.assertAlmostEqual(meta['fs'], 1000.0, delta=1.0)

        # 6. Validar unidades estrictas recuperadas del HPF (V y mV)
        self.assertEqual(meta['units'], ['V', 'mV'])
        self.assertEqual(meta['headers'][0]['dimension'], 'V')
        self.assertEqual(meta['headers'][1]['dimension'], 'mV')
        self.assertEqual(meta['start_time'], '2026-06-06 12:00:00')

        # 7. Validar integridad de amplitud
        self.assertAlmostEqual(signals[0][0], df['EMG_Biceps'].iloc[0], places=5)
        self.assertAlmostEqual(signals[1][0], df['EMG_Triceps'].iloc[0], places=5)

    def test_empty_or_invalid_file(self):
        """Comprueba el comportamiento defensivo ante archivos con datos no numéricos o corruptos."""
        invalid_path = os.path.join(self.temp_dir.name, "corrupt.csv")
        with open(invalid_path, 'w', encoding='utf-8') as f:
            f.write("header1,header2\ntexto1,texto2\n")

        with self.assertRaises((ValueError, TypeError)):
            signals, _ = self.processor.read_file(invalid_path)
            signals.astype(np.float64)


if __name__ == '__main__':
    unittest.main()