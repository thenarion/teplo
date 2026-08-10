"""
Расчёт теплового баланса сжигания топлива во вращающейся барабанной печи.
Включает:
- Расчёт времени пребывания по геометрии барабана
- Оценку полноты выгорания с учётом диаметра
- Фактическое тепловыделение с учётом полноты выгорания
- Тепловую нагрузку на барабан
- Расчёт теоретической температуры адиабатного горения
"""

from dataclasses import dataclass
from typing import Tuple
import math


# =========================================================
# ТИПЫ МАТЕРИАЛОВ
# =========================================================
MATERIAL_TYPES = {
    "high_mobility": {
        "name": "Высокоподвижные, мелкозернистые, сухие",
        "description": "Кварцевый песок, шлак, сухой уголь, апатитовый концентрат",
        "A_min": 0.60,
        "A_max": 0.65,
        "A_default": 0.62,
    },
    "medium_mobility": {
        "name": "Средней подвижности, кусковое сырьё",
        "description": "Гравий, щебень, известняк, древесная щепа",
        "A_min": 0.45,
        "A_max": 0.55,
        "A_default": 0.50,
    },
    "viscous_sticky": {
        "name": "Вязкие, липкие, переувлажнённые",
        "description": "Сырая глина, суглинки, влажный шлам, замазученные грунты",
        "A_min": 0.35,
        "A_max": 0.45,
        "A_default": 0.40,
    },
    "fibrous_light": {
        "name": "Волокнистые и сверхлёгкие",
        "description": "Торф, жом, опилки, измельчённая солома, помёт с подстилкой",
        "A_min": 0.20,
        "A_max": 0.35,
        "A_default": 0.30,
    },
    "custom": {
        "name": "Пользовательский",
        "description": "Задайте коэффициент вручную",
        "A_min": 0.10,
        "A_max": 0.80,
        "A_default": 0.50,
    },
}


@dataclass
class ThermalBalanceInput:
    """Входные данные для расчёта теплового баланса."""
    # Топливо
    fuel_feed: float = 3660.0          # Подача влажного топлива, кг/ч
    moisture: float = 0.50             # Влажность, доля (0-1)
    q_net_ar: float = 12.42            # Низшая теплота сгорания рабочей массы, МДж/кг
    ash_content: float = 0.20          # Зольность на рабочую массу, доля (0-1)
    bulk_density: float = 400.0        # Насыпная плотность отхода, кг/м³
    
    # Режим горения
    excess_air: float = 1.40           # Коэффициент избытка воздуха (α)
    flue_gas_temp: float = 700.0       # Температура дымовых газов на выходе, °C
    ambient_temp: float = 10.0         # Температура наружного воздуха, °C
    
    # Горелка
    burner_power: float = 1.6          # Мощность горелки (макс), МВт
    burner_min_power: float = 0.4      # Мощность горелки (мин), МВт
    
    # Потери
    wall_loss_pct: float = 0.08        # Потери через футеровку, доля
    ash_temp: float = 600.0            # Температура золы на выходе, °C
    
    # Геометрия барабана
    drum_length: float = 10.0          # Длина барабана, м
    drum_diameter: float = 1.9         # Диаметр барабана, м
    drum_angle: float = 2.0            # Угол наклона барабана, °
    drum_rpm: float = 1.5              # Скорость вращения, об/мин
    
    # Материал
    material_type: str = "fibrous_light"
    material_coeff: float = 0.30       # Коэффициент материала A
    
    # Ограничения
    max_heat_load: float = 200.0       # Максимальная тепловая нагрузка, кВт/м³
    max_fill_ratio: float = 0.20       # Максимальная степень заполнения, доля


@dataclass
class BurnoutResult:
    """Результаты оценки полноты выгорания."""
    # Геометрия
    drum_volume: float = 0.0
    
    # Время пребывания
    material_velocity: float = 0.0     # Скорость движения материала, м/мин
    residence_time: float = 0.0        # Время пребывания, мин
    
    # Загрузка
    mass_in_drum: float = 0.0
    volume_in_drum: float = 0.0
    fill_ratio: float = 0.0
    
    # Время выгорания
    t_drying: float = 0.0
    t_heating: float = 0.0
    t_combustion: float = 0.0
    t_burnout: float = 0.0
    t_required: float = 0.0
    
    # Оценка
    time_ratio: float = 0.0
    k_diameter: float = 0.0
    burnout_efficiency: float = 0.0
    
    # Тепловая нагрузка
    heat_load: float = 0.0
    heat_load_ok: bool = True
    
    # Выводы
    fill_ratio_ok: bool = True
    time_ok: bool = True
    overall_ok: bool = True


