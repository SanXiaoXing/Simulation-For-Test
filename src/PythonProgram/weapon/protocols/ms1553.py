"""1553B 协议占位。"""

from __future__ import annotations

from typing import Tuple
import random


def encode(word_count: int, payload: bytes) -> bytes:
    """编码 1553 帧。"""

    return payload[: 2 * word_count]


def decode(frame: bytes, ber: float = 0.0) -> Tuple[bytes, bool]:
    """解码并注入比特错误。"""

    if random.random() < ber:
        return frame, False
    return frame, True
