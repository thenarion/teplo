"""
Тепловой баланс и расчёт тепловой нагрузки теплообменника.
"""
from typing import Optional
from . import gas_properties as gp


def avg_cp(T_in_C: float, T_out_C: float) -> float:
    """
    Средняя теплоёмкость дымовых газов в диапазоне температур.
    Использует усреднение cp(T_in) и cp(T_out).
    """
    return (gp.cp_flue_gas(T_in_C) + gp.cp_flue_gas(T_out_C)) / 2.0


def avg_cp_air(T_in_C: float, T_out_C: float) -> float:
    """Средняя теплоёмкость воздуха."""
    return (gp.cp_air(T_in_C) + gp.cp_air(T_out_C)) / 2.0


def heat_duty(m_dot_kgs: float, cp_avg_kjkgK: float,
              T_in_C: float, T_out_C: float) -> float:
    """
    Тепловая нагрузка теплообменника.
    Q = m_dot * cp_avg * (T_in - T_out)
    Возвращает Q в Вт.
    """
    return m_dot_kgs * cp_avg_kjkgK * 1000 * (T_in_C - T_out_C)  # кДж/с * 1000 = Вт


def heat_duty_kW(m_dot_kgs: float, cp_avg_kjkgK: float,
                 T_in_C: float, T_out_C: float) -> float:
    """Тепловая нагрузка, кВт."""
    return heat_duty(m_dot_kgs, cp_avg_kjkgK, T_in_C, T_out_C) / 1000


def heat_duty_MW(m_dot_kgs: float, cp_avg_kjkgK: float,
                 T_in_C: float, T_out_C: float) -> float:
    """Тепловая нагрузка, МВт."""
    return heat_duty(m_dot_kgs, cp_avg_kjkgK, T_in_C, T_out_C) / 1e6


def heat_duty_leak_contribution(m_gas_kgs: float, m_air_kgs: float,
                                T_gas_in_C: float, T_mix_C: float,
                                T_out_C: float, T_ambient_C: float) -> dict:
    """
    Вклад подсоса воздуха в тепловую нагрузку.
    Возвращает dict:
      - Q_total: общая тепловая нагрузка, кВт
      - Q_from_gas: тепло, снимаемое с основных газов, кВт
      - Q_from_air: тепло, снимаемое с подсосного воздуха, кВт
      - fraction_air: доля воздуха в общей нагрузке
    """
    cp_gas = avg_cp(T_gas_in_C, T_out_C)
    cp_air = avg_cp_air(T_ambient_C, T_out_C)
    m_total = m_gas_kgs + m_air_kgs
    cp_mix = (m_gas_kgs * cp_gas + m_air_kgs * cp_air) / m_total if m_total > 0 else cp_gas

    Q_total = heat_duty_kW(m_total, cp_mix, T_mix_C, T_out_C)

    # Тепло от основных газов: если бы они охлаждались от T_gas_in до T_mix
    Q_gas_cooling = heat_duty_kW(m_gas_kgs, cp_gas, T_gas_in_C, T_mix_C)

    # Тепло от воздуха: если бы он нагревался от T_ambient до T_mix
    Q_air_heating = heat_duty_kW(m_air_kgs, cp_air, T_ambient_C, T_mix_C)

    # Общее тепло от T_mix до T_out
    # распределяем пропорционально массе
    fraction_air = m_air_kgs / m_total if m_total > 0 else 0

    Q_from_gas = Q_total * (1 - fraction_air)
    Q_from_air = Q_total * fraction_air

    return {
        "Q_total": Q_total,
        "Q_from_gas": Q_from_gas,
        "Q_from_air": Q_from_air,
        "fraction_air": fraction_air,
        "Q_gas_cooling": Q_gas_cooling,
        "Q_air_heating": Q_air_heating,
    }
