import sys
import os
import json
import time
import socket
import struct
import threading
import math
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QGroupBox, QFormLayout, QLabel, QLineEdit, QPushButton, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QRadioButton, 
                             QCheckBox, QSpinBox, QDoubleSpinBox, QSplitter)
from PyQt5.QtCore import QThread, pyqtSignal, QTimer, Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import numpy as np

from protocol import Protocol

# Load Config
CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.json')

class NetworkThread(QThread):
    data_received = pyqtSignal(dict)
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.running = True
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Bind to local port to receive
        try:
            self.sock.bind((config['network']['local_ip'], config['network']['local_port']))
            self.sock.settimeout(0.1) # Non-blocking with timeout
        except Exception as e:
            print(f"Error binding socket: {e}")

        self.remote_addr = (config['network']['remote_ip'], config['network']['remote_port'])
        
        # Simulation state
        self.sim_targets = config['targets']
        self.sensor_config = config['sensor']
        self.last_time = time.time()
        
        # Shared data buffer for UI
        self.latest_data = None
        self.lock = threading.Lock()

    def run(self):
        while self.running:
            # 1. Update Simulation (Simple Movement)
            current_time = time.time()
            dt = current_time - self.last_time
            self.last_time = current_time
            
            # Move targets slightly to simulate "Output Parameters" changing according to a pattern
            for t in self.sim_targets:
                # Simple circular motion logic or linear
                # Let's just rotate azimuth
                t['azimuth'] += (t.get('velocity', 0) / 1000.0) * dt # arbitrary scaling
                if t['azimuth'] > 180: t['azimuth'] -= 360
                if t['azimuth'] < -180: t['azimuth'] += 360
                
                # Update distance slightly
                t['distance'] += (t.get('velocity', 0) * dt)
                if t['distance'] < 0: t['distance'] = 10000
                if t['distance'] > 20000: t['distance'] = 1000

            # 2. Send Output Parameters
            try:
                packet = Protocol.pack_output(self.sensor_config, self.sim_targets)
                self.sock.sendto(packet, self.remote_addr)
            except Exception as e:
                print(f"Send Error: {e}")

            # 3. Receive Input Parameters
            try:
                data, addr = self.sock.recvfrom(4096)
                parsed = Protocol.unpack_input(data)
                if parsed:
                    # Thread-safe update
                    with self.lock:
                        self.latest_data = parsed
                    # Removed emit signal to avoid flooding main thread
            except socket.timeout:
                pass
            except Exception as e:
                print(f"Receive Error: {e}")
            
            # Sleep to match refresh rate roughly
            time.sleep(1.0 / self.sensor_config.get('RefreshRate_Hz', 20))

    def stop(self):
        self.running = False
        self.wait()
        self.sock.close()

    def update_sensor_config(self, key, value):
        self.sensor_config[key] = value

