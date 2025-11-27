//
// Created by SanXiaoXing on 2025/11/27.
//

#ifndef WEAPON_PYLON_SIM_H
#define WEAPON_PYLON_SIM_H

#include <stdint.h>

//====================== 输入结构体 ============================//

typedef struct {
    uint8_t type;          // 1 byte
    uint8_t count;         // 1 byte
} WeaponInfo;

typedef struct {
    uint8_t pylon_id;
    float pitch;
    float roll;
    float max_load;
} PylonConfig;  // 16 bytes

typedef struct {
    uint32_t target_id;
    float distance;
    float azimuth;
    float elevation;
    float radial_speed;
} TargetInfo;   // 32 bytes

typedef struct {
    float time_to_go;
    float ballistic_angle;
    float launch_angle;
} FireControlInput;    // 32 bytes

typedef struct {
    uint8_t bind_cmd;
} WeaponBindCmd;

typedef struct {
    uint8_t roe_level;
    uint8_t fire_permission;
} ROEConfig;    // 8 bytes

typedef struct {
    uint8_t mode;
} SystemMode;

typedef struct {
    float pos_x, pos_y, pos_z;
    float vel_x, vel_y, vel_z;
    float roll, pitch, yaw;
} NavFlightData;   // 64 bytes

typedef struct {
    uint8_t status;
    float temperature;
    float voltage;
} PylonFeedback;   // 16 bytes


//======================== 输出结构体 ========================//

typedef struct {
    uint8_t intercept_enable;
    uint8_t intercept_mode;
} InterceptDecision;

typedef struct {
    float lead_angle;
    float launch_time;
    float intercept_time;
} InterceptParam;     // 32 bytes

typedef struct {
    uint8_t remain_ammo;
    uint8_t usable;
} AmmoStatus;         // 8 bytes

typedef struct {
    uint8_t pylon_ok;
    float health_index;
} PylonHealth;        // 16 bytes

typedef struct {
    uint8_t fire_cmd;
} WeaponFireCmd;

typedef struct {
    float fcs_time;
    float aim_angle;
    float fuse_delay;
} FCSOutput;          // 32 bytes

typedef struct {
    uint8_t level;
} ThreatWarning;

typedef struct {
    uint8_t error_code;
} SystemWarning;

typedef struct {
    float sync_time;
    uint8_t wpn_ready;
} SyncData;           // 32 bytes

typedef struct {
    uint8_t msg_type;
    char text[15];
} HMIFeedback;        // 16 bytes


//====================== 函数接口声明 ========================//

void WeaponPylon_Process();

#endif
