import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import numpy as np
from PyQt5.QtWidgets import QFileDialog, QGroupBox, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton, QVBoxLayout, QWidget
from src.gui.metadata_window import MetadataDialog
from src.gui.widgets import MultiChannelPlotWidget
from src.modules.ecg_module import ECGProcessor
from src.modules.edf_converter import EDFExporter
from src.modules.emg_module import EMGProcessor
from src.modules.sync_module import SyncModule

LOCAL_TIMEZONE = ZoneInfo('Europe/Madrid')

class MainWindow(QMainWindow):
  def __init__(self):
    super().__init__()
    self.setWindowTitle('Sincronizador ECG/EMG')

    # Procesadores de señal
    self.emg_processor = EMGProcessor()
    self.ecg_processor = ECGProcessor()

    # Señal ECG
    self.ecg_signals_all = []
    self.ecg_headers_all = []
    self.ecg_meta = {}
    self.ecg_fs = None
    self.ecg_start_time = 0.0

    # Señal EMG
    self.emg_signals = None
    self.emg_headers = []
    self.emg_fs = None
    self.emg_start_time = 0.0

    # Marcas de eventos
    self.annotations = []

    # Inicializar GUI
    self.init_ui()

  def showEvent(self, event):
    """Maximiza la ventana automáticamente al iniciarse la aplicación"""
    super().showEvent(event)
    self.showMaximized()

  def align_time(self, dt_obj_or_str, is_local_time: bool = False) -> float:
      """Convierte fechas y aplica corrección de formato 12h (AM/PM) para archivos .hpf"""
      if not dt_obj_or_str:
        return 0.0

      dt = None

      if isinstance(dt_obj_or_str, (int, float)):
        return float(dt_obj_or_str)

      if isinstance(dt_obj_or_str, datetime):
        dt = dt_obj_or_str
      elif isinstance(dt_obj_or_str, (tuple, list)) and len(dt_obj_or_str) >= 3:
        try:
          dt = datetime(*[int(x) for x in dt_obj_or_str])
        except Exception:
          return 0.0

      if dt is None:
        dt_str = str(dt_obj_or_str).strip()
        if not dt_str:
          return 0.0

        cleaned = re.sub(r'(\.\d{6})\d+', r'\1', dt_str)
        formats = [
            '%Y-%m-%d %H:%M:%S.%f',
            '%Y-%m-%d %H:%M:%S',
            '%d-%m-%Y %H:%M:%S',
            '%d-%m-%y %H:%M:%S',
            '%d.%m.%Y %H.%M.%S',
            '%d.%m.%y %H.%M.%S',
            '%d.%m.%Y %H:%M:%S',
            '%d.%m.%y %H:%M:%S',
            '%Y/%m/%d %H:%M:%S.%f',
            '%Y/%m/%d %H:%M:%S',
        ]

        for fmt in formats:
          try:
            dt = datetime.strptime(cleaned, fmt)
            break
          except ValueError:
            pass

        if dt is None:
          try:
            dt = datetime.fromisoformat(cleaned.replace('/', '-'))
          except Exception:
            return 0.0

      if is_local_time and dt is not None and dt.hour < 12:
        if getattr(self, 'ecg_start_time', 0.0) > 0:
          ecg_dt = datetime.fromtimestamp(
              self.ecg_start_time, tz=timezone.utc
          )
          if ecg_dt.hour >= 10 and abs((dt - ecg_dt.replace(tzinfo=None)).total_seconds()) > 18000:
            dt += timedelta(hours=12)

      if is_local_time:
        if dt.tzinfo is None:
          dt = dt.replace(tzinfo=LOCAL_TIMEZONE)
        return dt.astimezone(timezone.utc).timestamp()
      else:
        if dt.tzinfo is None:
          dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()

  def get_ecg_start_epoch(self) -> float:
        """Garantiza la obtención del timestamp de inicio del ECG desde cualquier metadato."""
        if getattr(self, 'ecg_start_time', 0.0) > 0:
            return self.ecg_start_time

        if hasattr(self, 'ecg_meta') and self.ecg_meta:
            for key in ['startdate', 'start_date', 'start_time', 'meas_date', 'date', 'datetime']:
                val = self.ecg_meta.get(key)
                if val:
                    epoch = self.align_time(val)
                    if epoch > 0:
                        self.ecg_start_time = epoch
                        return epoch
        return 0.0  

  def init_ui(self):
    """Inicializa la interfaz de la aplicación."""
    central_widget = QWidget()
    self.setCentralWidget(central_widget)
    main_layout = QVBoxLayout(central_widget)

    file_layout = QHBoxLayout()

    self.btn_load_edf = QPushButton('Cargar EDF (.edf)')
    self.btn_load_edf.clicked.connect(self.load_edf)
    file_layout.addWidget(self.btn_load_edf)

    self.btn_extract_ecg = QPushButton('Extraer ECG')
    self.btn_extract_ecg.clicked.connect(self.extract_ecg)
    file_layout.addWidget(self.btn_extract_ecg)

    self.btn_load_emg = QPushButton('Cargar CSV (.csv)')
    self.btn_load_emg.clicked.connect(self.load_csv)
    file_layout.addWidget(self.btn_load_emg)

    self.btn_import_hpf = QPushButton('Importar Metadatos (.hpf)')
    self.btn_import_hpf.clicked.connect(self.import_hpf_metadata)
    file_layout.addWidget(self.btn_import_hpf)

    self.btn_inspect = QPushButton('Ver Metadatos')
    self.btn_inspect.clicked.connect(self.show_metadata_inspector)
    file_layout.addWidget(self.btn_inspect)

    self.btn_export = QPushButton('Exportar EDF+ Unificado')
    self.btn_export.clicked.connect(self.export_edf)
    file_layout.addWidget(self.btn_export)

    main_layout.addLayout(file_layout)

    sync_group = QGroupBox('Control de Sincronización Temporal')
    sync_layout = QHBoxLayout()

    self.btn_auto_sync = QPushButton(
        ' Sincronización Automática '
    )
    self.btn_auto_sync.clicked.connect(self.sync_auto)
    sync_layout.addWidget(self.btn_auto_sync)

    sync_group.setLayout(sync_layout)
    main_layout.addWidget(sync_group)

    self.lbl_status = QLabel('Cargue los datos.')
    main_layout.addWidget(self.lbl_status)

    self.plot_area = MultiChannelPlotWidget()
    main_layout.addWidget(self.plot_area, 1)

  def refresh_gui_plots(self):
    """Actualiza la interfaz."""
    self.plot_area.update_all_channels(
        ecg_signals=self.ecg_signals_all,
        ecg_headers=self.ecg_headers_all,
        ecg_start_time=self.ecg_start_time,
        emg_signals=self.emg_signals,
        emg_headers=self.emg_headers,
        emg_start_time=self.emg_start_time,
        annotations=self.annotations,
    )

  def load_edf(self):
      """Carga el archivo EDF/EDF+ exigiendo una frecuencia de muestreo válida y metadatos limpios."""
      path, _ = QFileDialog.getOpenFileName(
          self, 'Seleccionar ECG / EDF', 'data', 'EDF Files (*.edf)'
      )
      if not path:
        return

      res = self.ecg_processor.read_edf_all_channels(path)
      if isinstance(res, tuple) and len(res) == 3:
        signals, meta, annotations = res

        raw_fs = meta.get('fs')
        if raw_fs is None or float(raw_fs) <= 0:
          QMessageBox.critical(
              self,
              'Error',
              'El archivo EDF no especifica una frecuencia de muestreo (Fs) válida en su cabecera.\n\n'
              'La carga se ha cancelado para evitar datos corruptos.',
          )
          return

        self.ecg_fs = float(raw_fs)
        self.ecg_signals_all = signals
        self.ecg_meta = meta
        self.annotations = annotations
        self.ecg_headers_all = meta.get('headers', [])

        start_dt = meta.get('startdate') or meta.get('start_time')
        self.ecg_start_time = self.align_time(start_dt, is_local_time=False)

        self.emg_signals = None
        self.emg_headers = []
        self.emg_start_time = 0.0

        self.refresh_gui_plots()
        self.lbl_status.setText(
            f'EDF Cargado.'
        )

  def extract_ecg(self):
      """Aísla exclusivamente el canal ECG aplicando validación estricta."""
      if not self.ecg_signals_all:
        QMessageBox.warning(
            self, 'Aviso', 'Carga primero un archivo EDF/EDF+.'
        )
        return

      ecg_idx = None
      found_label = ''
      for i, h in enumerate(self.ecg_headers_all):
        lbl = str(h.get('label', ''))
        if 'ecg' in lbl.lower():
          ecg_idx = i
          found_label = lbl
          break

      if ecg_idx is None:
        QMessageBox.warning(
            self,
            'Error de Extracción',
            (
                'No se ha podido identificar ningún canal con la etiqueta'
                " 'ECG' en las cabeceras del archivo."
            ),
            QMessageBox.Ok,
        )
        return

      self.ecg_signals_all = [self.ecg_signals_all[ecg_idx]]
      self.ecg_headers_all = [self.ecg_headers_all[ecg_idx]]

      self.refresh_gui_plots()
      self.lbl_status.setText(
          f"Canal ECG aislado correctamente: '{found_label}'."
      )

  def load_csv(self):
      """Carga el CSV exigiendo que exista un archivo EDF (ECG) cargado previamente."""
      # Comprobar estrictamente si hay un EDF cargado antes de permitir el EMG
      if not getattr(self, 'ecg_signals_all', None):
        QMessageBox.warning(
            self,
            'Aviso',
            'Debe cargar un archivo EDF (ECG) antes de importar.'
        )
        return

      path, _ = QFileDialog.getOpenFileName(
          self,
          'Seleccionar EMG / CSV',
          'data/raw',
          'Archivos CSV/TXT (*.csv *.txt)',
      )
      if not path:
        return

      raw, meta = self.emg_processor.read_file(path)

      if raw is not None and raw.size > 0:
        raw_fs = meta.get('fs') or getattr(self.emg_processor, 'fs', None)
        if raw_fs is None or float(raw_fs) <= 0:
          QMessageBox.warning(
              self,
              'Error de Frecuencia',
              'No se ha podido detectar la frecuencia de muestreo (Fs) en el archivo EMG o en sus metadatos.',
          )
          return

        self.emg_fs = float(raw_fs)
        filtered = self.emg_processor.filter_signal_multichannel(raw)

        self.emg_signals_raw = filtered.copy()
        self.emg_signals = filtered.copy()

        total_samples = self.emg_signals_raw.shape[1]
        self.emg_duration_sec = total_samples / self.emg_fs

        num_channels = self.emg_signals_raw.shape[0]
        meta_headers = meta.get('headers', [])
        ch_names = getattr(self.emg_processor, 'channel_names', [])
        ch_units = getattr(self.emg_processor, 'units', [])
        global_dim = meta.get('dimension', '')

        extracted_headers = []
        for i in range(num_channels):
          label = f'EMG_{i+1}'
          if (
              meta_headers
              and i < len(meta_headers)
              and isinstance(meta_headers[i], dict)
          ):
            label = meta_headers[i].get('label', label)
          elif i < len(ch_names) and ch_names[i]:
            label = ch_names[i]

          dimension = None
          if (
              meta_headers
              and i < len(meta_headers)
              and isinstance(meta_headers[i], dict)
          ):
            dimension = (
                meta_headers[i].get('dimension')
                or meta_headers[i].get('units')
            )
          
          if not dimension and i < len(ch_units) and ch_units[i]:
            dimension = ch_units[i]
            
          if not dimension and global_dim:
            dimension = global_dim

          if not dimension and label:
            match = re.search(r'[\(\[](uV|µV|mV|V)[\)\]]', label, re.IGNORECASE)
            if match:
              dimension = match.group(1).replace('µ', 'u')

          if not dimension:
            QMessageBox.critical(
                self,
                'Error de Metadatos',
                f'El canal {i+1} ("{label}") no especifica ninguna unidad o dimensión.\n\n'
                'La carga se ha cancelado para evitar datos corruptos.',
            )
            return

          extracted_headers.append({
              'label': str(label),
              'dimension': str(dimension).strip(),
              'sample_rate': self.emg_fs,
          })

        self.emg_headers = extracted_headers
        self.refresh_gui_plots()

        mins = int(self.emg_duration_sec // 60)
        secs = self.emg_duration_sec % 60
        self.lbl_status.setText(
            f'CSV Cargado.'
        )

  def import_hpf_metadata(self):
      """Importa metadatos del HPF exigiendo que existan señales EMG cargadas previamente."""
      if (
          getattr(self, 'emg_signals', None) is None
          or self.emg_signals.size == 0
      ):
        QMessageBox.warning(
            self,
            'Aviso',
            'Debe cargar un archivo CSV antes de importar los'
            ' metadatos HPF.',
            QMessageBox.Ok,
        )
        return

      path, _ = QFileDialog.getOpenFileName(
          self,
          'Seleccionar Archivo de Metadatos HPF',
          'data/raw',
          'Archivos HPF (*.hpf)',
      )
      if not path:
        return

      meta = self.emg_processor.extract_hpf_metadata(path)

      if meta.get('start_time'):
        raw_fs = meta.get('fs') or getattr(self.emg_processor, 'fs', None)
        if raw_fs is None or float(raw_fs) <= 0:
          QMessageBox.critical(
              self,
              'Error de Metadatos',
              'El archivo HPF no especifica una frecuencia de muestreo (Fs)'
              ' válida.',
              QMessageBox.Ok,
          )
          return

        self.emg_fs = float(raw_fs)
        self.emg_start_time = self.align_time(
            meta['start_time'], is_local_time=True
        )

        num_channels = self.emg_signals.shape[0]
        meta_headers = meta.get('headers', [])
        ch_names = getattr(self.emg_processor, 'channel_names', [])
        ch_units = getattr(self.emg_processor, 'units', [])
        global_dim = meta.get('dimension', '')

        extracted_headers = []
        for i in range(num_channels):
          label = f'EMG_{i+1}'
          if (
              meta_headers
              and i < len(meta_headers)
              and isinstance(meta_headers[i], dict)
          ):
            label = meta_headers[i].get('label', label)
          elif i < len(ch_names) and ch_names[i]:
            label = ch_names[i]

          dimension = None
          if (
              meta_headers
              and i < len(meta_headers)
              and isinstance(meta_headers[i], dict)
          ):
            dimension = (
                meta_headers[i].get('dimension')
                or meta_headers[i].get('units')
            )
          if not dimension and i < len(ch_units) and ch_units[i]:
            dimension = ch_units[i]
          if not dimension and global_dim:
            dimension = global_dim

          if not dimension:
            QMessageBox.critical(
                self,
                'Error de Metadatos',
                f'El canal EMG {i+1} ("{label}") del HPF no especifica'
                ' dimensión o unidad.',
                QMessageBox.Ok,
            )
            return

          extracted_headers.append({
              'label': str(label),
              'dimension': str(dimension).strip(),
              'sample_rate': self.emg_fs,
          })

        self.emg_headers = extracted_headers

        offset_sec = max(0.0, self.emg_start_time - self.ecg_start_time)
        self.apply_offset(offset_sec)

        dt_local = datetime.fromtimestamp(self.emg_start_time, tz=LOCAL_TIMEZONE)
        dt_str_local = dt_local.strftime('%H:%M:%S')

        QMessageBox.information(
            self,
            'Metadatos HPF Sincronizados',
            'Señales EMG alineadas correctamente',
            QMessageBox.Ok,
        )
        self.lbl_status.setText('EMG Alineados.')
        self.hpf_loaded = True
      else:
        QMessageBox.warning(
            self,
            'Error',
            'No se pudo leer la etiqueta <StartTime> del archivo .hpf.',
            QMessageBox.Ok,
        )

  def apply_offset(self, offset_sec: float):
      """Sincroniza las señaes EMG aplicando padding de ceros al inicio y al final
      para igualar exactamente la duración total del canal ECG."""

      self.current_offset_sec = float(offset_sec)

      raw_emg = getattr(self, 'emg_signals_raw', None)
      if raw_emg is not None and self.ecg_signals_all:
        ecg_dur_sec = len(self.ecg_signals_all[0]) / float(self.ecg_fs)
        total_records = int(np.ceil(ecg_dur_sec))

        emg_fs = float(self.emg_fs)
        target_emg_samples = total_records * int(np.round(emg_fs))

        pad_start = int(
            np.round(max(0.0, self.current_offset_sec) * emg_fs)
        )

        aligned = []
        for sig in raw_emg:
          pad_end = max(0, target_emg_samples - (pad_start + len(sig)))
          sig_padded = np.pad(
              sig, (pad_start, pad_end), mode='constant', constant_values=0.0
          )[:target_emg_samples]
          aligned.append(sig_padded)

        self.emg_signals = np.array(aligned)
        self.emg_start_time = self.ecg_start_time
        self.refresh_gui_plots()

  def sync_auto(self):
        """Alinea las señales automaticamente tras verificar ECG, EMG y metadatos HPF."""
        if (
            not getattr(self, 'ecg_signals_all', None)
            or getattr(self, 'emg_signals_raw', None) is None
        ):
            QMessageBox.warning(
                self,
                'Aviso',
                'Debes cargar ECG y EMG previamente.',
                QMessageBox.Ok,
            )
            return

        # Comprobación de seguridad: verificar que se han importado los metadatos HPF
        if not getattr(self, 'hpf_loaded', False):
            QMessageBox.warning(
                self,
                'Aviso',
                'Debes importar los metadatos (.hpf) antes de realizar la sincronización automática.',
                QMessageBox.Ok,
            )
            return

        annotation_one_found = False
        ann_time = 0.0
        if self.annotations:
            for ann in self.annotations:
                label = str(
                    ann.get('label', '')
                    if isinstance(ann, dict)
                    else (ann[2] if len(ann) > 2 else '')
                ).strip()
                if label == '1':
                    annotation_one_found = True
                    ann_time = float(ann.get('time', 0.0) if isinstance(ann, dict) else ann[0])
                    break

        if not annotation_one_found:
            QMessageBox.warning(
                self,
                'Aviso',
                'No se ha encontrado ninguna anotación con la etiqueta "1" en el registro de ECG '
                'para utilizar como referencia de inicio.',
                QMessageBox.Ok,
            )
            return

        try:
            raw_emg = self.emg_signals_raw
            emg_fs = float(self.emg_fs)
            ecg_ref = self.ecg_signals_all[0]
            ecg_fs = float(self.ecg_headers_all[0]['sample_rate'])

            result = SyncModule.align_emg_to_annotation_one(
                raw_emg, emg_fs, self.annotations, ecg_ref, ecg_fs
            )
            
            if isinstance(result, tuple):
                self.emg_signals, offset_sec = result
            else:
                self.emg_signals = result
                offset_sec = ann_time

            self.emg_start_time = self.ecg_start_time

            self.refresh_gui_plots()
            self.lbl_status.setText(
                f'Señales de EMG sincronizadas | Anclados a Anotación "1" (Desfase: {offset_sec:.2f} s)'
            )

            QMessageBox.information(
                self,
                'Sincronización Automática',
                f'Señales EMG sincronizadas y ancladas a anotación "1" correctamente (Desfase: {offset_sec:.2f} s)',
                QMessageBox.Ok,
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                'Error de Sincronización',
                f'No se pudo completar la sincronización automática:\n{str(e)}',
                QMessageBox.Ok,
            )

  def export_edf(self):
      """Exporta a EDF/EDF+ unificado."""
      if not self.ecg_signals_all or self.emg_signals is None:
        QMessageBox.warning(
            self, 'Error', 'Debe cargar ECG y EMG antes de exportar.'
        )
        return

      save_path, _ = QFileDialog.getSaveFileName(
          self,
          'Guardar EDF+ Unificado',
          'data/output/estudio_completo.edf',
          'EDF Files (*.edf)',
      )
      if not save_path:
        return

      base_fs = float(self.ecg_fs) if hasattr(self, 'ecg_fs') else 0
      ecg_dur_sec = len(self.ecg_signals_all[0]) / base_fs
      total_records = int(np.ceil(ecg_dur_sec))

      headers = []
      signals_to_export = []

      for i, sig in enumerate(self.ecg_signals_all):
        h = self.ecg_headers_all[i] if i < len(self.ecg_headers_all) else {}
        lbl = h.get('label', f'ECG_{i+1}')
        
        ch_fs = h.get('sample_rate') or getattr(self, 'ecg_fs', None)
        if not ch_fs or float(ch_fs) <= 0:
          QMessageBox.critical(
              self,
              'Error de Exportación',
              f'El canal ECG {i+1} ("{lbl}") no especifica una frecuencia de muestreo válida.',
          )
          return
        ch_fs = float(ch_fs)

        unit = h.get('dimension') or h.get('units')
        if not unit:
          QMessageBox.critical(
              self,
              'Error de Exportación',
              f'El canal ECG {i+1} ("{lbl}") no especifica ninguna dimensión o unidad.',
          )
          return

        headers.append({
            'label': str(lbl)[:16],
            'sample_rate': ch_fs,
            'dimension': str(unit).strip(),
        })

        target_samples = total_records * int(np.round(ch_fs))
        pad_needed = target_samples - len(sig)
        if pad_needed > 0:
          sig_padded = np.pad(
              sig, (0, pad_needed), mode='constant', constant_values=0.0
          )
        else:
          sig_padded = sig[:target_samples]
        signals_to_export.append(sig_padded)

      for i in range(self.emg_signals.shape[0]):
        h_emg = self.emg_headers[i] if i < len(self.emg_headers) else {}
        name = h_emg.get('label', f'EMG_{i+1}')
        
        ch_emg_fs = h_emg.get('sample_rate') or getattr(self, 'emg_fs', None)
        if not ch_emg_fs or float(ch_emg_fs) <= 0:
          QMessageBox.critical(
              self,
              'Error de Exportación',
              f'El canal EMG {i+1} ("{name}") no especifica una frecuencia de muestreo válida.',
          )
          return
        ch_emg_fs = float(ch_emg_fs)

        unit_emg = h_emg.get('dimension') or h_emg.get('units')
        if not unit_emg:
          QMessageBox.critical(
              self,
              'Error de Exportación',
              f'El canal EMG {i+1} ("{name}") no especifica ninguna dimensión o unidad.',
          )
          return

        headers.append({
            'label': str(name)[:16],
            'sample_rate': ch_emg_fs,
            'dimension': str(unit_emg).strip(),
        })
        
        target_emg_samples = total_records * int(np.round(ch_emg_fs))
        sig_emg = self.emg_signals[i]
        pad_emg = target_emg_samples - len(sig_emg)
        if pad_emg > 0:
          sig_emg_padded = np.pad(
              sig_emg, (0, pad_emg), mode='constant', constant_values=0.0
          )
        else:
          sig_emg_padded = sig_emg[:target_emg_samples]
        signals_to_export.append(sig_emg_padded)

      if getattr(self, 'ecg_start_time', 0.0) > 0:
        start_date_dt = datetime.fromtimestamp(
            self.ecg_start_time, tz=timezone.utc
        )
      else:
        start_date_dt = datetime.now(timezone.utc)

      EDFExporter.export_unified_edf(
          save_path,
          signals_to_export,
          headers,
          self.annotations,
          start_date_dt,
      )

      QMessageBox.information(
          self,
          'Éxito',
          f'Archivo EDF+ unificado exportado correctamente. ({total_records} s / {len(signals_to_export)} canales).',
      )

  def show_metadata_inspector(self):
    """Muestra la ventana de metadatos de los canales cargados."""
    ecg_signals = getattr(self, 'ecg_signals_all', None)
    emg_signals = getattr(self, 'emg_signals', None)

    has_ecg = ecg_signals is not None and len(ecg_signals) > 0

    has_emg = (
        emg_signals is not None
        and hasattr(emg_signals, 'size')
        and emg_signals.size > 0
    )

    if not has_ecg and not has_emg:
        QMessageBox.warning(
            self,
            'Aviso',
            'Carga al menos un canal.',
        )
        return

    all_headers = []
    if has_ecg:
        ecg_headers = getattr(self, 'ecg_headers_all', [])
        for i, h in enumerate(ecg_headers):
            lbl = h.get('label', f'ECG_{i+1}')
            fs_val = h.get('sample_rate') or h.get('sample_frequency')
            if fs_val is None or float(fs_val) <= 0:
                QMessageBox.critical(
                    self,
                    'Error de Metadatos',
                    f'El canal ECG {i+1} ("{lbl}") '
                    'no especifica una frecuencia de muestreo válida.',
                )
                return

            fs_val = float(fs_val)
            unit = h.get('dimension') or h.get('units')
            if not unit:
                QMessageBox.critical(
                    self,
                    'Error de Metadatos',
                    f'El canal ECG {i+1} ("{lbl}") '
                    'no especifica ninguna dimensión o unidad.',
                )
                return

            sig = (
                ecg_signals[i]
                if i < len(ecg_signals)
                else []
            )

            n_samples = len(sig)
            dur_ch = n_samples / fs_val
            all_headers.append({
                'label': str(lbl),
                'sample_rate': fs_val,
                'dimension': str(unit).strip(),
                'duration_sec': dur_ch,
                'samples': n_samples,
            })

    raw_emg = getattr(self, 'emg_signals_raw', None)
    emg_source = (
        raw_emg
        if raw_emg is not None
        else emg_signals
    )

    has_emg_source = (
        emg_source is not None
        and hasattr(emg_source, 'size')
        and emg_source.size > 0
    )

    if has_emg_source:
        n_samples_raw = emg_source.shape[1]
        emg_headers = getattr(self, 'emg_headers', [])
        for i in range(emg_source.shape[0]):

            hdr_i = (
                emg_headers[i]
                if i < len(emg_headers)
                else {}
            )

            name = hdr_i.get(
                'label',
                f'EMG_{i+1}'
            )

            fs_val = (
                hdr_i.get('sample_rate')
                or getattr(self, 'emg_fs', None)
            )

            if fs_val is None or float(fs_val) <= 0:
                QMessageBox.critical(
                    self,
                    'Error de Metadatos',
                    f'El canal EMG {i+1} ("{name}") '
                    'no especifica una frecuencia de muestreo válida.',
                )
                return

            fs_val = float(fs_val)
            unit = (
                hdr_i.get('dimension')
                or hdr_i.get('units')
            )

            if not unit:
                QMessageBox.critical(
                    self,
                    'Error de Metadatos',
                    f'El canal EMG {i+1} ("{name}") '
                    'no especifica ninguna dimensión o unidad.',
                )
                return

            dur_emg_raw = n_samples_raw / fs_val
            all_headers.append({
                'label': str(name),
                'sample_rate': fs_val,
                'dimension': str(unit).strip(),
                'duration_sec': dur_emg_raw,
                'samples': n_samples_raw,
            })

    dur_master_sec = 0.0
    start_time_epoch = 0.0

    if has_ecg:
        ecg_fs = getattr(self, 'ecg_fs', None)

        if ecg_fs is not None and float(ecg_fs) > 0:
            dur_master_sec = (
                len(ecg_signals[0]) / float(ecg_fs)
            )

        if hasattr(self, 'get_ecg_start_epoch'):
            start_time_epoch = self.get_ecg_start_epoch()

    elif has_emg_source:
        emg_fs = getattr(self, 'emg_fs', None)

        if emg_fs is not None and float(emg_fs) > 0:
            dur_master_sec = (
                emg_source.shape[1] / float(emg_fs)
            )

        start_time_epoch = getattr(
            self,
            'emg_start_epoch',
            0.0
        )

    dialog = MetadataDialog(
        parent=self,
        headers=all_headers,
        annotations=getattr(self, 'annotations', []),
        duration_sec=dur_master_sec,
        start_time_epoch=start_time_epoch,
    )

    dialog.exec_()