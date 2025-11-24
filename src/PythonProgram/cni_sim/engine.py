from typing import List
import time

from .models import CNIState, Target

# 程序启动时刻，用于计算相对时间戳（0~65535）
START_EPOCH = time.time()


def _update_target_position(t: Target, dt: float) -> None:
    """基于速度外推目标位置。

    使用简单近似：纬度/经度不做球面投影，按小范围近似的米转度进行更新；高度按下降速度更新。

    Args:
        t: 目标对象。
        dt: 时间步长（秒）。
    """

    # 地球近似半径与经纬度转换（简化）
    R = 6378137.0
    north_m = float(t.vel_ned_mps_N) * dt
    east_m = float(t.vel_ned_mps_E) * dt
    down_m = float(t.vel_ned_mps_D) * dt

    dlat = north_m / R
    dlon = east_m / (R * max(1e-6, __import__('math').cos(t.lat_deg * __import__('math').pi / 180.0)))
    t.lat_deg = float(t.lat_deg) + dlat * 180.0 / __import__('math').pi
    t.lon_deg = float(t.lon_deg) + dlon * 180.0 / __import__('math').pi
    t.alt_m = float(t.alt_m) - down_m


def step(state: CNIState) -> None:
    """执行一次仿真步进。

    推进仿真时间，更新各目标位置与高度，保留其他模块状态不变或由UI输入驱动。

    Args:
        state: 全局仿真状态。
    """

    dt = float(state.dt_s)
    state.sim_time_s = float(state.sim_time_s) + dt
    # 使用系统时间的时分秒（当日秒数，0~86400）
    lt = time.localtime()
    state.shortwave.timestamp_s = float(lt.tm_hour * 3600 + lt.tm_min * 60 + lt.tm_sec)
    for t in state.targets:
        _update_target_position(t, dt)
