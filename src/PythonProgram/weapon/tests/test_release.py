"""释放流程单元测试。"""

from __future__ import annotations

from sim_core.models import Rack, Ejector, Fuze, Weapon, WeaponSystem
from sim_core.release import ReleaseController


def test_release_flow():
    """验证解锁与释放后状态变化。"""

    sys = WeaponSystem(Rack("R", 500.0), Ejector("E", 10.0), Weapon("W", 100.0, "external", fuze=Fuze("F", 0.5)))
    ctl = ReleaseController(sys)
    assert not ctl.start_release()
    ctl.unlock_rack()
    assert ctl.start_release()
    ctl.step()
    assert sys.weapon.state == "separated"
