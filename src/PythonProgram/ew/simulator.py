import math
import random
import socket
import threading
import time
from typing import Dict, Any, Optional

from .models import EWSignal, SignalType, Modulation, default_radar_library, default_comm_library, default_jam_modes


class EWSimulator:
    """电子战仿真引擎。

    负责周期性生成RWR/COMINT/ECM等信号，并通过UDP输出JSON与二进制两种格式。

    Attributes:
        running: 运行标志。
        udp_ip: UDP目标IP。
        udp_port: UDP目标端口。
        tick_hz: 仿真刷新频率（Hz）。
        radar_cfg: 当前雷达配置字典。
        comm_cfg: 当前通信配置字典。
        jam_cfg: 当前干扰模式配置字典。
        enable_missile: 是否开启导弹威胁。
        azimuth_deg: 当前方位角。
        elevation_deg: 当前俯仰角。
        range_m: 当前距离。
        base_snr_db: 基础SNR。
        base_power_dbm: 基础功率。
        center_freq_hz: 当前中心频率。
        bandwidth_hz: 当前带宽。
    """

    def __init__(
        self,
        udp_ip: str = "127.0.0.1",
        udp_port: int = 50000,
        tick_hz: float = 20.0,
        radar_index: int = 0,
        comm_index: int = 0,
        jam_index: Optional[int] = None,
        enable_missile: bool = False,
    ) -> None:
        """构造仿真器实例。

        Args:
            udp_ip: 目标IP地址。
            udp_port: 目标端口号。
            tick_hz: 刷新频率Hz。
            radar_index: 使用的雷达库索引。
            comm_index: 使用的通信库索引。
            jam_index: 干扰模式索引，None表示不启用。
            enable_missile: 是否开启导弹威胁。
        """

        self.running = False
        self.udp_ip = udp_ip
        self.udp_port = udp_port
        self.tick_hz = tick_hz
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.radar_lib = default_radar_library()
        self.comm_lib = default_comm_library()
        self.jam_lib = default_jam_modes()

        self.radar_cfg = self.radar_lib[radar_index % len(self.radar_lib)]
        self.comm_cfg = self.comm_lib[comm_index % len(self.comm_lib)]
        self.jam_cfg = self.jam_lib[jam_index] if jam_index is not None else None
        self.enable_missile = enable_missile

        self.azimuth_deg = float(self.radar_cfg["az_deg"]) if "az_deg" in self.radar_cfg else 0.0
        self.elevation_deg = 0.0
        self.range_m = float(self.radar_cfg["range_m"]) if "range_m" in self.radar_cfg else -1.0

        self.base_snr_db = 20.0
        self.base_power_dbm = float(self.radar_cfg.get("power_dbm", -10.0))
        self.center_freq_hz = float(self.radar_cfg.get("freq", 1.0e9))
        self.bandwidth_hz = float(self.radar_cfg.get("bw", 20e6))

        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """启动仿真线程。"""

        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """停止仿真线程。"""

        self.running = False
        if self._thread:
            self._thread.join(timeout=1.5)
            self._thread = None

    def _time_jitter(self, base_ms: float) -> float:
        """应用±5%时序抖动。

        Args:
            base_ms: 基准毫秒值。

        Returns:
            float: 抖动后的毫秒值。
        """

        jitter = base_ms * (1.0 + random.uniform(-0.05, 0.05))
        return max(0.0, jitter)

    def _power_with_jitter(self, base_dbm: float) -> float:
        """应用±1 dB功率抖动，并考虑干扰模式影响。

        Args:
            base_dbm: 基础功率。

        Returns:
            float: 抖动后的功率。
        """

        val = base_dbm + random.uniform(-1.0, 1.0)
        if self.jam_cfg is not None:
            val += float(self.jam_cfg.get("power_boost_db", 0.0))
        return val

    def _snr_with_jitter(self, base_db: float) -> float:
        """应用SNR波动，并考虑干扰模式影响。

        Args:
            base_db: 基础SNR。

        Returns:
            float: 抖动后的SNR。
        """

        val = base_db + random.uniform(-2.0, 2.0)
        if self.jam_cfg is not None:
            val -= float(self.jam_cfg.get("snr_drop_db", 0.0))
        return max(val, -30.0)

    def _freq_with_jitter(self, base_hz: float) -> float:
        """应用±0.1%频率抖动。

        Args:
            base_hz: 基准频率。

        Returns:
            float: 抖动后的频率。
        """

        return base_hz * (1.0 + random.uniform(-0.001, 0.001))

    def _radar_signal(self, ts_ms: int) -> EWSignal:
        """生成雷达信号样本。

        Args:
            ts_ms: 时间戳毫秒。

        Returns:
            EWSignal: 雷达信号。
        """

        self.azimuth_deg = (self.azimuth_deg + 0.5) % 360.0
        self.range_m = self.range_m + random.uniform(-50.0, 50.0)

        pri_range = self.radar_cfg.get("pri_ms", (1.0, 3.0))
        pw_range = self.radar_cfg.get("pw_us", (0.5, 1.5))
        pri_ms = self._time_jitter(random.uniform(*pri_range))
        pw_us = self._time_jitter(random.uniform(*pw_range)) * 1000.0 / 1000.0

        return EWSignal(
            source_id=1,
            type=SignalType.SIG_RADAR,
            timestamp_ms=ts_ms,
            center_freq_hz=self._freq_with_jitter(self.center_freq_hz),
            bandwidth_hz=self.bandwidth_hz,
            signal_power_dbm=self._power_with_jitter(self.base_power_dbm),
            snr_db=self._snr_with_jitter(self.base_snr_db),
            azimuth_deg=self.azimuth_deg,
            elevation_deg=self.elevation_deg,
            range_m=self.range_m,
            pri_ms=pri_ms,
            pulse_width_us=pw_us,
            modulation=Modulation.MOD_NONE,
        )

    def _comm_signal(self, ts_ms: int) -> EWSignal:
        """生成通信信号样本。

        Args:
            ts_ms: 时间戳毫秒。

        Returns:
            EWSignal: 通信信号。
        """

        snr_low, snr_high = self.comm_cfg.get("snr_db", (10, 30))
        power_low, power_high = self.comm_cfg.get("power_dbm", (-30, -10))
        bw_hz = float(self.comm_cfg.get("bw", 1e6))
        freq_hz = float(self.comm_cfg.get("freq", 1e9))

        return EWSignal(
            source_id=2,
            type=SignalType.SIG_COMM,
            timestamp_ms=ts_ms,
            center_freq_hz=self._freq_with_jitter(freq_hz),
            bandwidth_hz=bw_hz,
            signal_power_dbm=self._power_with_jitter(random.uniform(power_low, power_high)),
            snr_db=self._snr_with_jitter(random.uniform(snr_low, snr_high)),
            azimuth_deg=random.uniform(0.0, 360.0),
            elevation_deg=random.uniform(-10.0, 10.0),
            range_m=-1.0,
            pri_ms=0.0,
            pulse_width_us=0.0,
            modulation=self.comm_cfg.get("mod", Modulation.MOD_NONE),
        )

    def _jam_signal(self, ts_ms: int) -> Optional[EWSignal]:
        """生成干扰信号样本。

        Args:
            ts_ms: 时间戳毫秒。

        Returns:
            Optional[EWSignal]: 干扰信号或None。
        """

        if self.jam_cfg is None:
            return None

        return EWSignal(
            source_id=3,
            type=SignalType.SIG_JAM,
            timestamp_ms=ts_ms,
            center_freq_hz=self._freq_with_jitter(self.center_freq_hz),
            bandwidth_hz=self.bandwidth_hz * 1.2,
            signal_power_dbm=self._power_with_jitter(self.base_power_dbm + 3.0),
            snr_db=self._snr_with_jitter(self.base_snr_db - 10.0),
            azimuth_deg=self.azimuth_deg,
            elevation_deg=self.elevation_deg,
            range_m=self.range_m,
            pri_ms=self._time_jitter(1.0),
            pulse_width_us=self._time_jitter(1.0),
            modulation=Modulation.MOD_NONE,
        )

    def _send(self, sig: EWSignal) -> None:
        """以JSON与二进制双格式发送UDP数据包。

        Args:
            sig: 待发送信号。
        """

        js = sig.to_json().encode("utf-8")
        bi = sig.to_binary()
        try:
            self.sock.sendto(js, (self.udp_ip, self.udp_port))
            self.sock.sendto(bi, (self.udp_ip, self.udp_port))
        except Exception:
            pass

    def _loop(self) -> None:
        """仿真主循环，按`tick_hz`频率生成并发送信号。"""

        interval = 1.0 / max(self.tick_hz, 1.0)
        while self.running:
            ts_ms = int(time.time() * 1000)
            radar = self._radar_signal(ts_ms)
            comm = self._comm_signal(ts_ms)
            jam = self._jam_signal(ts_ms)

            self._send(radar)
            self._send(comm)
            if jam is not None:
                self._send(jam)

            time.sleep(interval)

