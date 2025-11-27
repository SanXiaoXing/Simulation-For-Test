"""图像增强与天气影响模拟模块。"""

from __future__ import annotations

try:
    import cv2  # type: ignore
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore
    np = None  # type: ignore


def apply_weather_effects(img, fog: float = 0.2, noise: float = 0.01):
    """应用雾与噪声等天气效果（占位）。

    Args:
        img: 输入图像（NumPy 数组）。
        fog: 雾强度（0-1）。
        noise: 噪声强度（0-1）。

    Returns:
        处理后的图像数组；若依赖不可用，则原样返回。
    """

    if cv2 is None or np is None:
        return img
    h, w = img.shape[:2]
    overlay = np.full((h, w, 3), 255, dtype=np.uint8)
    out = cv2.addWeighted(img, 1 - fog, overlay, fog, 0)
    gauss = (np.random.randn(h, w, 3) * (noise * 255)).astype(np.int16)
    out = np.clip(out.astype(np.int16) + gauss, 0, 255).astype(np.uint8)
    return out


def adjust_contrast(img, alpha: float = 1.2):
    """调整图像对比度（占位）。

    Args:
        img: 输入图像（NumPy 数组）。
        alpha: 对比度系数。

    Returns:
        调整后的图像数组；若依赖不可用，则原样返回。
    """

    if cv2 is None:
        return img
    return cv2.convertScaleAbs(img, alpha=alpha, beta=0)
