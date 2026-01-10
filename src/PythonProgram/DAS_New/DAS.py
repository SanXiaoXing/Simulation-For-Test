#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：631_ZHCLTest 
@File    ：DAS.py
@Author  ：SanXiaoXing
@Date    ：2025/7/4
@Description: 
"""
import numpy as np
# 设置matplotlib后端避免Qt问题
import matplotlib
matplotlib.use('TkAgg')  # 使用TkAgg后端避免Qt平台插件问题
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.patches import Circle
import matplotlib.animation as animation
from matplotlib.image import imread
from matplotlib.colors import LightSource
from typing import List, Dict, Tuple, Optional
from PIL import Image
import os

# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题


class Sensor:
    """传感器类，表示飞机上的单个分布式孔径传感器"""

    def __init__(self, position: Tuple[float, float, float],
                 field_of_view: float = 120.0,
                 detection_range: float = 100.0,
                 sensor_type: str = "infrared"):
        """
        初始化传感器参数

        参数:
            position: 传感器在飞机坐标系中的位置(x, y, z)
            field_of_view: 传感器视场角(度)
            detection_range: 传感器探测范围
            sensor_type: 传感器类型(如"infrared", "radar", "optical")
        """
        self.position = np.array(position)
        self.field_of_view = np.radians(field_of_view)  # 转换为弧度
        self.detection_range = detection_range
        self.sensor_type = sensor_type
        self.detected_targets = []  # 当前检测到的目标列表

    def can_detect(self, target_position: np.ndarray) -> bool:
        """
        判断传感器是否能检测到目标

        参数:
            target_position: 目标在飞机坐标系中的位置

        返回:
            bool: 能否检测到目标
        """
        # 计算目标与传感器的距离
        distance = np.linalg.norm(target_position - self.position)

        # 检查目标是否在探测范围内
        if distance > self.detection_range:
            return False

        # 计算目标相对于传感器的方向向量
        direction = target_position - self.position
        direction = direction / np.linalg.norm(direction)

        # 计算传感器的朝向(简化为指向飞机前方，实际应用中需要根据安装位置确定)
        sensor_orientation = np.array([1.0, 0.0, 0.0])  # 默认朝前

        # 计算目标方向与传感器朝向的夹角
        angle = np.arccos(np.dot(direction, sensor_orientation))

        # 检查目标是否在视场内
        return angle <= self.field_of_view / 2

    def detect(self, targets: List[np.ndarray]) -> List[Dict]:
        """
        检测所有目标并返回检测结果

        参数:
            targets: 目标位置列表

        返回:
            List[Dict]: 检测结果列表，包含目标位置和距离
        """
        self.detected_targets = []
        for target in targets:
            if self.can_detect(target):
                distance = np.linalg.norm(target - self.position)
                self.detected_targets.append({
                    "position": target,
                    "distance": distance,
                    "timestamp": np.random.randint(1000)  # 模拟时间戳
                })
        return self.detected_targets


class Aircraft:
    """飞机类，表示搭载分布式孔径系统的飞行器"""

    def __init__(self, position: Tuple[float, float, float] = (0, 0, 0),
                 orientation: Tuple[float, float, float] = (0, 0, 0)):
        """
        初始化飞机参数

        参数:
            position: 飞机在全局坐标系中的位置(x, y, z)
            orientation: 飞机的朝向(俯仰角, 偏航角, 滚转角)
        """
        self.position = np.array(position)
        self.orientation = np.array(orientation)
        self.sensors = []  # 飞机上的传感器列表
        self.detection_data = []  # 所有传感器的检测数据

        # 初始化默认的分布式传感器配置(基于F-35的AN/AAQ-37系统)
        self._initialize_default_sensors()

    def _initialize_default_sensors(self):
        """初始化默认的传感器配置"""
        # 传感器位置基于飞机机身分布(简化模型)
        sensor_positions = [
            (5, 0, 2),  # 机头上方
            (5, 0, -2),  # 机头下方
            (-3, 3, 0),  # 左机翼
            (-3, -3, 0),  # 右机翼
            (-5, 0, 1),  # 机尾上方
            (-5, 0, -1)  # 机尾下方
        ]

        for pos in sensor_positions:
            self.add_sensor(Sensor(pos))

    def add_sensor(self, sensor: Sensor):
        """添加传感器到飞机"""
        self.sensors.append(sensor)

    def update_position(self, new_position: np.ndarray):
        """更新飞机位置"""
        self.position = new_position

    def update_orientation(self, new_orientation: np.ndarray):
        """更新飞机朝向"""
        self.orientation = new_orientation

    def detect_targets(self, targets: List[np.ndarray]) -> List[Dict]:
        """
        使用所有传感器检测目标并融合结果

        参数:
            targets: 目标位置列表

        返回:
            List[Dict]: 融合后的检测结果
        """
        self.detection_data = []

        # 对每个传感器进行检测
        for sensor in self.sensors:
            sensor_data = sensor.detect(targets)
            for data in sensor_data:
                # 添加传感器ID信息
                data["sensor_id"] = self.sensors.index(sensor)
                data["sensor_type"] = sensor.sensor_type
                self.detection_data.append(data)

        # 简化的数据融合(实际应用中需要更复杂的算法)
        fused_data = self._fuse_detection_data()
        return fused_data

    def _fuse_detection_data(self) -> List[Dict]:
        """融合来自不同传感器的数据(简化版)"""
        # 在实际系统中，这里会实现复杂的数据关联和融合算法
        # 例如卡尔曼滤波、贝叶斯融合等
        return self.detection_data


class DASSimulation:
    """分布式孔径系统仿真类"""

    def __init__(self):
        """初始化仿真环境"""
        self.aircraft = Aircraft()
        self.targets = []  # 仿真中的目标列表
        self.frames = []  # 仿真帧数据

    def add_target(self, position: np.ndarray, velocity: np.ndarray = None):
        """
        添加目标到仿真环境

        参数:
            position: 目标初始位置
            velocity: 目标速度向量(默认静止)
        """
        if velocity is None:
            velocity = np.array([0, 0, 0])

        self.targets.append({
            "position": position,
            "velocity": velocity
        })

    def update_targets(self, dt: float = 1.0):
        """
        更新所有目标的位置

        参数:
            dt: 时间步长
        """
        for target in self.targets:
            target["position"] += (target["velocity"] * dt).astype(np.int32)

    def run_simulation(self, num_frames: int = 100, dt: float = 0.1):
        """
        运行仿真

        参数:
            num_frames: 仿真帧数
            dt: 每帧时间间隔
        """
        self.frames = []

        for _ in range(num_frames):
            # 更新目标位置
            self.update_targets(dt)

            # 获取当前目标位置列表
            target_positions = [t["position"] for t in self.targets]

            # 飞机检测目标
            detections = self.aircraft.detect_targets(target_positions)

            # 记录当前帧数据
            self.frames.append({
                "aircraft_position": self.aircraft.position,
                "targets": self.targets.copy(),
                "detections": detections
            })

    def visualize(self, background_style='cube_texture'):
        """可视化仿真结果
        
        参数:
            background_style: 背景样式 ('cube_texture')
        """
        fig = plt.figure(figsize=(12, 10))
        ax = fig.add_subplot(111, projection='3d')
        
        # 设置坐标轴范围（必须在贴图之前设置）
        ax.set_xlim(-150, 150)
        ax.set_ylim(-150, 150)
        ax.set_zlim(-50, 50)
        
        # 设置立方体六面贴图背景（先绘制背景，使用zorder=-1确保在底层）
        self._set_cube_texture_background(ax)
        
        # 初始化图形元素（zorder>0确保在背景之上）
        aircraft_plot = ax.scatter([], [], [], c='blue', s=150, marker='^', 
                                  label='Aircraft', depthshade=False, edgecolors='black', 
                                  linewidth=1, zorder=10)
        target_plots = ax.scatter([], [], [], c='red', s=80, marker='o', 
                                 label='Targets', depthshade=False, edgecolors='black', 
                                 linewidth=1, zorder=10)
        detection_plots = ax.scatter([], [], [], c='green', s=60, marker='*', 
                                    label='Detections', depthshade=False, edgecolors='black', 
                                    linewidth=1, zorder=10)

        # 传感器视场可视化 - 移除Circle对象，改用3D兼容的可视化方式
        # 注释掉Circle相关代码，因为Circle不支持3D投影
        # fov_patches = []
        # for sensor in self.aircraft.sensors:
        #     # 创建视场锥体(简化为圆形)
        #     circle = Circle((0, 0), sensor.detection_range, alpha=0.1, color='blue')
        #     ax.add_patch(circle)
        #     fov_patches.append(circle)

        ax.set_xlabel('X (km)')
        ax.set_ylabel('Y (km)')
        ax.set_zlabel('Z (km)')
        ax.set_title('Distributed Aperture System (DAS) Simulation')
        ax.legend()

        def update(frame_idx):
            frame = self.frames[frame_idx]

            # 更新飞机位置
            aircraft_pos = frame["aircraft_position"]
            aircraft_plot._offsets3d = ([aircraft_pos[0]], [aircraft_pos[1]], [aircraft_pos[2]])

            # 更新目标位置
            target_positions = [t["position"] for t in frame["targets"]]
            if target_positions:
                x, y, z = zip(*target_positions)
                target_plots._offsets3d = (x, y, z)

            # 更新检测位置
            detection_positions = [d["position"] for d in frame["detections"]]
            if detection_positions:
                x, y, z = zip(*detection_positions)
                detection_plots._offsets3d = (x, y, z)

            # 更新传感器视场位置
            for i, sensor in enumerate(self.aircraft.sensors):
                # 简化的视场可视化更新
                pass

            return aircraft_plot, target_plots, detection_plots

        # 创建动画
        ani = animation.FuncAnimation(fig, update, frames=len(self.frames),
                                      interval=100, blit=True)

        plt.show()
        # fig, ax = plt.subplots()  # 使用 2D 坐标轴代替 3D axes
    
    def _apply_texture(self, img_data, grid_size=50):
        """将图片数据适配到网格平面
        
        参数:
            img_data: 图片数据数组
            grid_size: 贴图分辨率
            
        返回:
            归一化的RGB值数组
        """
        try:
            # 确保图片数据是正确的格式
            if isinstance(img_data, np.ndarray):
                # 如果是浮点数据，转换为0-255范围的整数
                if img_data.dtype == np.float32 or img_data.dtype == np.float64:
                    if img_data.max() <= 1.0:
                        img_data = (img_data * 255).astype(np.uint8)
                    else:
                        img_data = img_data.astype(np.uint8)
                
                # 确保是uint8类型
                if img_data.dtype != np.uint8:
                    img_data = img_data.astype(np.uint8)
                
                # 处理不同的图片格式
                if len(img_data.shape) == 3:  # RGB或RGBA图片
                    if img_data.shape[2] == 4:  # RGBA，去掉alpha通道
                        img_data = img_data[:, :, :3]
                    # 使用PIL调整图片尺寸
                    pil_img = Image.fromarray(img_data, mode='RGB')
                    resized_img = np.array(pil_img.resize((grid_size, grid_size)))
                elif len(img_data.shape) == 2:  # 灰度图片
                    pil_img = Image.fromarray(img_data, mode='L')
                    resized_img = np.array(pil_img.resize((grid_size, grid_size)))
                    # 转换为RGB格式
                    resized_img = np.stack([resized_img] * 3, axis=-1)
                else:
                    raise ValueError(f"不支持的图片维度: {img_data.shape}")
                
                return resized_img / 255.0  # 归一化RGB值
            else:
                raise ValueError(f"不支持的数据类型: {type(img_data)}")
                
        except Exception as e:
            print(f"图片处理错误: {e}")
            # 返回默认纹理（灰色）
            return np.ones((grid_size, grid_size, 3)) * 0.5
    
    def _set_cube_texture_background(self, ax):
        """设置立方体六面贴图背景
        
        参数:
            ax: matplotlib 3D轴对象
        """
        # 定义六个面图片路径
        faces_dir = 'D:\\631_12代\\631_ZHCLTest\\dice_output\\faces'
        face_files = {
            'pos_x': os.path.join(faces_dir, 'face_right.png'),    # +X面
            'neg_x': os.path.join(faces_dir, 'face_left.png'),     # -X面
            'pos_y': os.path.join(faces_dir, 'face_front.png'),    # +Y面
            'neg_y': os.path.join(faces_dir, 'face_back.png'),     # -Y面
            'pos_z': os.path.join(faces_dir, 'face_top.png'),      # +Z面
            'neg_z': os.path.join(faces_dir, 'face_bottom.png')    # -Z面
        }
        
        # 获取当前坐标轴范围
        x_min, x_max = ax.get_xlim()
        y_min, y_max = ax.get_ylim()
        z_min, z_max = ax.get_zlim()
        
        # 创建网格基础
        grid_size = 50  # 贴图分辨率
        x = np.linspace(x_min, x_max, grid_size)
        y = np.linspace(y_min, y_max, grid_size)
        z = np.linspace(z_min, z_max, grid_size)
        
        # 加载六张图片
        img_dict = {}
        for key, file_path in face_files.items():
            if os.path.exists(file_path):
                try:
                    img_dict[key] = imread(file_path)
                    print(f"成功加载图片: {file_path}")
                except Exception as e:
                    print(f"加载图片失败 {file_path}: {e}")
                    # 使用默认纹理
                    img_dict[key] = np.ones((100, 100, 3)) * 0.5
            else:
                print(f"图片文件不存在: {file_path}")
                # 使用默认纹理
                img_dict[key] = np.ones((100, 100, 3)) * 0.5
        
        try:
            # 创建六个平面（注意法线方向和zorder）
            
            # +X平面（右面）- 完整图片显示，无切割效果
            if 'pos_x' in img_dict:
                Y, Z = np.meshgrid(y, z)
                X = np.full_like(Y, x_max)
                texture = self._apply_texture(img_dict['pos_x'], grid_size)
                ax.plot_surface(X, Y, Z, facecolors=texture, 
                               shade=False, alpha=0.5, zorder=-1)
            
            # -X平面（左面，需镜像翻转）- 完整图片显示，无切割效果
            if 'neg_x' in img_dict:
                Y, Z = np.meshgrid(y, z)
                X = np.full_like(Y, x_min)
                texture = self._apply_texture(np.fliplr(img_dict['neg_x']), grid_size)
                ax.plot_surface(X, Y, Z, facecolors=texture, 
                               shade=False, alpha=0.5, zorder=-1)
            
            # +Y平面（天花板）- 完整图片显示，无切割效果
            if 'pos_y' in img_dict:
                X, Z = np.meshgrid(x, z)
                Y = np.full_like(X, y_max)
                texture = self._apply_texture(img_dict['pos_y'], grid_size)
                ax.plot_surface(X, Y, Z, facecolors=texture, 
                               shade=False, alpha=0.5, zorder=-1)
            
            # -Y平面（地板）- 完整图片显示，无切割效果
            if 'neg_y' in img_dict:
                X, Z = np.meshgrid(x, z)
                Y = np.full_like(X, y_min)
                texture = self._apply_texture(img_dict['neg_y'], grid_size)
                ax.plot_surface(X, Y, Z, facecolors=texture, 
                               shade=False, alpha=0.5, zorder=-1)
            
            # +Z平面（后墙）- 完整图片显示，无切割效果
            if 'pos_z' in img_dict:
                X, Y = np.meshgrid(x, y)
                Z = np.full_like(X, z_max)
                texture = self._apply_texture(img_dict['pos_z'], grid_size)
                ax.plot_surface(X, Y, Z, facecolors=texture, 
                               shade=False, alpha=0.5, zorder=-1)
            
            # -Z平面（前墙，需镜像）- 完整图片显示，无切割效果
            if 'neg_z' in img_dict:
                X, Y = np.meshgrid(x, y)
                Z = np.full_like(X, z_min)
                texture = self._apply_texture(np.fliplr(img_dict['neg_z']), grid_size)
                ax.plot_surface(X, Y, Z, facecolors=texture, 
                               shade=False, alpha=0.5, zorder=-1)
                
            print("立方体六面贴图背景已应用")
            
        except Exception as e:
            print(f"创建立方体贴图时出错: {e}")
            # 如果加载失败，使用默认背景
            pass


# 主函数：运行仿真示例
def main(background='cube_texture'):
    """运行分布式孔径系统仿真示例
    
    参数:
        background: 背景样式 ('cube_texture')
    """
    # 创建仿真环境
    sim = DASSimulation()

    # 添加飞机
    aircraft = Aircraft(position=(0, 0, 0))
    sim.aircraft = aircraft

    # 添加目标
    sim.add_target(np.array([50, 20, 10]), np.array([-0.5, 0, 0]))  # 移动目标
    sim.add_target(np.array([80, -30, 5]), np.array([-0.8, 0.2, 0]))  # 移动目标
    sim.add_target(np.array([100, 0, 20]))  # 静止目标

    # 运行仿真
    sim.run_simulation(num_frames=100, dt=1.0)

    # 可视化结果
    sim.visualize(background_style=background)


def demo_backgrounds():
    """演示立方体六面贴图背景"""
    print("立方体六面贴图背景系统")
    print("使用dice_output/faces/目录中的六个面图片")
    print("\n面映射关系:")
    print("- face_right.png  -> +X面 (右面)")
    print("- face_left.png   -> -X面 (左面)")
    print("- face_front.png  -> +Y面 (前面)")
    print("- face_back.png   -> -Y面 (后面)")
    print("- face_top.png    -> +Z面 (顶面)")
    print("- face_bottom.png -> -Z面 (底面)")
    print("\n使用示例:")
    print("main()  # 立方体六面贴图背景")


if __name__ == "__main__":
    # 演示立方体六面贴图背景
    demo_backgrounds()
    
    # 运行立方体六面贴图背景的仿真
    main()