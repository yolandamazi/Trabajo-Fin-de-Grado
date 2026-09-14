from pathlib import Path

def ensure_directories_exist():
    """Crea los directorios esenciales del proyecto si no existen."""
    directories = [
        Path("data/raw"),
        Path("data/output")
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

