from __future__ import annotations

import socket
from typing import Optional


class UdpSender:
    """UDP发送器。

    Attributes:
        host: 目标主机。
        port: 目标端口。
    """

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = int(port)
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send(self, data: bytes) -> None:
        """发送数据。"""

        self._sock.sendto(data, (self.host, self.port))


class UdpListener:
    """UDP监听器(可选)。"""

    def __init__(self, port: int, on_recv: Optional[callable] = None) -> None:
        self.port = int(port)
        self.on_recv = on_recv
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("0.0.0.0", self.port))
        self._sock.setblocking(False)
        self._stop = False
        self._th = None

    def start(self) -> None:
        """启动监听线程。"""

        if self._th:
            return
        import threading
        self._stop = False
        self._th = threading.Thread(target=self._loop, daemon=True)
        self._th.start()

    def stop(self) -> None:
        """停止监听线程。"""

        self._stop = True
        if self._th:
            try:
                self._th.join(timeout=1.0)
            except Exception:
                pass
            self._th = None

    def _loop(self) -> None:
        """监听循环。"""

        import time
        while not self._stop:
            try:
                data, _addr = self._sock.recvfrom(65536)
                if data and self.on_recv:
                    try:
                        self.on_recv(data)
                    except Exception:
                        pass
            except BlockingIOError:
                pass
            except Exception:
                pass
            time.sleep(0.01)
