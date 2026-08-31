import logging
import os

class Logger:
    _instancia = None  # Almacena la única instancia de la clase

    def __new__(cls, *args, **kwargs):
        """Garantiza que solo exista una instancia del Logger en toda la app."""
        if not cls._instancia:
            cls._instancia = super(Logger, cls).__new__(cls)
            cls._instancia._configurar_logger()
        return cls._instancia

    def _configurar_logger(self):
        """Configuración interna del archivo de texto y formato."""
        self.ruta_log = 'logger_TFG_Proyecto.txt'
        self.logger = logging.getLogger("TFG_Proyecto")
        self.logger.setLevel(logging.INFO)

        # Si ya tiene handlers, no los duplicamos
        if not self.logger.handlers:
            formato = logging.Formatter(
                fmt='%(asctime)s - [%(levelname)s] - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )

            # Escritura en el archivo .txt
            file_handler = logging.FileHandler(self.ruta_log, encoding='utf-8')
            file_handler.setFormatter(formato)
            self.logger.addHandler(file_handler)

            # Muestra también en la consola de VS Code
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formato)
            self.logger.addHandler(console_handler)

    def info(self, mensaje):
        """Registra un evento informativo."""
        self.logger.info(mensaje)

    def error(self, mensaje):
        """Registra un fallo o excepción."""
        self.logger.error(mensaje)

    def advertencia(self, mensaje):
        """Registra una alerta o comportamiento inesperado."""
        self.logger.warning(mensaje)