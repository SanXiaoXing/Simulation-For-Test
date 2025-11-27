"""电子战影响模块。"""

from __future__ import annotations

from typing import List, Tuple
import random


def apply_angle_bias(az_deg: float, el_deg: float, bias_deg: float = 0.5) -> Tuple[float, float]:
    """施加测角偏移。"""

    return az_deg + random.uniform(-bias_deg, bias_deg), el_deg + random.uniform(-bias_deg, bias_deg)


def inject_false_detections(points: List[Tuple[float, float]], count: int = 1, spread_m: float = 500.0) -> List[Tuple[float, float]]:
    """注入伪目标。"""

    out = list(points)
    for _ in range(count):
        if points:
            x, y = random.choice(points)
            out.append((x + random.uniform(-spread_m, spread_m), y + random.uniform(-spread_m, spread_m)))
    return out
