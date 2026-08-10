"""
Расчёт газовоздушного охлаждения.
Дымовые газы охлаждаются наружным воздухом через теплообменник.
"""
import math
from typing import Optional
from . import gas_properties as gp
from . import hx_sizing


def cooling_air_mass_flow(Q_kW: float, cp_air_kjkgK: float,
                          T_air_in_C: float, T_air_out_C: float) -> float:
    """
    Массовый расход охлаждающего воздуха, кг/с.
    m_air = Q / (cp_air * dT_air)
    """
    dT = T_air_out_C - T_air_in_C
    if dT <= 0 or Q_kW <= 0:
        return 0.0
    return Q_kW / (cp_air_kjkgK * dT)


def cooling_air_volume_flow(m_air_kgs: float, T_air_C: float,
                            p_Pa: float = 101325) -> float:
    """
    Объёмный расход воздуха, м³/ч.
    """
    rho = gp.air_density(T_air_C, p_Pa)
    if rho <= 0:
        return 0.0
    return m_air_kgs * 3600 / rho


def air_frontal_area(V_air_m3h: float, v_air_ms: float) -> float:
    """
    Площадь фронтального сечения для прохода воздуха, м².
    A_front = V_air / v_air
    """
    if v_air_ms <= 0:
        return 0.0
    V_m3s = V_air_m3h / 3600
    return V_m3s / v_air_ms


def fan_power_estimate(V_air_m3h: float, dp_Pa: float = 200,
                       eta: float = 0.6) -> float:
    """
    Ориентировочная мощность вентиляторов, кВт.
    dp_Pa — аэродинамическое сопротивление, Па.
    eta — КПД вентиляторной установки.
    """
    V_m3s = V_air_m3h / 3600
    return V_m3s * dp_Pa / (eta * 1000)


def gas_air_cooling_calculate(
    Q_kW: float,
    T_gas_in_C: float,
    T_gas_out_C: float,
    T_air_in_C: float,
    T_air_max_out_C: float = 300.0,
    dT_air: float = 150.0,
    v_air: float = 3.0,
    U: float = 50.0,
    F: float = 0.9,
    v_gas: float = 8.0,
    V_gas_m3h: float = 0.0,
    p_Pa: float = 101325,
) -> dict:
    """
    Полный расчёт газовоздушного охлаждения.

    Возвращает dict с результатами.
    """
    warnings = []
    cp_air = gp.cp_air((T_air_in_C + T_air_in_C + dT_air) / 2)

    # Температура воздуха на выходе
    T_air_out_C = T_air_in_C + dT_air

    # Проверка: воздух не горячее газа на входе
    if T_air_out_C >= T_gas_in_C - 20:
        warnings.append(
            f"Температура воздуха на выходе ({T_air_out_C:.0f}°C) "
            f"слишком близка к температуре газа на входе ({T_gas_in_C:.0f}°C). "
            "LMTD будет очень малым."
        )

    # Проверка: воздух на выходе горячее газа на выходе (для противотока желательно)
    if T_air_out_C < T_gas_out_C:
        warnings.append(
            f"Температура воздуха на выходе ({T_air_out_C:.0f}°C) "
            f"ниже температуры газа на выходе ({T_gas_out_C:.0f}°C). "
            "Проверьте схему теплообменника."
        )

    # Ограничение по максимальной температуре воздуха
    if T_air_out_C > T_air_max_out_C:
        T_air_out_C = T_air_max_out_C
        dT_air = T_air_out_C - T_air_in_C
        warnings.append(
            f"Температура воздуха на выходе ограничена {T_air_max_out_C:.0f}°C."
        )

    # Массовый расход воздуха
    m_air = cooling_air_mass_flow(Q_kW, cp_air, T_air_in_C, T_air_out_C)

    # Объёмный расход воздуха
    T_air_avg = (T_air_in_C + T_air_out_C) / 2
    V_air_m3h = cooling_air_volume_flow(m_air, T_air_avg, p_Pa)

    # LMTD для противотока
    dT_hot = T_gas_in_C - T_air_out_C
    dT_cold = T_gas_out_C - T_air_in_C

    if dT_hot <= 0 or dT_cold <= 0:
        warnings.append(
            f"Невозможный режим: ΔT_hot={dT_hot:.0f}°C, ΔT_cold={dT_cold:.0f}°C. "
            "Уменьшите нагрев воздуха."
        )
        lmtd_val = 0.0
    else:
        lmtd_val = hx_sizing.lmtd(T_gas_in_C, T_gas_out_C, T_air_in_C, T_air_out_C)

    # Площадь теплообмена
    Q_W = Q_kW * 1000
    area = hx_sizing.heat_transfer_area(Q_W, U, F, lmtd_val)

    # Фронтальное сечение для воздуха
    A_front_air = air_frontal_area(V_air_m3h, v_air)

    # Фронтальное сечение для газа
    A_front_gas = 0.0
    if V_gas_m3h > 0 and v_gas > 0:
        A_front_gas = (V_gas_m3h / 3600) / v_gas

    # Мощность вентиляторов
    P_fan = fan_power_estimate(V_air_m3h)
    # Количество вентиляторов (~8000 м³/ч на вентилятор)
    n_fans = max(1, math.ceil(V_air_m3h / 8000))
    P_fan_total = n_fans * 2.0  # ~2 кВт на вентилятор

    # Проверки
    if lmtd_val <= 0:
        warnings.append("LMTD ≤ 0 — невозможный режим. Проверьте температуры.")

    if lmtd_val > 0 and lmtd_val < 50:
        warnings.append(
            f"LMTD = {lmtd_val:.0f}K — малый температурный напор. "
            "Площадь теплообмена будет очень большой."
        )

    if T_gas_out_C < T_air_in_C + 10:
        warnings.append(
            f"Целевая температура газа ({T_gas_out_C:.0f}°C) близка к "
            f"температуре воздуха ({T_air_in_C:.0f}°C). "
            "Температурный напор мал."
        )

    return {
        "T_air_out_C": T_air_out_C,
        "m_air_kgs": m_air,
        "V_air_m3h": V_air_m3h,
        "LMTD": lmtd_val,
        "area_m2": area,
        "A_front_air_m2": A_front_air,
        "A_front_gas_m2": A_front_gas,
        "P_fan_kW": P_fan_total,
        "n_fans": n_fans,
        "warnings": warnings,
    }
