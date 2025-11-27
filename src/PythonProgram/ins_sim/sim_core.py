from __future__ import annotations

import json
import math
import threading
import time
from dataclasses import dataclass
from typing import Callable, Dict, Optional

from PyQt5.QtCore import QObject, pyqtSignal

from .models import (
    INSParameters,
    IMUFaultConfig,
    NetworkConfig,
    RecordConfig,
    TrajectoryType,
    VehicleState,
    clamp,
    deg2rad,
    rad2deg,
    gaussian_noise,
)


class TrajectoryGenerator:
    """运动轨迹生成器。

    根据设定类型生成直线、曲线、转弯等轨迹，更新飞行器状态。

    Attributes:
        traj_type: 轨迹类型。
        turn_rate_dps: 转弯角速度(度/秒)。
        curve_freq_hz: 曲线频率(Hz)。
    """

    def __init__(self, traj_type: TrajectoryType = TrajectoryType.STRAIGHT) -> None:
        self.traj_type = traj_type
        self.turn_rate_dps = 3.0
        self.curve_freq_hz = 0.05

    def step(self, st: VehicleState, params: INSParameters, dt: float) -> None:
        """推进一步轨迹状态。

        Args:
            st: 当前状态(就地更新)。
            params: 惯导参数。
            dt: 时间步长(秒)。
        """

        if self.traj_type == TrajectoryType.STRAIGHT:
            yaw_deg = st.attitude_deg[2]
        elif self.traj_type == TrajectoryType.TURN:
            yaw_deg = st.attitude_deg[2] + self.turn_rate_dps * dt
        elif self.traj_type == TrajectoryType.CURVE:
            yaw_deg = st.attitude_deg[2] + math.sin(2.0 * math.pi * self.curve_freq_hz * time.time()) * 2.0
        else:
            yaw_deg = st.attitude_deg[2]

        st.attitude_deg = (st.attitude_deg[0], st.attitude_deg[1], yaw_deg)

        v = st.groundspeed_mps
        yaw_rad = deg2rad(yaw_deg)
        dn = v * math.cos(yaw_rad) * dt
        de = v * math.sin(yaw_rad) * dt
        dlat = (dn / params.earth_radius_m) * (180.0 / math.pi)
        dlon = (de / (params.earth_radius_m * math.cos(deg2rad(st.lat_deg)))) * (180.0 / math.pi)
        st.lat_deg += dlat
        st.lon_deg += dlon

        st.body_rates_rps = (st.body_rates_rps[0], st.body_rates_rps[1], deg2rad(self.turn_rate_dps) if self.traj_type == TrajectoryType.TURN else 0.0)
        st.body_accel_mps2 = (0.0, 0.0, 0.0)


class IMUSensor:
    """IMU传感器模拟(陀螺+加速度计)。

    提供噪声、零偏、比例因子与异常注入。
    """

    def __init__(self, params: INSParameters, faults: Optional[IMUFaultConfig] = None) -> None:
        self.params = params
        self.faults = faults or IMUFaultConfig()
        self._bias_g = self.params.imu_bias_gyro_rps
        self._bias_a = self.params.imu_bias_accel_mps2

    def read(self, st: VehicleState) -> Dict[str, float]:
        """读取IMU三轴数据。

        Args:
            st: 飞行器状态。

        Returns:
            包含加速度(ax, ay, az)与角速率(wx, wy, wz)字典。
        """

        wx = st.body_rates_rps[0]
        wy = st.body_rates_rps[1]
        wz = st.body_rates_rps[2]

        ax = st.body_accel_mps2[0]
        ay = st.body_accel_mps2[1]
        az = st.body_accel_mps2[2]

        wx = (wx * (1.0 + self.params.scale_factor_gyro)) + self._bias_g + gaussian_noise(self.params.imu_noise_gyro_rps)
        wy = (wy * (1.0 + self.params.scale_factor_gyro)) + self._bias_g + gaussian_noise(self.params.imu_noise_gyro_rps)
        wz = (wz * (1.0 + self.params.scale_factor_gyro)) + self._bias_g + gaussian_noise(self.params.imu_noise_gyro_rps)

        ax = (ax * (1.0 + self.params.scale_factor_accel)) + self._bias_a + gaussian_noise(self.params.imu_noise_accel_mps2)
        ay = (ay * (1.0 + self.params.scale_factor_accel)) + self._bias_a + gaussian_noise(self.params.imu_noise_accel_mps2)
        az = (az * (1.0 + self.params.scale_factor_accel)) + self._bias_a + gaussian_noise(self.params.imu_noise_accel_mps2)

        if self.faults.bias_step:
            wx += self.faults.bias_step_value
            wy += self.faults.bias_step_value
            wz += self.faults.bias_step_value
            ax += self.faults.bias_step_value
            ay += self.faults.bias_step_value
            az += self.faults.bias_step_value

        if self.faults.spike and random_event(self.faults.spike_prob):
            wx *= 5.0
            wy *= 5.0
            wz *= 5.0

        if self.faults.dropout and random_event(self.faults.dropout_prob):
            wx = 0.0
            wy = 0.0
            wz = 0.0
            ax = 0.0
            ay = 0.0
            az = 0.0

        if self.faults.saturation:
            ax = clamp(ax, -self.faults.saturation_limit_accel, self.faults.saturation_limit_accel)
            ay = clamp(ay, -self.faults.saturation_limit_accel, self.faults.saturation_limit_accel)
            az = clamp(az, -self.faults.saturation_limit_accel, self.faults.saturation_limit_accel)
            wx = clamp(wx, -self.faults.saturation_limit_gyro, self.faults.saturation_limit_gyro)
            wy = clamp(wy, -self.faults.saturation_limit_gyro, self.faults.saturation_limit_gyro)
            wz = clamp(wz, -self.faults.saturation_limit_gyro, self.faults.saturation_limit_gyro)

        return {"ax": ax, "ay": ay, "az": az, "wx": wx, "wy": wy, "wz": wz}


