import numpy as np
from datetime import datetime
from scipy.signal import correlate, correlation_lags

class SyncModule:
    @staticmethod
    def calculate_time_offset(ecg_start: datetime, emg_start: datetime) -> float:
        """
        Devuelve el desfase por timestamp SOLO si es razonable (< 5 minutos).
        Si supera los 5 minutos, devuelve 0.0 señalando que las cabeceras no son fiables.
        """
        if not ecg_start or not emg_start:
            return 0.0

        delta = (emg_start - ecg_start).total_seconds()

        # Si el desfase entre relojes es menor a 300 s (5 min), nos fiamos del timestamp
        if abs(delta) < 300:
            return delta

        # Si es mayor, los relojes no estaban sincronizados en origen
        return 0.0

    @staticmethod
    def adjust_annotations(annotations: list, offset_seconds: float) -> list:
        """
        Ajusta la posición temporal de las anotaciones clínicas.
        """
        adjusted = []
        if not annotations:
            return adjusted

        for ann in annotations:
            new_onset = ann['onset'] - offset_seconds
            adjusted.append({
                'onset': new_onset,
                'duration': ann.get('duration', 0.0),
                'description': ann.get('description', '')
            })
        return adjusted