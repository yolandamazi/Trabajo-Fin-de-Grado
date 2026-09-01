import numpy as np
from src.modules.emg_module import EMGProcessor

def test_emg_filtering():
    fs = 1000.0
    processor = EMGProcessor(fs=fs)
    t = np.linspace(0, 1.0, int(fs), endpoint=False)
    
    # Señal sintética con ruido (1 canal x 1000 muestras)
    signal = np.array([np.sin(2 * np.pi * 100 * t) + 0.5 * np.sin(2 * np.pi * 50 * t)])

    # Aplicar el filtrado multicanal real del procesador
    filtered = processor.filter_signal_multichannel(signal)
    
    assert filtered is not None
    assert filtered.shape == signal.shape
    assert not np.isnan(filtered).any()