/*
 CNI Simulation Application (简化示例)
  - 输入：目标列表、无线电/导航仿真输入、惯导/大气状态
  - 输出：导航数据包、通信数据、目标感知列表
  - 编译: gcc -O2 -o cni_sim cni_sim.c -lm
*/

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

/* ---------------------------
   常量与辅助函数
   --------------------------- */
#define MAX_TARGETS 128
#define DEG2RAD (M_PI/180.0)
#define RAD2DEG (180.0/M_PI)

static double normalize_heading(double hdg) {
    while (hdg < 0) hdg += 360.0;
    while (hdg >= 360.0) hdg -= 360.0;
    return hdg;
}

/* ---------------------------
   输入结构体定义（标注：这些为输入参数）
   --------------------------- */

/* 单个目标（来自 CNI 仿真系统） */
typedef struct {
    int id;                     /* 输入: 目标唯一标识符 */
    double lat_deg;             /* 输入: 目标经度 (deg) */
    double lon_deg;             /* 输入: 目标纬度 (deg) */
    double alt_m;               /* 输入: 目标高度 (m) */
    double vel_ned_mps[3];      /* 输入: 目标速度 N,E,D (m/s) */
    double azimuth_deg;         /* 输入: 目标相对于某参考的方位角 (deg) */
    int iff_code;               /* 输入: IFF/敌我识别数据 */
} Target;

/* 短波通信仿真包（输入示例） */
typedef struct {
    int source_id;              /* 输入: 发送方 id */
    int dest_id;                /* 输入: 目的方 id */
    double tx_power_dbm;        /* 输入: 发送功率 (dBm) */
    double frequency_hz;        /* 输入: 频率 */
    double timestamp_s;         /* 输入: 发包时间 */
    char payload[256];          /* 输入: 有效载荷（文本） */
} ShortwavePacket;

/* 雷达高度表仿真输入（占位）*/
typedef struct {
    int active;                 /* 输入: 是否启用 */
    double frequency_hz;
} RadarAltimeterInput;

/* TACAN / ILS / ADF 等可扩展为类似结构。此处只放占位结构 */
typedef struct {
    int tacan_active;
    int ils_active;
    int adf_active;
} RadioSystemInputs;

/* 惯导/大气仿真输入（飞行器自状态） */
typedef struct {
    double ego_lat_deg;         /* 输入: 本机经度 (deg) */
    double ego_lon_deg;         /* 输入: 本机纬度 (deg) */
    double ego_alt_m;           /* 输入: 本机高度 (m) */
    double airspeed_mps;        /* 输入: 空速 (m/s) */
    double groundspeed_mps;     /* 输入: 地速 (m/s) */
    double accel_mps2[3];       /* 输入: 机体加速度 (m/s^2) */
    double ang_rate_rps[3];     /* 输入: 角速度 (rad/s) */
    double attitude_deg[3];     /* 输入: 俯仰, 横滚, 偏航 (deg) */
} InertialAtmosInputs;

/* 整体输入容器 */
typedef struct {
    Target targets[MAX_TARGETS];        /* 输入: 目标数组 */
    int target_count;                   /* 输入: 目标数量 */
    ShortwavePacket sw_packet;          /* 输入: 短波信令样例 */
    RadarAltimeterInput radaralt;       /* 输入: 雷达高程仪 */
    RadioSystemInputs radio_inputs;     /* 输入: 其他无线电设备 */
    InertialAtmosInputs nav_inputs;     /* 输入: 惯导/大气状态 */
    double sim_time_s;                  /* 输入: 当前仿真时间 */
    double dt_s;                        /* 输入: 时间步 */
} CNIInputs;

/* ---------------------------
   输出结构体定义（标注：这些为输出参数）
   --------------------------- */

/* 导航输出（发往多功能显示仿真系统） */
typedef struct {
    double lat_deg;             /* 输出: 位置经度 (deg) */
    double lon_deg;             /* 输出: 位置纬度 (deg) */
    double alt_m;               /* 输出: 高度 (m) */
    double heading_deg;         /* 输出: 航向 (deg) */
    double groundspeed_mps;     /* 输出: 地速 (m/s) */
    double airspeed_mps;        /* 输出: 空速 (m/s) */
    double attitude_deg[3];     /* 输出: 俯仰, 横滚, 偏航 (deg) */
    double timestamp_s;         /* 输出: 时间戳 */
} NavOutput;

/* 单个目标轨迹/识别输出 */
typedef struct {
    int id;                     /* 输出: 目标 id */
    double est_lat_deg;         /* 输出: 估计经度 */
    double est_lon_deg;         /* 输出: 估计纬度 */
    double est_alt_m;           /* 输出: 估计高度 */
    double est_v_ned[3];        /* 输出: 估计速度 N,E,D */
    int iff_classified;         /* 输出: IFF 判定（0未知,1友好,2敌对）*/
    double track_snr_db;        /* 输出: 估计信噪比（示例值） */
} TrackOutput;

