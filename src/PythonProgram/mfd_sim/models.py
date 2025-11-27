from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class MFDMode(Enum):
    """多功能显示器模式。"""

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
    waypoint_name: str = "WP1"
    waypoint_distance_m: float = 5000.0


@dataclass
class WeaponState:
    """武器与火控状态。"""

    selected: str = "AAM"
    status: str = "READY"
    locked: bool = False
    max_range_m: float = 8000.0
    min_range_m: float = 500.0
    launch_perm: bool = False
    ammo_missile: int = 4
    ammo_gun: int = 120


@dataclass
class TacticalInfo:
    """战术与雷达信息。"""

    target_bearing_deg: float = 45.0
    target_distance_m: float = 6000.0
    closure_rate_mps: float = -120.0
    threat_level: str = "LOW"
    is_friend: bool = False
    radar_tracks: int = 0


@dataclass
class NetworkConfig:
    """网络接口配置。"""

    out_host: str = "127.0.0.1"
    out_port: int = 9201
    protocol: str = "udp"
    link_speed_bps: float = 100e6
    icd_path: Optional[str] = None


@dataclass
class MFDConfig:
    """MFD仿真配置。"""

    update_hz: float = 30.0
    mode: MFDMode = MFDMode.AIR_TO_AIR

