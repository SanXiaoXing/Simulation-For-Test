# 输入参数（每个信号事件/脉冲或截获包）

- `source_id (uint32)` — 信号来源 ID（仿真器分配）

- `type (enum SignalType)` — 雷达 / 通信 / 干扰（RADAR, COMM, JAM）

- `timestamp (uint64, UNIX ms)` — 事件时间戳（毫秒）

- `center_freq_hz (double)` — 中心频率（Hz）

- `bandwidth_hz (double)` — 带宽（Hz）

- `signal_power_dbm (float)` — 信号功率 dBm

- `snr_db (float)` — 估计信噪比 dB

- `azimuth_deg (float)` — 方向角（度）

- `elevation_deg (float)` — 仰角（度）

- `range_m (float)` — 估计距离（米） — 如果无则填 -1

- `pri_ms (float)` — 脉冲重复间隔 ms（雷达）

- `pulse_width_us (float)` — 脉冲宽度 微秒（雷达）

- `modulation (enum)` — 调制类型（NONE/PSK/FDM/AM/FM等）

- `raw_iq (optional pointer + length)` — 若需要可传 IQ 数据（此示例用 NULL）


# 输出参数 / 报文（ThreatReport）

- `report_id (uint64)` — 报告唯一 ID

- `detected_time_ms (uint64)` — 检测时间戳

- `source_id (uint32)` — 对应输入 source_id（若无法关联则 0）

- `threat_type (enum ThreatType)` — 雷达（TRACKING）, 导引雷达（MISSILE_TRACKING）, 通信（COMMS）, 干扰（JAMMER）, UNKNOWN

- `confidence (float 0..1)` — 置信度

- `alert_level (enum AlertLevel)` — INFO/WARNING/CRITICAL

- `azimuth_deg, elevation_deg, range_m, center_freq_hz` — 估计定位参数

- `classification_tags (bitmask/flags)` — 例如 PULSE_DOPPLER, CW, LPI 等

- `recommended_action (string 或 enum) `— 建议（DISPLAY_ONLY, WARN_OPERATOR, COUNTERMEASURE）

- `raw_features (optional)` — 结构化特征值（PRI, PW, PDOPPLER, SNR）