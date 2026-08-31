import numpy as np
import pyqtgraph as pg
from PyQt5.QtWidgets import QWidget, QVBoxLayout

class MultiChannelPlotWidget(QWidget):
    """Widget de visualización multicanal con ejes de tiempo vinculados."""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.graphics_layout = pg.GraphicsLayoutWidget()
        layout.addWidget(self.graphics_layout)
        
        # Subplot 1: ECG
        self.p_ecg = self.graphics_layout.addPlot(row=0, col=0, title="Canal ECG (Referencia)")
        self.p_ecg.showGrid(x=True, y=True)
        self.p_ecg.setLabel('left', 'Amplitud', units='mV')
        self.curve_ecg = self.p_ecg.plot(pen=pg.mkPen('#1f77b4', width=1.5))
        
        # Subplot 2: EMG
        self.p_emg = self.graphics_layout.addPlot(row=1, col=0, title="Canal EMG (Ajustable)")
        self.p_emg.showGrid(x=True, y=True)
        self.p_emg.setLabel('left', 'Amplitud', units='uV')
        self.p_emg.setLabel('bottom', 'Tiempo', units='s')
        self.curve_emg = self.p_emg.plot(pen=pg.mkPen('#d62728', width=1.5))
        
        # Vincular zoom y desplazamiento horizontal entre ambos paneles
        self.p_emg.setXLink(self.p_ecg)
        
        # Indicador de posición actual (Cursor sincronizado)
        self.v_line_ecg = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('g', style=pg.QtCore.Qt.DashLine))
        self.v_line_emg = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('g', style=pg.QtCore.Qt.DashLine))
        self.p_ecg.addItem(self.v_line_ecg)
        self.p_emg.addItem(self.v_line_emg)

    def set_ecg_data(self, signal: np.ndarray, fs: float):
        t = np.arange(len(signal)) / fs
        self.curve_ecg.setData(t, signal)

    def set_emg_data(self, signal: np.ndarray, fs: float, offset_sec: float = 0.0):
        t = (np.arange(len(signal)) / fs) + offset_sec
        self.curve_emg.setData(t, signal)

    def update_cursor_position(self, pos_sec: float):
        self.v_line_ecg.setValue(pos_sec)
        self.v_line_emg.setValue(pos_sec)