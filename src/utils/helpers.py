import logging
import os
from datetime import datetime

def setup_logger(name: str = "TFG_App") -> logging.Logger:
    """Configura el logger del sistema."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(name)s: %(message)s')
        
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)
    return logger

def ensure_directories_exist(base_path: str = ".") -> None:
    """Asegura la presencia de carpetas data/raw y data/output."""
    dirs = [
        os.path.join(base_path, "data", "raw"),
        os.path.join(base_path, "data", "output")
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)

def samples_to_timestamp(samples: int, fs: float) -> str:
    """Convierte número de muestras a formato MM:SS.mmm."""
    seconds = samples / fs
    minutes = int(seconds // 60)
    rem_seconds = seconds % 60
    return f"{minutes:02d}:{rem_seconds:06.3f}"