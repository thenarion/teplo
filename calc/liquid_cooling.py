"""
Расчёт жидкостного охлаждения антифризом.
Контур: газо-жидкостный ТА → насос → dry cooler → обратно.
"""
import math
from typing import Optional
from . import gas_properties as gp
from . import antifreeze
from . import hx_sizing


def liquid_flow_rate(Q_kW: float, cp_liquid_kjkgK: float,
                     dT_liquid_K: float) -> float:
    """
    Расход жидкости (антифриза), кг/с.
    m = Q / (cp * dT)
    """
    if dT_liquid_K <= 0 or cp_liquid_kjkgK <= 0:
        return 0.0
    return Q_kW / (cp_liquid_kjkgK * dT_liquid_K)


def liquid_volume_flow(m_kgs: float, density_kgm3: float) -> float:
    """
    Объёмный расход жидкости, м³/ч.
    """
    if density_kgm3 <= 0:
        return 0.0
    return m_kgs * 3600 / density_kgm3


def pump_power(V_m3h: float, dp_bar: float, eta: float = 0.6) -> float:
    """
    Мощность насоса, кВт.
    V_m3h — объёмный расход, м³/ч
    dp_bar — перепад давления, бар
    eta — КПД насоса
    """
    V_m3s = V_m3h / 3600
    dp_Pa = dp_bar * 1e5
    return V_m3s * dp_Pa / (eta * 1000)


def expansion_tank_volume(V_system_m3: float,
                          T_max_C: float = 90,
                          T_min_C: float = 20) -> float:
    """
    Ориентировочный объём расширительного бака, м³.
    Принимаем ~15-20% от объёма системы + запас.
    """
    # Коэффициент расширения воды/гликоля
    beta = 0.0004  # 1/K (приближённо)
    dT = T_max_C - T_min_C
    V_expansion = V_system_m3 * beta * dT
    # Запас ×3-4 (газовая подушка + запас)
    return max(V_expansion * 4, V_system_m3 * 0.15)


def dry_cooler_sizing(Q_kW: float,
                      T_liquid_in_C: float,
                      T_liquid_out_C: float,
                      T_air_in_C: float,
                      T_air_out_C: float = None,
                      dT_air: float = 15.0,
                      U_dry_cooler: float = 40.0,
                      F: float = 0.9,
                      margin_pct: float = 15.0) -> dict:
    """
    Подбор dry cooler / АВО.

    Возвращает dict с параметрами.
    """
    warnings = []

    if T_air_out_C is None:
        T_air_out_C = T_air_in_C + dT_air

    # Проверка: воздух на выходе не должен быть горячее антифриза на входе
    if T_air_out_C >= T_liquid_in_C - 5:
        warnings.append(
            f"T_air_out ({T_air_out_C:.0f}°C) слишком близка к "
            f"T_liquid_in ({T_liquid_in_C:.0f}°C). LMTD будет малым. "
            f"Уменьшите T_air_out или увеличьте T_liquid_in."
        )

    # Проверка: ΔT на горячем конце
    dT_hot = T_liquid_in_C - T_air_out_C
    dT_cold = T_liquid_out_C - T_air_in_C

    if dT_hot <= 5:
        warnings.append(
            f"ΔT на горячем конце = {dT_hot:.0f}°C — слишком мало. "
            f"Увеличьте температуру антифриза."
        )

    # Расход воздуха через dry cooler
    cp_air = gp.cp_air((T_air_in_C + T_air_out_C) / 2)
    m_air = liquid_flow_rate(Q_kW, cp_air, T_air_out_C - T_air_in_C)
    V_air_m3h = m_air * 3600 / gp.air_density((T_air_in_C + T_air_out_C) / 2)

    # LMTD для dry cooler
    # Hot = liquid (70→60), Cold = air (35→50), противоток
    # dT1 = T_liquid_in - T_air_out, dT2 = T_liquid_out - T_air_in
    lmtd_val = hx_sizing.lmtd(T_liquid_in_C, T_liquid_out_C,
                               T_air_in_C, T_air_out_C)

    # Площадь с запасом
    Q_design_W = Q_kW * 1000 * (1 + margin_pct / 100)
    area = hx_sizing.heat_transfer_area(Q_design_W, U_dry_cooler, F, lmtd_val)

    # Фронтальная площадь (воздух)
    v_air = 2.5  # м/с через оребрённый пучок
    A_front = (V_air_m3h / 3600) / v_air if v_air > 0 else 0

    # Количество вентиляторов (типичный диаметр 1.0-1.5 м)
    # Один вентилятор ~5000-10000 м³/ч
    n_fans = max(1, math.ceil(V_air_m3h / 8000))
    P_fan_each = 2.0  # кВт (типичный)
    P_fans_total = n_fans * P_fan_each

    if lmtd_val <= 0:
        warnings.append("LMTD ≤ 0 в dry cooler — невозможный режим.")
    if lmtd_val > 0 and lmtd_val < 20:
        warnings.append(
            f"LMTD dry cooler = {lmtd_val:.0f}K — малый напор. "
            "Площадь будет очень большой."
        )
    if T_liquid_in_C > 130:
        warnings.append(
            f"Температура антифриза {T_liquid_in_C:.0f}°C — "
            "высокая. Проверьте деградацию гликоля."
        )

    return {
        "m_air_kgs": m_air,
        "V_air_m3h": V_air_m3h,
        "LMTD": lmtd_val,
        "area_m2": area,
        "A_front_m2": A_front,
        "n_fans": n_fans,
        "P_fans_kW": P_fans_total,
        "T_air_out_C": T_air_out_C,
        "warnings": warnings,
    }


