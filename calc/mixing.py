"""
Модель смешения дымовых газов с подсосным воздухом в циклонах.
"""
from typing import Optional


def mixed_gas_temperature(m_gas: float, T_gas_C: float,
                          m_air: float, T_air_C: float,
                          cp_gas: float = 1.1,
                          cp_air: float = 1.005) -> float:
    """
    Температура смеси после подсоса воздуха в циклонах.
    Тепловой баланс: m_gas*cp_gas*T_gas + m_air*cp_air*T_air = (m_gas*cp_gas + m_air*cp_air)*T_mix

    Параметры:
        m_gas — массовый расход газов, кг/с
        T_gas_C — температура газов, °C
        m_air — массовый расход воздуха, кг/с
        T_air_C — температура воздуха, °C
        cp_gas — теплоёмкость газов, кДж/(кг·К)
        cp_air — теплоёмкость воздуха, кДж/(кг·К)

    Возвращает:
        Температуру смеси, °C
    """
    if m_gas <= 0:
        return T_air_C
    if m_air <= 0:
        return T_gas_C

    numerator = m_gas * cp_gas * T_gas_C + m_air * cp_air * T_air_C
    denominator = m_gas * cp_gas + m_air * cp_air

    if denominator <= 0:
        return T_gas_C

    return numerator / denominator


def validate_mixing(T_gas_C: float, T_air_C: float, T_mix_C: float,
                    leak_fraction: float) -> list:
    """
    Проверки результата смешения.
    Возвращает список предупреждений (пустой, если всё ОК).
    """
    warnings = []

    # Температура смеси должна быть между T_gas и T_air
    T_min = min(T_gas_C, T_air_C)
    T_max = max(T_gas_C, T_air_C)
    if T_mix_C < T_min - 1 or T_mix_C > T_max + 1:
        warnings.append(
            f"Температура смеси {T_mix_C:.1f}°C вне диапазона "
            f"[{T_min:.1f}, {T_max:.1f}]°C. Проверьте ввод."
        )

    # Подсос > 50%
    if leak_fraction > 0.5:
        warnings.append(
            f"Подсос воздуха {leak_fraction*100:.1f}% — очень высокий. "
            "Проверьте корректность данных."
        )

    # Подсос > 100%
    if leak_fraction > 1.0:
        warnings.append(
            f"Подсос воздуха {leak_fraction*100:.1f}% превышает расход газов. "
            "Возможна ошибка ввода."
        )

    # Температура смеси слишком близка к температуре воздуха
    if T_gas_C > T_air_C + 100 and abs(T_mix_C - T_air_C) < 10:
        warnings.append(
            f"Температура смеси ({T_mix_C:.1f}°C) слишком близка к "
            f"температуре воздуха ({T_air_C:.1f}°C). Проверьте подсос."
        )

    return warnings
