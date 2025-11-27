"""主窗口实现。

提供菜单栏、地图视图与视频面板，并内置仿真循环与运行控制。
"""

from __future__ import annotations

from typing import List, Tuple

from pathlib import Path

import math
import yaml

from PyQt5 import QtWidgets, QtCore

from .map_view import MapView
from .video_panel import VideoPanel

from sim.target_generator import TargetGenerator, Target
from sim.sensor_node import SensorNode
from sim.tracker import Tracker


class MainWindow(QtWidgets.QMainWindow):
    """主窗口类。

    提供基本菜单与三栏布局：左侧控制、中心地图、右侧数据面板。
    内置加载示例场景与定时仿真循环，实时更新地图显示。
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("分布式孔径仿真器")
        self.resize(1200, 800)

        # 菜单栏
        menubar = self.menuBar()
        file_menu = menubar.addMenu("文件")
        run_menu = menubar.addMenu("运行")
        tools_menu = menubar.addMenu("工具")

        act_start = run_menu.addAction("开始")
        act_pause = run_menu.addAction("暂停")
        act_stop = run_menu.addAction("停止")
        act_start.triggered.connect(self._on_start)
        act_pause.triggered.connect(self._on_pause)
        act_stop.triggered.connect(self._on_stop)

        # 中心部件
        central = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(central)

        self.map_view = MapView()
        self.video_panel = VideoPanel()

        layout.addWidget(self.map_view, 2)
        layout.addWidget(self.video_panel, 1)
        self.setCentralWidget(central)

        # 状态栏
        self.statusBar().showMessage("就绪")

        # 仿真状态
        self._running = True
        self._sim_time_s = 0.0
        self._dt_s = 0.5

        # 加载场景并初始化模块
        self._tg = TargetGenerator()
        self._sensors: List[SensorNode] = []
        self._tracker = Tracker(gate_threshold_m=200.0)
        self._load_scenario()

        # 定时器驱动仿真
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._step_sim)
        self._timer.start()

    def _load_scenario(self) -> None:
        """加载示例场景。

        优先加载 `scenarios/scenario_a.yaml`，若失败则使用内置默认场景。
        """

        try:
            scen_path = Path(__file__).resolve().parents[1] / "scenarios" / "scenario_a.yaml"
            data = yaml.safe_load(scen_path.read_text(encoding="utf-8"))
            self._dt_s = float(data.get("time_step_s", 0.5))
            # 传感器
            self._sensors.clear()
            for s in data.get("sensors", []):
                self._sensors.append(
                    SensorNode(
                        sensor_id=s["sensor_id"],
                        x_m=float(s["x_m"]),
                        y_m=float(s["y_m"]),
                        z_m=float(s.get("z_m", 0.0)),
                        fov_deg=float(s.get("fov_deg", 120.0)),
                    )
                )
            # 目标
            for t in data.get("targets", []):
                self._tg.add_target(
                    Target(
                        target_id=t["target_id"],
                        x_m=float(t["x_m"]),
                        y_m=float(t["y_m"]),
                        z_m=float(t.get("z_m", 0.0)),
                        vx_mps=float(t["vx_mps"]),
                        vy_mps=float(t["vy_mps"]),
                    )
                )
        except Exception:
            # 内置默认
            self._dt_s = 0.5
            self._sensors = [
                SensorNode("SENSOR_01", 0.0, 0.0, 0.0, fov_deg=120.0),
                SensorNode("SENSOR_02", 2000.0, 500.0, 0.0, fov_deg=120.0),
            ]
            self._tg.add_target(Target("TGT_1", 5000.0, 0.0, 1000.0, -200.0, 0.0))
            self._tg.add_target(Target("TGT_2", 6000.0, 500.0, 1000.0, -180.0, -10.0))

    def _on_start(self) -> None:
        """开始仿真。"""

        self._running = True
        self.statusBar().showMessage("运行中")

    def _on_pause(self) -> None:
        """暂停仿真。"""

        self._running = False
        self.statusBar().showMessage("已暂停")

    def _on_stop(self) -> None:
        """停止并复位仿真。"""

        self._running = False
        self._sim_time_s = 0.0
        self._tg = TargetGenerator()
        self._tracker = Tracker(gate_threshold_m=200.0)
        self._load_scenario()
        self.statusBar().showMessage("已停止")

    def _step_sim(self) -> None:
        """定时推进仿真并刷新显示。"""

        if not self._running:
            return

        # 推进目标
        self._tg.step(self._dt_s)
        targets = self._tg.list_targets()

        # 生成观测并做平面位置反演
        obs_xy: List[Tuple[float, float]] = []
        for s in self._sensors:
            obs = s.observe(targets)
            for o in obs:
                # 仅用平面方位与距离反演坐标
                rad = math.radians(o.az_deg)
                x = s.x_m + o.range_m * math.cos(rad)
                y = s.y_m + o.range_m * math.sin(rad)
                obs_xy.append((x, y))

        # 跟踪器预测与更新
        self._tracker.predict(self._dt_s)
        if obs_xy:
            self._tracker.update(obs_xy)

        tracks = self._tracker.get_tracks()

        # 更新视图
        sensors_xy = [(s.x_m, s.y_m) for s in self._sensors]
        targets_xy = [(t.x_m, t.y_m) for t in targets]
        tracks_xy = [(tr.x_m, tr.y_m) for tr in tracks]
        self.map_view.update_scene(sensors_xy, targets_xy, tracks_xy)

        # 状态栏信息
        self._sim_time_s += self._dt_s
        self.statusBar().showMessage(
            f"t={self._sim_time_s:.1f}s  传感器:{len(sensors_xy)}  目标:{len(targets_xy)}  轨迹:{len(tracks_xy)}"
        )