/* 通信输出包（发送到多功能显示或记录） */
typedef struct {
    int source_id;
    int dest_id;
    double rx_snr_db;           /* 输出: 接收端估计的信噪比 */
    char decoded_payload[256];  /* 输出: 解调/解码后的负载（文本） */
    double timestamp_s;
} CommOutput;

/* 整体输出容器 */
typedef struct {
    NavOutput nav;                      /* 输出: 导航数据 */
    TrackOutput tracks[MAX_TARGETS];    /* 输出: 目标轨迹列表 */
    int track_count;                    /* 输出: 轨迹个数 */
    CommOutput comm;                    /* 输出: 通信数据 */
} CNIOutputs;

/* ---------------------------
   模拟/处理函数（核心）
   这些函数实现输入->输出的转换（简化模型）
   --------------------------- */

/* 简单经纬度前向传播（WGS84 非精确，仅示例）：根据 N/E 位移（米）估计经纬度 */
static void latlon_offset(double lat_deg, double lon_deg,
                          double north_m, double east_m,
                          double *out_lat_deg, double *out_lon_deg) {
    /* 地球半径近似 */
    const double R = 6378137.0;
    double dlat = north_m / R;
    double dlon = east_m / (R * cos(lat_deg * DEG2RAD));
    *out_lat_deg = lat_deg + dlat * RAD2DEG;
    *out_lon_deg = lon_deg + dlon * RAD2DEG;
}

/* 估计目标位置（非常简单的线性外推） */
static void estimate_target(const Target *t, double dt, TrackOutput *out) {
    /* 输出 id */
    out->id = t->id;
    /* 用 N,E 分量假设 vel_ned_mps[0]=N, [1]=E, [2]=D */
    double north = t->vel_ned_mps[0] * dt;
    double east  = t->vel_ned_mps[1] * dt;
    double down  = t->vel_ned_mps[2] * dt;

    /* 将位移转换为经纬度偏移（占位） */
    double est_lat, est_lon;
    latlon_offset(t->lat_deg, t->lon_deg, north, east, &est_lat, &est_lon);

    out->est_lat_deg = est_lat;
    out->est_lon_deg = est_lon;
    out->est_alt_m = t->alt_m - down; /* 注意 down 是负向分量 */

    out->est_v_ned[0] = t->vel_ned_mps[0];
    out->est_v_ned[1] = t->vel_ned_mps[1];
    out->est_v_ned[2] = t->vel_ned_mps[2];

    /* IFF 简单映射：假设 iff_code > 0 为友好 */
    if (t->iff_code == 0) out->iff_classified = 0;
    else if (t->iff_code > 0) out->iff_classified = 1;
    else out->iff_classified = 2;

    /* SNR：根据距离做简单衰减估计（占位） */
    double latdiff = (out->est_lat_deg - t->lat_deg) * DEG2RAD;
    double londiff = (out->est_lon_deg - t->lon_deg) * DEG2RAD;
    double approx_dist = sqrt(latdiff*latdiff + londiff*londiff) * 6378137.0;
    double snr = 30.0 - 20.0*log10(1.0 + approx_dist/1000.0); /* 简单模型 */
    out->track_snr_db = snr;
}

/* 模拟短波信号接收与解码（占位） */
static void process_shortwave(const ShortwavePacket *pkt, const InertialAtmosInputs *nav,
                              CommOutput *out) {
    out->source_id = pkt->source_id;
    out->dest_id = pkt->dest_id;
    out->timestamp_s = pkt->timestamp_s;

    /* 简单 path loss based on distance between ego and pkt.dest (use coordinates) */
    /* 假设 pkt.dest_id 对应于本机（ego），否则简单衰减模型 */
    double dist_km = 100.0; /* 占位：实际应由目标位置计算 */
    double rx_snr = pkt->tx_power_dbm - (20.0 * log10(dist_km + 1.0)) - 100.0; /* 非物理但示例 */
    out->rx_snr_db = rx_snr;

    /* 解码策略：如果 snr > -10 dB 则认为能解码 */
    if (rx_snr > -10.0) {
        strncpy(out->decoded_payload, pkt->payload, sizeof(out->decoded_payload)-1);
        out->decoded_payload[sizeof(out->decoded_payload)-1] = '\0';
    } else {
        snprintf(out->decoded_payload, sizeof(out->decoded_payload), "[UNDECODABLE]");
    }
}

/* 生成导航输出（整合惯导状态与估计） */
static void generate_nav_output(const InertialAtmosInputs *navin, double sim_time, NavOutput *navout) {
    navout->lat_deg = navin->ego_lat_deg;
    navout->lon_deg = navin->ego_lon_deg;
    navout->alt_m = navin->ego_alt_m;
    navout->airspeed_mps = navin->airspeed_mps;
    navout->groundspeed_mps = navin->groundspeed_mps;
    navout->attitude_deg[0] = navin->attitude_deg[0];
    navout->attitude_deg[1] = navin->attitude_deg[1];
    navout->attitude_deg[2] = navin->attitude_deg[2];
    /* 估计航向： 使用偏航角作为航向（占位） */
    navout->heading_deg = normalize_heading(navin->attitude_deg[2]);
    navout->timestamp_s = sim_time;
}

