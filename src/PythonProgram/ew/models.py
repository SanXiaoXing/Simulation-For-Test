from dataclasses import dataclass, asdict
from enum import IntEnum
import json
import struct
from typing import Any, Dict, List, Optional


class SignalType(IntEnum):
    """信号类型枚举。

    仅包含仿真接口需要的三类类型，遵循README的结构体字段约束。

    Attributes:
        SIG_RADAR: 雷达信号。
        SIG_COMM: 通信信号。
        SIG_JAM: 干扰信号。
    """

    SIG_RADAR = 1
    SIG_COMM = 2
    SIG_JAM = 3


class Modulation(IntEnum):
    """调制方式枚举。

    基本覆盖AM、FM、PSK/QPSK、QAM、OFDM等常见体制。

    Attributes:
        MOD_NONE: 无调制/未指定。
        AM: 幅度调制。
        FM: 频率调制。
        BPSK: 二进制相移键控。
        QPSK: 正交相移键控。
        QAM16: 16阶正交幅度调制。
        QAM64: 64阶正交幅度调制。
        OFDM: 正交频分复用。
    """

    MOD_NONE = 0
    AM = 1
    FM = 2
    BPSK = 3
    QPSK = 4
    QAM16 = 5
    QAM64 = 6
    OFDM = 7


_EW_STRUCT_FMT = "<I i Q d d f f f f f f f i"


@dataclass
class EWSignal:
    """电子战仿真信号数据结构。

    字段定义与C结构体一一对应，用于JSON/二进制互转。

    Attributes:
        source_id: 来源ID（uint32）。
        type: 信号类型（SignalType）。
        timestamp_ms: 时间戳（uint64, ms）。
        center_freq_hz: 中心频率（double）。
        bandwidth_hz: 带宽（double）。
        signal_power_dbm: 信号功率（float, dBm）。
        snr_db: 信噪比（float, dB）。
        azimuth_deg: 方位角（float, deg）。
        elevation_deg: 俯仰角（float, deg）。
        range_m: 距离（float, m；-1 表示未知）。
        pri_ms: PRI（float, ms；雷达专用）。
        pulse_width_us: 脉宽（float, us；雷达专用）。
        modulation: 调制方式（Modulation）。
    """

    source_id: int
    type: SignalType
    timestamp_ms: int
    center_freq_hz: float
    bandwidth_hz: float
    signal_power_dbm: float
    snr_db: float
    azimuth_deg: float
    elevation_deg: float
    range_m: float
    pri_ms: float
    pulse_width_us: float
    modulation: Modulation

    def to_json(self) -> str:
        """将信号序列化为JSON字符串。

        Returns:
            str: JSON字符串表示。
        """

        data = asdict(self)
        data["type"] = int(self.type)
        data["modulation"] = int(self.modulation)
        return json.dumps(data, ensure_ascii=False)

    def to_binary(self) -> bytes:
        """将信号序列化为二进制结构体。

        采用小端序，结构格式与`_EW_STRUCT_FMT`一致，总长度72字节。

        Returns:
            bytes: 打包后的二进制字节串。
        """

        return struct.pack(
            _EW_STRUCT_FMT,
            int(self.source_id),
            int(self.type),
            int(self.timestamp_ms),
            float(self.center_freq_hz),
            float(self.bandwidth_hz),
            float(self.signal_power_dbm),
            float(self.snr_db),
            float(self.azimuth_deg),
            float(self.elevation_deg),
            float(self.range_m),
            float(self.pri_ms),
            float(self.pulse_width_us),
            int(self.modulation),
        )

    @staticmethod
    def from_json(js: str) -> "EWSignal":
        """从JSON字符串解析为信号实例。

        Args:
            js: JSON字符串。

        Returns:
            EWSignal: 解析后的信号对象。
        """

        data = json.loads(js)
        return EWSignal(
            source_id=int(data["source_id"]),
            type=SignalType(int(data["type"])),
            timestamp_ms=int(data["timestamp_ms"]),
            center_freq_hz=float(data["center_freq_hz"]),
            bandwidth_hz=float(data["bandwidth_hz"]),
            signal_power_dbm=float(data["signal_power_dbm"]),
            snr_db=float(data["snr_db"]),
            azimuth_deg=float(data["azimuth_deg"]),
            elevation_deg=float(data["elevation_deg"]),
            range_m=float(data["range_m"]),
            pri_ms=float(data["pri_ms"]),
            pulse_width_us=float(data["pulse_width_us"]),
            modulation=Modulation(int(data["modulation"]))
        )

    @staticmethod
    def from_binary(buf: bytes) -> "EWSignal":
        """从二进制字节解析为信号实例。

        Args:
            buf: 二进制字节序列，长度应为72字节。

        Returns:
            EWSignal: 解析后的信号对象。
        """

        unpacked = struct.unpack(_EW_STRUCT_FMT, buf)
        return EWSignal(
            source_id=int(unpacked[0]),
            type=SignalType(int(unpacked[1])),
            timestamp_ms=int(unpacked[2]),
            center_freq_hz=float(unpacked[3]),
            bandwidth_hz=float(unpacked[4]),
            signal_power_dbm=float(unpacked[5]),
            snr_db=float(unpacked[6]),
            azimuth_deg=float(unpacked[7]),
            elevation_deg=float(unpacked[8]),
            range_m=float(unpacked[9]),
            pri_ms=float(unpacked[10]),
            pulse_width_us=float(unpacked[11]),
            modulation=Modulation(int(unpacked[12]))
        )


