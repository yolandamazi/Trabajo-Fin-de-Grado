import os
import warnings
import pyedflib
import numpy as np

class EDFExporter:
    @staticmethod
    def export_unified_edf(output_path: str, 
                           signals: list, 
                           headers: list, 
                           annotations: list = None, 
                           start_date=None, 
                           **kwargs):
        """Exporta el archivo EDF+ completo usando writeSamples para escribir todos los bloques."""
        warnings.filterwarnings("ignore", category=UserWarning, module="pyedflib")

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        n_channels = len(signals)
        channel_info = []

        for i, h in enumerate(headers):
            sig = np.ascontiguousarray(signals[i], dtype=np.float64)
            if len(sig) > 0:
                raw_min = float(np.min(sig))
                raw_max = float(np.max(sig))
            else:
                raw_min, raw_max = -32768.0, 32767.0

            if raw_min == raw_max:
                raw_min -= 1.0
                raw_max += 1.0

            fs_val = int(h.get('sample_frequency') or h.get('sample_rate') or 1000)
            unit_val = str(h.get('dimension') or h.get('units') or 'uV')[:8]

            channel_info.append({
                'label': str(h.get('label', f'Ch_{i+1}'))[:16],
                'dimension': unit_val,
                'sample_frequency': fs_val,
                'physical_max': raw_max,
                'physical_min': raw_min,
                'digital_max': 32767,
                'digital_min': -32768,
                'transducer': '',
                'prefilter': ''
            })

        writer = pyedflib.EdfWriter(output_path, n_channels, file_type=pyedflib.FILETYPE_EDFPLUS)
        writer.setSignalHeaders(channel_info)

        if start_date:
            try:
                writer.setStartdatetime(start_date)
            except Exception:
                pass

        # CLAVE: Formatear los arrays y llamar a writeSamples para volcar la sesión completa
        formatted_signals = [np.ascontiguousarray(sig, dtype=np.float64) for sig in signals]
        writer.writeSamples(formatted_signals)

        # Escribir las anotaciones
        if annotations:
            for ann in annotations:
                try:
                    if isinstance(ann, dict):
                        onset = float(ann.get('onset', 0.0))
                        duration = float(ann.get('duration', -1.0))
                        desc = str(ann.get('description', '')).strip()
                    elif isinstance(ann, (list, tuple)):
                        onset = float(ann[0])
                        duration = float(ann[1]) if len(ann) >= 3 else -1.0
                        desc = str(ann[-1]).strip()
                    else:
                        continue

                    if desc:
                        writer.writeAnnotation(onset, duration, desc)
                except Exception as e:
                    print(f"Aviso escribiendo marca {ann}: {e}")

        writer.close()