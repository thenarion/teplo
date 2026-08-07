"""Тесты для теплового баланса."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from calc import heat_balance
import pytest


def test_avg_cp():
    """Средняя теплоёмкость."""
    cp = heat_balance.avg_cp(900, 150)
    assert 1.0 < cp < 1.2


def test_heat_duty_basic():
    """Базовый расчёт тепловой нагрузки."""
    # Q = m * cp * dT [кг/с * кДж/(кг·К) * K * 1000 = Вт]
    Q = heat_balance.heat_duty(5.0, 1.1, 900, 150)
    expected = 5.0 * 1.1 * 1000 * 750
    assert abs(Q - expected) < 1


def test_heat_duty_kW():
    """Тепловая нагрузка в кВт."""
    Q = heat_balance.heat_duty_kW(5.0, 1.1, 900, 150)
    expected = 5.0 * 1.1 * 750
    assert abs(Q - expected) < 1


def test_heat_duty_MW():
    """Тепловая нагрузка в МВт."""
    Q = heat_balance.heat_duty_MW(5.0, 1.1, 900, 150)
    assert abs(Q - 4.125) < 0.1


def test_heat_duty_zero_flow():
    """Нулевой расход — нулевая нагрузка."""
    assert heat_balance.heat_duty(0, 1.1, 900, 150) == 0


def test_heat_duty_same_temp():
    """Одинаковые температуры — нулевая нагрузка."""
    assert heat_balance.heat_duty(5.0, 1.1, 900, 900) == 0


def test_heat_duty_leak_contribution():
    """Вклад подсоса воздуха."""
    result = heat_balance.heat_duty_leak_contribution(
        m_gas_kgs=5.0,
        m_air_kgs=0.5,
        T_gas_in_C=900,
        T_mix_C=850,
        T_out_C=150,
        T_ambient_C=20,
    )
    assert result["Q_total"] > 0
    assert 0 < result["fraction_air"] < 1
    assert result["Q_from_gas"] > result["Q_from_air"]
