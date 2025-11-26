// ew_sim.c
// 编译: gcc -std=c99 -O2 -o ew_sim ew_sim.c
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <math.h>

/* ---------- 常量/枚举 ---------- */
typedef enum { SIG_RADAR=0, SIG_COMM, SIG_JAM } SignalType;
typedef enum { THR_UNKNOWN=0, THR_RADAR, THR_MISSILE_TRACKING, THR_COMMS, THR_JAMMER } ThreatType;
typedef enum { ALERT_INFO=0, ALERT_WARN, ALERT_CRITICAL } AlertLevel;
typedef enum { MOD_NONE=0, MOD_AM, MOD_FM, MOD_PSK, MOD_FDM } Modulation;

#define MAX_TAGS 32

/* ---------- 输入数据结构 ---------- */
typedef struct {
    uint32_t source_id;
    SignalType type;
    uint64_t timestamp_ms;        // UNIX ms
    double center_freq_hz;
    double bandwidth_hz;
    float signal_power_dbm;
    float snr_db;
    float azimuth_deg;
    float elevation_deg;
    float range_m;
    float pri_ms;
    float pulse_width_us;
    Modulation modulation;
    // raw_iq omitted in this example (pointer + length could be added)
} SignalInput;

/* ---------- 中间/输出结构 ---------- */
typedef struct {
    int detected;
    float detection_score; // 0..1
    float azimuth_deg;
    float elevation_deg;
    float range_m;
    double center_freq_hz;
} DetectionResult;

typedef struct {
    uint64_t report_id;
    uint64_t detected_time_ms;
    uint32_t source_id;
    ThreatType threat_type;
    float confidence;      // 0..1
    AlertLevel alert_level;
    float azimuth_deg;
    float elevation_deg;
    float range_m;
    double center_freq_hz;
    uint32_t classification_tags; // bitmask
    char recommended_action[64];
    // raw features
    float snr_db;
    float pri_ms;
    float pulse_width_us;
} ThreatReport;

/* ---------- 简单工具函数 ---------- */
static uint64_t now_ms() {
    struct timespec ts;
    clock_gettime(CLOCK_REALTIME, &ts);
    return (uint64_t)ts.tv_sec * 1000 + ts.tv_nsec / 1000000;
}

static uint64_t next_report_id() {
    static uint64_t id = 1000;
    return id++;
}

/* ---------- 模拟/占位 信号检测函数 ---------- */
/* 这里用非常简化的启发式规则：基于 SNR、pulse characteristics、freq、type 判别 */
void detect_signal(const SignalInput *in, DetectionResult *out) {
    if (!in || !out) return;
    out->detected = 0;
    out->detection_score = 0.0f;
    out->azimuth_deg = in->azimuth_deg;
    out->elevation_deg = in->elevation_deg;
    out->range_m = in->range_m;
    out->center_freq_hz = in->center_freq_hz;

    float score = 0.0f;
    // SNR 基础贡献
    if (in->snr_db > 20.0f) score += 0.6f;
    else if (in->snr_db > 10.0f) score += 0.35f;
    else if (in->snr_db > 0.0f) score += 0.15f;

    // 雷达特征（PRI, pulse width）
    if (in->type == SIG_RADAR) {
        if (in->pri_ms > 0.1f && in->pri_ms < 1000.0f) score += 0.25f;
        if (in->pulse_width_us > 0.05f && in->pulse_width_us < 10000.0f) score += 0.15f;
    }

    // 干扰/宽带特征
    if (in->type == SIG_JAM) {
        if (in->bandwidth_hz > 1e5) score += 0.3f;
    }

    // 通信：modulation 有效
    if (in->type == SIG_COMM && in->modulation != MOD_NONE) {
        score += 0.25f;
    }

    // cap
    if (score > 1.0f) score = 1.0f;
    out->detection_score = score;
    out->detected = (score >= 0.2f) ? 1 : 0;
}

/* ---------- 简单分类器（启发式） ---------- */
ThreatType classify_threat(const SignalInput *in, const DetectionResult *det) {
    if (!in || !det) return THR_UNKNOWN;

    // very simple rules:
    if (in->type == SIG_JAM) {
        return THR_JAMMER;
    } else if (in->type == SIG_COMM) {
        return THR_COMMS;
    } else if (in->type == SIG_RADAR) {
        // if narrow pulse and high snr and small pri -> tracking radar
        if (in->pulse_width_us < 10.0f && in->snr_db > 15.0f) {
            if (in->pri_ms < 10.0f) return THR_MISSILE_TRACKING;
            return THR_RADAR;
        } else {
            return THR_RADAR;
        }
    }
    return THR_UNKNOWN;
}

/* ---------- 生成告警等级 ---------- */
AlertLevel assess_alert_level(const DetectionResult *det, ThreatType t, const SignalInput *in) {
    if (!det || !in) return ALERT_INFO;
    if (!det->detected) return ALERT_INFO;

    // CRITICAL: 可能导引雷达或距离小且 SNR 高
    if (t == THR_MISSILE_TRACKING) return ALERT_CRITICAL;
    if (in->range_m > 0 && in->range_m < 500.0f && in->snr_db > 20.0f) return ALERT_CRITICAL;
    if (det->detection_score > 0.7f) return ALERT_WARN;
    return ALERT_INFO;
}

