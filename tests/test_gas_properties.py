"""Тесты для модуля свойств газов."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from calc import gas_properties as gp
import pytest


def test_gas_density_at_zero():
    """Плотность при 0°C и нормальном давлении."""
    rho = gp.gas_density(0, 101325, M=29.0)
    assert abs(rho - 1.29) < 0.1  # ~1.29 кг/м³


def test_gas_density_increases_with_pressure():
    rho1 = gp.gas_density(20, 101325)
    rho2 = gp.gas_density(20, 200000)
    assert rho2 > rho1


def test_gas_density_decreases_with_temperature():
    rho1 = gp.gas_density(20)
    rho2 = gp.gas_density(500)
    assert rho2 < rho1


def test_air_density():
    """Плотность воздуха при ~20°C ≈ 1.2 кг/м³."""
    rho = gp.air_density(20)
    assert abs(rho - 1.2) < 0.1


def test_cp_flue_gas_range():
    """Cp газов в разумном диапазоне."""
    cp20 = gp.cp_flue_gas(20)
    cp500 = gp.cp_flue_gas(500)
    cp1000 = gp.cp_flue_gas(1000)
    assert 0.9 < cp20 < 1.1
    assert 1.0 < cp500 < 1.2
    assert 1.05 < cp1000 < 1.25


def test_cp_air():
    cp = gp.cp_air(20)
    assert abs(cp - 1.005) < 0.01


def test_actual_to_mass_flow():
    """Перевод объёмного расхода в массовый."""
    # При 0°C и нормальном давлении, 3600 м³/ч → ~1.29 кг/с
    m = gp.actual_to_mass_flow(3600, 0, M=29.0)
    assert abs(m - 1.29) < 0.1


def test_normal_to_actual():
    """Перевод нормального расхода в фактический."""
    # При 0°C фактический = нормальный
    V = gp.normal_to_actual(1000, 0)
    assert abs(V - 1000) < 1

    # При 273.15°C фактический ≈ 2× нормальный
    V = gp.normal_to_actual(1000, 273.15)
    assert abs(V - 2000) < 10


def test_actual_to_normal():
    """Перевод фактического в нормальный."""
    V_norm = gp.actual_to_normal(2000, 273.15)
    assert abs(V_norm - 1000) < 10


def test_mass_flow_consistency():
    """Проверка консистентности: mass → actual → mass."""
    m_original = 5.0  # кг/с
    V_actual = gp.mass_to_actual(m_original, 200)
    m_back = gp.actual_to_mass_flow(V_actual, 200)
    assert abs(m_original - m_back) < 0.01


def test_mass_to_normal():
    """mass → normal → mass."""
    m = 5.0
    V_norm = gp.mass_to_normal(m)
    m_back = gp.actual_to_mass_flow(gp.normal_to_actual(V_norm, 0), 0)
    assert abs(m - m_back) < 0.01
