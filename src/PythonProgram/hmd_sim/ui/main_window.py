from __future__ import annotations

import os
import math
from typing import Optional

from PyQt5 import QtCore, QtGui, QtWidgets

from ..models import HMDConfig, HMDMode, NetworkConfig
from ..sim_core import HMDSimulator


class HMDCanvas(QtWidgets.QWidget):
    """HMD绘制画布。"""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(900, 650)
        self.fp = None
        self.ws = None
        self.ti = None
        self.mode = HMDMode.AIR_TO_AIR
        self._bg = QtGui.QColor(10, 10, 20)
        self._fg = QtGui.QColor(0, 255, 0)

    def update_data(self, fp, ws, ti, mode: HMDMode) -> None:
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
        if not self.fp or not self.ws or not self.ti:
            p.setPen(QtGui.QPen(self._fg, 2))
            p.drawText(20, 30, "HMD 初始化中...")
            return

        self._draw_video(p)
        self._draw_common(p)
        if self.mode == HMDMode.AIR_TO_AIR:
            self._draw_aaa(p)
        elif self.mode == HMDMode.AIR_TO_GROUND:
            self._draw_aag(p)
        else:
            self._draw_aas(p)

    def _draw_video(self, p: QtGui.QPainter) -> None:
        """绘制视频叠加背景。"""

        w = self.width(); h = self.height()
        vw, vh = int(w * 0.9), int(h * 0.85)
        vx, vy = (w - vw) // 2, (h - vh) // 2
        rect = QtCore.QRect(vx, vy, vw, vh)
        grad = QtGui.QLinearGradient(vx, vy, vx, vy + vh)
        grad.setColorAt(0.0, QtGui.QColor(20, 20, 30))
        grad.setColorAt(1.0, QtGui.QColor(0, 0, 0))
        p.fillRect(rect, QtGui.QBrush(grad))
        p.setPen(QtGui.QPen(QtGui.QColor(0, 120, 0), 1, QtCore.Qt.DashLine))
        for i in range(10):
            y = vy + i * (vh // 10)
            p.drawLine(vx, y, vx + vw, y)
        p.setPen(QtGui.QPen(self._fg, 2))
        p.drawRect(rect)
        p.drawText(vx + 10, vy + 25, "VIDEO OVERLAY")

    def _draw_common(self, p: QtGui.QPainter) -> None:
        """绘制通用元素。"""

        w = self.width(); h = self.height()
        p.setPen(QtGui.QPen(self._fg, 2))
        p.drawText(20, 30, f"SPD {self.fp.airspeed_mps:.0f} m/s")
        p.drawText(20, 55, f"ALT {self.fp.altitude_m:.0f} m")
        p.drawText(20, 80, f"HDG {self.fp.heading_deg:.0f}°")
        p.drawText(20, 105, f"G {self.fp.g_load:.1f}")
        p.drawText(20, 130, f"AOA {self.fp.aoa_deg:.1f}°")
        p.drawText(w - 220, 30, f"WPN {self.ws.selected}:{self.ws.status}")
        p.drawText(w - 220, 55, f"LOCK {'YES' if self.ws.locked else 'NO'}")
        p.drawText(w - 220, 80, f"RNG {self.ws.min_range_m:.0f}-{self.ws.max_range_m:.0f}m")
        p.drawText(w - 220, 105, f"SHOOT {'YES' if self.ws.launch_perm else 'NO'}")
        p.drawText(w - 220, 130, f"AMMO {self.ws.ammo_left}")

    def _draw_aaa(self, p: QtGui.QPainter) -> None:
        """绘制空空模式。"""

        cx = self.width() // 2; cy = self.height() // 2
        # 导弹离轴发射范围环
        r = 120
        p.setPen(QtGui.QPen(self._fg, 2))
        p.drawEllipse(QtCore.QPoint(cx, cy), r, r)
        p.drawText(cx - 60, cy - r - 10, f"OBA {self.ws.off_boresight_deg:.0f}°")

        # 动态锁定框随头部转动：将头部偏航/俯仰映射到屏幕偏移
        ox = int(2.0 * self.fp.head_yaw_deg)
        oy = int(-2.0 * self.fp.head_pitch_deg)
        # 目标 bearing 影响锁定框额外偏移
        rad = math.radians(self.ti.target_bearing_deg)
        bx = cx + ox + int(80 * math.cos(rad))
        by = cy + oy + int(80 * math.sin(rad))
        color = QtGui.QColor(0, 255, 0) if self.ti.is_friend else QtGui.QColor(255, 0, 0)
        p.setPen(QtGui.QPen(color, 2))
        p.drawRect(bx - 20, by - 20, 40, 40)
        p.setPen(QtGui.QPen(self._fg, 2))
        if self.ws.locked:
            p.drawText(bx - 25, by - 30, "LOCK")
        if self.ws.launch_perm:
            p.drawText(bx - 25, by + 40, "SHOOT")
        p.drawText(20, self.height() - 30, f"TGT {self.ti.target_distance_m:.0f}m | CLS {self.ti.closure_rate_mps:.0f}m/s")

        # Rmax/Rne 文字提示
        p.drawText(cx - 40, cy + r + 25, f"Rmax {self.ws.rmax_m:.0f}m / Rne {self.ws.rne_m:.0f}m")

    def _draw_aag(self, p: QtGui.QPainter) -> None:
        """绘制空地模式。"""

        w = self.width(); h = self.height()
        p.drawText(20, 155, f"WPT {self.ti.waypoint_distance_m:.0f}m")
        p.drawText(w - 220, 155, f"MODE CCRP")
        p.drawText(w - 220, 180, f"REL {'YES' if self.ws.launch_perm else 'NO'}")
        p.drawText(20, h - 55, f"THR {self.ti.threat_level}")
        p.drawText(20, h - 30, "地形回避")
        cx = w // 2; cy = h // 2
        p.drawLine(cx - 60, cy + 100, cx + 60, cy + 100)
        p.drawText(cx - 40, cy + 130, "弹着点预测")

    def _draw_aas(self, p: QtGui.QPainter) -> None:
        """绘制空海模式。"""

        w = self.width(); h = self.height()
        p.drawText(20, 155, f"FUEL {self.fp.fuel_kg:.0f}kg")
        p.drawText(w - 220, 155, "SEASKIM ALT 50m")
        p.drawText(20, h - 55, f"THR {self.ti.threat_level} | OBS {'YES' if self.ti.sea_obstacle_warn else 'NO'}")
        p.drawText(20, h - 30, f"RNG {self.ws.min_range_m:.0f}-{self.ws.max_range_m:.0f}m PERM {'YES' if self.ws.launch_perm else 'NO'}")


class HMDMainWindow(QtWidgets.QMainWindow):
    """HMD主窗口。"""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("头盔显示器接口特征仿真")
        self.resize(1280, 820)
        self.sim = HMDSimulator(HMDConfig())
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
        self.spin_port = QtWidgets.QSpinBox(); self.spin_port.setRange(1, 65535); self.spin_port.setValue(9102)
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

        self.canvas = HMDCanvas(); right.addWidget(self.canvas, 1)
        self.log = QtWidgets.QTextEdit(); self.log.setReadOnly(True); right.addWidget(self.log)

    def _select_icd(self) -> None:
        """选择ICD文件。"""

        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "选择ICD文件", os.getcwd(), "JSON (*.json)")
        if path:
            self.edit_icd.setText(path)

    def _on_mode_changed(self, idx: int) -> None:
        """切换显示模式。"""

        m = [HMDMode.AIR_TO_AIR, HMDMode.AIR_TO_GROUND, HMDMode.AIR_TO_SEA][max(0, min(2, idx))]
        self.sim.cfg.mode = m
        self.canvas.mode = m

    def _on_start(self) -> None:
        """启动仿真。"""

        cfg = HMDConfig(update_hz=float(self.spin_rate.value()), mode=self.sim.cfg.mode)
        net = NetworkConfig(out_host=self.edit_host.text().strip() or "127.0.0.1", out_port=int(self.spin_port.value()), protocol=self.combo_proto.currentText(), link_speed_bps=float(self.spin_link.value()), icd_path=(self.edit_icd.text().strip() or None))
        self.sim.configure(cfg=cfg, net=net)
        self.sim.start()
        self.btn_start.setEnabled(False); self.btn_stop.setEnabled(True)
        self.log.append("[INFO] HMD仿真启动")

    def _on_stop(self) -> None:
        """停止仿真。"""

        self.sim.stop()
        self.btn_start.setEnabled(True); self.btn_stop.setEnabled(False)
        self.log.append("[INFO] HMD仿真停止")

    def _on_frame(self, frame: dict) -> None:
        """处理仿真帧。"""

        self.canvas.update_data(frame.get("fp"), frame.get("ws"), frame.get("ti"), self.sim.cfg.mode)
        self.lbl_bw.setText(f"带宽占用: {frame.get('bw_pct', 0.0):.2f}%")

