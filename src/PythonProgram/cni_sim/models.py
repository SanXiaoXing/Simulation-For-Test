from dataclasses import dataclass, field
from typing import List
import time


@dataclass
class Target:
    """目标对象数据结构。

    Args:
        target_id: 目标唯一标识符（0~255）。
        lat_deg: 目标经度（deg）。
        lon_deg: 目标纬度（deg）。
        alt_m: 目标高度（m）。
        vel_ned_mps_N: 北向速度（m/s）。
        vel_ned_mps_E: 东向速度（m/s）。
        vel_ned_mps_D: 下降速度（m/s）。
        azimuth_deg: 相对于参考的方位角（deg）。
        iff_code: 敌我识别码（0/1/2等）。
    """

    target_id: int = 0
    lat_deg: float = 0.0
    lon_deg: float = 0.0
    alt_m: float = 0.0
    vel_ned_mps_N: float = 0.0
    vel_ned_mps_E: float = 0.0
    vel_ned_mps_D: float = 0.0
    azimuth_deg: float = 0.0
    iff_code: int = 0


@dataclass
class Shortwave:
    """短波通信参数。

    Args:
        source_id: 发送方id（0~255）。
        dest_id: 目的方id（0~255）。
        tx_power_dbm: 发送功率dBm。
        frequency_hz: 频率Hz。
        timestamp_s: 发包时间秒。
    """

    source_id: int = 0
    dest_id: int = 0
    tx_power_dbm: float = 0.0
    frequency_hz: float = 0.0
    timestamp_s: float = 0.0


@dataclass
class Altimeter:
    """无线电高度表参数。

    Args:
        active: 是否启用。
        frequency_hz: 高度表工作频率Hz。
    """

    active: int = 0
    frequency_hz: float = 0.0


@dataclass
class NavState:
    """本机导航/惯导状态。

    Args:
        ego_lat_deg: 本机经度deg。
        ego_lon_deg: 本机纬度deg。
        ego_alt_m: 本机高度m。
        airspeed_mps: 空速m/s。
        groundspeed_mps: 地速m/s。
        accel_mps2: 三轴加速度m/s^2。
        ang_rate_rps: 三轴角速度rad/s。
        attitude_deg: 姿态角（俯仰、横滚、偏航）deg。
    """

    ego_lat_deg: float = 0.0
    ego_lon_deg: float = 0.0
    ego_alt_m: float = 0.0
    airspeed_mps: float = 0.0
    groundspeed_mps: float = 0.0
    accel_mps2: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    ang_rate_rps: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    attitude_deg: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])


@dataclass
class CNIState:
    """CNI全局仿真状态。

    Args:
        sim_time_s: 仿真时间s。
        dt_s: 仿真步长s。
        targets: 目标列表。
        shortwave: 短波通信参数。
        altimeter: 无线电高度表参数。
        nav: 本机导航/惯导状态。
        frame_mode: 目标类型标识（1：雷达；2：通信导航）。
    """

    sim_time_s: float = 0.0
    dt_s: float = 1.0
    targets: List[Target] = field(default_factory=list)
    shortwave: Shortwave = field(default_factory=Shortwave)
    altimeter: Altimeter = field(default_factory=Altimeter)
    nav: NavState = field(default_factory=NavState)
    frame_mode: int = 1
