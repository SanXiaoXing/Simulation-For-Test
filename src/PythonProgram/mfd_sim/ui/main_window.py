from __future__ import annotations

import os
import math
from typing import Optional

from PyQt5 import QtCore, QtGui, QtWidgets

from src.PythonProgram.mfd_sim.models import MFDConfig, MFDMode, NetworkConfig
from src.PythonProgram.mfd_sim.sim_core import MFDSimulator


class MFDCanvas(QtWidgets.QWidget):
    """MFD绘制画布。"""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(900, 650)
        self.fp = None
        self.ws = None
        self.ti = None
        self.mode = MFDMode.AIR_TO_AIR
        self.page = "overview"
        self._bg = QtGui.QColor(8, 8, 10)
        self._fg = QtGui.QColor(0, 255, 0)

    def update_data(self, frame: dict, mode: MFDMode, page: str) -> None:
        """更新绘制数据。"""

        self.fp = frame.get("fp")
        self.ws = frame.get("ws")
        self.ti = frame.get("ti")
        self.mode = mode
        self.page = page
        self.update()

    def paintEvent(self, ev: QtGui.QPaintEvent) -> None:
        """绘制事件。"""

        p = QtGui.QPainter(self)
        p.fillRect(self.rect(), self._bg)
        if not self.fp or not self.ws or not self.ti:
            p.setPen(QtGui.QPen(self._fg, 2))
            p.drawText(20, 30, "MFD 初始化中...")
            return

        self._draw_common(p)
        if self.page == "overview":
            self._draw_overview(p)
        elif self.page == "air":
            self._draw_air(p)
        elif self.page == "ground":
            self._draw_ground(p)
        elif self.page == "sea":
            self._draw_sea(p)
        else:
            self._draw_external_video(p)

    def _draw_common(self, p: QtGui.QPainter) -> None:
        """绘制通用元素。"""

        w = self.width(); h = self.height()
        p.setPen(QtGui.QPen(self._fg, 2))
        p.drawText(20, 30, f"SPD {self.fp.airspeed_mps:.0f} m/s")
        p.drawText(20, 55, f"ALT {self.fp.altitude_m:.0f} m")
        p.drawText(20, 80, f"HDG {self.fp.heading_deg:.0f}°")
        p.drawText(20, 105, f"G {self.fp.g_load:.1f}")
        p.drawText(20, 130, f"AOA {self.fp.aoa_deg:.1f}°")
        p.drawText(20, 155, f"WPT {self.fp.waypoint_name} {self.fp.waypoint_distance_m:.0f}m")
        p.drawText(w - 260, 30, f"WPN {self.ws.selected}:{self.ws.status}")
        p.drawText(w - 260, 55, f"LOCK {'YES' if self.ws.locked else 'NO'}")
        p.drawText(w - 260, 80, f"AMMO MSL {self.ws.ammo_missile} | GUN {self.ws.ammo_gun}")
        p.drawText(w - 260, 105, f"PERM {'YES' if self.ws.launch_perm else 'NO'}")

    def _draw_overview(self, p: QtGui.QPainter) -> None:
        """集成显示页。"""

        w = self.width(); h = self.height(); cx = w // 2; cy = h // 2
        p.setPen(QtGui.QPen(self._fg, 2))
        p.drawText(cx - 60, 180, f"RADAR TRK {self.ti.radar_tracks}")
        p.drawText(cx - 60, 205, f"THR {self.ti.threat_level}")
        p.drawText(cx - 60, 230, f"TGT {self.ti.target_distance_m:.0f}m")
        p.drawEllipse(QtCore.QPoint(cx, cy), 140, 140)
        rad = math.radians(self.ti.target_bearing_deg)
        bx = cx + int(110 * math.cos(rad))
        by = cy + int(110 * math.sin(rad))
        color = QtGui.QColor(0, 255, 0) if self.ti.is_friend else QtGui.QColor(255, 0, 0)
        p.setPen(QtGui.QPen(color, 2))
        p.drawRect(bx - 16, by - 16, 32, 32)
        p.setPen(QtGui.QPen(self._fg, 1, QtCore.Qt.DashLine))
        p.drawLine(cx, cy, bx, by)

    def _draw_air(self, p: QtGui.QPainter) -> None:
        """空空模式页。"""

        w = self.width(); h = self.height(); cx = w // 2; cy = h // 2
        p.setPen(QtGui.QPen(self._fg, 2))
        p.drawText(20, h - 30, f"TGT {self.ti.target_distance_m:.0f}m | CLS {self.ti.closure_rate_mps:.0f}m/s")
        rad = math.radians(self.ti.target_bearing_deg)
        bx = cx + int(120 * math.cos(rad))
        by = cy + int(120 * math.sin(rad))
        color = QtGui.QColor(0, 255, 0) if self.ti.is_friend else QtGui.QColor(255, 0, 0)
        p.setPen(QtGui.QPen(color, 2))
        p.drawRect(bx - 20, by - 20, 40, 40)
        p.setPen(QtGui.QPen(self._fg, 2))
        if self.ws.locked:
            p.drawText(bx - 25, by - 30, "LOCK")

    def _draw_ground(self, p: QtGui.QPainter) -> None:
        """空地模式页。"""

        w = self.width(); h = self.height(); cx = w // 2; cy = h // 2
        p.setPen(QtGui.QPen(self._fg, 2))
        p.drawText(w - 260, 180, f"REL {'YES' if self.ws.launch_perm else 'NO'}")
        p.drawLine(cx - 60, cy + 100, cx + 60, cy + 100)
        p.drawText(cx - 40, cy + 130, "弹着点预测")

    def _draw_sea(self, p: QtGui.QPainter) -> None:
        """空海模式页。"""

        w = self.width(); h = self.height()
        p.setPen(QtGui.QPen(self._fg, 2))
        p.drawText(20, h - 55, f"THR {self.ti.threat_level}")
        p.drawText(20, h - 30, f"RADAR TRK {self.ti.radar_tracks}")

    def _draw_external_video(self, p: QtGui.QPainter) -> None:
        """外视频转发页（叠加占位）。"""

        w = self.width(); h = self.height()
        vw, vh = int(w * 0.9), int(h * 0.85)
        vx, vy = (w - vw) // 2, (h - vh) // 2
        rect = QtCore.QRect(vx, vy, vw, vh)
        grad = QtGui.QLinearGradient(vx, vy, vx, vy + vh)
        grad.setColorAt(0.0, QtGui.QColor(20, 20, 30))
        grad.setColorAt(1.0, QtGui.QColor(0, 0, 0))
        p.fillRect(rect, QtGui.QBrush(grad))
        p.setPen(QtGui.QPen(self._fg, 2))
        p.drawRect(rect)
        p.drawText(vx + 10, vy + 25, "EXTERNAL VIDEO FORWARDING")