/* 主处理函数：把所有输入映射为输出 */
static void cni_process_step(const CNIInputs *in, CNIOutputs *out) {
    /* 1) 生成导航输出 */
    generate_nav_output(&in->nav_inputs, in->sim_time_s, &out->nav);

    /* 2) 处理目标列表 -> 轨迹输出 */
    out->track_count = in->target_count;
    for (int i = 0; i < in->target_count && i < MAX_TARGETS; ++i) {
        estimate_target(&in->targets[i], in->dt_s, &out->tracks[i]);
    }

    /* 3) 处理短波通信包 */
    process_shortwave(&in->sw_packet, &in->nav_inputs, &out->comm);

    /* 4) 其他无线电系统（TACAN/ILS/ADF/雷高）可以在此处扩展并填充 out 结构 */
}

/* ---------------------------
   示例 main()：构造输入并运行一次仿真循环
   --------------------------- */
int main(int argc, char **argv) {
    CNIInputs in;
    CNIOutputs out;
    memset(&in, 0, sizeof(in));
    memset(&out, 0, sizeof(out));

    /* 填充示例目标 */
    in.target_count = 2;
    in.targets[0].id = 101;
    in.targets[0].lat_deg = 1.350;   /* deg */
    in.targets[0].lon_deg = 103.820; /* deg */
    in.targets[0].alt_m = 8000.0;
    in.targets[0].vel_ned_mps[0] = 200.0; /* N */
    in.targets[0].vel_ned_mps[1] = 10.0;  /* E */
    in.targets[0].vel_ned_mps[2] = -5.0;  /* D (down) */
    in.targets[0].azimuth_deg = 45.0;
    in.targets[0].iff_code = 1;

    in.targets[1].id = 202;
    in.targets[1].lat_deg = 1.360;
    in.targets[1].lon_deg = 103.830;
    in.targets[1].alt_m = 5000.0;
    in.targets[1].vel_ned_mps[0] = -50.0;
    in.targets[1].vel_ned_mps[1] = 30.0;
    in.targets[1].vel_ned_mps[2] = 0.0;
    in.targets[1].azimuth_deg = 120.0;
    in.targets[1].iff_code = 0;

    /* 填充短波包（示例输入） */
    in.sw_packet.source_id = 999;
    in.sw_packet.dest_id = 0; /* assume 0 is ego */
    in.sw_packet.tx_power_dbm = 20.0;
    in.sw_packet.frequency_hz = 5.0e6;
    in.sw_packet.timestamp_s = 100.0;
    strncpy(in.sw_packet.payload, "Hello from SW radio", sizeof(in.sw_packet.payload)-1);

    /* 惯导输入示例 */
    in.nav_inputs.ego_lat_deg = 1.352;
    in.nav_inputs.ego_lon_deg = 103.825;
    in.nav_inputs.ego_alt_m = 12000.0;
    in.nav_inputs.airspeed_mps = 250.0;
    in.nav_inputs.groundspeed_mps = 260.0;
    in.nav_inputs.accel_mps2[0] = 0.0;
    in.nav_inputs.ang_rate_rps[2] = 0.01;
    in.nav_inputs.attitude_deg[0] = 2.5;
    in.nav_inputs.attitude_deg[1] = 0.5;
    in.nav_inputs.attitude_deg[2] = 85.0;

    in.sim_time_s = 100.0;
    in.dt_s = 1.0;

    /* 运行一步仿真处理 */
    cni_process_step(&in, &out);

    /* 输出结果（示例打印） */
    printf("=== Nav Output ===\n");
    printf("Lat: %.6f Lon: %.6f Alt: %.1f m\n", out.nav.lat_deg, out.nav.lon_deg, out.nav.alt_m);
    printf("Heading: %.2f deg GroundSpeed: %.2f m/s Airspeed: %.2f m/s\n",
           out.nav.heading_deg, out.nav.groundspeed_mps, out.nav.airspeed_mps);
    printf("Attitude (pitch, roll, yaw): %.2f, %.2f, %.2f deg\n",
           out.nav.attitude_deg[0], out.nav.attitude_deg[1], out.nav.attitude_deg[2]);

    printf("\n=== Tracks (%d) ===\n", out.track_count);
    for (int i = 0; i < out.track_count; ++i) {
        TrackOutput *t = &out.tracks[i];
        printf("ID=%d EstLat=%.6f EstLon=%.6f EstAlt=%.1f m SNR=%.2f dB IFF=%d\n",
               t->id, t->est_lat_deg, t->est_lon_deg, t->est_alt_m, t->track_snr_db, t->iff_classified);
    }

    printf("\n=== Comm Output ===\n");
    printf("From %d to %d, RxSNR=%.2f dB, Payload=\"%s\"\n",
           out.comm.source_id, out.comm.dest_id, out.comm.rx_snr_db, out.comm.decoded_payload);

    return 0;
}
