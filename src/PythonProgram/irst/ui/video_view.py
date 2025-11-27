"""视频视图组件。"""

from __future__ import annotations

from typing import List, Tuple

try:
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover
    np = None  # type: ignore

from PyQt5 import QtWidgets, QtGui, QtCore


class VideoView(QtWidgets.QWidget):
    """显示热像与检测框的视图。"""

    def __init__(self, resolution: Tuple[int, int] = (640, 480)) -> None:
        super().__init__()
        self._w, self._h = resolution
        self._img = None
        self._boxes: List[Tuple[int, int, int, int, float]] = []
        self.setMinimumSize(self._w, self._h)

    def update_frame(self, img_array, boxes: List[Tuple[int, int, int, int, float]]) -> None:
        """更新图像帧与检测框。"""

        self._img = img_array
        self._boxes = boxes
        self.update()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        """绘制帧与叠加信息。"""

        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), QtGui.QColor(0, 0, 0))
        if self._img is not None and np is not None:
            h, w = self._img.shape
            qimg = QtGui.QImage(self._img.data, w, h, w, QtGui.QImage.Format_Grayscale8)
            painter.drawImage(QtCore.QPoint(0, 0), qimg.scaled(self.width(), self.height()))
        painter.setPen(QtGui.QPen(QtGui.QColor(255, 80, 80), 2))
        for x, y, ww, hh, conf in self._boxes:
            painter.drawRect(int(x * self.width() / self._w), int(y * self.height() / self._h), int(ww * self.width() / self._w), int(hh * self.height() / self._h))
            painter.drawText(int(x * self.width() / self._w), int(y * self.height() / self._h) - 2, f"{conf:.2f}")
