import pandas as pd
import numpy as np
import os

class EMGProcessor:
    def __init__(self):
        self.fs = 1000.0
        self.start_time = None
        self.channel_names = []

    def parse_hpf_metadata(self, hpf_path: str):
        """Lee el archivo .hpf gemelo para extraer la hora de inicio y los nombres de los músculos."""
        if not os.path.exists(hpf_path):
            return

        try:
            with open(hpf_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            names = []
            for line in lines:
                line_str = line.strip()
                if 'start' in line_str.lower() or 'time' in line_str.lower():
                    parts = line_str.split('=')
                    if len(parts) > 1:
                        self.start_time = parts[1].strip()
                if line_str.startswith('Channel') or line_str.startswith('Sensor'):
                    parts = line_str.split(':')
                    if len(parts) > 1:
                        names.append(parts[1].strip())

            if names:
                self.channel_names = names
        except Exception as e:
            print(f"Aviso al leer HPF: {e}")

    def read_file(self, file_path: str):
        """Lee el CSV/TXT estandarizando la señal de EMG a microvoltios (uV)."""
        try:
            df = pd.read_csv(file_path, sep=None, engine='python')
        except Exception:
            df = pd.read_csv(file_path, sep=',')

        first_col_name = str(df.columns[0]).strip().lower()

        # Descartar columna de tiempo si existe
        is_time_col = any(keyword in first_col_name for keyword in ['x [s]', 'time', 'tiempo', 'x', 't'])

        if is_time_col:
            time_vector = df.iloc[:, 0].values
            if len(time_vector) > 1:
                dt = np.mean(np.diff(time_vector))
                if dt > 0:
                    self.fs = float(1.0 / dt)

            emg_signals = df.iloc[:, 1:].values.T
            csv_channel_names = [str(col).strip() for col in df.columns[1:]]
        else:
            emg_signals = df.values.T
            csv_channel_names = [str(col).strip() for col in df.columns]

        # Convertir a uV si los datos del CSV están en V o mV (valores promedio < 1.0)
        max_val = np.max(np.abs(emg_signals)) if emg_signals.size > 0 else 0
        if max_val < 0.01:  # Están en Voltios
            emg_signals = emg_signals * 1e6
        elif max_val < 10.0:  # Están en MiliVoltios
            emg_signals = emg_signals * 1000.0

        if not self.channel_names or len(self.channel_names) != emg_signals.shape[0]:
            self.channel_names = csv_channel_names

        meta = {
            'fs': self.fs,
            'start_time': self.start_time,
            'headers': [{'label': name, 'dimension': 'uV'} for name in self.channel_names]
        }

        return emg_signals, meta

    def filter_signal_multichannel(self, signals: np.ndarray) -> np.ndarray:
        return signals