@dataclass
class ThermalBalanceResult:
    """Результаты расчёта теплового баланса."""
    input: ThermalBalanceInput = None

    # Массовый баланс
    fuel_feed: float = 0.0
    water_mass: float = 0.0
    dry_mass: float = 0.0
    ash_mass: float = 0.0
    combustible_mass: float = 0.0

    # Теплота сгорания
    q_net_ar: float = 0.0

    # Тепловой приход
    q_fuel_nominal: float = 0.0        # Номинальное тепловыделение (если бы всё сгорело)
    q_fuel_actual: float = 0.0         # Фактическое тепловыделение (с учётом полноты выгорания)
    q_burner: float = 0.0
    q_input_nominal: float = 0.0
    q_input_actual: float = 0.0

    # Полнота выгорания
    burnout: BurnoutResult = None

    # Расчёт воздуха
    v_air_theoretical_per_kg: float = 0.0
    v_air_theoretical_total: float = 0.0
    v_air_actual: float = 0.0
    m_air: float = 0.0

    # Дымовые газы
    v_flue: float = 0.0
    m_flue: float = 0.0
    v_flue_actual_hot: float = 0.0
    v_flue_actual_cold: float = 0.0

    # Температура
    t_adiabatic: float = 0.0           # Теоретическая температура адиабатного горения, °C

    # Тепловой расход
    q_flue_gas: float = 0.0
    q_wall: float = 0.0
    q_ash: float = 0.0
    q_loss_total: float = 0.0

    # Тепловой баланс
    q_useful_no_burner: float = 0.0
    q_useful_with_burner: float = 0.0

    # КПД
    efficiency_no_burner: float = 0.0
    efficiency_with_burner: float = 0.0

    # O2 в сухих газах
    o2_dry_approx: float = 0.0


def calculate_residence_time(
    drum_length: float,
    drum_diameter: float,
    drum_angle_deg: float,
    drum_rpm: float,
    material_coeff: float,
) -> Tuple[float, float]:
    """
    Рассчитывает время пребывания материала в барабане.
    
    Формула:
    v = A × D × n × tan(β)
    t = L / v
    
    где:
    - A — коэффициент материала
    - D — диаметр барабана, м
    - n — скорость вращения, об/мин
    - β — угол наклона, градусы
    """
    if drum_angle_deg <= 0 or drum_rpm <= 0 or drum_diameter <= 0 or material_coeff <= 0:
        return 0.0, 0.0

    angle_rad = math.radians(drum_angle_deg)
    v_material = material_coeff * drum_diameter * drum_rpm * math.tan(angle_rad)

    if v_material <= 0:
        return 0.0, 0.0

    t_residence = drum_length / (v_material*9)

    return v_material, t_residence


def calculate_burnout_efficiency(
    t_residence: float,
    t_required: float,
    drum_diameter: float,
) -> Tuple[float, float]:
    """
    Рассчитывает полноту выгорания с учётом времени пребывания и диаметра.
    
    Returns
    -------
    tuple
        (полнота выгорания, коэффициент диаметра)
    """
    if t_required <= 0:
        return 0.99, 1.0

    # Коэффициент запаса времени
    k_time = t_residence / t_required

    # Базовая полнота выгорания по времени
    if k_time >= 1.5:
        eta_base = 0.99
    elif k_time >= 1.2:
        eta_base = 0.95 + 0.04 * (k_time - 1.2) / 0.3
    elif k_time >= 1.0:
        eta_base = 0.90 + 0.05 * (k_time - 1.0) / 0.2
    elif k_time >= 0.7:
        eta_base = 0.75 + 0.15 * (k_time - 0.7) / 0.3
    else:
        eta_base = 0.50 + 0.25 * k_time / 0.7

    # Коэффициент диаметра (линейная зависимость)
    # D = 1.0 м → k = 0.85
    # D = 3.0 м → k = 1.00
    k_diameter = 0.85 + 0.15 * (drum_diameter - 1.0) / 2.0
    k_diameter = max(0.80, min(1.10, k_diameter))

    # Итоговая полнота выгорания
    eta_burnout = eta_base * k_diameter
    eta_burnout = max(0.0, min(0.99, eta_burnout))

    return eta_burnout, k_diameter


