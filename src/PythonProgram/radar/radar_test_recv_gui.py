#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：Simulation 
@File    ：radar_test_recv_gui.py
@Author  ：Auto
@Date    ：2025/12/02
@Description: 接收数据测试（带GUI）

该脚本同时打开两个界面窗口：
1) 服务器窗口：启动TCP服务器，用于接收并展示收到的数据帧；
2) 客户端窗口：连接服务器，自动按仿真生成并发送数据帧。

用途：验证界面中的“接收数据”标签页是否能实时显示从网络接收的帧，
并与雷达画布联动展示。
"""

import sys
import time
from PyQt5.QtWidgets import QApplication
from radar_ui import MainWindow


def launch_server_ui(host: str = "127.0.0.1", port: int = 8888) -> MainWindow:
    """启动服务器界面并监听指定地址端口。

    Args:
        host: 服务器监听地址。
        port: 服务器监听端口。

    Returns:
        已配置为服务器模式的主窗口对象。
    """
    win = MainWindow()
    win.setWindowTitle("接收测试 — 服务器")
    win.host_input.setText(host)
    win.port_input.setValue(port)
    win.on_start_server()
    win.move(60, 60)
    win.show()
    return win


def launch_client_ui(host: str = "127.0.0.1", port: int = 8888) -> MainWindow:
    """启动客户端界面，连接到服务器并自动发送。

    Args:
        host: 服务器地址。
        port: 服务器端口。

    Returns:
        已连接并自动发送的主窗口对象。
    """
    win = MainWindow()
    win.setWindowTitle("接收测试 — 客户端")
    win.host_input.setText(host)
    win.port_input.setValue(port)
    win.on_connect_client()
    # 调整发送频率与运动模式，使数据变化更明显
    win.send_interval.setValue(500)
    win.motion_mode_combo.setCurrentIndex(2)  # 圆周
    win.on_motion_mode_change(2)
    # 开启自动发送与仿真
    win.auto_send_check.setChecked(True)
    win.on_start_simulation()
    win.move(820, 60)
    win.show()
    return win


def main():
    """主入口：同时启动服务器与客户端界面，并运行事件循环。"""
    app = QApplication(sys.argv)
    server = launch_server_ui()
    client = launch_client_ui()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

