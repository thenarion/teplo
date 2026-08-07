"""
Свойства газов и воздуха.
Плотности, теплоёмкости, перевод расходов.
"""
import math

R = 8.314  # Дж/(моль·К)


def gas_density(T_C: float, p_Pa: float = 101325, M: float = 29.0) -> float:
    """Плотность газа по уравнению идеального газа. кг/м³."""
    T_K = T_C + 273.15
    return (p_Pa * M) / (R * T_K * 1000)  # M в кг/кмоль → делим на 1000


def air_density(T_C: float, p_Pa: float = 101325) -> float:
    """Плотность воздуха. кг/м³. M_air ≈ 28.97 кг/кмоль."""
    return gas_density(T_C, p_Pa, M=28.97)


def cp_flue_gas(T_C: float) -> float:
    """Теплоёмкость дымовых газов, кДж/(кг·К). Зависит от температуры."""
    # Полиномиальная аппроксимация для дымовых газов
    # При 20°C ~1.005, при 500°C ~1.09, при 1000°C ~1.17
    T = T_C
    if T < 0:
        return 1.005
    return 1.005 + 1.5e-4 * T + 5e-8 * T * T


def cp_air(T_C: float) -> float:
    """Теплоёмкость воздуха, кДж/(кг·К)."""
    T = T_C
    if T < 0:
        return 1.005
    return 1.005 + 1e-4 * T + 3e-8 * T * T


def actual_to_mass_flow(V_actual_m3h: float, T_C: float,
                        p_Pa: float = 101325, M: float = 29.0) -> float:
    """Перевод объёмного расхода (м³/ч при рабочих условиях) в массовый (кг/с)."""
    rho = gas_density(T_C, p_Pa, M)
    return V_actual_m3h * rho / 3600


def normal_to_actual(V_normal_m3h: float, T_actual_C: float,
                     p_actual_Pa: float = 101325) -> float:
    """Перевод нормального расхода (Нм³/ч при 0°C, 101325 Па) в фактический (м³/ч)."""
    T_normal_K = 273.15
    T_actual_K = T_actual_C + 273.15
    p_normal = 101325
    return V_normal_m3h * (T_actual_K / T_normal_K) * (p_normal / p_actual_Pa)


def actual_to_normal(V_actual_m3h: float, T_actual_C: float,
                     p_actual_Pa: float = 101325) -> float:
    """Перевод фактического расхода (м³/ч) в нормальный (Нм³/ч)."""
    T_normal_K = 273.15
    T_actual_K = T_actual_C + 273.15
    p_normal = 101325
    return V_actual_m3h * (T_normal_K / T_actual_K) * (p_actual_Pa / p_normal)


def mass_to_actual(m_dot_kgs: float, T_C: float,
                   p_Pa: float = 101325, M: float = 29.0) -> float:
    """Перевод массового расхода (кг/с) в объёмный (м³/ч при рабочих условиях)."""
    rho = gas_density(T_C, p_Pa, M)
    return m_dot_kgs * 3600 / rho


def mass_to_normal(m_dot_kgs: float, M: float = 29.0) -> float:
    """Перевод массового расхода (кг/с) в нормальный объёмный (Нм³/ч)."""
    # Плотность при н.у. (0°C, 101325 Па)
    rho_normal = gas_density(0, 101325, M)
    return m_dot_kgs * 3600 / rho_normal