class RadarPlot(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111, projection='polar')
        self.axes.set_theta_zero_location('N')
        self.axes.set_theta_direction(-1) # Clockwise
        self.axes.set_ylim(0, 20000) # Max range
        self.axes.set_facecolor('#1e1e1e')
        fig.patch.set_facecolor('#1e1e1e')
        
        # Initial scatter
        self.scat = self.axes.scatter([], [], c='lime', s=50, animated=True)
        self.texts = [] # Store text objects
        
        # Grid settings
        self.axes.grid(True, color='green', alpha=0.5)
        self.axes.tick_params(axis='x', colors='white')
        self.axes.tick_params(axis='y', colors='white')
        
        super(RadarPlot, self).__init__(fig)
        self.bg = None

    def update_plot(self, targets):
        if not targets:
            # Clear data
            offsets = np.empty((0, 2))
            self.scat.set_offsets(offsets)
            for txt in self.texts: txt.set_visible(False)
            self.draw()
            return

        # Update Scatter
        azimuths = [math.radians(t['azimuth']) for t in targets]
        distances = [t['distance'] for t in targets]
        
        # set_offsets expects (x, y) but for polar scatter in matplotlib, 
        # it actually works with (theta, r) if we transform it, OR 
        # we can just re-plot if optimization is hard. 
        # Actually, simpler optimization: don't call clear().
        
        # Matplotlib scatter set_offsets on polar plot is tricky because it expects projected coordinates.
        # Simplest stable optimization:
        # Remove old collection, add new one. (Faster than clear() which rebuilds grid)
        
        try:
            self.scat.remove()
        except:
            pass
            
        self.scat = self.axes.scatter(azimuths, distances, c='lime', s=50)
        
        # Update labels
        # Ensure enough text objects
        while len(self.texts) < len(targets):
            txt = self.axes.text(0, 0, "", color='white', fontsize=10)
            self.texts.append(txt)
            
        # Update texts
        for i, t in enumerate(targets):
            az = math.radians(t['azimuth'])
            r = t['distance']
            self.texts[i].set_position((az, r))
            self.texts[i].set_text(str(t['id']))
            self.texts[i].set_visible(True)
            
        # Hide unused texts
        for i in range(len(targets), len(self.texts)):
            self.texts[i].set_visible(False)
            
        self.draw()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IRST Simulator")
        self.resize(1200, 800)
        
        # Load Config
        try:
            with open(CONFIG_PATH, 'r') as f:
                self.config = json.load(f)
        except:
            self.config = {
                "network": {"local_ip": "127.0.0.1", "local_port": 5001, "remote_ip": "127.0.0.1", "remote_port": 5000},
                "sensor": {"DetectRange_m": 20000},
                "targets": []
            }

        self.init_ui()
        
        # Network Thread
        self.net_thread = NetworkThread(self.config)
        # self.net_thread.data_received.connect(self.update_display) # Decoupled
        self.net_thread.start()
        
        # UI Update Timer (Throttle to 20 FPS)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_display)
        self.timer.start(50) # 50ms = 20 FPS

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        
        # Left Panel (Controls + Table)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # 1. Work Mode Settings
        mode_group = QGroupBox("工作模式设置区")
        mode_layout = QFormLayout()
        
        self.detect_range_input = QDoubleSpinBox()
        self.detect_range_input.setRange(0, 200000)
        self.detect_range_input.setValue(self.config['sensor'].get('DetectRange_m', 20000))
        self.detect_range_input.valueChanged.connect(lambda v: self.update_config('DetectRange_m', v))
        mode_layout.addRow("探测距离 (m):", self.detect_range_input)
        
        self.refresh_rate_input = QDoubleSpinBox()
        self.refresh_rate_input.setRange(1, 200)
        self.refresh_rate_input.setValue(self.config['sensor'].get('RefreshRate_Hz', 20))
        self.refresh_rate_input.valueChanged.connect(lambda v: self.update_config('RefreshRate_Hz', v))
        mode_layout.addRow("刷新频率 (Hz):", self.refresh_rate_input)
        
        mode_group.setLayout(mode_layout)
        left_layout.addWidget(mode_group)
        
        # 2. Optical Axis Control
        axis_group = QGroupBox("光轴控制设置区")
        axis_layout = QFormLayout()
        
        self.fov_center_input = QDoubleSpinBox()
        self.fov_center_input.setRange(-180, 180)
        self.fov_center_input.setValue(self.config['sensor'].get('FOVCenterAzimuth_deg', 0))
        self.fov_center_input.valueChanged.connect(lambda v: self.update_config('FOVCenterAzimuth_deg', v))
        axis_layout.addRow("视场中心 (deg):", self.fov_center_input)
        
        axis_group.setLayout(axis_layout)
        left_layout.addWidget(axis_group)
        
        # 3. Data Display (Table)
        data_group = QGroupBox("目标信息数据显示区")
        data_layout = QVBoxLayout()
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "距离(m)", "方位(deg)", "俯仰(deg)", "速度(m/s)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        data_layout.addWidget(self.table)
        data_group.setLayout(data_layout)
        left_layout.addWidget(data_group)
        
        # Right Panel (Radar)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        radar_group = QGroupBox("目标信息二维态势显示区")
        radar_layout = QVBoxLayout()
        self.radar = RadarPlot(self)
        radar_layout.addWidget(self.radar)
        radar_group.setLayout(radar_layout)
        
        right_layout.addWidget(radar_group)
        
        # Add to main splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(1, 2) # Right side larger
        
        layout.addWidget(splitter)

    def update_config(self, key, value):
        if hasattr(self, 'net_thread'):
            self.net_thread.update_sensor_config(key, value)

    def update_display(self):
        # Poll latest data from Network Thread
        if not hasattr(self, 'net_thread'): return
        
        data = None
        with self.net_thread.lock:
            if self.net_thread.latest_data:
                data = self.net_thread.latest_data
                # Optional: clear it if we only want to process unique frames, 
                # but for UI state display, just showing latest is fine.
        
        if not data: return
        
        # Update Table
        targets = data.get('targets', [])
        
        # Optimization: Reuse table items
        # If row count matches, just update text
        if self.table.rowCount() != len(targets):
            self.table.setRowCount(len(targets))
            for i in range(len(targets)):
                for j in range(5):
                    self.table.setItem(i, j, QTableWidgetItem(""))

        for i, t in enumerate(targets):
            # Column 0: ID
            item = self.table.item(i, 0)
            if item: item.setText(str(t['id']))
            
            # Column 1: Dist
            item = self.table.item(i, 1)
            if item: item.setText(f"{t['distance']:.1f}")
            
            # Column 2: Az
            item = self.table.item(i, 2)
            if item: item.setText(f"{t['azimuth']:.2f}")
            
            # Column 3: El
            item = self.table.item(i, 3)
            if item: item.setText(f"{t['elevation']:.2f}")
            
            # Column 4: Vel
            item = self.table.item(i, 4)
            if item: item.setText(f"{t['velocity']:.1f}")
            
        # Update Radar
        self.radar.update_plot(targets)

    def closeEvent(self, event):
        if hasattr(self, 'net_thread'):
            self.net_thread.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
