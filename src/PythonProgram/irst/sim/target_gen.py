"""目标生成模块。

定义 IRST 场景目标及其匀速轨迹推进。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class Target:
    """目标状态与红外特征。"""

    target_id: str
    x_m: float
    y_m: float
    z_m: float
    vx_mps: float
    vy_mps: float
    ir_signature: float = 0.6
    stealth_level: float = 0.0


class TargetGenerator:
    """目标生成与推进器。"""

    def __init__(self) -> None:
        self._targets: List[Target] = []

    def add(self, t: Target) -> None:
        """添加目标。"""

        self._targets.append(t)

    def step(self, dt_s: float) -> None:
        """推进所有目标状态。"""

        for t in self._targets:
            t.x_m += t.vx_mps * dt_s
            t.y_m += t.vy_mps * dt_s

    def list(self) -> List[Target]:
        """返回目标列表副本。"""

        return list(self._targets)
