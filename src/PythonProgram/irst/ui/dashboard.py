"""仪表盘面板。"""

from __future__ import annotations

from typing import List
from PyQt5 import QtWidgets


class Dashboard(QtWidgets.QWidget):
    """显示轨迹与告警信息的面板。"""

    def __init__(self) -> None:
        super().__init__()
        self._table = QtWidgets.QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(["Track", "X(m)", "Y(m)", "Conf", "Threat"])
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("状态/轨迹"))
        layout.addWidget(self._table)

    def update_tracks(self, rows: List[tuple]) -> None:
        """更新轨迹表格。"""

        self._table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                self._table.setItem(r, c, QtWidgets.QTableWidgetItem(str(val)))
