import socket
from typing import Optional

from PyQt5.QtCore import QThread, pyqtSignal

from .models import EWSignal


class UDPReceiver(QThread):
    """UDP接收线程。

    监听指定端口的UDP报文，自动识别JSON或二进制结构体并解析为`EWSignal`对象，通过`signal_received`信号向GUI传递。

    Attributes:
        host: 绑定IP地址。
        port: 绑定端口号。
        signal_received: 信号到达时发射的Qt信号。
    """

    signal_received = pyqtSignal(object)

    def __init__(self, host: str = "0.0.0.0", port: int = 50000) -> None:
        """构造接收器。

        Args:
            host: 监听IP地址。
            port: 监听端口号。
        """

        super().__init__()
        self.host = host
        self.port = port
        self._sock: Optional[socket.socket] = None
        self._running = False

    def run(self) -> None:
        """线程运行函数，持续接收与解析报文。"""

        self._running = True
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.bind((self.host, self.port))
        self._sock.settimeout(0.5)
        while self._running:
            try:
                data, _addr = self._sock.recvfrom(2048)
            except socket.timeout:
                continue
            except Exception:
                break
            if not data:
                continue
            try:
                if data[:1] in (b"{", b"["):
                    sig = EWSignal.from_json(data.decode("utf-8"))
                else:
                    if len(data) >= 72:
                        sig = EWSignal.from_binary(data[:72])
                    else:
                        continue
                self.signal_received.emit(sig)
            except Exception:
                continue

    def stop(self) -> None:
        """停止接收线程并释放资源。"""

        self._running = False
        try:
            if self._sock is not None:
                self._sock.close()
                self._sock = None
        except Exception:
            pass

