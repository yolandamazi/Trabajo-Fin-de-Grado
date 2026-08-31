import numpy as np
from datetime import datetime
from scipy.signal import correlate, correlation_lags

class SyncModule:
    @staticmethod
    def calculate_offset(signal_ref: np.ndarray, signal_target: np.ndarray, fs: float) -> tuple[int, float]:
        """
        Calcula el desfase (offset) entre dos señales usando correlación cruzada.
        Devuelve (offset_muestras, offset_segundos).
        """
        norm_ref = (signal_ref - np.mean(signal_ref)) / (np.std(signal_ref) + 1e-8)
        norm_target = (signal_target - np.mean(signal_target)) / (np.std(signal_target) + 1e-8)

        corr = correlate(norm_ref, norm_target, mode='full')
        lags = correlation_lags(len(norm_ref), len(norm_target), mode='full')
        
        best_lag = lags[np.argmax(corr)]
        offset_seconds = float(best_lag) / fs
        
        return int(best_lag), offset_seconds

    @staticmethod
    def align_signals(signal: np.ndarray, offset_samples: int) -> np.ndarray:
        """Alinea la señal aplicando desplazamiento mediante pad o recorte."""
        if offset_samples > 0:
            return np.pad(signal, (offset_samples, 0), mode='constant')[:len(signal)]
        elif offset_samples < 0:
            abs_off = abs(offset_samples)
            shifted = signal[abs_off:]
            return np.pad(shifted, (0, abs_off), mode='constant')
        return signal

    @staticmethod
    def calculate_time_offset(ecg_start: datetime, emg_start: datetime) -> float:
        """Calcula el desfase inicial en segundos a partir de las marcas de tiempo."""
        if ecg_start and emg_start:
            return (emg_start - ecg_start).total_seconds()
        return 0.0

    @staticmethod
    def adjust_annotations(annotations: list, offset_seconds: float) -> list:
        """
        Ajusta la posición temporal de los eventos (t0, t1, t2...) 
        recalculando sus 'onsets' en función del desfase aplicado.
        """
        adjusted = []
        if not annotations:
            return adjusted

        for ann in annotations:
            new_onset = ann['onset'] - offset_seconds
            if new_onset >= 0:
                adjusted.append({
                    'onset': new_onset,
                    'duration': ann.get('duration', 0.0),
                    'description': ann.get('description', '')
                })
        return adjusted