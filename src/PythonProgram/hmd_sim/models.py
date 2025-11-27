from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class HMDMode(Enum):
    """头盔显示模式。"""

    AIR_TO_AIR = "air_to_air"
    AIR_TO_GROUND = "air_to_ground"
    AIR_TO_SEA = "air_to_sea"


@dataclass
class FlightParameters:
    """基础飞行参数。"""

    airspeed_mps: float = 150.0
    altitude_m: float = 1200.0
    heading_deg: float = 90.0
    g_load: float = 1.0
    aoa_deg: float = 5.0
    fuel_kg: float = 1200.0
    # 头部姿态（用于动态锁定框随头部转动）
    head_yaw_deg: float = 0.0
    head_pitch_deg: float = 0.0
    head_roll_deg: float = 0.0


@dataclass
class WeaponState:
    """武器与火控状态。"""

    selected: str = "AAM"
    status: str = "READY"
    locked: bool = False
    max_range_m: float = 8000.0
    min_range_m: float = 500.0
    launch_perm: bool = False
    ammo_left: int = 4
    off_boresight_deg: float = 30.0
    rmax_m: float = 8000.0
    rne_m: float = 3000.0


@dataclass
class TacticalInfo:
    """战术与威胁信息。"""

    target_bearing_deg: float = 45.0
    target_distance_m: float = 6000.0
    closure_rate_mps: float = -120.0
    threat_level: str = "LOW"
    is_friend: bool = False
    waypoint_distance_m: float = 0.0
    sea_obstacle_warn: bool = False


@dataclass
class NetworkConfig:
    """网络接口配置。"""

    out_host: str = "127.0.0.1"
    out_port: int = 9102
    protocol: str = "udp"
    link_speed_bps: float = 100e6
    icd_path: Optional[str] = None


@dataclass
class HMDConfig:
    """头盔显示仿真配置。"""

    update_hz: float = 60.0
    mode: HMDMode = HMDMode.AIR_TO_AIR

