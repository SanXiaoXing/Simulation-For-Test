from typing import Callable, Optional

from PyQt5 import QtWidgets, QtCore
import time

from src.PythonProgram.cni_sim.models import CNIState, Target
from src.PythonProgram.cni_sim.engine import step as sim_step
from src.PythonProgram.cni_sim.protocol import build_frame, frame_to_hex
from src.PythonProgram.cni_sim.udp import UdpSender, UdpListener


class MainWindow(QtWidgets.QMainWindow):
    """CNI仿真主界面。

    提供参数录入、目标管理、仿真控制和报文发送。

    Args:
        state: 初始仿真状态对象。
        out_host: 发送目的IP。
        out_port: 发送目的端口。
        listen_port: 可选监听端口（为0则不监听）。
    """

    def __init__(self, state: CNIState, out_host: str, out_port: int, listen_port: int = 0) -> None:
        super().__init__()
        self.state = state
        self.sender = UdpSender(out_host, out_port)
        self.listener: Optional[UdpListener] = None
        if listen_port > 0:
            self.listener = UdpListener(listen_port, on_recv=self._on_recv)
            self.listener.start()

        self.setWindowTitle('CNI通信导航识别接口特征仿真')
        self.resize(1100, 700)
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._build_ui()
        self._hook_listeners()
        self._on_input_changed()

    def _build_ui(self) -> None:
        """构建界面组件。"""

        root = QtWidgets.QWidget()
        self.setCentralWidget(root)
        layout = QtWidgets.QVBoxLayout(root)

        # 顶部控制栏
        ctrl = QtWidgets.QHBoxLayout()
        self.spin_dt = QtWidgets.QDoubleSpinBox()
        self.spin_dt.setRange(0.05, 2.0)
        self.spin_dt.setSingleStep(0.05)
        self.spin_dt.setValue(self.state.dt_s)
        self.btn_start = QtWidgets.QPushButton('开始仿真')
        self.btn_stop = QtWidgets.QPushButton('停止仿真')
        self.btn_start.clicked.connect(self._start)
        self.btn_stop.clicked.connect(self._stop)
        self.combo_mode = QtWidgets.QComboBox()
        self.combo_mode.addItems(['雷达(1)', '通信导航(2)'])
        self.edit_out_host = QtWidgets.QLineEdit('127.0.0.1')
        self.spin_out_port = QtWidgets.QSpinBox()
        self.spin_out_port.setRange(1, 65535)
        self.spin_out_port.setValue(6006)
        ctrl.addWidget(QtWidgets.QLabel('dt(s)'))
        ctrl.addWidget(self.spin_dt)
        ctrl.addWidget(QtWidgets.QLabel('模式'))
        ctrl.addWidget(self.combo_mode)
        ctrl.addWidget(QtWidgets.QLabel('目的IP'))
        ctrl.addWidget(self.edit_out_host)
        ctrl.addWidget(QtWidgets.QLabel('端口'))
        ctrl.addWidget(self.spin_out_port)
        ctrl.addWidget(self.btn_start)
        ctrl.addWidget(self.btn_stop)
        layout.addLayout(ctrl)

        splitter = QtWidgets.QSplitter()
        splitter.setOrientation(QtCore.Qt.Horizontal)
        layout.addWidget(splitter)

        # 左侧：目标列表
        left = QtWidgets.QWidget()
        lyt_left = QtWidgets.QVBoxLayout(left)
        self.table_targets = QtWidgets.QTableWidget(0, 9)
        self.table_targets.setHorizontalHeaderLabels(
            ['id', 'lat', 'lon', 'alt', 'vN', 'vE', 'vD', 'az', 'iff']
        )
        self.table_targets.horizontalHeader().setStretchLastSection(True)
        btns = QtWidgets.QHBoxLayout()
        self.btn_add_target = QtWidgets.QPushButton('新增目标')
        self.btn_del_target = QtWidgets.QPushButton('删除选中')
        self.btn_add_target.clicked.connect(self._add_target)
        self.btn_del_target.clicked.connect(self._del_target)
        btns.addWidget(self.btn_add_target)
        btns.addWidget(self.btn_del_target)
        lyt_left.addWidget(self.table_targets)
        lyt_left.addLayout(btns)
        splitter.addWidget(left)

        # 右侧：模块参数与日志
        right = QtWidgets.QTabWidget()
        splitter.addWidget(right)

        # 短波通信
        tab_sw = QtWidgets.QWidget()
        lyt_sw = QtWidgets.QFormLayout(tab_sw)
        self.spin_src = QtWidgets.QSpinBox(); self.spin_src.setRange(0, 255)
        self.spin_dst = QtWidgets.QSpinBox(); self.spin_dst.setRange(0, 255)
        self.spin_tx = QtWidgets.QDoubleSpinBox(); self.spin_tx.setRange(-200.0, 100.0)
        self.spin_freq = QtWidgets.QDoubleSpinBox(); self.spin_freq.setRange(0, 1e10); self.spin_freq.setDecimals(2)
        self.spin_tstamp = QtWidgets.QDoubleSpinBox(); self.spin_tstamp.setRange(0, 86400); self.spin_tstamp.setDecimals(0); self.spin_tstamp.setReadOnly(True); self.spin_tstamp.setValue(0)
        lyt_sw.addRow('source_id', self.spin_src)
        lyt_sw.addRow('dest_id', self.spin_dst)
        lyt_sw.addRow('tx_power_dbm', self.spin_tx)
        lyt_sw.addRow('frequency_hz', self.spin_freq)
        lyt_sw.addRow('timestamp_s', self.spin_tstamp)
        right.addTab(tab_sw, '短波通信')

        # ALT
        tab_alt = QtWidgets.QWidget()
        lyt_alt = QtWidgets.QFormLayout(tab_alt)
        self.chk_alt_active = QtWidgets.QCheckBox('启用')
        self.spin_alt_freq = QtWidgets.QDoubleSpinBox(); self.spin_alt_freq.setRange(0, 1e10); self.spin_alt_freq.setDecimals(2)
        lyt_alt.addRow('active', self.chk_alt_active)
        lyt_alt.addRow('frequency_hz', self.spin_alt_freq)
        right.addTab(tab_alt, '无线电高度表')

        # 导航/惯导
        tab_nav = QtWidgets.QWidget()
        lyt_nav = QtWidgets.QFormLayout(tab_nav)
        self.spin_lat = QtWidgets.QDoubleSpinBox(); self.spin_lat.setRange(-90.0, 90.0); self.spin_lat.setDecimals(6)
        self.spin_lon = QtWidgets.QDoubleSpinBox(); self.spin_lon.setRange(-180.0, 180.0); self.spin_lon.setDecimals(6)
        self.spin_alt = QtWidgets.QDoubleSpinBox(); self.spin_alt.setRange(-1000.0, 50000.0)
        self.spin_ias = QtWidgets.QDoubleSpinBox(); self.spin_ias.setRange(0.0, 2000.0)
        self.spin_gs = QtWidgets.QDoubleSpinBox(); self.spin_gs.setRange(0.0, 2000.0)
        self.spin_ax = QtWidgets.QDoubleSpinBox(); self.spin_ax.setRange(-200.0, 200.0)
        self.spin_ay = QtWidgets.QDoubleSpinBox(); self.spin_ay.setRange(-200.0, 200.0)
        self.spin_az = QtWidgets.QDoubleSpinBox(); self.spin_az.setRange(-200.0, 200.0)
        self.spin_wx = QtWidgets.QDoubleSpinBox(); self.spin_wx.setRange(-50.0, 50.0)
        self.spin_wy = QtWidgets.QDoubleSpinBox(); self.spin_wy.setRange(-50.0, 50.0)
        self.spin_wz = QtWidgets.QDoubleSpinBox(); self.spin_wz.setRange(-50.0, 50.0)
        self.spin_pitch = QtWidgets.QDoubleSpinBox(); self.spin_pitch.setRange(-90.0, 90.0)
        self.spin_roll = QtWidgets.QDoubleSpinBox(); self.spin_roll.setRange(-180.0, 180.0)
        self.spin_yaw = QtWidgets.QDoubleSpinBox(); self.spin_yaw.setRange(-180.0, 180.0)
        lyt_nav.addRow('ego_lat_deg', self.spin_lat)
        lyt_nav.addRow('ego_lon_deg', self.spin_lon)
        lyt_nav.addRow('ego_alt_m', self.spin_alt)
        lyt_nav.addRow('airspeed_mps', self.spin_ias)
        lyt_nav.addRow('groundspeed_mps', self.spin_gs)
        lyt_nav.addRow('accel_mps2_x', self.spin_ax)
        lyt_nav.addRow('accel_mps2_y', self.spin_ay)
        lyt_nav.addRow('accel_mps2_z', self.spin_az)
        lyt_nav.addRow('ang_rate_rps_x', self.spin_wx)
        lyt_nav.addRow('ang_rate_rps_y', self.spin_wy)
        lyt_nav.addRow('ang_rate_rps_z', self.spin_wz)
        lyt_nav.addRow('attitude_pitch', self.spin_pitch)
        lyt_nav.addRow('attitude_roll', self.spin_roll)
        lyt_nav.addRow('attitude_yaw', self.spin_yaw)
        right.addTab(tab_nav, '导航/惯导')

        # 日志与报文
        tab_log = QtWidgets.QWidget()
        lyt_log = QtWidgets.QVBoxLayout(tab_log)
        self.text_log = QtWidgets.QPlainTextEdit(); self.text_log.setReadOnly(True)
        self.text_hex = QtWidgets.QPlainTextEdit(); self.text_hex.setReadOnly(True)
        self.btn_gen_hex = QtWidgets.QPushButton('生成测试帧')
        self.btn_gen_hex.clicked.connect(self._gen_hex)
        lyt_log.addWidget(QtWidgets.QLabel('日志'))
        lyt_log.addWidget(self.text_log)
        lyt_log.addWidget(QtWidgets.QLabel('十六进制帧'))
        lyt_log.addWidget(self.text_hex)
        lyt_log.addWidget(self.btn_gen_hex)
        right.addTab(tab_log, '日志与报文')

        # 初始化一行示例目标
        self._add_target()

    def _start(self) -> None:
        """开始仿真与下发。"""

        self.state.dt_s = float(self.spin_dt.value())
        mode_text = self.combo_mode.currentText()
        self.state.frame_mode = 1 if '雷达' in mode_text else 2
        # 更新sender目的地址
        self.sender = UdpSender(self.edit_out_host.text().strip(), int(self.spin_out_port.value()))
        self._timer.start(int(self.state.dt_s * 1000))
        self._log('仿真开始')

    def _stop(self) -> None:
        """停止仿真。"""

        self._timer.stop()
        self._log('仿真停止')

    def _on_tick(self) -> None:
        """周期回调：推进仿真，打包并发送。"""

        self._pull_state_from_ui()
        sim_step(self.state)
        # 将最新系统时间戳回显到界面
        try:
            self.spin_tstamp.setValue(float(self.state.shortwave.timestamp_s))
        except Exception:
            pass
        frame = build_frame(self.state)
        try:
            self.sender.send(frame)
            self._log(f'发送帧 len={len(frame)} sim_time={self.state.sim_time_s:.3f}')
        except Exception as e:
            self._log(f'发送失败: {e!r}')

    def _hook_listeners(self) -> None:
        """建立数据变更监听机制并注册响应逻辑。

        当界面控件或目标表格数据发生变化时，自动进行数据验证、状态更新、
        数据联动（构建并发送更新报文）。

        """

        try:
            self.table_targets.itemChanged.connect(lambda _item: self._on_input_changed())
        except Exception:
            pass

        for w in [
            self.spin_dt,
            self.spin_src, self.spin_dst, self.spin_tx, self.spin_freq,
            self.chk_alt_active, self.spin_alt_freq,
            self.spin_lat, self.spin_lon, self.spin_alt,
            self.spin_ias, self.spin_gs,
            self.spin_ax, self.spin_ay, self.spin_az,
            self.spin_wx, self.spin_wy, self.spin_wz,
            self.spin_pitch, self.spin_roll, self.spin_yaw,
            self.combo_mode,
            self.edit_out_host, self.spin_out_port,
        ]:
            try:
                if hasattr(w, 'valueChanged'):
                    w.valueChanged.connect(self._on_input_changed)
                elif hasattr(w, 'toggled'):
                    w.toggled.connect(self._on_input_changed)
                elif hasattr(w, 'currentIndexChanged'):
                    w.currentIndexChanged.connect(lambda _idx: self._on_input_changed())
                elif hasattr(w, 'textChanged'):
                    w.textChanged.connect(lambda _txt: self._on_input_changed())
            except Exception:
                pass

    def _on_input_changed(self) -> None:
        """输入变更回调：响应式处理逻辑。

        执行顺序：
        1) 从界面拉取状态
        2) 数据验证（业务规则与数据类型）
        3) 状态更新（自动字段与派生量）
        4) 数据联动（构建并发送更新报文，并显示十六进制）

        """

        try:
            self._pull_state_from_ui()
        except Exception as e:
            self._log(f'拉取状态失败: {e!r}')
            return

        ok, errors = validate_state(self.state)
        self._apply_validation_feedback(errors)
        if not ok:
            self._log('输入校验失败，已阻止发送更新帧')
            return

        self._apply_state_effects()
        try:
            frame = build_frame(self.state)
            self.text_hex.setPlainText(frame_to_hex(frame, group=1))
            self.sender.send(frame)
            self._log(f'更新帧已发送 len={len(frame)}')
        except Exception as e:
            self._log(f'更新帧发送失败: {e!r}')

    def _apply_state_effects(self) -> None:
        """根据初始值和当前输入自动更新相关组件状态。"""

        # 短波时间戳自动刷新为当前系统时分秒
        lt = time.localtime()
        try:
            self.state.shortwave.timestamp_s = float(lt.tm_hour * 3600 + lt.tm_min * 60 + lt.tm_sec)
            self.spin_tstamp.setValue(self.state.shortwave.timestamp_s)
        except Exception:
            pass

        # 导航派生量：若未填写地速，则依据空速回填（简化）
        try:
            if float(self.state.nav.groundspeed_mps) <= 0.0 and float(self.state.nav.airspeed_mps) > 0.0:
                self.state.nav.groundspeed_mps = float(self.state.nav.airspeed_mps)
        except Exception:
            pass

        # 模式联动：从组合框确定frame_mode
        try:
            mode_text = self.combo_mode.currentText()
            self.state.frame_mode = 1 if '雷达' in mode_text else 2
        except Exception:
            pass

    def _apply_validation_feedback(self, errors: list) -> None:
        """将校验结果反馈到UI（高亮错误控件并日志提示）。

        Args:
            errors: 错误信息列表，每项为字典包含`field`与`msg`。
        """

        # 清理目标表格背景
        try:
            for r in range(self.table_targets.rowCount()):
                for c in range(self.table_targets.columnCount()):
                    item = self.table_targets.item(r, c)
                    if item:
                        item.setBackground(QtCore.Qt.white)
        except Exception:
            pass

        # 高亮错误项
        for err in errors:
            f = err.get('field', '')
            msg = err.get('msg', '')
            self._log(f'校验错误: {f} -> {msg}')
            if f.startswith('targets['):
                try:
                    idx = f[len('targets['):].split(']')[0]
                    row = int(idx)
                    col_map = {
                        'id': 0, 'lat': 1, 'lon': 2, 'alt': 3,
                        'vN': 4, 'vE': 5, 'vD': 6, 'az': 7, 'iff': 8,
                    }
                    for key, col in col_map.items():
                        if f.endswith(key):
                            item = self.table_targets.item(row, col)
                            if item:
                                item.setBackground(QtCore.Qt.red)
                            break
                except Exception:
                    pass
            else:
                # 简单反馈：无控件映射时仅日志
                pass


    def _pull_state_from_ui(self) -> None:
        """从界面读取输入更新状态。"""

        # 目标表格 -> state.targets
        targets = []
        for row in range(self.table_targets.rowCount()):
            def _val(col: int) -> float:
                item = self.table_targets.item(row, col)
                return float(item.text()) if item else 0.0

            t = Target(
                target_id=int(_val(0)),
                lat_deg=_val(1),
                lon_deg=_val(2),
                alt_m=_val(3),
                vel_ned_mps_N=_val(4),
                vel_ned_mps_E=_val(5),
                vel_ned_mps_D=_val(6),
                azimuth_deg=_val(7),
                iff_code=int(_val(8)),
            )
            targets.append(t)
        self.state.targets = targets

        # 短波
        sw = self.state.shortwave
        sw.source_id = int(self.spin_src.value())
        sw.dest_id = int(self.spin_dst.value())
        sw.tx_power_dbm = float(self.spin_tx.value())
        sw.frequency_hz = float(self.spin_freq.value())
        # 时间戳不再由UI控件写入，由引擎自动刷新为系统时间
        # sw.timestamp_s = float(self.spin_tstamp.value())

        # ALT
        self.state.altimeter.active = 1 if self.chk_alt_active.isChecked() else 0
        self.state.altimeter.frequency_hz = float(self.spin_alt_freq.value())

        # 导航
        nav = self.state.nav
        nav.ego_lat_deg = float(self.spin_lat.value())
        nav.ego_lon_deg = float(self.spin_lon.value())
        nav.ego_alt_m = float(self.spin_alt.value())
        nav.airspeed_mps = float(self.spin_ias.value())
        nav.groundspeed_mps = float(self.spin_gs.value())
        nav.accel_mps2[0] = float(self.spin_ax.value())
        nav.accel_mps2[1] = float(self.spin_ay.value())
        nav.accel_mps2[2] = float(self.spin_az.value())
        nav.ang_rate_rps[0] = float(self.spin_wx.value())
        nav.ang_rate_rps[1] = float(self.spin_wy.value())
        nav.ang_rate_rps[2] = float(self.spin_wz.value())
        nav.attitude_deg[0] = float(self.spin_pitch.value())
        nav.attitude_deg[1] = float(self.spin_roll.value())
        nav.attitude_deg[2] = float(self.spin_yaw.value())

    def _add_target(self) -> None:
        """新增一个目标行，填充默认示例值。"""

        r = self.table_targets.rowCount()
        self.table_targets.insertRow(r)
        defaults = ['1', '30.0', '120.0', '1000.0', '0.0', '0.0', '0.0', '0.0', '0']
        for c, val in enumerate(defaults):
            item = QtWidgets.QTableWidgetItem(val)
            self.table_targets.setItem(r, c, item)

    def _del_target(self) -> None:
        """删除选中的目标行。"""

        rows = {idx.row() for idx in self.table_targets.selectedIndexes()}
        for row in sorted(rows, reverse=True):
            self.table_targets.removeRow(row)

    def _gen_hex(self) -> None:
        """生成当前状态的十六进制帧并显示。"""

        self._pull_state_from_ui()
        frame = build_frame(self.state)
        self.text_hex.setPlainText(frame_to_hex(frame, group=1))
        self._log(f'生成测试帧 len={len(frame)}')

    def _on_recv(self, data: bytes) -> None:
        """接收回调：打印数据长度。"""

        self._log(f'RX {len(data)} 字节')

    def _log(self, msg: str) -> None:
        """追加日志信息。"""

        self.text_log.appendPlainText(msg)