def default_radar_library() -> List[Dict[str, Any]]:
    """构建10个典型雷达的默认参数库。

    Returns:
        List[Dict[str, Any]]: 雷达参数表。
    """

    return [
        {"name": "Search-L1", "freq": 1.2e9, "bw": 20e6, "pri_ms": (2.0, 4.0), "pw_us": (1.0, 2.0), "power_dbm": -10.0, "az_deg": 45.0, "range_m": 25000},
        {"name": "Track-S", "freq": 3.1e9, "bw": 30e6, "pri_ms": (1.5, 3.0), "pw_us": (0.8, 1.5), "power_dbm": -8.0, "az_deg": 80.0, "range_m": 18000},
        {"name": "FireCtrl-X", "freq": 9.5e9, "bw": 50e6, "pri_ms": (1.0, 2.0), "pw_us": (0.5, 1.0), "power_dbm": -5.0, "az_deg": 120.0, "range_m": 15000},
        {"name": "Maritime-C", "freq": 5.4e9, "bw": 40e6, "pri_ms": (1.8, 3.5), "pw_us": (0.9, 1.6), "power_dbm": -9.0, "az_deg": 10.0, "range_m": 30000},
        {"name": "Airborne-Ku", "freq": 13.5e9, "bw": 80e6, "pri_ms": (0.8, 1.6), "pw_us": (0.3, 0.8), "power_dbm": -7.0, "az_deg": 200.0, "range_m": 22000},
        {"name": "AEW-E", "freq": 2.9e9, "bw": 25e6, "pri_ms": (2.5, 5.0), "pw_us": (1.2, 2.2), "power_dbm": -11.0, "az_deg": 300.0, "range_m": 40000},
        {"name": "Ground-Surv", "freq": 2.1e9, "bw": 15e6, "pri_ms": (3.0, 6.0), "pw_us": (1.5, 2.5), "power_dbm": -12.0, "az_deg": 270.0, "range_m": 35000},
        {"name": "Target-Illum", "freq": 10.0e9, "bw": 60e6, "pri_ms": (0.9, 1.8), "pw_us": (0.4, 0.9), "power_dbm": -6.0, "az_deg": 150.0, "range_m": 12000},
        {"name": "LowBand-UHF", "freq": 800e6, "bw": 10e6, "pri_ms": (4.0, 8.0), "pw_us": (2.0, 3.5), "power_dbm": -13.0, "az_deg": 60.0, "range_m": 50000},
        {"name": "Phased-Array", "freq": 7.8e9, "bw": 70e6, "pri_ms": (1.2, 2.4), "pw_us": (0.6, 1.2), "power_dbm": -7.5, "az_deg": 330.0, "range_m": 28000},
    ]


