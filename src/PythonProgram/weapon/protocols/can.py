"""CAN 协议占位。"""

from __future__ import annotations

from typing import Tuple


def pack(id_: int, data: bytes) -> bytes:
    """打包 CAN 帧。"""

    return id_.to_bytes(4, "big") + data[:8]


def unpack(frame: bytes) -> Tuple[int, bytes]:
    """解包 CAN 帧。"""

    return int.from_bytes(frame[:4], "big"), frame[4:]
