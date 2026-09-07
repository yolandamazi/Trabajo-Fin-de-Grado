import numpy as np
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QTabWidget, QWidget
from PyQt5.QtCore import Qt

class MetadataDialog(QDialog):
    def __init__(self, parent=None, headers=None, annotations=None, duration_sec=0.0, file_info=""):
        super().__init__(parent)
        self.setWindowTitle("Inspección de Metadatos del Estudio")
        self.resize(750, 500)

        self.headers = headers or []
        self.annotations = annotations or []
        self.duration_sec = duration_sec
        self.file_info = file_info

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Tab Widget para organizar la info
        tabs = QTabWidget()
        
        # Pestaña 1: Canales
        tabs.addTab(self._create_channels_tab(), "Canales y Frecuencias")
        # Pestaña 2: Anotaciones / Eventos
        tabs.addTab(self._create_annotations_tab(), "Eventos / Anotaciones")

        layout.addWidget(tabs)

        # Botón de cierre
        btn_close = QPushButton("Cerrar")
        btn_close.setFixedWidth(120)
        btn_close.clicked.connect(self.accept)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)

    def _create_channels_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Cabecera informativa
        lbl_info = QLabel(
            f"<b>Duración Total del Registro:</b> {self.duration_sec:.2f} s "
            f"({self.duration_sec/60:.2f} min) | "
            f"<b>Canales detectados:</b> {len(self.headers)}"
        )
        layout.addWidget(lbl_info)

        # Tabla de Canales
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Canal / Label", "Fs (Hz)", "Dimensión", "Estado / Muestras"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setRowCount(len(self.headers))

        for i, h in enumerate(self.headers):
            lbl = str(h.get('label', f'Ch_{i+1}'))
            unit = str(h.get('dimension', 'uV'))
            
            raw_fs = h.get('sample_rate') or h.get('sample_frequency')
            try:
                fs_num = float(raw_fs)
                fs_str = f"{fs_num:.2f}" 
            except (ValueError, TypeError):
                fs_num = None
                fs_str = '---'

            # Muestras estimadas
            try:
                samples = int(fs_num * self.duration_sec) if fs_num is not None else '---'
            except Exception:
                samples = '---'

            table.setItem(i, 0, QTableWidgetItem(lbl))
            table.setItem(i, 1, QTableWidgetItem(fs_str))
            table.setItem(i, 2, QTableWidgetItem(unit))
            table.setItem(i, 3, QTableWidgetItem(f"{samples} muestras" if samples != '---' else 'OK'))

        layout.addWidget(table)
        return widget

    def _create_annotations_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        lbl_info = QLabel(f"<b>Total de Eventos Registrados:</b> {len(self.annotations)}")
        layout.addWidget(lbl_info)

        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Tiempo Inicio (Onset)", "Duración", "Descripción / Etiqueta"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setRowCount(len(self.annotations))

        for i, ann in enumerate(self.annotations):
            if isinstance(ann, dict):
                onset = f"{float(ann.get('onset', 0.0)):.3f} s"
                dur = f"{float(ann.get('duration', -1.0)):.2f} s"
                desc = str(ann.get('description', ''))
            elif isinstance(ann, (list, tuple)):
                onset = f"{float(ann[0]):.3f} s"
                dur = f"{float(ann[1]):.2f} s" if len(ann) >= 3 else "N/A"
                desc = str(ann[-1])
            else:
                continue

            table.setItem(i, 0, QTableWidgetItem(onset))
            table.setItem(i, 1, QTableWidgetItem(dur))
            table.setItem(i, 2, QTableWidgetItem(desc))

        layout.addWidget(table)
        return widget