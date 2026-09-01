import pyedflib
import numpy as np
from scipy.signal import find_peaks

class ECGProcessor:
    def __init__(self):
        pass

    def read_edf(self, file_path: str, channel_index: int = 0) -> tuple[np.ndarray, dict]:
        """
        Lee señal ECG de un archivo EDF.
        Devuelve (señal, metadatos_canal).
        """
        f = pyedflib.EdfReader(file_path)
        signal = f.readSignal(channel_index)
        header = f.getSignalHeader(channel_index)
        
        # Obtención segura de la frecuencia de muestreo directamente desde pyedflib
        fs = f.getSampleFrequency(channel_index)
        
        meta = {
            'label': header.get('label', f'Channel_{channel_index}'),
            'fs': float(fs),
            'dimension': header.get('dimension', 'uV'),
            'startdate': f.getStartdatetime()
        }
        f.close()
        return signal, meta

    def detect_r_peaks(self, signal: np.ndarray, fs: float, distance_ms: float = 600.0) -> np.ndarray:
        """Detección básica de picos R basándose en umbral y distancia mínima."""
        distance_samples = int((distance_ms / 1000.0) * fs)
        threshold = np.mean(signal) + 2.0 * np.std(signal)
        peaks, _ = find_peaks(signal, height=threshold, distance=distance_samples)
        return peaks

    def read_edf_with_annotations(self, file_path: str, channel_index: int = 0) -> tuple[np.ndarray, dict, list]:
        """
        Lee la señal ECG y extrae los metadatos y las anotaciones/marcas de eventos.
        Devuelve (señal, metadatos, lista_de_anotaciones).
        """
        f = pyedflib.EdfReader(file_path)
        
        # Leer señal y metadatos del canal seleccionado
        signal = f.readSignal(channel_index)
        header = f.getSignalHeader(channel_index)
        fs = f.getSampleFrequency(channel_index)
        
        meta = {
            'label': header.get('label', 'ECG'),
            'fs': float(fs),
            'dimension': header.get('dimension', 'mV'),
            'startdate': f.getStartdatetime()
        }

        # Extraer marcas/anotaciones de tiempo
        annotations = []
        try:
            raw_ann = f.readAnnotations()
            for onset, duration, desc in zip(raw_ann[0], raw_ann[1], raw_ann[2]):
                annotations.append({
                    'onset': float(onset),
                    'duration': float(duration) if duration else 0.0,
                    'description': str(desc)
                })
        except Exception:
            pass

        f.close()
        return signal, meta, annotations

    def read_file(self, file_path: str):
        """Alias para mantener compatibilidad."""
        return self.read_edf_with_annotations(file_path)

    def read_edf_all_channels(self, file_path: str):
        """Lee todos los canales, sus etiquetas y las anotaciones de un archivo EDF+."""
        f = pyedflib.EdfReader(file_path)
        n_channels = f.signals_in_file
        
        signals = []
        labels = []
        for i in range(n_channels):
            signals.append(f.readSignal(i))
            labels.append(f.getSignalHeader(i).get('label', f'Ch_{i}'))
        
        meta = {
            'label': labels[0] if labels else 'ECG',
            'fs': float(f.getSampleFrequency(0)),
            'startdate': f.getStartdatetime(),
            'labels': labels
        }

        annotations = []
        try:
            raw_ann = f.readAnnotations()
            for onset, duration, desc in zip(raw_ann[0], raw_ann[1], raw_ann[2]):
                annotations.append({
                    'onset': float(onset),
                    'duration': float(duration) if duration else 0.0,
                    'description': str(desc)
                })
        except Exception:
            pass

        f.close()
        return signals, meta, annotations