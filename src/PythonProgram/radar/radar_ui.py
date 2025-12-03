#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：Simulation 
@File    ：radar_ui.py
@Author  ：SanXiaoXing
@Date    ：2025/11/21
@Description: 雷达接口特征模拟器UI界面模块 - 包含PyQt5界面相关代码
"""
import math
import sys
import time
from typing import List, Dict, Optional

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QFont, QFontDatabase
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QComboBox, QSpinBox, QLineEdit,
    QTextEdit, QGroupBox, QFormLayout, QCheckBox, QDoubleSpinBox, QTabWidget,
    QMessageBox, QSizePolicy
)
from PyQt5.QtWidgets import QFileDialog
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
import json
import socket
import os

# 配置matplotlib中文字体支持
matplotlib.rcParams['font.sans-serif'] = [
    'Microsoft YaHei', 'SimHei', 'SimSun', 'Microsoft YaHei UI',
    'Noto Sans CJK SC', 'Arial Unicode MS'
]
matplotlib.rcParams['axes.unicode_minus'] = False

# 导入业务逻辑模块
from radar_core import (
    RadarMode, DataFrameCodec, RadarSimulatorCore, NetworkInterface,
    ImageTarget, RadarTarget, DataFrame
)

# ----------------------------- UDP下发支持 -----------------------------
class UDPSender:
    """UDP发送器

    提供基于UDP的简单发送能力。

    Attributes:
        remote: 远端主机与端口元组。
        sock: UDP套接字对象。
    """

    def __init__(self, host: str, port: int):
        """初始化UDP发送器

        Args:
            host: 远端主机地址。
            port: 远端端口号。
        """
        self.remote = (host, int(port))
        self.sock: Optional[socket.socket] = None

    def open(self) -> bool:
        """打开UDP套接字

        Returns:
            True表示打开成功，False表示失败。
        """
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            return True
        except Exception:
            self.sock = None
            return False

    def send_json(self, obj: dict) -> bool:
        """发送JSON对象

        Args:
            obj: 待发送的字典对象，将序列化为UTF-8 JSON字符串。

        Returns:
            True表示发送成功。
        """
        if not self.sock:
            return False
        try:
            payload = json.dumps(obj, ensure_ascii=False).encode('utf-8')
            self.sock.sendto(payload, self.remote)
            return True
        except Exception:
            return False

    def close(self):
        """关闭UDP套接字"""
        try:
            if self.sock:
                self.sock.close()
        finally:
            self.sock = None


def compute_length(n_image: int, n_radar: int, n_req: int) -> int:
    """根据协议计算Length字段

    根据README公式：30*n + 18*m + k + 3。

    Args:
        n_image: 图像目标数量。
        n_radar: 雷达目标数量。
        n_req: 火控请求数量。

    Returns:
        计算得到的长度值（整型）。
    """
    return 30 * int(n_image) + 18 * int(n_radar) + int(n_req) + 3


def build_protocol_json(ip: str, port: int, card: Optional[str],
                        image_targets: List[Dict], radar_targets: List[Dict],
                        req_ids: List[int], frame_id: int = 1) -> Dict:
    """构建README协议格式的JSON对象

    Args:
        ip: 目标IP地址。
        port: 目标端口。
        card: 接口卡标识（可选）。
        image_targets: 图像目标列表。
        radar_targets: 雷达目标列表。
        req_ids: 火控请求的目标ID列表。
        frame_id: 数据帧的ID（默认为1）。

    Returns:
        满足README定义结构的字典对象。
    """
    n_image = len(image_targets)
    n_radar = len(radar_targets)
    n_req = len(req_ids)
    length = compute_length(n_image, n_radar, n_req)

    return {
        "IP": ip,
        "Port": int(port),
        "Card": card or "",
        "Data": {
            "ID": int(frame_id),
            "Length": length,
            "ImageTargets": {
                "count": n_image,
                "item_size": 30,
                "items": image_targets,
            },
            "RadarTargets": {
                "count": n_radar,
                "item_size": 18,
                "items": radar_targets,
            },
            "FireControlRequests": {
                "count": n_req,
                "item_size": 1,
                "items": [{"Requested_target_id": int(tid)} for tid in req_ids],
            },
        },
    }


def convert_image_targets(raw_targets: List[Dict]) -> List[Dict]:
    """将原始目标数据转换为协议所需的图像目标字典

    Args:
        raw_targets: 包含字段的字典列表。

    Returns:
        满足README协议字段命名的图像目标字典列表。
    """
    out: List[Dict] = []
    for t in raw_targets:
        out.append({
            "ImageTarget_id": int(t.get("id", 0)),
            "Type": int(t.get("type", 0)),
            "ImageTarget_distance_m": float(t.get("distance_m", 0.0)),
            "ImageTarget_azimuth_deg": float(t.get("azimuth_deg", 0.0)),
            "Frequency_hz": float(t.get("frequency_hz", 0.0)),
            "Distance_30ms_m": float(t.get("distance_30ms_m", 0.0)),
            "Azimuth_30ms_deg": float(t.get("azimuth_30ms_deg", 0.0)),
            "Speed_m_s": float(t.get("speed_m_s", 0.0)),
            "Direction_deg": float(t.get("direction_deg", 0.0)),
        })
    return out


def convert_radar_targets(raw_targets: List[Dict]) -> List[Dict]:
    """将原始目标数据转换为协议所需的雷达目标字典

    Args:
        raw_targets: 包含字段的字典列表。

    Returns:
        满足README协议字段命名的雷达目标字典列表。
    """
    out: List[Dict] = []
    for t in raw_targets:
        out.append({
            "RadarTarget_id": int(t.get("id", 0)),
            "RadarTarget_distance_m": float(t.get("distance_m", 0.0)),
            "RadarTarget_azimuth_deg": float(t.get("azimuth_deg", 0.0)),
            "Rcs_db": float(t.get("rcs_db", 0.0)),
            "Velocity_m_s": float(t.get("velocity_m_s", 0.0)),
        })
    return out


def load_device_config(path: str) -> Dict:
    """加载设备配置JSON

    支持键：IP, Port, Cards, Card, Channel。

    Args:
        path: 配置文件路径。

    Returns:
        解析后的配置字典，并注入便捷键。
    """
    with open(path, 'r', encoding='utf-8') as f:
        cfg = json.load(f)

    ip = cfg.get("IP")
    port = cfg.get("Port")
    cards = cfg.get("Cards") or []
    card_val = cfg.get("Card")
    if card_val:
        card = card_val
    else:
        if isinstance(cards, list) and cards:
            card = cards[0]
        elif isinstance(cards, str) and cards:
            card = cards
        else:
            card = None
    channel = cfg.get("Channel")

    interface = "udp" if ip and port else ("ieee1394" if card else "udp")

    try:
        port_int = int(port) if port is not None else 8888
    except Exception:
        port_int = 8888
    # 固定数据ID（优先取ID，否则取Channel）
    id_val = cfg.get("ID")
    if id_val is None:
        id_val = cfg.get("Channel")
    try:
        id_int = int(id_val) if id_val is not None else 1
    except Exception:
        id_int = 1

    return {
        **cfg,
        "interface": interface,
        "remote_host": ip or "127.0.0.1",
        "remote_port": port_int,
        "card": card or "",
        "channel": channel,
        "frame_id": id_int,
    }
# ----------------------------- GUI组件 -----------------------------

def _set_app_chinese_font(app: QtWidgets.QApplication):
    """设置应用中文字体
    
    优先选择系统常见中文字体，确保界面与图像中的中文正常显示。
    """
    preferred_fonts = [
        'Microsoft YaHei', 'SimHei', 'SimSun', 'Microsoft YaHei UI',
        'Noto Sans CJK SC', 'Arial Unicode MS'
    ]
    families = set(QFontDatabase().families())
    for fname in preferred_fonts:
        if fname in families:
            app.setFont(QFont(fname))
            break

class RadarCanvas(FigureCanvas):
    """雷达显示画布"""
    
    def __init__(self, parent=None, size=(6, 6)):
        fig = Figure(figsize=size) 
        self.ax = fig.add_subplot(111, projection='polar')
        super().__init__(fig)
        fig.tight_layout()
        self.ax.set_theta_zero_location("N")
        self.ax.set_theta_direction(-1)
        self.max_range = 50000.0
        self.radar_line = None
        self.target_scatter = None
        self.radar_pos = 0
        
    def plot_radar_scan(self, antenna_angle: float, targets: List[RadarTarget]):
        """绘制雷达扫描图像"""
        self.ax.clear()
        self.ax.set_theta_zero_location("N")
        self.ax.set_theta_direction(-1)
        
        # 绘制雷达扫描线
        theta = math.radians(antenna_angle)
        self.ax.plot([theta, theta], [0, self.max_range], 'g-', linewidth=2, alpha=0.7)
        
        # 绘制目标
        if targets:
            rs = []
            thetas = []
            labels = []
            colors = []
            sizes = []
            
            for target in targets:
                r = target.distance_m
                theta = math.radians(target.azimuth_deg)
                rs.append(r)
                thetas.append(theta)
                labels.append(str(target.id))
                
                # 根据RCS值设置颜色
                if target.rcs_db > 5:
                    colors.append('red')
                    sizes.append(100)
                elif target.rcs_db > -5:
                    colors.append('orange')
                    sizes.append(80)
                else:
                    colors.append('blue')
                    sizes.append(60)
            
            if rs:
                self.target_scatter = self.ax.scatter(thetas, rs, c=colors, s=sizes, alpha=0.8)
                for i, (th, r, label) in enumerate(zip(thetas, rs, labels)):
                    self.ax.annotate(label, (th, r), textcoords="offset points", 
                                   xytext=(5, 5), fontsize=8)
        
        # 设置显示范围
        self.ax.set_ylim(0, self.max_range)
        self.ax.set_title(f'雷达扫描显示', pad=20)
        self.ax.grid(True, alpha=0.3)
        
        # 添加距离环
        self.ax.set_rgrids([10000, 20000, 30000, 40000, 50000], 
                          ['10km', '20km', '30km', '40km', '50km'])
        
        self.draw()

class MainWindow(QMainWindow):
    """主窗口类"""
    
    # 定义信号
    data_received = pyqtSignal(bytes)
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("雷达接口特征模拟器仿真软件")
        self.resize(1400, 900)
        
        # 初始化核心组件
        self.core = RadarSimulatorCore()
        self.codec = DataFrameCodec()
        self.network = NetworkInterface()
        
        # 连接信号
        self.data_received.connect(self.on_data_received)
        self.network.set_receive_callback(self.on_network_data_received)
        
        # 定时器
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.on_update_timer)
        self.send_timer = QTimer()
        self.send_timer.timeout.connect(self.on_send_timer)
        self.json_sender: Optional[UDPSender] = None
        self.frame_seq: int = 1
        self.frame_fixed_id: int = 1
        self.current_card: str = ""
        # 默认设备配置路径（Radar_Connect/config/device.json）
        self.default_cfg_path: str = os.path.normpath(os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..', 'Radar_Connect', 'config', 'device.json'
        ))
        # 数据存储
        self.received_frames = []
        self.sent_frames = []
        self.is_sending = False
        self.last_received_targets: List[RadarTarget] = []
        self.last_sent_targets: List[RadarTarget] = []
        
        self.init_ui()
        try:
            self._try_load_default_config()
        except Exception:
            pass
        
    def init_ui(self):
        """初始化用户界面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧控制面板
        left_panel = self.create_left_panel()
        left_panel.setFixedWidth(380)
        left_panel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        main_layout.addWidget(left_panel)
        
        # 中间雷达显示
        center_panel = self.create_center_panel()
        center_panel.setFixedWidth(720)
        center_panel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        main_layout.addWidget(center_panel)
        
        # 右侧数据面板
        right_panel = self.create_right_panel()
        right_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main_layout.addWidget(right_panel)

        # 将额外宽度分配给右侧
        main_layout.setStretch(0, 0)
        main_layout.setStretch(1, 0)
        main_layout.setStretch(2, 1)
    
    def create_left_panel(self) -> QWidget:
        """创建左侧控制面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # 雷达模式组
        mode_group = QGroupBox("雷达工作模式")
        mode_layout = QFormLayout(mode_group)
        
        self.mode_combo = QComboBox()
        for mode in RadarMode:
            self.mode_combo.addItem(mode.value, mode)
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        mode_layout.addRow("当前模式:", self.mode_combo)
        
        # 模式参数显示
        self.mode_params_text = QTextEdit()
        self.mode_params_text.setReadOnly(True)
        self.mode_params_text.setMaximumHeight(100)
        mode_layout.addRow("模式参数:", self.mode_params_text)
        
        layout.addWidget(mode_group)
        
        # 网络连接组
        network_group = QGroupBox("网络连接")
        network_layout = QFormLayout(network_group)
        
        self.host_input = QLineEdit("127.0.0.1")
        self.port_input = QSpinBox()
        self.port_input.setRange(1000, 65535)
        self.port_input.setValue(8888)
        
        network_layout.addRow("主机地址:", self.host_input)
        network_layout.addRow("端口:", self.port_input)
        self.load_cfg_btn = QPushButton("加载接口配置")
        self.load_cfg_btn.clicked.connect(self.on_load_device_config)
        network_layout.addRow(self.load_cfg_btn)
        
        # 连接按钮（单一操作）
        button_layout = QHBoxLayout()
        self.apply_btn = QPushButton("应用UDP目标")
        self.apply_btn.clicked.connect(self.on_apply_udp_target)
        self.disconnect_btn = QPushButton("断开连接")
        self.disconnect_btn.clicked.connect(self.on_disconnect)
        self.disconnect_btn.setEnabled(False)

        button_layout.addWidget(self.apply_btn)
        button_layout.addWidget(self.disconnect_btn)
        network_layout.addRow(button_layout)
        
        # 连接状态
        self.connection_status = QLabel("未连接")
        network_layout.addRow("连接状态:", self.connection_status)
        
        layout.addWidget(network_group)
        
        # 数据发送控制组
        send_group = QGroupBox("数据发送控制")
        send_layout = QFormLayout(send_group)
        
        self.send_interval = QSpinBox()
        self.send_interval.setRange(100, 5000)
        self.send_interval.setValue(1000)
        self.send_interval.setSuffix(" ms")
        
        self.auto_send_check = QCheckBox("自动发送")
        self.auto_send_check.stateChanged.connect(self.on_auto_send_changed)
        
        self.send_btn = QPushButton("手动发送")
        self.send_btn.clicked.connect(self.on_manual_send)
        self.motion_mode_combo = QComboBox()
        self.motion_mode_combo.addItem("随机", "random")
        self.motion_mode_combo.addItem("直线", "linear")
        self.motion_mode_combo.addItem("圆周", "circular")
        self.motion_mode_combo.setCurrentIndex(1)
        self.motion_mode_combo.currentIndexChanged.connect(self.on_motion_mode_change)
        
        send_layout.addRow("发送间隔:", self.send_interval)
        send_layout.addRow(self.auto_send_check)
        send_layout.addRow(self.send_btn)
        send_layout.addRow("运动模式:", self.motion_mode_combo)
        
        layout.addWidget(send_group)
        
        # 雷达状态组
        status_group = QGroupBox("雷达状态")
        status_layout = QFormLayout(status_group)
        
        self.radar_status_text = QTextEdit()
        self.radar_status_text.setReadOnly(True)
        self.radar_status_text.setMaximumHeight(150)
        status_layout.addRow("状态信息:", self.radar_status_text)
        
        layout.addWidget(status_group)
        
        # 添加弹簧
        layout.addStretch()
        
        return panel
    
    def create_center_panel(self) -> QWidget:
        """创建中间显示面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # 雷达显示画布
        self.radar_canvas = RadarCanvas(self, size=(8, 8))
        self.radar_canvas.setFixedSize(600, 600)
        layout.addWidget(self.radar_canvas)
        
        # 控制按钮
        control_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("开始仿真")
        self.start_btn.clicked.connect(self.on_start_simulation)
        
        self.stop_btn = QPushButton("停止仿真")
        self.stop_btn.clicked.connect(self.on_stop_simulation)
        self.stop_btn.setEnabled(False)
        
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)
        control_layout.addStretch()
        
        layout.addLayout(control_layout)
        
        return panel
    
    def create_right_panel(self) -> QWidget:
        """创建右侧数据面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # 创建标签页
        tab_widget = QTabWidget()
        
        # 发送数据标签页
        send_tab = QWidget()
        send_layout = QVBoxLayout(send_tab)
        
        self.sent_data_table = QTableWidget(0, 9)
        self.sent_data_table.setHorizontalHeaderLabels([
            "帧序号", "图像目标数", "雷达目标数", "火控请求数", 
            "数据长度", "发送时间", "模式", "状态", "详情"
        ])
        self.sent_data_table.setAlternatingRowColors(True)
        send_layout.addWidget(self.sent_data_table)
        
        tab_widget.addTab(send_tab, "发送数据")
        
        # 接收数据标签页
        receive_tab = QWidget()
        receive_layout = QVBoxLayout(receive_tab)
        
        self.received_data_table = QTableWidget(0, 9)
        self.received_data_table.setHorizontalHeaderLabels([
            "帧序号", "图像目标数", "雷达目标数", "火控请求数", 
            "数据长度", "接收时间", "模式", "状态", "详情"
        ])
        self.received_data_table.setAlternatingRowColors(True)
        receive_layout.addWidget(self.received_data_table)
        
        tab_widget.addTab(receive_tab, "接收数据")
        
        # 日志标签页
        log_tab = QWidget()
        log_layout = QVBoxLayout(log_tab)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        log_layout.addWidget(self.log_text)
        
        # 日志控制按钮
        log_button_layout = QHBoxLayout()
        self.clear_log_btn = QPushButton("清空日志")
        self.clear_log_btn.clicked.connect(self.on_clear_log)
        log_button_layout.addWidget(self.clear_log_btn)
        log_button_layout.addStretch()
        log_layout.addLayout(log_button_layout)
        
        tab_widget.addTab(log_tab, "系统日志")
        
        layout.addWidget(tab_widget)
        
        return panel
    
    # ----------------------------- 事件处理 -----------------------------
    
    def on_mode_changed(self, index):
        """模式改变事件"""
        mode = self.mode_combo.itemData(index)
        self.core.set_mode(mode)
        
        # 更新模式参数显示
        status = self.core.get_radar_status_data()
        params_text = f"""
