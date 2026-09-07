import pandas as pd
import numpy as np
import re

class EMGProcessor:
    def __init__(self):
        self.fs = 1000.0
        self.start_time = None
        self.channel_names = []
        self.units = []

    def read_file(self, file_path: str):
        """Lee el CSV/TXT manteniendo los datos en su escala original"""
        try:
            df = pd.read_csv(file_path, sep=None, engine='python')
        except Exception:
            df = pd.read_csv(file_path, sep=',')

        first_col_name = str(df.columns[0]).strip().lower()

        # Calcular la Fs real
        is_time_col = any(keyword in first_col_name for keyword in ['x [s]', 'time', 'tiempo', 'x', 't'])

        if is_time_col:
            time_vector = df.iloc[:, 0].values
            if len(time_vector) > 1:
                dt = np.mean(np.diff(time_vector))
                if dt > 0:
                    self.fs = float(1.0 / dt)

            emg_signals = df.iloc[:, 1:].values.T
            raw_channel_names = [str(col).strip() for col in df.columns[1:]]
        else:
            emg_signals = df.values.T
            raw_channel_names = [str(col).strip() for col in df.columns]

        self.channel_names = raw_channel_names

        headers = []
        self.units = []

        for name in raw_channel_names:
            unit = 'uV'  # Unidad de respaldo por defecto
            
            # Buscar patrones como [V], (mV), [uV], [µV] en el texto de la columna
            match = re.search(r'[\(\[](uV|µV|mV|V)[\)\]]', name, re.IGNORECASE)
            if match:
                detected = match.group(1).replace('µ', 'u')
                if detected.lower() == 'v':
                    unit = 'V'
                elif detected.lower() == 'mv':
                    unit = 'mV'
                elif detected.lower() == 'uv':
                    unit = 'uV'

            self.units.append(unit)
            headers.append({'label': name, 'dimension': unit})

        meta = {
            'fs': self.fs,
            'start_time': self.start_time,
            'units': self.units,
            'headers': headers
        }

        return emg_signals, meta

    def filter_signal_multichannel(self, signals: np.ndarray) -> np.ndarray:
        return signals