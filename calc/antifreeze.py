"""
Свойства антифризов и рекомендации по концентрации.
Пропиленгликоль и этиленгликоль в водных растворах.
"""

# Таблица температур замерзания (концентрация % → температура °C)
# Приближённые данные для этиленгликоля
ETHYLENE_GLYCOL_FREEZE = {
    0: 0,
    10: -3.2,
    20: -7.8,
    25: -10.5,
    30: -14.0,
    35: -17.8,
    40: -22.3,
    45: -27.5,
    50: -33.8,
    55: -41.0,
    60: -50.0,
}

# Приближённые данные для пропиленгликоля
PROPYLENE_GLYCOL_FREEZE = {
    0: 0,
    10: -2.6,
    20: -6.5,
    25: -8.9,
    30: -12.0,
    35: -15.5,
    40: -20.0,
    45: -25.0,
    50: -32.0,
    55: -39.0,
    60: -47.0,
}

# Поправка на вязкость: чем выше концентрация, тем хуже теплопередача
# Приближённый множитель к Cp и к вязкости
GLYCOL_CP_FACTORS = {
    0: 1.0,
    20: 0.87,
    30: 0.82,
    40: 0.76,
    50: 0.70,
    60: 0.64,
}

GLYCOL_VISCOSITY_FACTORS = {
    0: 1.0,
    20: 1.5,
    30: 2.0,
    40: 2.8,
    50: 4.0,
    60: 6.0,
}


def interpolate_table(table: dict, x: float) -> float:
    """Линейная интерполяция по таблице."""
    keys = sorted(table.keys())
    if x <= keys[0]:
        return table[keys[0]]
    if x >= keys[-1]:
        return table[keys[-1]]
    for i in range(len(keys) - 1):
        if keys[i] <= x <= keys[i + 1]:
            frac = (x - keys[i]) / (keys[i + 1] - keys[i])
            return table[keys[i]] + frac * (table[keys[i + 1]] - table[keys[i]])
    return table[keys[-1]]


def freeze_temperature(glycol_type: str, concentration_pct: float) -> float:
    """
    Температура замерзания раствора гликоля, °C.
    glycol_type: "ethylene" или "propylene"
    concentration_pct: 0-60%
    """
    if glycol_type == "ethylene":
        return interpolate_table(ETHYLENE_GLYCOL_FREEZE, concentration_pct)
    else:
        return interpolate_table(PROPYLENE_GLYCOL_FREEZE, concentration_pct)


def recommend_antifreeze_concentration(T_min_ambient: float,
                                       glycol_type: str = "propylene",
                                       safety_margin: float = 10.0) -> dict:
    """
    Рекомендация концентрации гликоля по минимальной температуре.

    Возвращает dict:
      - concentration: рекомендуемая концентрация, %
      - freeze_temp: температура замерзания, °C
      - warnings: предупреждения
    """
    warnings = []
    T_target = T_min_ambient - safety_margin

    # Ищем минимальную концентрацию, дающую нужную температуру
    table = (ETHYLENE_GLYCOL_FREEZE if glycol_type == "ethylene"
             else PROPYLENE_GLYCOL_FREEZE)

    concentration = 0.0
    for conc in sorted(table.keys(), reverse=True):
        if table[conc] <= T_target:
            concentration = conc
        else:
            break

    # Если не нашли подходящую концентрацию
    if concentration == 0 and T_target < 0:
        concentration = 20.0  # минимальная разумная
        warnings.append(
            f"Минимальная температура {T_min_ambient:.0f}°C — "
            "требуется антифриз с концентрацией не менее 20%."
        )

    if concentration > 55:
        warnings.append(
            f"Концентрация {concentration:.0f}% — высокая. "
            "Увеличивается вязкость и ухудшается теплопередача. "
            "Рассмотрите пропиленгликоль или другой тип антифриза."
        )

    if concentration > 60:
        warnings.append(
            "Концентрация выше 60% не рекомендуется без специального обоснования. "
            "Критически высокая вязкость."
        )

    freeze_t = freeze_temperature(glycol_type, concentration)

    return {
        "concentration": concentration,
        "freeze_temp": freeze_t,
        "target_temp": T_target,
        "warnings": warnings,
    }


def antifreeze_properties(glycol_type: str, concentration_pct: float,
                          T_avg_C: float = 50.0) -> dict:
    """
    Свойства раствора гликоля.

    Возвращает dict:
      - cp: теплоёмкость, кДж/(кг·К)
      - density: плотность, кг/м³
      - viscosity_factor: множитель вязкости относительно воды
      - freeze_temp: температура замерзания, °C
      - warnings: предупреждения
    """
    warnings = []

    # Базовая теплоёмкость воды
    cp_water = 4.186  # кДж/(кг·К)
    cp_factor = interpolate_table(GLYCOL_CP_FACTORS, concentration_pct)
    cp = cp_water * cp_factor

    # Плотность: вода + поправка на гликоль
    # Чистый гликоль ~1040 кг/м³ (этилен) или ~1036 (пропилен)
    rho_water = 988  # при ~50°C
    rho_glycol = 1040 if glycol_type == "ethylene" else 1036
    density = rho_water + (rho_glycol - rho_water) * concentration_pct / 100.0

    # Вязкость
    viscosity_factor = interpolate_table(GLYCOL_VISCOSITY_FACTORS, concentration_pct)

    # Температура замерзания
    freeze_t = freeze_temperature(glycol_type, concentration_pct)

    if T_avg_C > 150:
        warnings.append(
            f"Средняя температура теплоносителя {T_avg_C:.0f}°C — "
            "высокая. Возможно деградация гликоля. "
            "Для этиленгликоля макс. ~170°C, для пропиленгликоля ~150°C."
        )

    if concentration_pct > 50:
        warnings.append(
            f"Концентрация {concentration_pct:.0f}% — "
            "высокая вязкость, увеличивается нагрузка на насос."
        )

    return {
        "cp": cp,
        "density": density,
        "viscosity_factor": viscosity_factor,
        "freeze_temp": freeze_t,
        "warnings": warnings,
    }
