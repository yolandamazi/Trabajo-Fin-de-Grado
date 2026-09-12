from datetime import datetime
import numpy as np
from PyQt5.QtWidgets import QDialog, QHBoxLayout, QHeaderView, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget

class MetadataDialog(QDialog):
  def __init__(
      self,
      parent=None,
      headers=None,
      annotations=None,
      duration_sec=0.0,
      start_time_epoch=0.0,
      file_info='',
  ):
    super().__init__(parent)
    self.setWindowTitle('Metadatos de las señales')
    self.resize(820, 520)

    self.headers = headers or []
    self.annotations = annotations or []
    self.duration_sec = duration_sec
    self.start_time_epoch = float(start_time_epoch or 0.0)
    self.file_info = file_info

    self.init_ui()

  def init_ui(self):
    """Inicializa la interfaz gráfica."""
    layout = QVBoxLayout(self)

    tabs = QTabWidget()
    tabs.addTab(self._create_channels_tab(), 'Canales')
    tabs.addTab(self._create_annotations_tab(), 'Eventos / Anotaciones')

    layout.addWidget(tabs)

    btn_close = QPushButton('Cerrar')
    btn_close.setFixedWidth(120)
    btn_close.clicked.connect(self.accept)

    btn_layout = QHBoxLayout()
    btn_layout.addStretch()
    btn_layout.addWidget(btn_close)
    layout.addLayout(btn_layout)

  def _create_channels_tab(self):
    """Genera la pestaña de canales."""
    widget = QWidget()
    layout = QVBoxLayout(widget)

    lbl_info = QLabel(
        f'<b>Duración ECG:</b> {self.duration_sec:.2f} s '
        f'({self.duration_sec/60:.2f} min) | '
        f'<b>Total Canales:</b> {len(self.headers)}'
    )
    layout.addWidget(lbl_info)

    table = QTableWidget()
    table.setColumnCount(4)
    table.setHorizontalHeaderLabels(
        ['Canal', 'Fs (Hz)', 'Duración', 'Nº Muestras']
    )

    # Ajuste de anchura de columnas
    header = table.horizontalHeader()
    header.setSectionResizeMode(
        0, QHeaderView.Stretch
    )  # Canal ocupa el espacio restante
    header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Fs
    header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Duración
    header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Muestras

    table.setRowCount(len(self.headers))

    for i, h in enumerate(self.headers):
      lbl = str(h.get('label', f'Ch_{i+1}'))

      raw_fs = h.get('sample_rate') or h.get('sample_frequency')
      try:
        fs_num = float(raw_fs)
        fs_str = (
            f'{fs_num:.6f}'.rstrip('0').rstrip('.')
            if fs_num % 1 != 0
            else f'{fs_num:.1f}'
        )
      except (ValueError, TypeError):
        fs_num = None
        fs_str = '---'

      dur_ch = float(h.get('duration_sec', self.duration_sec))
      mins = int(dur_ch // 60)
      secs = dur_ch % 60
      dur_str = f'{mins}m {secs:.1f}s'

      samples_val = h.get('samples')
      if (
          samples_val is None
          or samples_val == '---'
          or not isinstance(samples_val, (int, float, np.integer))
      ):
        if fs_num is not None and dur_ch > 0:
          samples_val = int(np.round(fs_num * dur_ch))
        else:
          samples_val = '---'

      if isinstance(samples_val, (int, float, np.integer)) and samples_val > 0:
        samples_str = f'{int(samples_val):,}'.replace(',', '.')
      else:
        samples_str = '---'

      table.setItem(i, 0, QTableWidgetItem(lbl))
      table.setItem(i, 1, QTableWidgetItem(fs_str))
      table.setItem(i, 2, QTableWidgetItem(dur_str))
      table.setItem(i, 3, QTableWidgetItem(samples_str))

    layout.addWidget(table)
    return widget

  def _create_annotations_tab(self):
    """Calcula la hora de la anotación"""
    widget = QWidget()
    layout = QVBoxLayout(widget)

    lbl_info = QLabel(
        f'<b>Total de Eventos Registrados:</b> {len(self.annotations)}'
    )
    layout.addWidget(lbl_info)

    table = QTableWidget()
    table.setColumnCount(2)
    table.setHorizontalHeaderLabels(
        ['Hora Real', 'Etiqueta']
    )

    header = table.horizontalHeader()
    header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
    header.setSectionResizeMode(1, QHeaderView.Stretch)

    table.setRowCount(len(self.annotations))

    for i, ann in enumerate(self.annotations):
      if isinstance(ann, dict):
        onset_sec = float(ann.get('onset', 0.0))
        desc = str(
            ann.get('description') or ann.get('label') or ann.get('text', '')
        )
      elif isinstance(ann, (list, tuple)):
        onset_sec = float(ann[0])
        desc = str(ann[-1]) if len(ann) > 1 else ''
      else:
        continue

      if self.start_time_epoch > 0:
        abs_timestamp = self.start_time_epoch + onset_sec
        dt_obj = datetime.fromtimestamp(abs_timestamp)
        time_str = dt_obj.strftime('%H:%M:%S')
      else:
        hrs = int(onset_sec // 3600)
        mins = int((onset_sec % 3600) // 60)
        secs = int(onset_sec % 60)
        time_str = f'{hrs:02d}:{mins:02d}:{secs:02d}'

      table.setItem(i, 0, QTableWidgetItem(time_str))
      table.setItem(i, 1, QTableWidgetItem(desc))

    layout.addWidget(table)
    return widget