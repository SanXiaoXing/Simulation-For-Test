"""配置加载模块。

提供仿真、传感器、检测、激光与威胁等级的默认配置与 YAML 加载。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple
from pathlib import Path
import yaml


@dataclass
class SimCfg:
    """仿真基础配置。"""

    dt_s: float = 0.05
    enable_laser: bool = True


@dataclass
class SensorCfg:
    """传感器配置。"""

    fov_deg: float = 40.0
    resolution: Tuple[int, int] = (640, 480)
    angle_noise_deg: float = 0.1


@dataclass
class DetectionCfg:
    """检测配置。"""

    conf_threshold: float = 0.6


@dataclass
class LaserCfg:
    """激光测距配置。"""

    accuracy_m: float = 5.0
    fail_prob: float = 0.02


@dataclass
class ThreatCfg:
    """威胁等级阈值。"""

    high_conf: float = 0.85
    med_conf: float = 0.6


@dataclass
class CfgBundle:
    """完整配置包。"""

    sim: SimCfg
    sensor: SensorCfg
    detection: DetectionCfg
    laser: LaserCfg
    threat: ThreatCfg


def load_cfg(path: Path) -> CfgBundle:
    """从 YAML 文件加载配置（带默认）。

    Args:
        path: 配置文件路径。

    Returns:
        CfgBundle 对象，若文件不存在或解析失败则返回默认配置。
    """

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    sim = data.get("sim", {})
    sensor = data.get("sensor", {})
    detection = data.get("detection", {})
    laser = data.get("laser", {})
    threat = data.get("threat", {})
    return CfgBundle(
        sim=SimCfg(dt_s=float(sim.get("dt_s", 0.05)), enable_laser=bool(sim.get("enable_laser", True))),
        sensor=SensorCfg(
            fov_deg=float(sensor.get("fov_deg", 40.0)),
            resolution=tuple(sensor.get("resolution", (640, 480))),
            angle_noise_deg=float(sensor.get("angle_noise_deg", 0.1)),
        ),
        detection=DetectionCfg(conf_threshold=float(detection.get("conf_threshold", 0.6))),
        laser=LaserCfg(accuracy_m=float(laser.get("accuracy_m", 5.0)), fail_prob=float(laser.get("fail_prob", 0.02))),
        threat=ThreatCfg(high_conf=float(threat.get("high_conf", 0.85)), med_conf=float(threat.get("med_conf", 0.6))),
    )
