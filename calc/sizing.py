"""
Укрупнённая оценка габаритов теплообменного аппарата.
"""
import math


def gas_flow_cross_section(V_gas_m3h: float, v_gas_ms: float) -> dict:
    """
    Площадь проходного сечения газового тракта и эквивалентный диаметр.

    V_gas_m3h — объёмный расход газа, м³/ч
    v_gas_ms — скорость газа, м/с

    Возвращает dict: A_flow_m2, D_eq_m
    """
    if v_gas_ms <= 0:
        return {"A_flow_m2": 0, "D_eq_m": 0}

    V_m3s = V_gas_m3h / 3600
    A_flow = V_m3s / v_gas_ms
    D_eq = math.sqrt(4 * A_flow / math.pi)

    return {"A_flow_m2": A_flow, "D_eq_m": D_eq}


def hx_volume(A_heat_m2: float, a_specific: float) -> float:
    """
    Объём теплообменной части, м³.
    V = A / a, где a — удельная поверхность, м²/м³.
    """
    if a_specific <= 0:
        return 0.0
    return A_heat_m2 / a_specific


def estimate_dimensions(A_heat_m2: float, A_flow_m2: float,
                        a_specific: float = 40.0,
                        L_depth: float = 1.5) -> dict:
    """
    Оценка габаритов модуля теплообменника.

    A_heat_m2 — поверхность теплообмена, м²
    A_flow_m2 — площадь проходного сечения, м²
    a_specific — удельная поверхность, м²/м³
    L_depth — глубина модуля, м

    Возвращает dict:
      - V_bundle_m3: объём пучка
      - A_front_m2: фронтальная площадь
      - W_m: ширина (поперёк потока)
      - H_m: высота
      - L_m: длина (вдоль потока)
      - mass_kg: ориентировочная масса
    """
    # Объём пучка
    V = hx_volume(A_heat_m2, a_specific)

    # Фронтальная площадь
    if L_depth > 0:
        A_front = V / L_depth
    else:
        A_front = A_flow_m2 if A_flow_m2 > 0 else 0

    # Размеры фронтального сечения (принимаем H/W ≈ 1.5-2)
    if A_front > 0:
        H = math.sqrt(A_front * 1.5)
        W = A_front / H
    else:
        H = 0
        W = 0

    # Ориентировочная масса (стальной каркас + трубы)
    # Принимаем ~50-80 кг/м² поверхности для оребрённых модулей
    mass = A_heat_m2 * 65  # кг

    return {
        "V_bundle_m3": V,
        "A_front_m2": A_front,
        "W_m": W,
        "H_m": H,
        "L_m": L_depth,
        "mass_kg": mass,
    }


def dry_cooler_dimensions(A_front_m2: float, n_fans: int,
                          fan_diameter: float = 1.2) -> dict:
    """
    Оценка габаритов dry cooler.

    A_front_m2 — фронтальная площадь
    n_fans — количество вентиляторов
    fan_diameter — диаметр вентилятора, м

    Возвращает dict:
      - W_m: ширина
      - L_m: длина
      - H_m: высота (ориентировочная)
    """
    if n_fans <= 0:
        return {"W_m": 0, "L_m": 0, "H_m": 0}

    # Вентиляторы располагаются в ряд или в 2 ряда
    if n_fans <= 4:
        cols = n_fans
        rows = 1
    else:
        cols = math.ceil(n_fans / 2)
        rows = 2

    W = cols * (fan_diameter + 0.3)  # зазор между вентиляторами
    L = rows * (fan_diameter + 0.5)  # глубина
    H = 2.0  # типовая высота

    return {"W_m": W, "L_m": L, "H_m": H}
