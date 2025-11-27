from __future__ import annotations

import sys
from PyQt5 import QtWidgets

from .ui.main_window import MFDMainWindow


def main(argv=None) -> int:
    """程序入口。"""

    app = QtWidgets.QApplication(sys.argv)
    win = MFDMainWindow()
    win.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())

