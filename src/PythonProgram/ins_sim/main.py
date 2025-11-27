from __future__ import annotations

import sys
from PyQt5 import QtWidgets

from .ui.main_window import INSMainWindow


def main() -> int:
    """应用入口。"""

    app = QtWidgets.QApplication(sys.argv)
    w = INSMainWindow()
    w.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())

