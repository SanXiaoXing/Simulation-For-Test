"""主窗口实现。"""

from __future__ import annotations

from PyQt5 import QtWidgets, QtCore
from pathlib import Path
import yaml

from sim_core.models import Rack, Ejector, Weapon, Fuze, WeaponSystem
from sim_core.release import ReleaseController
from sim_core.bus import BusConfig, BusSimulator
from protocols import ms1553

from .panels.status_panel import StatusPanel
from .panels.release_panel import ReleasePanel
from .panels.effect_panel import EffectPanel
from .panels.fault_panel import FaultPanel
from .panels.training_panel import TrainingPanel
from .panels.netmon_panel import NetMonPanel
from .panels.config_panel import ConfigPanel


class MainWindow(QtWidgets.QMainWindow):
    """武器外挂仿真主窗口。"""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("武器外挂接口特征模拟器")
        self.resize(1280, 900)

        # 初始化系统与释放控制
        rack = Rack("RACK_A", max_load_kg=500.0)
        ejector = Ejector("EJ_A", pressure_mpa=15.0)
        fuze = Fuze("FZ_A", sensitivity=0.7, anti_jam=0.6)
        weapon = Weapon("AIM-120", mass_kg=150.0, aerodynamic_mode="external", fuze=fuze)
        self.sys = WeaponSystem(rack, ejector, weapon)
        self.release = ReleaseController(self.sys)

        # 总线监控
        self.bus_1553 = BusSimulator(BusConfig("1553B", bandwidth_bps=1_000_000, frame_size_bytes=32, refresh_hz=50))
        self.bus_can = BusSimulator(BusConfig("CAN", bandwidth_bps=500_000, frame_size_bytes=16, refresh_hz=100))
        self.bus_udp = BusSimulator(BusConfig("UDP", bandwidth_bps=5_000_000, frame_size_bytes=512, refresh_hz=200))

        # 标签页
        tabs = QtWidgets.QTabWidget()
        self._tabs = tabs
        self.status_panel = StatusPanel(self.sys)
        self.release_panel = ReleasePanel(self.sys, self.release)
        self.effect_panel = EffectPanel(self.sys)
        self.fault_panel = FaultPanel(self.sys, self.release)
        self.training_panel = TrainingPanel(self.sys, self.release)
        self.netmon_panel = NetMonPanel(self.bus_1553, self.bus_can, self.bus_udp)
        self.config_panel = ConfigPanel(self.sys)

        tabs.addTab(self.status_panel, "主面板")
        tabs.addTab(self.release_panel, "释放控制")
        tabs.addTab(self.effect_panel, "效能仿真")
        tabs.addTab(self.fault_panel, "故障诊断")
        tabs.addTab(self.training_panel, "训练模式")
        tabs.addTab(self.netmon_panel, "网络/总线监控")
        tabs.addTab(self.config_panel, "系统配置")
        self.setCentralWidget(tabs)

        # 定时器：刷新状态与总线统计
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

        self.statusBar().showMessage("就绪")

    def _tick(self) -> None:
        """定时刷新状态与图表。"""

        # 温度更新与状态面板刷新
        self.sys.step_temperature(ambient_c=15.0)

        app = QtWidgets.QApplication.instance()
        if app and app.activePopupWidget() is not None:
            return

        current = self._tabs.currentWidget() if hasattr(self, "_tabs") else None
        if current is self.status_panel:
            self.status_panel.refresh()
        # 总线仿真：发送帧并统计错误
        payload = b"0123456789ABCDEF"
        if self.bus_1553.send_frame(len(payload)):
            frame = ms1553.encode(8, payload)
            _, ok = ms1553.decode(frame, ber=self.bus_1553.stats.bit_error_rate)
            if not ok:
                self.bus_1553.stats.errors += 1
        self.bus_can.send_frame(len(payload))
        self.bus_udp.send_frame(len(payload) * 2)
        # 图表刷新
        if current is self.netmon_panel:
            self.netmon_panel.refresh()
