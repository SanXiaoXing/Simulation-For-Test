from __future__ import annotations

import os
from typing import Optional

from PyQt5 import QtCore, QtGui, QtWidgets

from ..models import HUDConfig, HUDMode, NetworkConfig
from ..sim_core import HUDSimulator


class HUDCanvas(QtWidgets.QWidget):
    """HUD绘制画布。"""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(800, 600)
        self.fp = None
        self.ws = None
        self.ti = None
        self.mode = HUDMode.AIR_TO_AIR
        self._bg = QtGui.QColor(10, 20, 10)
        self._fg = QtGui.QColor(0, 255, 0)

    def update_data(self, fp, ws, ti, mode: HUDMode) -> None:
        """更新绘制数据。"""

        self.fp = fp
        self.ws = ws
        self.ti = ti
        self.mode = mode
        self.update()

    def paintEvent(self, ev: QtGui.QPaintEvent) -> None:
        """绘制事件。"""

        p = QtGui.QPainter(self)
        p.fillRect(self.rect(), self._bg)
        p.setPen(QtGui.QPen(self._fg, 2))
        if not self.fp or not self.ws or not self.ti:
            p.drawText(20, 30, "HUD 初始化中...")
            return
        self._draw_common(p)
        if self.mode == HUDMode.AIR_TO_AIR:
            self._draw_aaa(p)
        elif self.mode == HUDMode.AIR_TO_GROUND:
            self._draw_aag(p)
        else:
            self._draw_aas(p)

    def _draw_common(self, p: QtGui.QPainter) -> None:
        """绘制通用元素。"""

        w = self.width(); h = self.height()
        p.drawText(20, 30, f"SPD {self.fp.airspeed_mps:.0f} m/s")
        p.drawText(20, 55, f"ALT {self.fp.altitude_m:.0f} m")
        p.drawText(20, 80, f"HDG {self.fp.heading_deg:.0f}°")
        p.drawText(20, 105, f"G {self.fp.g_load:.1f}")
        p.drawText(20, 130, f"AOA {self.fp.aoa_deg:.1f}°")
        p.drawText(w - 180, 30, f"WPN {self.ws.selected}:{self.ws.status}")
        p.drawText(w - 180, 55, f"LS {'YES' if self.ws.locked else 'NO'}")
        p.drawText(w - 180, 80, f"RNG {self.ws.min_range_m:.0f}-{self.ws.max_range_m:.0f}m")
        p.drawText(w - 180, 105, f"PERM {'YES' if self.ws.launch_perm else 'NO'}")
        p.drawText(w - 180, 130, f"AMMO {self.ws.ammo_left}")

    def _draw_aaa(self, p: QtGui.QPainter) -> None:
        """绘制空空模式。"""

        cx = self.width() // 2; cy = self.height() // 2
        p.drawEllipse(QtCore.QPoint(cx, cy + 80), 60, 60)
        p.drawText(cx - 40, cy + 160, "预测命中点")
        import math
        rad = math.radians(self.ti.target_bearing_deg)
        bx = cx + int(120 * math.cos(rad))
        by = cy + int(120 * math.sin(rad))
        p.drawRect(bx - 20, by - 20, 40, 40)
        p.drawText(bx - 25, by - 30, "雷达锁定")
        p.drawText(20, self.height() - 30, f"TGT {self.ti.target_distance_m:.0f}m | CLS {self.ti.closure_rate_mps:.0f}m/s | THR {self.ti.threat_level}")

    def _draw_aag(self, p: QtGui.QPainter) -> None:
        """绘制空地模式。"""

        w = self.width(); h = self.height()
        p.drawText(20, 155, f"DIVE {self.fp.dive_deg:.1f}°")
        p.drawText(20, 180, f"CLIMB {self.fp.climb_deg:.1f}°")
        p.drawText(w - 200, 155, f"MODE CCRP")
        p.drawText(w - 200, 180, f"AMMO {self.ws.ammo_left}")
        p.drawText(w - 200, 205, f"REL {'YES' if self.ws.launch_perm else 'NO'}")
        p.drawText(20, h - 55, f"NAV {self.ti.waypoint_distance_m:.0f}m | WARN {self.ti.threat_level}")
        p.drawText(20, h - 30, "地形回避")
        cx = w // 2; cy = h // 2
        p.drawLine(cx - 60, cy + 100, cx + 60, cy + 100)
        p.drawText(cx - 40, cy + 130, "弹着点预测")

    def _draw_aas(self, p: QtGui.QPainter) -> None:
        """绘制空海模式。"""

        w = self.width(); h = self.height()
        p.drawText(20, 155, f"FUEL {self.fp.fuel_kg:.0f}kg")
        p.drawText(w - 200, 155, f"SEASKIM ALT 50m")
        p.drawText(20, h - 55, f"THR {self.ti.threat_level} | OBS {'YES' if self.ti.sea_obstacle_warn else 'NO'}")
        p.drawText(20, h - 30, f"RNG {self.ws.min_range_m:.0f}-{self.ws.max_range_m:.0f}m PERM {'YES' if self.ws.launch_perm else 'NO'}")


