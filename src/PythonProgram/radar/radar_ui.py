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
    QMessageBox
)
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

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
        
        # 数据存储
        self.received_frames = []
        self.sent_frames = []
        self.is_sending = False
        
        self.init_ui()
        
    def init_ui(self):
        """初始化用户界面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧控制面板
        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel, 1)
        
        # 中间雷达显示
        center_panel = self.create_center_panel()
        main_layout.addWidget(center_panel, 2)
        
        # 右侧数据面板
        right_panel = self.create_right_panel()
        main_layout.addWidget(right_panel, 1)
    
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
        
        # 连接按钮
        button_layout = QHBoxLayout()
        self.server_btn = QPushButton("启动服务器")
        self.server_btn.clicked.connect(self.on_start_server)
        self.client_btn = QPushButton("连接服务器")
        self.client_btn.clicked.connect(self.on_connect_client)
        self.disconnect_btn = QPushButton("断开连接")
        self.disconnect_btn.clicked.connect(self.on_disconnect)
        self.disconnect_btn.setEnabled(False)
        
        button_layout.addWidget(self.server_btn)
        button_layout.addWidget(self.client_btn)
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
        
        send_layout.addRow("发送间隔:", self.send_interval)
        send_layout.addRow(self.auto_send_check)
        send_layout.addRow(self.send_btn)
        
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
        """启动服务器"""
        host = self.host_input.text()
        port = self.port_input.value()
        
        success, message = self.network.start_server(host, port)
        if success:
            self.connection_status.setText(f"服务器模式: {host}:{port}")
            self.server_btn.setEnabled(False)
            self.client_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)
            self.log("服务器启动成功")
        else:
            self.log(f"服务器启动失败: {message}")
    
    def on_connect_client(self):
        """连接服务器"""
        host = self.host_input.text()
        port = self.port_input.value()
        
        success, message = self.network.connect_to_server(host, port)
        if success:
            self.connection_status.setText(f"客户端模式: {host}:{port}")
            self.server_btn.setEnabled(False)
            self.client_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)
            self.log("连接服务器成功")
        else:
            self.log(f"连接服务器失败: {message}")
    
    def on_disconnect(self):
        """断开连接"""
        self.network.stop()
        self.connection_status.setText("未连接")
        self.server_btn.setEnabled(True)
        self.client_btn.setEnabled(True)
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
        
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        self.log("雷达仿真已启动")
    
    def on_stop_simulation(self):
        """停止仿真"""
        self.core.is_running = False
        self.update_timer.stop()
        
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
        radar_targets = self.core.generate_radar_targets()
        self.radar_canvas.plot_radar_scan(status['antenna_angle'], radar_targets)
    
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
            else:
                self.log("接收到无效数据帧")
        except Exception as e:
            self.log(f"数据处理错误: {str(e)}")
    
    def send_frame(self):
        """发送数据帧"""
        if not self.network.is_connected:
            self.log("网络未连接，无法发送数据")
            return
        
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
            
            # 编码并发送
            data = self.codec.encode_frame(frame)
            success = self.network.send_data(data)
            
            if success:
                self.sent_frames.append({
                    'frame': frame,
                    'time': time.strftime('%H:%M:%S'),
                    'mode': self.core.current_mode.value
                })
                self.update_sent_table()
                self.log(f"数据帧发送成功: 图像目标{len(image_targets)}个, 雷达目标{len(radar_targets)}个")

                # 打印与记录发送数据内容
                summary = self._format_frame_summary(frame)
                hexdata = self._hexdump(data, max_len=256)
                self.log(f"发送数据内容:\n{summary}\nHEX: {hexdata}")
                print("发送数据内容:\n" + summary)
                print("HEX: " + hexdata)
            else:
                self.log("数据帧发送失败")
                
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
        self.sent_data_table.setRowCount(len(self.sent_frames))
        
        for i, frame_data in enumerate(self.sent_frames[-20:]):  # 只显示最近20条
            frame = frame_data['frame']
            
            # 帧序号
            self.sent_data_table.setItem(i, 0, QTableWidgetItem(str(len(self.sent_frames) - len(self.sent_frames[-20:]) + i)))
            
            # 图像目标数
            self.sent_data_table.setItem(i, 1, QTableWidgetItem(str(frame.image_target_num)))
            
            # 雷达目标数
            self.sent_data_table.setItem(i, 2, QTableWidgetItem(str(frame.radar_target_num)))
            
            # 火控请求数
            self.sent_data_table.setItem(i, 3, QTableWidgetItem(str(frame.requested_target_num)))
            
            # 数据长度
            self.sent_data_table.setItem(i, 4, QTableWidgetItem(str(frame.length)))
            
            # 发送时间
            self.sent_data_table.setItem(i, 5, QTableWidgetItem(frame_data['time']))
            
            # 模式
            self.sent_data_table.setItem(i, 6, QTableWidgetItem(frame_data['mode']))
            
            # 状态
            self.sent_data_table.setItem(i, 7, QTableWidgetItem("成功"))
            
            # 详情
            detail_btn = QPushButton("查看")
            detail_btn.clicked.connect(lambda checked, idx=i: self.show_frame_detail(self.sent_frames[-20:][idx], "发送"))
            self.sent_data_table.setCellWidget(i, 8, detail_btn)
    
    def update_received_table(self):
        """更新接收数据表格"""
        self.received_data_table.setRowCount(len(self.received_frames))
        
        for i, frame_data in enumerate(self.received_frames[-20:]):  # 只显示最近20条
            frame = frame_data['frame']
            
            # 帧序号
            self.received_data_table.setItem(i, 0, QTableWidgetItem(str(len(self.received_frames) - len(self.received_frames[-20:]) + i)))
            
            # 图像目标数
            self.received_data_table.setItem(i, 1, QTableWidgetItem(str(frame.image_target_num)))
            
            # 雷达目标数
            self.received_data_table.setItem(i, 2, QTableWidgetItem(str(frame.radar_target_num)))
            
            # 火控请求数
            self.received_data_table.setItem(i, 3, QTableWidgetItem(str(frame.requested_target_num)))
            
            # 数据长度
            self.received_data_table.setItem(i, 4, QTableWidgetItem(str(frame.length)))
            
            # 接收时间
            self.received_data_table.setItem(i, 5, QTableWidgetItem(frame_data['time']))
            
            # 模式
            self.received_data_table.setItem(i, 6, QTableWidgetItem(frame_data['mode']))
            
            # 状态
            self.received_data_table.setItem(i, 7, QTableWidgetItem("成功"))
            
            # 详情
            detail_btn = QPushButton("查看")
            detail_btn.clicked.connect(lambda checked, idx=i: self.show_frame_detail(self.received_frames[-20:][idx], "接收"))
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