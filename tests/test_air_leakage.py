"""Тесты для модуля подсосов воздуха."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from calc import air_leakage
import pytest


def test_leak_from_percent():
    """Подсос в % от расхода."""
    result = air_leakage.leak_from_percent(1000, 10)
    assert abs(result - 100) < 0.01


def test_leak_from_percent_zero():
    assert air_leakage.leak_from_percent(1000, 0) == 0


def test_leak_from_orifice():
    """Формула истечения через отверстие."""
    # Пример из ТЗ: Cd=0.6, A=0.01, dp=1000, rho=1.2
    Q = air_leakage.leak_from_orifice(0.01, 1000, 1.2, 0.6)
    assert abs(Q - 0.245) < 0.05  # ~0.245 м³/с


def test_leak_from_o2():
    """Формула по O₂."""
    # Пример из ТЗ: O2_before=8, O2_after=10 → ~18.3%
    frac = air_leakage.leak_from_o2(8, 10)
    assert abs(frac - 0.183) < 0.01


def test_leak_from_o2_no_leak():
    """Нет разницы O₂ → нет подсоса."""
    assert air_leakage.leak_from_o2(8, 8) == 0


def test_leak_from_o2_invalid():
    """Невалидные данные."""
    assert air_leakage.leak_from_o2(10, 8) == 0  # O2_after < O2_before
    assert air_leakage.leak_from_o2(10, 20.9) == 0  # O2_after = 20.9


def test_leak_from_temperature_drop():
    """Формула по падению температуры."""
    # Пример из ТЗ: 900→800, T_amb=20, cp_gas=1.1, cp_air=1.0 → ~14%
    r = air_leakage.leak_from_temperature_drop(900, 800, 20, 1.1, 1.0)
    assert abs(r - 0.141) < 0.02


def test_leak_from_fan_curve():
    """Эмпирическая модель."""
    Q = air_leakage.leak_from_fan_curve(1000, 0.05, 1.0)
    assert abs(Q - 50) < 0.01


def test_calculate_leak_percent():
    """Универсальная функция — режим percent."""
    result = air_leakage.calculate_leak(
        mode="percent",
        Q_gas_m3h=10000,
        leak_percent=10,
    )
    assert abs(result["leak_fraction"] - 0.1) < 0.001
    assert abs(result["leak_value"] - 1000) < 0.1


def test_calculate_leak_o2():
    """Универсальная функция — режим o2."""
    result = air_leakage.calculate_leak(
        mode="o2",
        O2_before=8,
        O2_after=10,
    )
    assert abs(result["leak_fraction"] - 0.183) < 0.01


def test_calculate_leak_high_warning():
    """Предупреждение при высоком подсосе."""
    result = air_leakage.calculate_leak(
        mode="percent",
        Q_gas_m3h=10000,
        leak_percent=60,
    )
    assert result["warning"] is not None


def test_leak_from_temperature_no_drop():
    """Нет падения температуры → нет подсоса."""
    assert air_leakage.leak_from_temperature_drop(800, 800, 20) == 0
