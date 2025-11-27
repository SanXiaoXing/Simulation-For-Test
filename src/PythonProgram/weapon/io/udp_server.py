"""UDP JSON 接收器占位。"""

from __future__ import annotations

import asyncio
import json
from typing import Optional, Callable, Awaitable


class UdpJsonServer:
    """异步 UDP JSON 接收器。"""

    def __init__(self, host: str = "127.0.0.1", port: int = 9400, on_message: Optional[Callable[[dict], Awaitable[None]]] = None) -> None:
        self._host = host
        self._port = port
        self._on_message = on_message
        self._transport = None

    def connection_made(self, transport):
        self._transport = transport

    def datagram_received(self, data: bytes, addr):
        try:
            msg = json.loads(data.decode("utf-8"))
        except Exception:
            return
        if self._on_message:
            asyncio.create_task(self._on_message(msg))

    async def start(self) -> None:
        loop = asyncio.get_running_loop()
        await loop.create_datagram_endpoint(lambda: self, local_addr=(self._host, self._port))
