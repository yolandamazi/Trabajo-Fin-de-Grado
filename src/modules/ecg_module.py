import pyedflib
import numpy as np

class ECGProcessor:
    def __init__(self):
        pass

    def read_edf_all_channels(self, file_path: str):
        """Lee todas las señales del EDF convirtiendo automáticamente a uV para estandarizar."""
        f = pyedflib.EdfReader(file_path)
        n_channels = f.signals_in_file
        signals = []
        headers = []

        for i in range(n_channels):
            sig = np.array(f.readSignal(i), dtype=np.float64)
            unit = f.getPhysicalDimension(i).strip()
            
            # Convertir de mV a uV si corresponde
            if 'mv' in unit.lower():
                sig = sig * 1000.0
                unit = 'uV'
            elif 'v' in unit.lower() and 'uv' not in unit.lower():
                sig = sig * 1e6
                unit = 'uV'
            elif not unit:
                unit = 'uV'

            signals.append(sig)
            headers.append({
                'label': f.getLabel(i).strip(),
                'dimension': unit,
                'sample_frequency': f.getSampleFrequency(i)
            })

        meta = {
            'fs': f.getSampleFrequency(0) if n_channels > 0 else 1000.0,
            'headers': headers,
            'labels': [h['label'] for h in headers],
            'startdate': f.getStartdatetime()
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