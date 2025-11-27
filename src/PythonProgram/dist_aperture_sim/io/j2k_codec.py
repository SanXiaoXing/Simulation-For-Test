"""JPEG2000 编解码占位模块。

优先尝试 imagecodecs/glymur，否则使用近似压缩（高斯模糊 + 量化）作为回退。
"""

from __future__ import annotations

from typing import Optional

try:
    import imagecodecs as ic  # type: ignore
except Exception:
    ic = None  # type: ignore

try:
    import glymur  # type: ignore
except Exception:
    glymur = None  # type: ignore

try:
    from PIL import Image, ImageFilter
except Exception:  # pragma: no cover
    Image = None  # type: ignore
    ImageFilter = None  # type: ignore


def encode_j2k(img_bytes: bytes, quality: int = 50) -> bytes:
    """将原始图像字节编码为 JPEG2000。

    Args:
        img_bytes: 输入图像（JPEG/PNG 等格式）字节。
        quality: 压缩质量（0-100）。

    Returns:
        编码后的字节；若库不可用，返回近似处理后的 PNG/JPEG 字节。
    """

    if ic is not None:
        # imagecodecs 不直接处理常规图片字节，此处略作简化占位
        return img_bytes
    if glymur is not None:
        return img_bytes
    # 回退：轻度模糊 + 量化近似压缩
    if Image is None:
        return img_bytes
    from io import BytesIO

    with BytesIO(img_bytes) as bio:
        im = Image.open(bio)
        im = im.filter(ImageFilter.GaussianBlur(radius=max(0, (100 - quality) / 50)))
        out = BytesIO()
        im.save(out, format="JPEG", quality=max(10, min(95, quality)))
        return out.getvalue()


def decode_j2k(j2k_bytes: bytes) -> bytes:
    """解码 JPEG2000 字节为标准图像字节。

    Args:
        j2k_bytes: JPEG2000 字节。

    Returns:
        解码后的常规图像字节；库不可用时原样返回。
    """

    return j2k_bytes
