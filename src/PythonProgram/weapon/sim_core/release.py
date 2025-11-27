"""释放控制逻辑。

实现手动/自动释放、协同释放时序与事件日志记录。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List
import time

from .models import WeaponSystem


@dataclass
class ReleaseEvent:
    """释放事件记录。"""

    ts: float
    level: str
    message: str


@dataclass
class ReleaseController:
    """释放控制器。"""

    sys: WeaponSystem
    log: List[ReleaseEvent] = field(default_factory=list)
    running: bool = False

    def _log(self, level: str, msg: str) -> None:
        """追加日志。"""

        self.log.append(ReleaseEvent(time.time(), level, msg))

    def unlock_rack(self) -> None:
        """解锁挂架。"""

        self.sys.rack.locked = False
        self._log("INFO", "挂架解锁")

    def arm_fuze(self) -> None:
        """待发引信。"""

        self.sys.weapon.fuze.armed = True
        self._log("INFO", "引信待发")

    def start_release(self) -> bool:
        """发起释放流程。"""

        if not self.sys.can_release():
            self._log("WARN", "条件不满足，无法释放")
            return False
        self.running = True
        self.sys.weapon.state = "releasing"
        self._log("INFO", "开始释放时序")
        return True

    def step(self) -> None:
        """推进释放时序。"""

        if not self.running:
            return
        # 简化：一步完成分离
        self.sys.weapon.state = "separated"
        self._log("INFO", "武器分离完成")
        self.running = False

    def reset(self) -> None:
        """重置流程。"""

        self.sys.weapon.state = "mounted"
        self.sys.rack.locked = True
        self.sys.weapon.fuze.armed = False
        self._log("INFO", "重置完成")
