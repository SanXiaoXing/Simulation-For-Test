"""IRST 仿真器主入口。

提供 PyQt5 应用启动和主窗口展示。

Functions:
    main(): 启动应用与显示主窗口。
"""

from typing import NoReturn

import sys
from PyQt5 import QtWidgets

from ui.main_window import MainWindow


def main() -> NoReturn:
    """启动 PyQt5 应用并显示主窗口。"""

    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
