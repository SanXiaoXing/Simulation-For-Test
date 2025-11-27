"""总线与带宽监控。

提供 1553/CAN/UDP 的带宽配置、发送速率限制与统计。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List
import time


@dataclass
class BusStats:
    """总线统计。"""

    bytes_sent: int = 0
    packets_sent: int = 0
    bit_error_rate: float = 0.0
    errors: int = 0
    drops: int = 0
    last_update_ts: float = time.time()
    history_bytes: List[int] = field(default_factory=list)
    history_ts: List[float] = field(default_factory=list)


@dataclass
class BusConfig:
    """总线配置。"""

    name: str
    bandwidth_bps: int
    frame_size_bytes: int
    refresh_hz: float


class BusSimulator:
    """总线仿真与监控。"""

    def __init__(self, cfg: BusConfig) -> None:
        self.cfg = cfg
        self.stats = BusStats()

    def send_frame(self, payload_size: int) -> bool:
        """发送一帧，受带宽与刷新率限制并记录历史。"""

        now = time.time()
        elapsed = now - self.stats.last_update_ts
        max_bytes = int(self.cfg.bandwidth_bps * elapsed / 8.0) if elapsed > 0 else self.cfg.frame_size_bytes
        if self.stats.bytes_sent + payload_size > max_bytes:
            self.stats.drops += 1
            return False
        self.stats.bytes_sent += payload_size
        self.stats.packets_sent += 1
        self.stats.last_update_ts = now
        self.stats.history_bytes.append(self.stats.bytes_sent)
        self.stats.history_ts.append(now)
        if len(self.stats.history_bytes) > 200:
            self.stats.history_bytes = self.stats.history_bytes[-200:]
            self.stats.history_ts = self.stats.history_ts[-200:]
        return True
