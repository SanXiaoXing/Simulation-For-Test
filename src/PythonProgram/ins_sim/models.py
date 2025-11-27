from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Tuple


class TrajectoryType(Enum):
    """轨迹类型枚举。"""

    STRAIGHT = "straight"
    CURVE = "curve"
    TURN = "turn"
    CUSTOM = "custom"


@dataclass
class INSParameters:
    """惯导系统参数。

    Attributes:
        update_hz: 仿真更新频率(Hz)。
        earth_radius_m: 地球半径(米)。
        gravity_mps2: 重力加速度(米/秒^2)。
        imu_noise_gyro_rps: 陀螺噪声(弧度/秒, 1σ)。
        imu_noise_accel_mps2: 加计噪声(米/秒^2, 1σ)。
        imu_bias_gyro_rps: 陀螺零偏(弧度/秒)。
        imu_bias_accel_mps2: 加计零偏(米/秒^2)。
        scale_factor_gyro: 陀螺比例因子误差。
        scale_factor_accel: 加计比例因子误差。
    """

    update_hz: float = 400.0
    earth_radius_m: float = 6_371_000.0
    gravity_mps2: float = 9.80665
    imu_noise_gyro_rps: float = 0.005
    imu_noise_accel_mps2: float = 0.05
    imu_bias_gyro_rps: float = 0.0005
    imu_bias_accel_mps2: float = 0.02
    scale_factor_gyro: float = 0.0005
    scale_factor_accel: float = 0.0005


@dataclass
class VehicleState:
    """飞行器状态。"""

    # 位置与速度(地理坐标系)
    lat_deg: float = 31.2304
    lon_deg: float = 121.4737
    alt_m: float = 1000.0
    v_ned_mps: Tuple[float, float, float] = (120.0, 0.0, 0.0)

    # 姿态与角速率(机体坐标系)
    attitude_deg: Tuple[float, float, float] = (0.0, 0.0, 0.0)  # pitch, roll, yaw
    body_rates_rps: Tuple[float, float, float] = (0.0, 0.0, 0.0)  # wx, wy, wz

    # 加速度(机体坐标系)
    body_accel_mps2: Tuple[float, float, float] = (0.0, 0.0, 0.0)

    # 空速/地速
    airspeed_mps: float = 120.0
    groundspeed_mps: float = 120.0


@dataclass
class IMUFaultConfig:
    """IMU异常配置。"""

    dropout: bool = False
    spike: bool = False
    bias_step: bool = False
    saturation: bool = False
    spike_prob: float = 0.001
    dropout_prob: float = 0.001
    bias_step_value: float = 0.02
    saturation_limit_accel: float = 20.0
    saturation_limit_gyro: float = 5.0


@dataclass
class NetworkConfig:
    """网络接口配置。"""

    out_host: str = "127.0.0.1"
    out_port: int = 9001
    protocol: str = "udp"  # 可扩展: "tcp", "afdx", "fc"
    link_speed_bps: float = 100e6
    icd_path: Optional[str] = None


@dataclass
class RecordConfig:
    """记录/重放配置。"""

    enable_record: bool = True
    record_path: str = "ins_record.jsonl"
    enable_replay: bool = False
    replay_path: str = "ins_record.jsonl"


def clamp(v: float, lo: float, hi: float) -> float:
    """限幅函数。

    Args:
        v: 输入值。
        lo: 下限。
        hi: 上限。

    Returns:
        限幅后的值。
    """

    return max(lo, min(hi, v))


def deg2rad(d: float) -> float:
    """角度转弧度。"""

    return d * math.pi / 180.0


def rad2deg(r: float) -> float:
    """弧度转角度。"""

    return r * 180.0 / math.pi


def gaussian_noise(sigma: float) -> float:
    """生成高斯噪声。"""

    return random.gauss(0.0, sigma)

