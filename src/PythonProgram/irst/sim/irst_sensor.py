"""IRST 传感器前端模型。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple
import math
import random

from .target_gen import Target


@dataclass
class Detection:
    """检测结果。"""

    detection_id: str
    az_deg: float
    el_deg: float
    snr_db: float
    confidence: float


@dataclass
class IrstSensor:
    """IRST 传感器参数与投影。"""

    sensor_id: str
    x_m: float
    y_m: float
    z_m: float
    fov_deg: float = 40.0
    resolution: Tuple[int, int] = (640, 480)
    angle_noise_deg: float = 0.1

    def observe(self, targets: List[Target]) -> List[Detection]:
        """生成角度观测与检测。"""

        out: List[Detection] = []
        for idx, t in enumerate(targets):
            dx = t.x_m - self.x_m
            dy = t.y_m - self.y_m
            dz = t.z_m - self.z_m
            rng = math.sqrt(dx * dx + dy * dy + dz * dz)
            az = math.degrees(math.atan2(dy, dx)) + random.gauss(0, self.angle_noise_deg)
            el = math.degrees(math.atan2(dz, math.sqrt(dx * dx + dy * dy))) + random.gauss(0, self.angle_noise_deg)
            if abs(az) <= self.fov_deg / 2 and abs(el) <= self.fov_deg / 2:
                base_snr = 20.0 - 0.01 * rng
                snr = max(1.0, base_snr * (t.ir_signature * (1.0 - 0.7 * t.stealth_level)))
                conf = min(1.0, 0.5 + 0.02 * snr)
                out.append(Detection(f"D_{idx}", az, el, snr, conf))
        return out

    def project_to_image(self, az_deg: float, el_deg: float) -> Tuple[int, int]:
        """将角度投影到图像像素坐标。"""

        w, h = self.resolution
        x = int((az_deg / (self.fov_deg / 2)) * (w / 2) + w / 2)
        y = int((-el_deg / (self.fov_deg / 2)) * (h / 2) + h / 2)
        return max(0, min(w - 1, x)), max(0, min(h - 1, y))
