import numpy as np
from src.modules.sync_module import SyncModule

def test_offset_calculation():
    fs = 1000.0
    t = np.linspace(0, 2.0, int(fs*2), endpoint=False)
    sig_ref = np.sin(2 * np.pi * 5 * t)
    
    # Desplazar 100 muestras
    shift = 100
    sig_target = np.roll(sig_ref, shift)
    
    offset_samples, _ = SyncModule.calculate_offset(sig_ref, sig_target, fs)
    assert abs(offset_samples - shift) <= 2