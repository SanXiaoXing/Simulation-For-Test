# Prompt（用于生成/编写 Python + PyQt5 的“分布式孔径接口特征仿真器/模拟器”源码）

> 目标：用 Python（3.8.10+）和 PyQt5 实现一个可运行的分布式孔径接口特征仿真软件（桌面应用），用于飞机分布式孔径子系统的接口特征仿真、雷达/光电系统验证、图像拼接与目标识别、JPEG2000 多路视频压缩传输仿真、以及电子战（EW）干扰/虚假目标生成。代码应生产级可读、模块化、含单元测试与示例数据，便于雷达系统验证与集成测试。

---

## 1）总体要求（必须）

* 语言与环境：Python 3.8.10+；UI 使用 PyQt5；可选使用 numpy、scipy、opencv-python、pillow、imagecodecs（或 glymur / openjpeg 绑定）用于 JPEG2000；使用 asyncio 或 multiprocessing 对视频流与网络进行并发处理。
* 代码风格：PEP8，详尽类型注解（type hints），模块化，单元测试（pytest），README、安装与运行说明。
* 架构要点：清晰分层（核心仿真引擎、数据接口层、视频/图像处理层、EW 仿真层、UI 层、日志与监控层）。支持配置文件（YAML/JSON）。
* 可扩展性：模块化插件式目标模型、干扰模型、融合算法接口。
* 网络接口：支持 UDP（低延迟传输）、TCP（可靠控制）、以及本地回环用于测试。定义并实现 JSON-over-UDP/TCP 的报文/二进制协议，并提供示例发送器/接收器。
* 性能与资源：支持多路视频流仿真（示例：4路 720p 或 2路 1080p 模拟），可配置帧率与压缩比；提供多进程/线程选项以利用多核。

---

## 2）功能需求（具体）

### 核心仿真

* 多目标生成器：定义目标轨迹（空、地、海）、RCS/IR 签名、速度、航向、高度等；支持静态与动态目标群组（成群移动、编队）。
* 多孔径仿真节点：模拟多个有源/被动相控阵或光电孔径，按地理位置/朝向/视角生成观测数据（位置误差、测量噪声、遮挡、置信度）。
* 跟踪器：实现至少一种多目标跟踪（MHT/JPDA 或卡尔曼 + 数据关联），并支持动态调整跟踪参数（阈值、门限、滤波器噪声）。
* 数据融合：实现时序融合（来自多孔径的时延/角度/距离融合），并可展示融合前后精度差异。
* 图像拼接与目标识别：对多路视频/图像流做几何拼接（简单的平面拼接/特征配准），并使用 OpenCV + 预置轻量目标检测（如基于 Haar 或简单 DNN 的示例）进行目标识别与标注。

### 光电/红外仿真

* 模拟昼夜与恶劣气象（雾、云、雨）对图像的影响：添加可配置的模糊、对比度降级、噪声、散射模型（简化），并在 UI 上可控。
* JPEG2000 压缩仿真：实现视频帧编码/解码流程（可用 imagecodecs / glymur 或用模拟函数近似压缩影响），并模拟不同码率下的帧失真与传输带宽占用。

### 电子战（EW）仿真

* 虚假目标注入：在传感器/跟踪器接收层注入伪目标数据（时空位置与强度），支持规则/概率触发与移动伪目标。
* 干扰信号仿真：对探测链路施加抑制（降低 SNR、增加测量噪声、丢帧、延迟），并可动态调整干扰参数以测试抗欺骗能力。
* 可视化干扰效果指标：命中率、误报率、跟踪丢失率、定位误差统计。

### 接口与集成

* 输出：实时跟踪列表（JSON），融合数据（CSV/JSON 记录），视频拼接流（本地窗口预览 + 可选 RTSP/UDP 输出），日志。
* 控制 API：本地 REST 或 TCP 命令接口（例如启动/停止场景、注入伪目标、调整噪声参数）。
* 配置文件：场景定义（targets, sensors, EW policies, compression settings）。

---

## 3）UI 设计（PyQt5）

主窗口布局（左列控件、中心场景可视化、右列数据面板）：

* 顶部菜单：文件（打开场景/保存场景）、运行（Start/Pause/Step/Stop）、工具（导出日志、实例生成器）。
* 中央：交互式地图/航迹视图（支持缩放/平移），显示传感器位置、目标轨迹、跟踪框与置信度。
* 下方：多路视频面板（支持选择某一路全屏），拼接结果预览，帧率与带宽显示，JPEG2000 码率滑块。
* 右侧面板：跟踪列表（ID、位置、速度、置信度）、统计面板（误报率、漏报率、定位误差），干扰控制（开/关，强度滑条），日志窗口。
* 场景控制面板：加载场景、调整时间步长、注入手动目标、保存快照。

UX 要求：响应式、可停靠面板、可拖拽调整，重要操作有确认与提示。

---

## 4）数据/协议规范（示例）

### 4.1 UDP 观测报文（JSON-over-UDP）

