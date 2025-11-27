"""释放控制面板。"""

from __future__ import annotations

from PyQt5 import QtWidgets
from sim_core.models import WeaponSystem
from sim_core.release import ReleaseController


class ReleasePanel(QtWidgets.QWidget):
    """提供解锁、引信待发与释放控制。"""

    def __init__(self, sys: WeaponSystem, controller: ReleaseController) -> None:
        super().__init__()
        self._sys = sys
        self._ctl = controller
        self._log = QtWidgets.QTextEdit()
        self._log.setReadOnly(True)

        btn_unlock = QtWidgets.QPushButton("挂架解锁")
        btn_arm = QtWidgets.QPushButton("引信待发")
        btn_release = QtWidgets.QPushButton("开始释放")
        btn_step = QtWidgets.QPushButton("推进时序")
        btn_reset = QtWidgets.QPushButton("重置")

        btn_unlock.clicked.connect(self._on_unlock)
        btn_arm.clicked.connect(self._on_arm)
        btn_release.clicked.connect(self._on_release)
        btn_step.clicked.connect(self._on_step)
        btn_reset.clicked.connect(self._on_reset)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("释放控制"))
        layout.addWidget(btn_unlock)
        layout.addWidget(btn_arm)
        layout.addWidget(btn_release)
        layout.addWidget(btn_step)
        layout.addWidget(btn_reset)
        layout.addWidget(QtWidgets.QLabel("事件日志"))
        layout.addWidget(self._log)

    def _flush_log(self) -> None:
        """刷新事件日志显示。"""

        self._log.clear()
        for e in self._ctl.log[-100:]:
            self._log.append(f"[{e.level}] {e.message}")

    def _on_unlock(self) -> None:
        """挂架解锁操作。"""

        self._ctl.unlock_rack()
        self._flush_log()

    def _on_arm(self) -> None:
        """引信待发操作。"""

        self._ctl.arm_fuze()
        self._flush_log()

    def _on_release(self) -> None:
        """开始释放操作。"""

        self._ctl.start_release()
        self._flush_log()

    def _on_step(self) -> None:
        """推进释放时序。"""

        self._ctl.step()
        self._flush_log()

    def _on_reset(self) -> None:
        """重置释放流程。"""

        self._ctl.reset()
        self._flush_log()
