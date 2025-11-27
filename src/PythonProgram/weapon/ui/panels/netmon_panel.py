"""网络/总线监控面板。"""

from __future__ import annotations

from PyQt5 import QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from sim_core.bus import BusSimulator


class NetMonPanel(QtWidgets.QWidget):
    """显示带宽占用与丢包率图表。"""

    def __init__(self, bus_1553: BusSimulator, bus_can: BusSimulator, bus_udp: BusSimulator) -> None:
        super().__init__()
        self._b1 = bus_1553
        self._b2 = bus_can
        self._b3 = bus_udp
        self._fig = Figure(figsize=(6, 4))
        self._canvas = FigureCanvas(self._fig)
        self._ax = self._fig.add_subplot(111)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("带宽占用率时序曲线"))
        layout.addWidget(self._canvas)

    def refresh(self) -> None:
        """刷新图表数据为折线图。"""

        self._ax.clear()
        self._ax.plot(self._b1.stats.history_ts, self._b1.stats.history_bytes, label="1553B")
        self._ax.plot(self._b2.stats.history_ts, self._b2.stats.history_bytes, label="CAN")
        self._ax.plot(self._b3.stats.history_ts, self._b3.stats.history_bytes, label="UDP")
        self._ax.set_ylabel("Bytes")
        self._ax.set_xlabel("Time")
        self._ax.legend(loc="upper left")
        self._canvas.draw()
