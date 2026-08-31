import os
import numpy as np
import pyedflib
from src.modules.edf_converter import EDFExporter

def test_edf_export(tmp_path):
    output_file = os.path.join(tmp_path, "test_output.edf")
    signals = [np.random.randn(1000), np.random.randn(1000)]
    headers = [
        {'label': 'CH1', 'sample_rate': 1000, 'dimension': 'uV'},
        {'label': 'CH2', 'sample_rate': 1000, 'dimension': 'mV'}
    ]
    
    success = EDFExporter.export_unified_edf(output_file, signals, headers)
    assert success
    assert os.path.exists(output_file)