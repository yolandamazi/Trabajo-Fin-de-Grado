import numpy as np

class SyncModule:

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

  @staticmethod
  def align_emg_to_annotation_one(
      raw_emg: np.ndarray,
      emg_fs: float,
      annotations: list,
      ecg_signal: np.ndarray,
      ecg_fs: float,
  ) -> np.ndarray:
    """Calcula el anclaje de las señales EMG basándose de forma estricta en la anotación '1'."""
    t1_onset = 0.0
    for ann in annotations:
      label = str(
          ann.get('label', '')
          if isinstance(ann, dict)
          else (ann[2] if len(ann) > 2 else '')
      ).strip()
      if label == '1':
        t1_onset = float(
            ann.get('onset', 0.0) if isinstance(ann, dict) else ann[0]
        )
        break

    ecg_dur_sec = len(ecg_signal) / float(ecg_fs)
    target_samples = int(np.ceil(ecg_dur_sec)) * int(np.round(emg_fs))

    pad_start = int(np.round(t1_onset * emg_fs))
    padded_signals = []

    for sig in raw_emg:
      pad_end = max(0, target_samples - (pad_start + len(sig)))
      padded = np.pad(
          sig, (pad_start, pad_end), mode='constant', constant_values=0.0
      )[:target_samples]
      padded_signals.append(padded)

    return np.array(padded_signals)