import sys
import os
import json
import time
import socket
import threading
import numpy as np
import math

# PyQt5
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QGroupBox, QFormLayout, QLabel, QLineEdit, QPushButton, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QSplitter, QComboBox, QSpinBox)
from PyQt5.QtCore import QThread, pyqtSignal, QTimer, Qt

# Matplotlib
import matplotlib
matplotlib.use('Qt5Agg') # Ensure Qt5 backend
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D

# Custom Modules
from das_protocol import DASProtocol

# Reuse logic from DAS.py by importing or re-implementing needed parts
# Since DAS.py has imports that might conflict or assumes running as script, 
# I will re-implement the core logic cleanly here to avoid issues, 
# but referencing the math/logic from DAS.py.

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'das_config.json')

class DASLogic:
    """Separated Logic from UI"""
    def __init__(self, config):
        self.config = config
        self.aircraft_pos = np.array(config['simulation']['aircraft_pos'], dtype=float)
        
        # Targets: list of dict {'id', 'position': np.array, 'velocity': np.array}
        self.targets = []
        for t in config['simulation']['default_targets']:
            self.targets.append({
                'id': t['id'],
                'position': np.array(t['position'], dtype=float),
                'velocity': np.array(t['velocity'], dtype=float)
            })
            
        self.last_update = time.time()
        
    def update(self):
        now = time.time()
        dt = now - self.last_update
        self.last_update = now
        
        # Update Target Positions
        for t in self.targets:
            t['position'] += t['velocity'] * dt * 10 # Speed up for vis
            
    def get_detected_targets(self):
        # Simplified detection: Return relative position (Az, El, Range)
        detected = []
        for t in self.targets:
            rel_pos = t['position'] - self.aircraft_pos
            dist = np.linalg.norm(rel_pos)
            
            # Calculate Az/El
            # Assuming Aircraft pointing +X
            # Azimuth: angle in XY plane
            az = math.degrees(math.atan2(rel_pos[1], rel_pos[0]))
            
            # Elevation: angle from XY plane
            hyp_xy = np.sqrt(rel_pos[0]**2 + rel_pos[1]**2)
            el = math.degrees(math.atan2(rel_pos[2], hyp_xy))
            
            detected.append({
                'id': t['id'],
                'azimuth': az,
                'elevation': el,
                'range': dist,
                'position': t['position'] # For 3D plot
            })
        return detected

class NetworkThread(QThread):
    def __init__(self, config, logic):
        super().__init__()
        self.config = config
        self.logic = logic
        self.running = True
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.sock.bind((config['network']['local_ip'], config['network']['local_port']))
            self.sock.settimeout(0.05)
        except Exception as e:
            print(f"Socket Bind Error: {e}")
            
        self.remote_addr = (config['network']['remote_ip'], config['network']['remote_port'])
        self.seq = 0
        
        # Buffer for received control state
        self.control_state = {
            'ControlCmd': 0, 'SystemMode': 0, 'TaskMode': 0, 
            'SimulationState': 0, 'OverlayEnable': 1, 'RenderMode': 0
        }
        
    def run(self):
        while self.running:
            # 1. Receive Input (Control)
            try:
                data, _ = self.sock.recvfrom(4096)
                parsed = DASProtocol.unpack_input(data)
                if parsed:
                    # Update control state
                    self.control_state.update({
                        'ControlCmd': parsed['cmd'],
                        'SystemMode': parsed['sys_mode'],
                        'TaskMode': parsed['task_mode'],
                        'SimulationState': parsed['sim_state']
                    })
                    # Could also update truth targets if provided by input
            except socket.timeout:
                pass
            except Exception as e:
                print(f"Recv Error: {e}")
                
            # 2. Send Output (Sensor Data)
            try:
                # Get latest simulation data
                targets = self.logic.get_detected_targets()
                
                # Mock Image Data (Small noise)
                w = self.config['sensor']['ImageWidth']
                h = self.config['sensor']['ImageHeight']
                # image_data = np.random.randint(0, 255, (w, h), dtype=np.uint8).tobytes()
                # To save bandwidth/performance, just send empty or very small
                image_data = bytes([128] * (w*h)) 
                
                fov_info = {
                    'center_az': 0, 'center_el': 0,
                    'width': self.config['sensor']['FOVWidth'],
                    'height': self.config['sensor']['FOVHeight']
                }
                
                packet = DASProtocol.pack_output(
                    self.seq, 
                    self.control_state, 
                    self.config['sensor'], 
                    image_data, 
                    targets, 
                    fov_info
                )
                
                self.sock.sendto(packet, self.remote_addr)
                self.seq = (self.seq + 1) % 65535
                
            except Exception as e:
                print(f"Send Error: {e}")
                
            time.sleep(0.05) # 20Hz

    def stop(self):
        self.running = False
        self.wait()
        self.sock.close()

