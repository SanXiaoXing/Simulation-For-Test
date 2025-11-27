"""视频面板占位实现。"""

from __future__ import annotations

from PyQt5 import QtWidgets


class VideoPanel(QtWidgets.QWidget):
    """简化视频面板，用于展示拼接结果（占位）。"""

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumWidth(300)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("视频拼接预览（占位）"))
