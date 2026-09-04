import numpy as np
from datetime import datetime
from scipy.signal import correlate, correlation_lags

class SyncModule:
    @staticmethod
    def calculate_time_offset(ecg_start: datetime, emg_start: datetime, ecg_duration: float = 0.0) -> float:
        """
        Calcula el desfase temporal por cabecera (timestamps).
        Devuelve el desfase SOLO si cae dentro del rango temporal del registro ECG.
        Si supera la duración del ECG o faltan cabeceras, devuelve 0.0.
        """
        if not ecg_start or not emg_start:
            return 0.0

        delta = (emg_start - ecg_start).total_seconds()

        # Si no se indica duración, se puede usar un valor por defecto
        max_allowed_offset = ecg_duration if ecg_duration > 0 else 300.0

        # Validar si el desfase cae dentro del tiempo de la prueba
        if abs(delta) < max_allowed_offset:
            return delta

        # Si el desfase es mayor que la duración del ECG, las horas de los equipos no estaban coordinadas
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