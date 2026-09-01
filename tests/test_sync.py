from datetime import datetime, timedelta
from src.modules.sync_module import SyncModule

def test_offset_calculation():
    # 1. Caso de prueba: Desfase menor a 5 minutos (Aceptado por cabecera)
    ecg_start = datetime(2026, 5, 10, 10, 0, 0)
    emg_start = datetime(2026, 5, 10, 10, 0, 15)  # 15 segundos después

    offset = SyncModule.calculate_time_offset(ecg_start, emg_start)
    assert offset == 15.0

def test_offset_unreliable_clocks():
    # 2. Caso de prueba: Desfase mayor a 5 minutos (Relojes desalineados -> Devuelve 0.0)
    ecg_start = datetime(2026, 5, 10, 10, 0, 0)
    emg_start = datetime(2026, 5, 10, 12, 33, 0)  # ~2,5 horas después

    offset = SyncModule.calculate_time_offset(ecg_start, emg_start)
    assert offset == 0.0  # El sistema identifica que las cabeceras no son fiables