"""图像拼接占位模块。"""

from __future__ import annotations

try:
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover
    np = None  # type: ignore


def simple_stitch(images):
    """将多幅图像水平拼接（占位）。

    Args:
        images: 图像数组列表（形状一致）。

    Returns:
        拼接后的图像；依赖不可用时返回第一幅图。
    """

    if np is None or not images:
        return images[0] if images else None
    return np.hstack(images)