class HUDMainWindow(QtWidgets.QMainWindow):
    """HUD主窗口。"""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("平视显示器接口特征仿真")
        self.resize(1200, 800)
        self.sim = HUDSimulator(HUDConfig())
        self.sim.frame_signal.connect(self._on_frame)
        self._build_ui()

    def _build_ui(self) -> None:
        """搭建界面。"""

        cw = QtWidgets.QWidget(); self.setCentralWidget(cw)
        layout = QtWidgets.QHBoxLayout(cw)
        left = QtWidgets.QVBoxLayout(); right = QtWidgets.QVBoxLayout()
        layout.addLayout(left, 3); layout.addLayout(right, 5)

        box_cfg = QtWidgets.QGroupBox("仿真与模式配置")
        form = QtWidgets.QFormLayout(box_cfg)
        self.spin_rate = QtWidgets.QDoubleSpinBox(); self.spin_rate.setRange(10.0, 240.0); self.spin_rate.setValue(60.0)
        self.combo_mode = QtWidgets.QComboBox(); self.combo_mode.addItems(["空空", "空地", "空海"]); self.combo_mode.currentIndexChanged.connect(self._on_mode_changed)
        form.addRow("更新频率(Hz)", self.spin_rate)
        form.addRow("模式", self.combo_mode)
        left.addWidget(box_cfg)

        box_net = QtWidgets.QGroupBox("仿真数据接口/带宽")
        nform = QtWidgets.QFormLayout(box_net)
        self.edit_host = QtWidgets.QLineEdit("127.0.0.1")
        self.spin_port = QtWidgets.QSpinBox(); self.spin_port.setRange(1, 65535); self.spin_port.setValue(9101)
        self.combo_proto = QtWidgets.QComboBox(); self.combo_proto.addItems(["udp", "tcp", "afdx", "fc"])
        self.spin_link = QtWidgets.QDoubleSpinBox(); self.spin_link.setRange(1e6, 1e9); self.spin_link.setDecimals(0); self.spin_link.setValue(100e6)
        self.edit_icd = QtWidgets.QLineEdit("")
        btn_icd = QtWidgets.QPushButton("选择ICD文件"); btn_icd.clicked.connect(self._select_icd)
        self.lbl_bw = QtWidgets.QLabel("带宽占用: 0.00%")
        nform.addRow("目标主机", self.edit_host)
        nform.addRow("目标端口", self.spin_port)
        nform.addRow("协议", self.combo_proto)
        nform.addRow("链路速率(bps)", self.spin_link)
        nform.addRow("ICD路径", self.edit_icd)
        nform.addRow("", btn_icd)
        nform.addRow("", self.lbl_bw)
        left.addWidget(box_net)

        hbtn = QtWidgets.QHBoxLayout()
        self.btn_start = QtWidgets.QPushButton("启动仿真"); self.btn_start.clicked.connect(self._on_start)
        self.btn_stop = QtWidgets.QPushButton("停止仿真"); self.btn_stop.setEnabled(False); self.btn_stop.clicked.connect(self._on_stop)
        hbtn.addWidget(self.btn_start); hbtn.addWidget(self.btn_stop)
        left.addLayout(hbtn)

        self.canvas = HUDCanvas(); right.addWidget(self.canvas, 1)
        self.log = QtWidgets.QTextEdit(); self.log.setReadOnly(True); right.addWidget(self.log)

    def _select_icd(self) -> None:
        """选择ICD文件。"""

        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "选择ICD文件", os.getcwd(), "JSON (*.json)")
        if path:
            self.edit_icd.setText(path)

    def _on_mode_changed(self, idx: int) -> None:
        """切换显示模式。"""

        m = [HUDMode.AIR_TO_AIR, HUDMode.AIR_TO_GROUND, HUDMode.AIR_TO_SEA][max(0, min(2, idx))]
        self.sim.cfg.mode = m
        self.canvas.mode = m

    def _on_start(self) -> None:
        """启动仿真。"""

        cfg = HUDConfig(update_hz=float(self.spin_rate.value()), mode=self.sim.cfg.mode)
        net = NetworkConfig(out_host=self.edit_host.text().strip() or "127.0.0.1", out_port=int(self.spin_port.value()), protocol=self.combo_proto.currentText(), link_speed_bps=float(self.spin_link.value()), icd_path=(self.edit_icd.text().strip() or None))
        self.sim.configure(cfg=cfg, net=net)
        self.sim.start()
        self.btn_start.setEnabled(False); self.btn_stop.setEnabled(True)
        self.log.append("[INFO] HUD仿真启动")

    def _on_stop(self) -> None:
        """停止仿真。"""

        self.sim.stop()
        self.btn_start.setEnabled(True); self.btn_stop.setEnabled(False)
        self.log.append("[INFO] HUD仿真停止")

    def _on_frame(self, frame: dict) -> None:
        """处理仿真帧。"""

        self.canvas.update_data(frame.get("fp"), frame.get("ws"), frame.get("ti"), self.sim.cfg.mode)
        self.lbl_bw.setText(f"带宽占用: {frame.get('bw_pct', 0.0):.2f}%")
