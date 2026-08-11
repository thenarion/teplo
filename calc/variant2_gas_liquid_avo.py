from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Tuple


class CalcError(Exception):
    """Ошибка исходных данных или невозможный режим."""


# ------------------------------------------------------------------
# Упрощённые справочные данные по водным растворам гликолей.
# Концентрация указана в массовых процентах.
# Значения приближённые, только для предварительного расчёта.
# ------------------------------------------------------------------
_FREEZE_TABLES = {
    "Этиленгликоль": [
        (0.0, 0.0),
        (10.0, -3.5),
        (20.0, -8.5),
        (30.0, -15.0),
        (40.0, -24.0),
        (50.0, -36.0),
        (60.0, -49.0),
        (70.0, -55.0),
        (80.0, -47.0),
        (90.0, -29.0),
        (100.0, -13.0),
    ],
    "Пропиленгликоль": [
        (0.0, 0.0),
        (10.0, -3.0),
        (20.0, -8.0),
        (30.0, -14.0),
        (40.0, -22.0),
        (50.0, -34.0),
        (60.0, -47.0),
        (70.0, -54.0),
        (80.0, -57.0),
        (90.0, -58.5),
        (100.0, -59.0),
    ],
}

_PURE_DENSITY20 = {
    "Этиленгликоль": 1113.0,
    "Пропиленгликоль": 1036.0,
}

_PURE_CP = {
    "Этиленгликоль": 2.40,
    "Пропиленгликоль": 2.48,
}

_PURE_MU20_MPAS = {
    "Этиленгликоль": 16.0,
    "Пропиленгликоль": 48.0,
}


@dataclass
class Variant2Inputs:
    # Общие газовые исходные данные
    t_gas_in_c: float
    gas_flow_nm3h: float
    t_amb_c: float
    leakage_pct: float
    t_gas_out_c: float

    # Жидкостной контур
    t_liq_in_c: float
    t_liq_out_c: float

    # База подсоса
    leakage_basis: str = "Объём (н.у.)"

    # Выбор гликоля
    fluid_type: str = "Этиленгликоль"
    concentration_mode: str = "Автоматически по минимальной температуре"
    manual_concentration_pct: float = 40.0
    design_min_temp_c: float = -20.0
    freeze_safety_k: float = 3.0

    # Свойства газов и воздуха
    cp_gas_kjkgk: float = 1.08
    cp_air_kjkgk: float = 1.005
    rho_gas_n_kgm3: float = 1.30
    rho_air_n_kgm3: float = 1.293

    # Газо-жидкостный теплообменник на печи
    U_gas_liquid_Wm2K: float = 80.0
    lmtd_correction_gas_liquid: float = 0.95
    target_gas_velocity_ms: float = 12.0
    tube_od_mm: float = 32.0
    tube_wall_mm: float = 2.0
    tube_max_length_m: float = 3.0
    tube_min_length_m: float = 0.5
    pitch_ratio: float = 1.30
    layout_eff: float = 0.85
    shell_thickness_mm: float = 4.0
    tubesheet_thickness_mm: float = 20.0
    mass_factor: float = 1.25
    steel_density: float = 7850.0

    # Насос
    pump_dp_kpa: float = 150.0
    pump_eff: float = 0.60
    pump_motor_margin: float = 1.15

    # АВО
    U_avo_Wm2K: float = 30.0
    lmtd_correction_avo: float = 0.90
    avo_air_dt_c: float = 15.0
    avo_face_velocity_ms: float = 2.5
    avo_dp_pa: float = 250.0
    avo_fan_eff: float = 0.60
    avo_motor_margin: float = 1.15

    # Конструкция АВО, упрощённо
    fin_area_per_m: float = 20.0
    avo_specific_volume_m3_per_m2: float = 0.003
    avo_specific_mass_kg_per_m2: float = 12.0
    target_liquid_velocity_ms: float = 1.5
    avo_tube_od_mm: float = 25.0
    avo_tube_wall_mm: float = 2.0
    avo_min_tube_length_m: float = 0.5
    avo_max_tube_length_m: float = 3.0