def calculate_required_burnout_time(
    moisture: float,
    flue_gas_temp: float,
) -> Tuple[float, float, float, float, float]:
    """
    Рассчитывает необходимое время выгорания по стадиям.
    """
    # Время сушки (зависит от влажности)
    t_drying = 5.0 + 20.0 * moisture

    # Время нагрева и воспламенения
    t_heating = 4.0

    # Время основного горения (зависит от температуры в барабане)
    if flue_gas_temp >= 1000:
        t_combustion = 10.0
    elif flue_gas_temp >= 700:
        t_combustion = 10.0 + 10.0 * (1000.0 - flue_gas_temp) / 300.0
    else:
        t_combustion = 20.0 + 10.0 * (700.0 - flue_gas_temp) / 300.0

    # Время дожигания
    t_burnout = 5.0

    # Итого
    t_required = t_drying + t_heating + t_combustion + t_burnout

    return t_drying, t_heating, t_combustion, t_burnout, t_required


def calculate_adiabatic_temp(
    q_net_ar: float,
    v_flue_per_kg: float,
    ambient_temp: float,
    combustion_efficiency: float = 0.75,
) -> float:
    """
    Рассчитывает теоретическую и реальную температуру горения.
    
    Parameters
    ----------
    q_net_ar : float
        Низшая теплота сгорания, МДж/кг.
    v_flue_per_kg : float
        Объём дымовых газов на кг сгоревшего топлива, Нм³/кг.
    ambient_temp : float
        Температура окружающего воздуха, °C.
    combustion_efficiency : float
        Доля тепла, остающаяся в газах (0.7-0.85).
        Учитывает потери на излучение и теплообмен с материалом.
    
    Returns
    -------
    float
        Ожидаемая температура в зоне горения, °C.
    """
    # Масса дымовых газов на кг топлива
    m_flue_per_kg = v_flue_per_kg * 1.3  # кг/кг
    
    # Средняя теплоёмкость дымовых газов
    cp_flue = 1.15  # кДж/(кг·K)
    
    if m_flue_per_kg > 0 and cp_flue > 0:
        # Теоретическая адиабатная температура
        t_adiabatic = ambient_temp + (q_net_ar * 1000.0) / (m_flue_per_kg * cp_flue)
    else:
        t_adiabatic = ambient_temp
    
    # Реальная температура горения
    # T_real = T_amb + (T_adiabatic - T_amb) × combustion_efficiency
    t_combustion = ambient_temp + (t_adiabatic - ambient_temp) * combustion_efficiency
    
    return t_combustion

