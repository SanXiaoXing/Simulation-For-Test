"""训练模式面板。"""

from __future__ import annotations

from PyQt5 import QtWidgets
from pathlib import Path
import csv
from sim_core.models import WeaponSystem
from sim_core.release import ReleaseController


class TrainingPanel(QtWidgets.QWidget):
    """人机操作步骤与评分占位。"""

    def __init__(self, sys: WeaponSystem, ctl: ReleaseController) -> None:
        super().__init__()
        self._sys = sys
        self._ctl = ctl
        self._steps = [
            ("挂架解锁", lambda: not self._sys.rack.locked),
            ("引信待发", lambda: self._sys.weapon.fuze.armed),
            ("开始释放", lambda: self._sys.weapon.state == "releasing" or self._sys.weapon.state == "separated"),
            ("分离完成", lambda: self._sys.weapon.state == "separated"),
        ]
        self._checks = []
        self._score_label = QtWidgets.QLabel("评分: -")
        btn_eval = QtWidgets.QPushButton("评估并导出")
        btn_eval.clicked.connect(self._on_eval)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("训练步骤"))
        for name, _ in self._steps:
            cb = QtWidgets.QCheckBox(name)
            self._checks.append(cb)
            layout.addWidget(cb)
        layout.addWidget(btn_eval)
        layout.addWidget(self._score_label)

    def _on_eval(self) -> None:
        """评估完成度并导出历史记录。"""

        done = 0
        total = len(self._steps)
        for i, (_, cond) in enumerate(self._steps):
            ok = bool(cond())
            self._checks[i].setChecked(ok)
            if ok:
                done += 1
        score = int(100 * done / total)
        self._score_label.setText(f"评分: {score}")
        p = Path(__file__).resolve().parents[2] / "configs" / "training_history.csv"
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([self._sys.weapon.weapon_id, score, done, total])