@dataclass
class Variant2Result:
    messages: List[str] = field(default_factory=list)

    heat_duty_kw: float = 0.0
    t_gas_after_leak_c: float = 0.0
    t_gas_out_c: float = 0.0
    t_liq_in_c: float = 0.0
    t_liq_out_c: float = 0.0

    fluid_type: str = ""
    selected_concentration_pct: float = 0.0
    recommended_concentration_pct: float = 0.0
    freeze_point_selected_c: float = 0.0
    recommendation_text: str = ""

    liq_density_kgm3: float = 0.0
    liq_cp_kjkgk: float = 0.0
    liq_viscosity_mpas: float = 0.0
    liq_mass_flow_kgs: float = 0.0
    liq_volume_flow_m3h: float = 0.0

    # Газо-жидкостный ТО на печи
    gl_area_req_m2: float = 0.0
    gl_area_provided_m2: float = 0.0
    gl_lmtd_k: float = 0.0
    gl_U_Wm2K: float = 0.0
    gl_shell_diameter_m: float = 0.0
    gl_length_overall_m: float = 0.0
    gl_mass_t: float = 0.0
    gl_gas_velocity_ms: float = 0.0
    gl_gas_pressure_drop_pa: float = 0.0
    gl_n_tubes: int = 0
    gl_tube_length_m: float = 0.0

    # Насос
    pump_dp_kpa: float = 0.0
    pump_hydraulic_kw: float = 0.0
    pump_shaft_kw: float = 0.0
    pump_motor_kw: float = 0.0

    # АВО
    avo_area_req_m2: float = 0.0
    avo_area_provided_m2: float = 0.0
    avo_lmtd_k: float = 0.0
    avo_U_Wm2K: float = 0.0
    avo_air_mass_flow_kgs: float = 0.0
    avo_air_volume_flow_m3h: float = 0.0
    avo_air_out_c: float = 0.0
    avo_fan_shaft_kw: float = 0.0
    avo_fan_motor_kw: float = 0.0
    avo_face_area_m2: float = 0.0
    avo_front_side_m: float = 0.0
    avo_depth_m: float = 0.0
    avo_volume_m3: float = 0.0
    avo_mass_t: float = 0.0
    avo_n_tubes: int = 0
    avo_tube_length_m: float = 0.0
    avo_liquid_velocity_ms: float = 0.0

    total_mass_t: float = 0.0
    total_power_kw: float = 0.0


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _interp_table(table: List[Tuple[float, float]], x: float) -> float:
    if x <= table[0][0]:
        return table[0][1]
    if x >= table[-1][0]:
        return table[-1][1]

    for i in range(1, len(table)):
        x0, y0 = table[i - 1]
        x1, y1 = table[i]
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)

    return table[-1][1]


def glycol_freeze_point(fluid_type: str, concentration_pct: float) -> float:
    if fluid_type not in _FREEZE_TABLES:
        raise CalcError(f"Неизвестный теплоноситель: {fluid_type}")

    c = _clamp(concentration_pct, 0.0, 100.0)
    return _interp_table(_FREEZE_TABLES[fluid_type], c)


def glycol_properties(fluid_type: str, concentration_pct: float, t_c: float) -> dict:
    """
    Очень приближённые свойства водного раствора гликоля:
    - плотность, кг/м³;
    - cp, кДж/(кг·K);
    - вязкость, мПа·с;
    - температура замерзания, °C.
    """
    if fluid_type not in _FREEZE_TABLES:
        raise CalcError(f"Неизвестный теплоноситель: {fluid_type}")

    c = _clamp(concentration_pct, 0.0, 100.0)
    w = c / 100.0

    freeze_c = _interp_table(_FREEZE_TABLES[fluid_type], c)

    # Плотность: линейное смешение воды и чистого гликоля с температурной поправкой.
    rho_water = max(900.0, 1000.0 - 0.2 * (t_c - 20.0))
    rho_glycol = max(800.0, _PURE_DENSITY20[fluid_type] - 0.6 * (t_c - 20.0))
    rho = (1.0 - w) * rho_water + w * rho_glycol

    # Теплоёмкость: линейное смешение, cp слегка растёт с температурой.
    cp_water = 4.18 + 0.001 * (t_c - 20.0)
    cp_glycol = _PURE_CP[fluid_type] + 0.002 * (t_c - 20.0)
    cp = (1.0 - w) * cp_water + w * cp_glycol

    # Вязкость: логарифмическое смешение + условный избыточный вклад.
    mu_water_mpas = max(0.05, 1.0 * math.exp(-0.02 * (t_c - 20.0)))
    mu_glycol_mpas = max(0.2, _PURE_MU20_MPAS[fluid_type] * math.exp(-0.03 * (t_c - 20.0)))

    ln_mu = w * math.log(mu_glycol_mpas) + (1.0 - w) * math.log(mu_water_mpas)
    mu_mpas = math.exp(ln_mu) * (1.0 + 1.5 * w * (1.0 - w))

    return {
        "freeze_c": freeze_c,
        "rho_kgm3": rho,
        "cp_kjkgk": cp,
        "mu_mpas": mu_mpas,
    }


