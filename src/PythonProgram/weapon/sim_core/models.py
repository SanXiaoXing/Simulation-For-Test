"""外挂系统模型定义。

包含挂架、弹射器、引信与武器状态的基础数据结构与更新逻辑。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class Rack:
    """挂架状态模型。"""

    rack_id: str
    max_load_kg: float
    locked: bool = True
    overload_protect: bool = False
    electrical_ok: bool = True


@dataclass
class Ejector:
    """弹射器状态模型。"""

    ejector_id: str
    pressure_mpa: float
    ready: bool = True
    fault: bool = False


@dataclass
class Fuze:
    """引信模型。"""

    fuze_id: str
    sensitivity: float  # 0-1
    armed: bool = False
    anti_jam: float = 0.5  # 0-1 抗干扰能力


@dataclass
class Weapon:
    """武器状态模型。"""

    weapon_id: str
    mass_kg: float
    aerodynamic_mode: str  # external/internal
    temperature_c: float = 20.0
    state: str = "mounted"  # mounted/releasing/separated
    fuze: Fuze = field(default_factory=lambda: Fuze("FZ", 0.5))


@dataclass
class WeaponSystem:
    """武器外挂系统聚合。"""

    rack: Rack
    ejector: Ejector
    weapon: Weapon

    def can_release(self) -> bool:
        """判断是否可释放。"""

        return (
            not self.rack.locked
            and self.rack.electrical_ok
            and self.ejector.ready
            and not self.ejector.fault
            and not self.rack.overload_protect
            and self.weapon.state == "mounted"
        )

    def step_temperature(self, ambient_c: float) -> None:
        """更新武器温度。"""

        target = ambient_c if self.weapon.aerodynamic_mode == "external" else ambient_c + 5.0
        self.weapon.temperature_c += (target - self.weapon.temperature_c) * 0.05
