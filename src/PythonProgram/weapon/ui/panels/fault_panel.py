"""故障诊断面板。"""

from __future__ import annotations

from PyQt5 import QtWidgets
from sim_core.models import WeaponSystem
from sim_core.release import ReleaseController
from sim_core.bus import BusSimulator


class FaultPanel(QtWidgets.QWidget):
    """故障注入与诊断占位。"""

    def __init__(self, sys: WeaponSystem, ctl: ReleaseController) -> None:
        super().__init__()
        self._sys = sys
        self._ctl = ctl
        self._ber = QtWidgets.QDoubleSpinBox()
        self._ber.setRange(0.0, 0.5)
        self._ber.setSingleStep(0.01)
        self._ber.setValue(0.0)
        self._overload = QtWidgets.QCheckBox("挂架过载保护")
        self._eject_fault = QtWidgets.QCheckBox("弹射器故障")
        self._replay = QtWidgets.QPushButton("回放释放日志")
        self._log = QtWidgets.QTextEdit()
        self._log.setReadOnly(True)

        layout = QtWidgets.QFormLayout(self)
        layout.addRow("1553B 比特错误率", self._ber)
        layout.addRow(self._overload)
        layout.addRow(self._eject_fault)
        layout.addRow(self._replay)
        layout.addRow("日志", self._log)

        self._ber.valueChanged.connect(self._on_ber)
        self._overload.toggled.connect(self._on_overload)
        self._eject_fault.toggled.connect(self._on_eject_fault)
        self._replay.clicked.connect(self._on_replay)

    def _on_ber(self, v: float) -> None:
        """设置1553B比特错误率。"""

        # 作为全局示意，记录到释放日志方便观察
        self._ctl._log("INFO", f"设置 BER={v:.2f}")
        self._flush_log()

    def _on_overload(self, flag: bool) -> None:
        """切换挂架过载保护。"""

        self._sys.rack.overload_protect = flag
        self._ctl._log("WARN" if flag else "INFO", f"过载保护={'开启' if flag else '关闭'}")
        self._flush_log()

    def _on_eject_fault(self, flag: bool) -> None:
        """切换弹射器故障。"""

        self._sys.ejector.fault = flag
        self._ctl._log("ERROR" if flag else "INFO", f"弹射器故障={'是' if flag else '否'}")
        self._flush_log()

    def _on_replay(self) -> None:
        """回放释放日志。"""

        self._log.clear()
        for e in self._ctl.log:
            self._log.append(f"[{e.level}] {e.message}")

    def _flush_log(self) -> None:
        """刷新日志显示。"""

        self._on_replay()
