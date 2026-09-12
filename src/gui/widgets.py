from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QScrollArea, QSplitter, QSizePolicy, QLabel
from PyQt5.QtCore import Qt
import pyqtgraph as pg
import numpy as np
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

LOCAL_TIMEZONE = ZoneInfo("Europe/Madrid")

class TimeAxisItem(pg.AxisItem):
  def __init__(self, *args, tz=LOCAL_TIMEZONE, **kwargs):
    super().__init__(*args, **kwargs)
    self.tz = tz

  def tickStrings(self, values, scale, spacing):
    strings = []
    for v in values:
      try:
        dt_utc = datetime.fromtimestamp(v, tz=timezone.utc)
        dt_local = dt_utc.astimezone(self.tz)
        strings.append(dt_local.strftime("%H:%M:%S"))
      except (ValueError, OverflowError, OSError):
        strings.append("")
    return strings


class MultiChannelPlotWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # PANEL IZQUIERDO: CANALES EDF 
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(2, 2, 2, 2)
        
        self.lbl_ecg_title = QLabel("CANALES EDF")
        self.lbl_ecg_title.setAlignment(Qt.AlignCenter)
        self.lbl_ecg_title.setStyleSheet("""
            QLabel {
                background-color: #112233;
                color: #00ccff;
                font-weight: bold;
                font-size: 13px;
                padding: 6px;
                border: 1px solid #224455;
                border-radius: 4px;
            }
        """)
        left_layout.addWidget(self.lbl_ecg_title)
        
        self.ecg_scroll = QScrollArea()
        self.ecg_scroll.setWidgetResizable(True)
        self.ecg_scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.ecg_graphics = pg.GraphicsLayoutWidget()
        self.ecg_scroll.setWidget(self.ecg_graphics)
        left_layout.addWidget(self.ecg_scroll)

        # PANEL DERECHO: CANALES EMG (HPF/CSV)
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(2, 2, 2, 2)
        
        self.lbl_emg_title = QLabel("CANALES EMG")
        self.lbl_emg_title.setAlignment(Qt.AlignCenter)
        self.lbl_emg_title.setStyleSheet("""
            QLabel {
                background-color: #2b1515;
                color: #ff5555;
                font-weight: bold;
                font-size: 13px;
                padding: 6px;
                border: 1px solid #442222;
                border-radius: 4px;
            }
        """)
        right_layout.addWidget(self.lbl_emg_title)
        
        self.emg_scroll = QScrollArea()
        self.emg_scroll.setWidgetResizable(True)
        self.emg_scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.emg_graphics = pg.GraphicsLayoutWidget()
        self.emg_scroll.setWidget(self.emg_graphics)
        right_layout.addWidget(self.emg_scroll)
        
        self.splitter.addWidget(left_container)
        self.splitter.addWidget(right_container)
        self.splitter.setSizes([600, 600])
        
        main_layout.addWidget(self.splitter)
        
        self.plots = []
        self.master_plot = None

    def update_all_channels(
        self,
        ecg_signals: list,
        ecg_headers: list,
        ecg_start_time: float = 0.0,
        emg_signals: np.ndarray = None,
        emg_headers: list = None,
        emg_start_time: float = 0.0,
        annotations: list = None,
    ):
      """Actualiza las gráficas exigiendo que cada canal tenga su Fs y dimensión en su propia cabecera."""
      self.ecg_graphics.clear()
      self.emg_graphics.clear()
      self.plots.clear()
      self.master_plot = None

      n_ecg_count = len(ecg_signals) if ecg_signals else 0
      n_emg_count = (
          emg_signals.shape[0]
          if emg_signals is not None and emg_signals.size > 0
          else 0
      )

      self.lbl_ecg_title.setText(f'CANALES EDF ({n_ecg_count})')
      self.lbl_emg_title.setText(f'CANALES EMG ({n_emg_count})')

      # PANEL IZQUIERDO: CANALES ECG
      row_ecg = 0
      if ecg_signals and len(ecg_signals) > 0:
        for i, sig in enumerate(ecg_signals):
          if len(sig) == 0:
            continue

          hdr = (
              ecg_headers[i] if ecg_headers and i < len(ecg_headers) else {}
          )
          if not isinstance(hdr, dict):
            raise ValueError(f'Cabecera inválida para el canal ECG {i+1}')

          label = str(hdr.get('label', f'Canal_{i+1}'))

          unit = hdr.get('dimension') or hdr.get('units')
          if not unit:
            raise ValueError(
                f'El canal ECG {i+1} ("{label}") no especifica dimensión o unidad.'
            )
          unit_str = str(unit).strip()

          ch_fs = hdr.get('sample_frequency') or hdr.get('sample_rate')
          if ch_fs is None or float(ch_fs) <= 0:
            raise ValueError(
                f'El canal ECG {i+1} ("{label}") no especifica un sample_rate válido.'
            )
          ch_fs = float(ch_fs)

          time_axis_item = TimeAxisItem(orientation='bottom')
          time_axis_item.enableAutoSIPrefix(False)
          p = self.ecg_graphics.addPlot(
              row=row_ecg,
              col=0,
              title=f'[{i+1}] {label}',
              axisItems={'bottom': time_axis_item},
          )
          p.setMinimumHeight(150)
          p.showGrid(x=True, y=True)
          p.enableAutoRange(axis=pg.ViewBox.YAxis, enable=True)

          p.setLabel('left', 'Amplitud', units=unit_str)
          p.setLabel('bottom', 'Hora Real')

          time_axis = ecg_start_time + (np.arange(len(sig)) / ch_fs)
          p.plot(time_axis, sig, pen=pg.mkPen(color=(0, 220, 255), width=1))

          if self.master_plot is None:
            self.master_plot = p
          else:
            p.setXLink(self.master_plot)

          self.plots.append(p)
          row_ecg += 1

      self.ecg_graphics.setMinimumHeight(max(300, row_ecg * 160 + 50))

      # PANEL DERECHO: CANALES EMG
      row_emg = 0
      if emg_signals is not None and emg_signals.size > 0:
        for i in range(n_emg_count):
          sig = emg_signals[i]
          hdr = (
              emg_headers[i] if emg_headers and i < len(emg_headers) else {}
          )
          if not isinstance(hdr, dict):
            raise ValueError(f'Cabecera inválida para el canal EMG {i+1}')

          label = str(hdr.get('label', f'EMG_{i+1}'))

          unit = hdr.get('dimension') or hdr.get('units')
          if not unit:
            raise ValueError(
                f'El canal EMG {i+1} ("{label}") no especifica dimensión o unidad.'
            )
          unit_str = str(unit).strip()

          ch_fs = hdr.get('sample_frequency') or hdr.get('sample_rate')
          if ch_fs is None or float(ch_fs) <= 0:
            raise ValueError(
                f'El canal EMG {i+1} ("{label}") no especifica un frecuencia de muestreo válida.'
            )
          ch_fs = float(ch_fs)

          time_axis_item = TimeAxisItem(orientation='bottom')
          time_axis_item.enableAutoSIPrefix(False)
          p = self.emg_graphics.addPlot(
              row=row_emg,
              col=0,
              title=f'[EMG {i+1}] {label}',
              axisItems={'bottom': time_axis_item},
          )
          p.setMinimumHeight(150)
          p.showGrid(x=True, y=True)
          p.enableAutoRange(axis=pg.ViewBox.YAxis, enable=True)

          p.setLabel('left', 'Amplitud', units=unit_str)
          p.setLabel('bottom', 'Hora Real')

          time_axis = emg_start_time + (np.arange(len(sig)) / ch_fs)
          p.plot(time_axis, sig, pen=pg.mkPen(color=(255, 60, 60), width=1))

          if self.master_plot is None:
            self.master_plot = p
          else:
            p.setXLink(self.master_plot)

          self.plots.append(p)
          row_emg += 1

      self.emg_graphics.setMinimumHeight(max(300, row_emg * 160 + 50))

      if annotations:
        self.draw_annotations(annotations, ecg_start_time)

      if self.master_plot is not None:
        self.master_plot.enableAutoRange(axis=pg.ViewBox.XAxis, enable=True)
        self.master_plot.autoRange()

    def draw_annotations(self, annotations: list, ecg_start_time: float = 0.0):
        """Dibuja las líneas de eventos trasladandolas a la hora real."""
        if not annotations or self.master_plot is None:
            return

        for ann in annotations:
            if isinstance(ann, dict):
                rel_onset = float(ann.get('onset', 0.0))
                label = str(ann.get('label', ''))
            else:
                rel_onset = float(ann[0])
                label = str(ann[2]) if len(ann) > 2 else ''

            abs_onset = ecg_start_time + rel_onset

            for p in self.plots:
                line = pg.InfiniteLine(
                    pos=abs_onset, 
                    angle=90, 
                    pen=pg.mkPen(color=(255, 255, 0), width=1.5, style=Qt.DashLine)
                )
                text = pg.TextItem(text=label, color=(255, 255, 0), anchor=(0.5, 1))
                text.setPos(abs_onset, 0)
                
                p.addItem(line)
                p.addItem(text)