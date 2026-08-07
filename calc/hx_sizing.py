"""
Расчёт LMTD и площади теплообмена.
"""
import math
from typing import Optional


def lmtd(T_hot_in: float, T_hot_out: float,
         T_cold_in: float, T_cold_out: float) -> float:
    """
    Логарифмический средний температурный напор (LMTD) для противоточной схемы.

    dT1 = T_hot_in - T_cold_out
    dT2 = T_hot_out - T_cold_in
    LMTD = (dT1 - dT2) / ln(dT1/dT2)

    Возвращает LMTD в K (или °C, разность одинакова).
    """
    dT1 = T_hot_in - T_cold_out
    dT2 = T_hot_out - T_cold_in

    if dT1 <= 0 or dT2 <= 0:
        return 0.0

    if abs(dT1 - dT2) < 0.01:
        # Если dT1 ≈ dT2, возвращаем арифметическое среднее
        return (dT1 + dT2) / 2.0

    return (dT1 - dT2) / math.log(dT1 / dT2)


def heat_transfer_area(Q_W: float, U: float, F: float,
                       dT_lm: float) -> float:
    """
    Площадь теплообмена.
    A = Q / (U * F * dT_lm)

    Параметры:
        Q_W — тепловая нагрузка, Вт
        U — коэффициент теплопередачи, Вт/(м²·К)
        F — поправочный коэффициент LMTD
        dT_lm — логарифмический средний напор, K

    Возвращает площадь в м².
    """
    if U <= 0 or F <= 0 or dT_lm <= 0:
        return 0.0
    return Q_W / (U * F * dT_lm)


def area_for_u_range(Q_W: float, F: float, dT_lm: float,
                     U_min: float = 30, U_design: float = 60,
                     U_max: float = 120) -> dict:
    """
    Площадь для трёх значений U.
    U_max → A_min (лучший случай)
    U_design → A_design (расчётный)
    U_min → A_max (худший случай)
    """
    return {
        "A_min": heat_transfer_area(Q_W, U_max, F, dT_lm),
        "A_design": heat_transfer_area(Q_W, U_design, F, dT_lm),
        "A_max": heat_transfer_area(Q_W, U_min, F, dT_lm),
        "U_min": U_min,
        "U_design": U_design,
        "U_max": U_max,
    }


def validate_lmtd(T_hot_in: float, T_hot_out: float,
                  T_cold_in: float, T_cold_out: float) -> list:
    """
    Проверки LMTD.
    Возвращает список предупреждений.
    """
    warnings = []
    dT1 = T_hot_in - T_cold_out
    dT2 = T_hot_out - T_cold_in

    if dT1 <= 0:
        warnings.append(
            f"Температурный перекрёст: dT1 = {dT1:.1f}K ≤ 0. "
            "Невозможно обеспечить требуемый нагрев холодного потока."
        )

    if dT2 <= 0:
        warnings.append(
            f"Температурный перекрёст: dT2 = {dT2:.1f}K ≤ 0. "
            "Невозможно обеспечить требуемое охлаждение горячего потока."
        )

    if dT1 > 0 and dT2 > 0:
        ratio = max(dT1, dT2) / min(dT1, dT2)
        if ratio > 4:
            warnings.append(
                f"Большой разброс температурных напоров (dT1/dT2 = {ratio:.1f}). "
                "LMTD может быть неточным, рассмотрите многоходовую схему."
            )

    return warnings
