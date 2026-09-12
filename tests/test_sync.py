import copy
import unittest
import numpy as np
from src.modules.sync_module import SyncModule


class TestSyncModule(unittest.TestCase):

    def test_adjust_annotations_positive_offset_dict(self):
        """Verifica que un offset positivo desplace las marcas en formato diccionario (onset - offset)."""
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

    def test_adjust_annotations_tuple_format(self):
        """Verifica que acepte y procese anotaciones en formato tupla (onset, duration, description)."""
        annotations = [
            (10.0, 0.0, 't0'),
            (25.5, 1.0, 't1')
        ]
        offset_sec = 2.5

        adjusted = SyncModule.adjust_annotations(annotations, offset_sec)

        self.assertEqual(len(adjusted), 2)
        
        # Evaluar según el tipo devuelto (diccionario o tupla)
        onset_0 = adjusted[0]['onset'] if isinstance(adjusted[0], dict) else adjusted[0][0]
        onset_1 = adjusted[1]['onset'] if isinstance(adjusted[1], dict) else adjusted[1][0]
        
        self.assertAlmostEqual(float(onset_0), 7.5, places=2)
        self.assertAlmostEqual(float(onset_1), 23.0, places=2)

    def test_adjust_annotations_immutability(self):
        """Asegura que la función no modifique la lista o diccionarios de entrada originales."""
        original = [
            {'onset': 10.0, 'duration': 0.0, 'description': 't0'}
        ]
        backup = copy.deepcopy(original)

        _ = SyncModule.adjust_annotations(original, 5.0)

        # Comprobar que la lista original permanece intacta
        self.assertEqual(original[0]['onset'], backup[0]['onset'])

    def test_adjust_annotations_zero_offset(self):
        """Comprueba que con offset = 0.0 las marcas se mantengan idénticas."""
        annotations = [{'onset': 15.0, 'duration': 0.5, 'description': 't0'}]
        adjusted = SyncModule.adjust_annotations(annotations, 0.0)

        onset_val = adjusted[0]['onset'] if isinstance(adjusted[0], dict) else adjusted[0][0]
        self.assertAlmostEqual(float(onset_val), 15.0, places=2)

    def test_align_emg_to_annotation_one(self):
      """Verifica que la alineación automática de EMG anclada a la anotación '1' funcione correctamente."""
      raw_emg = np.array([[1.0, 2.0, 3.0, 4.0, 5.0]])
      emg_fs = 100.0
      annotations = [{'onset': 0.02, 'duration': 0.0, 'label': '1'}]
      
      # 1.0 segundo a 1000 Hz de referencia (ceil(1.0) * 100 Hz = 100 muestras)
      ecg_signal = np.zeros(1000)  
      ecg_fs = 1000.0

      aligned = SyncModule.align_emg_to_annotation_one(
          raw_emg, emg_fs, annotations, ecg_signal, ecg_fs
      )

      self.assertIsInstance(aligned, np.ndarray)
      self.assertEqual(aligned.shape[0], 1)
      self.assertEqual(aligned.shape[1], 100)
      self.assertAlmostEqual(aligned[0, 2], 1.0)

if __name__ == '__main__':
    unittest.main()