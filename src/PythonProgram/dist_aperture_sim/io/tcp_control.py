"""TCP 控制接口（占位）。

基于 asyncio Stream 的简单命令处理示例。
"""

from __future__ import annotations

import asyncio
from typing import Callable, Awaitable


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, on_command: Callable[[str], Awaitable[str]]):
    """处理 TCP 客户端连接。

    Args:
        reader: 输入流。
        writer: 输出流。
        on_command: 命令处理回调，返回字符串响应。
    """

    data = await reader.readline()
    cmd = data.decode().strip()
    resp = await on_command(cmd)
    writer.write((resp + "\n").encode("utf-8"))
    await writer.drain()
    writer.close()


async def start_server(host: str = "127.0.0.1", port: int = 9100, on_command: Callable[[str], Awaitable[str]] = lambda s: asyncio.sleep(0) or "OK"):
    """启动 TCP 控制服务器。"""

    server = await asyncio.start_server(lambda r, w: handle_client(r, w, on_command), host, port)
    async with server:
        await server.serve_forever()
