#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：Simulation 
@File    ：radar_simulation.py
@Author  ：SanXiaoXing
@Date    ：2025/11/20
@Description: 
"""

import sys
import math
import random
import time
from dataclasses import dataclass
from typing import List, Dict, Optional
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QComboBox, QSpinBox, QLineEdit,
    QTextEdit, QGroupBox, QFormLayout
)
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# ----------------------------- Data classes -----------------------------
@dataclass
class ImageTarget:
    id: int
    type: int
    distance_m: float
    azimuth_deg: float
    frequency_hz: float
    distance_30ms_m: float
    azimuth_30ms_deg: float
    speed_m_s: float
    direction_deg: float

@dataclass
class RadarTarget:
    id: int
    distance_m: float
    azimuth_deg: float
    rcs_db: float
    velocity_m_s: float

@dataclass
class Track:
    id: int
    distance_m: float
    azimuth_deg: float
    speed_m_s: float
    last_update: float
    source: str = "fused"
    rcs_db: Optional[float] = None
    threat_score: float = 0.0

# ----------------------------- Simulation core -----------------------------
class RadarSimulatorCore:
    def __init__(self, max_image=8, max_radar=8):
        self.max_image = max_image
        self.max_radar = max_radar
        self.frame_time = 0.03  # 30 ms default frame interval
        self.tracks: Dict[int, Track] = {}
        self.frame_counter = 0
        self.mode = "Search"  # default mode
        random.seed(0)

    def generate_image_targets(self)->List[ImageTarget]:
        n = random.randint(0, self.max_image)
        targets = []
        for i in range(n):
            tid = random.randint(100, 250)
            distance = random.uniform(1000, 40000)  # meters
            az = random.uniform(0, 360)
            speed = random.uniform(0, 300)
            dir_deg = random.uniform(0, 360)
            freq = random.choice([0.0, 1.2e9, 2.4e9, 5.8e9])
            d30 = max(0.0, distance - speed * 0.03)
            az30 = (az + (speed/1000.0)*0.03*360) % 360
            targets.append(ImageTarget(
                id=tid, type=random.choice([1,2,3]), distance_m=distance,
                azimuth_deg=az, frequency_hz=freq, distance_30ms_m=d30,
                azimuth_30ms_deg=az30, speed_m_s=speed, direction_deg=dir_deg
            ))
        return targets

    def generate_radar_targets(self)->List[RadarTarget]:
        m = random.randint(0, self.max_radar)
        targets = []
        for i in range(m):
            tid = random.randint(100, 250)
            distance = random.uniform(500, 50000)
            az = random.uniform(0, 360)
            vel = random.uniform(-200, 400)
            rcs = random.uniform(-20, 20)
            targets.append(RadarTarget(id=tid, distance_m=distance,
                                       azimuth_deg=az, rcs_db=rcs,
                                       velocity_m_s=vel))
        return targets

    def fuse_and_track(self, image_targets:List[ImageTarget], radar_targets:List[RadarTarget]):
        timestamp = time.time()
        updated_ids = set()
        radar_by_id = {r.id: r for r in radar_targets}

        # process image targets
        for it in image_targets:
            if it.id in self.tracks:
                t = self.tracks[it.id]
                alpha = 0.6
                t.distance_m = alpha*it.distance_m + (1-alpha)*t.distance_m
                t.azimuth_deg = (alpha*it.azimuth_deg + (1-alpha)*t.azimuth_deg) % 360
                t.speed_m_s = alpha*it.speed_m_s + (1-alpha)*t.speed_m_s
                t.last_update = timestamp
                t.source = "image"
                updated_ids.add(it.id)
            else:
                r = radar_by_id.get(it.id)
                t = Track(id=it.id, distance_m=it.distance_m, azimuth_deg=it.azimuth_deg,
                          speed_m_s=it.speed_m_s, last_update=timestamp, source="image",
                          rcs_db=(r.rcs_db if r else None))
                self.tracks[it.id] = t
                updated_ids.add(it.id)

        # process radar targets
        for rt in radar_targets:
            if rt.id in self.tracks:
                t = self.tracks[rt.id]
                alpha = 0.6
                t.distance_m = alpha*rt.distance_m + (1-alpha)*t.distance_m
                a1 = math.radians(t.azimuth_deg)
                a2 = math.radians(rt.azimuth_deg)
                x = math.cos(a1)*(1-alpha) + math.cos(a2)*alpha
                y = math.sin(a1)*(1-alpha) + math.sin(a2)*alpha
                t.azimuth_deg = (math.degrees(math.atan2(y,x)) + 360) % 360
                t.speed_m_s = alpha*rt.velocity_m_s + (1-alpha)*t.speed_m_s
                t.rcs_db = rt.rcs_db
                t.last_update = timestamp
                t.source = "radar"
                updated_ids.add(rt.id)
            else:
                t = Track(id=rt.id, distance_m=rt.distance_m, azimuth_deg=rt.azimuth_deg,
                          speed_m_s=rt.velocity_m_s, last_update=timestamp, source="radar",
                          rcs_db=rt.rcs_db)
                self.tracks[rt.id] = t
                updated_ids.add(rt.id)

        # merge close image->radar targets
        for it in image_targets:
            if it.id in updated_ids:
                continue
            best = None
            best_score = None
            for rt in radar_targets:
                d_dist = abs(it.distance_m - rt.distance_m) / max(1.0, (it.distance_m+rt.distance_m)/2.0)
                d_az = min(abs(it.azimuth_deg - rt.azimuth_deg), 360-abs(it.azimuth_deg-rt.azimuth_deg))/180.0
                score = d_dist + d_az
                if best_score is None or score < best_score:
                    best_score = score
                    best = rt
            if best and best_score < 0.15:
                if best.id in self.tracks:
                    t = self.tracks[best.id]
                    alpha = 0.5
                    t.distance_m = alpha*it.distance_m + (1-alpha)*t.distance_m
                    t.azimuth_deg = (alpha*it.azimuth_deg + (1-alpha)*t.azimuth_deg) % 360
                    t.speed_m_s = alpha*it.speed_m_s + (1-alpha)*t.speed_m_s
                    t.last_update = timestamp
                    t.source = "fused"
                    updated_ids.add(best.id)
                else:
                    self.tracks[best.id] = Track(id=best.id, distance_m=it.distance_m,
                                                 azimuth_deg=it.azimuth_deg, speed_m_s=it.speed_m_s,
                                                 last_update=timestamp, source="fused", rcs_db=best.rcs_db)
                    updated_ids.add(best.id)
            else:
                self.tracks[it.id] = Track(id=it.id, distance_m=it.distance_m,
                                           azimuth_deg=it.azimuth_deg, speed_m_s=it.speed_m_s,
                                           last_update=timestamp, source="image")
                updated_ids.add(it.id)

        # age-out
        ttl = 5.0
        stale_ids = [tid for tid,t in self.tracks.items() if (time.time() - t.last_update) > ttl]
        for sid in stale_ids:
            del self.tracks[sid]

        # threat scoring
        for tid, t in self.tracks.items():
            dist_score = max(0.0, 1.0 - (t.distance_m / 50000.0))
            speed_score = min(1.0, abs(t.speed_m_s) / 400.0)
            rcs_score = 0.5
            if t.rcs_db is not None:
                rcs_score = (t.rcs_db + 20.0) / 40.0
            mode_factor = 1.0
            if self.mode == "AirCombat":
                mode_factor = 1.5
            score = 0.6*dist_score + 0.3*speed_score + 0.1*rcs_score
            score *= mode_factor
            t.threat_score = max(0.0, min(1.5, score))

        self.frame_counter += 1
        return list(self.tracks.values())

    def handle_fire_control_request(self, requested_ids:List[int])->List[Dict]:
        responses = []
        for rid in requested_ids:
            if rid in self.tracks:
                t = self.tracks[rid]
                responses.append({"requested":rid, "selected":t.id, "distance_m":t.distance_m, "azimuth_deg":t.azimuth_deg, "status":"OK"})
            else:
                if not self.tracks:
                    responses.append({"requested":rid, "selected":None, "status":"NO_TARGET"})
                else:
                    best = min(self.tracks.values(), key=lambda x: x.distance_m)
                    responses.append({"requested":rid, "selected":best.id, "distance_m":best.distance_m, "azimuth_deg":best.azimuth_deg, "status":"FALLBACK"})
        return responses

# ----------------------------- GUI -----------------------------
class RadarCanvas(FigureCanvas):
    def __init__(self, parent=None, size=(5,5)):
        fig = Figure(figsize=size)
        self.ax = fig.add_subplot(111, projection='polar')
        super().__init__(fig)
        fig.tight_layout()
        self.ax.set_theta_zero_location("N")
        self.ax.set_theta_direction(-1)
        self.max_range = 50000.0
        self.scat = None

    def plot_tracks(self, tracks:List[Track]):
        self.ax.clear()
        self.ax.set_theta_zero_location("N")
        self.ax.set_theta_direction(-1)
        rs = []
        thetas = []
        labels = []
        sizes = []
        for t in tracks:
            r = t.distance_m
            theta = math.radians(t.azimuth_deg)
            rs.append(r)
            thetas.append(theta)
            labels.append(str(t.id))
            sizes.append(max(10, min(200, 200*(t.threat_score+0.1))))

        if rs:
            self.scat = self.ax.scatter(thetas, rs)
            for i,(th,r,label) in enumerate(zip(thetas,rs,labels)):
                self.ax.annotate(label, (th, r), textcoords="offset points", xytext=(5,5))
        self.ax.set_ylim(0, self.max_range)
        self.draw()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("雷达前端仿真器（PyQt5）")
        self.resize(1200, 700)
        self.core = RadarSimulatorCore(max_image=6, max_radar=6)
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        left = QVBoxLayout()
        main_layout.addLayout(left, 0)
        mode_box = QGroupBox("模式与控制")
        mlayout = QFormLayout()
        self.mode_cb = QComboBox()
        self.mode_cb.addItem("搜索", "Search")
        self.mode_cb.addItem("同时跟踪扫描", "TWS")
        self.mode_cb.addItem("单目标跟踪", "STT")
        self.mode_cb.addItem("空战", "AirCombat")
        self.mode_cb.addItem("海上搜索", "SeaSearch")
        self.mode_cb.addItem("地面地图", "GroundMap")
        self.mode_cb.currentIndexChanged.connect(self.on_mode_change_index)
        mlayout.addRow(QLabel("雷达模式："), self.mode_cb)
        self.frame_interval_spin = QSpinBox()
        self.frame_interval_spin.setRange(10, 1000)
        self.frame_interval_spin.setValue(30)
        self.frame_interval_spin.setSuffix(" ms")
        self.frame_interval_spin.valueChanged.connect(self.on_interval_change)
        mlayout.addRow(QLabel("帧间隔："), self.frame_interval_spin)
        self.start_btn = QPushButton("开始")
        self.start_btn.clicked.connect(self.on_start)
        self.stop_btn = QPushButton("停止")
        self.stop_btn.clicked.connect(self.on_stop)
        self.stop_btn.setEnabled(False)
        hb = QHBoxLayout()
        hb.addWidget(self.start_btn); hb.addWidget(self.stop_btn)
        mlayout.addRow(hb)
        mode_box.setLayout(mlayout)
        left.addWidget(mode_box)
        self.image_table = QTableWidget(0,9)
        self.image_table.setHorizontalHeaderLabels(["ID","类型","距离(米)","方位(度)","频率(Hz)","距离+30ms","方位+30ms","速度","方向"])
        self.radar_table = QTableWidget(0,5)
        self.radar_table.setHorizontalHeaderLabels(["ID","距离(米)","方位(度)","RCS(dB)","速度(m/s)"])
        left.addWidget(QLabel("图像目标："))
        left.addWidget(self.image_table, 1)
        left.addWidget(QLabel("雷达目标："))
        left.addWidget(self.radar_table, 1)
        fc_box = QGroupBox("火控请求")
        fcl = QVBoxLayout()
        self.fc_input = QLineEdit()
        self.fc_input.setPlaceholderText("请输入请求的目标ID，使用逗号分隔，例如 101,102")
        self.fc_send_btn = QPushButton("发送请求")
        self.fc_send_btn.clicked.connect(self.on_fc_request)
        self.fc_out = QTextEdit()
        self.fc_out.setReadOnly(True)
        fcl.addWidget(self.fc_input); fcl.addWidget(self.fc_send_btn); fcl.addWidget(self.fc_out)
        fc_box.setLayout(fcl)
        left.addWidget(fc_box, 1)
        right = QVBoxLayout()
        main_layout.addLayout(right, 1)
        self.canvas = RadarCanvas(self, size=(6,6))
        right.addWidget(self.canvas, 4)
        self.track_table = QTableWidget(0,7)
        self.track_table.setHorizontalHeaderLabels(["ID","距离(米)","方位(度)","速度(m/s)","RCS","来源","威胁值"])
        right.addWidget(QLabel("航迹（融合）："))
        right.addWidget(self.track_table, 3)
        self.status = QLabel("状态：已停止")
        right.addWidget(self.status)
        self.timer = QTimer()
        self.timer.timeout.connect(self.on_frame_tick)
        self.running = False
        self.mode_cn_map = {
            "Search": "搜索",
            "TWS": "同时跟踪扫描",
            "STT": "单目标跟踪",
            "AirCombat": "空战",
            "SeaSearch": "海上搜索",
            "GroundMap": "地面地图",
        }

    def on_mode_change(self, mode):
        self.core.mode = mode

    def on_mode_change_index(self, idx):
        self.core.mode = self.mode_cb.itemData(idx)

    def on_interval_change(self, val):
        self.core.frame_time = val/1000.0

    def on_start(self):
        self.running = True
        self.timer.start(self.frame_interval_spin.value())
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status.setText("状态：运行中")

    def on_stop(self):
        self.running = False
        self.timer.stop()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status.setText("状态：已停止")

    def on_frame_tick(self):
        image_targets = self.core.generate_image_targets()
        radar_targets = self.core.generate_radar_targets()
        self.update_image_table(image_targets)
        self.update_radar_table(radar_targets)
        tracks = self.core.fuse_and_track(image_targets, radar_targets)
        self.update_track_table(tracks)
        self.canvas.plot_tracks(tracks)
        mode_cn = self.mode_cn_map.get(self.core.mode, self.core.mode)
        self.status.setText(f"状态：运行中 | 模式：{mode_cn} | 帧：{self.core.frame_counter} | 航迹：{len(tracks)}")

    def update_image_table(self, image_targets:List[ImageTarget]):
        self.image_table.setRowCount(len(image_targets))
        for i, it in enumerate(image_targets):
            vals = [it.id, it.type, f"{it.distance_m:.1f}", f"{it.azimuth_deg:.1f}", f"{it.frequency_hz:.1e}", f"{it.distance_30ms_m:.1f}", f"{it.azimuth_30ms_deg:.2f}", f"{it.speed_m_s:.1f}", f"{it.direction_deg:.1f}"]
            for j,v in enumerate(vals):
                item = QTableWidgetItem(str(v))
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.image_table.setItem(i,j,item)

    def update_radar_table(self, radar_targets:List[RadarTarget]):
        self.radar_table.setRowCount(len(radar_targets))
        for i, rt in enumerate(radar_targets):
            vals = [rt.id, f"{rt.distance_m:.1f}", f"{rt.azimuth_deg:.1f}", f"{rt.rcs_db:.1f}", f"{rt.velocity_m_s:.1f}"]
            for j,v in enumerate(vals):
                item = QTableWidgetItem(str(v))
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.radar_table.setItem(i,j,item)

    def update_track_table(self, tracks:List[Track]):
        self.track_table.setRowCount(len(tracks))
        for i,t in enumerate(tracks):
            source_cn = {"image":"图像","radar":"雷达","fused":"融合"}.get(t.source, t.source)
            rcs_str = f"{t.rcs_db:.1f}" if t.rcs_db is not None else "无"
            vals = [t.id, f"{t.distance_m:.1f}", f"{t.azimuth_deg:.2f}", f"{t.speed_m_s:.1f}", rcs_str, source_cn, f"{t.threat_score:.3f}"]
            for j,v in enumerate(vals):
                item = QTableWidgetItem(str(v))
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.track_table.setItem(i,j,item)

    def on_fc_request(self):
        text = self.fc_input.text().strip()
        if not text:
            return
        try:
            ids = [int(x.strip()) for x in text.split(",") if x.strip()!='']
        except ValueError:
            self.fc_out.append("输入格式无效。请使用逗号分隔的ID。")
            return
        responses = self.core.handle_fire_control_request(ids)
        for r in responses:
            status_map = {"OK":"正常","NO_TARGET":"无目标","FALLBACK":"回退选择"}
            status_cn = status_map.get(r.get("status"), r.get("status"))
            sel = r.get("selected")
            dist = r.get("distance_m")
            az = r.get("azimuth_deg")
            dist_str = f"{dist:.1f}" if (dist is not None and sel is not None) else "-"
            az_str = f"{az:.1f}" if (az is not None and sel is not None) else "-"
            self.fc_out.append(f"请求ID: {r.get('requested')} | 选择ID: {sel if sel is not None else '-'} | 距离(米): {dist_str} | 方位(度): {az_str} | 状态: {status_cn}")

def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