def recommend_glycol_concentration(
    fluid_type: str,
    design_min_temp_c: float,
    safety_k: float = 3.0,
) -> Tuple[float, float, str]:
    """
    Подбирает минимальную массовую концентрацию гликоля,
    чтобы температура замерзания была не выше:
        design_min_temp_c - safety_k
    """
    if fluid_type not in _FREEZE_TABLES:
        raise CalcError(f"Неизвестный теплоноситель: {fluid_type}")

    target_freeze_c = design_min_temp_c - safety_k

    if target_freeze_c >= 0.0:
        fp = glycol_freeze_point(fluid_type, 0.0)
        text = (
            "Для положительных минимальных температур антифриз формально не требуется. "
            "Можно использовать воду с ингибиторами коррозии, но для резервных режимов "
            "лучше проверить риск заморозки отдельно."
        )
        return 0.0, fp, text

    best_conc = None
    c = 0.0
    while c <= 100.0 + 1e-6:
        fp = glycol_freeze_point(fluid_type, c)
        if fp <= target_freeze_c:
            best_conc = c
            break
        c += 0.5

    if best_conc is not None:
        fp = glycol_freeze_point(fluid_type, best_conc)
        text = (
            f"Для {fluid_type.lower()} рекомендуется массовая концентрация около {best_conc:.0f} %. "
            f"Расчётная температура замерзания раствора около {fp:.1f} °C "
            f"при требуемой минимальной температуре {design_min_temp_c:.1f} °C "
            f"и запасе {safety_k:.1f} K."
        )
        return best_conc, fp, text

    # Если не нашли, ищем концентрацию с минимальной температурой замерзания.
    min_fp = 1e9
    min_c = 0.0
    c = 0.0
    while c <= 100.0 + 1e-6:
        fp = glycol_freeze_point(fluid_type, c)
        if fp < min_fp:
            min_fp = fp
            min_c = c
        c += 0.5

    text = (
        f"Не удаётся обеспечить требуемое значение {target_freeze_c:.1f} °C для {fluid_type.lower()}. "
        f"Минимальная расчётная температура замерзания около {min_fp:.1f} °C при концентрации {min_c:.0f} %. "
        "Рассмотрите другой теплоноситель, увеличение запаса или иную схему."
    )
    return min_c, min_fp, text


def _lmtd(dt_hot_end: float, dt_cold_end: float) -> float:
    if dt_hot_end <= 0.0 or dt_cold_end <= 0.0:
        raise CalcError(
            "Температурный напор на концах теплообменника должен быть положительным. "
            "Проверьте температуры потоков."
        )

    if abs(dt_hot_end - dt_cold_end) < 1e-6:
        return dt_hot_end

    return (dt_hot_end - dt_cold_end) / math.log(dt_hot_end / dt_cold_end)


def _sutherland_viscosity_air_like(t_k: float) -> float:
    mu0 = 1.716e-5
    t0 = 273.15
    s = 110.4
    return mu0 * (t_k / t0) ** 1.5 * (t0 + s) / (t_k + s)