def calculate_thermal_balance(inp: ThermalBalanceInput) -> ThermalBalanceResult:
    """
    Выполняет полный расчёт теплового баланса.
    """
    res = ThermalBalanceResult(input=inp)

    # =========================================================
    # 1. МАССОВЫЙ БАЛАНС
    # =========================================================
    res.fuel_feed = inp.fuel_feed
    res.water_mass = inp.fuel_feed * inp.moisture
    res.dry_mass = inp.fuel_feed - res.water_mass
    res.ash_mass = inp.fuel_feed * inp.ash_content
    res.combustible_mass = res.dry_mass - res.ash_mass

    # =========================================================
    # 2. ТЕПЛОТА СГОРАНИЯ
    # =========================================================
    res.q_net_ar = max(0.0, inp.q_net_ar)

    # Номинальное тепловыделение (если бы всё сгорело)
    res.q_fuel_nominal = (inp.fuel_feed * res.q_net_ar) / 3600.0
    res.q_burner = inp.burner_power
    res.q_input_nominal = res.q_fuel_nominal + inp.burner_power

    # =========================================================
    # 3. ГЕОМЕТРИЯ БАРАБАНА И ВРЕМЯ ПРЕБЫВАНИЯ
    # =========================================================
    drum_volume = math.pi * (inp.drum_diameter ** 2) / 4.0 * inp.drum_length

    v_material, t_residence = calculate_residence_time(
        inp.drum_length,
        inp.drum_diameter,
        inp.drum_angle,
        inp.drum_rpm,
        inp.material_coeff,
    )

    # Масса и объём отхода в барабане
    mass_in_drum = inp.fuel_feed * (t_residence / 60.0)
    volume_in_drum = mass_in_drum / inp.bulk_density if inp.bulk_density > 0 else 0.0
    fill_ratio = volume_in_drum / drum_volume if drum_volume > 0 else 1.0

    # =========================================================
    # 4. НЕОБХОДИМОЕ ВРЕМЯ ВЫГОРАНИЯ
    # =========================================================
    t_drying, t_heating, t_combustion, t_burnout, t_required = \
        calculate_required_burnout_time(inp.moisture, inp.flue_gas_temp)

    # =========================================================
    # 5. ПОЛНОТА ВЫГОРАНИЯ
    # =========================================================
    eta_burnout, k_diameter = calculate_burnout_efficiency(
        t_residence, t_required, inp.drum_diameter
    )

    # =========================================================
    # 6. ФАКТИЧЕСКОЕ ТЕПЛОВЫДЕЛЕНИЕ
    # =========================================================
    res.q_fuel_actual = res.q_fuel_nominal * eta_burnout
    res.q_input_actual = res.q_fuel_actual + inp.burner_power

    # =========================================================
    # 7. РАСЧЁТ РАСХОДА ВОЗДУХА (с учётом фактического сгорания)
    # =========================================================
    # Теоретический объём воздуха
    if res.q_net_ar > 0:
        res.v_air_theoretical_per_kg = res.q_net_ar / 4.0
    else:
        res.v_air_theoretical_per_kg = 0.0

    # Расчёт для фактически сгоревшего топлива
    fuel_burned = inp.fuel_feed * eta_burnout
    res.v_air_theoretical_total = fuel_burned * res.v_air_theoretical_per_kg
    res.v_air_actual = inp.excess_air * res.v_air_theoretical_total
    res.m_air = res.v_air_actual * 1.293

    # =========================================================
    # 8. ДЫМОВЫЕ ГАЗЫ
    # =========================================================
    res.m_flue = res.m_air + fuel_burned
    res.v_flue = res.v_air_actual + fuel_burned * 1.0

    # Объём при рабочей температуре
    t_hot_k = inp.flue_gas_temp + 273.0
    res.v_flue_actual_hot = res.v_flue * (t_hot_k / 273.0)

    # Объём при 150°C (для газоочистки)
    t_cold_k = 150.0 + 273.0
    res.v_flue_actual_cold = res.v_flue * (t_cold_k / 273.0)

    # =========================================================
    # 9. ТЕОРЕТИЧЕСКАЯ ТЕМПЕРАТУРА ГОРЕНИЯ
    # =========================================================
    v_flue_per_kg = res.v_flue / fuel_burned if fuel_burned > 0 else 0.0
    res.t_adiabatic = calculate_adiabatic_temp(
        res.q_net_ar, v_flue_per_kg, inp.ambient_temp
    )

    # =========================================================
    # 10. ТЕПЛОВОЙ РАСХОД
    # =========================================================
    # Тепло, уносимое дымовыми газами
    cp_flue = 1.15  # кДж/(кг·K)
    delta_t_gas = inp.flue_gas_temp - inp.ambient_temp
    res.q_flue_gas = (res.m_flue * cp_flue * delta_t_gas) / 3600000.0

    # Потери через футеровку (от фактического тепловыделения)
    res.q_wall = inp.wall_loss_pct * res.q_fuel_actual

    # Потери с золой
    cp_ash = 0.8  # кДж/(кг·K)
    delta_t_ash = inp.ash_temp - inp.ambient_temp
    res.q_ash = (res.ash_mass * cp_ash * delta_t_ash) / 3600000.0

    res.q_loss_total = res.q_flue_gas + res.q_wall + res.q_ash

    # =========================================================
    # 11. ТЕПЛОВОЙ БАЛАНС
    # =========================================================
    res.q_useful_no_burner = res.q_fuel_actual - res.q_loss_total
    if res.q_useful_no_burner < 0:
        res.q_useful_no_burner = 0.0

    res.q_useful_with_burner = res.q_input_actual - res.q_loss_total
    if res.q_useful_with_burner < 0:
        res.q_useful_with_burner = 0.0

    # =========================================================
    # 12. КПД
    # =========================================================
    if res.q_fuel_actual > 0:
        res.efficiency_no_burner = res.q_useful_no_burner / res.q_fuel_actual
    else:
        res.efficiency_no_burner = 0.0

    if res.q_input_actual > 0:
        res.efficiency_with_burner = res.q_useful_with_burner / res.q_input_actual
    else:
        res.efficiency_with_burner = 0.0

    # =========================================================
    # 13. O2 В СУХИХ ГАЗАХ
    # =========================================================
    if inp.excess_air > 1.0:
        res.o2_dry_approx = 21.0 * (inp.excess_air - 1.0) / inp.excess_air
    else:
        res.o2_dry_approx = 0.0

    # =========================================================
    # 14. РЕЗУЛЬТАТЫ ПОЛНОТЫ ВЫГОРАНИЯ
    # =========================================================
    burnout = BurnoutResult()
    burnout.drum_volume = drum_volume
    burnout.material_velocity = v_material
    burnout.residence_time = t_residence
    burnout.mass_in_drum = mass_in_drum
    burnout.volume_in_drum = volume_in_drum
    burnout.fill_ratio = fill_ratio
    burnout.fill_ratio_ok = fill_ratio <= inp.max_fill_ratio

    burnout.t_drying = t_drying
    burnout.t_heating = t_heating
    burnout.t_combustion = t_combustion
    burnout.t_burnout = t_burnout
    burnout.t_required = t_required

    if t_required > 0:
        burnout.time_ratio = t_residence / t_required
    else:
        burnout.time_ratio = 1.0

    burnout.time_ok = burnout.time_ratio >= 1.0
    burnout.k_diameter = k_diameter
    burnout.burnout_efficiency = eta_burnout

    # Тепловая нагрузка (от фактического тепловыделения)
    if drum_volume > 0:
        burnout.heat_load = (res.q_fuel_actual * 1000.0) / drum_volume
    else:
        burnout.heat_load = 0.0

    burnout.heat_load_ok = burnout.heat_load <= inp.max_heat_load
    burnout.overall_ok = burnout.fill_ratio_ok and burnout.time_ok and burnout.heat_load_ok

    res.burnout = burnout

    return res


