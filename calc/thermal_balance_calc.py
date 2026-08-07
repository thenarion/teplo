"""
Расчёт теплового баланса сжигания топлива во вращающейся барабанной печи.
Включает оценку полноты выгорания и тепловую нагрузку на барабан.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ThermalBalanceInput:
    """Входные данные для расчёта теплового баланса."""
    # Топливо
    fuel_feed: float = 3660.0          # Подача влажного топлива, кг/ч
    moisture: float = 0.50             # Влажность, доля (0-1)
    q_net_ar: float = 12.42            # Низшая теплота сгорания рабочей массы, МДж/кг
    ash_content: float = 0.20          # Зольность на рабочую массу, доля (0-1)
    
    # Режим горения
    excess_air: float = 1.40           # Коэффициент избытка воздуха (α)
    flue_gas_temp: float = 700.0       # Температура дымовых газов на выходе, °C
    ambient_temp: float = 10.0         # Температура наружного воздуха, °C
    
    # Горелка
    burner_power: float = 1.6          # Мощность горелки (макс), МВт
    burner_min_power: float = 0.4      # Мощность горелки (мин), МВт
    
    # Потери
    wall_loss_pct: float = 0.08        # Потери через футеровку, доля
    unburned_pct: float = 0.03         # Недожог, доля
    ash_temp: float = 600.0            # Температура золы на выходе, °C
    
    # Геометрия барабана
    drum_length: float = 10.0          # Длина барабана, м
    drum_diameter: float = 1.9         # Диаметр барабана, м
    residence_time: float = 40.0       # Время пребывания отхода, мин
    bulk_density: float = 400.0        # Насыпная плотность отхода, кг/м³
    
    # Ограничения
    max_heat_load: float = 200.0       # Максимальная тепловая нагрузка, кВт/м³
    max_fill_ratio: float = 0.20       # Максимальная степень заполнения, доля


@dataclass
class BurnoutResult:
    """Результаты оценки полноты выгорания."""
    # Геометрия
    drum_volume: float = 0.0           # Объём барабана, м³
    
    # Загрузка
    mass_in_drum: float = 0.0          # Масса отхода в барабане, кг
    volume_in_drum: float = 0.0        # Объём отхода в барабане, м³
    fill_ratio: float = 0.0            # Степень заполнения, доля
    
    # Время выгорания
    t_drying: float = 0.0              # Время сушки, мин
    t_heating: float = 0.0             # Время нагрева, мин
    t_combustion: float = 0.0          # Время горения, мин
    t_burnout: float = 0.0             # Время дожигания, мин
    t_required: float = 0.0            # Необходимое время выгорания, мин
    
    # Оценка
    time_ratio: float = 0.0            # Коэффициент запаса времени
    burnout_efficiency: float = 0.0    # Полнота выгорания, доля
    
    # Тепловая нагрузка
    heat_load: float = 0.0             # Тепловая нагрузка, кВт/м³
    heat_load_ok: bool = True          # Тепловая нагрузка в норме
    
    # Выводы
    fill_ratio_ok: bool = True         # Степень заполнения в норме
    time_ok: bool = True               # Время пребывания достаточно
    overall_ok: bool = True            # Общий вывод


@dataclass
class ThermalBalanceResult:
    """Результаты расчёта теплового баланса."""
    # Входные данные (копия)
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
    q_fuel: float = 0.0
    q_burner: float = 0.0
    q_air: float = 0.0
    q_input_no_burner: float = 0.0
    q_input_with_burner: float = 0.0

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

    # Тепловой расход
    q_flue_gas: float = 0.0
    q_wall: float = 0.0
    q_ash: float = 0.0
    q_unburned: float = 0.0
    q_loss_total: float = 0.0

    # Тепловой баланс
    q_useful_no_burner: float = 0.0
    q_useful_with_burner: float = 0.0

    # КПД
    efficiency_no_burner: float = 0.0
    efficiency_with_burner: float = 0.0

    # O2 в сухих газах (приближённо)
    o2_dry_approx: float = 0.0
    
    # Полнота выгорания
    burnout: BurnoutResult = None


def calculate_burnout(inp: ThermalBalanceInput, q_fuel_mw: float) -> BurnoutResult:
    """
    Рассчитывает полноту выгорания отхода в барабане.

    Parameters
    ----------
    inp : ThermalBalanceInput
        Входные данные расчёта.
    q_fuel_mw : float
        Тепловыделение от топлива, МВт.

    Returns
    -------
    BurnoutResult
        Результаты оценки полноты выгорания.
    """
    res = BurnoutResult()

    # =========================================================
    # 1. ГЕОМЕТРИЯ БАРАБАНА
    # =========================================================
    import math
    res.drum_volume = math.pi * (inp.drum_diameter ** 2) / 4.0 * inp.drum_length

    # =========================================================
    # 2. МАССА И ОБЪЁМ ОТХОДА В БАРАБАНЕ
    # =========================================================
    # Масса отхода в барабане
    res.mass_in_drum = inp.fuel_feed * (inp.residence_time / 60.0)

    # Объём отхода в барабане
    if inp.bulk_density > 0:
        res.volume_in_drum = res.mass_in_drum / inp.bulk_density
    else:
        res.volume_in_drum = 0.0

    # Степень заполнения
    if res.drum_volume > 0:
        res.fill_ratio = res.volume_in_drum / res.drum_volume
    else:
        res.fill_ratio = 1.0

    # Проверка степени заполнения
    res.fill_ratio_ok = res.fill_ratio <= inp.max_fill_ratio

    # =========================================================
    # 3. НЕОБХОДИМОЕ ВРЕМЯ ВЫГОРАНИЯ
    # =========================================================
    # Время сушки (зависит от влажности)
    # Эмпирическая формула: 5 + 20 * W минут
    res.t_drying = 5.0 + 20.0 * inp.moisture

    # Время нагрева и воспламенения
    # Примерно 3-5 минут
    res.t_heating = 4.0

    # Время основного горения (зависит от температуры)
    # При 700°C: ~20 мин, при 1000°C: ~10 мин
    if inp.flue_gas_temp >= 1000:
        res.t_combustion = 10.0
    elif inp.flue_gas_temp >= 700:
        res.t_combustion = 10.0 + 10.0 * (1000.0 - inp.flue_gas_temp) / 300.0
    else:
        res.t_combustion = 20.0 + 10.0 * (700.0 - inp.flue_gas_temp) / 300.0

    # Время дожигания
    res.t_burnout = 5.0

    # Итого необходимое время
    res.t_required = res.t_drying + res.t_heating + res.t_combustion + res.t_burnout

    # =========================================================
    # 4. КОЭФФИЦИЕНТ ЗАПАСА ВРЕМЕНИ
    # =========================================================
    if res.t_required > 0:
        res.time_ratio = inp.residence_time / res.t_required
    else:
        res.time_ratio = 1.0

    # =========================================================
    # 5. ПОЛНОТА ВЫГОРАНИЯ
    # =========================================================
    # Эмпирическая зависимость полноты выгорания от коэффициента запаса времени
    if res.time_ratio >= 1.5:
        res.burnout_efficiency = 0.99
    elif res.time_ratio >= 1.2:
        res.burnout_efficiency = 0.95 + 0.04 * (res.time_ratio - 1.2) / 0.3
    elif res.time_ratio >= 1.0:
        res.burnout_efficiency = 0.90 + 0.05 * (res.time_ratio - 1.0) / 0.2
    elif res.time_ratio >= 0.7:
        res.burnout_efficiency = 0.75 + 0.15 * (res.time_ratio - 0.7) / 0.3
    else:
        res.burnout_efficiency = 0.50 + 0.25 * res.time_ratio / 0.7

    # Ограничение диапазона
    res.burnout_efficiency = max(0.0, min(1.0, res.burnout_efficiency))

    # Проверка времени
    res.time_ok = res.time_ratio >= 1.0

    # =========================================================
    # 6. ТЕПЛОВАЯ НАГРУЗКА НА БАРАБАН
    # =========================================================
    # Тепловая нагрузка в кВт/м³
    if res.drum_volume > 0:
        res.heat_load = (q_fuel_mw * 1000.0) / res.drum_volume  # МВт → кВт
    else:
        res.heat_load = 0.0

    # Проверка тепловой нагрузки
    res.heat_load_ok = res.heat_load <= inp.max_heat_load

    # =========================================================
    # 7. ОБЩИЙ ВЫВОД
    # =========================================================
    res.overall_ok = res.fill_ratio_ok and res.time_ok and res.heat_load_ok

    return res


def calculate_thermal_balance(inp: ThermalBalanceInput) -> ThermalBalanceResult:
    """
    Выполняет полный расчёт теплового баланса.

    Parameters
    ----------
    inp : ThermalBalanceInput
        Входные данные расчёта.

    Returns
    -------
    ThermalBalanceResult
        Полные результаты расчёта.
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
    # 2. ТЕПЛОТА СГОРАНИЯ (задаётся напрямую)
    # =========================================================
    res.q_net_ar = inp.q_net_ar

    # Защита от отрицательных значений
    if res.q_net_ar < 0:
        res.q_net_ar = 0.0

    # =========================================================
    # 3. ТЕПЛОВОЙ ПРИХОД
    # =========================================================
    # Тепло от сгорания топлива (МВт)
    # fuel_feed [кг/ч] × q_net_ar [МДж/кг] = МДж/ч
    # МДж/ч / 3600 = МВт
    res.q_fuel = (inp.fuel_feed * res.q_net_ar) / 3600.0

    # Тепло от горелки
    res.q_burner = inp.burner_power
    res.q_air = 0.0  # Воздух не подогрет

    # Итого приход
    res.q_input_no_burner = res.q_fuel
    res.q_input_with_burner = res.q_fuel + inp.burner_power

    # =========================================================
    # 4. РАСЧЁТ РАСХОДА ВОЗДУХА
    # =========================================================
    # Теоретический объём воздуха (Нм³/кг)
    if res.q_net_ar > 0:
        res.v_air_theoretical_per_kg = res.q_net_ar / 4.0
    else:
        res.v_air_theoretical_per_kg = 0.0

    # Теоретический объём на всю подачу
    res.v_air_theoretical_total = inp.fuel_feed * res.v_air_theoretical_per_kg

    # Фактический объём воздуха
    res.v_air_actual = inp.excess_air * res.v_air_theoretical_total

    # Масса воздуха (ρ_air = 1.293 кг/Нм³)
    res.m_air = res.v_air_actual * 1.293

    # =========================================================
    # 5. РАСЧЁТ ОБЪЁМА ДЫМОВЫХ ГАЗОВ
    # =========================================================
    v_fuel_gases = inp.fuel_feed * 1.0

    # Общий объём дымовых газов
    res.v_flue = res.v_air_actual + v_fuel_gases

    # Масса дымовых газов (ρ_flue ≈ 1.3 кг/Нм³ при н.у.)
    res.m_flue = res.v_flue * 1.3

    # Фактический объём при температуре газов
    t_hot_k = inp.flue_gas_temp + 273.0
    res.v_flue_actual_hot = res.v_flue * (t_hot_k / 273.0)

    # Фактический объём при 150°C (для газоочистки)
    t_cold_k = 150.0 + 273.0
    res.v_flue_actual_cold = res.v_flue * (t_cold_k / 273.0)

    # =========================================================
    # 6. ТЕПЛОВОЙ РАСХОД
    # =========================================================
    # 6.1. Тепло, уносимое дымовыми газами
    # m_flue [кг/ч] × cp [кДж/(кг·К)] × ΔT [К] = кДж/ч
    # кДж/ч / 3600000 = МВт
    cp_flue = 1.15  # кДж/(кг·K) при ~700°C
    delta_t_gas = inp.flue_gas_temp - inp.ambient_temp
    res.q_flue_gas = (res.m_flue * cp_flue * delta_t_gas) / 3600000.0

    # 6.2. Потери через футеровку
    res.q_wall = inp.wall_loss_pct * res.q_fuel

    # 6.3. Потери с золой
    # m_ash [кг/ч] × cp [кДж/(кг·К)] × ΔT [К] = кДж/ч
    # кДж/ч / 3600000 = МВт
    cp_ash = 0.8  # кДж/(кг·K)
    delta_t_ash = inp.ash_temp - inp.ambient_temp
    res.q_ash = (res.ash_mass * cp_ash * delta_t_ash) / 3600000.0

    # 6.4. Недожог
    res.q_unburned = inp.unburned_pct * res.q_fuel

    # 6.5. Итого потери
    res.q_loss_total = res.q_flue_gas + res.q_wall + res.q_ash + res.q_unburned

    # =========================================================
    # 7. ТЕПЛОВОЙ БАЛАНС
    # =========================================================
    res.q_useful_no_burner = res.q_fuel - res.q_loss_total
    if res.q_useful_no_burner < 0:
        res.q_useful_no_burner = 0.0

    res.q_useful_with_burner = res.q_input_with_burner - res.q_loss_total
    if res.q_useful_with_burner < 0:
        res.q_useful_with_burner = 0.0

    # =========================================================
    # 8. КПД
    # =========================================================
    if res.q_fuel > 0:
        res.efficiency_no_burner = res.q_useful_no_burner / res.q_fuel
    else:
        res.efficiency_no_burner = 0.0

    if res.q_input_with_burner > 0:
        res.efficiency_with_burner = res.q_useful_with_burner / res.q_input_with_burner
    else:
        res.efficiency_with_burner = 0.0

    # =========================================================
    # 9. O2 В СУХИХ ГАЗАХ (ПРИБЛИЖЁННО)
    # =========================================================
    if inp.excess_air > 1.0:
        res.o2_dry_approx = 21.0 * (inp.excess_air - 1.0) / inp.excess_air
    else:
        res.o2_dry_approx = 0.0

    # =========================================================
    # 10. ПОЛНОТА ВЫГОРАНИЯ И ТЕПЛОВАЯ НАГРУЗКА
    # =========================================================
    res.burnout = calculate_burnout(inp, res.q_fuel)

    return res


