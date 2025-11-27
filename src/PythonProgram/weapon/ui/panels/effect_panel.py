"""效能仿真面板。"""

from __future__ import annotations

from PyQt5 import QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from sim_core.models import WeaponSystem
import numpy as np


class EffectPanel(QtWidgets.QWidget):
    """显示命中概率与气动影响占位。"""

    def __init__(self, sys: WeaponSystem) -> None:
        super().__init__()
        self._sys = sys
        self._fig = Figure(figsize=(6, 4))
        self._canvas = FigureCanvas(self._fig)
        self._ax1 = self._fig.add_subplot(121)
        self._ax2 = self._fig.add_subplot(122)
        self._range_spin = QtWidgets.QDoubleSpinBox()
        self._range_spin.setRange(1000.0, 50000.0)
        self._range_spin.setValue(10000.0)
        self._sens_spin = QtWidgets.QDoubleSpinBox()
        self._sens_spin.setRange(0.0, 1.0)
        self._sens_spin.setSingleStep(0.05)
        self._sens_spin.setValue(self._sys.weapon.fuze.sensitivity)
        btn_update = QtWidgets.QPushButton("更新曲线")
        btn_update.clicked.connect(self._update_curves)
        form = QtWidgets.QFormLayout()
        form.addRow("目标距离(m)", self._range_spin)
        form.addRow("引信灵敏度", self._sens_spin)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self._canvas)
        self._update_curves()

    def _update_curves(self) -> None:
        """计算并绘制命中概率与气动影响曲线。"""

        dist = float(self._range_spin.value())
        sens = float(self._sens_spin.value())
        v = np.linspace(200, 800, 50)
        p_hit = np.clip(sens * (1.0 - dist / 50000.0) * (v / 800.0), 0.0, 1.0)
        self._ax1.clear()
        self._ax1.plot(v, p_hit)
        self._ax1.set_title("命中概率 vs 速度")
        self._ax1.set_xlabel("速度(m/s)")
        self._ax1.set_ylabel("概率")

        cd_external = 0.04
        cd_internal = 0.02
        v2 = np.linspace(100, 600, 50)
        drag_ext = cd_external * v2**2
        drag_int = cd_internal * v2**2
        self._ax2.clear()
        self._ax2.plot(v2, drag_ext, label="外挂")
        self._ax2.plot(v2, drag_int, label="内置")
        self._ax2.set_title("气动影响(阻力) vs 速度")
        self._ax2.set_xlabel("速度(m/s)")
        self._ax2.legend()
        self._canvas.draw()
