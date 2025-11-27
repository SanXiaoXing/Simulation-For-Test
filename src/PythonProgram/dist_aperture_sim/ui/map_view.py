"""地图/航迹视图实现。"""

from __future__ import annotations

from PyQt5 import QtWidgets, QtGui, QtCore


class MapView(QtWidgets.QWidget):
    """简化地图视图，用于演示传感器、目标与轨迹绘制。"""

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumHeight(400)
        self._sensors = []  # List[Tuple[float, float]]
        self._targets = []  # List[Tuple[float, float]]
        self._tracks = []   # List[Tuple[float, float]]
        self._scale = 0.05  # 像素/米

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        """绘制背景与元素。"""

        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), QtGui.QColor(30, 30, 30))
        painter.setPen(QtGui.QPen(QtGui.QColor(80, 80, 80)))
        for x in range(0, self.width(), 40):
            painter.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), 40):
            painter.drawLine(0, y, self.width(), y)
        painter.setPen(QtGui.QPen(QtGui.QColor(180, 180, 180)))
        painter.drawText(10, 20, "地图视图")

        # 原点为中心，Y 轴向上
        cx = self.width() // 2
        cy = self.height() // 2

        # 绘制传感器
        painter.setPen(QtGui.QPen(QtGui.QColor(80, 160, 255)))
        painter.setBrush(QtGui.QBrush(QtGui.QColor(80, 160, 255)))
        for x_m, y_m in self._sensors:
            x = int(cx + x_m * self._scale)
            y = int(cy - y_m * self._scale)
            painter.drawRect(x - 5, y - 5, 10, 10)

        # 绘制目标
        painter.setPen(QtGui.QPen(QtGui.QColor(240, 200, 80)))
        painter.setBrush(QtGui.QBrush(QtGui.QColor(240, 200, 80, 150)))
        for x_m, y_m in self._targets:
            x = int(cx + x_m * self._scale)
            y = int(cy - y_m * self._scale)
            painter.drawEllipse(QtCore.QPoint(x, y), 6, 6)

        # 绘制轨迹
        painter.setPen(QtGui.QPen(QtGui.QColor(120, 255, 120)))
        painter.setBrush(QtGui.QBrush(QtGui.QColor(120, 255, 120, 150)))
        for x_m, y_m in self._tracks:
            x = int(cx + x_m * self._scale)
            y = int(cy - y_m * self._scale)
            points = [QtCore.QPoint(x, y - 6), QtCore.QPoint(x - 6, y + 6), QtCore.QPoint(x + 6, y + 6)]
            painter.drawPolygon(QtGui.QPolygon(points))

    def update_scene(self, sensors, targets, tracks) -> None:
        """更新场景元素并重绘。

        Args:
            sensors: 传感器位置列表 (x_m, y_m)。
            targets: 目标位置列表 (x_m, y_m)。
            tracks: 轨迹位置列表 (x_m, y_m)。
        """

        self._sensors = sensors
        self._targets = targets
        self._tracks = tracks
        self.update()