def validate_state(state: CNIState) -> (bool, list):
    """校验仿真状态的业务规则与数据类型。

    校验范围覆盖目标、短波、无线电高度表与导航数据。

    Args:
        state: 待校验的仿真状态。

    Returns:
        Tuple[bool, list]: 是否通过与错误列表，每项包含字段名与错误信息。
    """

    errs = []

    def in_range(val, lo, hi) -> bool:
        try:
            v = float(val)
        except Exception:
            return False
        return (v >= lo) and (v <= hi)

    # 目标
    for i, t in enumerate(state.targets):
        if not (isinstance(t.target_id, int) and 0 <= int(t.target_id) <= 255):
            errs.append({'field': f'targets[{i}].id', 'msg': '目标ID需为0~255整数'})
        if not in_range(t.lat_deg, -90.0, 90.0):
            errs.append({'field': f'targets[{i}].lat', 'msg': '纬度范围-90~90'})
        if not in_range(t.lon_deg, -180.0, 180.0):
            errs.append({'field': f'targets[{i}].lon', 'msg': '经度范围-180~180'})
        if not in_range(t.alt_m, -1000.0, 50000.0):
            errs.append({'field': f'targets[{i}].alt', 'msg': '高度范围-1000~50000'})
        if not in_range(t.vel_ned_mps_N, -200.0, 200.0):
            errs.append({'field': f'targets[{i}].vN', 'msg': '北向速度范围-200~200'})
        if not in_range(t.vel_ned_mps_E, -200.0, 200.0):
            errs.append({'field': f'targets[{i}].vE', 'msg': '东向速度范围-200~200'})
        if not in_range(t.vel_ned_mps_D, -200.0, 200.0):
            errs.append({'field': f'targets[{i}].vD', 'msg': '下降速度范围-200~200'})
        if not in_range(t.azimuth_deg, 0.0, 360.0):
            errs.append({'field': f'targets[{i}].az', 'msg': '方位角范围0~360'})
        if not (isinstance(t.iff_code, int) and 0 <= int(t.iff_code) <= 255):
            errs.append({'field': f'targets[{i}].iff', 'msg': 'IFF需为0~255整数'})

    # 短波
    sw = state.shortwave
    if not (isinstance(sw.source_id, int) and 0 <= int(sw.source_id) <= 255):
        errs.append({'field': 'shortwave.source_id', 'msg': 'source_id需为0~255整数'})
    if not (isinstance(sw.dest_id, int) and 0 <= int(sw.dest_id) <= 255):
        errs.append({'field': 'shortwave.dest_id', 'msg': 'dest_id需为0~255整数'})
    if not in_range(sw.tx_power_dbm, -200.0, 100.0):
        errs.append({'field': 'shortwave.tx_power_dbm', 'msg': '功率范围-200~100dBm'})
    if not in_range(sw.frequency_hz, 0.0, 1e10):
        errs.append({'field': 'shortwave.frequency_hz', 'msg': '频率范围0~1e10Hz'})
    if not in_range(sw.timestamp_s, 0.0, 86400.0):
        errs.append({'field': 'shortwave.timestamp_s', 'msg': '时间戳范围0~86400'})

    # ALT
    alt = state.altimeter
    if int(getattr(alt, 'active', 0)) not in (0, 1):
        errs.append({'field': 'altimeter.active', 'msg': 'active需为0或1'})
    if not in_range(alt.frequency_hz, 0.0, 1e10):
        errs.append({'field': 'altimeter.frequency_hz', 'msg': '频率范围0~1e10Hz'})

    # 导航
    nav = state.nav
    if not in_range(nav.ego_lat_deg, -90.0, 90.0):
        errs.append({'field': 'nav.ego_lat_deg', 'msg': '本机纬度范围-90~90'})
    if not in_range(nav.ego_lon_deg, -180.0, 180.0):
        errs.append({'field': 'nav.ego_lon_deg', 'msg': '本机经度范围-180~180'})
    if not in_range(nav.ego_alt_m, -1000.0, 50000.0):
        errs.append({'field': 'nav.ego_alt_m', 'msg': '本机高度范围-1000~50000'})
    if not in_range(nav.airspeed_mps, 0.0, 2000.0):
        errs.append({'field': 'nav.airspeed_mps', 'msg': '空速范围0~2000'})
    if not in_range(nav.groundspeed_mps, 0.0, 2000.0):
        errs.append({'field': 'nav.groundspeed_mps', 'msg': '地速范围0~2000'})
    for i, lab, lo, hi in [
        (0, 'accel_x', -200.0, 200.0),
        (1, 'accel_y', -200.0, 200.0),
        (2, 'accel_z', -200.0, 200.0),
    ]:
        if not in_range(nav.accel_mps2[i], lo, hi):
            errs.append({'field': f'nav.{lab}', 'msg': f'{lab}范围{lo}~{hi}'})
    for i, lab, lo, hi in [
        (0, 'ang_rate_x', -50.0, 50.0),
        (1, 'ang_rate_y', -50.0, 50.0),
        (2, 'ang_rate_z', -50.0, 50.0),
    ]:
        if not in_range(nav.ang_rate_rps[i], lo, hi):
            errs.append({'field': f'nav.{lab}', 'msg': f'{lab}范围{lo}~{hi}'})
    for i, lab, lo, hi in [
        (0, 'pitch', -90.0, 90.0),
        (1, 'roll', -180.0, 180.0),
        (2, 'yaw', -180.0, 180.0),
    ]:
        if not in_range(nav.attitude_deg[i], lo, hi):
            errs.append({'field': f'nav.{lab}', 'msg': f'{lab}范围{lo}~{hi}'})

    return (len(errs) == 0, errs)
