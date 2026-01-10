# IRST Simulator 运行说明

## 环境要求
- Python 3.8.10
- PyQt5
- matplotlib
- numpy

## 文件说明
- `main.py`: 模拟器主程序，包含界面和网络通信逻辑。
- `protocol.py`: 定义通信协议（输入/输出参数打包与解析）。
- `config.json`: 配置文件，用于设置默认参数和初始目标信息。
- `test_server.py`: （可选）简单的内仿真模拟脚本，用于测试通信回路。

## 运行步骤

1. **启动模拟器**:
   ```bash
   python main.py
   ```
   启动后，界面将显示，并开始向配置的 `remote_ip:remote_port` 发送模拟的目标数据。

2. **测试回路 (如果没有真实的内仿真程序)**:
   在另一个终端运行测试脚本，它会接收模拟器的数据并回传，从而在模拟器界面上显示出目标。
   ```bash
   python test_server.py
   ```

## 配置说明 (config.json)
- `network`: 配置本地和远程的IP/端口。
- `sensor`: 配置传感器的初始参数（探测距离、刷新率等）。
- `targets`: 配置初始模拟目标的列表。模拟器会自动根据速度更新目标的方位和距离。
