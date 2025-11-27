"""主窗口实现。"""

from __future__ import annotations

from typing import List, Tuple
from pathlib import Path
import math
import yaml

try:
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover
    np = None  # type: ignore

from PyQt5 import QtWidgets, QtCore

from sim.target_gen import TargetGenerator, Target
from sim.irst_sensor import IrstSensor
from sim.detector import detections_to_boxes
from sim.laser_ranger import simulate_range
from sim.fusion import azel_range_to_xy
from sim.tracker import Tracker
from sim.config import load_cfg, CfgBundle

from ui.video_view import VideoView
from ui.dashboard import Dashboard


class MainWindow(QtWidgets.QMainWindow):
    """IRST 仿真主窗口。"""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("IRST 前端仿真")
        self.resize(1200, 800)

        menubar = self.menuBar()
        m_run = menubar.addMenu("运行")
        act_start = m_run.addAction("开始")
        act_pause = m_run.addAction("暂停")
        act_stop = m_run.addAction("停止")
        act_start.triggered.connect(self._on_start)
        act_pause.triggered.connect(self._on_pause)
        act_stop.triggered.connect(self._on_stop)

        central = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(central)
        self.video = VideoView((640, 480))
        self.dashboard = Dashboard()
        layout.addWidget(self.video, 2)
        layout.addWidget(self.dashboard, 1)
        self.setCentralWidget(central)

        self._running = True
        self._sim_t = 0.0
        # 加载配置与初始化传感器
        cfg_path = Path(__file__).resolve().parents[1] / "scenarios" / "config.yaml"
        self._cfg: CfgBundle = load_cfg(cfg_path)
        self._dt_s = self._cfg.sim.dt_s
        self._sensor = IrstSensor(
            "IRST_FWD_01",
            0.0,
            0.0,
            0.0,
            fov_deg=self._cfg.sensor.fov_deg,
            resolution=self._cfg.sensor.resolution,
            angle_noise_deg=self._cfg.sensor.angle_noise_deg,
        )
        self._tg = TargetGenerator()
        self._tracker = Tracker(gate_m=300.0)
        self._enable_laser = self._cfg.sim.enable_laser
        self._load_scenario()

        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(10)
        self._timer.timeout.connect(self._step)
        self._timer.start()

        self.statusBar().showMessage("就绪")

    def _load_scenario(self) -> None:
        """加载场景或使用默认。"""

        try:
            p = Path(__file__).resolve().parents[1] / "scenarios" / "scenario_a.yaml"
            data = yaml.safe_load(p.read_text(encoding="utf-8"))
            self._dt_s = float(data.get("time_step_s", 0.05))
            for t in data.get("targets", []):
                self._tg.add(Target(t["target_id"], float(t["x_m"]), float(t["y_m"]), float(t.get("z_m", 0.0)), float(t["vx_mps"]), float(t["vy_mps"]), float(t.get("ir_signature", 0.7)), float(t.get("stealth_level", 0.0))))
        except Exception:
            self._tg.add(Target("T1", 5000.0, 0.0, 0.0, -250.0, 0.0, 0.8, 0.2))
            self._tg.add(Target("T2", 6000.0, 600.0, 0.0, -220.0, -20.0, 0.7, 0.0))

    def _on_start(self) -> None:
        """开始仿真。"""

        self._running = True
        self.statusBar().showMessage("运行中")

    def _on_pause(self) -> None:
        """暂停仿真。"""

        self._running = False
        self.statusBar().showMessage("已暂停")

    def _on_stop(self) -> None:
        """停止并重置。"""

        self._running = False
        self._sim_t = 0.0
        self._tg = TargetGenerator()
        self._tracker = Tracker(gate_m=300.0)
        self._load_scenario()
        self.statusBar().showMessage("已停止")

    def _make_heat_image(self, dets) -> "np.ndarray":
        """生成热像图像数组。"""

        if np is None:
            return None  # type: ignore
        h, w = self._sensor.resolution[1], self._sensor.resolution[0]
        img = np.random.randint(10, 20, (h, w), dtype=np.uint8)
        for d in dets:
            x, y = self._sensor.project_to_image(d.az_deg, d.el_deg)
            sz = 12
            x0 = max(0, x - sz)
            y0 = max(0, y - sz)
            x1 = min(w, x + sz)
            y1 = min(h, y + sz)
            img[y0:y1, x0:x1] = np.clip(img[y0:y1, x0:x1] + 80, 0, 255)
        return img

    def _step(self) -> None:
        """仿真步进并刷新显示。"""

        if not self._running:
            return
        self._tg.step(self._dt_s)
        targets = self._tg.list()
        dets = self._sensor.observe(targets)
        # 根据检测置信度阈值过滤
        dets = [d for d in dets if d.confidence >= self._cfg.detection.conf_threshold]

        xy_points: List[Tuple[float, float]] = []
        for d in dets:
            rng_m = 8000.0
            ok = True
            if self._enable_laser:
                rng_m, ok = simulate_range(
                    rng_m, accuracy_m=self._cfg.laser.accuracy_m, fail_prob=self._cfg.laser.fail_prob
                )
            if ok:
                xy = azel_range_to_xy((self._sensor.x_m, self._sensor.y_m), d.az_deg, d.el_deg, rng_m)
                xy_points.append(xy)

        self._tracker.update(xy_points)
        tracks = self._tracker.list()

        boxes = detections_to_boxes(self._sensor, dets, box_size=20)
        img = self._make_heat_image(dets)
        self.video.update_frame(img, boxes)

        rows = []
        for tr in tracks:
            threat = (
                "HIGH"
                if tr.confidence > self._cfg.threat.high_conf
                else ("MED" if tr.confidence > self._cfg.threat.med_conf else "LOW")
            )
            rows.append((tr.track_id, f"{tr.x_m:.1f}", f"{tr.y_m:.1f}", f"{tr.confidence:.2f}", threat))
        self.dashboard.update_tracks(rows)

        self._sim_t += self._dt_s
        self.statusBar().showMessage(f"t={self._sim_t:.2f}s det={len(dets)} trk={len(tracks)}")
