"""UDP JSON 接收服务器（简化）。

基于 asyncio 的 UDP 接收器，解析 JSON 并回调到上层处理。
"""

from __future__ import annotations

import asyncio
import json
from typing import Callable, Awaitable, Optional


class UdpJsonServer:
    """UDP JSON 服务器。

    Attributes:
        host: 监听地址。
        port: 监听端口。
        on_message: 消息回调，签名为 async def fn(dict)。
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 9000, on_message: Optional[Callable[[dict], Awaitable[None]]] = None) -> None:
        self._host = host
        self._port = port
        self._on_message = on_message
        self._transport: Optional[asyncio.transports.DatagramTransport] = None

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self._transport = transport  # type: ignore

    def datagram_received(self, data: bytes, addr) -> None:
        try:
            msg = json.loads(data.decode("utf-8"))
        except Exception:
            return
        if self._on_message:
            asyncio.create_task(self._on_message(msg))

    async def start(self) -> None:
        """启动 UDP 接收。"""

        loop = asyncio.get_running_loop()
        await loop.create_datagram_endpoint(lambda: self, local_addr=(self._host, self._port))

    async def stop(self) -> None:
        """停止 UDP 接收。"""

        if self._transport:
            self._transport.close()
