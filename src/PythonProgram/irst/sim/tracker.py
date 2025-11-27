"""IRST 跟踪器模块。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple
import math


@dataclass
class Track:
    """轨迹状态。"""

    track_id: str
    x_m: float
    y_m: float
    confidence: float = 0.6


class Tracker:
    """最近邻关联的简易跟踪器。"""

    def __init__(self, gate_m: float = 200.0) -> None:
        self._tracks: Dict[str, Track] = {}
        self._next = 1
        self._gate = gate_m

    def _dist(self, a: Tuple[float, float], b: Tuple[float, float]) -> float:
        """计算欧氏距离。"""

        return math.hypot(a[0] - b[0], a[1] - b[1])

    def update(self, points: List[Tuple[float, float]]) -> None:
        """用平面点更新轨迹。"""

        used = set()
        for tr in list(self._tracks.values()):
            bi = None
            bd = float("inf")
            for i, p in enumerate(points):
                if i in used:
                    continue
                d = self._dist((tr.x_m, tr.y_m), p)
                if d < bd:
                    bd = d
                    bi = i
            if bi is not None and bd <= self._gate:
                px, py = points[bi]
                used.add(bi)
                alpha = 0.6
                tr.x_m = alpha * px + (1 - alpha) * tr.x_m
                tr.y_m = alpha * py + (1 - alpha) * tr.y_m
                tr.confidence = min(1.0, tr.confidence + 0.05)
            else:
                tr.confidence = max(0.0, tr.confidence - 0.1)

        for i, p in enumerate(points):
            if i in used:
                continue
            tid = f"TRK_{self._next}"
            self._next += 1
            self._tracks[tid] = Track(tid, p[0], p[1], 0.7)

    def list(self) -> List[Track]:
        """返回轨迹列表。"""

        return list(self._tracks.values())
