from __future__ import annotations

import json
import math
import time
from typing import Dict, Optional

from PyQt5.QtCore import QObject, pyqtSignal, QTimer

from .models import FlightParameters, MFDConfig, MFDMode, NetworkConfig, TacticalInfo, WeaponState


class OutputMultiplexer:
    """输出多路复用器。"""

    def __init__(self, net: NetworkConfig) -> None:
        self.net = net
        self.icd_schema: Optional[Dict] = None
        self._udp = None
        self._tcp = None
        try:
            from ins_sim.io.udp import UdpSender
            self._udp = UdpSender(self.net.out_host, int(self.net.out_port))
        except Exception:
            self._udp = None
        try:
            from ins_sim.io.tcp import TcpSender
            self._tcp = TcpSender(self.net.out_host, int(self.net.out_port))
        except Exception:
            self._tcp = None

    def load_icd(self, path: Optional[str]) -> None:
        """加载ICD文件。"""

        if not path:
            self.icd_schema = None
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.icd_schema = json.load(f)
        except Exception:
            self.icd_schema = None

    def encode(self, fp: FlightParameters, ws: WeaponState, ti: TacticalInfo, ts: float, mode: MFDMode, page: str) -> bytes:
        """编码一帧MFD数据。"""

        payload = {
            "ts": ts,
            "mode": mode.value,
            "page": page,
            "flight": {
                "airspeed_mps": fp.airspeed_mps,
                "altitude_m": fp.altitude_m,
                "heading_deg": fp.heading_deg,
                "g_load": fp.g_load,
                "aoa_deg": fp.aoa_deg,
                "fuel_kg": fp.fuel_kg,
                "waypoint_name": fp.waypoint_name,
                "waypoint_distance_m": fp.waypoint_distance_m,
            },
            "weapon": {
                "selected": ws.selected,
                "status": ws.status,
                "locked": ws.locked,
                "max_range_m": ws.max_range_m,
                "min_range_m": ws.min_range_m,
                "launch_perm": ws.launch_perm,
                "ammo_missile": ws.ammo_missile,
                "ammo_gun": ws.ammo_gun,
            },
            "tactical": {
                "target_bearing_deg": ti.target_bearing_deg,
                "target_distance_m": ti.target_distance_m,
                "closure_rate_mps": ti.closure_rate_mps,
                "threat_level": ti.threat_level,
                "is_friend": ti.is_friend,
                "radar_tracks": ti.radar_tracks,
            },
        }
        if self.icd_schema and self.icd_schema.get("fields"):
            filtered = {}
            for f in self.icd_schema["fields"]:
                name = f.get("name")
                if not name:
                    continue
                parts = name.split(".")
                cur = payload
                ok = True
                for p in parts:
                    if isinstance(cur, dict) and p in cur:
                        cur = cur[p]
                    else:
                        ok = False
                        break
                if ok:
                    filtered[name] = cur
            payload = filtered or payload
        return json.dumps(payload, ensure_ascii=False).encode("utf-8")

    def bandwidth(self, msg_len_bytes: int, rate_hz: float) -> float:
        """计算带宽占用率(%)。"""

        bps = msg_len_bytes * rate_hz * 8.0
        if self.net.link_speed_bps <= 0:
            return 0.0
        return (bps / self.net.link_speed_bps) * 100.0

    def send(self, data: bytes) -> None:
        """发送数据。"""

        if self.net.protocol == "udp" and self._udp:
            try:
                self._udp.send(data)
            except Exception:
                pass
        elif self.net.protocol == "tcp" and self._tcp:
            try:
                self._tcp.send(data)
            except Exception:
                pass


class MFDSimulator(QObject):
    """多功能显示器仿真器。"""

    frame_signal = pyqtSignal(dict)

    def __init__(self, cfg: Optional[MFDConfig] = None) -> None:
        super().__init__()
        self.cfg = cfg or MFDConfig()
        self.net = OutputMultiplexer(NetworkConfig())
        self.fp = FlightParameters()
        self.ws = WeaponState()
        self.ti = TacticalInfo()
        self.page: str = "overview"
        self._timer = QTimer()
        self._timer.timeout.connect(self._on_tick)

    def start(self) -> None:
        """启动仿真。"""

        interval_ms = int(1000.0 / max(1.0, self.cfg.update_hz))
        self._timer.start(max(1, interval_ms))

    def stop(self) -> None:
        """停止仿真。"""

        self._timer.stop()

    def configure(self, cfg: Optional[MFDConfig] = None, net: Optional[NetworkConfig] = None) -> None:
        """应用配置。"""

        if cfg:
            self.cfg = cfg
        if net:
            self.net = OutputMultiplexer(net)
            self.net.load_icd(net.icd_path)

    def set_page(self, page: str) -> None:
        """设置当前显示页。"""

        self.page = page

    def toggle_lock(self) -> None:
        """交互：切换雷达锁定状态。"""

        self.ws.locked = not self.ws.locked

    def next_waypoint(self) -> None:
        """交互：切换航路点。"""

        name = self.fp.waypoint_name
        idx = int(name[2:]) if name.startswith("WP") else 1
        idx = (idx % 5) + 1
        self.fp.waypoint_name = f"WP{idx}"
        self.fp.waypoint_distance_m = max(1000.0, (self.fp.waypoint_distance_m - 500.0))

    def _on_tick(self) -> None:
        """一次仿真步。"""

        t = time.time()
        self.fp.airspeed_mps = max(0.0, self.fp.airspeed_mps + math.sin(t * 0.25) * 0.9)
        self.fp.altitude_m = max(0.0, self.fp.altitude_m + math.sin(t * 0.18) * 1.2)
        self.fp.heading_deg = (self.fp.heading_deg + 0.6) % 360.0
        self.fp.g_load = 1.0 + 0.35 * math.sin(t * 0.5)
        self.fp.aoa_deg = 5.0 + 2.0 * math.sin(t * 0.7)
        self.fp.fuel_kg = max(0.0, self.fp.fuel_kg - 0.05)

        # 武器/雷达状态
        self.ws.launch_perm = self.ws.locked and (self.ti.target_distance_m < self.ws.max_range_m) and (self.ti.target_distance_m > self.ws.min_range_m)

        # 雷达与目标
        self.ti.target_bearing_deg = (self.ti.target_bearing_deg + 1.0) % 360.0
        self.ti.target_distance_m = max(500.0, self.ti.target_distance_m + self.ti.closure_rate_mps * 0.1)
        self.ti.is_friend = (math.sin(t * 0.22) > 0.0)
        self.ti.radar_tracks = int(5 + 3 * max(0.0, math.sin(t * 0.3)))

        payload = self.net.encode(self.fp, self.ws, self.ti, t, self.cfg.mode, self.page)
        self.net.send(payload)
        bw = self.net.bandwidth(len(payload), self.cfg.update_hz)
        self.frame_signal.emit({"ts": t, "fp": self.fp, "ws": self.ws, "ti": self.ti, "bw_pct": bw, "page": self.page})

