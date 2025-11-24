import socket
import threading
from typing import Optional, Callable


class UdpSender:
    """UDP发送器。

    Args:
        host: 发送目的IP地址。
        port: 发送目的端口。
    """

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = int(port)
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send(self, data: bytes) -> None:
        """发送报文。

        Args:
            data: 字节串。
        """

        self._sock.sendto(data, (self.host, self.port))


class UdpListener:
    """UDP监听器（可选）。

    非阻塞接收并回调处理。

    Args:
        port: 监听端口。
        on_recv: 接收回调函数，签名`fn(bytes)`。
    """

    def __init__(self, port: int, on_recv: Optional[Callable[[bytes], None]] = None) -> None:
        self.port = int(port)
        self.on_recv = on_recv
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(('0.0.0.0', self.port))
        self._sock.setblocking(False)
        self._th: Optional[threading.Thread] = None
        self._stop = threading.Event()

    def start(self) -> None:
        """启动监听线程。"""

        if self._th and self._th.is_alive():
            return
        self._stop.clear()
        self._th = threading.Thread(target=self._loop, daemon=True)
        self._th.start()

    def stop(self) -> None:
        """停止监听线程。"""

        self._stop.set()
        if self._th:
            self._th.join(timeout=1.0)

    def _loop(self) -> None:
        """监听循环。"""

        while not self._stop.is_set():
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
            # 简单轮询休眠
            threading.Event().wait(0.02)

