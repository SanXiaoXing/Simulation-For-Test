# ✅ **1. 输入与输出参数定义（含类型、字节数）**

## **1.1 输入参数（仿真软件接收数据）**

| 输入名称               | 功能说明                  | 类型      | 字节数    |
| ------------------ | --------------------- | ------- | ------ |
| weapon_type        | 武器类型（导弹、炸弹、火箭等）       | uint8_t | 1      |
| weapon_count       | 武器数量                  | uint8_t | 1      |
| pylon_config[]     | 外挂点配置参数（编号、姿态角、载荷限制等） | struct  | 16 × N |
| target_info        | 目标探测数据（距离/方位/速度/ID）   | struct  | 32     |
| fire_control_input | 火控解算输入（弹道参数/时间等）      | struct  | 32     |
| weapon_bind_cmd    | 武器装订/解除指令             | uint8_t | 1      |
| roe_config         | ROE 交战规则              | struct  | 8      |
| system_mode        | 系统模式指令                | uint8_t | 1      |
| nav_flight_data    | 导航飞行数据（姿态/速度/GPS等）    | struct  | 64     |
| pylon_feedback     | 外挂物健康反馈（温度、电源、状态）     | struct  | 16     |

---

## **1.2 输出参数（仿真软件发送数据）**

| 输出名称               | 功能               | 类型      | 字节数 |
| ------------------ | ---------------- | ------- | --- |
| intercept_decision | 是否拦截、模式选择        | uint8_t | 1   |
| intercept_param    | 拦截参数（提前量、时间、火控量） | struct  | 32  |
| ammo_status        | 弹药管理状态（剩余弹量、可用性） | struct  | 8   |
| pylon_health       | 外挂物健康状态          | struct  | 16  |
| weapon_fire_cmd    | 武器发射指令           | uint8_t | 1   |
| fcs_output         | 火控参数输出           | struct  | 32  |
| threat_warning     | 威胁告警             | struct  | 8   |
| system_warning     | 系统异常告警           | struct  | 8   |
| sync_data          | 武器航电同步数据         | struct  | 32  |
| hmi_feedback       | 人机交互回显信息         | struct  | 16  |


