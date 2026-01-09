# ✅ **1. 输入与输出参数定义（含类型、字节数）**

## **1.1 输入参数（仿真软件接收/配置数据）**

### UDP 接口配置

| 输入名称 | 功能说明 | 类型 | 字节数 |
| --- | --- | --- | --- |
| `out_host` | UDP 发送目的 IP | string | - |
| `out_port` | UDP 发送目的端口（默认 `6006`） | uint16 | 2 |
| `listen_port` | 可选 UDP 监听端口（>0 时开启监听） | uint16 | 2 |

说明：当前版本监听端口仅用于回显“收到的字节长度”，不对输入报文做解析与字段映射。

### 生成报文的状态输入（UI/仿真状态）

| 输入名称 | 功能说明 | 类型 | 字节数 |
| --- | --- | --- | --- |
| `frame_mode` | 模式/目标类型标识：`1`=雷达，`2`=通信导航 | uint8 | 1 |
| `targets[]` | 目标列表（见“目标块”字段） | struct | 30 × N |
| `shortwave + altimeter` | 短波通信 + 无线电高度表参数块 | struct | 19 |
| `nav` | 导航/惯导参数块 | struct | 64 |
| `rx_payload` | 任意 UDP 数据报（当前仅打印长度，不解析） | bytes | 变长（0~65536） |

## **1.2 输出参数（仿真软件发送数据：UDP 二进制帧）**

### 1.2.1 总体结构

- 字节序：小端（Little Endian）
- 浮点：IEEE-754 `float32`
- 帧总长度：`5 + payload_len`
- `payload_len` 计算：`target_count * 30 + 19 + 64`（即 `target_count * 30 + 83`）

### 1.2.2 帧头（5 字节）

结构体格式（Python `struct`）：`<H B B B`

| 字段名 | 功能说明 | 类型 | 字节数 |
| --- | --- | --- | --- |
| `header` | 包头固定值 `0xAA55` | uint16 | 2 |
| `frame_mode` | 模式/目标类型标识：`1`=雷达，`2`=通信导航 | uint8 | 1 |
| `payload_len` | 负载长度（不含帧头） | uint8 | 1 |
| `target_count` | 目标数量 `N` | uint8 | 1 |

### 1.2.3 目标块（`N` × 30 字节）

单目标结构体格式（Python `struct`）：`<B f f f f f f f B`

| 字段名 | 功能说明 | 类型 | 字节数 |
| --- | --- | --- | --- |
| `target_id` | 目标唯一标识（0~255） | uint8 | 1 |
| `lat_deg` | 纬度（deg） | float32 | 4 |
| `lon_deg` | 经度（deg） | float32 | 4 |
| `alt_m` | 高度（m） | float32 | 4 |
| `vel_ned_mps_N` | 北向速度（m/s） | float32 | 4 |
| `vel_ned_mps_E` | 东向速度（m/s） | float32 | 4 |
| `vel_ned_mps_D` | 下向速度（m/s，Down 为正） | float32 | 4 |
| `azimuth_deg` | 方位角（deg） | float32 | 4 |
| `iff_code` | 敌我识别码（0~255） | uint8 | 1 |

### 1.2.4 通信与无线电高度表块（19 字节）

结构体格式（Python `struct`）：`<B B f f f B f`

| 字段名 | 功能说明 | 类型 | 字节数 |
| --- | --- | --- | --- |
| `shortwave.source_id` | 短波发送方 ID（0~255） | uint8 | 1 |
| `shortwave.dest_id` | 短波接收方 ID（0~255） | uint8 | 1 |
| `shortwave.tx_power_dbm` | 发射功率（dBm） | float32 | 4 |
| `shortwave.frequency_hz` | 频率（Hz） | float32 | 4 |
| `shortwave.timestamp_s` | 时间戳（秒，取当日秒数 0~86400） | float32 | 4 |
| `altimeter.active` | 无线电高度表启用标志（0/1） | uint8 | 1 |
| `altimeter.frequency_hz` | 无线电高度表工作频率（Hz） | float32 | 4 |

### 1.2.5 导航/惯导块（64 字节）

结构体格式（Python `struct`）：`<f f f f f f f f f f f f f f f f`（16 × `float32`）

| 序号 | 字段名 | 功能说明 | 类型 | 字节数 |
| ---: | --- | --- | --- | --- |
| 1 | `nav.ego_lat_deg` | 本机纬度（deg） | float32 | 4 |
| 2 | `nav.ego_lon_deg` | 本机经度（deg） | float32 | 4 |
| 3 | `nav.ego_alt_m` | 本机高度（m） | float32 | 4 |
| 4 | `nav.airspeed_mps` | 空速（m/s） | float32 | 4 |
| 5 | `nav.groundspeed_mps` | 地速（m/s） | float32 | 4 |
| 6 | `nav.accel_mps2[0]` | 加速度 X（m/s²） | float32 | 4 |
| 7 | `nav.accel_mps2[1]` | 加速度 Y（m/s²） | float32 | 4 |
| 8 | `nav.accel_mps2[2]` | 加速度 Z（m/s²） | float32 | 4 |
| 9 | `nav.ang_rate_rps[0]` | 角速度 X（rad/s） | float32 | 4 |
| 10 | `nav.ang_rate_rps[1]` | 角速度 Y（rad/s） | float32 | 4 |
| 11 | `nav.ang_rate_rps[2]` | 角速度 Z（rad/s） | float32 | 4 |
| 12 | `nav.attitude_deg[0]` | 俯仰（deg） | float32 | 4 |
| 13 | `nav.attitude_deg[1]` | 横滚（deg） | float32 | 4 |
| 14 | `nav.attitude_deg[2]` | 偏航（deg） | float32 | 4 |
| 15 | `reserved_1` | 预留 | float32 | 4 |
| 16 | `reserved_2` | 预留 | float32 | 4 |

## 2. 约束与注意事项

| 项 | 说明 |
| --- | --- |
| `payload_len` 为 1 字节 | 当 `target_count` 过大时会溢出（代码中按 `& 0xFF` 截断）。为避免溢出，建议 `target_count <= 5`（此时 `payload_len = 233`）。 |
| `target_count` 为 1 字节 | 取值范围 0~255，但仍受 `payload_len` 上述约束影响。 |
| 当前无 CRC/校验字段 | 若用于联调，建议接收端先校验 `header==0xAA55` 与长度一致性。 |
