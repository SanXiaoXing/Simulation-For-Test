"""UDP 协议占位。"""

from __future__ import annotations

import socket


def send(host: str, port: int, payload: bytes) -> bool:
    """发送 UDP 数据报。"""

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.sendto(payload, (host, port))
        s.close()
        return True
    except Exception:
        return False
