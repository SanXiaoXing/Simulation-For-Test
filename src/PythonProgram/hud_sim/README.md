# ✅ **1. 输入与输出参数定义（含类型、字节数）**

## **1.1 输入参数（仿真软件接收/配置数据）**

| 输入名称 | 功能说明 | 类型 | 字节数 |
| --- | --- | --- | --- |
| update_hz | 仿真更新频率（Hz），决定发送周期 | float64 | 8 |
| mode | HUD 显示模式：`air_to_air`/`air_to_ground`/`air_to_sea` | enum(string) | 变长 |
| out_host | 输出目标主机（IP/域名） | string(UTF-8) | 变长 |
| out_port | 输出目标端口 | uint16 | 2 |
| protocol | 输出协议：`udp`/`tcp`（UI 里也可选 `afdx`/`fc`，当前未实现发送器） | enum(string) | 变长 |
| link_speed_bps | 链路速率（用于带宽占用计算） | float64 | 8 |
| icd_path | ICD（字段筛选）JSON 文件路径（为空则不筛选） | string(UTF-8) / null | 变长 |
| icd_schema.fields[].name | ICD 字段白名单，支持点分路径（如 `flight.airspeed_mps`） | string(UTF-8) | 变长 |

---

## **1.2 输出参数（仿真软件发送数据）**

| 输出名称 | 功能说明 | 类型 | 字节数 |
| --- | --- | --- | --- |
| hud_frame | 单帧 HUD 数据（按 update_hz 周期发送） | bytes（UTF-8 JSON） | 变长 |
| ts | 时间戳（Unix 秒，浮点） | float64 | 8（JSON 变长） |
| mode | 当前 HUD 模式（同输入 mode） | string(UTF-8) | 变长 |
| flight.airspeed_mps | 空速（m/s） | float64 | 8（JSON 变长） |
| flight.altitude_m | 高度（m） | float64 | 8（JSON 变长） |
| flight.heading_deg | 航向（deg） | float64 | 8（JSON 变长） |
| flight.g_load | 过载（G） | float64 | 8（JSON 变长） |
| flight.aoa_deg | 迎角（deg） | float64 | 8（JSON 变长） |
| flight.dive_deg | 俯冲角（deg，仅空地模式动态更新） | float64 | 8（JSON 变长） |
| flight.climb_deg | 爬升角（deg，仅空地模式动态更新） | float64 | 8（JSON 变长） |
| flight.fuel_kg | 燃油（kg） | float64 | 8（JSON 变长） |
| weapon.selected | 选中武器类型标识（示例：`AAM`） | string(UTF-8) | 变长 |
| weapon.status | 武器状态（示例：`READY`） | string(UTF-8) | 变长 |
| weapon.locked | 是否锁定目标 | bool | 1（JSON 变长） |
| weapon.max_range_m | 最大射程（m） | float64 | 8（JSON 变长） |
| weapon.min_range_m | 最小射程（m） | float64 | 8（JSON 变长） |
| weapon.launch_perm | 是否具备发射许可 | bool | 1（JSON 变长） |
| weapon.ammo_left | 剩余弹量 | int | 变长 |
| tactical.target_bearing_deg | 目标方位（deg） | float64 | 8（JSON 变长） |
| tactical.target_distance_m | 目标距离（m） | float64 | 8（JSON 变长） |
| tactical.closure_rate_mps | 闭合速度（m/s，示例为负表示接近） | float64 | 8（JSON 变长） |
| tactical.threat_level | 威胁等级（示例：`LOW`） | string(UTF-8) | 变长 |
| tactical.waypoint_distance_m | 航路点距离（m） | float64 | 8（JSON 变长） |
| tactical.sea_obstacle_warn | 海面障碍告警 | bool | 1（JSON 变长） |

