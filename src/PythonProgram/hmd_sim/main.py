from __future__ import annotations

import sys
from PyQt5 import QtWidgets

from .ui.main_window import HMDMainWindow


def main(argv=None) -> int:
    """程序入口。"""

    app = QtWidgets.QApplication(sys.argv)
    win = HMDMainWindow()
    win.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())

