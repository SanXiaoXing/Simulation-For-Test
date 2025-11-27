from __future__ import annotations

import os
from typing import Optional

from PyQt5 import QtCore, QtWidgets

from ..models import INSParameters, IMUFaultConfig, NetworkConfig, TrajectoryType, VehicleState
from ..sim_core import INSSimulator


class INSMainWindow(QtWidgets.QMainWindow):
    """惯性导航接口模拟器主窗口。"""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("惯性导航接口特征仿真器")
        self.resize(1100, 700)
        self.sim = INSSimulator(VehicleState(), INSParameters())
        self.sim.frame_signal.connect(self._on_frame)
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._update_ui_tick)
        self._build_ui()

    def _build_ui(self) -> None:
        """搭建界面。"""

        cw = QtWidgets.QWidget()
        self.setCentralWidget(cw)
        layout = QtWidgets.QHBoxLayout(cw)

        left = QtWidgets.QVBoxLayout()
        right = QtWidgets.QVBoxLayout()
        layout.addLayout(left, 2)
        layout.addLayout(right, 3)

        box_cfg = QtWidgets.QGroupBox("仿真配置")
        form = QtWidgets.QFormLayout(box_cfg)
        self.spin_rate = QtWidgets.QDoubleSpinBox(); self.spin_rate.setRange(50.0, 2000.0); self.spin_rate.setValue(400.0)
        self.combo_traj = QtWidgets.QComboBox(); self.combo_traj.addItems(["直线", "曲线", "转弯"])
        self.edit_lat = QtWidgets.QDoubleSpinBox(); self.edit_lat.setRange(-90.0, 90.0); self.edit_lat.setValue(31.23)
        self.edit_lon = QtWidgets.QDoubleSpinBox(); self.edit_lon.setRange(-180.0, 180.0); self.edit_lon.setValue(121.47)
        self.edit_alt = QtWidgets.QDoubleSpinBox(); self.edit_alt.setRange(-1000.0, 20000.0); self.edit_alt.setValue(1000.0)
        self.edit_gs = QtWidgets.QDoubleSpinBox(); self.edit_gs.setRange(0.0, 400.0); self.edit_gs.setValue(120.0)
        form.addRow("更新频率(Hz)", self.spin_rate)
        form.addRow("轨迹类型", self.combo_traj)
        form.addRow("纬度(°)", self.edit_lat)
        form.addRow("经度(°)", self.edit_lon)
        form.addRow("高度(m)", self.edit_alt)
        form.addRow("地速(m/s)", self.edit_gs)
        left.addWidget(box_cfg)

        box_net = QtWidgets.QGroupBox("接口配置/带宽")
        nform = QtWidgets.QFormLayout(box_net)
        self.edit_host = QtWidgets.QLineEdit("127.0.0.1")
        self.spin_port = QtWidgets.QSpinBox(); self.spin_port.setRange(1, 65535); self.spin_port.setValue(9001)
        self.combo_proto = QtWidgets.QComboBox(); self.combo_proto.addItems(["udp", "tcp", "afdx", "fc"])
        self.spin_link = QtWidgets.QDoubleSpinBox(); self.spin_link.setRange(1e6, 1e9); self.spin_link.setDecimals(0); self.spin_link.setValue(100e6)
        self.edit_icd = QtWidgets.QLineEdit("")
        btn_icd = QtWidgets.QPushButton("选择ICD文件")
        btn_icd.clicked.connect(self._select_icd)
        self.lbl_bw = QtWidgets.QLabel("带宽占用: 0.00%")
        self.spin_listen = QtWidgets.QSpinBox(); self.spin_listen.setRange(0, 65535); self.spin_listen.setValue(0)
        nform.addRow("监听端口(控制)", self.spin_listen)
        nform.addRow("目标主机", self.edit_host)
        nform.addRow("目标端口", self.spin_port)
        nform.addRow("协议", self.combo_proto)
        nform.addRow("链路速率(bps)", self.spin_link)
        nform.addRow("ICD路径", self.edit_icd)
        nform.addRow("", btn_icd)
        nform.addRow("", self.lbl_bw)
        left.addWidget(box_net)

        box_fault = QtWidgets.QGroupBox("异常模拟")
        fform = QtWidgets.QFormLayout(box_fault)
        self.chk_dropout = QtWidgets.QCheckBox("丢失")
        self.chk_spike = QtWidgets.QCheckBox("冲击")
        self.chk_bias = QtWidgets.QCheckBox("偏置阶跃")
        self.chk_sat = QtWidgets.QCheckBox("饱和")
        fform.addRow(self.chk_dropout, self.chk_spike)
        fform.addRow(self.chk_bias, self.chk_sat)
        left.addWidget(box_fault)

        hbtn = QtWidgets.QHBoxLayout()
        self.btn_start = QtWidgets.QPushButton("启动仿真")
        self.btn_stop = QtWidgets.QPushButton("停止仿真")
        self.btn_stop.setEnabled(False)
        self.btn_start.clicked.connect(self._on_start)
        self.btn_stop.clicked.connect(self._on_stop)
        hbtn.addWidget(self.btn_start); hbtn.addWidget(self.btn_stop)
        left.addLayout(hbtn)

        box_disp = QtWidgets.QGroupBox("参数实时显示")
        dform = QtWidgets.QFormLayout(box_disp)
        self.lbl_lat = QtWidgets.QLabel("0.000000")
        self.lbl_lon = QtWidgets.QLabel("0.000000")
        self.lbl_alt = QtWidgets.QLabel("0.0")
        self.lbl_ias = QtWidgets.QLabel("0.0")
        self.lbl_gs = QtWidgets.QLabel("0.0")
        self.lbl_ax = QtWidgets.QLabel("0.0")
        self.lbl_ay = QtWidgets.QLabel("0.0")
        self.lbl_az = QtWidgets.QLabel("0.0")
        self.lbl_wx = QtWidgets.QLabel("0.0")
        self.lbl_wy = QtWidgets.QLabel("0.0")
        self.lbl_wz = QtWidgets.QLabel("0.0")
        self.lbl_pitch = QtWidgets.QLabel("0.0")
        self.lbl_roll = QtWidgets.QLabel("0.0")
        self.lbl_yaw = QtWidgets.QLabel("0.0")
        dform.addRow("纬度(°)", self.lbl_lat)
        dform.addRow("经度(°)", self.lbl_lon)
        dform.addRow("高度(m)", self.lbl_alt)
        dform.addRow("空速(m/s)", self.lbl_ias)
        dform.addRow("地速(m/s)", self.lbl_gs)
        dform.addRow("加速度X", self.lbl_ax)
        dform.addRow("加速度Y", self.lbl_ay)
        dform.addRow("加速度Z", self.lbl_az)
        dform.addRow("角速率X", self.lbl_wx)
        dform.addRow("角速率Y", self.lbl_wy)
        dform.addRow("角速率Z", self.lbl_wz)
        dform.addRow("俯仰", self.lbl_pitch)
        dform.addRow("滚转", self.lbl_roll)
        dform.addRow("航向", self.lbl_yaw)
        right.addWidget(box_disp)

        box_rec = QtWidgets.QGroupBox("记录/重放")
        rform = QtWidgets.QFormLayout(box_rec)
        self.chk_record = QtWidgets.QCheckBox("记录启用")
        self.edit_rec_path = QtWidgets.QLineEdit("ins_record.jsonl")
        self.chk_replay = QtWidgets.QCheckBox("重放启用")
        self.edit_replay_path = QtWidgets.QLineEdit("ins_record.jsonl")
        rform.addRow(self.chk_record, self.edit_rec_path)
        rform.addRow(self.chk_replay, self.edit_replay_path)
        right.addWidget(box_rec)

        self.log = QtWidgets.QTextEdit(); self.log.setReadOnly(True)
        right.addWidget(self.log, 1)

    def _select_icd(self) -> None:
        """选择ICD文件。"""

        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "选择ICD文件", os.getcwd(), "JSON (*.json);;YAML (*.yaml *.yml)")
        if path:
            self.edit_icd.setText(path)

    def _on_start(self) -> None:
        """启动仿真。"""

        params = INSParameters(update_hz=float(self.spin_rate.value()))
        st = VehicleState(
            lat_deg=float(self.edit_lat.value()),
            lon_deg=float(self.edit_lon.value()),
            alt_m=float(self.edit_alt.value()),
            groundspeed_mps=float(self.edit_gs.value()),
            airspeed_mps=float(self.edit_gs.value()),
        )
        self.sim.state = st
        net = NetworkConfig(
            out_host=self.edit_host.text().strip() or "127.0.0.1",
            out_port=int(self.spin_port.value()),
            protocol=self.combo_proto.currentText(),
            link_speed_bps=float(self.spin_link.value()),
            icd_path=(self.edit_icd.text().strip() or None),
        )
        faults = IMUFaultConfig(
            dropout=self.chk_dropout.isChecked(),
            spike=self.chk_spike.isChecked(),
            bias_step=self.chk_bias.isChecked(),
            saturation=self.chk_sat.isChecked(),
        )
        traj_idx = self.combo_traj.currentIndex()
        traj_type = [TrajectoryType.STRAIGHT, TrajectoryType.CURVE, TrajectoryType.TURN][min(2, max(0, traj_idx))]
        self.sim.configure(params=params, net=net, faults=faults, traj_type=traj_type)
        self.sim.record.enable_record = self.chk_record.isChecked()
        self.sim.record.record_path = self.edit_rec_path.text().strip() or "ins_record.jsonl"
        self.sim.record.enable_replay = self.chk_replay.isChecked()
        self.sim.record.replay_path = self.edit_replay_path.text().strip() or "ins_record.jsonl"
        self.sim.start()
        lp = int(self.spin_listen.value())
        if lp > 0:
            self.sim.start_control_listener(lp)
        self._timer.start(50)
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.log.append("[INFO] 仿真启动")

    def _on_stop(self) -> None:
        """停止仿真。"""

        self.sim.stop()
        self._timer.stop()
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.log.append("[INFO] 仿真停止")

    def _on_frame(self, frame: dict) -> None:
        """接收仿真帧。"""

        bw = frame.get("bandwidth_pct", 0.0)
        self.lbl_bw.setText(f"带宽占用: {bw:.2f}%")

    def _update_ui_tick(self) -> None:
        """UI周期更新。"""

        st = self.sim.state
        imu = self.sim.imu.read(st)
        self.lbl_lat.setText(f"{st.lat_deg:.6f}")
        self.lbl_lon.setText(f"{st.lon_deg:.6f}")
        self.lbl_alt.setText(f"{st.alt_m:.1f}")
        self.lbl_ias.setText(f"{st.airspeed_mps:.1f}")
        self.lbl_gs.setText(f"{st.groundspeed_mps:.1f}")
        self.lbl_ax.setText(f"{imu['ax']:.3f}")
        self.lbl_ay.setText(f"{imu['ay']:.3f}")
        self.lbl_az.setText(f"{imu['az']:.3f}")
        self.lbl_wx.setText(f"{imu['wx']:.4f}")
        self.lbl_wy.setText(f"{imu['wy']:.4f}")
        self.lbl_wz.setText(f"{imu['wz']:.4f}")
        self.lbl_pitch.setText(f"{st.attitude_deg[0]:.2f}")
        self.lbl_roll.setText(f"{st.attitude_deg[1]:.2f}")
        self.lbl_yaw.setText(f"{st.attitude_deg[2]:.2f}")
