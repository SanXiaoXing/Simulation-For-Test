"""检出器模块。"""

from __future__ import annotations

from typing import List, Tuple

from .irst_sensor import Detection, IrstSensor


def detections_to_boxes(sensor: IrstSensor, dets: List[Detection], box_size: int = 16) -> List[Tuple[int, int, int, int, float]]:
    """将角度检测转换为图像框。"""

    boxes = []
    for d in dets:
        x, y = sensor.project_to_image(d.az_deg, d.el_deg)
        half = box_size // 2
        boxes.append((x - half, y - half, box_size, box_size, d.confidence))
    return boxes
