//
// Created by SanXiaoXing on 2025/11/27.
//
/* display_sim.c
 *
 * 简单的综合显控数据处理仿真应用（示例实现）
 *
 * 功能：
 *  - 定义输入/输出结构体
 *  - 实现 process_frame() 以把传感器目标映射为动态符号，并输出若干数值/字符串
 *  - 包含一个简单的测试数据生成器和 main() 演示
 *
 * 说明：
 *  - 屏幕坐标定义为相对坐标 [0.0, 1.0]，(0,0) 左上角，(1,1) 右下角
 *  - map_target_to_symbol() 使用非常简化的投影：以方位角和俯仰角映射到屏幕偏移
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <math.h>
#include <time.h>

/* ===== 基本类型定义 ===== */
typedef double real_t;
typedef uint64_t u64;
typedef uint32_t u32;
typedef uint16_t u16;
typedef uint8_t  u8;
typedef int32_t  i32;

typedef struct {
    u64 sec;
    u32 usec;
} Timestamp;

/* ===== 输入结构体 ===== */

typedef struct {
    Timestamp ts;
    real_t latitude_deg;
    real_t longitude_deg;
    real_t altitude_m;
    real_t roll_deg;
    real_t pitch_deg;
    real_t yaw_deg;
    real_t vel_n_mps;
    real_t vel_e_mps;
    real_t vel_d_mps;
    int status; // 0 invalid, 1 valid
} INS_Data;

typedef struct {
    Timestamp ts;
    int com1_lock;
    int nav1_lock;
    real_t radio_alt_m;
    char active_freq_str[32];
} Radio_Data;

typedef struct {
    Timestamp ts;
    real_t pressure_hpa;
    real_t temperature_c;
    real_t wind_speed_mps;
    real_t wind_dir_deg;
    real_t density_kg_m3;
} Atmosphere_Data;

typedef struct {
    Timestamp ts;
    real_t airspeed_mps;
    real_t mach;
    real_t g_load;
    real_t fuel_percent;
    int on_ground;
    int parking_brake;
} Aircraft_State;

typedef enum { SENSOR_RADAR=0, SENSOR_DAS=1, SENSOR_IR=2 } SensorType;
typedef struct {
    u32 target_id;
    SensorType sensor;
    Timestamp ts;
    real_t range_m;
    real_t azimuth_deg;   // 相对机头，右为正
    real_t elevation_deg; // 正为上仰
    real_t rcs_dbsm;
    real_t track_covariance[3];
    int track_status;     // 0=lost,1=tentative,2=track
} Sensor_Target;

#define MAX_TARGETS 128
typedef struct {
    Timestamp ts;
    u16 target_count;
    Sensor_Target targets[MAX_TARGETS];
} Sensor_Target_List;

typedef struct {
    Timestamp ts;
    int master_arm;
    int selected_weapon_type;
    u16 weapon_count;
    struct {
        u32 id;
        int status;
        real_t remaining_sec;
    } stores[32];
} Weapon_Status;

typedef struct {
    Timestamp ts;
    INS_Data ins;
    Radio_Data radio;
    Atmosphere_Data atmos;
    Aircraft_State ac_state;
    Sensor_Target_List sensor_targets;
    Weapon_Status weapon;
} Inputs_Packet;

/* ===== 输出结构体 ===== */

typedef struct { real_t x; real_t y; } ScreenPos;
typedef enum { SYM_STYLE_NORMAL=0, SYM_STYLE_FLASH=1, SYM_STYLE_DIM=2 } SymbolStyle;

typedef struct {
    u32 symbol_id;
    ScreenPos pos;
    int visible;
    int flash_enable;
    real_t flash_rate_hz;
    SymbolStyle style;
    real_t scale;
} Dynamic_Symbol;

typedef struct {
    u32 field_id;
    int valid;
    real_t value;
    char units[8];
    ScreenPos pos;
    int decimal_places;
} Numeric_Symbol;

typedef struct {
    u32 field_id;
    int valid;
    char text[64];
    ScreenPos pos;
    int font_size;
} String_Symbol;

#define MAX_DYNAMIC_SYMBOLS 256
#define MAX_NUMERIC_SYMBOLS 64
#define MAX_STRING_SYMBOLS  64

typedef struct {
    Timestamp ts;
    u16 page_number;
    u16 dyn_count;
    Dynamic_Symbol dyn_symbols[MAX_DYNAMIC_SYMBOLS];
    u16 num_count;
    Numeric_Symbol num_symbols[MAX_NUMERIC_SYMBOLS];
    u16 str_count;
    String_Symbol str_symbols[MAX_STRING_SYMBOLS];
} Outputs_Packet;

