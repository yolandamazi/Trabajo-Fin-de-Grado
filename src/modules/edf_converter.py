from datetime import datetime
import numpy as np
import pyedflib

class EDFExporter:
    @staticmethod
    def export_unified_edf(output_path: str, signals: list, headers: list, 
                            annotations: list = None, start_date: datetime = None) -> bool:
        """
        Exporta ECG + canales EMG + Anotaciones a un único archivo EDF+.
        Ajusta escala y redondeo de rangos físicos para cumplir con el límite de 8 caracteres de EDF+.
        """
        n_channels = len(signals)
        writer = pyedflib.EdfWriter(output_path, n_channels, file_type=pyedflib.FILETYPE_EDFPLUS)
        
        if start_date:
            writer.setStartdatetime(start_date)

        channel_info = []
        processed_signals = []

        for i, h in enumerate(headers):
            sig = np.array(signals[i], dtype=np.float64)
            unit = h.get('dimension', 'uV')

            # Si el canal es EMG en uV pero los datos están en Voltios (< 0.1 V), escalar a uV (x 1,000,000)
            if unit == 'uV' and len(sig) > 0 and np.max(np.abs(sig)) < 0.1:
                sig = sig * 1e6

            processed_signals.append(sig)

            # Obtener mínimos y máximos físicos
            p_min = float(np.min(sig)) if len(sig) > 0 else -100.0
            p_max = float(np.max(sig)) if len(sig) > 0 else 100.0

            if p_min == p_max:
                p_min -= 1.0
                p_max += 1.0

            # Redondear para garantizar que la representación en string no exceda 8 caracteres
            p_min_rounded = float(f"{p_min:.4g}")
            p_max_rounded = float(f"{p_max:.4g}")

            # Asegurar pequeño margen si tras el redondeo quedaran iguales
            if p_min_rounded == p_max_rounded:
                p_min_rounded -= 0.01
                p_max_rounded += 0.01

            fs_val = h.get('sample_frequency') or h.get('sample_rate') or 1000

            info = {
                'label': h.get('label', f'Channel_{i}')[:16],
                'dimension': unit,
                'sample_frequency': int(fs_val),
                'physical_min': p_min_rounded,
                'physical_max': p_max_rounded,
                'digital_min': -32768,
                'digital_max': 32767,
                'transducer': '',
                'prefilter': ''
            }
            channel_info.append(info)

        writer.setSignalHeaders(channel_info)
        writer.writeSamples(processed_signals)

        # Escribir las marcas de eventos (t0, t1, t2...)
        if annotations:
            for ann in annotations:
                writer.writeAnnotation(ann['onset'], ann['duration'], ann['description'])

        writer.close()
        return True