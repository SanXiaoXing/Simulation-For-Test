"""传感器节点仿真模块。

根据传感器的地理位置与朝向，对场景目标生成观测测量，并注入噪声与遮挡影响。

Classes:
    SensorNode: 表示单个传感器节点并生成观测。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List
import math
import random

from .target_generator import Target


@dataclass
class Observation:
    """单个目标的观测量。

    Attributes:
        target_id: 目标 ID。
        range_m: 距离（米）。
        az_deg: 方位角（度）。
        el_deg: 仰角（度）。
        snr_db: 信噪比（dB）。
        rfi_flag: 干扰标记。
    """

    target_id: str
    range_m: float
    az_deg: float
    el_deg: float
    snr_db: float
    rfi_flag: bool


@dataclass
class SensorNode:
    """传感器节点。

    Attributes:
        sensor_id: 传感器唯一标识。
        x_m: X 坐标。
        y_m: Y 坐标。
        z_m: 高度。
        fov_deg: 视场角（简化，圆锥）。
        noise_std: 距离测量噪声标准差。
    """

    sensor_id: str
    x_m: float
    y_m: float
    z_m: float
    fov_deg: float = 90.0
    noise_std: float = 5.0

    def observe(self, targets: List[Target]) -> List[Observation]:
        """对给定目标集生成观测。

        简化模型：假定传感器朝向全向，判断是否在视场角内，并对距离与角度添加高斯噪声。

        Args:
            targets: 目标列表。

        Returns:
            该传感器对各目标的观测列表。
        """

        obs_list: List[Observation] = []
        for t in targets:
            dx = t.x_m - self.x_m
            dy = t.y_m - self.y_m
            dz = t.z_m - self.z_m
            rng = math.sqrt(dx * dx + dy * dy + dz * dz)
            az = math.degrees(math.atan2(dy, dx))
            el = math.degrees(math.atan2(dz, math.sqrt(dx * dx + dy * dy)))

            # 简化视场判断：方位与仰角绝对值均小于 fov/2
            if abs(az) <= self.fov_deg / 2 and abs(el) <= self.fov_deg / 2:
                noisy_rng = rng + random.gauss(0, self.noise_std)
                noisy_az = az + random.gauss(0, 0.2)
                noisy_el = el + random.gauss(0, 0.2)
                snr_db = max(5.0, 30.0 - 0.01 * rng)
                obs_list.append(
                    Observation(
                        target_id=t.target_id,
                        range_m=noisy_rng,
                        az_deg=noisy_az,
                        el_deg=noisy_el,
                        snr_db=snr_db,
                        rfi_flag=False,
                    )
                )
        return obs_list