/* ===== 函数原型 ===== */
int display_sim_init(void);
void outputs_reset(Outputs_Packet *out);
int map_target_to_symbol(const Sensor_Target *t, const Inputs_Packet *in, Dynamic_Symbol *sym);
int process_frame(const Inputs_Packet *in, Outputs_Packet *out);
void display_sim_shutdown(void);

/* ===== 实现 ===== */

int display_sim_init(void) {
    /* 如需初始化符号库 / 日志 / 资源可在此扩展 */
    return 0;
}

void outputs_reset(Outputs_Packet *out) {
    if (!out) return;
    memset(out, 0, sizeof(Outputs_Packet));
    out->page_number = 0;
}

/* 简化投影：把相对方位角与仰角映射到屏幕坐标
 *
 * 说明：
 *  - 假定视场（FOV）：水平 +/- 60 度，垂直 +/- 30 度（可根据 HUD 调整）
 *  - x = 0.5 + azimuth / (2*FOV_H)
 *  - y = 0.5 - elevation / (2*FOV_V)
 *  - 若在视场外则 visible = 0
 *
 * 这里仅为示例，真实系统应使用姿态矩阵、相机投影等。
 */
int map_target_to_symbol(const Sensor_Target *t, const Inputs_Packet *in, Dynamic_Symbol *sym) {
    if (!t || !sym) return -1;

    const real_t FOV_H_DEG = 60.0; // 每侧
    const real_t FOV_V_DEG = 30.0; // 每侧

    real_t az = t->azimuth_deg;      // 右为正
    real_t el = t->elevation_deg;    // 上为正

    // 判断视场内外
    if (az < -FOV_H_DEG || az > FOV_H_DEG || el < -FOV_V_DEG || el > FOV_V_DEG) {
        sym->visible = 0;
    } else {
        sym->visible = 1;
    }

    // 简单线性投影
    sym->pos.x = 0.5 + (az / (2.0 * FOV_H_DEG));   // map [-FOV_H,FOV_H] -> [0,1]
    sym->pos.y = 0.5 - (el / (2.0 * FOV_V_DEG));   // map [-FOV_V,FOV_V] -> [0,1] (y downward)

    // clamp
    if (sym->pos.x < 0.0) sym->pos.x = 0.0;
    if (sym->pos.x > 1.0) sym->pos.x = 1.0;
    if (sym->pos.y < 0.0) sym->pos.y = 0.0;
    if (sym->pos.y > 1.0) sym->pos.y = 1.0;

    // symbol id: 根据传感器和状态选择不同图标（示例）
    if (t->sensor == SENSOR_RADAR) sym->symbol_id = 100; // radar contact
    else if (t->sensor == SENSOR_IR) sym->symbol_id = 120; // IR contact
    else sym->symbol_id = 110; // generic

    // flash when tentative
    sym->flash_enable = (t->track_status == 1) ? 1 : 0;
    sym->flash_rate_hz = (sym->flash_enable) ? 1.0 : 0.0;
    sym->style = (t->track_status == 2) ? SYM_STYLE_NORMAL : SYM_STYLE_FLASH;
    sym->scale = 1.0;
    return 0;
}

