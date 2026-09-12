import numpy as np
import pyedflib

class ECGProcessor:
  def __init__(self):
    pass

  def read_edf_all_channels(self, file_path: str):
    """Lee todas las señales del EDF exigiendo metadatos estrictos sin valores por defecto ni comodines."""
    f = pyedflib.EdfReader(file_path)
    n_channels = f.signals_in_file
    if n_channels <= 0:
      f.close()
      raise ValueError(
          'El archivo EDF no contiene ningún canal de señal válido.'
      )

    signals = []
    headers = []

    for i in range(n_channels):
      sig = np.array(f.readSignal(i), dtype=np.float64)

      unit = f.getPhysicalDimension(i).strip()
      if not unit:
        f.close()
        raise ValueError(
            f'El canal EDF {i+1} ("{f.getLabel(i).strip()}") no especifica'
            ' ninguna dimensión o unidad física en su cabecera.'
        )

      fs_val = f.getSampleFrequency(i)
      if fs_val is None or fs_val <= 0:
        f.close()
        raise ValueError(
            f'El canal EDF {i+1} ("{f.getLabel(i).strip()}") no especifica'
            ' una frecuencia de muestreo válida.'
        )

      signals.append(sig)
      headers.append({
          'label': f.getLabel(i).strip(),
          'dimension': unit,
          'sample_frequency': float(fs_val),
          'sample_rate': float(fs_val),
      })

    global_fs = f.getSampleFrequency(0)
    if global_fs is None or global_fs <= 0:
      f.close()
      raise ValueError(
          'No se pudo determinar una frecuencia de muestreo global válida en el'
          ' archivo EDF.'
      )

    meta = {
        'fs': float(global_fs),
        'headers': headers,
        'labels': [h['label'] for h in headers],
        'startdate': f.getStartdatetime(),
    }

    annotations = []
    try:
      raw_ann = f.readAnnotations()
      if raw_ann and len(raw_ann[0]) > 0:
        annotations = list(zip(raw_ann[0], raw_ann[1], raw_ann[2]))
    except Exception:
      annotations = []

    f.close()
    return signals, meta, annotations