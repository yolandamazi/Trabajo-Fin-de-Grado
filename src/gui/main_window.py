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
# from src.utils.helpers import setup_logger

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sincronizador Biomédico ECG/EMG - TFG")
        self.resize(1100, 700)
        # self.logger = setup_logger()
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
        self.btn_auto_sync.clicked.connect(self.sync_auto)
        sync_layout.addWidget(self.btn_auto_sync)

        sync_layout.addWidget(QLabel("Offset Manual (seg):"))
        
        # Control de precisión fina
        self.spin_offset = QDoubleSpinBox()
        self.spin_offset.setRange(-10000.0, 10000.0)
        self.spin_offset.setSingleStep(0.1)
        self.spin_offset.setDecimals(3)
        self.spin_offset.valueChanged.connect(self.on_spin_changed)
        sync_layout.addWidget(self.spin_offset)

        # Deslizador rápido
        self.slider_offset = QSlider(Qt.Horizontal)
        self.slider_offset.setRange(-5000, 5000) # -5.0s a +5.0s en ms
        self.slider_offset.setValue(0)
        self.slider_offset.valueChanged.connect(self.on_slider_changed)
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
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar ECG / EDF Unificado", "data/raw", "EDF Files (*.edf)")
        if path:
            import numpy as np

            # 1. Resetear el offset
            self.spin_offset.setValue(0.0)
            self.current_offset_sec = 0.0

            # 2. Leer canales y metadatos
            signals, self.ecg_meta, self.annotations = self.ecg_processor.read_edf_all_channels(path)
            labels = self.ecg_meta.get('labels', [])

            # Canal principal (ECG)
            self.ecg_signal = signals[0]
            self.plot_area.set_ecg_data(self.ecg_signal, self.ecg_meta['fs'])
            self.plot_area.draw_annotations(self.annotations)

            # 3. Filtrar canales que sean explícitamente de EMG
            emg_indices = [i for i, label in enumerate(labels) if 'EMG' in label.upper()]

            if emg_indices:
                # Es un EDF Unificado exportado previa o externamente
                raw_emg = [signals[i] for i in emg_indices]
                min_len = min(len(s) for s in raw_emg)
                self.emg_signals = np.array([s[:min_len] for s in raw_emg])
                
                self.emg_fs = self.ecg_meta['fs']
                self.plot_area.set_emg_data(self.emg_signals[0], self.emg_fs, 0.0)
                self.lbl_status.setText(f"EDF Unificado Cargado: 1 ECG + {len(self.emg_signals)} EMG. Eventos: {len(self.annotations)}")
            else:
                # Es un ECG estándar (puro), se vacía el estado del EMG previo
                self.emg_signals = None
                self.plot_area.plot_emg.clear()
                self.lbl_status.setText(f"ECG Cargado ({len(self.ecg_signal)} muestras). Eventos: {len(self.annotations)}")
                               
    def load_emg(self):
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar EMG", "data/raw", "Archivos EMG (*.csv *.txt *.hpf)")
        if path:
            raw, meta = self.emg_processor.read_file(path)
            
            if raw.size > 0:
                # 1. Guardar explícitamente
                self.emg_signals = self.emg_processor.filter_signal_multichannel(raw)
                self.emg_fs = self.emg_processor.fs
                
                # 2. Actualizar visualización
                self.plot_area.set_emg_data(self.emg_signals[0], self.emg_processor.fs, self.current_offset_sec)
                self.lbl_status.setText(f"EMG Cargado: {self.emg_signals.shape[0]} canales musculares.")
            else:
                self.lbl_status.setText(f"Metadatos .hpf leídos correctamente ({len(meta['channels'])} canales). Selecciona ahora el .csv.")

    def sync_auto(self):
        """Estrategia de sincronización inteligente: Timestamps > Evento t0 > Manual"""
        if self.ecg_signal is None or self.emg_signals is None:
            QMessageBox.warning(self, "Error", "Debes cargar ECG y EMG previamente.")
            return

        ecg_start = self.ecg_meta.get('startdate') if self.ecg_meta else None
        emg_start = self.emg_processor.start_time

        # 1. Probar por timestamp de cabecera
        offset = SyncModule.calculate_time_offset(ecg_start, emg_start)

        if offset != 0.0:
            msg = f"Sincronizado automáticamente por cabecera.\nDesfase: {offset:.3f} s."
        # 2. Si las cabeceras no son fiables, usar la marca del primer evento (t0)
        elif hasattr(self, 'annotations') and len(self.annotations) > 0:
            offset = self.annotations[0]['onset']
            msg = f"Cabeceras no fiables. Alineado automáticamente con la marca del primer evento (t0 = {offset:.2f} s)."
        # 3. Si no hay marcas, avisar para ajuste manual
        else:
            msg = "Relojes no sincronizados en origen y sin marcas t0. Realiza el ajuste mediante 'Offset Manual'."

        # Aplicar a la interfaz
        self.spin_offset.setValue(offset)
        self.on_offset_changed(offset)

        QMessageBox.information(self, "Sincronización Automática", msg)

    def on_spin_changed(self, val: float):
        """Se activa al cambiar el SpinBox (casilla)."""
        self.slider_offset.blockSignals(True)
        self.slider_offset.setValue(int(val))
        self.slider_offset.blockSignals(False)
        self.apply_offset(val)

    def on_slider_changed(self, val: int):
        """Se activa al arrastrar el Slider (barra)."""
        self.spin_offset.blockSignals(True)
        self.spin_offset.setValue(float(val))
        self.spin_offset.blockSignals(False)
        self.apply_offset(float(val))

    def apply_offset(self, offset_val: float):
        """Aplica el cambio en pantalla en tiempo real."""
        self.current_offset_sec = offset_val
        
        # Usar la variable guardada self.emg_fs
        if self.emg_signals is not None and len(self.emg_signals) > 0:
            fs = getattr(self, 'emg_fs', 1000.0)
            self.plot_area.set_emg_data(self.emg_signals[0], fs, self.current_offset_sec)

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

    def on_offset_changed(self, val: float):
        """Aplica el offset al EMG en tiempo real."""
        self.current_offset_sec = float(val)

        # Mover la señal de EMG en el eje X
        if self.emg_signals is not None and len(self.emg_signals) > 0:
            self.plot_area.set_emg_data(self.emg_signals[0], self.emg_processor.fs, self.current_offset_sec)