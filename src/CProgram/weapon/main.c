//
// Created by SanXiaoXing on 2025/11/27.
//
#include <stdio.h>
#include "weapon_pylon_sim.h"

// 输入数据（实际工程中来自总线/UDP/仿真系统）
WeaponInfo g_weapon;
TargetInfo g_target;
FireControlInput g_fcs_input;
NavFlightData g_nav;
PylonFeedback g_pylon_fb;

// 输出数据
InterceptDecision g_intercept_decision;
InterceptParam g_intercept_param;
AmmoStatus g_ammo_status;
WeaponFireCmd g_fire_cmd;

void calc_intercept_decision() {
    if (g_target.distance < 15000 && g_fcs_input.time_to_go > 0)
        g_intercept_decision.intercept_enable = 1;
    else
        g_intercept_decision.intercept_enable = 0;
}

void calc_intercept_param() {
    g_intercept_param.lead_angle = g_target.azimuth * 0.1f;
    g_intercept_param.launch_time = 1.2f;
    g_intercept_param.intercept_time = g_target.distance / 300.0f;
}

void calc_fire_command() {
    if (g_intercept_decision.intercept_enable && g_ammo_status.remain_ammo > 0)
        g_fire_cmd.fire_cmd = 1;
    else
        g_fire_cmd.fire_cmd = 0;
}

// 主处理流程
void WeaponPylon_Process() {
    calc_intercept_decision();
    calc_intercept_param();
    calc_fire_command();
}

int main() {
    g_weapon.type = 1;     // 导弹
    g_weapon.count = 2;

    g_target.distance = 12000.0f;
    g_target.azimuth = 30.0f;

    g_ammo_status.remain_ammo = 2;

    printf("Running Weapon Pylon Simulation...\n");

    WeaponPylon_Process();

    printf("Intercept Decision: %d\n", g_intercept_decision.intercept_enable);
    printf("Lead Angle: %.2f\n", g_intercept_param.lead_angle);
    printf("Fire Command: %d\n", g_fire_cmd.fire_cmd);

    return 0;
}
