#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：Simulation 
@File    ：radar_core.py
@Author  ：SanXiaoXing
@Date    ：2025/11/20
@Description: 雷达接口特征模拟器核心业务模块 - 包含数据帧编解码、雷达仿真核心和网络通信
"""
import math
import struct
import time
import random
import socket
import threading
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from enum import Enum

# ----------------------------- 数据帧结构定义 -----------------------------
class RadarMode(Enum):
    """雷达工作模式枚举"""
    VELOCITY_SEARCH = "速度搜索模式"
    RANGE_SEARCH = "搜索测距模式"
    TARGET_TRACK = "目标跟踪模式"
    SCAN_TRACK = "扫描跟踪模式"
    AIR_COMBAT = "空中格斗模式"
    MAP_MAPPING = "地图测绘模式"
    FREEZE_FRAME = "画面冻结模式"
    BEAM_SHARPENING = "波束锐化模式"
    BEACON = "信标模式"
    WEATHER_DETECT = "气象探测模式"
    COLLISION_AVOID = "防撞模式"
    IDENTIFY = "识别模式"
    ANTI_JAM = "抗干扰模式"
    SEA_SEARCH_1 = "空海搜索模式1"
    SEA_SEARCH_2 = "空海搜索模式2"

class TargetType(Enum):
    """目标类型枚举"""
    UNKNOWN = 0
    AIR = 1
    SURFACE = 2
    MISSILE = 3

@dataclass
class ImageTarget:
    """图像目标数据结构"""
    id: int
    type: int
    distance_m: float
    azimuth_deg: float
    frequency_hz: float
    distance_30ms_m: float
    azimuth_30ms_deg: float
    speed_m_s: float
    direction_deg: float

@dataclass
class RadarTarget:
    """雷达目标数据结构"""
    id: int
    distance_m: float
    azimuth_deg: float
    rcs_db: float
    velocity_m_s: float

@dataclass
class MotionTarget:
    """运动目标数据结构

    保存目标的极坐标位置与运动参数，用于生成按规律运动的目标。
    """
    id: int
    distance_m: float
    azimuth_deg: float
    radial_speed_m_s: float
    angular_speed_deg_s: float
    type: int

@dataclass
class FireControlRequest:
    """火控请求数据结构"""
    requested_target_id: int

@dataclass
class DataFrame:
    """数据帧结构"""
    header: int = 0xAA55  # 包头
    target: int = 0       # 目标标识
    length: int = 0       # 数据总长度
    image_target_num: int = 0
    image_targets: List[ImageTarget] = None
    radar_target_num: int = 0
    radar_targets: List[RadarTarget] = None
    requested_target_num: int = 0
    requested_target_ids: List[int] = None
    
    def __post_init__(self):
        if self.image_targets is None:
            self.image_targets = []
        if self.radar_targets is None:
            self.radar_targets = []
        if self.requested_target_ids is None:
            self.requested_target_ids = []

# ----------------------------- 数据帧编解码模块 -----------------------------
class DataFrameCodec:
    """数据帧编解码器"""
    
    @staticmethod
    def encode_frame(frame: DataFrame) -> bytes:
        """编码数据帧为字节流"""
        # 计算动态长度（实际字节数）：
        # 头部2 + 目标1 + 长度1 + 图像数1 + 雷达数1 + 请求数1 = 7
        # 图像目标：每个 2（ID+类型） + 7*8（double） = 58 字节
        # 雷达目标：每个 2（ID+保留） + 4*8（double） = 34 字节
        expected_len = 7 + frame.image_target_num * 58 + frame.radar_target_num * 34 + frame.requested_target_num
        # 长度字段为1字节，避免溢出
        frame.length = min(expected_len, 255)
        
        buffer = bytearray()
        
        # 包头 (2字节)
        buffer.extend(struct.pack('>H', frame.header))
        
        # 目标标识 (1字节)
        buffer.extend(struct.pack('B', frame.target))
        
        # 长度 (1字节)
        buffer.extend(struct.pack('B', frame.length))
        
        # 图像目标数量 (1字节)
        buffer.extend(struct.pack('B', frame.image_target_num))
        
        # 图像目标数据 (每个30字节)
        for target in frame.image_targets:
            buffer.extend(struct.pack('>BB', target.id, target.type))
            buffer.extend(struct.pack('>d', target.distance_m))
            buffer.extend(struct.pack('>d', target.azimuth_deg))
            buffer.extend(struct.pack('>d', target.frequency_hz))
            buffer.extend(struct.pack('>d', target.distance_30ms_m))
            buffer.extend(struct.pack('>d', target.azimuth_30ms_deg))
            buffer.extend(struct.pack('>d', target.speed_m_s))
            buffer.extend(struct.pack('>d', target.direction_deg))
        
        # 雷达目标数量 (1字节)
        buffer.extend(struct.pack('B', frame.radar_target_num))
        
        # 雷达目标数据 (每个18字节)
        for target in frame.radar_targets:
            buffer.extend(struct.pack('>BB', target.id, 0))  # 保留字节
            buffer.extend(struct.pack('>d', target.distance_m))
            buffer.extend(struct.pack('>d', target.azimuth_deg))
            buffer.extend(struct.pack('>d', target.rcs_db))
            buffer.extend(struct.pack('>d', target.velocity_m_s))
        
        # 火控请求数量 (1字节)
        buffer.extend(struct.pack('B', frame.requested_target_num))
        
        # 火控请求ID (每个1字节)
        for target_id in frame.requested_target_ids:
            buffer.extend(struct.pack('B', target_id))
        
        return bytes(buffer)
    
    @staticmethod
    def decode_frame(data: bytes) -> Optional[DataFrame]:
        """解码字节流为数据帧"""
        if len(data) < 4:
            return None
        
        try:
            offset = 0
            
            # 解析包头
            header = struct.unpack('>H', data[offset:offset+2])[0]
            offset += 2
            
            if header != 0xAA55:
                return None
            
            # 解析目标标识和长度
            target = struct.unpack('B', data[offset:offset+1])[0]
            offset += 1
            length = struct.unpack('B', data[offset:offset+1])[0]
            offset += 1
            
            frame = DataFrame(header=header, target=target, length=length)
            
            # 解析图像目标
            if offset < len(data):
                frame.image_target_num = struct.unpack('B', data[offset:offset+1])[0]
                offset += 1
                
                for i in range(frame.image_target_num):
                    if offset + 58 > len(data):
                        break
                    
                    target_id, target_type = struct.unpack('>BB', data[offset:offset+2])
                    offset += 2
                    
                    distance = struct.unpack('>d', data[offset:offset+8])[0]
                    offset += 8
                    azimuth = struct.unpack('>d', data[offset:offset+8])[0]
                    offset += 8
                    frequency = struct.unpack('>d', data[offset:offset+8])[0]
                    offset += 8
                    distance_30ms = struct.unpack('>d', data[offset:offset+8])[0]
                    offset += 8
                    azimuth_30ms = struct.unpack('>d', data[offset:offset+8])[0]
                    offset += 8
                    speed = struct.unpack('>d', data[offset:offset+8])[0]
                    offset += 8
                    direction = struct.unpack('>d', data[offset:offset+8])[0]
                    offset += 8
                    
                    frame.image_targets.append(ImageTarget(
                        id=target_id, type=target_type,
                        distance_m=distance, azimuth_deg=azimuth,
                        frequency_hz=frequency, distance_30ms_m=distance_30ms,
                        azimuth_30ms_deg=azimuth_30ms, speed_m_s=speed,
                        direction_deg=direction
                    ))
            
            # 解析雷达目标
            if offset < len(data):
                frame.radar_target_num = struct.unpack('B', data[offset:offset+1])[0]
                offset += 1
                
                for i in range(frame.radar_target_num):
                    if offset + 34 > len(data):
                        break
                    
                    target_id, _ = struct.unpack('>BB', data[offset:offset+2])
                    offset += 2
                    
                    distance = struct.unpack('>d', data[offset:offset+8])[0]
                    offset += 8
                    azimuth = struct.unpack('>d', data[offset:offset+8])[0]
                    offset += 8
                    rcs = struct.unpack('>d', data[offset:offset+8])[0]
                    offset += 8
                    velocity = struct.unpack('>d', data[offset:offset+8])[0]
                    offset += 8
                    
                    frame.radar_targets.append(RadarTarget(
                        id=target_id, distance_m=distance,
                        azimuth_deg=azimuth, rcs_db=rcs,
                        velocity_m_s=velocity
                    ))
            
            # 解析火控请求
            if offset < len(data):
                frame.requested_target_num = struct.unpack('B', data[offset:offset+1])[0]
                offset += 1
                
                for i in range(frame.requested_target_num):
                    if offset >= len(data):
                        break
                    target_id = struct.unpack('B', data[offset:offset+1])[0]
                    offset += 1
                    frame.requested_target_ids.append(target_id)
            
            return frame
            
        except (struct.error, IndexError):
            return None

# ----------------------------- 雷达仿真核心 -----------------------------
class RadarSimulatorCore:
    """雷达仿真核心类"""
    
    def __init__(self):
        self.current_mode = RadarMode.RANGE_SEARCH
        self.max_image_targets = 8
        self.max_radar_targets = 8
        self.frame_counter = 0
        self.is_running = False
        self.motion_targets: List[MotionTarget] = []
        self.motion_mode: str = "linear"
        self._last_update_ts: Optional[float] = None
        
        # 雷达状态参数
        self.radar_status = {
            'power_on': True,
            'antenna_angle': 0.0,
            'scan_rate': 60.0,  # 度/秒
            'frequency': 9.4e9,  # Hz
            'prf': 1000,  # 脉冲重复频率
            'bandwidth': 1e6,  # 带宽
        }
        
        # 目标生成参数
        self.target_params = {
            'air_target_prob': 0.6,
            'surface_target_prob': 0.3,
            'missile_target_prob': 0.1,
            'max_distance': 50000,  # 米
            'min_distance': 500,    # 米
            'max_speed': 400,     # m/s
            'min_speed': 0,        # m/s
        }
    
    def set_mode(self, mode: RadarMode):
        """设置雷达工作模式"""
        self.current_mode = mode
        # 根据模式调整参数
        mode_configs = {
            RadarMode.VELOCITY_SEARCH: {'scan_rate': 120.0, 'frequency': 9.6e9},
            RadarMode.RANGE_SEARCH: {'scan_rate': 60.0, 'frequency': 9.4e9},
            RadarMode.TARGET_TRACK: {'scan_rate': 30.0, 'frequency': 9.5e9},
            RadarMode.SCAN_TRACK: {'scan_rate': 45.0, 'frequency': 9.4e9},
            RadarMode.AIR_COMBAT: {'scan_rate': 180.0, 'frequency': 9.7e9},
            RadarMode.MAP_MAPPING: {'scan_rate': 15.0, 'frequency': 9.3e9},
            RadarMode.FREEZE_FRAME: {'scan_rate': 0.0, 'frequency': 9.4e9},
            RadarMode.BEAM_SHARPENING: {'scan_rate': 20.0, 'frequency': 9.8e9},
            RadarMode.BEACON: {'scan_rate': 0.0, 'frequency': 1.0e9},
            RadarMode.WEATHER_DETECT: {'scan_rate': 25.0, 'frequency': 5.6e9},
            RadarMode.COLLISION_AVOID: {'scan_rate': 90.0, 'frequency': 9.9e9},
            RadarMode.ANTI_JAM: {'scan_rate': 100.0, 'frequency': 10.0e9},
            RadarMode.SEA_SEARCH_1: {'scan_rate': 40.0, 'frequency': 9.2e9},
            RadarMode.SEA_SEARCH_2: {'scan_rate': 35.0, 'frequency': 9.1e9},
        }
        
        if mode in mode_configs:
            config = mode_configs[mode]
            self.radar_status.update(config)

    def set_motion_mode(self, mode: str):
        """设置目标运动模式

        支持"random"随机、"linear"直线运动、"circular"圆周运动。
        """
        self.motion_mode = mode
        self._init_motion_targets()

    def _init_motion_targets(self):
        """初始化运动目标列表

        根据运动模式创建固定数量的目标用于后续生成。
        """
        self.motion_targets = []
        count = max(self.max_image_targets, self.max_radar_targets)
        base_ids = list(range(101, 101 + count))
        if self.motion_mode == "circular":
            radius = 20000.0
            for i, tid in enumerate(base_ids):
                az = (i * (360.0 / count)) % 360.0
                ang_speed = 20.0 + (i % 3) * 10.0
                self.motion_targets.append(MotionTarget(
                    id=tid, distance_m=radius, azimuth_deg=az,
                    radial_speed_m_s=0.0, angular_speed_deg_s=ang_speed,
                    type=random.choice([TargetType.AIR.value, TargetType.SURFACE.value, TargetType.MISSILE.value])
                ))
        else:
            for i, tid in enumerate(base_ids):
                dist = 8000.0 + (i % 6) * 4000.0
                az = (30.0 + i * (360.0 / count)) % 360.0
                r_speed = 150.0 + (i % 4) * 50.0
                ang_speed = ((-1) ** (i % 2)) * 5.0
                self.motion_targets.append(MotionTarget(
                    id=tid, distance_m=dist, azimuth_deg=az,
                    radial_speed_m_s=r_speed, angular_speed_deg_s=ang_speed,
                    type=random.choice([TargetType.AIR.value, TargetType.SURFACE.value, TargetType.MISSILE.value])
                ))

    def _step_motion(self, dt: float):
        """推进运动目标状态

        距离越界时反弹，方位角取模。
        """
        if self.motion_mode == "random":
            return
        if not self.motion_targets:
            self._init_motion_targets()
        for mt in self.motion_targets:
            mt.distance_m += mt.radial_speed_m_s * dt
            if mt.distance_m < 500.0:
                mt.distance_m = 500.0
                mt.radial_speed_m_s = abs(mt.radial_speed_m_s)
            elif mt.distance_m > 50000.0:
                mt.distance_m = 50000.0
                mt.radial_speed_m_s = -abs(mt.radial_speed_m_s)
            mt.azimuth_deg = (mt.azimuth_deg + mt.angular_speed_deg_s * dt) % 360.0
    
    def generate_image_targets(self) -> List[ImageTarget]:
        """生成图像目标数据"""
        if self.motion_mode == "random":
            num_targets = random.randint(0, self.max_image_targets)
            targets = []
            for i in range(num_targets):
                target_id = random.randint(100, 250)
                rand = random.random()
                if rand < self.target_params['missile_target_prob']:
                    target_type = TargetType.MISSILE.value
                    speed = random.uniform(200, 400)
                elif rand < self.target_params['missile_target_prob'] + self.target_params['surface_target_prob']:
                    target_type = TargetType.SURFACE.value
                    speed = random.uniform(0, 50)
                else:
                    target_type = TargetType.AIR.value
                    speed = random.uniform(50, 300)
                distance = random.uniform(self.target_params['min_distance'], self.target_params['max_distance'])
                azimuth = random.uniform(0, 360)
                direction = random.uniform(0, 360)
                distance_30ms = max(0, distance - speed * 0.03)
                azimuth_30ms = (azimuth + (speed/1000.0) * 0.03 * 360) % 360
                if target_type == TargetType.MISSILE.value:
                    frequency = random.choice([2.4e9, 5.8e9])
                elif target_type == TargetType.AIR.value:
                    frequency = random.choice([0.0, 1.2e9, 2.4e9])
                else:
                    frequency = 0.0
                targets.append(ImageTarget(
                    id=target_id, type=target_type, distance_m=distance,
                    azimuth_deg=azimuth, frequency_hz=frequency,
                    distance_30ms_m=distance_30ms, azimuth_30ms_deg=azimuth_30ms,
                    speed_m_s=speed, direction_deg=direction
                ))
            return targets
        # 运动模式生成
        n = min(self.max_image_targets, len(self.motion_targets) or self.max_image_targets)
        sel = self.motion_targets[:n] if self.motion_targets else []
        targets: List[ImageTarget] = []
        for mt in sel:
            if mt.type == TargetType.MISSILE.value:
                frequency = 5.8e9
            elif mt.type == TargetType.AIR.value:
                frequency = 2.4e9
            else:
                frequency = 0.0
            distance_30ms = max(0, mt.distance_m - mt.radial_speed_m_s * 0.03)
            azimuth_30ms = (mt.azimuth_deg + mt.angular_speed_deg_s * 0.03) % 360.0
            targets.append(ImageTarget(
                id=mt.id, type=mt.type, distance_m=mt.distance_m,
                azimuth_deg=mt.azimuth_deg, frequency_hz=frequency,
                distance_30ms_m=distance_30ms, azimuth_30ms_deg=azimuth_30ms,
                speed_m_s=abs(mt.radial_speed_m_s), direction_deg=mt.azimuth_deg
            ))
        return targets
    
    def generate_radar_targets(self) -> List[RadarTarget]:
        """生成雷达目标数据"""
        if self.motion_mode == "random":
            num_targets = random.randint(0, self.max_radar_targets)
            targets = []
            for i in range(num_targets):
                target_id = random.randint(100, 250)
                distance = random.uniform(self.target_params['min_distance'], self.target_params['max_distance'])
                azimuth = random.uniform(0, 360)
                velocity = random.uniform(-200, 400)
                base_rcs = random.uniform(-20, 20)
                if self.current_mode in [RadarMode.SEA_SEARCH_1, RadarMode.SEA_SEARCH_2]:
                    rcs = base_rcs + random.uniform(-5, 15)
                elif self.current_mode == RadarMode.AIR_COMBAT:
                    rcs = base_rcs - random.uniform(0, 10)
                else:
                    rcs = base_rcs
                targets.append(RadarTarget(
                    id=target_id, distance_m=distance, azimuth_deg=azimuth,
                    rcs_db=rcs, velocity_m_s=velocity
                ))
            return targets
        # 运动模式生成
        m = min(self.max_radar_targets, len(self.motion_targets) or self.max_radar_targets)
        sel = self.motion_targets[:m] if self.motion_targets else []
        targets: List[RadarTarget] = []
        for mt in sel:
            base_rcs = 20.0 - (mt.distance_m / 50000.0) * 20.0
            if self.current_mode in [RadarMode.SEA_SEARCH_1, RadarMode.SEA_SEARCH_2]:
                rcs = base_rcs + 5.0
            elif self.current_mode == RadarMode.AIR_COMBAT:
                rcs = base_rcs - 5.0
            else:
                rcs = base_rcs
            targets.append(RadarTarget(
                id=mt.id, distance_m=mt.distance_m, azimuth_deg=mt.azimuth_deg,
                rcs_db=rcs, velocity_m_s=mt.radial_speed_m_s
            ))
        return targets
    
    def generate_fire_control_requests(self) -> List[int]:
        """生成火控请求"""
        # 随机生成1-3个火控请求
        num_requests = random.randint(0, 3)
        requests = []
        
        for i in range(num_requests):
            target_id = random.randint(100, 250)
            requests.append(target_id)
        
        return requests
    
    def update_antenna_angle(self):
        """更新天线角度"""
        if self.radar_status['scan_rate'] > 0:
            self.radar_status['antenna_angle'] += self.radar_status['scan_rate'] * 0.03  # 30ms更新
            self.radar_status['antenna_angle'] %= 360
    
    def get_radar_status_data(self) -> Dict:
        """获取雷达状态数据"""
        self.update_antenna_angle()
        now = time.time()
        if self._last_update_ts is None:
            dt = 0.03
        else:
            dt = max(0.01, min(0.2, now - self._last_update_ts))
        self._last_update_ts = now
        self._step_motion(dt)
        return self.radar_status.copy()

# ----------------------------- 网络通信模块 -----------------------------
class NetworkInterface:
    """网络通信接口类"""
    
    def __init__(self):
        self.socket = None
        self.is_connected = False
        self.receive_callback = None
        self.receive_thread = None
        self.running = False
        self.client_sockets = []
        self.is_server = False
        
    def start_server(self, host: str = '127.0.0.1', port: int = 8888):
        """启动服务器"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((host, port))
            self.socket.listen(5)
            self.is_connected = True
            self.running = True
            self.is_server = True
            
            # 启动接收线程
            self.receive_thread = threading.Thread(target=self._accept_connections)
            self.receive_thread.daemon = True
            self.receive_thread.start()
            
            return True, f"服务器启动成功: {host}:{port}"
        except Exception as e:
            return False, f"服务器启动失败: {str(e)}"
    
    def connect_to_server(self, host: str = '127.0.0.1', port: int = 8888):
        """连接到服务器"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, port))
            self.is_connected = True
            self.running = True
            self.is_server = False
            
            # 启动接收线程
            self.receive_thread = threading.Thread(target=self._receive_data)
            self.receive_thread.daemon = True
            self.receive_thread.start()
            
            return True, f"连接服务器成功: {host}:{port}"
        except Exception as e:
            return False, f"连接服务器失败: {str(e)}"
    
    def send_data(self, data: bytes) -> bool:
        """发送数据"""
        if not self.is_connected:
            return False
        
        try:
            # 添加长度前缀
            length = len(data)
            payload = struct.pack('>I', length) + data
            if self.is_server:
                if not self.client_sockets:
                    return False
                ok = True
                for cs in list(self.client_sockets):
                    try:
                        cs.sendall(payload)
                    except Exception:
                        ok = False
                return ok
            else:
                if not self.socket:
                    return False
                self.socket.sendall(payload)
                return True
        except Exception as e:
            print(f"发送数据失败: {str(e)}")
            return False
    
    def set_receive_callback(self, callback):
        """设置接收数据回调函数"""
        self.receive_callback = callback
    
    def _accept_connections(self):
        """接受连接（服务器模式）"""
        while self.running:
            try:
                client_socket, address = self.socket.accept()
                print(f"客户端连接: {address}")
                self.client_sockets.append(client_socket)
                
                # 为每个客户端创建接收线程
                client_thread = threading.Thread(
                    target=self._handle_client, 
                    args=(client_socket,)
                )
                client_thread.daemon = True
                client_thread.start()
                
            except Exception as e:
                if self.running:
                    print(f"接受连接失败: {str(e)}")
                break
    
    def _handle_client(self, client_socket: socket.socket):
        """处理客户端连接"""
        try:
            while self.running:
                # 接收长度前缀
                length_data = self._recv_exact(client_socket, 4)
                if not length_data:
                    break
                
                length = struct.unpack('>I', length_data)[0]
                
                # 接收实际数据
                data = self._recv_exact(client_socket, length)
                if not data:
                    break
                
                # 调用回调函数处理数据
                if self.receive_callback:
                    self.receive_callback(data)
                # 回显到所有客户端，便于联调显示
                try:
                    self.send_data(data)
                except Exception:
                    pass
                    
        except Exception as e:
            print(f"客户端处理错误: {str(e)}")
        finally:
            try:
                self.client_sockets.remove(client_socket)
            except ValueError:
                pass
            client_socket.close()
    
    def _receive_data(self):
        """接收数据（客户端模式）"""
        try:
            while self.running:
                # 接收长度前缀
                length_data = self._recv_exact(self.socket, 4)
                if not length_data:
                    break
                
                length = struct.unpack('>I', length_data)[0]
                
                # 接收实际数据
                data = self._recv_exact(self.socket, length)
                if not data:
                    break
                
                try:
                    print(f"接收数据：{len(data)} 字节")
                except Exception:
                    pass

                # 调用回调函数处理数据
                if self.receive_callback:
                    self.receive_callback(data)
                    
        except Exception as e:
            print(f"接收数据错误: {str(e)}")
        finally:
            self.is_connected = False
    
    def _recv_exact(self, sock: socket.socket, n: int) -> Optional[bytes]:
        """精确接收指定长度的数据"""
        data = b''
        try:
            while len(data) < n:
                packet = sock.recv(n - len(data))
                if not packet:
                    return None
                data += packet
            return data
        except Exception:
            return None
    
    def stop(self):
        """停止网络通信"""
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        self.is_connected = False
        self.is_server = False
        for cs in list(self.client_sockets):
            try:
                cs.close()
            except:
                pass
        self.client_sockets.clear()
        
        if self.receive_thread:
            self.receive_thread.join(timeout=1)

# ----------------------------- 工具函数 -----------------------------
def get_mode_config(mode: RadarMode) -> Dict:
    """获取雷达模式的配置参数"""
    mode_configs = {
        RadarMode.VELOCITY_SEARCH: {'scan_rate': 120.0, 'frequency': 9.6e9, 'description': '速度搜索模式'},
        RadarMode.RANGE_SEARCH: {'scan_rate': 60.0, 'frequency': 9.4e9, 'description': '搜索测距模式'},
        RadarMode.TARGET_TRACK: {'scan_rate': 30.0, 'frequency': 9.5e9, 'description': '目标跟踪模式'},
        RadarMode.SCAN_TRACK: {'scan_rate': 45.0, 'frequency': 9.4e9, 'description': '扫描跟踪模式'},
        RadarMode.AIR_COMBAT: {'scan_rate': 180.0, 'frequency': 9.7e9, 'description': '空中格斗模式'},
        RadarMode.MAP_MAPPING: {'scan_rate': 15.0, 'frequency': 9.3e9, 'description': '地图测绘模式'},
        RadarMode.FREEZE_FRAME: {'scan_rate': 0.0, 'frequency': 9.4e9, 'description': '画面冻结模式'},
        RadarMode.BEAM_SHARPENING: {'scan_rate': 20.0, 'frequency': 9.8e9, 'description': '波束锐化模式'},
        RadarMode.BEACON: {'scan_rate': 0.0, 'frequency': 1.0e9, 'description': '信标模式'},
        RadarMode.WEATHER_DETECT: {'scan_rate': 25.0, 'frequency': 5.6e9, 'description': '气象探测模式'},
        RadarMode.COLLISION_AVOID: {'scan_rate': 90.0, 'frequency': 9.9e9, 'description': '防撞模式'},
        RadarMode.ANTI_JAM: {'scan_rate': 100.0, 'frequency': 10.0e9, 'description': '抗干扰模式'},
        RadarMode.SEA_SEARCH_1: {'scan_rate': 40.0, 'frequency': 9.2e9, 'description': '空海搜索模式1'},
        RadarMode.SEA_SEARCH_2: {'scan_rate': 35.0, 'frequency': 9.1e9, 'description': '空海搜索模式2'},
    }
    
    return mode_configs.get(mode, {'scan_rate': 60.0, 'frequency': 9.4e9, 'description': '默认模式'})

def create_sample_data_frame() -> DataFrame:
    """创建示例数据帧"""
    frame = DataFrame()
    
    # 添加示例图像目标
    frame.image_targets = [
        ImageTarget(
            id=101, type=TargetType.AIR.value,
            distance_m=15000.0, azimuth_deg=45.0,
            frequency_hz=2.4e9, distance_30ms_m=14950.0,
            azimuth_30ms_deg=45.1, speed_m_s=150.0,
            direction_deg=90.0
        ),
        ImageTarget(
            id=102, type=TargetType.SURFACE.value,
            distance_m=25000.0, azimuth_deg=120.0,
            frequency_hz=0.0, distance_30ms_m=24980.0,
            azimuth_30ms_deg=120.0, speed_m_s=30.0,
            direction_deg=180.0
        )
    ]
    frame.image_target_num = len(frame.image_targets)
    
    # 添加示例雷达目标
    frame.radar_targets = [
        RadarTarget(
            id=201, distance_m=15000.0,
            azimuth_deg=45.0, rcs_db=5.0,
            velocity_m_s=150.0
        ),
        RadarTarget(
            id=202, distance_m=25000.0,
            azimuth_deg=120.0, rcs_db=-3.0,
            velocity_m_s=30.0
        )
    ]
    frame.radar_target_num = len(frame.radar_targets)
    
    # 添加火控请求
    frame.requested_target_ids = [101, 201]
    frame.requested_target_num = len(frame.requested_target_ids)
    
    return frame