def calculate_variant2(inp: Variant2Inputs) -> Variant2Result:
    messages: List[str] = []

    # ------------------------------------------------------------------
    # 1. Проверки исходных данных
    # ------------------------------------------------------------------
    if inp.gas_flow_nm3h <= 0.0:
        raise CalcError("Расход дымовых газов должен быть больше нуля.")

    if inp.U_gas_liquid_Wm2K <= 0.0 or inp.U_avo_Wm2K <= 0.0:
        raise CalcError("Коэффициенты теплопередачи должны быть больше нуля.")

    if inp.cp_gas_kjkgk <= 0.0 or inp.cp_air_kjkgk <= 0.0:
        raise CalcError("Теплоёмкости газов и воздуха должны быть больше нуля.")

    if inp.rho_gas_n_kgm3 <= 0.0 or inp.rho_air_n_kgm3 <= 0.0:
        raise CalcError("Плотности при нормальных условиях должны быть больше нуля.")

    if inp.leakage_pct < 0.0:
        raise CalcError("Подсос воздуха не может быть отрицательным.")

    if inp.t_liq_out_c <= inp.t_liq_in_c:
        raise CalcError("Температура жидкости на выходе из ТО должна быть выше температуры на входе.")

    if inp.t_amb_c >= inp.t_liq_in_c:
        raise CalcError(
            "Температура жидкости на входе в газо-жидкостный ТО должна быть выше температуры окружающей среды, "
            "иначе АВО без холодильной машины не сможет охладить жидкость до такой температуры."
        )

    if inp.t_liq_in_c - inp.t_amb_c < 3.0:
        messages.append(
            "Очень малый подход между температурой жидкости после АВО и температурой окружающей среды (< 3 K). "
            "Площадь АВО будет резко расти."
        )

    if inp.avo_air_dt_c <= 0.0:
        raise CalcError("Нагрев воздуха в АВО должен быть больше нуля.")

    if inp.avo_face_velocity_ms <= 0.0:
        raise CalcError("Скорость воздуха во фронте АВО должна быть больше нуля.")

    if inp.fin_area_per_m <= 0.0:
        raise CalcError("Удельная площадь оребрения должна быть больше нуля.")

    if inp.pump_eff <= 0.0 or inp.pump_eff > 1.0:
        raise CalcError("КПД насоса должен быть в диапазоне от 0 до 1.")

    if inp.avo_fan_eff <= 0.0 or inp.avo_fan_eff > 1.0:
        raise CalcError("КПД вентилятора АВО должен быть в диапазоне от 0 до 1.")

    if inp.lmtd_correction_gas_liquid <= 0.0 or inp.lmtd_correction_gas_liquid > 1.0:
        raise CalcError("Поправка LMTD для газо-жидкостного ТО должна быть в диапазоне от 0 до 1.")

    if inp.lmtd_correction_avo <= 0.0 or inp.lmtd_correction_avo > 1.0:
        raise CalcError("Поправка LMTD для АВО должна быть в диапазоне от 0 до 1.")

    if inp.tube_od_mm <= 2.0 * inp.tube_wall_mm:
        raise CalcError("Толщина стенки труб газо-жидкостного ТО слишком большая.")

    if inp.avo_tube_od_mm <= 2.0 * inp.avo_tube_wall_mm:
        raise CalcError("Толщина стенки труб АВО слишком большая.")

    if inp.tube_min_length_m <= 0.0 or inp.tube_max_length_m < inp.tube_min_length_m:
        raise CalcError("Длины труб газо-жидкостного ТО заданы некорректно.")

    if inp.avo_min_tube_length_m <= 0.0 or inp.avo_max_tube_length_m < inp.avo_min_tube_length_m:
        raise CalcError("Длины труб АВО заданы некорректно.")

    if inp.fluid_type not in _FREEZE_TABLES:
        raise CalcError("Допустимые теплоносители: Этиленгликоль, Пропиленгликоль.")

    # ------------------------------------------------------------------
    # 2. Подсос воздуха и температура газов перед ТО
    # ------------------------------------------------------------------
    T0 = 273.15

    Vg_n = inp.gas_flow_nm3h / 3600.0
    m_g = Vg_n * inp.rho_gas_n_kgm3

    if inp.leakage_basis == "Объём (н.у.)":
        V_leak_n = Vg_n * inp.leakage_pct / 100.0
        m_leak = V_leak_n * inp.rho_air_n_kgm3
    elif inp.leakage_basis == "Масса":
        m_leak = m_g * inp.leakage_pct / 100.0
        V_leak_n = m_leak / inp.rho_air_n_kgm3
    else:
        raise CalcError("Неверно задана база подсоса: используйте 'Объём (н.у.)' или 'Масса'.")

    m_h = m_g + m_leak
    V_total_n = Vg_n + V_leak_n
    rho_mix_n = m_h / V_total_n if V_total_n > 0.0 else inp.rho_gas_n_kgm3

    T_g_K = inp.t_gas_in_c + T0
    T_amb_K = inp.t_amb_c + T0

    denom_cp = m_g * inp.cp_gas_kjkgk + m_leak * inp.cp_air_kjkgk
    if denom_cp <= 0.0:
        raise CalcError("Некорректный тепловой баланс смешения газов и подсоса.")

    T_mix_K = (
        m_g * inp.cp_gas_kjkgk * T_g_K + m_leak * inp.cp_air_kjkgk * T_amb_K
    ) / denom_cp

    T_mix_C = T_mix_K - T0
    cp_hot = denom_cp / m_h

    if T_mix_C <= inp.t_amb_c:
        raise CalcError("Температура газов после подсоса получилась не выше температуры окружающей среды.")

    if inp.t_gas_out_c >= T_mix_C:
        raise CalcError("Температура газов после ТО должна быть ниже температуры газов после подсоса.")

    if inp.t_gas_out_c <= inp.t_amb_c:
        raise CalcError("Температура газов после ТО должна быть выше температуры окружающей среды.")

    if inp.t_liq_out_c >= T_mix_C:
        raise CalcError("Температура жидкости на выходе из ТО должна быть ниже температуры газов после подсоса.")

    if inp.t_gas_out_c <= inp.t_liq_in_c:
        raise CalcError(
            "Температура газов на выходе из газо-жидкостного ТО должна быть выше температуры жидкости на входе."
        )

    # ------------------------------------------------------------------
    # 3. Концентрация гликоля
    # ------------------------------------------------------------------
    recommended_conc, recommended_fp, recommendation_text = recommend_glycol_concentration(
        fluid_type=inp.fluid_type,
        design_min_temp_c=inp.design_min_temp_c,
        safety_k=inp.freeze_safety_k,
    )

    if inp.concentration_mode == "Автоматически по минимальной температуре":
        selected_conc = recommended_conc
    elif inp.concentration_mode == "Вручную":
        selected_conc = _clamp(inp.manual_concentration_pct, 0.0, 100.0)
    else:
        raise CalcError("Неверный режим выбора концентрации.")

    selected_freeze = glycol_freeze_point(inp.fluid_type, selected_conc)
    target_freeze = inp.design_min_temp_c - inp.freeze_safety_k

    if selected_freeze > target_freeze:
        messages.append(
            f"Выбранная концентрация {selected_conc:.0f} % может быть недостаточной: "
            f"температура замерзания около {selected_freeze:.1f} °C, "
            f"а требуемое значение не выше {target_freeze:.1f} °C."
        )

    if inp.fluid_type == "Этиленгликоль":
        messages.append(
            "Этиленгликоль токсичен. Для общественных, жилых и пищевых контуров обычно предпочтительнее пропиленгликоль."
        )

    # ------------------------------------------------------------------
    # 4. Тепловая нагрузка и расход жидкости
    # ------------------------------------------------------------------
    Q_kW = m_h * cp_hot * (T_mix_C - inp.t_gas_out_c)
    if Q_kW <= 0.0:
        raise CalcError("Получена неположительная тепловая нагрузка.")

    t_liq_mean_c = 0.5 * (inp.t_liq_in_c + inp.t_liq_out_c)
    props = glycol_properties(inp.fluid_type, selected_conc, t_liq_mean_c)

    rho_liq = props["rho_kgm3"]
    cp_liq = props["cp_kjkgk"]
    mu_liq_mpas = props["mu_mpas"]

    dt_liq = inp.t_liq_out_c - inp.t_liq_in_c
    if dt_liq <= 0.0 or cp_liq <= 0.0:
        raise CalcError("Некорректный температурный перепад или теплоёмкость жидкости.")

    m_liq = Q_kW / (cp_liq * dt_liq)
    V_liq = m_liq / rho_liq
    V_liq_h = V_liq * 3600.0

    # ------------------------------------------------------------------
    # 5. Газо-жидкостный ТО на печи: LMTD и площадь
    # ------------------------------------------------------------------
    dt_hot_end_gl = T_mix_C - inp.t_liq_out_c
    dt_cold_end_gl = inp.t_gas_out_c - inp.t_liq_in_c
    lmtd_gl = _lmtd(dt_hot_end_gl, dt_cold_end_gl)

    Q_W = Q_kW * 1000.0
    UA_gl = Q_W / (inp.lmtd_correction_gas_liquid * lmtd_gl)
    area_gl_req = UA_gl / inp.U_gas_liquid_Wm2K

    # ------------------------------------------------------------------
    # 6. Фактические объёмы газов и геометрия газо-жидкостного ТО
    # ------------------------------------------------------------------
    T_gas_out_K = inp.t_gas_out_c + T0
    rho_gas_in = rho_mix_n * T0 / T_mix_K
    rho_gas_out = rho_mix_n * T0 / T_gas_out_K

    T_mean_gas_C = 0.5 * (T_mix_C + inp.t_gas_out_c)
    T_mean_gas_K = T_mean_gas_C + T0
    rho_gas_mean = rho_mix_n * T0 / T_mean_gas_K
    V_gas_mean_actual = m_h / rho_gas_mean

    d_o = inp.tube_od_mm / 1000.0
    wall = inp.tube_wall_mm / 1000.0
    d_i = d_o - 2.0 * wall
    a_id = math.pi * d_i * d_i / 4.0

    if inp.target_gas_velocity_ms > 0.0:
        N_vel = math.ceil(V_gas_mean_actual / (inp.target_gas_velocity_ms * a_id))
    else:
        N_vel = 1

    N_area_max = math.ceil(area_gl_req / (math.pi * d_o * inp.tube_max_length_m))
    N_gl = max(1, int(N_vel), int(N_area_max))

    L_calc_gl = area_gl_req / (N_gl * math.pi * d_o) if N_gl > 0 else inp.tube_max_length_m
    L_gl = max(inp.tube_min_length_m, min(inp.tube_max_length_m, L_calc_gl))

    area_gl_prov = N_gl * math.pi * d_o * L_gl
    gas_flow_area_gl = N_gl * a_id
    v_gas_gl = V_gas_mean_actual / gas_flow_area_gl if gas_flow_area_gl > 0.0 else 0.0

    pitch = inp.pitch_ratio * d_o
    area_layout = 0.866 * pitch * pitch
    bundle_D = math.sqrt(4.0 * N_gl * area_layout / (math.pi * inp.layout_eff))
    bundle_D = max(bundle_D, 2.0 * d_o)

    shell_D = bundle_D + 0.03
    shell_D = max(shell_D, 0.2)

    length_overall_gl = L_gl + 0.6

    rho_steel = inp.steel_density
    tube_metal_area = math.pi / 4.0 * (d_o * d_o - d_i * d_i)
    mass_tubes_gl = N_gl * tube_metal_area * L_gl * rho_steel

    t_shell = inp.shell_thickness_mm / 1000.0
    mass_shell_gl = math.pi * shell_D * t_shell * L_gl * rho_steel

    t_sheet = inp.tubesheet_thickness_mm / 1000.0
    mass_tubesheets_gl = 2.0 * (math.pi / 4.0) * shell_D * shell_D * t_sheet * rho_steel

    mass_gl_total = (mass_tubes_gl + mass_shell_gl + mass_tubesheets_gl) * inp.mass_factor

    # Газовое сопротивление в трубах ТО на печи, приближённо
    mu_gas = _sutherland_viscosity_air_like(T_mean_gas_K)
    Re_gas = rho_gas_mean * v_gas_gl * d_i / mu_gas if mu_gas > 0.0 and v_gas_gl > 0.0 else 0.0

    if Re_gas > 0.0:
        if Re_gas < 2300.0:
            f_gas = 64.0 / Re_gas
        else:
            f_gas = 0.3164 / (Re_gas ** 0.25)
    else:
        f_gas = 0.0

    dyn_gas = 0.5 * rho_gas_mean * v_gas_gl * v_gas_gl
    dp_gas_gl = f_gas * (L_gl / d_i) * dyn_gas + 1.5 * dyn_gas

    # ------------------------------------------------------------------
    # 7. Насос жидкостного контура
    # ------------------------------------------------------------------
    pump_dp_pa = inp.pump_dp_kpa * 1000.0
    pump_hyd_W = V_liq * pump_dp_pa
    pump_shaft_W = pump_hyd_W / inp.pump_eff if inp.pump_eff > 0.0 else 0.0
    pump_motor_W = pump_shaft_W * inp.pump_motor_margin

    # ------------------------------------------------------------------
    # 8. АВО: охлаждение жидкости наружным воздухом
    # ------------------------------------------------------------------
    t_air_out_avo = inp.t_amb_c + inp.avo_air_dt_c

    dt_hot_end_avo = inp.t_liq_out_c - t_air_out_avo
    dt_cold_end_avo = inp.t_liq_in_c - inp.t_amb_c

    if dt_hot_end_avo <= 0.0:
        raise CalcError(
            "Температура воздуха на выходе из АВО получилась не ниже температуры горячей жидкости на входе в АВО. "
            "Уменьшите нагрев воздуха в АВО или измените температуры жидкости."
        )

    if dt_cold_end_avo <= 0.0:
        raise CalcError(
            "Температура жидкости после АВО должна быть выше температуры окружающей среды."
        )

    lmtd_avo = _lmtd(dt_hot_end_avo, dt_cold_end_avo)

    UA_avo = Q_W / (inp.lmtd_correction_avo * lmtd_avo)
    area_avo_req = UA_avo / inp.U_avo_Wm2K

    m_air_avo = Q_kW / (inp.cp_air_kjkgk * inp.avo_air_dt_c)
    rho_air_amb = inp.rho_air_n_kgm3 * T0 / T_amb_K
    V_air_avo = m_air_avo / rho_air_amb
    V_air_avo_h = V_air_avo * 3600.0

    fan_avo_hyd_W = V_air_avo * max(inp.avo_dp_pa, 0.0)
    fan_avo_shaft_W = fan_avo_hyd_W / inp.avo_fan_eff if inp.avo_fan_eff > 0.0 else 0.0
    fan_avo_motor_W = fan_avo_shaft_W * inp.avo_motor_margin

    # Геометрия АВО, упрощённо: оребрённые трубы
    avo_d_o = inp.avo_tube_od_mm / 1000.0
    avo_wall = inp.avo_tube_wall_mm / 1000.0
    avo_d_i = avo_d_o - 2.0 * avo_wall
    avo_a_id = math.pi * avo_d_i * avo_d_i / 4.0

    if inp.target_liquid_velocity_ms > 0.0:
        N_liq_avo = math.ceil(V_liq / (inp.target_liquid_velocity_ms * avo_a_id))
    else:
        N_liq_avo = 1

    N_area_avo = math.ceil(area_avo_req / (inp.fin_area_per_m * inp.avo_max_tube_length_m))
    N_avo = max(1, int(N_liq_avo), int(N_area_avo))

    L_calc_avo = area_avo_req / (N_avo * inp.fin_area_per_m) if N_avo > 0 else inp.avo_max_tube_length_m
    L_avo = max(inp.avo_min_tube_length_m, min(inp.avo_max_tube_length_m, L_calc_avo))

    area_avo_prov = N_avo * inp.fin_area_per_m * L_avo
    liq_flow_area_avo = N_avo * avo_a_id
    v_liq_avo = V_liq / liq_flow_area_avo if liq_flow_area_avo > 0.0 else 0.0

    face_area_avo = V_air_avo / inp.avo_face_velocity_ms
    front_side_avo = math.sqrt(face_area_avo) if face_area_avo > 0.0 else 0.0

    avo_volume = area_avo_prov * inp.avo_specific_volume_m3_per_m2
    avo_depth = avo_volume / face_area_avo if face_area_avo > 0.0 else 0.0
    avo_mass = area_avo_prov * inp.avo_specific_mass_kg_per_m2

    # ------------------------------------------------------------------
    # 9. Предупреждения
    # ------------------------------------------------------------------
    if dt_hot_end_gl < 5.0 or dt_cold_end_gl < 5.0:
        messages.append(
            "Малый температурный напор на концах газо-жидкостного ТО (< 5 K). Площадь будет расти."
        )

    if dt_hot_end_avo < 5.0 or dt_cold_end_avo < 5.0:
        messages.append(
            "Малый температурный напор на концах АВО (< 5 K). Площадь АВО будет расти."
        )

    if v_gas_gl < 5.0:
        messages.append(
            "Низкая скорость газов в трубах газо-жидкостного ТО (< 5 м/с). Возможны загрязнение и низкая теплоотдача."
        )
    elif v_gas_gl > 25.0:
        messages.append(
            "Высокая скорость газов в трубах газо-жидкостного ТО (> 25 м/с). Возможны высокое сопротивление и эрозия."
        )

    if v_liq_avo < 0.3:
        messages.append(
            "Очень низкая скорость жидкости в трубах АВО (< 0.3 м/с). Возможны застойные зоны и снижение теплоотдачи."
        )
    elif v_liq_avo > 3.0:
        messages.append(
            "Высокая скорость жидкости в трубах АВО (> 3 м/с). Возможно высокое гидравлическое сопротивление."
        )

    if inp.t_liq_in_c <= selected_freeze + 5.0:
        messages.append(
            "Рабочая температура жидкости на входе близка к температуре замерзания выбранного раствора. "
            "Проверьте концентрацию и режимы пуска/останова."
        )

    if dp_gas_gl > 1500.0:
        messages.append(
            "Сопротивление газового тракта газо-жидкостного ТО получилось более 1500 Па. Проверьте дымосос."
        )

    if inp.pump_dp_kpa > 300.0:
        messages.append(
            "Заданное сопротивление жидкостного контура выше 300 кПа. Мощность насоса может быть завышенной. "
            "Для рабочего проекта нужен гидравлический расчёт."
        )

    # ------------------------------------------------------------------
    # 10. Итоги
    # ------------------------------------------------------------------
    total_mass_t = mass_gl_total / 1000.0 + avo_mass / 1000.0
    total_power_kw = pump_motor_W / 1000.0 + fan_avo_motor_W / 1000.0

    return Variant2Result(
        messages=messages,
        heat_duty_kw=Q_kW,
        t_gas_after_leak_c=T_mix_C,
        t_gas_out_c=inp.t_gas_out_c,
        t_liq_in_c=inp.t_liq_in_c,
        t_liq_out_c=inp.t_liq_out_c,
        fluid_type=inp.fluid_type,
        selected_concentration_pct=selected_conc,
        recommended_concentration_pct=recommended_conc,
        freeze_point_selected_c=selected_freeze,
        recommendation_text=recommendation_text,
        liq_density_kgm3=rho_liq,
        liq_cp_kjkgk=cp_liq,
        liq_viscosity_mpas=mu_liq_mpas,
        liq_mass_flow_kgs=m_liq,
        liq_volume_flow_m3h=V_liq_h,
        gl_area_req_m2=area_gl_req,
        gl_area_provided_m2=area_gl_prov,
        gl_lmtd_k=lmtd_gl,
        gl_U_Wm2K=inp.U_gas_liquid_Wm2K,
        gl_shell_diameter_m=shell_D,
        gl_length_overall_m=length_overall_gl,
        gl_mass_t=mass_gl_total / 1000.0,
        gl_gas_velocity_ms=v_gas_gl,
        gl_gas_pressure_drop_pa=dp_gas_gl,
        gl_n_tubes=N_gl,
        gl_tube_length_m=L_gl,
        pump_dp_kpa=inp.pump_dp_kpa,
        pump_hydraulic_kw=pump_hyd_W / 1000.0,
        pump_shaft_kw=pump_shaft_W / 1000.0,
        pump_motor_kw=pump_motor_W / 1000.0,
        avo_area_req_m2=area_avo_req,
        avo_area_provided_m2=area_avo_prov,
        avo_lmtd_k=lmtd_avo,
        avo_U_Wm2K=inp.U_avo_Wm2K,
        avo_air_mass_flow_kgs=m_air_avo,
        avo_air_volume_flow_m3h=V_air_avo_h,
        avo_air_out_c=t_air_out_avo,
        avo_fan_shaft_kw=fan_avo_shaft_W / 1000.0,
        avo_fan_motor_kw=fan_avo_motor_W / 1000.0,
        avo_face_area_m2=face_area_avo,
        avo_front_side_m=front_side_avo,
        avo_depth_m=avo_depth,
        avo_volume_m3=avo_volume,
        avo_mass_t=avo_mass / 1000.0,
        avo_n_tubes=N_avo,
        avo_tube_length_m=L_avo,
        avo_liquid_velocity_ms=v_liq_avo,
        total_mass_t=total_mass_t,
        total_power_kw=total_power_kw,
    )