def get_summary_table(res: ThermalBalanceResult) -> list:
    """Возвращает сводную таблицу теплового баланса."""
    q_in = res.q_input_actual
    if q_in == 0:
        q_in = 1.0

    table = [
        {"Статья": "ПРИХОД", "МВт": "", "%": ""},
        {"Статья": "Тепло от топлива (фактическое)", "МВт": f"{res.q_fuel_actual:.3f}", "%": f"{res.q_fuel_actual/q_in*100:.1f}%"},
        {"Статья": "Тепло от горелки", "МВт": f"{res.input.burner_power:.3f}", "%": f"{res.input.burner_power/q_in*100:.1f}%"},
        {"Статья": "Итого приход", "МВт": f"{q_in:.3f}", "%": "100%"},
        {"Статья": "", "МВт": "", "%": ""},
        {"Статья": "РАСХОД", "МВт": "", "%": ""},
        {"Статья": f"Уходящие газы ({res.input.flue_gas_temp:.0f}°C)", "МВт": f"{res.q_flue_gas:.3f}", "%": f"{res.q_flue_gas/q_in*100:.1f}%"},
        {"Статья": "Потери через футеровку", "МВт": f"{res.q_wall:.3f}", "%": f"{res.q_wall/q_in*100:.1f}%"},
        {"Статья": "Потери с золой", "МВт": f"{res.q_ash:.3f}", "%": f"{res.q_ash/q_in*100:.1f}%"},
        {"Статья": "Полезное тепло", "МВт": f"{res.q_useful_with_burner:.3f}", "%": f"{res.q_useful_with_burner/q_in*100:.1f}%"},
        {"Статья": "Итого расход", "МВт": f"{q_in:.3f}", "%": "100%"},
        {"Статья": "", "МВт": "", "%": ""},
        {"Статья": "СПРАВКА", "МВт": "", "%": ""},
        {"Статья": "Тепло от топлива (номинальное)", "МВт": f"{res.q_fuel_nominal:.3f}", "%": ""},
        {"Статья": "Полнота выгорания", "МВт": f"{res.burnout.burnout_efficiency*100:.1f}%", "%": ""},
        {"Статья": "Удельная тепловая нагрузка", "МВт": f"{res.burnout.heat_load:.0f} кВт/м³", "%": f"лимит {res.input.max_heat_load:.0f}"},
        {"Статья": "T адиабатного горения (оценка)", "МВт": f"{res.t_adiabatic:.0f}°C", "%": ""},
    ]
    return table