def default_missile_library() -> List[Dict[str, Any]]:
    """构建5个典型导弹模型库。

    Returns:
        List[Dict[str, Any]]: 导弹参数表。
    """

    return [
        {"name": "IR-Stalker", "guidance": "IR", "v0_mps": 320.0, "trajectory": "pursuit", "max_detect_m": 15000},
        {"name": "RF-Seeker-1", "guidance": "RF", "v0_mps": 450.0, "trajectory": "lead", "max_detect_m": 20000},
        {"name": "IR-Darter", "guidance": "IR", "v0_mps": 280.0, "trajectory": "pursuit", "max_detect_m": 12000},
        {"name": "RF-Lancer", "guidance": "RF", "v0_mps": 520.0, "trajectory": "proportional", "max_detect_m": 25000},
        {"name": "Dual-Seeker", "guidance": "IR/RF", "v0_mps": 400.0, "trajectory": "mixed", "max_detect_m": 22000},
    ]


def default_comm_library() -> List[Dict[str, Any]]:
    """构建8种典型通信信号库。

    Returns:
        List[Dict[str, Any]]: 通信信号参数表。
    """

    return [
        {"name": "AM-Voice", "mod": Modulation.AM, "bw": 6e3, "power_dbm": (-30, -10), "snr_db": (5, 25), "freq": 120e6},
        {"name": "FM-Voice", "mod": Modulation.FM, "bw": 150e3, "power_dbm": (-35, -12), "snr_db": (10, 30), "freq": 105e6},
        {"name": "BPSK-Telemetry", "mod": Modulation.BPSK, "bw": 1e6, "power_dbm": (-25, -5), "snr_db": (8, 28), "freq": 2.2e9},
        {"name": "QPSK-Link", "mod": Modulation.QPSK, "bw": 2e6, "power_dbm": (-22, -2), "snr_db": (12, 32), "freq": 2.45e9},
        {"name": "QAM16-Data", "mod": Modulation.QAM16, "bw": 5e6, "power_dbm": (-20, 0), "snr_db": (15, 35), "freq": 3.5e9},
        {"name": "QAM64-Backhaul", "mod": Modulation.QAM64, "bw": 10e6, "power_dbm": (-18, 2), "snr_db": (18, 38), "freq": 4.9e9},
        {"name": "OFDM-WLAN", "mod": Modulation.OFDM, "bw": 20e6, "power_dbm": (-28, -8), "snr_db": (10, 30), "freq": 5.2e9},
        {"name": "OFDM-LTE", "mod": Modulation.OFDM, "bw": 15e6, "power_dbm": (-26, -6), "snr_db": (12, 32), "freq": 1.8e9},
    ]


def default_jam_modes() -> List[Dict[str, Any]]:
    """构建5种干扰模式定义。

    Returns:
        List[Dict[str, Any]]: 干扰模式参数表。
    """

    return [
        {"name": "Noise Jammer", "desc": "宽带噪声压制，提高干扰功率，降低目标SNR", "power_boost_db": 6.0, "snr_drop_db": 8.0},
        {"name": "Deception Jammer", "desc": "欺骗式干扰，改变脉冲时序与频率特性", "power_boost_db": 3.0, "snr_drop_db": 6.0},
        {"name": "DRFM Jammer", "desc": "数字射频存储转发，产生伪目标", "power_boost_db": 4.0, "snr_drop_db": 7.0},
        {"name": "Spot Jammer", "desc": "窄带压制，针对性提升某频段功率", "power_boost_db": 5.0, "snr_drop_db": 5.0},
        {"name": "Sweep Jammer", "desc": "扫频压制，频谱范围内来回扫动", "power_boost_db": 4.0, "snr_drop_db": 6.0},
    ]