/* ---------- 生成 ThreatReport ---------- */
void build_report(const SignalInput *in, const DetectionResult *det, ThreatReport *rep) {
    if (!in || !det || !rep) return;
    rep->report_id = next_report_id();
    rep->detected_time_ms = now_ms();
    rep->source_id = in->source_id;
    rep->threat_type = classify_threat(in, det);
    rep->confidence = det->detection_score;
    rep->alert_level = assess_alert_level(det, rep->threat_type, in);
    rep->azimuth_deg = det->azimuth_deg;
    rep->elevation_deg = det->elevation_deg;
    rep->range_m = det->range_m;
    rep->center_freq_hz = det->center_freq_hz;
    rep->classification_tags = 0;
    // example tags bit assignment (user can extend)
    if (in->pulse_width_us > 0 && in->pulse_width_us < 50.0f) rep->classification_tags |= (1<<0); // SHORT_PULSE
    if (in->bandwidth_hz > 1e5) rep->classification_tags |= (1<<1); // WIDEBAND
    // recommended actions
    switch (rep->alert_level) {
        case ALERT_CRITICAL: strncpy(rep->recommended_action, "WARN_OPERATOR; CONSIDER_CM", sizeof(rep->recommended_action)); break;
        case ALERT_WARN: strncpy(rep->recommended_action, "DISPLAY_PROMINENT", sizeof(rep->recommended_action)); break;
        default: strncpy(rep->recommended_action, "LOG_ONLY", sizeof(rep->recommended_action)); break;
    }
    rep->snr_db = in->snr_db;
    rep->pri_ms = in->pri_ms;
    rep->pulse_width_us = in->pulse_width_us;
}

/* ---------- 输出/发送接口（目前打印；可替换为 UDP/IPC） ---------- */
void send_report(const ThreatReport *r) {
    if (!r) return;
    const char *atype = (r->alert_level==ALERT_CRITICAL)?"CRITICAL":(r->alert_level==ALERT_WARN)?"WARN":"INFO";
    const char *ttype = "UNKNOWN";
    switch (r->threat_type) {
        case THR_RADAR: ttype="RADAR"; break;
        case THR_MISSILE_TRACKING: ttype="MISSILE_TRACK"; break;
        case THR_COMMS: ttype="COMMS"; break;
        case THR_JAMMER: ttype="JAMMER"; break;
        default: break;
    }
    printf("=== ThreatReport ID:%llu ===\n", (unsigned long long)r->report_id);
    printf("time(ms): %llu  src:%u  type:%s  alert:%s  conf:%.2f\n",
        (unsigned long long)r->detected_time_ms, r->source_id, ttype, atype, r->confidence);
    printf("freq: %.1f MHz  az: %.1f el: %.1f  range: %.1f m\n", r->center_freq_hz/1e6, r->azimuth_deg, r->elevation_deg, r->range_m);
    printf("snr: %.1f dB  pri: %.2f ms  pw: %.2f us\n", r->snr_db, r->pri_ms, r->pulse_width_us);
    printf("tags: 0x%08x  action: %s\n", r->classification_tags, r->recommended_action);
    printf("=============================\n\n");
    // TODO: Add networking/IPC transport here, e.g., UDP send to display system.
}

/* ---------- 示例主循环（接收或生成输入） ---------- */
void simulate_input_and_process(int loops) {
    for (int i = 0; i < loops; ++i) {
        SignalInput in;
        memset(&in,0,sizeof(in));
        // simulate varying types
        if (i % 7 == 0) in.type = SIG_JAM;
        else if (i % 3 == 0) in.type = SIG_COMM;
        else in.type = SIG_RADAR;

        in.source_id = (uint32_t)(100 + i);
        in.timestamp_ms = now_ms();
        // set some typical values (vary by i)
        in.center_freq_hz = 3e9 + (i%10)*1e6; // 3 GHz +/- few MHz
        in.bandwidth_hz = (in.type==SIG_JAM) ? 5e6 : 1e6;
        in.signal_power_dbm = -20.0f + (i%5);
        in.snr_db = (in.type==SIG_JAM) ? 5.0f : 15.0f + (i%10);
        in.azimuth_deg = fmodf(10.0f * i, 360.0f);
        in.elevation_deg = 2.0f + (i%5);
        in.range_m = 1000.0f - (i*10);
        in.pri_ms = (in.type==SIG_RADAR) ? (5.0f + (i%10)) : 0.0f;
        in.pulse_width_us = (in.type==SIG_RADAR) ? (1.0f + (i%4)) : 0.0f;
        in.modulation = (in.type==SIG_COMM) ? MOD_PSK : MOD_NONE;

        // detection
        DetectionResult det; memset(&det,0,sizeof(det));
        detect_signal(&in, &det);
        if (!det.detected) {
            // nothing to report, but could log
            //printf("No detection for source %u (score %.2f)\n", in.source_id, det.detection_score);
            continue;
        }

        // classification + report
        ThreatReport rep; memset(&rep,0,sizeof(rep));
        build_report(&in, &det, &rep);

        // send/print
        send_report(&rep);

        // small sleep to simulate streaming (not strict)
        struct timespec ts = {0, 200 * 1000 * 1000}; // 200ms
        nanosleep(&ts, NULL);
    }
}

/* ---------- main ---------- */
int main(int argc, char **argv) {
    int loops = 20;
    if (argc > 1) loops = atoi(argv[1]);
    printf("Starting EW Simulation Processor, loops=%d\n", loops);
    simulate_input_and_process(loops);
    printf("Finished.\n");
    return 0;
}
