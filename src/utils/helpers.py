import os
from datetime import datetime

def ensure_directories_exist(base_path: str = ".") -> None:
    """Asegura la presencia de carpetas data/raw y data/output."""
    dirs = [
        os.path.join(base_path, "data", "raw"),
        os.path.join(base_path, "data", "output")
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
