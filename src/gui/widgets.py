import numpy as np
import pyqtgraph as pg
from PyQt5.QtWidgets import QWidget, QVBoxLayout

class MultiChannelPlotWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        # Crear vista de gráficos pyqtgraph
        self.win = pg.GraphicsLayoutWidget()
        layout.addWidget(self.win)

        # Gráfica ECG
        self.plot_ecg = self.win.addPlot(title="Canal ECG (Referencia + Eventos)")
        self.plot_ecg.showGrid(x=True, y=True)

        self.win.nextRow()

        # Gráfica EMG
        self.plot_emg = self.win.addPlot(title="Canal EMG (Ajustable)")
        self.plot_emg.showGrid(x=True, y=True)

        # Enlazar ejes X para zoom sincronizado
        self.plot_emg.setXLink(self.plot_ecg)

        # Variables internas de estado
        self.ecg_signal = None
        self.ecg_fs = 1000.0
        self.annotations = []
        self.current_offset = 0.0

    def set_ecg_data(self, signal, fs):
        """Guarda la señal de ECG y refresca el gráfico."""
        self.ecg_signal = signal
        self.ecg_fs = fs
        self.update_ecg_plot()

    def draw_annotations(self, annotations):
        """Dibuja las marcas de eventos en su tiempo real sobre la señal de ECG."""
        self.plot_ecg.clear()
        
        # Volver a pintar el ECG si existe
        if self.ecg_signal is not None and len(self.ecg_signal) > 0:
            time = [i / self.ecg_fs for i in range(len(self.ecg_signal))]
            self.plot_ecg.plot(time, self.ecg_signal, pen=pg.mkPen('c', width=1))

        if not annotations:
            return

        for ann in annotations:
            # Las marcas pertenecen al eje de tiempo del ECG (no se desplazan con el offset)
            pos_x = ann['onset']
            
            # Línea vertical
            line = pg.InfiniteLine(
                pos=pos_x, 
                angle=90, 
                pen=pg.mkPen(color='y', style=pg.QtCore.Qt.DashLine, width=1.5)
            )
            self.plot_ecg.addItem(line)

            # Etiqueta textual (t0, t1...)
            text = pg.TextItem(text=str(ann['description']), color='y', anchor=(0, 1))
            text.setPos(pos_x, 0)
            self.plot_ecg.addItem(text)

    def set_emg_data(self, signal, fs, offset=0.0):
        """Redibuja el canal EMG desplazando su eje X según el offset."""
        self.plot_emg.clear()
        if signal is not None and len(signal) > 0:
            time = [(i / fs) + offset for i in range(len(signal))]
            self.plot_emg.plot(time, signal, pen=pg.mkPen('r', width=1))
            
    def update_ecg_plot(self):
        """
        BARRE Y REDIBUJA EL PANEL ECG COMPLETO.
        Garantiza que no queden marcas viejas colgadas.
        """
        # 1. Limpieza absoluta del lienzo ECG
        self.plot_ecg.clear()

        # 2. Dibujar la señal de ECG si existe
        if self.ecg_signal is not None and len(self.ecg_signal) > 0:
            time = [i / self.ecg_fs for i in range(len(self.ecg_signal))]
            self.plot_ecg.plot(time, self.ecg_signal, pen=pg.mkPen('c', width=1))

        # 3. Dibujar las marcas amarillas de eventos actuales
        if self.annotations:
            for ann in self.annotations:
                pos_x = ann['onset'] - self.current_offset
                
                # Línea vertical
                line = pg.InfiniteLine(
                    pos=pos_x, 
                    angle=90, 
                    pen=pg.mkPen(color='y', style=pg.QtCore.Qt.DashLine, width=1.5)
                )
                self.plot_ecg.addItem(line)

                # Etiqueta de texto
                text = pg.TextItem(text=str(ann['description']), color='y', anchor=(0, 1))
                text.setPos(pos_x, 0)
                self.plot_ecg.addItem(text)