def random_event(prob: float) -> bool:
    """随机事件触发。"""

    import random

    return random.random() < prob


class NavComputer:
    """简化惯导导航解算。

    将IMU角速率积分为姿态，将机体速度/加速度用于估计空速/地速与位置。
    """

    def __init__(self, params: INSParameters) -> None:
        self.params = params

    def mechanize(self, st: VehicleState, imu: Dict[str, float], dt: float) -> None:
        """执行一次解算更新。

        Args:
            st: 飞行器状态(就地更新)。
            imu: 传感器数据。
            dt: 步长。
        """

        pitch, roll, yaw = st.attitude_deg
        pitch += rad2deg(imu.get("wy", 0.0) * dt)
        roll += rad2deg(imu.get("wx", 0.0) * dt)
        yaw += rad2deg(imu.get("wz", 0.0) * dt)
        st.attitude_deg = (pitch, roll, yaw)

        st.airspeed_mps = max(0.0, st.airspeed_mps + imu.get("ax", 0.0) * dt)
        st.groundspeed_mps = max(0.0, st.groundspeed_mps + imu.get("ax", 0.0) * dt)


class OutputMultiplexer:
    """输出多路复用器。

    负责将仿真数据编码并通过各种接口发送，同时计算带宽占用。
    """

    def __init__(self, net: NetworkConfig) -> None:
        self.net = net
        self._udp = None
        self._tcp = None
        self.icd_schema: Optional[Dict] = None
        try:
            from .io.udp import UdpSender
            self._udp = UdpSender(self.net.out_host, int(self.net.out_port))
        except Exception:
            self._udp = None
        try:
            from .io.tcp import TcpSender
            self._tcp = TcpSender(self.net.out_host, int(self.net.out_port))
        except Exception:
            self._tcp = None

    def load_icd(self, path: Optional[str]) -> None:
        """加载ICD文件。"""

        if not path:
            self.icd_schema = None
            return
        try:
            import json
            with open(path, "r", encoding="utf-8") as f:
                self.icd_schema = json.load(f)
        except Exception:
            self.icd_schema = None

    def encode(self, st: VehicleState, imu: Dict[str, float], ts: float) -> bytes:
        """编码一帧数据。"""

        payload = {
            "timestamp": ts,
            "lat_deg": st.lat_deg,
            "lon_deg": st.lon_deg,
            "alt_m": st.alt_m,
            "airspeed_mps": st.airspeed_mps,
            "groundspeed_mps": st.groundspeed_mps,
            "attitude": {"pitch": st.attitude_deg[0], "roll": st.attitude_deg[1], "yaw": st.attitude_deg[2]},
            "imu": imu,
        }
        if self.icd_schema and self.icd_schema.get("fields"):
            # 简单字段筛选/映射
            filtered = {}
            for f in self.icd_schema["fields"]:
                name = f.get("name")
                if name in payload:
                    filtered[name] = payload[name]
            payload = filtered or payload
        return json.dumps(payload, ensure_ascii=False).encode("utf-8")

    def bandwidth(self, msg_len_bytes: int, rate_hz: float) -> float:
        """计算带宽占用率(%)。"""

        bps = msg_len_bytes * rate_hz * 8.0
        if self.net.link_speed_bps <= 0:
            return 0.0
        return (bps / self.net.link_speed_bps) * 100.0

    def send(self, data: bytes) -> None:
        """发送一帧数据。"""

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


