from __future__ import annotations

import socket


class TcpSender:
    """TCP发送器(短连接)。

    每次发送建立连接并关闭，便于简单集成。
    """

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = int(port)

    def send(self, data: bytes) -> None:
        """发送数据。"""

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.05)
        try:
            sock.connect((self.host, self.port))
            sock.sendall(data)
        finally:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            sock.close()
