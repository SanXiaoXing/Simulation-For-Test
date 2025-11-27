"""主面板状态视图。"""

from __future__ import annotations

from PyQt5 import QtWidgets
from sim_core.models import WeaponSystem


class StatusPanel(QtWidgets.QWidget):
    """显示飞机→挂架→武器拓扑与实时状态。"""

    def __init__(self, sys: WeaponSystem) -> None:
        super().__init__()
        self._sys = sys
        self._tree = QtWidgets.QTreeWidget()
        self._tree.setHeaderLabels(["节点", "状态"])
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("拓扑结构"))
        layout.addWidget(self._tree)
        self.refresh()

    def refresh(self) -> None:
        """刷新树状视图内容。"""

        self._tree.clear()
        plane = QtWidgets.QTreeWidgetItem(["飞机", "正常"])
        rack = QtWidgets.QTreeWidgetItem([f"挂架 {self._sys.rack.rack_id}", f"锁定={self._sys.rack.locked}"])
        weapon = QtWidgets.QTreeWidgetItem([f"武器 {self._sys.weapon.weapon_id}", f"状态={self._sys.weapon.state}"])
        fuze = QtWidgets.QTreeWidgetItem([f"引信 {self._sys.weapon.fuze.fuze_id}", f"待发={self._sys.weapon.fuze.armed}"])
        temp = QtWidgets.QTreeWidgetItem(["温度", f"{self._sys.weapon.temperature_c:.1f} ℃"])
        self._tree.addTopLevelItem(plane)
        plane.addChild(rack)
        rack.addChild(weapon)
        weapon.addChild(fuze)
        weapon.addChild(temp)