```json
{
  "msg_type": "observation",        // observation / image / control
  "sensor_id": "SENSOR_01",
  "timestamp_utc": "2025-11-27T06:00:00.123Z",
  "obs": [
    { "target_id": "TGT_42", "range_m": 12345.6, "az_deg": 45.2, "el_deg": 1.5, "snr_db": 12.3, "rfi_flag": false }
  ]
}
```

### 4.2 跟踪/融合输出（JSON）

```json
{
  "msg_type": "track",
  "track_id": "TRK_1001",
  "timestamp_utc": "...",
  "state": { "x_m": ..., "y_m": ..., "z_m": ..., "vx_mps": ..., "vy_mps": ... },
  "covariance": [[...]],
  "sources": ["SENSOR_01","SENSOR_02"],
  "confidence": 0.87
}
```

### 4.3 视频帧传输（二进制或 base64 JPEG2000 payload）

* 包含 header（sensor_id, frame_number, timestamp, compressed_bytes_length）后接压缩帧数据。示例也可用 JSON meta + base64 数据（便于演示，但效率低）。

---

## 5）实现细节与技术选型建议

* 并发：视频/网络 -> 使用 asyncio + aiofiles 或 multiprocessing.Process + Queue（视频编码/解码可能受 GIL 影响，建议使用子进程）。
* 图像处理：OpenCV（cv2）用于拼接、增强与目标检测；Pillow 处理帧格式转换。
* JPEG2000：首选 imagecodecs（pip 安装）或 glymur（需 OpenJPEG）；若不可用，提供“近似压缩”函数（高斯模糊 + 量化）作为回退。
* 跟踪与数据关联：numpy + scipy；实现扩展卡尔曼滤波器/匀速卡尔曼与简单最近邻/匹门（gate）数据关联；为复杂场景保留接口以替换为 MHT/JPDA。
* 日志：使用 python logging（支持 file + rotating + UI 实时输出）。
* 配置：使用 pydantic 或 dataclasses 解析 YAML/JSON 场景文件。
* 单元测试：pytest 覆盖关键模块（目标生成器、跟踪器、数据融合、EW 注入、协议解析）。

---

## 6）交付物清单（输出）

* 可运行项目目录（带 README、requirements.txt、setup.sh 或 venv 指导）。
* 主程序 `main.py`（启动 UI + 后端仿真）。
* 模块目录：`sim/`（仿真内核）、`ui/`（PyQt5 界面）、`io/`（网络/文件接口）、`processors/`（图像/视频）、`ew/`（电子战模块）、`tests/`（pytest）。
* 示例场景文件（至少 3 个：空战超视距、空地联合、EW 干扰强场景）。
* 演示脚本：`run_demo.sh`、`send_test_udp.py`（向模拟器发送观测/控制包的客户端）。
* 文档：API 文档（简要）、运行指南、示例场景说明、性能与已知限制说明。

---

## 7）验收标准（Acceptance Criteria）

1. 可以加载场景并在 UI 上可视化多个传感器与目标轨迹。
2. 多目标跟踪能输出 track JSON，跟踪误差统计能计算并在界面显示。
3. 至少 2 路视频流能被仿真、压缩为 JPEG2000（或回退压缩）、并在 UI 中播放；可以模拟不同带宽导致的帧丢失/质量下降。
4. 可以注入虚假目标与 EW 干扰，并能观测到跟踪性能下降（误报/漏报率上升）。
5. 提供网络接口（示例：UDP 观测接收、TCP 控制），并有示例客户端。
6. 包含单元测试覆盖关键逻辑（运行 `pytest` 通过）。

---

## 8）演示场景与测试用例（至少包含）

* 场景 A：超视距空战 — 3 个空中目标，2 个相控阵传感器，数据融合后定位精度目标 < 200 m。
* 场景 B：空地混合 — 地面目标低对比度，昼夜切换影响识别率。
* 场景 C：EW 强干扰 — 注入 5 个伪目标 + 干扰噪声，提高跟踪丢失率，展示干扰前后指标对比。

每个场景应有脚本自动运行并导出结果（CSV/JSON）作为回归测试。

---

## 9）示例文件结构（候选）

```
dist_aperture_sim/
├─ README.md
├─ requirements.txt
├─ main.py
├─ sim/
│  ├─ __init__.py
│  ├─ target_generator.py
│  ├─ sensor_node.py
│  ├─ tracker.py
│  ├─ fusion.py
│  └─ ew_simulator.py
├─ ui/
│  ├─ __init__.py
│  ├─ main_window.py
│  ├─ map_view.py
│  └─ video_panel.py
├─ io/
│  ├─ udp_server.py
│  ├─ tcp_control.py
│  └─ j2k_codec.py
├─ processors/
│  ├─ image_enhance.py
│  └─ stitcher.py
├─ tests/
│  └─ test_tracker.py
├─ scenarios/
│  └─ scenario_a.yaml
└─ tools/
   └─ send_test_udp.py
```

---

## 10）交付给代码生成器/开发者时的额外说明（短句）

* 优先保证仿真正确性与模块化接口；性能可在后续迭代优化。
* 将复杂算法实现为可替换的策略类（Strategy Pattern），便于后续替换为更复杂的 MHT/深度学习方法。
* 在 UI 中暴露主要参数（噪声、码率、干扰强度），便于实验调参。