def get_summary_table(res: ThermalBalanceResult) -> list:
    """Возвращает сводную таблицу теплового баланса."""
    q_in = res.q_input_with_burner
    if q_in == 0:
        q_in = 1.0

    table = [
        {"Статья": "ПРИХОД", "МВт": "", "%": ""},
        {"Статья": "Тепло от топлива", "МВт": f"{res.q_fuel:.3f}", "%": f"{res.q_fuel/q_in*100:.1f}%"},
        {"Статья": "Тепло от горелки", "МВт": f"{res.input.burner_power:.3f}", "%": f"{res.input.burner_power/q_in*100:.1f}%"},
        {"Статья": "Итого приход", "МВт": f"{q_in:.3f}", "%": "100%"},
        {"Статья": "РАСХОД", "МВт": "", "%": ""},
        {"Статья": f"Уходящие газы ({res.input.flue_gas_temp:.0f}°C)", "МВт": f"{res.q_flue_gas:.3f}", "%": f"{res.q_flue_gas/q_in*100:.1f}%"},
        {"Статья": "Потери через футеровку", "МВт": f"{res.q_wall:.3f}", "%": f"{res.q_wall/q_in*100:.1f}%"},
        {"Статья": "Потери с золой", "МВт": f"{res.q_ash:.3f}", "%": f"{res.q_ash/q_in*100:.1f}%"},
        {"Статья": "Недожог", "МВт": f"{res.q_unburned:.3f}", "%": f"{res.q_unburned/q_in*100:.1f}%"},
        {"Статья": "Полезное тепло", "МВт": f"{res.q_useful_with_burner:.3f}", "%": f"{res.q_useful_with_burner/q_in*100:.1f}%"},
        {"Статья": "Итого расход", "МВт": f"{q_in:.3f}", "%": "100%"},
        {"Статья": "", "МВт": "", "%": ""},
        {"Статья": "ТЕПЛОВАЯ НАГРУЗКА НА БАРАБАН", "МВт": "", "%": ""},
        {"Статья": f"Удельная тепловая нагрузка", "МВт": f"{res.burnout.heat_load:.0f} кВт/м³", "%": f"лимит {res.input.max_heat_load:.0f} кВт/м³"},
    ]
    return table