/* 处理每帧输入 -> 生成输出 */
int process_frame(const Inputs_Packet *in, Outputs_Packet *out) {
    if (!in || !out) return -1;
    outputs_reset(out);
    out->ts = in->ts;

    // 1) 选择画面号（简单策略）
    if (in->weapon.master_arm && in->weapon.weapon_count > 0) out->page_number = 3;
    else if (!in->ac_state.on_ground) out->page_number = 1;
    else out->page_number = 0;

    // 2) 基本数值：高度(米)，空速(m/s->kts)，航向
    if (in->ins.status == 1) {
        Numeric_Symbol alt = { .field_id=1, .valid=1, .value=in->ins.altitude_m, .pos={0.92,0.12}, .decimal_places=0 };
        strncpy(alt.units, "m", sizeof(alt.units)-1);
        out->num_symbols[out->num_count++] = alt;

        // convert m/s to knots (~1 m/s = 1.943844 knots)
        Numeric_Symbol spd = { .field_id=2, .valid=1, .value=in->ac_state.airspeed_mps * 1.943844, .pos={0.92,0.20}, .decimal_places=1 };
        strncpy(spd.units, "kts", sizeof(spd.units)-1);
        out->num_symbols[out->num_count++] = spd;

        Numeric_Symbol hdg = { .field_id=3, .valid=1, .value=in->ins.yaw_deg, .pos={0.92,0.28}, .decimal_places=0 };
        strncpy(hdg.units, "deg", sizeof(hdg.units)-1);
        out->num_symbols[out->num_count++] = hdg;
    } else {
        Numeric_Symbol invalid_alt = { .field_id=1, .valid=0, .value=0.0, .pos={0.92,0.12}, .decimal_places=0 };
        out->num_symbols[out->num_count++] = invalid_alt;
    }

    // 3) 把目标映射为动态符号
    for (u16 i = 0; i < in->sensor_targets.target_count && out->dyn_count < MAX_DYNAMIC_SYMBOLS; ++i) {
        Dynamic_Symbol sym;
        memset(&sym, 0, sizeof(sym));
        if (map_target_to_symbol(&in->sensor_targets.targets[i], in, &sym) == 0 && sym.visible) {
            out->dyn_symbols[out->dyn_count++] = sym;
        }
    }

    // 4) 告警/提示（示例）
    if (in->weapon.master_arm && in->weapon.weapon_count == 0) {
        String_Symbol s;
        memset(&s, 0, sizeof(s));
        s.field_id = 10;
        s.valid = 1;
        strncpy(s.text, "WEAPON ARMED - NO STORES", sizeof(s.text)-1);
        s.pos.x = 0.5; s.pos.y = 0.04;
        s.font_size = 14;
        out->str_symbols[out->str_count++] = s;
    }

    // 5) 其它状态文本示例：燃油低
    if (in->ac_state.fuel_percent < 20.0) {
        String_Symbol s2;
        memset(&s2, 0, sizeof(s2));
        s2.field_id = 11;
        s2.valid = 1;
        snprintf(s2.text, sizeof(s2.text), "FUEL LOW: %.1f%%", in->ac_state.fuel_percent);
        s2.pos.x = 0.5; s2.pos.y = 0.07;
        s2.font_size = 12;
        out->str_symbols[out->str_count++] = s2;
    }

    return 0;
}

void display_sim_shutdown(void) {
    /* 释放资源（若有） */
}

/* ===== 测试数据生成器 ===== */
static Timestamp make_timestamp_now(void) {
    Timestamp t;
    struct timespec ts;
    clock_gettime(CLOCK_REALTIME, &ts);
    t.sec = (u64)ts.tv_sec;
    t.usec = (u32)(ts.tv_nsec / 1000);
    return t;
}

void generate_sample_inputs(Inputs_Packet *in) {
    if (!in) return;
    memset(in, 0, sizeof(Inputs_Packet));
    in->ts = make_timestamp_now();

    // INS
    in->ins.ts = in->ts;
    in->ins.latitude_deg = 30.0;
    in->ins.longitude_deg = 114.0;
    in->ins.altitude_m = 4500.0;
    in->ins.roll_deg = 2.0;
    in->ins.pitch_deg = 1.0;
    in->ins.yaw_deg = 85.0;
    in->ins.vel_n_mps = 100.0;
    in->ins.vel_e_mps = 3.0;
    in->ins.vel_d_mps = -1.2;
    in->ins.status = 1;

    // Radio
    in->radio.ts = in->ts;
    in->radio.com1_lock = 1;
    in->radio.nav1_lock = 1;
    in->radio.radio_alt_m = 120.0;
    strncpy(in->radio.active_freq_str, "118.300", sizeof(in->radio.active_freq_str)-1);

    // Atmosphere
    in->atmos.ts = in->ts;
    in->atmos.pressure_hpa = 1013.25;
    in->atmos.temperature_c = 5.0;
    in->atmos.wind_speed_mps = 8.0;
    in->atmos.wind_dir_deg = 270.0;
    in->atmos.density_kg_m3 = 1.225;

    // Aircraft state
    in->ac_state.ts = in->ts;
    in->ac_state.airspeed_mps = 220.0 / 3.6; // km/h -> m/s (approx)
    in->ac_state.mach = 0.5;
    in->ac_state.g_load = 1.0;
    in->ac_state.fuel_percent = 45.0;
    in->ac_state.on_ground = 0;
    in->ac_state.parking_brake = 0;

    // Weapon status
    in->weapon.ts = in->ts;
    in->weapon.master_arm = 1;
    in->weapon.selected_weapon_type = 1;
    in->weapon.weapon_count = 0; // 触发无弹提示

    // Sensor targets（几个示例目标）
    in->sensor_targets.ts = in->ts;
    in->sensor_targets.target_count = 4;
    // Target 1: ahead, slight right
    in->sensor_targets.targets[0].target_id = 1;
    in->sensor_targets.targets[0].sensor = SENSOR_RADAR;
    in->sensor_targets.targets[0].ts = in->ts;
    in->sensor_targets.targets[0].range_m = 15000.0;
    in->sensor_targets.targets[0].azimuth_deg = 5.0;
    in->sensor_targets.targets[0].elevation_deg = -1.0;
    in->sensor_targets.targets[0].track_status = 2;

    // Target 2: right, tentative
    in->sensor_targets.targets[1].target_id = 2;
    in->sensor_targets.targets[1].sensor = SENSOR_IR;
    in->sensor_targets.targets[1].ts = in->ts;
    in->sensor_targets.targets[1].range_m = 8000.0;
    in->sensor_targets.targets[1].azimuth_deg = 22.0;
    in->sensor_targets.targets[1].elevation_deg = 2.0;
    in->sensor_targets.targets[1].track_status = 1;

    // Target 3: left, out of FOV (will be filtered)
    in->sensor_targets.targets[2].target_id = 3;
    in->sensor_targets.targets[2].sensor = SENSOR_DAS;
    in->sensor_targets.targets[2].ts = in->ts;
    in->sensor_targets.targets[2].range_m = 22000.0;
    in->sensor_targets.targets[2].azimuth_deg = -75.0; // out of FOV
    in->sensor_targets.targets[2].elevation_deg = 0.0;
    in->sensor_targets.targets[2].track_status = 2;

    // Target 4: above-right
    in->sensor_targets.targets[3].target_id = 4;
    in->sensor_targets.targets[3].sensor = SENSOR_RADAR;
    in->sensor_targets.targets[3].ts = in->ts;
    in->sensor_targets.targets[3].range_m = 5000.0;
    in->sensor_targets.targets[3].azimuth_deg = 40.0; // near edge
    in->sensor_targets.targets[3].elevation_deg = 10.0;
    in->sensor_targets.targets[3].track_status = 2;
}

