"""系统配置面板。"""

from __future__ import annotations

from PyQt5 import QtWidgets
from pathlib import Path
import yaml
from sim_core.models import WeaponSystem
from protocols.icd import load_icd


class ConfigPanel(QtWidgets.QWidget):
    """初始化参数配置与场景保存/加载。"""

    def __init__(self, sys: WeaponSystem) -> None:
        super().__init__()
        self._sys = sys
        self._mass = QtWidgets.QDoubleSpinBox()
        self._mass.setRange(1.0, 2000.0)
        self._mass.setValue(self._sys.weapon.mass_kg)
        self._fuze_sens = QtWidgets.QDoubleSpinBox()
        self._fuze_sens.setRange(0.0, 1.0)
        self._fuze_sens.setSingleStep(0.05)
        self._fuze_sens.setValue(self._sys.weapon.fuze.sensitivity)
        self._rack_load = QtWidgets.QDoubleSpinBox()
        self._rack_load.setRange(10.0, 2000.0)
        self._rack_load.setValue(self._sys.rack.max_load_kg)
        self._ej_press = QtWidgets.QDoubleSpinBox()
        self._ej_press.setRange(0.0, 50.0)
        self._ej_press.setValue(self._sys.ejector.pressure_mpa)
        self._aero_mode = QtWidgets.QComboBox()
        self._aero_mode.addItems(["external", "internal"])
        self._aero_mode.setCurrentText(self._sys.weapon.aerodynamic_mode)
        self._icd_path = QtWidgets.QLineEdit()
        self._icd_path.setText(str(Path(__file__).resolve().parents[2] / "configs" / "icd_example.json"))
        self._icd_view = QtWidgets.QTextEdit()
        self._icd_view.setReadOnly(True)
        btn_save = QtWidgets.QPushButton("保存场景")
        btn_load = QtWidgets.QPushButton("加载场景")
        btn_icd = QtWidgets.QPushButton("加载ICD")
        btn_save.clicked.connect(self._on_save)
        btn_load.clicked.connect(self._on_load)
        btn_icd.clicked.connect(self._on_icd)
        layout = QtWidgets.QFormLayout(self)
        layout.addRow("武器质量(kg)", self._mass)
        layout.addRow("引信灵敏度", self._fuze_sens)
        layout.addRow("挂架最大载荷(kg)", self._rack_load)
        layout.addRow("弹射器压力(MPa)", self._ej_press)
        layout.addRow("气动模式", self._aero_mode)
        layout.addRow(btn_save, btn_load)
        layout.addRow("ICD 路径", self._icd_path)
        layout.addRow(btn_icd, self._icd_view)

    def _on_save(self) -> None:
        """保存当前配置到 YAML。"""

        p = Path(__file__).resolve().parents[2] / "configs" / "weapon_scene.yaml"
        p.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "weapon_id": self._sys.weapon.weapon_id,
            "mass_kg": float(self._mass.value()),
            "fuze_sensitivity": float(self._fuze_sens.value()),
            "rack_max_load_kg": float(self._rack_load.value()),
            "ejector_pressure_mpa": float(self._ej_press.value()),
            "aerodynamic_mode": self._aero_mode.currentText(),
        }
        p.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")

    def _on_load(self) -> None:
        """从 YAML 加载配置。"""

        p = Path(__file__).resolve().parents[2] / "configs" / "weapon_scene.yaml"
        try:
            data = yaml.safe_load(p.read_text(encoding="utf-8"))
            self._sys.weapon.mass_kg = float(data.get("mass_kg", self._sys.weapon.mass_kg))
            self._sys.weapon.fuze.sensitivity = float(data.get("fuze_sensitivity", self._sys.weapon.fuze.sensitivity))
            self._sys.rack.max_load_kg = float(data.get("rack_max_load_kg", self._sys.rack.max_load_kg))
            self._sys.ejector.pressure_mpa = float(data.get("ejector_pressure_mpa", self._sys.ejector.pressure_mpa))
            self._sys.weapon.aerodynamic_mode = str(data.get("aerodynamic_mode", self._sys.weapon.aerodynamic_mode))
            self._mass.setValue(self._sys.weapon.mass_kg)
            self._fuze_sens.setValue(self._sys.weapon.fuze.sensitivity)
            self._rack_load.setValue(self._sys.rack.max_load_kg)
            self._ej_press.setValue(self._sys.ejector.pressure_mpa)
            self._aero_mode.setCurrentText(self._sys.weapon.aerodynamic_mode)
        except Exception:
            pass

    def _on_icd(self) -> None:
        """加载并展示 ICD 文件。"""

        p = Path(self._icd_path.text())
        data = load_icd(p)
        self._icd_view.setPlainText(yaml.safe_dump(data, allow_unicode=True))
