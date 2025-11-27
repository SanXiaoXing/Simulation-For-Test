"""分布式孔径接口特征仿真器主入口。

此模块负责启动 PyQt5 图形界面与后端仿真线程/协程。

Functions:
    main(): 启动应用程序与主窗口。
"""

from typing import NoReturn

import sys

from PyQt5 import QtWidgets

from ui.main_window import MainWindow


def main() -> NoReturn:
    """启动 PyQt5 应用与主窗口。

    此函数创建 QApplication，并加载主窗口 MainWindow。该窗口
    包含地图视图、视频面板与数据控制面板的占位实现。

    Raises:
        RuntimeError: 当 GUI 初始化失败时抛出异常。
    """

    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
