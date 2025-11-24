import struct
from typing import List

from .models import CNIState, Target


def _pack_targets(targets: List[Target]) -> bytes:
    """打包目标块。

    将每个目标按30字节布局打包：
    `<B f f f f f f f B>`，小端字节序。

    Args:
        targets: 目标列表。

    Returns:
        bytes: 目标块二进制数据。
    """

    buf = bytearray()
    fmt = '<B f f f f f f f B'
    for t in targets:
        buf += struct.pack(
            fmt,
            int(t.target_id) & 0xFF,
            float(t.lat_deg),
            float(t.lon_deg),
            float(t.alt_m),
            float(t.vel_ned_mps_N),
            float(t.vel_ned_mps_E),
            float(t.vel_ned_mps_D),
            float(t.azimuth_deg),
            int(t.iff_code) & 0xFF,
        )
    return bytes(buf)


def _pack_comm_and_alt(state: CNIState) -> bytes:
    """打包通信与高度表块（19字节）。

    布局：`<B B f f f B f>`。

    Args:
        state: 全局仿真状态。

    Returns:
        bytes: 通信与高度表块。
    """

    fmt = '<B B f f f B f'
    return struct.pack(
        fmt,
        int(state.shortwave.source_id) & 0xFF,
        int(state.shortwave.dest_id) & 0xFF,
        float(state.shortwave.tx_power_dbm),
        float(state.shortwave.frequency_hz),
        float(state.shortwave.timestamp_s),
        int(state.altimeter.active) & 0xFF,
        float(state.altimeter.frequency_hz),
    )


def _pack_nav(state: CNIState) -> bytes:
    """打包导航/惯导块（16×float32 = 64字节）。

    布局：`<f f f f f f f f f f f f f f f f>`。

    Args:
        state: 全局仿真状态。

    Returns:
        bytes: 导航块。
    """

    n = state.nav
    fmt = '<' + 'f ' * 16
    fmt = fmt.replace(' ', '')
    values = [
        float(n.ego_lat_deg),
        float(n.ego_lon_deg),
        float(n.ego_alt_m),
        float(n.airspeed_mps),
        float(n.groundspeed_mps),
        float(n.accel_mps2[0]),
        float(n.accel_mps2[1]),
        float(n.accel_mps2[2]),
        float(n.ang_rate_rps[0]),
        float(n.ang_rate_rps[1]),
        float(n.ang_rate_rps[2]),
        float(n.attitude_deg[0]),
        float(n.attitude_deg[1]),
        float(n.attitude_deg[2]),
        float(0.0),  # 预留位，如需扩展可替换
        float(0.0),
    ]
    return struct.pack(fmt, *values)


def build_frame(state: CNIState) -> bytes:
    """构建完整CNI二进制报文帧。

    布局：
      头部`<H B B B>`：包头AA55（uint16）、目标类型（uint8）、长度（uint8）、目标数量（uint8）。
      目标块：`n`个目标，每块30字节。
      通信与高度表块：19字节。
      导航块：64字节。

    长度字段为：`n*30 + 19 + 64`。

    Args:
        state: 全局仿真状态。

    Returns:
        bytes: 完整报文字节串。
    """

    targets_payload = _pack_targets(state.targets)
    comm_alt_payload = _pack_comm_and_alt(state)
    nav_payload = _pack_nav(state)
    payload_len = len(targets_payload) + len(comm_alt_payload) + len(nav_payload)

    header = struct.pack(
        '<H B B B',
        0xAA55,
        int(state.frame_mode) & 0xFF,
        payload_len & 0xFF,
        len(state.targets) & 0xFF,
    )
    return header + targets_payload + comm_alt_payload + nav_payload


def frame_to_hex(frame: bytes, group: int = 1) -> str:
    """将报文字节串转为十六进制字符串。

    Args:
        frame: 报文字节串。
        group: 分组显示字节数（默认1）。

    Returns:
        str: 十六进制字符串，按分组插入空格。
    """

    hexstr = frame.hex()
    if group <= 1:
        return hexstr
    return ' '.join(hexstr[i : i + 2 * group] for i in range(0, len(hexstr), 2 * group))

