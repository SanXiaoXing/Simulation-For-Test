"""数据融合模块。

提供简单的基于加权平均的时序融合示例。
"""

from __future__ import annotations

from typing import List, Tuple


def fuse_positions(samples: List[Tuple[float, float, float]]) -> Tuple[float, float]:
    """融合多个位置样本。

    简化：输入为 (x, y, weight) 三元组，输出加权平均位置。

    Args:
        samples: 位置与权重列表。

    Returns:
        融合后位置 (x, y)。当权重和为 0 时返回 (0, 0)。
    """

    wsum = sum(s[2] for s in samples)
    if wsum <= 1e-9:
        return 0.0, 0.0
    x = sum(s[0] * s[2] for s in samples) / wsum
    y = sum(s[1] * s[2] for s in samples) / wsum
    return x, y
