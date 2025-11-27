"""定位与融合模块。"""

from __future__ import annotations

from typing import Tuple
import math


def azel_range_to_xy(sensor_xy: Tuple[float, float], az_deg: float, el_deg: float, range_m: float) -> Tuple[float, float]:
    """将角度与测距转换为平面坐标。"""

    x0, y0 = sensor_xy
    rad = math.radians(az_deg)
    x = x0 + range_m * math.cos(rad)
    y = y0 + range_m * math.sin(rad)
    return x, y
