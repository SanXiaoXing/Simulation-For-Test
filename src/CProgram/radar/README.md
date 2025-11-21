图像威胁输入

↓

雷达前端目标输入

↓

火控模块查询请求（可选）
↓
雷达信号处理引擎运行：
- 目标匹配
- 状态跟踪
- 威胁分析
- 火控解算

↓

并行输出：

→ 
  
多功能显示系统
    - 威胁表
    - 雷达目标表
    - 图像态势数据
      → 火控计算模块
    - 指定目标定位数据

输入数据：
```
/* 输入数据 */
ImageThreat img_targets[2] = {
    {101, TARGET_AIR, 15000, 45.0, 2.4e9, 14990, 45.1, 200, 90},
    {102, TARGET_SURFACE, 8000, 270, 0, 7997, 269.9, 5, 270}
};

RadarTarget radar_targets[3] = {
    {101, 15003, 45.2,  -4.0, 198},
    {201, 5000,  10.0,   3.0,   0},
    {102, 7998,  269.7, -10.0,  5}
};

FireControlRequest fc_req = {101};   /* 火控请求攻击目标101 */
```

示例输出：
```
=== Radar Simulation Unified Run ===

=== Output To MFD (Threat Display) ===
Effective Threat Count: 2
Threat[0] id=101 dist=15000.0 az=45.00 speed=200.0
Threat[1] id=102 dist=8000.0 az=270.00 speed=5.0

=== Output To MFD (Radar Display) ===
Radar Targets: 3 (Radar image snapshot (3 targets))
Radar[0] id=101 dist=15003.0 az=45.20 vel=198.0
Radar[1] id=201 dist=5000.0 az=10.00 vel=0.0
Radar[2] id=102 dist=7998.0 az=269.70 vel=5.0

=== Output To Fire Control ===
Selected Target: id=101 dist=15003.0 az=45.20

=== Simulation Complete ===
````

