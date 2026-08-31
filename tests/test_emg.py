import numpy as np
from src.modules.emg_module import EMGProcessor

def test_emg_filtering():
    fs = 1000.0
    processor = EMGProcessor(fs=fs)
    t = np.linspace(0, 1.0, int(fs), endpoint=False)
    # Señal sintética con ruido a 50Hz
    signal = np.sin(2 * np.pi * 100 * t) + 0.5 * np.sin(2 * np.pi * 50 * t)
    
    filtered = processor.apply_notch_filter(signal)
    assert len(filtered) == len(signal)
    assert not np.isnan(filtered).any()