扫描速率: {status['scan_rate']:.1f}°/s
工作频率: {status['frequency']:.1e} Hz
脉冲重复频率: {status['prf']} Hz
带宽: {status['bandwidth']:.1e} Hz
"""
        self.mode_params_text.setPlainText(params_text)
        
        self.log(f"雷达模式切换到: {mode.value}")
    
    def on_start_server(self):
        """启用UDP发送器"""
        host = self.host_input.text()
        port = self.port_input.value()
        
        try:
            self._ensure_json_sender()
            self.connection_status.setText(f"UDP发送器: {host}:{port}")
            self.server_btn.setEnabled(False)
            self.client_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)
            self.log("UDP发送器已启用")
        except Exception as e:
            self.log(f"UDP发送器启用失败: {str(e)}")
    
    def on_connect_client(self):
        """连接UDP目标（应用目标地址）"""
        host = self.host_input.text()
        port = self.port_input.value()
        
        try:
            self._ensure_json_sender()
            self.connection_status.setText(f"UDP目标: {host}:{port}")
            self.server_btn.setEnabled(False)
            self.client_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)
            self.log("已应用UDP目标地址")
        except Exception as e:
            self.log(f"应用UDP目标失败: {str(e)}")
    
    def on_disconnect(self):
        """断开连接"""
        try:
            if self.json_sender:
                self.json_sender.close()
        except Exception:
            pass
        self.network.stop()
        self.connection_status.setText("未连接")
        try:
            self.apply_btn.setEnabled(True)
        except Exception:
            pass
        self.disconnect_btn.setEnabled(False)
        self.log("网络连接已断开")
    
    def on_auto_send_changed(self, state):
        """自动发送状态改变"""
        if state == Qt.Checked:
            interval = self.send_interval.value()
            self.send_timer.start(interval)
            self.send_btn.setEnabled(False)
            self.log(f"自动发送已启动，间隔: {interval}ms")
        else:
            self.send_timer.stop()
            self.send_btn.setEnabled(True)
            self.log("自动发送已停止")
    
    def on_apply_udp_target(self):
        """应用UDP目标并启用发送器"""
        host = self.host_input.text()
        port = self.port_input.value()
        try:
            self._ensure_json_sender()
            self.connection_status.setText(f"UDP目标: {host}:{port}")
            self.apply_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)
            self.log("已应用UDP目标地址并启用发送器")
        except Exception as e:
            self.log(f"应用UDP目标失败: {str(e)}")
    
    def on_load_device_config(self):
        """加载接口配置JSON文件并应用到UDP下发"""
        path, _ = QFileDialog.getOpenFileName(
            self, "选择设备配置JSON", "", "JSON Files (*.json);;All Files (*.*)"
        )
        if not path:
            return
        try:
            cfg = load_device_config(path)
            self.host_input.setText(cfg.get("remote_host", "127.0.0.1"))
            self.port_input.setValue(int(cfg.get("remote_port", 8888)))
            self.current_card = cfg.get("card", "")
            self.frame_fixed_id = cfg.get("frame_id", 1)
            # 仅更新界面，不进行连接，等待用户主动点击“应用UDP目标”
            self.connection_status.setText("未连接")
            try:
                self.apply_btn.setEnabled(True)
            except Exception:
                pass
            self.log(f"已加载接口配置: {path}")
        except Exception as e:
            self.log(f"加载配置失败: {str(e)}")

    def _ensure_json_sender(self):
        """基于当前主机与端口保证UDP发送器可用"""
        host = self.host_input.text().strip() or "127.0.0.1"
        port = int(self.port_input.value())
        self.json_sender = UDPSender(host, port)
        ok = self.json_sender.open()
        if ok:
            self.log(f"UDP目标: {host}:{port}")
        else:
            self.log("UDP发送器初始化失败")

    def _try_load_default_config(self):
        path = self.default_cfg_path
        if os.path.exists(path):
            cfg = load_device_config(path)
            self.host_input.setText(cfg.get("remote_host", "127.0.0.1"))
            self.port_input.setValue(int(cfg.get("remote_port", 8888)))
            self.current_card = cfg.get("card", "")
            self.frame_fixed_id = cfg.get("frame_id", 1)
            # 不自动连接，保持手动连接流程
            self.connection_status.setText("未连接")
            try:
                self.apply_btn.setEnabled(True)
                self.disconnect_btn.setEnabled(False)
            except Exception:
                pass
            self.log(f"已加载默认接口配置: {path}（未连接）")
    
    def on_send_timer(self):
        """定时发送数据"""
        self.send_frame()
    
    def on_manual_send(self):
        """手动发送数据"""
        self.send_frame()
    
    def on_start_simulation(self):
        """开始仿真"""
        self.core.is_running = True
        self.update_timer.start(100)  # 100ms更新一次
        self.core.set_motion_mode(self.motion_mode_combo.currentData())
        # 自动开始发送并立即发送一帧
        try:
            self.auto_send_check.setChecked(True)
            self.send_frame()
        except Exception:
            pass
        
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        self.log("雷达仿真已启动")
    
    def on_stop_simulation(self):
        """停止仿真"""
        self.core.is_running = False
        self.update_timer.stop()
        # 停止自动发送
        try:
            self.auto_send_check.setChecked(False)
        except Exception:
            pass
        
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        self.log("雷达仿真已停止")
    
    def on_update_timer(self):
        """更新定时器"""
        # 更新雷达状态显示
        status = self.core.get_radar_status_data()
        status_text = f"""
