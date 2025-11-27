"""电子战（EW）仿真模块。

支持注入伪目标与对链路施加噪声/丢帧影响的占位实现。
"""

from __future__ import annotations

from typing import List, Tuple
import random


def inject_false_targets(observations: List[Tuple[float, float]], count: int = 2, spread_m: float = 500.0) -> List[Tuple[float, float]]:
    """在观测中注入伪目标。

    Args:
        observations: 原始观测坐标列表。
        count: 注入的伪目标数量。
        spread_m: 伪目标相对于真实观测的随机散布尺度。

    Returns:
        含伪目标的观测列表副本。
    """

    out = list(observations)
    for _ in range(count):
        if observations:
            ox, oy = random.choice(observations)
            out.append((ox + random.uniform(-spread_m, spread_m), oy + random.uniform(-spread_m, spread_m)))
    return out


def apply_jamming_snr(snr_db: float, reduction_db: float = 10.0) -> float:
    """对信噪比施加抑制。

    Args:
        snr_db: 原始信噪比。
        reduction_db: 抑制分贝值。

    Returns:
        抑制后的信噪比（不小于 0）。
    """

    return max(0.0, snr_db - reduction_db)