def liquid_cooling_calculate(
    Q_kW: float,
    T_gas_in_C: float,
    T_gas_out_C: float,
    T_liquid_in_C: float = 90.0,
    dT_liquid_K: float = 20.0,
    glycol_type: str = "propylene",
    concentration_pct: float = 30.0,
    T_min_ambient: float = -30.0,
    T_max_ambient: float = 35.0,
    U_gas_liquid: float = 60.0,
    U_dry_cooler: float = 60.0,
    F: float = 0.9,
    margin_pct: float = 25.0,
    dp_system_bar: float = 1.5,
    pump_eta: float = 0.6,
    dT_air_cooler: float = 30.0,
) -> dict:
    """
    Полный расчёт жидкостного контура охлаждения.

    Возвращает dict с результатами.
    """
    warnings = []

    # Свойства антифриза
    T_liquid_avg = T_liquid_in_C + dT_liquid_K / 2
    af_props = antifreeze.antifreeze_properties(
        glycol_type, concentration_pct, T_liquid_avg
    )
    warnings.extend(af_props["warnings"])

    cp_liquid = af_props["cp"]
    rho_liquid = af_props["density"]

    # Температура на выходе из газо-жидкостного ТА
    T_liquid_out_C = T_liquid_in_C + dT_liquid_K

    # Расход антифриза
    m_liquid = liquid_flow_rate(Q_kW, cp_liquid, dT_liquid_K)
    V_liquid_m3h = liquid_volume_flow(m_liquid, rho_liquid)

    # LMTD газо-жидкостного ТА
    lmtd_gas_liq = hx_sizing.lmtd(T_gas_in_C, T_gas_out_C,
                                    T_liquid_in_C, T_liquid_out_C)

    # Площадь газо-жидкостного ТА
    Q_W = Q_kW * 1000
    area_gas_liq = hx_sizing.heat_transfer_area(Q_W, U_gas_liquid, F, lmtd_gas_liq)
    area_gas_liq_with_margin = area_gas_liq * (1 + margin_pct / 100)

    # Мощность насоса
    P_pump = pump_power(V_liquid_m3h, dp_system_bar, pump_eta)

    # Dry cooler
    dc = dry_cooler_sizing(
        Q_kW=Q_kW,
        T_liquid_in_C=T_liquid_out_C,
        T_liquid_out_C=T_liquid_in_C,
        T_air_in_C=T_max_ambient,
        dT_air=dT_air_cooler,
        U_dry_cooler=U_dry_cooler,
        F=F,
        margin_pct=15.0,
    )
    warnings.extend(dc["warnings"])

    if dc["LMTD"] < 20:
        warnings.append(
            f"LMTD dry cooler = {dc['LMTD']:.0f}K. "
            f"Рекомендуется увеличить температуру антифриза до 90-110°C "
            f"или уменьшить нагрев воздуха."
        )

    if dc["area_m2"] > 5000:
        warnings.append(
            f"Площадь dry cooler = {dc['area_m2']:.0f} м² — очень большая. "
            f"Проверьте параметры: температуру антифриза и нагрев воздуха."
        )

    # Проверки
    if T_liquid_out_C > 120:
        warnings.append(
            f"Температура антифриза на выходе {T_liquid_out_C:.0f}°C — "
            "высокая. Риск деградации гликоля."
        )

    if m_liquid <= 0:
        warnings.append("Расход антифриза ≤ 0. Проверьте входные данные.")

    # Объём системы (приближённо)
    V_system = area_gas_liq * 0.01 + 1.0  # м³ (грубая оценка)
    V_tank = expansion_tank_volume(V_system)

    return {
        # Свойства антифриза
        "glycol_type": glycol_type,
        "concentration_pct": concentration_pct,
        "freeze_temp": af_props["freeze_temp"],
        "cp_liquid": cp_liquid,
        "density_liquid": rho_liquid,
        "viscosity_factor": af_props["viscosity_factor"],
        # Температуры
        "T_liquid_in_C": T_liquid_in_C,
        "T_liquid_out_C": T_liquid_out_C,
        # Расходы
        "m_liquid_kgs": m_liquid,
        "V_liquid_m3h": V_liquid_m3h,
        # Газо-жидкостный ТА
        "LMTD_gas_liquid": lmtd_gas_liq,
        "area_gas_liquid_m2": area_gas_liq,
        "area_gas_liquid_with_margin_m2": area_gas_liq_with_margin,
        # Насос
        "P_pump_kW": P_pump,
        "dp_system_bar": dp_system_bar,
        # Расширительный бак
        "V_expansion_tank_m3": V_tank,
        # Dry cooler
        "dry_cooler": dc,
        "warnings": warnings,
    }