def get_flue_gas_params(res: ThermalBalanceResult) -> list:
    """Возвращает параметры дымовых газов для теплообменника."""
    table = [
        {"Параметр": "Объём дымовых газов (н.у.)", "Значение": f"{res.v_flue:.0f} Нм³/ч"},
        {"Параметр": "Масса дымовых газов", "Значение": f"{res.m_flue:.0f} кг/ч"},
        {"Параметр": "Объём при температуре газов", "Значение": f"{res.v_flue_actual_hot:.0f} м³/ч"},
        {"Параметр": "Объём после охлаждения до 150°C", "Значение": f"{res.v_flue_actual_cold:.0f} м³/ч"},
        {"Параметр": "Температура на выходе барабана", "Значение": f"{res.input.flue_gas_temp:.0f}°C"},
        {"Параметр": "T адиабатного горения (оценка)", "Значение": f"{res.t_adiabatic:.0f}°C"},
        {"Параметр": "Тепловая нагрузка на теплообменник", "Значение": f"{res.q_useful_with_burner:.3f} МВт"},
        {"Параметр": "O₂ в сухих газах (приближённо)", "Значение": f"{res.o2_dry_approx:.1f}%"},
    ]
    return table


def get_burnout_params(res: ThermalBalanceResult) -> list:
    """Возвращает параметры полноты выгорания."""
    b = res.burnout
    table = [
        {"Параметр": "Объём барабана", "Значение": f"{b.drum_volume:.2f} м³"},
        {"Параметр": "Скорость движения материала", "Значение": f"{b.material_velocity:.3f} м/мин"},
        {"Параметр": "Время пребывания (расчётное)", "Значение": f"{b.residence_time:.1f} мин"},
        {"Параметр": "Масса отхода в барабане", "Значение": f"{b.mass_in_drum:.0f} кг"},
        {"Параметр": "Объём отхода в барабане", "Значение": f"{b.volume_in_drum:.2f} м³"},
        {"Параметр": "Степень заполнения", "Значение": f"{b.fill_ratio*100:.1f}%"},
        {"Параметр": "", "Значение": ""},
        {"Параметр": "Время сушки", "Значение": f"{b.t_drying:.1f} мин"},
        {"Параметр": "Время нагрева", "Значение": f"{b.t_heating:.1f} мин"},
        {"Параметр": "Время горения", "Значение": f"{b.t_combustion:.1f} мин"},
        {"Параметр": "Время дожигания", "Значение": f"{b.t_burnout:.1f} мин"},
        {"Параметр": "Необходимое время выгорания", "Значение": f"{b.t_required:.1f} мин"},
        {"Параметр": "", "Значение": ""},
        {"Параметр": "Коэффициент запаса времени", "Значение": f"{b.time_ratio:.2f}"},
        {"Параметр": "Коэффициент диаметра", "Значение": f"{b.k_diameter:.3f}"},
        {"Параметр": "Полнота выгорания", "Значение": f"{b.burnout_efficiency*100:.1f}%"},
        {"Параметр": "", "Значение": ""},
        {"Параметр": "Удельная тепловая нагрузка", "Значение": f"{b.heat_load:.0f} кВт/м³"},
        {"Параметр": "Тепловая нагрузка в норме", "Значение": "✅ Да" if b.heat_load_ok else "❌ Нет"},
    ]
    return table