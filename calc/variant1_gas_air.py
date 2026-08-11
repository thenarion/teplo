from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List


class CalcError(Exception):
    """Ошибка исходных данных или невозможный режим."""


@dataclass
class Variant1Inputs:
    # Обязательные технологические исходные данные
    t_gas_in_c: float
    gas_flow_nm3h: float
    t_amb_c: float
    leakage_pct: float
    t_gas_out_c: float
    t_air_out_c: float

    # База для подсоса: процент от нормального объёма газов или от массы газов
    leakage_basis: str = "Объём (н.у.)"

    # Свойства потоков, упрощённо
    cp_gas_kjkgk: float = 1.08
    cp_air_kjkgk: float = 1.005
    rho_gas_n_kgm3: float = 1.30
    rho_air_n_kgm3: float = 1.293

    # Теплосъём и LMTD
    U_Wm2K: float = 40.0
    lmtd_correction: float = 0.95

    # Вентилятор воздуха
    fan_dp_pa: float = 1200.0
    fan_eff: float = 0.65
    motor_margin: float = 1.15

    # Предварительная конструкция трубного теплообменника
    target_gas_velocity_ms: float = 15.0
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


@dataclass
class Variant1Result:
    messages: List[str] = field(default_factory=list)

    # Основные результаты
    area_req_m2: float = 0.0
    area_provided_m2: float = 0.0
    air_mass_flow_kgs: float = 0.0
    air_volume_flow_amb_m3h: float = 0.0
    fan_shaft_power_kw: float = 0.0
    fan_motor_power_kw: float = 0.0
    shell_diameter_m: float = 0.0
    length_overall_m: float = 0.0
    mass_total_t: float = 0.0

    # Тепловые величины
    heat_duty_kw: float = 0.0
    t_gas_in_raw_c: float = 0.0
    t_gas_after_leak_c: float = 0.0
    t_gas_out_c: float = 0.0
    t_air_in_c: float = 0.0
    t_air_out_c: float = 0.0
    dt_hot_end_k: float = 0.0
    dt_cold_end_k: float = 0.0
    lmtd_k: float = 0.0
    lmtd_correction: float = 0.0
    effectiveness: float = 0.0
    ntu: float = 0.0
    ua_w_per_k: float = 0.0
    c_hot_kwk: float = 0.0
    c_cold_kwk: float = 0.0
    c_min_kwk: float = 0.0
    cr: float = 0.0

    # Потоки и подсос
    gas_mass_flow_kgs: float = 0.0
    leak_air_mass_flow_kgs: float = 0.0
    total_hot_mass_flow_kgs: float = 0.0
    gas_volume_flow_nm3h: float = 0.0
    leak_air_volume_nm3h: float = 0.0
    gas_volume_total_nm3h: float = 0.0
    gas_volume_in_actual_m3h: float = 0.0
    gas_volume_out_actual_m3h: float = 0.0
    gas_density_in_kgm3: float = 0.0
    gas_density_out_kgm3: float = 0.0
    cp_hot_mixed_kjkgk: float = 0.0

    # Конструкция и аэродинамика
    n_tubes: int = 0
    tube_od_mm: float = 0.0
    tube_id_mm: float = 0.0
    tube_length_m: float = 0.0
    gas_velocity_ms: float = 0.0
    gas_reynolds: float = 0.0
    gas_pressure_drop_pa: float = 0.0
    bundle_diameter_m: float = 0.0
    mass_tubes_kg: float = 0.0
    mass_shell_kg: float = 0.0
    mass_tubesheets_kg: float = 0.0


def _lmtd_counterflow(dt_hot_end: float, dt_cold_end: float) -> float:
    """
    LMTD для противотока.
    dt_hot_end = Th_in - Tc_out
    dt_cold_end = Th_out - Tc_in
    """
    if dt_hot_end <= 0.0 or dt_cold_end <= 0.0:
        raise CalcError(
            "Температурный напор на концах теплообменника должен быть положительным. "
            "Проверьте температуры газов и воздуха."
        )

    if abs(dt_hot_end - dt_cold_end) < 1e-6:
        return dt_hot_end

    return (dt_hot_end - dt_cold_end) / math.log(dt_hot_end / dt_cold_end)


