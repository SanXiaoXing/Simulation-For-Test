"""示例：向仿真器发送 UDP 观测 JSON。"""

from __future__ import annotations

import json
import socket
from datetime import datetime, timezone


def make_observation() -> dict:
    """生成观测 JSON 示例。"""

    return {
        "msg_type": "observation",
        "sensor_id": "SENSOR_01",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "obs": [
            {
                "target_id": "TGT_42",
                "range_m": 12345.6,
                "az_deg": 45.2,
                "el_deg": 1.5,
                "snr_db": 12.3,
                "rfi_flag": False,
            }
        ],
    }


def send_udp(host: str = "127.0.0.1", port: int = 9000) -> None:
    """发送单条 UDP 报文。"""

    msg = json.dumps(make_observation()).encode("utf-8")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(msg, (host, port))
    sock.close()


if __name__ == "__main__":
    send_udp()
