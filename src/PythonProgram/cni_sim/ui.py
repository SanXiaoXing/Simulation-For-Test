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
