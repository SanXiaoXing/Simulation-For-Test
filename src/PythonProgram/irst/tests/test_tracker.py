"""IRST 跟踪器单元测试。"""

from __future__ import annotations

from sim.tracker import Tracker


def test_tracker_creates_and_updates():
    """验证跟踪器创建与更新。"""

    tr = Tracker(gate_m=100.0)
    tr.update([(0.0, 0.0), (100.0, 0.0)])
    assert len(tr.list()) == 2
    tr.update([(10.0, 0.0)])
    xs = [t.x_m for t in tr.list()]
    assert any(abs(x - 10.0) < 6.0 for x in xs)