class MFDMainWindow(QtWidgets.QMainWindow):
    """MFD主窗口。"""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("多功能显示器接口特征仿真")
        self.resize(1280, 860)
        self.sim = MFDSimulator(MFDConfig())
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
        self.spin_rate = QtWidgets.QDoubleSpinBox(); self.spin_rate.setRange(10.0, 240.0); self.spin_rate.setValue(30.0)
        self.combo_mode = QtWidgets.QComboBox(); self.combo_mode.addItems(["空空", "空地", "空海"]); self.combo_mode.currentIndexChanged.connect(self._on_mode_changed)
        form.addRow("更新频率(Hz)", self.spin_rate)
        form.addRow("模式", self.combo_mode)
        left.addWidget(box_cfg)

        box_net = QtWidgets.QGroupBox("仿真数据接口/带宽")
        nform = QtWidgets.QFormLayout(box_net)
        self.edit_host = QtWidgets.QLineEdit("127.0.0.1")
        self.spin_port = QtWidgets.QSpinBox(); self.spin_port.setRange(1, 65535); self.spin_port.setValue(9201)
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

        box_ops = QtWidgets.QGroupBox("交互与操作")
        hbtn = QtWidgets.QHBoxLayout(box_ops)
        self.btn_start = QtWidgets.QPushButton("启动仿真"); self.btn_start.clicked.connect(self._on_start)
        self.btn_stop = QtWidgets.QPushButton("停止仿真"); self.btn_stop.setEnabled(False); self.btn_stop.clicked.connect(self._on_stop)
        self.btn_lock = QtWidgets.QPushButton("切换锁定"); self.btn_lock.clicked.connect(self._on_toggle_lock)
        self.btn_wp = QtWidgets.QPushButton("下一航路点"); self.btn_wp.clicked.connect(self._on_next_wp)
        hbtn.addWidget(self.btn_start); hbtn.addWidget(self.btn_stop); hbtn.addWidget(self.btn_lock); hbtn.addWidget(self.btn_wp)
        left.addWidget(box_ops)

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.addTab(QtWidgets.QWidget(), "集成显示")
        self.tabs.addTab(QtWidgets.QWidget(), "空空")
        self.tabs.addTab(QtWidgets.QWidget(), "空地")
        self.tabs.addTab(QtWidgets.QWidget(), "空海")
        self.tabs.addTab(QtWidgets.QWidget(), "外视频")
        self.tabs.currentChanged.connect(self._on_page_changed)
        right.addWidget(self.tabs)

        self.canvas = MFDCanvas(); right.addWidget(self.canvas, 1)
        self.log = QtWidgets.QTextEdit(); self.log.setReadOnly(True); right.addWidget(self.log)

    def _select_icd(self) -> None:
        """选择ICD文件。"""

        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "选择ICD文件", os.getcwd(), "JSON (*.json)")
        if path:
            self.edit_icd.setText(path)

    def _on_mode_changed(self, idx: int) -> None:
        """切换显示模式。"""

        m = [MFDMode.AIR_TO_AIR, MFDMode.AIR_TO_GROUND, MFDMode.AIR_TO_SEA][max(0, min(2, idx))]
        self.sim.cfg.mode = m

    def _on_page_changed(self, idx: int) -> None:
        """切换显示页。"""

        pages = ["overview", "air", "ground", "sea", "external"]
        self.sim.set_page(pages[max(0, min(4, idx))])

    def _on_toggle_lock(self) -> None:
        """交互：切换锁定。"""

        self.sim.toggle_lock()

    def _on_next_wp(self) -> None:
        """交互：下一航路点。"""

        self.sim.next_waypoint()

    def _on_start(self) -> None:
        """启动仿真。"""

        cfg = MFDConfig(update_hz=float(self.spin_rate.value()), mode=self.sim.cfg.mode)
        net = NetworkConfig(out_host=self.edit_host.text().strip() or "127.0.0.1", out_port=int(self.spin_port.value()), protocol=self.combo_proto.currentText(), link_speed_bps=float(self.spin_link.value()), icd_path=(self.edit_icd.text().strip() or None))
        self.sim.configure(cfg=cfg, net=net)
        self.sim.start()
        self.btn_start.setEnabled(False); self.btn_stop.setEnabled(True)
        self.log.append("[INFO] MFD仿真启动")

    def _on_stop(self) -> None:
        """停止仿真。"""

        self.sim.stop()
        self.btn_start.setEnabled(True); self.btn_stop.setEnabled(False)
        self.log.append("[INFO] MFD仿真停止")

    def _on_frame(self, frame: dict) -> None:
        """处理仿真帧。"""

        self.canvas.update_data(frame, self.sim.cfg.mode, frame.get("page", "overview"))
        self.lbl_bw.setText(f"带宽占用: {frame.get('bw_pct', 0.0):.2f}%")

