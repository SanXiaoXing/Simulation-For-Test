#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
雷达接口特征模拟器（Radar_Connect）UI与下发模块

- 依据 `src/PythonProgram/radar/` 的界面结构进行精简重构
- 通过选择 JSON 配置文件（如 `config/device.json`）加载接口参数
- 以 UDP 方式向下位机下发 README 中定义的指令结构的 JSON 内容

依赖：PyQt5
"""

import json
import os
import socket
import sys
import time
from typing import Dict, List, Optional, Tuple

from PyQt5 import QtWidgets
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QComboBox, QSpinBox, QLineEdit,
    QTextEdit, QGroupBox, QFormLayout, QFileDialog
)


class UDPSender:
    """UDP发送器

    提供基于UDP的简单发送能力。

    Attributes:
        remote (Tuple[str, int]): 远端主机与端口。
        sock (socket.socket): UDP套接字。
    """

    def __init__(self, host: str, port: int):
        """初始化UDP发送器

        Args:
            host: 远端主机地址。
            port: 远端端口号。
        """
        self.remote: Tuple[str, int] = (host, int(port))
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

    def send_json(self, obj: Dict) -> bool:
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

    根据 README 公式：`30*n + 18*m + k + 3`。

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
        image_targets: 图像目标列表，每项为字典，包含协议字段。
        radar_targets: 雷达目标列表，每项为字典，包含协议字段。
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
        raw_targets: 包含`id`, `type`, `distance_m`, `azimuth_deg`,
            `frequency_hz`, `distance_30ms_m`, `azimuth_30ms_deg`,
            `speed_m_s`, `direction_deg`等键的字典列表。

    Returns:
        满足README协议字段命名的图像目标字典列表。
    """
    out = []
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
        raw_targets: 包含`id`, `distance_m`, `azimuth_deg`, `rcs_db`,
            `velocity_m_s`等键的字典列表。

    Returns:
        满足README协议字段命名的雷达目标字典列表。
    """
    out = []
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

    支持如下键：`IP`, `Port`, `Cards`, `Card`, `Channel`。

    Args:
        path: 配置文件路径。

    Returns:
        解析后的配置字典，并注入`interface`字段(`udp`或`ieee1394`)与
        `remote_host`, `remote_port`, `card`等便捷键。
    """
    with open(path, 'r', encoding='utf-8') as f:
        cfg = json.load(f)

    ip = cfg.get("IP")
    port = cfg.get("Port")
    cards = cfg.get("Cards") or []
    card = cfg.get("Card") or (cards[0] if isinstance(cards, list) and cards else None)
    channel = cfg.get("Channel")

    interface = "udp" if ip and port else ("ieee1394" if card else "udp")

    try:
        port_int = int(port) if port is not None else 8888
    except Exception:
        port_int = 8888

    cfg_out = {
        **cfg,
        "interface": interface,
        "remote_host": ip or "127.0.0.1",
        "remote_port": port_int,
        "card": card or "",
        "channel": channel,
    }
    return cfg_out


