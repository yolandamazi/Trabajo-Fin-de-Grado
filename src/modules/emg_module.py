import os
import re
import numpy as np
import pandas as pd

class EMGProcessor:
  def __init__(self):
    self.fs = None
    self.start_time = None
    self.channel_names = []
    self.units = []

  def extract_hpf_metadata(self, hpf_path: str) -> dict:
    """Extrae la frecuencia exacta, hora de inicio y canales del HPF cuando se importa."""
    if not os.path.exists(hpf_path):
      raise FileNotFoundError(f'No se encuentra el archivo HPF: {hpf_path}')

    meta = {
        'fs': None,
        'start_time': None,
        'channel_names': [],
        'units': [],
        'headers': [],
    }

    with open(hpf_path, 'r', encoding='latin-1', errors='ignore') as f:
      content = f.read(100000)

    start_match = re.search(r'<StartTime>(.*?)</StartTime>', content) or re.search(
        r'<RecordingDate>(.*?)</RecordingDate>', content
    )

    if start_match:
      meta['start_time'] = start_match.group(1).strip()
      self.start_time = meta['start_time']
    else:
      raise ValueError(
          'El archivo HPF no especifica <StartTime> o <RecordingDate> de forma'
          ' válida.'
      )

    fs_match = re.search(
        r'<PerChannelSampleRate>(.*?)</PerChannelSampleRate>', content
    )
    if fs_match:
      fs_val = float(fs_match.group(1).strip())
      if fs_val <= 0:
        raise ValueError(
            'La frecuencia de muestreo en el HPF no es válida (<= 0).'
        )
      meta['fs'] = fs_val
      self.fs = fs_val
    else:
      raise ValueError(
          'El archivo HPF no especifica <PerChannelSampleRate> de forma válida.'
      )

    channel_blocks = re.findall(
        r'<ChannelInformation>(.*?)</ChannelInformation>', content, re.DOTALL
    )
    if not channel_blocks:
      raise ValueError('El archivo HPF no contiene bloques <ChannelInformation>.')

    for i, block in enumerate(channel_blocks):
      name_match = re.search(r'<Name>(.*?)</Name>', block)
      unit_match = re.search(r'<Unit>(.*?)</Unit>', block)

      if not name_match:
        raise ValueError(
            f'El canal EMG {i+1} en el HPF no especifica un <Name> válido.'
        )
      name = name_match.group(1).strip()

      if not unit_match or not unit_match.group(1).strip():
        raise ValueError(
            f'El canal EMG {i+1} ("{name}") en el HPF no especifica ninguna'
            ' <Unit> o dimensión.'
        )
      unit = unit_match.group(1).strip()

      meta['channel_names'].append(name)
      meta['units'].append(unit)
      meta['headers'].append({'label': name, 'dimension': unit})

    self.channel_names = meta['channel_names']
    self.units = meta['units']

    return meta

  def read_file(self, file_path: str):
    """Lee el archivo CSV de EMG de forma independiente (el HPF se cargará después mediante su botón específico)."""
    hpf_candidate = (
        file_path
        if file_path.lower().endswith('.hpf')
        else os.path.splitext(file_path)[0] + '.hpf'
    )

    hpf_meta = {}
    if os.path.exists(hpf_candidate):
      try:
        hpf_meta = self.extract_hpf_metadata(hpf_candidate)
      except Exception:
        pass

    try:
      df = pd.read_csv(file_path, sep=None, engine='python')
    except Exception:
      df = pd.read_csv(file_path, sep=',')

    if df.empty:
      raise ValueError('El archivo CSV de EMG está vacío.')

    first_col_name = str(df.columns[0]).strip().lower()
    is_time_col = any(
        keyword in first_col_name
        for keyword in ['x [s]', 'time', 'tiempo', 'x', 't']
    )

    if is_time_col:
      time_vector = df.iloc[:, 0].values
      if len(time_vector) > 1:
        dt = np.mean(np.diff(time_vector))
        if dt > 0 and self.fs is None:
          self.fs = float(1.0 / dt)
      emg_signals = df.iloc[:, 1:].values.T
      raw_channel_names = [str(col).strip() for col in df.columns[1:]]
    else:
      emg_signals = df.values.T
      raw_channel_names = [str(col).strip() for col in df.columns]

    if emg_signals.size == 0:
      raise ValueError('No se han encontrado señales EMG válidas en el CSV.')

    headers = hpf_meta.get('headers', [])
    if not headers:
      headers = [{'label': name, 'dimension': ''} for name in raw_channel_names]

    meta = {
        'fs': self.fs,
        'start_time': hpf_meta.get('start_time'),
        'units': [h.get('dimension', '') for h in headers],
        'headers': headers,
    }

    return emg_signals, meta

  def filter_signal_multichannel(self, signals: np.ndarray) -> np.ndarray:
    return signals