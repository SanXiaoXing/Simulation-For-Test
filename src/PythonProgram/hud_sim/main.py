from __future__ import annotations

import sys
from PyQt5 import QtWidgets

from src.PythonProgram.hud_sim.ui.main_window import HUDMainWindow


def main() -> int:
    """应用入口。"""

    app = QtWidgets.QApplication(sys.argv)
    w = HUDMainWindow()
    w.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
