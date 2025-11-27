"""多目标跟踪器模块。

提供基于匀速模型的简易卡尔曼滤波与最近邻数据关联。

Classes:
    Track: 轨迹状态结构。
    Tracker: 跟踪器实现，支持预测、更新与关联。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import math


@dataclass
class Track:
    """轨迹状态。

    Attributes:
        track_id: 轨迹 ID。
        x_m: X 位置。
        y_m: Y 位置。
        vx_mps: X 速度。
        vy_mps: Y 速度。
        confidence: 置信度（0-1）。
    """

    track_id: str
    x_m: float
    y_m: float
    vx_mps: float
    vy_mps: float
    confidence: float = 0.5


class Tracker:
    """简易多目标跟踪器。

    使用匀速模型进行状态预测，并采用最近邻关联将位置观测更新到轨迹。

    Methods:
        predict(dt_s): 进行状态预测。
        update(observations): 根据观测更新轨迹。
        get_tracks(): 返回当前轨迹列表。
    """

    def __init__(self, gate_threshold_m: float = 200.0) -> None:
        self._tracks: Dict[str, Track] = {}
        self._next_id: int = 1
        self._gate = gate_threshold_m

    def _distance(self, x1: float, y1: float, x2: float, y2: float) -> float:
        """计算二维欧氏距离。

        Args:
            x1: 点1 X。
            y1: 点1 Y。
            x2: 点2 X。
            y2: 点2 Y。

        Returns:
            欧氏距离（米）。
        """

        return math.hypot(x1 - x2, y1 - y2)

    def predict(self, dt_s: float) -> None:
        """按匀速模型推进所有轨迹状态。

        Args:
            dt_s: 时间步长（秒）。
        """

        for trk in self._tracks.values():
            trk.x_m += trk.vx_mps * dt_s
            trk.y_m += trk.vy_mps * dt_s

    def update(self, observations: List[Tuple[float, float]]) -> None:
        """使用位置观测更新轨迹。

        简化：观测为平面坐标 (x, y)。进行最近邻关联，距离超过门限则新建轨迹。

        Args:
            observations: 观测点列表 [(x, y), ...]。
        """

        used = set()
        # 先尝试关联到已有轨迹
        for trk in list(self._tracks.values()):
            best_idx = None
            best_dist = float("inf")
            for idx, (ox, oy) in enumerate(observations):
                if idx in used:
                    continue
                d = self._distance(trk.x_m, trk.y_m, ox, oy)
                if d < best_dist:
                    best_dist = d
                    best_idx = idx
            if best_idx is not None and best_dist <= self._gate:
                ox, oy = observations[best_idx]
                used.add(best_idx)
                # 简化的卡尔曼更新：位置直接朝观测做指数移动平均
                alpha = 0.6
                trk.x_m = alpha * ox + (1 - alpha) * trk.x_m
                trk.y_m = alpha * oy + (1 - alpha) * trk.y_m
                trk.confidence = min(1.0, trk.confidence + 0.05)
            else:
                # 未关联则降低置信度
                trk.confidence = max(0.0, trk.confidence - 0.1)

        # 余下观测新建轨迹
        for idx, (ox, oy) in enumerate(observations):
            if idx in used:
                continue
            trk_id = f"TRK_{self._next_id}"
            self._next_id += 1
            self._tracks[trk_id] = Track(trk_id, ox, oy, 0.0, 0.0, 0.6)

    def get_tracks(self) -> List[Track]:
        """获取当前轨迹列表。

        Returns:
            轨迹对象列表。
        """

        return list(self._tracks.values())
