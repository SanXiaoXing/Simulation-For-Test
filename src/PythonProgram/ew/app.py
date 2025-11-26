import argparse
import sys
import time

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QCoreApplication

from src.PythonProgram.ew.simulator import EWSimulator
from src.PythonProgram.ew.udp import UDPReceiver
from src.PythonProgram.ew.gui import MainWindow


def run_gui() -> int:
    """启动PyQt5图形界面。

    Returns:
        int: 进程返回码。
    """

    try:
        QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
        QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    except Exception:
        pass
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    return app.exec_()


def run_headless(seconds: float = 2.0) -> None:
    """在无GUI模式下运行仿真与接收，快速验证端到端。

    Args:
        seconds: 运行时长秒。
    """

    sim = EWSimulator()
    sim.start()
    rx = UDPReceiver()
    rx.start()
    time.sleep(seconds)
    rx.stop()
    rx.wait(1000)
    sim.stop()


def main() -> None:
    """应用入口，解析参数并运行相应模式。"""

    parser = argparse.ArgumentParser(description="EW 接口特征仿真")
    parser.add_argument("--nogui", action="store_true", help="仅运行仿真和接收进行自检")
    parser.add_argument("--seconds", type=float, default=2.0, help="无GUI模式运行秒数")
    args = parser.parse_args()

    if args.nogui:
        run_headless(args.seconds)
    else:
        sys.exit(run_gui())


if __name__ == "__main__":
    main()
