import os
import numpy as np
from PyQt5.QtWidgets import QMainWindow, QPushButton, QFileDialog, QLabel, QVBoxLayout, QHBoxLayout, QWidget, QMessageBox, QGroupBox, QSlider, QDoubleSpinBox
from PyQt5.QtCore import Qt
from src.modules.emg_module import EMGProcessor
from src.modules.ecg_module import ECGProcessor
from src.modules.edf_converter import EDFExporter
from src.gui.widgets import MultiChannelPlotWidget
from src.gui.metadata_window import MetadataDialog

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sincronizador ECG/EMG")

        self.emg_processor = EMGProcessor()
        self.ecg_processor = ECGProcessor()
        
        self.ecg_signals_all = []
        self.ecg_headers_all = []
        self.ecg_meta = {}
        self.ecg_fs = 1000.0

        self.emg_signals = None
        self.emg_headers = []
        self.emg_fs = 1000.0

        self.annotations = []
        self.current_offset_sec = 0.0

        self.init_ui()

    def showEvent(self, event):
        super().showEvent(event)
        self.showMaximized()

    def init_ui(self):
        """Inicializa la interfaz UI/UX de la aplicación"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Barra superior de acciones
        file_layout = QHBoxLayout()
        
        self.btn_load_edf = QPushButton("1. Cargar EDF (.edf)")
        self.btn_load_edf.clicked.connect(self.load_edf)
        file_layout.addWidget(self.btn_load_edf)

        self.btn_extract_ecg = QPushButton("2. Extraer Canal ECG")
        self.btn_extract_ecg.clicked.connect(self.extract_ecg)
        file_layout.addWidget(self.btn_extract_ecg)

        self.btn_load_emg = QPushButton("3. Cargar Señal EMG (.csv)")
        self.btn_load_emg.clicked.connect(self.load_emg)
        file_layout.addWidget(self.btn_load_emg)

        self.btn_inspect = QPushButton("4. Mostrar Metadatos")
        self.btn_inspect.clicked.connect(self.show_metadata_inspector)
        file_layout.addWidget(self.btn_inspect)

        self.btn_export = QPushButton("5. Exportar EDF/EDF+ Unificado")
        self.btn_export.clicked.connect(self.export_edf)
        file_layout.addWidget(self.btn_export)

        self.btn_load_unified = QPushButton("6. Mostrar EDF/EDF+ Unificado")
        self.btn_load_unified.clicked.connect(self.load_edf)
        file_layout.addWidget(self.btn_load_unified)

        main_layout.addLayout(file_layout)

        # Controles de sincronización y enfoque
        sync_group = QGroupBox("Controles de Sincronización Temporal")
        sync_layout = QHBoxLayout()

        self.btn_auto_sync = QPushButton(" Sincronización Automática ")
        self.btn_auto_sync.clicked.connect(self.sync_auto)
        sync_layout.addWidget(self.btn_auto_sync)

        self.lbl_offset_info = QLabel("Desfase: +0.000 s (0.00 min)")
        sync_layout.addWidget(self.lbl_offset_info)

        sync_layout.addWidget(QLabel("Offset Manual (seg):"))
        
        self.spin_offset = QDoubleSpinBox()
        self.spin_offset.setRange(-10000.0, 10000.0)
        self.spin_offset.setSingleStep(0.1)
        self.spin_offset.setDecimals(3)
        self.spin_offset.valueChanged.connect(self.on_spin_changed)
        sync_layout.addWidget(self.spin_offset)

        self.slider_offset = QSlider(Qt.Horizontal)
        self.slider_offset.setRange(-5000, 5000)
        self.slider_offset.setValue(0)
        self.slider_offset.valueChanged.connect(self.on_slider_changed)
        sync_layout.addWidget(self.slider_offset)

        sync_group.setLayout(sync_layout)
        main_layout.addWidget(sync_group)

        # Estado de la sesión
        self.lbl_status = QLabel("Estado: Cargue los datos.")
        main_layout.addWidget(self.lbl_status)

        # Visor multicanal
        self.plot_area = MultiChannelPlotWidget()
        main_layout.addWidget(self.plot_area, 1)

    def refresh_gui_plots(self):
        """Actualiza la interfaz UI/UX"""
        self.plot_area.update_all_channels(
            ecg_signals=self.ecg_signals_all,
            ecg_headers=self.ecg_headers_all,
            ecg_fs=self.ecg_fs,
            emg_signals=self.emg_signals,
            emg_headers=self.emg_headers,
            emg_fs=self.emg_fs,
            offset_sec=self.current_offset_sec,
            annotations=self.annotations
        )

    def load_edf(self):
        """Carga el archivo EDF completo."""
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar ECG / EDF", "data", "EDF Files (*.edf)")
        if path:
            self.spin_offset.setValue(0.0)
            self.current_offset_sec = 0.0

            res = self.ecg_processor.read_edf_all_channels(path)
            if isinstance(res, tuple) and len(res) == 3:
                signals, meta, annotations = res
            else:
                QMessageBox.critical(self, "Error", "No se pudieron leer las señales del archivo EDF.")
                return

            self.ecg_signals_all = signals
            self.ecg_meta = meta
            self.ecg_fs = float(meta.get('fs', 1000.0))
            self.annotations = annotations
            self.ecg_headers_all = meta.get('headers', [])

            self.emg_signals = None
            self.emg_headers = []

            self.refresh_gui_plots()
            
            self.lbl_status.setText(
                f"EDF Cargado: {len(self.ecg_signals_all)} canales. "
                f"Marcas de eventos: {len(self.annotations)}"
            )

    def extract_ecg(self):
        """Aisla exclusivamente el canal principal de ECG."""
        if not self.ecg_signals_all:
            QMessageBox.warning(self, "Aviso", "Carga primero un archivo EDF de origen.")
            return

        ecg_idx = 0
        found_label = ""
        for i, h in enumerate(self.ecg_headers_all):
            lbl = str(h.get('label', ''))
            if 'ecg' in lbl.lower():
                ecg_idx = i
                found_label = lbl
                break

        if not found_label and len(self.ecg_headers_all) > 0:
            found_label = str(self.ecg_headers_all[0].get('label', 'Canal_1'))

        self.ecg_signals_all = [self.ecg_signals_all[ecg_idx]]
        self.ecg_headers_all = [self.ecg_headers_all[ecg_idx]]

        self.refresh_gui_plots()

        self.lbl_status.setText(f"Canal ECG aislado correctamente: '{found_label}'.")
        QMessageBox.information(
            self, "ECG Aislado", 
            f"Se ha extraído el canal principal de ECG ('{found_label}').\n\n"
        )

    def load_emg(self):
        """Carga los datos del archivo (.csv)."""
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar Señal EMG", "data/raw", "Archivos CSV/TXT (*.csv *.txt)")
        if path:
            raw, meta = self.emg_processor.read_file(path)

            if raw is not None and raw.size > 0:
                self.emg_signals = self.emg_processor.filter_signal_multichannel(raw)
                self.emg_fs = float(self.emg_processor.fs)
                
                unit = meta.get('dimension')
                names = getattr(self.emg_processor, 'channel_names', [])
                if names and len(names) == self.emg_signals.shape[0]:
                    self.emg_headers = [{'label': name, 'dimension': unit} for name in names]
                else:
                    self.emg_headers = meta.get('headers', [{'label': f'EMG_{i+1}', 'dimension': unit} for i in range(self.emg_signals.shape[0])])

                self.refresh_gui_plots()
                self.lbl_status.setText(f"EMG Cargado: {self.emg_signals.shape[0]} canales musculares.")
                
                self.emg_signals_raw = self.emg_signals.copy()
                self.apply_offset(self.current_offset_sec)

    def sync_auto(self):
        """Calcula el offset automático y aplica el desplazamiento + relleno/padding."""
        if not self.ecg_signals_all or self.emg_signals is None:
            QMessageBox.warning(self, "Error", "Debes cargar ECG y EMG previamente.")
            return

        offset = 0.0
        if hasattr(self, 'annotations') and len(self.annotations) > 0:
            ann = self.annotations[0] 
            if isinstance(ann, (list, tuple)):
                offset = float(ann[0])
            else:
                float(ann.get('onset', 0.0))

        self.spin_offset.setValue(offset)
        self.apply_offset(offset)

    def on_spin_changed(self, val: float):
        """Sincroniza el slider con el valor numérico del spinbox y aplica el nuevo offset temporal."""
        self.slider_offset.blockSignals(True)
        self.slider_offset.setValue(int(val))
        self.slider_offset.blockSignals(False)
        self.apply_offset(val)

    def on_slider_changed(self, val: int):
        """Sincroniza el spinbox con la posición del slider y aplica el nuevo offset temporal."""
        self.spin_offset.blockSignals(True)
        self.spin_offset.setValue(float(val))
        self.spin_offset.blockSignals(False)
        self.apply_offset(float(val))

    def apply_offset(self, offset_sec: float):
        """Alinea la señal EMG según el offset aplicado, y rellena con ceros (padding)"""
        self.current_offset_sec = float(offset_sec)

        if getattr(self, 'emg_signals_raw', None) is not None and self.ecg_signals_all:
            ecg_dur_sec = len(self.ecg_signals_all[0]) / float(self.ecg_fs)
            total_records = int(np.ceil(ecg_dur_sec))

            emg_fs = float(self.emg_fs)
            target_emg_samples = total_records * int(np.round(emg_fs))

            pad_start = int(np.round(max(0.0, self.current_offset_sec) * emg_fs))

            aligned = []
            for sig in self.emg_signals_raw:
                pad_end = max(0, target_emg_samples - (pad_start + len(sig)))
                sig_padded = np.pad(sig, (pad_start, pad_end), mode='constant', constant_values=0.0)[:target_emg_samples]
                aligned.append(sig_padded)

            self.emg_signals = np.array(aligned)

        self.refresh_gui_plots()

    def export_edf(self):
        """Exportación a EDF/EDF+ con las señales ECG y EMG."""
        if not self.ecg_signals_all or self.emg_signals is None:
            QMessageBox.warning(self, "Error", "Debe cargar ECG y EMG antes de exportar.")
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self, "Guardar EDF+ Unificado", "data/output/estudio_completo.edf", "EDF Files (*.edf)"
        )
        if not save_path:
            return

        # Determinar total de segundos enteros de la sesión
        ecg_dur_sec = len(self.ecg_signals_all[0]) / float(self.ecg_fs)
        total_records = int(np.ceil(ecg_dur_sec))

        headers = []
        signals_to_export = []

        # Canal ECG
        target_ecg_samples = total_records * int(np.round(self.ecg_fs))
        for i, sig in enumerate(self.ecg_signals_all):
            h = self.ecg_headers_all[i] if i < len(self.ecg_headers_all) else {}
            lbl = h.get('label', f'ECG_{i+1}')
            unit = h.get('dimension', 'mV')
            headers.append({'label': str(lbl)[:16], 'sample_rate': self.ecg_fs, 'dimension': unit})

            pad_needed = target_ecg_samples - len(sig)
            if pad_needed > 0:
                sig_padded = np.pad(sig, (0, pad_needed), mode='constant', constant_values=0.0)
            else:
                sig_padded = sig[:target_ecg_samples]
            signals_to_export.append(sig_padded)

        # Canal o Canales EMG 
        ch_names = getattr(self.emg_processor, 'channel_names', [])
        for i in range(self.emg_signals.shape[0]):
            name = ch_names[i] if i < len(ch_names) else f"EMG_{i+1}"
            headers.append({'label': str(name)[:16], 'sample_rate': self.emg_fs, 'dimension': 'uV'})
            signals_to_export.append(self.emg_signals[i])

        # Exportar archivo unificado
        start_date = getattr(self.emg_processor, 'start_time', None) or self.ecg_meta.get('startdate')
        EDFExporter.export_unified_edf(save_path, signals_to_export, headers, self.annotations, start_date)

        QMessageBox.information(
            self, "Éxito", 
            f"Archivo exportado correctamente ({total_records} s / {len(signals_to_export)} canales)."
        )

    def show_metadata_inspector(self):
        """Abre la ventana con los metadatos"""
        if not self.ecg_signals_all and self.emg_signals is None:
            QMessageBox.warning(self, "Aviso", "Carga al menos un archivo antes de inspeccionar metadatos.")
            return

        all_headers = []
        
        # Cabeceras del ECG 
        for i, h in enumerate(self.ecg_headers_all):
            # Lee la unidad guardada en el archivo. Si no existe, usa 'uV' como respaldo
            unit = str(h.get('dimension') or h.get('units') or 'uV').strip()
            fs_val = float(h.get('sample_rate') or h.get('sample_frequency') or self.ecg_fs)
            
            all_headers.append({
                'label': h.get('label', f'ECG_{i+1}'),
                'sample_rate': fs_val,
                'dimension': unit
            })

        # Cabeceras EMG 
        if self.emg_signals is not None and self.emg_signals.size > 0:
            ch_names = getattr(self.emg_processor, 'channel_names', [])
            emg_units = getattr(self.emg_processor, 'units', [])
            
            for i in range(self.emg_signals.shape[0]):
                name = ch_names[i] if i < len(ch_names) else f"EMG_{i+1}"
                
                unit = 'uV'
                if hasattr(self, 'emg_headers') and i < len(self.emg_headers):
                    hdr_i = self.emg_headers[i]
                    if isinstance(hdr_i, dict):
                        unit = hdr_i.get('dimension') or hdr_i.get('units') or unit
                elif i < len(emg_units) and emg_units[i]:
                    unit = emg_units[i]

                all_headers.append({
                    'label': name,
                    'sample_rate': getattr(self, 'emg_fs', 1000.0),
                    'dimension': str(unit).strip()
                })

        dur_sec = len(self.ecg_signals_all[0]) / float(self.ecg_fs) if self.ecg_signals_all else 0.0

        dialog = MetadataDialog(
            parent=self,
            headers=all_headers,
            annotations=getattr(self, 'annotations', []),
            duration_sec=dur_sec
        )
        dialog.exec_()
