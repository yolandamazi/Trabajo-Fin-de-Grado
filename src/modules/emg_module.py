import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime
import numpy as np
import pandas as pd
from scipy.signal import butter, filtfilt, iirnotch

class EMGProcessor:
    def __init__(self, fs: float = 1000.0):
        self.fs = fs
        self.channel_names = []
        self.start_time = None

    def read_file(self, file_path: str):
        """
        Detecta la extensión y procesa .hpf (metadatos) o .csv (señales).
        """
        ext = os.path.splitext(file_path)[1].lower()

        if ext == '.hpf':
            # Extrae metadatos XML del HPF
            meta = self.parse_hpf_metadata(file_path)
            
            # Si existe un CSV con el mismo nombre en la misma carpeta, lo carga
            csv_path = os.path.splitext(file_path)[0] + '.csv'
            if os.path.exists(csv_path):
                signals = self.read_emg_csv(csv_path)
            else:
                signals = np.array([])  # Solo metadatos
                
            return signals, meta
        else:
            # Procesa directamente como datos numéricos CSV/TXT
            signals = self.read_emg_csv(file_path)
            meta = {
                'fs': self.fs,
                'channels': self.channel_names,
                'start_time': self.start_time
            }
            return signals, meta

    def parse_hpf_metadata(self, hpf_path: str) -> dict:
        """Extrae metadatos del bloque XML embebido en el archivo .hpf."""
        with open(hpf_path, 'r', encoding='latin-1', errors='ignore') as f:
            content = f.read()

        metadata = {'channels': [], 'fs': 1000.0, 'start_time': None}

        # Extraer fecha/hora de inicio
        date_match = re.search(r'<RecordingDate>(.*?)</RecordingDate>', content)
        if date_match:
            date_str = date_match.group(1).strip()
            try:
                # Formato: 2025/07/31 12:42:16.2338410
                metadata['start_time'] = datetime.strptime(date_str[:26], '%Y/%m/%d %H:%M:%S.%f')
            except ValueError:
                pass

        # Extraer canales y frecuencias de muestreo
        channels_xml = re.findall(r'<ChannelInformation>(.*?)</ChannelInformation>', content, re.DOTALL)
        for ch_xml in channels_xml:
            try:
                root = ET.fromstring(f"<ChannelInformation>{ch_xml}</ChannelInformation>")
                name = root.find('Name').text if root.find('Name') is not None else 'EMG'
                fs_elem = root.find('PerChannelSampleRate')
                fs = float(fs_elem.text) if fs_elem is not None else 1000.0
                
                metadata['channels'].append(name)
                metadata['fs'] = fs  # Se asume misma Fs para los canales
            except Exception:
                continue

        self.channel_names = metadata['channels']
        self.fs = metadata['fs']
        self.start_time = metadata['start_time']
        return metadata

    def read_emg_csv(self, csv_path: str) -> np.ndarray:
        """
        Lee la matriz multicanal del archivo .csv.
        Devuelve un array 2D de forma (num_canales, num_muestras).
        """
        encodings = ['utf-8', 'latin-1', 'cp1252']
        separators = [',', ';', '\t', r'\s+']

        df = None
        for enc in encodings:
            for sep in separators:
                try:
                    df = pd.read_csv(csv_path, sep=sep, comment='#', encoding=enc, engine='python')
                    # Filtrar columnas numéricas
                    numeric_cols = [c for c in df.columns if pd.to_numeric(df[c], errors='coerce').notna().sum() > len(df) * 0.5]
                    if len(numeric_cols) > 0:
                        df = df[numeric_cols].apply(pd.to_numeric, errors='coerce').dropna()
                        break
                except Exception:
                    continue
            if df is not None and not df.empty:
                break

        if df is None or df.empty:
            raise ValueError("No se pudieron leer columnas numéricas válidas del CSV de EMG.")

        # Retornar en forma (canales, muestras)
        return df.to_numpy().T

    def filter_signal_multichannel(self, signals: np.ndarray) -> np.ndarray:
        """Aplica filtros pasabanda y Notch a cada canal muscular."""
        filtered = np.zeros_like(signals)
        nyq = 0.5 * self.fs
        
        # Filtro Pasabanda 20-450 Hz
        b_band, a_band = butter(4, [20.0 / nyq, min(450.0 / nyq, 0.99)], btype='band')
        # Filtro Notch 50 Hz
        b_notch, a_notch = iirnotch(50.0, 30.0, fs=self.fs)

        for i in range(signals.shape[0]):
            sig = filtfilt(b_notch, a_notch, signals[i])
            filtered[i] = filtfilt(b_band, a_band, sig)
            
        return filtered