class INSSimulator(QObject):
    """惯性导航仿真器。

    将轨迹生成、IMU读数、导航解算与接口输出串联。
    """

    frame_signal = pyqtSignal(dict)

    def __init__(self, init_state: Optional[VehicleState] = None, params: Optional[INSParameters] = None) -> None:
        super().__init__()
        self.params = params or INSParameters()
        self.state = init_state or VehicleState()
        self.traj = TrajectoryGenerator(TrajectoryType.STRAIGHT)
        self.imu = IMUSensor(self.params)
        self.nav = NavComputer(self.params)
        self.net = OutputMultiplexer(NetworkConfig())
        self.record = RecordConfig()
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self.running = False
        self._ctrl_listener = None

    def configure(self, params: Optional[INSParameters] = None, net: Optional[NetworkConfig] = None, faults: Optional[IMUFaultConfig] = None, traj_type: Optional[TrajectoryType] = None) -> None:
        """应用配置变更。"""

        if params:
            self.params = params
        if net:
            self.net = OutputMultiplexer(net)
            self.net.load_icd(net.icd_path)
        if faults:
            self.imu.faults = faults
        if traj_type:
            self.traj.traj_type = traj_type

    def start(self) -> None:
        """启动仿真线程。"""

        if self.running:
            return
        self.running = True
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """停止仿真线程。"""

        self.running = False
        self._stop.set()
        if self._thread:
            try:
                self._thread.join(timeout=1.0)
            finally:
                self._thread = None
        if self._ctrl_listener:
            try:
                self._ctrl_listener.stop()
            except Exception:
                pass
            self._ctrl_listener = None

    def start_control_listener(self, port: int, log_path: str = "ins_ctrl.jsonl") -> None:
        """开启控制指令监听。"""

        try:
            from .io.udp import UdpListener
            def _on_recv(data: bytes) -> None:
                try:
                    s = data.decode("utf-8", errors="ignore")
                except Exception:
                    s = str(data)
                try:
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps({"ts": time.time(), "raw": s}, ensure_ascii=False) + "\n")
                except Exception:
                    pass
            self._ctrl_listener = UdpListener(int(port), on_recv=_on_recv)
            self._ctrl_listener.start()
        except Exception:
            self._ctrl_listener = None

    def _loop(self) -> None:
        """后台仿真循环。"""

        dt = 1.0 / max(1.0, self.params.update_hz)
        last = time.perf_counter()
        if self.record.enable_replay:
            try:
                with open(self.record.replay_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if self._stop.is_set():
                            break
                        now = time.perf_counter()
                        if now - last < dt:
                            time.sleep(max(0.0, dt - (now - last)))
                            continue
                        last = now
                        try:
                            rec = json.loads(line)
                        except Exception:
                            continue
                        # 更新状态(仅有限字段)
                        self.state.lat_deg = rec.get("lat", self.state.lat_deg)
                        self.state.lon_deg = rec.get("lon", self.state.lon_deg)
                        self.state.alt_m = rec.get("alt", self.state.alt_m)
                        att = rec.get("attitude")
                        if isinstance(att, (list, tuple)) and len(att) == 3:
                            self.state.attitude_deg = tuple(att)  # type: ignore
                        imu = rec.get("imu", {})
                        ts = rec.get("ts", time.time())
                        data_bytes = self.net.encode(self.state, imu, ts)
                        self.net.send(data_bytes)
                        frame = {
                            "timestamp": ts,
                            "state": self.state,
                            "imu": imu,
                            "bandwidth_pct": self.net.bandwidth(len(data_bytes), self.params.update_hz),
                        }
                        self.frame_signal.emit(frame)
            except Exception:
                pass
            return

        while not self._stop.is_set():
            now = time.perf_counter()
            if now - last < dt:
                time.sleep(max(0.0, dt - (now - last)))
                continue
            last = now

            self.traj.step(self.state, self.params, dt)
            imu = self.imu.read(self.state)
            self.nav.mechanize(self.state, imu, dt)

            ts = time.time()
            data_bytes = self.net.encode(self.state, imu, ts)
            self.net.send(data_bytes)

            frame = {
                "timestamp": ts,
                "state": self.state,
                "imu": imu,
                "bandwidth_pct": self.net.bandwidth(len(data_bytes), self.params.update_hz),
            }
            self.frame_signal.emit(frame)

            if self.record.enable_record:
                try:
                    with open(self.record.record_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps({"ts": ts, "payload_len": len(data_bytes), "imu": imu, "attitude": self.state.attitude_deg, "lat": self.state.lat_deg, "lon": self.state.lon_deg, "alt": self.state.alt_m}, ensure_ascii=False) + "\n")
                except Exception:
                    pass
