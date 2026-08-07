"""Тесты для модуля смешения."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from calc import mixing
import pytest


def test_mixed_temperature_no_air():
    """Без подсоса — температура газа не меняется."""
    T = mixing.mixed_gas_temperature(5.0, 900, 0, 20)
    assert abs(T - 900) < 0.01


def test_mixed_temperature_no_gas():
    """Нет газа — температура воздуха."""
    T = mixing.mixed_gas_temperature(0, 900, 5.0, 20)
    assert abs(T - 20) < 0.01


def test_mixed_temperature_equal_cp():
    """При равных cp — средневзвешенная по массе."""
    T = mixing.mixed_gas_temperature(
        10, 900, 10, 20, cp_gas=1.0, cp_air=1.0
    )
    assert abs(T - 460) < 1


def test_mixed_temperature_with_leak():
    """10% подсос при 900°C, 20°C воздух."""
    m_gas = 5.0
    m_air = 0.5  # 10%
    T = mixing.mixed_gas_temperature(m_gas, 900, m_air, 20)
    assert 800 < T < 900


def test_mixed_temperature_range():
    """Температура смеси между T_gas и T_air."""
    T = mixing.mixed_gas_temperature(5, 900, 2, 20, 1.1, 1.0)
    assert 20 < T < 900


def test_validate_mixing_ok():
    """Валидный случай — без предупреждений."""
    warnings = mixing.validate_mixing(900, 20, 850, 0.1)
    assert len(warnings) == 0


def test_validate_mixing_high_leak():
    """Высокий подсос — предупреждение."""
    warnings = mixing.validate_mixing(900, 20, 400, 0.6)
    assert any("высокий" in w.lower() for w in warnings)


def test_validate_mixing_out_of_range():
    """Температура вне диапазона."""
    warnings = mixing.validate_mixing(900, 20, 950, 0.1)
    assert len(warnings) > 0
