"""跟踪器单元测试。"""

from __future__ import annotations

import math

from ..sim.tracker import Tracker


def test_tracker_updates_and_creates_tracks():
    """验证跟踪器能创建并更新轨迹。"""

    trk = Tracker(gate_threshold_m=100.0)
    # 初始两点，创建两条轨迹
    trk.update([(0.0, 0.0), (100.0, 0.0)])
    tracks = trk.get_tracks()
    assert len(tracks) == 2

    # 预测移动
    trk.predict(1.0)

    # 观测靠近第一条轨迹位置
    trk.update([(10.0, 0.0)])
    tracks = trk.get_tracks()
    # 第一条应靠近 (10, 0)（指数平均）
    xs = [t.x_m for t in tracks]
    assert any(abs(x - 10.0) < 6.0 for x in xs)