电源状态: {'开启' if status['power_on'] else '关闭'}
天线角度: {status['antenna_angle']:.1f}°
扫描速率: {status['scan_rate']:.1f}°/s
工作频率: {status['frequency']:.1e} Hz
脉冲重复频率: {status['prf']} Hz
"""
        self.radar_status_text.setPlainText(status_text)
        
        # 更新雷达显示
        if self.last_received_targets:
            self.radar_canvas.plot_radar_scan(status['antenna_angle'], self.last_received_targets)
        elif self.last_sent_targets:
            self.radar_canvas.plot_radar_scan(status['antenna_angle'], self.last_sent_targets)
        else:
            radar_targets = self.core.generate_radar_targets()
            self.radar_canvas.plot_radar_scan(status['antenna_angle'], radar_targets)

    def on_motion_mode_change(self, idx: int):
        """运动模式切换"""
        mode = self.motion_mode_combo.itemData(idx)
        try:
            self.core.set_motion_mode(mode)
        except Exception:
            pass
    
    def on_network_data_received(self, data: bytes):
        """网络数据接收回调"""
        self.data_received.emit(data)
    
    def on_data_received(self, data: bytes):
        """处理接收到的数据"""
        try:
            # 解码数据帧
            frame = self.codec.decode_frame(data)
            if frame:
                self.process_received_frame(frame)
                # 将接收的雷达目标用于画布显示
                if frame.radar_targets:
                    self.last_received_targets = frame.radar_targets
                # 控制台打印十六进制预览
                hexdata = self._hexdump(data, max_len=256)
                print("接收数据内容: 帧长度=", len(data))
                print("HEX: ", hexdata)
            else:
                self.log("接收到无效数据帧")
        except Exception as e:
            self.log(f"数据处理错误: {str(e)}")
    
    def send_frame(self):
        """发送数据帧"""
        try:
            # 生成数据
            image_targets = self.core.generate_image_targets()
            radar_targets = self.core.generate_radar_targets()
            fire_control_requests = self.core.generate_fire_control_requests()
            
            # 创建数据帧
            frame = DataFrame()
            frame.image_targets = image_targets
            frame.image_target_num = len(image_targets)
            frame.radar_targets = radar_targets
            frame.radar_target_num = len(radar_targets)
            frame.requested_target_ids = fire_control_requests
            frame.requested_target_num = len(fire_control_requests)
            
            # 构建JSON并通过UDP下发
            ip = self.host_input.text().strip() or "127.0.0.1"
            port = int(self.port_input.value())
            img_raw = [{
                "id": t.id,
                "type": getattr(t, 'type', 0),
                "distance_m": t.distance_m,
                "azimuth_deg": t.azimuth_deg,
                "frequency_hz": getattr(t, 'frequency_hz', 0.0),
                "distance_30ms_m": getattr(t, 'distance_30ms_m', t.distance_m),
                "azimuth_30ms_deg": getattr(t, 'azimuth_30ms_deg', t.azimuth_deg),
                "speed_m_s": getattr(t, 'speed_m_s', 0.0),
                "direction_deg": getattr(t, 'direction_deg', 0.0),
            } for t in image_targets]
            rad_raw = [{
                "id": t.id,
                "distance_m": t.distance_m,
                "azimuth_deg": t.azimuth_deg,
                "rcs_db": getattr(t, 'rcs_db', 0.0),
                "velocity_m_s": getattr(t, 'velocity_m_s', 0.0),
            } for t in radar_targets]
            img_items = convert_image_targets(img_raw)
            rad_items = convert_radar_targets(rad_raw)
            obj = build_protocol_json(
                ip=ip,
                port=port,
                card=self.current_card,
                image_targets=img_items,
                radar_targets=rad_items,
                req_ids=fire_control_requests,
                frame_id=self.frame_fixed_id,
            )
            if not self.json_sender:
                self._ensure_json_sender()
            success = self.json_sender.send_json(obj) if self.json_sender else False
            status_text = "成功" if success else "失败"
            # 将本次发送的雷达目标用于画布显示
            self.last_sent_targets = radar_targets
            
            # 记录发送结果到表格（无论成功与否）
            self.sent_frames.append({
                'frame': frame,
                'time': time.strftime('%H:%M:%S'),
                'mode': self.core.current_mode.value,
                'status': status_text
            })
            self.update_sent_table()
            if success:
                self.log(f"JSON下发成功: 图像{len(image_targets)} 雷达{len(radar_targets)} 请求{len(fire_control_requests)}")
            else:
                self.log(f"JSON下发{status_text}: 图像{len(image_targets)} 雷达{len(radar_targets)} 请求{len(fire_control_requests)}")
            
                
        except Exception as e:
            self.log(f"发送数据错误: {str(e)}")
    
    def process_received_frame(self, frame: DataFrame):
        """处理接收到的数据帧"""
        self.received_frames.append({
            'frame': frame,
            'time': time.strftime('%H:%M:%S'),
            'mode': self.core.current_mode.value
        })
        
        self.update_received_table()
        
        # 记录详细信息
        self.log(f"接收到数据帧: 图像目标{frame.image_target_num}个, 雷达目标{frame.radar_target_num}个, 火控请求{frame.requested_target_num}个")
    
    def update_sent_table(self):
        """更新发送数据表格"""
        total = len(self.sent_frames)
        self.sent_data_table.setRowCount(total)
        for i, frame_data in enumerate(self.sent_frames):
            frame = frame_data['frame']
            self.sent_data_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.sent_data_table.setItem(i, 1, QTableWidgetItem(str(frame.image_target_num)))
            self.sent_data_table.setItem(i, 2, QTableWidgetItem(str(frame.radar_target_num)))
            self.sent_data_table.setItem(i, 3, QTableWidgetItem(str(frame.requested_target_num)))
            try:
                actual_len = len(self.codec.encode_frame(frame))
            except Exception:
                actual_len = frame.length
            self.sent_data_table.setItem(i, 4, QTableWidgetItem(str(actual_len)))
            self.sent_data_table.setItem(i, 5, QTableWidgetItem(frame_data['time']))
            self.sent_data_table.setItem(i, 6, QTableWidgetItem(frame_data['mode']))
            self.sent_data_table.setItem(i, 7, QTableWidgetItem(frame_data.get('status', '成功')))
            detail_btn = QPushButton("查看")
            detail_btn.clicked.connect(lambda checked, idx=i: self.show_frame_detail(self.sent_frames[idx], "发送"))
            self.sent_data_table.setCellWidget(i, 8, detail_btn)
    
    def update_received_table(self):
        """更新接收数据表格"""
        total = len(self.received_frames)
        self.received_data_table.setRowCount(total)
        for i, frame_data in enumerate(self.received_frames):
            frame = frame_data['frame']
            self.received_data_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.received_data_table.setItem(i, 1, QTableWidgetItem(str(frame.image_target_num)))
            self.received_data_table.setItem(i, 2, QTableWidgetItem(str(frame.radar_target_num)))
            self.received_data_table.setItem(i, 3, QTableWidgetItem(str(frame.requested_target_num)))
            try:
                actual_len = len(self.codec.encode_frame(frame))
            except Exception:
                actual_len = frame.length
            self.received_data_table.setItem(i, 4, QTableWidgetItem(str(actual_len)))
            self.received_data_table.setItem(i, 5, QTableWidgetItem(frame_data['time']))
            self.received_data_table.setItem(i, 6, QTableWidgetItem(frame_data['mode']))
            self.received_data_table.setItem(i, 7, QTableWidgetItem("成功"))
            detail_btn = QPushButton("查看")
            detail_btn.clicked.connect(lambda checked, idx=i: self.show_frame_detail(self.received_frames[idx], "接收"))
            self.received_data_table.setCellWidget(i, 8, detail_btn)
    
    def show_frame_detail(self, frame_data: dict, frame_type: str):
        """显示帧详情"""
        frame = frame_data['frame']
        
        detail_text = f"""
{frame_type}数据帧详情:
时间: {frame_data['time']}
模式: {frame_data['mode']}
数据长度: {frame.length} 字节

