from typing import Optional
import logging
import math
import random
import numpy as np

from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QComboBox,
    QSpinBox,
    QDoubleSpinBox,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QGroupBox,
)
from PyQt5.QtCore import Qt, QTimer

try:
    import pyqtgraph as pg
except Exception:
    pg = None

from .models import (
    EWSignal,
    default_radar_library,
    default_comm_library,
    default_jam_modes,
)
from .simulator import EWSimulator
from .udp import UDPReceiver


class MainWindow(QMainWindow):
    """电子战仿真GUI主窗口。

    包含参数控制、实时表格与可选的波形/频谱显示，并与仿真引擎及UDP接收线程联动。

    Attributes:
        sim: 仿真实例。
        rx: UDP接收线程。
        table: 实时参数表。
        plot: 波形/频谱绘图部件（可选）。
    """

    def __init__(self) -> None:
        """构造GUI并初始化控件。"""

        super().__init__()
        self.setWindowTitle("EW 接口特征仿真")
        self.resize(1100, 700)

        self.sim: Optional[EWSimulator] = None
        self.rx: Optional[UDPReceiver] = None

        self._radars = default_radar_library()
        self._comms = default_comm_library()
        self._jams = default_jam_modes()

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        ctrl_group = QGroupBox("参数控制")
        ctrl_layout = QHBoxLayout(ctrl_group)
        layout.addWidget(ctrl_group)

        self.radar_combo = QComboBox()
        for r in self._radars:
            self.radar_combo.addItem(r["name"]) 

        self.comm_combo = QComboBox()
        for c in self._comms:
            self.comm_combo.addItem(c["name"]) 

        self.jam_combo = QComboBox()
        self.jam_combo.addItem("不启用干扰")
        for j in self._jams:
            self.jam_combo.addItem(j["name"]) 

        ctrl_layout.addWidget(QLabel("雷达源"))
        ctrl_layout.addWidget(self.radar_combo)
        ctrl_layout.addWidget(QLabel("通信源"))
        ctrl_layout.addWidget(self.comm_combo)
        ctrl_layout.addWidget(QLabel("干扰模式"))
        ctrl_layout.addWidget(self.jam_combo)

        self.start_btn = QPushButton("启动仿真")
        self.stop_btn = QPushButton("停止仿真")
        self.stop_btn.setEnabled(False)
        ctrl_layout.addWidget(self.start_btn)
        ctrl_layout.addWidget(self.stop_btn)

        self.table = QTableWidget(0, 12)
        self.table.setHorizontalHeaderLabels([
            "source_id",
            "type",
            "timestamp_ms",
            "center_freq_hz",
            "bandwidth_hz",
            "signal_power_dbm",
            "snr_db",
            "azimuth_deg",
            "elevation_deg",
            "range_m",
            "pri_ms",
            "pulse_width_us",
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, stretch=2)

        if pg is not None:
            plot_group = QGroupBox("波形/频谱显示")
            plot_layout = QVBoxLayout(plot_group)
            pg.setConfigOptions(antialias=True)
            self.plot = pg.PlotWidget()
            self.plot.showGrid(x=True, y=True)
            self.plot.setLabel("bottom", "样点")
            self.plot.setLabel("left", "幅度")
            self._n = 1024
            self._x = np.arange(self._n)
            self.curve = self.plot.plot(self._x, np.zeros(self._n), pen=pg.mkPen(color=(50, 170, 255), width=2))
            self.base_curve = self.plot.plot(self._x, np.zeros(self._n), pen=None)
            try:
                self.curve.setDownsampling(True, auto=True)
                self.curve.setClipToView(True)
            except Exception:
                pass
            try:
                self.fill = pg.FillBetweenItem(self.curve, self.base_curve, brush=pg.mkBrush(50, 170, 255, 60))
                self.plot.addItem(self.fill)
            except Exception:
                self.fill = None
            plot_layout.addWidget(self.plot)
            layout.addWidget(plot_group, stretch=1)
        else:
            self.plot = None

        self.start_btn.clicked.connect(self._on_start)
        self.stop_btn.clicked.connect(self._on_stop)

        self._pending_sig: Optional[EWSignal] = None
        self._update_timer = QTimer(self)
        self._update_timer.setInterval(50)
        self._update_timer.timeout.connect(self._on_update_timer)
        self._update_timer.start()
        self._auto_ranged = False
        logging.basicConfig(level=logging.INFO)

    def _on_start(self) -> None:
        """启动仿真与接收线程。"""

        radar_idx = self.radar_combo.currentIndex()
        comm_idx = self.comm_combo.currentIndex()
        jam_idx = self.jam_combo.currentIndex() - 1
        jam_idx = jam_idx if jam_idx >= 0 else None

        self.sim = EWSimulator(
            radar_index=radar_idx,
            comm_index=comm_idx,
            jam_index=jam_idx,
            enable_missile=False,
        )
        self.sim.start()

        self.rx = UDPReceiver(port=50000)
        self.rx.signal_received.connect(self._on_signal)
        self.rx.start()

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

    def _on_stop(self) -> None:
        """停止仿真与接收线程。"""

        try:
            if self.rx:
                self.rx.stop()
                self.rx.wait(1000)
                self.rx = None
            if self.sim:
                self.sim.stop()
                self.sim = None
        finally:
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)

    def _on_signal(self, sig: EWSignal) -> None:
        """接收信号回调，更新表格并刷新波形。"""

        row = self.table.rowCount()
        self.table.insertRow(row)
        values = [
            sig.source_id,
            int(sig.type),
            sig.timestamp_ms,
            f"{sig.center_freq_hz:.3f}",
            f"{sig.bandwidth_hz:.3f}",
            f"{sig.signal_power_dbm:.2f}",
            f"{sig.snr_db:.2f}",
            f"{sig.azimuth_deg:.2f}",
            f"{sig.elevation_deg:.2f}",
            f"{sig.range_m:.2f}",
            f"{sig.pri_ms:.3f}",
            f"{sig.pulse_width_us:.3f}",
        ]
        for col, val in enumerate(values):
            item = QTableWidgetItem(str(val))
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.table.setItem(row, col, item)
        self.table.scrollToBottom()

        if self.plot is not None:
            self._pending_sig = sig

    def _on_update_timer(self) -> None:
        if self.plot is None:
            return
        sig = self._pending_sig
        if sig is None:
            return
        self._pending_sig = None
        try:
            snr_lin = max(10 ** (sig.snr_db / 10.0), 1e-6)
            noise_std = 1.0 / (snr_lin ** 0.5)
            freq = 5.0
            amp = max(sig.signal_power_dbm / 10.0, 0.1)
            y = (amp * 0.7 * np.sin(2 * math.pi * freq * (self._x / self._n))) + np.random.uniform(-noise_std, noise_std, size=self._n)
            self.curve.setData(self._x, y)
            self.base_curve.setData(self._x, np.zeros(self._n))
            if not self._auto_ranged:
                try:
                    self.plot.autoRange()
                except Exception:
                    pass
                self._auto_ranged = True
        except Exception as e:
            logging.exception("plot update failed: %s", e)
            try:
                self.statusBar().showMessage("绘制异常，详见日志", 2000)
            except Exception:
                pass
