import os
import numpy as np
from PyQt5.QtWidgets import (QMainWindow, QPushButton, QFileDialog, QLabel, 
                             QVBoxLayout, QHBoxLayout, QWidget, QMessageBox, 
                             QGroupBox, QSlider, QDoubleSpinBox)
from PyQt5.QtCore import Qt

from src.modules.emg_module import EMGProcessor
from src.modules.ecg_module import ECGProcessor
from src.modules.sync_module import SyncModule
from src.modules.edf_converter import EDFExporter
from src.gui.widgets import MultiChannelPlotWidget
from src.utils.helpers import setup_logger

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sincronizador Biomédico ECG/EMG - TFG")
        self.resize(1100, 700)
        self.logger = setup_logger()
        self.emg_processor = EMGProcessor()
        self.ecg_processor = ECGProcessor()
        self.ecg_raw = None
        self.emg_raw = None
        self.current_offset_sec = 0.0
        self.fs = 1000.0

        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 1. Barra superior: Carga y exportación
        file_layout = QHBoxLayout()
        
        self.btn_load_ecg = QPushButton("1. Cargar ECG (.edf)")
        self.btn_load_ecg.clicked.connect(self.load_ecg)
        file_layout.addWidget(self.btn_load_ecg)

        self.btn_load_emg = QPushButton("2. Cargar EMG (.csv/.hpf)")
        self.btn_load_emg.clicked.connect(self.load_emg)
        file_layout.addWidget(self.btn_load_emg)

        self.btn_export = QPushButton("3. Exportar EDF Unificado")
        self.btn_export.clicked.connect(self.export_edf)
        file_layout.addWidget(self.btn_export)

        main_layout.addLayout(file_layout)

        # 2. Panel de control de sincronización (Auto + Manual)
        sync_group = QGroupBox("Controles de Sincronización Temporal")
        sync_layout = QHBoxLayout()

        self.btn_auto_sync = QPushButton("Sincronización Automática (Cross-Corr)")
        self.btn_auto_sync.clicked.connect(self.auto_sync)
        sync_layout.addWidget(self.btn_auto_sync)

        sync_layout.addWidget(QLabel("Offset Manual (seg):"))
        
        # Control de precisión fina
        self.spin_offset = QDoubleSpinBox()
        self.spin_offset.setRange(-10.0, 10.0)
        self.spin_offset.setSingleStep(0.001)
        self.spin_offset.setDecimals(3)
        self.spin_offset.valueChanged.connect(self.on_spin_offset_changed)
        sync_layout.addWidget(self.spin_offset)

        # Deslizador rápido
        self.slider_offset = QSlider(Qt.Horizontal)
        self.slider_offset.setRange(-5000, 5000) # -5.0s a +5.0s en ms
        self.slider_offset.setValue(0)
        self.slider_offset.valueChanged.connect(self.on_slider_offset_changed)
        sync_layout.addWidget(self.slider_offset)

        sync_group.setLayout(sync_layout)
        main_layout.addWidget(sync_group)

        # 3. Estado de la sesión
        self.lbl_status = QLabel("Estado: Cargue los archivos para iniciar.")
        main_layout.addWidget(self.lbl_status)

        # 4. Visor multicanal
        self.plot_area = MultiChannelPlotWidget()
        main_layout.addWidget(self.plot_area)

    def load_ecg(self):
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar ECG", "data/raw", "EDF Files (*.edf)")
        if path:
            # Guardar explícitamente en self.ecg_signal, self.ecg_meta y self.annotations
            self.ecg_signal, self.ecg_meta, self.annotations = self.ecg_processor.read_edf_with_annotations(path)
            self.plot_area.set_ecg_data(self.ecg_signal, self.ecg_meta['fs'])
            
            ann_names = [a['description'] for a in self.annotations]
            self.lbl_status.setText(f"ECG Cargado ({len(self.ecg_signal)} muestras). Eventos: {len(self.annotations)}")

    def load_emg(self):
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar EMG", "data/raw", "Archivos EMG (*.csv *.txt *.hpf)")
        if path:
            raw, meta = self.emg_processor.read_file(path)
            
            if raw.size > 0:
                # Guardar explícitamente en self.emg_signals
                self.emg_signals = self.emg_processor.filter_signal_multichannel(raw)
                self.plot_area.set_emg_data(self.emg_signals[0], self.emg_processor.fs, self.current_offset_sec)
                self.lbl_status.setText(f"EMG Cargado: {self.emg_signals.shape[0]} canales musculares.")
            else:
                self.lbl_status.setText(f"Metadatos .hpf leídos correctamente ({len(meta['channels'])} canales). Selecciona ahora el .csv.")

    def auto_sync(self):
        if self.ecg_raw is None or self.emg_raw is None:
            QMessageBox.warning(self, "Error", "Debes cargar ECG y EMG previamente.")
            return

        min_len = min(len(self.ecg_raw), len(self.emg_raw))
        _, offset_sec = SyncModule.calculate_offset(
            self.ecg_raw[:min_len], self.emg_raw[:min_len], self.fs
        )
        
        self.current_offset_sec = offset_sec
        
        # Bloquear señales momentáneamente para evitar bucles de actualización
        self.spin_offset.blockSignals(True)
        self.slider_offset.blockSignals(True)
        
        self.spin_offset.setValue(offset_sec)
        self.slider_offset.setValue(int(offset_sec * 1000))
        
        self.spin_offset.blockSignals(False)
        self.slider_offset.blockSignals(False)
        
        self.update_emg_plot()
        self.lbl_status.setText(f"Sincronización automática calculada. Desfase: {offset_sec:.4f} s")

    def on_spin_offset_changed(self, val: float):
        self.current_offset_sec = val
        self.slider_offset.blockSignals(True)
        self.slider_offset.setValue(int(val * 1000))
        self.slider_offset.blockSignals(False)
        self.update_emg_plot()

    def on_slider_offset_changed(self, val: int):
        self.current_offset_sec = val / 1000.0
        self.spin_offset.blockSignals(True)
        self.spin_offset.setValue(self.current_offset_sec)
        self.spin_offset.blockSignals(False)
        self.update_emg_plot()

    def update_emg_plot(self):
        if self.emg_raw is not None:
            self.plot_area.set_emg_data(self.emg_raw, self.fs, self.current_offset_sec)

    def export_edf(self):
        # Validar que ambas señales estén guardadas en la instancia
        if self.ecg_signal is None or self.emg_signals is None or len(self.emg_signals) == 0:
            QMessageBox.warning(self, "Error", "Faltan señales para exportar.")
            return

        save_path, _ = QFileDialog.getSaveFileName(self, "Guardar EDF+ Unificado", "data/output/estudio_completo.edf", "EDF Files (*.edf)")
        if save_path:
            # 1. Ajustar anotaciones según offset
            adj_annotations = SyncModule.adjust_annotations(self.annotations, self.current_offset_sec)

            # 2. Construir cabeceras
            headers = [{'label': self.ecg_meta['label'], 'sample_rate': self.ecg_meta['fs'], 'dimension': 'mV'}]
            signals_to_export = [self.ecg_signal]

            ch_names = self.emg_processor.channel_names
            for i in range(self.emg_signals.shape[0]):
                name = ch_names[i] if i < len(ch_names) else f"EMG_{i+1}"
                headers.append({'label': name[:16], 'sample_rate': self.emg_processor.fs, 'dimension': 'uV'})
                signals_to_export.append(self.emg_signals[i])

            # 3. Exportar a EDF+
            start_date = self.emg_processor.start_time or self.ecg_meta.get('startdate')
            EDFExporter.export_unified_edf(save_path, signals_to_export, headers, adj_annotations, start_date)
            
            QMessageBox.information(self, "Éxito", f"Archivo exportado correctamente con {len(signals_to_export)} canales en:\n{save_path}")