class DASPlot3D(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.ax = fig.add_subplot(111, projection='3d')
        super().__init__(fig)
        self.setParent(parent)
        
        # Initial setup
        self.ax.set_xlim(-150, 150)
        self.ax.set_ylim(-150, 150)
        self.ax.set_zlim(-50, 50)
        self.ax.set_xlabel('X (km)')
        self.ax.set_ylabel('Y (km)')
        self.ax.set_zlabel('Z (km)')
        self.ax.set_title('DAS 3D Situation')
        
        # Plots
        self.aircraft_scat = self.ax.scatter([0], [0], [0], c='blue', s=100, marker='^', label='Aircraft')
        self.target_scat = self.ax.scatter([], [], [], c='red', s=50, marker='o', label='Targets')
        self.ax.legend()

    def update_plot(self, aircraft_pos, targets):
        # Update Aircraft
        self.aircraft_scat._offsets3d = ([aircraft_pos[0]], [aircraft_pos[1]], [aircraft_pos[2]])
        
        # Update Targets
        if targets:
            xs = [t['position'][0] for t in targets]
            ys = [t['position'][1] for t in targets]
            zs = [t['position'][2] for t in targets]
            self.target_scat._offsets3d = (xs, ys, zs)
        else:
            self.target_scat._offsets3d = ([], [], [])
            
        self.draw()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DAS Simulation (PyQt5)")
        self.resize(1200, 800)
        
        # Load Config
        try:
            with open(CONFIG_PATH, 'r') as f:
                self.config = json.load(f)
        except:
            print("Config not found, using defaults")
            self.config = {
                "network": {"local_ip": "127.0.0.1", "local_port": 6001, "remote_ip": "127.0.0.1", "remote_port": 6000},
                "sensor": {"SensorID": 1, "ImageWidth": 64, "ImageHeight": 64, "FOVWidth": 120},
                "simulation": {"aircraft_pos": [0,0,0], "default_targets": []}
            }
            
        # Logic & Network
        self.logic = DASLogic(self.config)
        self.net_thread = NetworkThread(self.config, self.logic)
        self.net_thread.start()
        
        self.init_ui()
        
        # UI Update Timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_loop)
        self.timer.start(50) # 20 FPS

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        
        # Left Panel: Controls & Status
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # 1. System Control
        ctrl_group = QGroupBox("系统控制")
        ctrl_layout = QFormLayout()
        
        self.cb_mode = QComboBox()
        self.cb_mode.addItems(["待机", "搜索", "跟踪", "自检"])
        ctrl_layout.addRow("系统模式:", self.cb_mode)
        
        self.cb_scenario = QComboBox()
        self.cb_scenario.addItems(["空空", "空地", "空海"])
        ctrl_layout.addRow("作战场景:", self.cb_scenario)
        
        self.btn_reset = QPushButton("复位仿真")
        self.btn_reset.clicked.connect(self.reset_sim)
        ctrl_layout.addRow(self.btn_reset)
        
        ctrl_group.setLayout(ctrl_layout)
        left_layout.addWidget(ctrl_group)
        
        # 2. Target Table
        tgt_group = QGroupBox("目标列表")
        tgt_layout = QVBoxLayout()
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "方位(deg)", "俯仰(deg)", "距离(m)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        tgt_layout.addWidget(self.table)
        tgt_group.setLayout(tgt_layout)
        left_layout.addWidget(tgt_group)
        
        # Right Panel: 3D Visualization
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        vis_group = QGroupBox("三维态势显示")
        vis_layout = QVBoxLayout()
        self.plot3d = DASPlot3D(self)
        vis_layout.addWidget(self.plot3d)
        vis_group.setLayout(vis_layout)
        right_layout.addWidget(vis_group)
        
        # Splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(1, 2)
        
        layout.addWidget(splitter)

    def reset_sim(self):
        # Reload logic targets
        self.logic = DASLogic(self.config)
        self.net_thread.logic = self.logic # Swap logic ref

    def update_loop(self):
        # 1. Update Logic
        self.logic.update()
        
        # 2. Get Data
        targets = self.logic.get_detected_targets()
        aircraft_pos = self.logic.aircraft_pos
        
        # 3. Update Table
        self.table.setRowCount(len(targets))
        for i, t in enumerate(targets):
            self.table.setItem(i, 0, QTableWidgetItem(str(t['id'])))
            self.table.setItem(i, 1, QTableWidgetItem(f"{t['azimuth']:.1f}"))
            self.table.setItem(i, 2, QTableWidgetItem(f"{t['elevation']:.1f}"))
            self.table.setItem(i, 3, QTableWidgetItem(f"{t['range']:.1f}"))
            
        # 4. Update 3D Plot
        self.plot3d.update_plot(aircraft_pos, targets)

    def closeEvent(self, event):
        self.net_thread.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