def _sutherland_viscosity_air_like(t_k: float) -> float:
    """
    Приближённая динамическая вязкость для газовоздушной смеси по формуле Сазерленда.
    Подходит для предварительной оценки, т.к. дымовые газы приняты близкими к воздуху.
    """
    mu0 = 1.716e-5
    t0 = 273.15
    s = 110.4
    return mu0 * (t_k / t0) ** 1.5 * (t0 + s) / (t_k + s)


def calculate_variant1(inp: Variant1Inputs) -> Variant1Result:
    messages: List[str] = []

    # ------------------------------------------------------------------
    # 1. Базовые проверки
    # ------------------------------------------------------------------
    if inp.gas_flow_nm3h <= 0.0:
        raise CalcError("Расход дымовых газов должен быть больше нуля.")

    if inp.U_Wm2K <= 0.0:
        raise CalcError("Коэффициент теплопередачи U должен быть больше нуля.")

    if inp.cp_gas_kjkgk <= 0.0 or inp.cp_air_kjkgk <= 0.0:
        raise CalcError("Теплоёмкости cp должны быть больше нуля.")

    if inp.rho_gas_n_kgm3 <= 0.0 or inp.rho_air_n_kgm3 <= 0.0:
        raise CalcError("Плотности при нормальных условиях должны быть больше нуля.")

    if inp.leakage_pct < 0.0:
        raise CalcError("Подсос воздуха не может быть отрицательным.")

    if inp.fan_eff <= 0.0 or inp.fan_eff > 1.0:
        raise CalcError("КПД вентилятора должен быть в диапазоне от 0 до 1.")

    if inp.motor_margin <= 0.0:
        raise CalcError("Запас мощности двигателя должен быть больше нуля.")

    if inp.lmtd_correction <= 0.0 or inp.lmtd_correction > 1.0:
        raise CalcError("Поправочный коэффициент LMTD должен быть в диапазоне от 0 до 1.")

    if inp.tube_od_mm <= 0.0 or inp.tube_wall_mm <= 0.0:
        raise CalcError("Размеры труб должны быть положительными.")

    if inp.tube_od_mm <= 2.0 * inp.tube_wall_mm:
        raise CalcError("Толщина стенки трубы слишком большая: внутренний диаметр получается неположительным.")

    if inp.tube_min_length_m <= 0.0 or inp.tube_max_length_m < inp.tube_min_length_m:
        raise CalcError("Максимальная длина труб должна быть не меньше минимальной, а обе длины положительными.")

    if inp.target_gas_velocity_ms < 0.0:
        raise CalcError("Целевая скорость газов не может быть отрицательной.")

    if inp.pitch_ratio <= 1.0:
        raise CalcError("Шаг труб должен быть больше наружного диаметра, т.е. t/d > 1.")

    if not (0.0 < inp.layout_eff <= 1.0):
        raise CalcError("Коэффициент заполнения трубной доски должен быть в диапазоне от 0 до 1.")

    if inp.mass_factor <= 0.0:
        raise CalcError("Коэффициент добавочной массы должен быть больше нуля.")

    if inp.t_gas_in_c <= inp.t_amb_c:
        raise CalcError("Температура дымовых газов должна быть выше температуры окружающей среды.")

    # ------------------------------------------------------------------
    # 2. Потоки и подсос воздуха на циклонах
    # ------------------------------------------------------------------
    T0 = 273.15

    # Нормальный объём газов, м³/с при н.у.
    Vg_n = inp.gas_flow_nm3h / 3600.0

    # Массовый расход газов без подсоса
    m_g = Vg_n * inp.rho_gas_n_kgm3

    # Подсос воздуха
    if inp.leakage_basis == "Объём (н.у.)":
        # Проценты от нормального объёма газов
        V_leak_n = Vg_n * inp.leakage_pct / 100.0
        m_leak = V_leak_n * inp.rho_air_n_kgm3
    elif inp.leakage_basis == "Масса":
        # Проценты от массового расхода газов
        m_leak = m_g * inp.leakage_pct / 100.0
        V_leak_n = m_leak / inp.rho_air_n_kgm3
    else:
        raise CalcError("Неверно задана база подсоса: используйте 'Объём (н.у.)' или 'Масса'.")

    # Суммарный горячий поток после подсоса
    m_h = m_g + m_leak
    V_total_n = Vg_n + V_leak_n
    rho_mix_n = m_h / V_total_n if V_total_n > 0.0 else inp.rho_gas_n_kgm3

    # ------------------------------------------------------------------
    # 3. Температура газов после подсоса
    # ------------------------------------------------------------------
    T_g_K = inp.t_gas_in_c + T0
    T_amb_K = inp.t_amb_c + T0

    denom_cp = m_g * inp.cp_gas_kjkgk + m_leak * inp.cp_air_kjkgk
    if denom_cp <= 0.0:
        raise CalcError("Некорректный тепловой баланс: получен нулевой или отрицательный знаменатель.")

    T_mix_K = (
        m_g * inp.cp_gas_kjkgk * T_g_K + m_leak * inp.cp_air_kjkgk * T_amb_K
    ) / denom_cp

    T_mix_C = T_mix_K - T0

    # Осреднённая теплоёмкость горячего потока после подсоса
    cp_hot = denom_cp / m_h

    if T_mix_C <= inp.t_amb_c:
        raise CalcError(
            "После подсоса воздуха температура газов стала не выше температуры окружающей среды. "
            "Теплообмен с нагревом воздуха в таких условиях невозможен."
        )

    # ------------------------------------------------------------------
    # 4. Проверки целевых температур
    # ------------------------------------------------------------------
    if inp.t_gas_out_c >= T_mix_C:
        raise CalcError(
            "Температура газов после теплообменника не может быть выше температуры газов после подсоса."
        )

    if inp.t_air_out_c <= inp.t_amb_c:
        raise CalcError(
            "Температура нагретого воздуха должна быть выше температуры окружающей среды."
        )

    if inp.t_gas_out_c <= inp.t_amb_c:
        raise CalcError(
            "Температура газов на выходе из теплообменника должна быть выше температуры окружающей среды, "
            "иначе передача тепла воздуху невозможна."
        )

    if inp.t_air_out_c >= T_mix_C:
        raise CalcError(
            "Температура нагретого воздуха должна быть ниже температуры газов после подсоса."
        )

    dt_hot_end = T_mix_C - inp.t_air_out_c
    dt_cold_end = inp.t_gas_out_c - inp.t_amb_c

    lmtd = _lmtd_counterflow(dt_hot_end, dt_cold_end)

    # ------------------------------------------------------------------
    # 5. Тепловая нагрузка и расход нагреваемого воздуха
    # ------------------------------------------------------------------
    dt_air = inp.t_air_out_c - inp.t_amb_c
    if dt_air <= 0.0:
        raise CalcError("Разность температур воздуха должна быть положительной.")

    Q_kW = m_h * cp_hot * (T_mix_C - inp.t_gas_out_c)
    if Q_kW <= 0.0:
        raise CalcError("Получена неположительная тепловая нагрузка. Проверьте исходные температуры и расходы.")

    # Массовый расход воздуха через теплообменник
    m_cold = Q_kW / (inp.cp_air_kjkgk * dt_air)

    # Плотность воздуха при температуре окружающей среды
    rho_air_amb = inp.rho_air_n_kgm3 * T0 / T_amb_K
    if rho_air_amb <= 0.0:
        raise CalcError("Некорректная плотность воздуха.")

    V_air_amb = m_cold / rho_air_amb
    V_air_amb_h = V_air_amb * 3600.0

    # ------------------------------------------------------------------
    # 6. Теплоёмкости потоков, эффективность, NTU, площадь
    # ------------------------------------------------------------------
    C_h = m_h * cp_hot
    C_c = m_cold * inp.cp_air_kjkgk

    C_min = min(C_h, C_c)
    C_max = max(C_h, C_c)
    Cr = C_min / C_max if C_max > 0.0 else 0.0

    effectiveness = Q_kW / (C_min * (T_mix_C - inp.t_amb_c)) if C_min > 0.0 else 0.0
    if effectiveness > 1.0:
        effectiveness = 1.0

    Q_W = Q_kW * 1000.0
    UA = Q_W / (inp.lmtd_correction * lmtd)
    area_req = UA / inp.U_Wm2K

    ntu = UA / (C_min * 1000.0) if C_min > 0.0 else 0.0

    # ------------------------------------------------------------------
    # 7. Фактические объёмы газов до и после теплообменника
    # ------------------------------------------------------------------
    T_gas_out_K = inp.t_gas_out_c + T0

    rho_gas_in = rho_mix_n * T0 / T_mix_K
    rho_gas_out = rho_mix_n * T0 / T_gas_out_K

    V_gas_in_actual_h = (m_h / rho_gas_in) * 3600.0
    V_gas_out_actual_h = (m_h / rho_gas_out) * 3600.0

    T_mean_gas_C = 0.5 * (T_mix_C + inp.t_gas_out_c)
    T_mean_gas_K = T_mean_gas_C + T0
    rho_gas_mean = rho_mix_n * T0 / T_mean_gas_K
    V_gas_mean_actual = m_h / rho_gas_mean  # м³/с

    # ------------------------------------------------------------------
    # 8. Предварительная трубная геометрия
    # ------------------------------------------------------------------
    d_o = inp.tube_od_mm / 1000.0
    wall = inp.tube_wall_mm / 1000.0
    d_i = d_o - 2.0 * wall

    if d_i <= 0.0:
        raise CalcError("Внутренний диаметр трубы получился неположительным.")

    a_id = math.pi * d_i * d_i / 4.0

    # Число труб по целевой скорости газа
    if inp.target_gas_velocity_ms > 0.0:
        N_vel = math.ceil(V_gas_mean_actual / (inp.target_gas_velocity_ms * a_id))
    else:
        N_vel = 1

    # Число труб, чтобы при максимальной длине трубок обеспечить требуемую площадь
    N_area_max = math.ceil(area_req / (math.pi * d_o * inp.tube_max_length_m))

    N = max(1, int(N_vel), int(N_area_max))

    # Длина труб, обеспечивающая требуемую площадь при выбранном N
    L_calc = area_req / (N * math.pi * d_o) if N > 0 else inp.tube_max_length_m
    L = max(inp.tube_min_length_m, min(inp.tube_max_length_m, L_calc))

    area_provided = N * math.pi * d_o * L
    gas_flow_area = N * a_id
    v_gas = V_gas_mean_actual / gas_flow_area if gas_flow_area > 0.0 else 0.0

    # Диаметр трубного пучка, приближённо для треугольной разводки
    pitch = inp.pitch_ratio * d_o
    area_layout = 0.866 * pitch * pitch
    bundle_D = math.sqrt(4.0 * N * area_layout / (math.pi * inp.layout_eff))
    bundle_D = max(bundle_D, 2.0 * d_o)

    shell_D = bundle_D + 0.03
    shell_D = max(shell_D, 0.2)

    # Ориентировочная габаритная длина: трубная часть + камеры/патрубки
    length_overall = L + 0.6

    # ------------------------------------------------------------------
    # 9. Ориентировочная масса
    # ------------------------------------------------------------------
    rho_steel = inp.steel_density

    tube_metal_area = math.pi / 4.0 * (d_o * d_o - d_i * d_i)
    mass_tubes = N * tube_metal_area * L * rho_steel

    t_shell = inp.shell_thickness_mm / 1000.0
    mass_shell = math.pi * shell_D * t_shell * L * rho_steel

    t_sheet = inp.tubesheet_thickness_mm / 1000.0
    mass_tubesheets = 2.0 * (math.pi / 4.0) * shell_D * shell_D * t_sheet * rho_steel

    mass_total = (mass_tubes + mass_shell + mass_tubesheets) * inp.mass_factor

    # ------------------------------------------------------------------
    # 10. Газодинамическое сопротивление трубного хода, приближённо
    # ------------------------------------------------------------------
    mu_gas = _sutherland_viscosity_air_like(T_mean_gas_K)
    Re = rho_gas_mean * v_gas * d_i / mu_gas if mu_gas > 0.0 and v_gas > 0.0 else 0.0

    if Re > 0.0:
        if Re < 2300.0:
            f = 64.0 / Re
        else:
            f = 0.3164 / (Re ** 0.25)
    else:
        f = 0.0

    dyn_pressure = 0.5 * rho_gas_mean * v_gas * v_gas
    dp_gas = f * (L / d_i) * dyn_pressure + 1.5 * dyn_pressure

    # ------------------------------------------------------------------
    # 11. Вентилятор воздуха
    # ------------------------------------------------------------------
    fan_hyd_W = V_air_amb * max(inp.fan_dp_pa, 0.0)
    fan_shaft_W = fan_hyd_W / inp.fan_eff if inp.fan_eff > 0.0 else 0.0
    fan_motor_W = fan_shaft_W * inp.motor_margin

    # ------------------------------------------------------------------
    # 12. Предупреждения и рекомендации
    # ------------------------------------------------------------------
    if inp.t_gas_out_c < 120.0:
        messages.append(
            "Температура газов на выходе ниже 120 °C: повышенный риск конденсации и низкотемпературной коррозии. "
            "Для реального проекта нужна температура кислотной точки росы по составу газов (SOx, H2O)."
        )

    if dt_hot_end < 5.0 or dt_cold_end < 5.0:
        messages.append(
            "Малый температурный напор на концах теплообменника (< 5 K). "
            "В этой зоне площадь сильно растёт; рассмотрите изменение целевых температур."
        )

    if 0.0 < v_gas < 5.0:
        messages.append(
            "Низкая скорость газов в трубах (< 5 м/с): возможно усиленное загрязнение и снижение теплоотдачи. "
            "Можно уменьшить число труб, изменить диаметр труб или число ходов."
        )
    elif v_gas > 25.0:
        messages.append(
            "Высокая скорость газов в трубах (> 25 м/с): возможно большое сопротивление и эрозионный износ. "
            "Увеличьте число труб или уменьшите целевую скорость."
        )

    if dp_gas > 1500.0:
        messages.append(
            "Расчётное сопротивление газового тракта получилось более 1500 Па. "
            "Проверьте располагаемый напор дымососа/вентилятора газов или измените геометрию."
        )

    if area_provided > 1.2 * area_req:
        messages.append(
            "Конструктивная площадь теплообмена заметно превышает требуемую. "
            "Это может быть связано с минимальной длиной труб, шагом или целевой скоростью газа."
        )

    if shell_D > 3.0:
        messages.append(
            "Получается очень большой диаметр корпуса (> 3 м). "
            "Для предварительного проекта рассмотрите несколько параллельных секций."
        )

    if effectiveness > 0.85:
        messages.append(
            "Высокая эффективность (> 0.85): аппарат получается большим по NTU. "
            "Проверьте экономическую целесообразность и минимальные напоры."
        )

    # ------------------------------------------------------------------
    # 13. Результат
    # ------------------------------------------------------------------
    return Variant1Result(
        messages=messages,
        area_req_m2=area_req,
        area_provided_m2=area_provided,
        air_mass_flow_kgs=m_cold,
        air_volume_flow_amb_m3h=V_air_amb_h,
        fan_shaft_power_kw=fan_shaft_W / 1000.0,
        fan_motor_power_kw=fan_motor_W / 1000.0,
        shell_diameter_m=shell_D,
        length_overall_m=length_overall,
        mass_total_t=mass_total / 1000.0,
        heat_duty_kw=Q_kW,
        t_gas_in_raw_c=inp.t_gas_in_c,
        t_gas_after_leak_c=T_mix_C,
        t_gas_out_c=inp.t_gas_out_c,
        t_air_in_c=inp.t_amb_c,
        t_air_out_c=inp.t_air_out_c,
        dt_hot_end_k=dt_hot_end,
        dt_cold_end_k=dt_cold_end,
        lmtd_k=lmtd,
        lmtd_correction=inp.lmtd_correction,
        effectiveness=effectiveness,
        ntu=ntu,
        ua_w_per_k=UA,
        c_hot_kwk=C_h,
        c_cold_kwk=C_c,
        c_min_kwk=C_min,
        cr=Cr,
        gas_mass_flow_kgs=m_g,
        leak_air_mass_flow_kgs=m_leak,
        total_hot_mass_flow_kgs=m_h,
        gas_volume_flow_nm3h=inp.gas_flow_nm3h,
        leak_air_volume_nm3h=V_leak_n * 3600.0,
        gas_volume_total_nm3h=V_total_n * 3600.0,
        gas_volume_in_actual_m3h=V_gas_in_actual_h,
        gas_volume_out_actual_m3h=V_gas_out_actual_h,
        gas_density_in_kgm3=rho_gas_in,
        gas_density_out_kgm3=rho_gas_out,
        cp_hot_mixed_kjkgk=cp_hot,
        n_tubes=N,
        tube_od_mm=inp.tube_od_mm,
        tube_id_mm=d_i * 1000.0,
        tube_length_m=L,
        gas_velocity_ms=v_gas,
        gas_reynolds=Re,
        gas_pressure_drop_pa=dp_gas,
        bundle_diameter_m=bundle_D,
        mass_tubes_kg=mass_tubes,
        mass_shell_kg=mass_shell,
        mass_tubesheets_kg=mass_tubesheets,
    )