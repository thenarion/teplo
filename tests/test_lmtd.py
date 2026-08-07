"""Тесты для расчёта LMTD и площади."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from calc import hx_sizing
import pytest
import math


def test_lmtd_counterflow():
    """Противоточная схема — базовый случай."""
    # T_hot: 900→150, T_cold: 20→80
    # dT1 = 900-80=820, dT2 = 150-20=130
    # LMTD = (820-130)/ln(820/130) ≈ 373 K
    lmtd = hx_sizing.lmtd(900, 150, 20, 80)
    assert abs(lmtd - 373) < 5


def test_lmtd_equal_dt():
    """Когда dT1 = dT2 — LMTD = dT."""
    lmtd = hx_sizing.lmtd(500, 200, 100, 400)
    # dT1 = 500-400=100, dT2 = 200-100=100
    assert abs(lmtd - 100) < 1


def test_lmtd_crossover():
    """Температурный перекрёст — возвращает 0."""
    # T_hot_out < T_cold_in → dT2 < 0
    lmtd = hx_sizing.lmtd(500, 50, 100, 200)
    assert lmtd == 0


def test_lmtd_negative_dt():
    """Отрицательный dT — возвращает 0."""
    lmtd = hx_sizing.lmtd(100, 200, 300, 400)
    assert lmtd == 0


def test_heat_transfer_area():
    """Базовый расчёт площади."""
    # A = Q / (U * F * LMTD)
    A = hx_sizing.heat_transfer_area(100000, 50, 0.9, 200)
    expected = 100000 / (50 * 0.9 * 200)
    assert abs(A - expected) < 0.01


def test_heat_transfer_area_zero_params():
    """Нулевые параметры — возвращает 0."""
    assert hx_sizing.heat_transfer_area(100000, 0, 0.9, 200) == 0
    assert hx_sizing.heat_transfer_area(100000, 50, 0, 200) == 0
    assert hx_sizing.heat_transfer_area(100000, 50, 0.9, 0) == 0


def test_area_for_u_range():
    """Площадь для трёх U."""
    result = hx_sizing.area_for_u_range(100000, 0.9, 200, 30, 60, 120)
    assert result["A_min"] < result["A_design"] < result["A_max"]
    assert result["U_min"] == 30
    assert result["U_design"] == 60
    assert result["U_max"] == 120


def test_validate_lmtd_ok():
    """Валидный случай — умеренный разброс."""
    # dT1 = 400-80=320, dT2 = 150-20=130, ratio ≈ 2.5 — без предупреждения
    warnings = hx_sizing.validate_lmtd(400, 150, 20, 80)
    assert len(warnings) == 0


def test_validate_lmtd_crossover():
    """Перекрёст — ошибка."""
    warnings = hx_sizing.validate_lmtd(500, 50, 100, 200)
    assert len(warnings) > 0


def test_validate_lmtd_large_ratio():
    """Большой разброс dT — предупреждение."""
    warnings = hx_sizing.validate_lmtd(1000, 200, 20, 30)
    assert len(warnings) > 0
