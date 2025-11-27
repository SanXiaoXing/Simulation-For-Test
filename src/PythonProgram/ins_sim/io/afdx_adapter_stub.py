from __future__ import annotations


class AFDXAdapter:
    """AFDX适配器占位。

    实际系统中需映射到AFDX端口与VL，此处仅进行数据长度统计与占用率计算，可复用UDP发送作为底层传输。
    """

    def __init__(self) -> None:
        pass

    def send(self, data: bytes) -> None:
        """发送AFDX帧(占位)。"""

        # 可扩展: 添加AFDX头、VL编号等
        pass

