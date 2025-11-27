"""激光测距模拟模块。"""

from __future__ import annotations

from typing import Tuple
import random


def simulate_range(distance_m: float, accuracy_m: float = 5.0, fail_prob: float = 0.05) -> Tuple[float, bool]:
    """模拟激光测距。"""

    if random.random() < fail_prob:
        return 0.0, False
    meas = max(0.0, distance_m + random.gauss(0.0, accuracy_m))
    return meas, True
