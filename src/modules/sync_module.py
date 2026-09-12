import numpy as np
from datetime import datetime, timezone

class SyncModule:
    @staticmethod
    def calculate_time_offset(ecg_start: datetime, emg_start: datetime, ecg_duration: float = 0.0) -> float:
        """ Calcula el desfase temporal entre timestamps normalizando zonas horarias"""
        if not ecg_start or not emg_start:
            return 0.0

        try:
            if ecg_start.tzinfo is None and emg_start.tzinfo is None:
                t_ecg = ecg_start
                t_emg = emg_start
            else:
                t_ecg = ecg_start.astimezone(timezone.utc) if ecg_start.tzinfo else ecg_start.replace(tzinfo=timezone.utc)
                t_emg = emg_start.astimezone(timezone.utc) if emg_start.tzinfo else emg_start.replace(tzinfo=timezone.utc)

            delta = (t_emg - t_ecg).total_seconds()

        except Exception as e:
            print(f"Aviso al comparar timestamps: {e}")
            return 0.0

        max_allowed_offset = ecg_duration if ecg_duration > 0 else 300.0

        if abs(delta) < max_allowed_offset:
            return delta

        return 0.0

    @staticmethod
    def adjust_annotations(annotations: list, offset_seconds: float) -> list:
        """Ajusta la posición temporal de las anotaciones."""
        adjusted = []
        if not annotations:
            return adjusted

        for ann in annotations:
            if isinstance(ann, dict):
                new_ann = dict(ann)
                new_ann['onset'] = float(ann.get('onset', 0.0)) - offset_seconds
                adjusted.append(new_ann)
            elif isinstance(ann, (list, tuple)):
                new_onset = float(ann[0]) - offset_seconds
                adjusted.append((new_onset, *ann[1:]))

        return adjusted