"""目标生成器模块。

提供目标数据结构与轨迹生成逻辑，用于在场景中创建动态/静态目标。

Classes:
    Target: 表示单个目标的物理状态。
    TargetGenerator: 生成多目标轨迹的管理器。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Iterable, Tuple


@dataclass
class Target:
    """目标状态数据结构。

    Attributes:
        target_id: 目标唯一标识符。
        x_m: 目标 X 位置（米）。
        y_m: 目标 Y 位置（米）。
        z_m: 目标高度（米）。
        vx_mps: X 方向速度（米/秒）。
        vy_mps: Y 方向速度（米/秒）。
        rcs_dbsm: 雷达散射截面（dBsm）。
        ir_strength: 红外强度（归一化 0-1）。
    """

    target_id: str
    x_m: float
    y_m: float
    z_m: float
    vx_mps: float
    vy_mps: float
    rcs_dbsm: float = 0.0
    ir_strength: float = 0.5


class TargetGenerator:
    """目标轨迹生成器。

    提供基于简单匀速模型的轨迹推进，并支持批量管理多个目标。

    Methods:
        add_target(target): 添加新目标。
        step(dt_s): 推进所有目标状态 dt_s 秒。
        list_targets(): 返回当前所有目标状态列表。
    """

    def __init__(self) -> None:
        self._targets: List[Target] = []

    def add_target(self, target: Target) -> None:
        """添加目标。

        Args:
            target: 目标对象。
        """

        self._targets.append(target)

    def step(self, dt_s: float) -> None:
        """推进所有目标状态。

        Args:
            dt_s: 时间步长（秒）。
        """

        for t in self._targets:
            t.x_m += t.vx_mps * dt_s
            t.y_m += t.vy_mps * dt_s

    def list_targets(self) -> List[Target]:
        """返回当前所有目标状态列表。

        Returns:
            目标列表拷贝，便于外部安全读取。
        """

        return list(self._targets)
