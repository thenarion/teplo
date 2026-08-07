"""
Модель подсосов воздуха в циклонах.
7 режимов расчёта.
"""
import math
from typing import Optional


def leak_from_percent(Q_gas: float, leak_percent: float) -> float:
    """Подсос в % от расхода газов. Возвращает расход подсоса в тех же единицах."""
    return Q_gas * leak_percent / 100.0


def leak_from_volume(Q_leak_m3h: float) -> float:
    """Ручной ввод подсоса в м³/ч. Возвращает как есть."""
    return Q_leak_m3h


def leak_from_mass(Q_leak_kgs: float) -> float:
    """Ручной ввод подсоса в кг/с. Возвращает как есть."""
    return Q_leak_kgs


def leak_from_orifice(A_leak: float, dp_Pa: float, rho_air: float,
                      Cd: float = 0.65) -> float:
    """
    Расчёт подсоса через эквивалентное отверстие.
    Q_air = Cd * A_leak * sqrt(2 * dp / rho)
    Возвращает объёмный расход, м³/с.
    """
    if dp_Pa <= 0 or A_leak <= 0:
        return 0.0
    return Cd * A_leak * math.sqrt(2.0 * dp_Pa / rho_air)


def leak_from_o2(O2_before: float, O2_after: float) -> float:
    """
    Расчёт подсоса по кислороду.
    Возвращает отношение Q_air/Q_gas (долю).
    Формула: (O2_after - O2_before) / (20.9 - O2_after)
    Справедлива для сухих газов, без горения между точками замера.
    """
    if O2_after <= O2_before or O2_after >= 20.9:
        return 0.0
    return (O2_after - O2_before) / (20.9 - O2_after)


def leak_from_temperature_drop(T_before_C: float, T_after_C: float,
                                T_ambient_C: float,
                                cp_gas: float = 1.1,
                                cp_air: float = 1.005) -> float:
    """
    Расчёт подсоса по падению температуры в циклонах.
    Возвращает отношение массового расхода воздуха к газу (r = m_air/m_gas).
    Тепловой баланс смешения.
    """
    if T_after_C <= T_ambient_C or T_before_C <= T_after_C:
        return 0.0
    numerator = cp_gas * (T_before_C - T_after_C)
    denominator = cp_air * (T_after_C - T_ambient_C)
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def leak_from_fan_curve(Q_fan: float, k_leak: float,
                        alpha: float = 1.0) -> float:
    """
    Эмпирическая модель: Q_leak = k * Q_fan^alpha.
    Q_fan и Q_leak в одних единицах.
    """
    if Q_fan <= 0 or k_leak <= 0:
        return 0.0
    return k_leak * (Q_fan ** alpha)


def calculate_leak(mode: str,
                   Q_gas_m3h: float = 0.0,
                   leak_percent: float = 0.0,
                   leak_m3h: float = 0.0,
                   leak_kgs: float = 0.0,
                   A_leak: float = 0.0,
                   dp_Pa: float = 0.0,
                   rho_air: float = 1.2,
                   Cd: float = 0.65,
                   O2_before: float = 0.0,
                   O2_after: float = 0.0,
                   T_before_C: float = 0.0,
                   T_after_C: float = 0.0,
                   T_ambient_C: float = 20.0,
                   cp_gas: float = 1.1,
                   cp_air: float = 1.005,
                   Q_fan: float = 0.0,
                   k_leak: float = 0.0,
                   alpha: float = 1.0) -> dict:
    """
    Универсальная функция расчёта подсоса.
    Возвращает dict с ключами:
      - leak_value: значение подсоса
      - leak_unit: единица измерения
      - leak_fraction: доля подсоса (0-1+)
      - warning: предупреждение (если есть)
    """
    result = {
        "leak_value": 0.0,
        "leak_unit": "",
        "leak_fraction": 0.0,
        "warning": None,
    }

    if mode == "percent":
        val = leak_from_percent(Q_gas_m3h, leak_percent)
        result["leak_value"] = val
        result["leak_unit"] = "м³/ч"
        result["leak_fraction"] = leak_percent / 100.0
        if leak_percent > 50:
            result["warning"] = f"Подсос {leak_percent}% — очень высокий, проверьте ввод."

    elif mode == "m3h":
        val = leak_from_volume(leak_m3h)
        result["leak_value"] = val
        result["leak_unit"] = "м³/ч"
        if Q_gas_m3h > 0:
            result["leak_fraction"] = val / Q_gas_m3h
            if result["leak_fraction"] > 0.5:
                result["warning"] = "Подсос более 50% от расхода газов."

    elif mode == "kgs":
        val = leak_from_mass(leak_kgs)
        result["leak_value"] = val
        result["leak_unit"] = "кг/с"
        result["leak_fraction"] = 0  # нужен массовый расход газа для доли

    elif mode == "orifice":
        val = leak_from_orifice(A_leak, dp_Pa, rho_air, Cd)
        result["leak_value"] = val * 3600  # м³/с → м³/ч
        result["leak_unit"] = "м³/ч"
        if Q_gas_m3h > 0:
            result["leak_fraction"] = (val * 3600) / Q_gas_m3h

    elif mode == "o2":
        frac = leak_from_o2(O2_before, O2_after)
        result["leak_fraction"] = frac
        result["leak_value"] = frac * 100
        result["leak_unit"] = "%"
        if frac > 0.5:
            result["warning"] = f"Подсос {frac*100:.1f}% — очень высокий."

    elif mode == "temperature":
        r = leak_from_temperature_drop(
            T_before_C, T_after_C, T_ambient_C, cp_gas, cp_air
        )
        result["leak_fraction"] = r
        result["leak_value"] = r * 100
        result["leak_unit"] = "% (по массе)"
        if r > 0.5:
            result["warning"] = (
                f"Подсос {r*100:.1f}% по массе — высокий. "
                "Частично снижение температуры может быть связано с теплопотерями."
            )

    elif mode == "empirical":
        val = leak_from_fan_curve(Q_fan, k_leak, alpha)
        result["leak_value"] = val
        result["leak_unit"] = "м³/ч"
        if Q_fan > 0:
            result["leak_fraction"] = val / Q_fan
        result["warning"] = (
            "Эмпирическая модель — оценочная. "
            "Требуется калибровка по измерениям."
        )

    else:
        result["warning"] = f"Неизвестный режим: {mode}"

    return result