图像目标数量: {frame.image_target_num}
"""
        
        if frame.image_targets:
            detail_text += "图像目标详情:\n"
            for i, target in enumerate(frame.image_targets[:3]):  # 只显示前3个
                detail_text += f"  目标{i+1}: ID={target.id}, 距离={target.distance_m:.1f}m, 方位={target.azimuth_deg:.1f}°, 速度={target.speed_m_s:.1f}m/s\n"
            if len(frame.image_targets) > 3:
                detail_text += f"  ... 还有 {len(frame.image_targets) - 3} 个目标\n"
        
        detail_text += f"\n雷达目标数量: {frame.radar_target_num}\n"
        if frame.radar_targets:
            detail_text += "雷达目标详情:\n"
            for i, target in enumerate(frame.radar_targets[:3]):  # 只显示前3个
                detail_text += f"  目标{i+1}: ID={target.id}, 距离={target.distance_m:.1f}m, 方位={target.azimuth_deg:.1f}°, RCS={target.rcs_db:.1f}dB\n"
            if len(frame.radar_targets) > 3:
                detail_text += f"  ... 还有 {len(frame.radar_targets) - 3} 个目标\n"
        
        detail_text += f"\n火控请求数量: {frame.requested_target_num}\n"
        if frame.requested_target_ids:
            detail_text += f"请求目标ID: {', '.join(map(str, frame.requested_target_ids))}\n"
        
        # 创建详情对话框
        msg_box = QMessageBox()
        msg_box.setWindowTitle(f"{frame_type}数据帧详情")
        msg_box.setText(detail_text)
        msg_box.exec_()
    
    def on_clear_log(self):
        """清空日志"""
        self.log_text.clear()
    
    def log(self, message: str):
        """记录日志"""
        timestamp = time.strftime('%H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        self.log_text.append(log_entry)
        
        # 自动滚动到底部
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _format_frame_summary(self, frame: DataFrame) -> str:
        """格式化数据帧概要信息

        返回包含帧头、数量统计以及部分目标详情的字符串，便于日志查看。
        """
        lines = []
        lines.append(f"包头: 0x{frame.header:04X}")
        lines.append(f"目标标识: {frame.target}")
        lines.append(f"长度字段: {frame.length} 字节")
        lines.append(f"图像目标数: {frame.image_target_num}")
        lines.append(f"雷达目标数: {frame.radar_target_num}")
        lines.append(f"火控请求数: {frame.requested_target_num}")

        if frame.image_targets:
            lines.append("图像目标示例:")
            for t in frame.image_targets[:3]:
                lines.append(
                    f"  ID={t.id}, 类型={t.type}, 距离={t.distance_m:.1f}m, 方位={t.azimuth_deg:.1f}°, 速度={t.speed_m_s:.1f}m/s"
                )
        if frame.radar_targets:
            lines.append("雷达目标示例:")
            for t in frame.radar_targets[:3]:
                lines.append(
                    f"  ID={t.id}, 距离={t.distance_m:.1f}m, 方位={t.azimuth_deg:.1f}°, RCS={t.rcs_db:.1f}dB, 速度={t.velocity_m_s:.1f}m/s"
                )
        if frame.requested_target_ids:
            lines.append(f"请求目标ID: {', '.join(map(str, frame.requested_target_ids))}")

        return "\n".join(lines)

    def _hexdump(self, data: bytes, max_len: int = 128) -> str:
        """生成数据的十六进制预览字符串

        仅展示前 max_len 字节，按16字节分组，便于快速查看数据内容。
        """
        view = data[:max_len]
        hex_bytes = [f"{b:02X}" for b in view]
        lines = []
        for i in range(0, len(hex_bytes), 16):
            chunk = " ".join(hex_bytes[i:i+16])
            lines.append(chunk)
        if len(data) > max_len:
            lines.append(f"... (共 {len(data)} 字节)")
        return " ".join(lines)
    
    def closeEvent(self, event):
        """关闭事件"""
        # 停止所有定时器
        self.update_timer.stop()
        self.send_timer.stop()
        try:
            if self.json_sender:
                self.json_sender.close()
        except Exception:
            pass
        
        # 停止网络连接
        self.network.stop()
        
        # 停止仿真
        self.core.is_running = False
        
        event.accept()

# ----------------------------- 主程序 -----------------------------
def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    _set_app_chinese_font(app)
    
    # 创建并显示主窗口
    window = MainWindow()
    window.show()
    
    # 记录启动日志
    window.log("雷达接口特征模拟器仿真软件已启动")
    window.log("请配置网络连接并选择雷达工作模式")
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