class MainWindow(QMainWindow):
    """主界面窗口

    - 左侧：配置选择与发送控制
    - 右侧：已下发数据列表与日志
    """

    def __init__(self):
        """初始化UI组件与状态"""
        super().__init__()
        self.setWindowTitle("Radar_Connect 下发模拟器")
        self.resize(1100, 700)

        # 状态
        self.device_cfg: Dict = {}
        self.sender: Optional[UDPSender] = None
        self.frame_seq: int = 1

        # 定时器
        self.send_timer = QTimer()
        self.send_timer.timeout.connect(self.on_send_timer)

        # 构建界面
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        left = self._build_left_panel()
        left.setFixedWidth(420)
        main_layout.addWidget(left)

        right = self._build_right_panel()
        main_layout.addWidget(right)

    def _build_left_panel(self) -> QWidget:
        """构建左侧配置与控制面板

        Returns:
            左侧布局的容器部件。
        """
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # 接口配置
        cfg_group = QGroupBox("接口配置")
        cfg_form = QFormLayout(cfg_group)

        self.cfg_path_edit = QLineEdit(os.path.join(os.path.dirname(__file__), "config", "device.json"))
        self.cfg_browse_btn = QPushButton("选择配置文件")
        self.cfg_browse_btn.clicked.connect(self.on_browse_cfg)
        browse_row = QHBoxLayout()
        browse_row.addWidget(self.cfg_path_edit)
        browse_row.addWidget(self.cfg_browse_btn)
        cfg_form.addRow("配置文件:", QWidget())
        cfg_form.itemAt(cfg_form.rowCount() - 1, QFormLayout.FieldRole).widget().setLayout(browse_row)

        self.interface_combo = QComboBox()
        self.interface_combo.addItem("UDP", "udp")
        self.interface_combo.addItem("IEEE-1394(模拟)", "ieee1394")
        cfg_form.addRow("接口类型:", self.interface_combo)

        self.ip_edit = QLineEdit("127.0.0.1")
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(8888)
        cfg_form.addRow("IP地址:", self.ip_edit)
        cfg_form.addRow("端口:", self.port_spin)

        self.card_edit = QLineEdit("")
        cfg_form.addRow("接口卡:", self.card_edit)

        self.load_cfg_btn = QPushButton("加载配置")
        self.load_cfg_btn.clicked.connect(self.on_load_cfg)
        cfg_form.addRow(self.load_cfg_btn)

        layout.addWidget(cfg_group)

        # 发送控制
        send_group = QGroupBox("发送控制")
        send_form = QFormLayout(send_group)

        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(100, 5000)
        self.interval_spin.setValue(1000)
        self.interval_spin.setSuffix(" ms")
        send_form.addRow("自动间隔:", self.interval_spin)

        self.auto_send_combo = QComboBox()
        self.auto_send_combo.addItem("停止", False)
        self.auto_send_combo.addItem("启动", True)
        self.auto_send_combo.currentIndexChanged.connect(self.on_auto_send_changed)
        send_form.addRow("自动发送:", self.auto_send_combo)

        self.send_btn = QPushButton("手动下发")
        self.send_btn.clicked.connect(self.on_manual_send)
        send_form.addRow(self.send_btn)

        layout.addWidget(send_group)

        # 日志
        log_group = QGroupBox("日志")
        vbox = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        vbox.addWidget(self.log_text)
        layout.addWidget(log_group)

        layout.addStretch()
        return panel

    def _build_right_panel(self) -> QWidget:
        """构建右侧下发数据展示面板

        Returns:
            右侧布局的容器部件。
        """
        panel = QWidget()
        layout = QVBoxLayout(panel)

        self.sent_table = QTableWidget(0, 7)
        self.sent_table.setHorizontalHeaderLabels([
            "序号", "时间", "接口", "IP:端口", "图像目标数", "雷达目标数", "火控请求数",
        ])
        layout.addWidget(self.sent_table)

        self.preview_json = QTextEdit()
        self.preview_json.setReadOnly(True)
        layout.addWidget(QLabel("最近一次下发JSON预览："))
        layout.addWidget(self.preview_json)

        return panel

    def log(self, msg: str):
        """追加日志文本

        Args:
            msg: 日志消息。
        """
        ts = time.strftime('%H:%M:%S')
        self.log_text.append(f"[{ts}] {msg}")
        sb = self.log_text.verticalScrollBar()
        sb.setValue(sb.maximum())

    def on_browse_cfg(self):
        """选择配置文件事件处理"""
        path, _ = QFileDialog.getOpenFileName(self, "选择设备配置JSON", self.cfg_path_edit.text(), "JSON Files (*.json)")
        if path:
            self.cfg_path_edit.setText(path)

    def on_load_cfg(self):
        """加载设备配置并更新界面"""
        try:
            cfg = load_device_config(self.cfg_path_edit.text())
            self.device_cfg = cfg
            # 更新界面
            idx = 0 if cfg.get("interface") == "udp" else 1
            self.interface_combo.setCurrentIndex(idx)
            self.ip_edit.setText(cfg.get("remote_host", "127.0.0.1"))
            self.port_spin.setValue(int(cfg.get("remote_port", 8888)))
            self.card_edit.setText(cfg.get("card", ""))
            self.log("配置加载成功")
            # 初始化UDP
            self._ensure_sender()
        except Exception as e:
            self.log(f"配置加载失败: {str(e)}")

    def _ensure_sender(self):
        """基于当前配置保证UDP发送器可用"""
        host = self.ip_edit.text().strip() or "127.0.0.1"
        port = int(self.port_spin.value())
        self.sender = UDPSender(host, port)
        ok = self.sender.open()
        if ok:
            self.log(f"UDP目标: {host}:{port}")
        else:
            self.log("UDP发送器初始化失败")

    def on_auto_send_changed(self, idx: int):
        """自动发送启停切换"""
        running = bool(self.auto_send_combo.itemData(idx))
        if running:
            interval = self.interval_spin.value()
            self.send_timer.start(interval)
            self.log(f"自动发送已启动，间隔{interval}ms")
        else:
            self.send_timer.stop()
            self.log("自动发送已停止")

    def on_send_timer(self):
        """自动定时下发回调"""
        self._send_once()

    def on_manual_send(self):
        """手动下发点击处理"""
        self._send_once()

    def _gen_targets(self) -> Tuple[List[Dict], List[Dict], List[int]]:
        """生成一帧示例目标集合

        使用简单的伪随机数据，字段对齐README协议。若需更复杂的仿真，可引入
        `src/PythonProgram/radar/radar_core.py` 的生成逻辑。

        Returns:
            (image_targets, radar_targets, req_ids) 三元组。
        """
        # 简化生成逻辑：固定数量+少量随机扰动
        import random

        n_img = random.randint(1, 5)
        n_rad = random.randint(1, 5)
        n_req = random.randint(0, 3)

        image_targets: List[Dict] = []
        for i in range(n_img):
            image_targets.append({
                "id": 100 + i,
                "type": random.choice([1, 2, 3]),
                "distance_m": random.uniform(1000, 50000),
                "azimuth_deg": random.uniform(0, 360),
                "frequency_hz": random.choice([0.0, 1.2e9, 2.4e9, 5.8e9]),
                "distance_30ms_m": random.uniform(1000, 50000),
                "azimuth_30ms_deg": random.uniform(0, 360),
                "speed_m_s": random.uniform(0, 400),
                "direction_deg": random.uniform(0, 360),
            })

        radar_targets: List[Dict] = []
        for i in range(n_rad):
            radar_targets.append({
                "id": 200 + i,
                "distance_m": random.uniform(1000, 50000),
                "azimuth_deg": random.uniform(0, 360),
                "rcs_db": random.uniform(-20, 20),
                "velocity_m_s": random.uniform(-200, 400),
            })

        req_ids = [100 + i for i in range(n_req)]
        return image_targets, radar_targets, req_ids

    def _send_once(self):
        """生成并下发一帧JSON数据"""
        # 生成目标
        img_raw, rad_raw, req_ids = self._gen_targets()
        img_items = convert_image_targets(img_raw)
        rad_items = convert_radar_targets(rad_raw)

        # 构建JSON
        ip = self.ip_edit.text().strip() or "127.0.0.1"
        port = int(self.port_spin.value())
        card = self.card_edit.text().strip()
        obj = build_protocol_json(
            ip=ip,
            port=port,
            card=card,
            image_targets=img_items,
            radar_targets=rad_items,
            req_ids=req_ids,
            frame_id=self.frame_seq,
        )

        # 发送
        if not self.sender:
            self._ensure_sender()
        ok = self.sender.send_json(obj) if self.sender else False

        # 记录UI
        self._append_sent_row(obj, ok)
        self.preview_json.setPlainText(json.dumps(obj, ensure_ascii=False, indent=2))

        # 自增序号
        self.frame_seq += 1
        self.log(f"JSON下发{'成功' if ok else '失败'}: 图像{len(img_items)} 雷达{len(rad_items)} 请求{len(req_ids)}")

    def _append_sent_row(self, obj: Dict, status: bool):
        """在表格中追加一条下发记录"""
        row = self.sent_table.rowCount()
        self.sent_table.insertRow(row)
        ts = time.strftime('%H:%M:%S')
        ip = obj.get("IP", "")
        port = obj.get("Port", 0)
        iface = self.interface_combo.currentData()

        self.sent_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
        self.sent_table.setItem(row, 1, QTableWidgetItem(ts))
        self.sent_table.setItem(row, 2, QTableWidgetItem("UDP" if iface == "udp" else "IEEE-1394"))
        self.sent_table.setItem(row, 3, QTableWidgetItem(f"{ip}:{port}"))
        data = obj.get("Data", {})
        itc = str(data.get("ImageTargets", {}).get("count", 0))
        rtc = str(data.get("RadarTargets", {}).get("count", 0))
        frc = str(data.get("FireControlRequests", {}).get("count", 0))
        self.sent_table.setItem(row, 4, QTableWidgetItem(itc))
        self.sent_table.setItem(row, 5, QTableWidgetItem(rtc))
        self.sent_table.setItem(row, 6, QTableWidgetItem(frc))

        # 高亮失败行
        if not status:
            for col in range(0, 7):
                item = self.sent_table.item(row, col)
                if item:
                    item.setForeground(Qt.red)


def main():
    """程序入口"""
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

