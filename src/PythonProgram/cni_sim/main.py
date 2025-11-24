import argparse
import sys

from PyQt5 import QtWidgets

from src.PythonProgram.cni_sim.models import CNIState
from src.PythonProgram.cni_sim.ui import MainWindow


def parse_args(argv):
    """解析命令行参数。

    Args:
        argv: 命令行参数列表。

    Returns:
        argparse.Namespace: 参数对象，包含listen_port、out_host、out_port、dt。
    """

    p = argparse.ArgumentParser(description='CNI接口特征仿真（Python+PyQt5）')
    p.add_argument('--listen-port', type=int, default=0)
    p.add_argument('--out-host', type=str, default='127.0.0.1')
    p.add_argument('--out-port', type=int, default=6006)
    p.add_argument('--dt', type=float, default=0.5)
    return p.parse_args(argv)


def main(argv=None):
    """程序入口。

    创建仿真状态与主界面，并启动Qt事件循环。

    Args:
        argv: 可选的命令行参数列表。

    Returns:
        int: 进程退出码。
    """

    args = parse_args(argv or sys.argv[1:])
    state = CNIState(dt_s=float(args.dt))
    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow(state, out_host=args.out_host, out_port=args.out_port, listen_port=args.listen_port)
    win.show()
    return app.exec_()


if __name__ == '__main__':
    sys.exit(main())