/* ===== 输出打印函数（便于观察） ===== */
void print_outputs(const Outputs_Packet *out) {
    if (!out) return;
    printf("=== Outputs Packet ===\n");
    printf("Timestamp: %llu.%06u\n", (unsigned long long)out->ts.sec, (unsigned)out->ts.usec);
    printf("Page number: %u\n", out->page_number);
    printf("\n-- Numeric Symbols (%u) --\n", out->num_count);
    for (u16 i = 0; i < out->num_count; ++i) {
        const Numeric_Symbol *n = &out->num_symbols[i];
        if (n->valid) {
            printf("Field %u: %. *s%.*f %s @ (%.3f,%.3f)\n",
                   n->field_id,
                   n->decimal_places, "", n->decimal_places, n->value,
                   n->units,
                   n->pos.x, n->pos.y);
            // above uses a trick to print decimal_places controlled; fallback easier:
            // But to keep portable, do explicit formatting:
            // printf("Field %u: value=%.2f %s pos=(%.3f,%.3f)\n", n->field_id, n->value, n->units, n->pos.x, n->pos.y);
        } else {
            printf("Field %u: INVALID\n", n->field_id);
        }
    }

    printf("\n-- Dynamic Symbols (%u) --\n", out->dyn_count);
    for (u16 i = 0; i < out->dyn_count; ++i) {
        const Dynamic_Symbol *d = &out->dyn_symbols[i];
        printf("SymID %u at (%.3f,%.3f) visible=%d flash=%d style=%d scale=%.2f\n",
               d->symbol_id, d->pos.x, d->pos.y, d->visible, d->flash_enable, d->style, d->scale);
    }

    printf("\n-- String Symbols (%u) --\n", out->str_count);
    for (u16 i = 0; i < out->str_count; ++i) {
        const String_Symbol *s = &out->str_symbols[i];
        printf("TextID %u: \"%s\" @ (%.3f,%.3f)\n", s->field_id, s->text, s->pos.x, s->pos.y);
    }
    printf("======================\n");
}

/* ===== main 测试入口 ===== */
int main(int argc, char **argv) {
    (void)argc; (void)argv;
    if (display_sim_init() != 0) {
        fprintf(stderr, "Init failed\n");
        return 1;
    }

    Inputs_Packet in;
    Outputs_Packet out;

    generate_sample_inputs(&in);

    if (process_frame(&in, &out) != 0) {
        fprintf(stderr, "process_frame failed\n");
        return 2;
    }

    print_outputs(&out);

    display_sim_shutdown();
    return 0;
}
