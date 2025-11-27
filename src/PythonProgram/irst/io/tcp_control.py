"""TCP 控制接口占位。"""

from __future__ import annotations

import asyncio


async def start_server(host: str = "127.0.0.1", port: int = 9300):
    """启动简单 TCP 控制服务。"""

    async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        data = await reader.readline()
        writer.write(b"OK\n")
        await writer.drain()
        writer.close()

    srv = await asyncio.start_server(handle, host, port)
    async with srv:
        await srv.serve_forever()