def get_flue_gas_params(res: ThermalBalanceResult) -> list:
    """Возвращает параметры дымовых газов для теплообменника."""
    table = [
        {"Параметр": "Объём дымовых газов (н.у.)", "Значение": f"{res.v_flue:.0f} Нм³/ч"},
        {"Параметр": "Масса дымовых газов", "Значение": f"{res.m_flue:.0f} кг/ч"},
        {"Параметр": "Объём при температуре газов", "Значение": f"{res.v_flue_actual_hot:.0f} м³/ч"},
        {"Параметр": "Объём после охлаждения до 150°C", "Значение": f"{res.v_flue_actual_cold:.0f} м³/ч"},
        {"Параметр": "Температура на входе в теплообменник", "Значение": f"{res.input.flue_gas_temp:.0f}°C"},
        {"Параметр": "Температура на выходе (рекомендуемая)", "Значение": "150–200°C"},
        {"Параметр": "Тепловая нагрузка на теплообменник", "Значение": f"{res.q_useful_with_burner:.3f} МВт"},
        {"Параметр": "O₂ в сухих газах (приближённо)", "Значение": f"{res.o2_dry_approx:.1f}%"},
    ]
    return table


def get_burnout_params(res: ThermalBalanceResult) -> list:
    """Возвращает параметры полноты выгорания."""
    b = res.burnout
    table = [
        {"Параметр": "Объём барабана", "Значение": f"{b.drum_volume:.2f} м³"},
        {"Параметр": "Масса отхода в барабане", "Значение": f"{b.mass_in_drum:.0f} кг"},
        {"Параметр": "Объём отхода в барабане", "Значение": f"{b.volume_in_drum:.2f} м³"},
        {"Параметр": "Степень заполнения", "Значение": f"{b.fill_ratio*100:.1f}%"},
        {"Параметр": "Время сушки", "Значение": f"{b.t_drying:.1f} мин"},
        {"Параметр": "Время нагрева", "Значение": f"{b.t_heating:.1f} мин"},
        {"Параметр": "Время горения", "Значение": f"{b.t_combustion:.1f} мин"},
        {"Параметр": "Время дожигания", "Значение": f"{b.t_burnout:.1f} мин"},
        {"Параметр": "Необходимое время выгорания", "Значение": f"{b.t_required:.1f} мин"},
        {"Параметр": "Фактическое время пребывания", "Значение": f"{res.input.residence_time:.1f} мин"},
        {"Параметр": "Коэффициент запаса времени", "Значение": f"{b.time_ratio:.2f}"},
        {"Параметр": "Полнота выгорания", "Значение": f"{b.burnout_efficiency*100:.1f}%"},
        {"Параметр": "Удельная тепловая нагрузка", "Значение": f"{b.heat_load:.0f} кВт/м³"},
    ]
    return table