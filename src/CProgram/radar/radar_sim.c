#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>

#define MAX_THREATS 64
#define MAX_RADAR_TARGETS 128

/*---------- 数据结构定义 ----------*/

/* 图像传感系统的威胁目标 */
typedef enum { TARGET_UNKNOWN=0, TARGET_AIR, TARGET_SURFACE, TARGET_MISSILE } TargetType;

typedef struct {
    int id;
    TargetType type;
    double distance_m;
    double azimuth_deg;
    double frequency_hz;
    double distance_30ms_m;
    double azimuth_30ms_deg;
    double speed_m_s;
    double direction_deg;
} ImageThreat;

/* 雷达前端目标 */
typedef struct {
    int id;
    double distance_m;
    double azimuth_deg;
    double rcs_db;
    double velocity_m_s;
} RadarTarget;

/* 火控请求 */
typedef struct {
    int requested_target_id;
} FireControlRequest;

/* 向多功能显示 (MFD) 的输出 */
typedef struct {
    int effective_count;
    int threat_count;
    ImageThreat threats[MAX_THREATS];
} MFDThreatOutput;

typedef struct {
    int radar_count;
    RadarTarget radar_targets[MAX_RADAR_TARGETS];
    char radar_image_info[256];
} MFDRadarOutput;

/* 火控响应输出 */
typedef struct {
    int target_id;
    double distance_m;
    double azimuth_deg;
} FireControlOutput;

/*---------- 主处理函数 ----------*/

/*
一次性处理整个数据链路：
输入：
- 图像威胁列表
- 雷达列表
- 火控请求

输出：
- 输出给 MFD 的威胁结果
- 输出给 MFD 的雷达可视化结果
- 输出给火控模块的选中目标参数
*/
void radar_signal_processing_pipeline(
        ImageThreat *img_list, int img_count,
        RadarTarget *radar_list, int radar_count,
        FireControlRequest *fc_req,
        MFDThreatOutput *out_mfd_threat,
        MFDRadarOutput *out_mfd_radar,
        FireControlOutput *out_fc)
{
    /*------------------------------------------------*/
    /* 1. 处理图像威胁列表 → 输出有效威胁数量         */
    /*------------------------------------------------*/
    out_mfd_threat->threat_count = 0;
    for (int i = 0; i < img_count && i < MAX_THREATS; i++) {
        out_mfd_threat->threats[out_mfd_threat->threat_count++] = img_list[i];
    }

    int eff = 0;
    for (int i = 0; i < out_mfd_threat->threat_count; i++) {
        if (img_list[i].speed_m_s > 0.1 || img_list[i].distance_m < 100000)
            eff++;
    }
    out_mfd_threat->effective_count = eff;

    /*------------------------------------------------*/
    /* 2. 处理雷达列表 → 输出给 MFD 的雷达信息        */
    /*------------------------------------------------*/
    out_mfd_radar->radar_count = 0;
    for (int i = 0; i < radar_count && i < MAX_RADAR_TARGETS; i++) {
        out_mfd_radar->radar_targets[out_mfd_radar->radar_count++] = radar_list[i];
    }
    snprintf(out_mfd_radar->radar_image_info,
             sizeof(out_mfd_radar->radar_image_info),
             "Radar image snapshot (%d targets)", out_mfd_radar->radar_count);

    /*------------------------------------------------*/
    /* 3. 火控请求处理 → 找到合适的目标返回           */
    /*------------------------------------------------*/
    int found = -1;
    for (int i = 0; i < radar_count; i++) {
        if (radar_list[i].id == fc_req->requested_target_id) {
            found = i;
            break;
        }
    }

    if (found >= 0) {
        /* 找到精确目标 */
        out_fc->target_id   = radar_list[found].id;
        out_fc->distance_m  = radar_list[found].distance_m;
        out_fc->azimuth_deg = radar_list[found].azimuth_deg;
    } else if (radar_count > 0) {
        /* 找不到 → 使用距离最近目标作为回退策略 */
        int idx = 0;
        double best_d = radar_list[0].distance_m;

        for (int i = 1; i < radar_count; i++) {
            if (radar_list[i].distance_m < best_d) {
                best_d = radar_list[i].distance_m;
                idx = i;
            }
        }
        out_fc->target_id   = radar_list[idx].id;
        out_fc->distance_m  = radar_list[idx].distance_m;
        out_fc->azimuth_deg = radar_list[idx].azimuth_deg;
    } else {
        /* 连一个目标都没有 */
        out_fc->target_id   = -1;
        out_fc->distance_m  = 0;
        out_fc->azimuth_deg = 0;
    }
}

/*---------- Demo：一次输入 → 全部输出 ----------*/
int main()
{
    printf("=== Radar Simulation Unified Run ===\n");

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

    FireControlRequest fc_req[2] = {
        {101},
        {102}
    };   /* 火控请求攻击目标101 */

    /* 输出结构 */
    MFDThreatOutput mfd_threat;
    MFDRadarOutput  mfd_radar;
    FireControlOutput fc_out;

    /* 一次处理完成整套链路 */
    radar_signal_processing_pipeline(
        img_targets, 2,
        radar_targets, 3,
        &fc_req,
        &mfd_threat,
        &mfd_radar,
        &fc_out
    );

    /*------------------------------------------------*/
    /* 输出结果：一次汇总打印                        */
    /*------------------------------------------------*/
    printf("\n=== Output To MFD (Threat Display) ===\n");
    printf("Effective Threat Count: %d\n", mfd_threat.effective_count);
    for (int i = 0; i < mfd_threat.threat_count; i++) {
        ImageThreat *t = &mfd_threat.threats[i];
        printf("Threat[%d] id=%d dist=%.1f az=%.2f speed=%.1f\n",
               i, t->id, t->distance_m, t->azimuth_deg, t->speed_m_s);
    }

    printf("\n=== Output To MFD (Radar Display) ===\n");
    printf("Radar Targets: %d (%s)\n", mfd_radar.radar_count, mfd_radar.radar_image_info);
    for (int i = 0; i < mfd_radar.radar_count; i++) {
        RadarTarget *r = &mfd_radar.radar_targets[i];
        printf("Radar[%d] id=%d dist=%.1f az=%.2f vel=%.1f\n",
               i, r->id, r->distance_m, r->azimuth_deg, r->velocity_m_s);
    }

    printf("\n=== Output To Fire Control ===\n");
    if (fc_out.target_id >= 0) {
        printf("Selected Target: id=%d dist=%.1f az=%.2f\n",
               fc_out.target_id, fc_out.distance_m, fc_out.azimuth_deg);
    } else {
        printf("No valid radar target for fire control.\n");
    }

    printf("\n=== Simulation Complete ===\n");
    return 0;
}
