"""向 IRST 仿真器发送观测 JSON 示例。"""

from __future__ import annotations

import json
import socket
from datetime import datetime, timezone


def make_observation() -> dict:
    """生成观测 JSON。"""

    return {
        "msg_type": "observation",
        "sensor_id": "IRST_FWD_01",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "frame_number": 1,
        "detections": [
            {"detection_id": "D_1", "az_deg": 10.0, "el_deg": 0.0, "snr_db": 8.2, "confidence": 0.75}
        ],
    }


def send_udp(host: str = "127.0.0.1", port: int = 9200) -> None:
    """发送 UDP 报文。"""

    msg = json.dumps(make_observation()).encode("utf-8")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(msg, (host, port))
    sock.close()


if __name__ == "__main__":
    send_udp()
