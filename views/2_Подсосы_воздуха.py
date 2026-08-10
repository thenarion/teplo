"""
Страница 2: Подсосы воздуха.
"""
import streamlit as st
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ui.inputs import render_sidebar, get_params, get_leak_params, render_leak_inputs, load_defaults
from calc import air_leakage
from calc import gas_properties as gp

render_sidebar()

st.header("Подсосы воздуха в циклонах")

params = get_params()
defaults = load_defaults()
M = defaults.get("M_flue_gas", 29.0)

if params["flow_type"] == "normal":
    V_actual = gp.normal_to_actual(params["V_fan"], params["T_fan"])
else:
    V_actual = params["V_fan"]

m_gas = gp.actual_to_mass_flow(V_actual, params["T_fan"], M=M)
rho_air = gp.air_density(params["T_ambient"])

render_leak_inputs()

st.divider()

leak_params = get_leak_params()

result = air_leakage.calculate_leak(
    mode=leak_params["leak_mode"],
    Q_gas_m3h=V_actual,
    leak_percent=leak_params.get("leak_percent", 0),
    leak_m3h=leak_params.get("leak_m3h", 0),
    A_leak=leak_params.get("leak_A", 0),
    dp_Pa=leak_params.get("leak_dp", 0),
    rho_air=rho_air,
    Cd=leak_params.get("leak_Cd", 0.65),
    O2_before=leak_params.get("O2_before", 0),
    O2_after=leak_params.get("O2_after", 0),
    T_before_C=leak_params.get("T_before_cyclone", 0),
    T_after_C=leak_params.get("T_after_cyclone", 0),
    T_ambient_C=leak_params.get("T_ambient_for_leak", params["T_ambient"]),
    cp_gas=gp.cp_flue_gas(params["T_afterburner"]),
    cp_air=gp.cp_air(params["T_ambient"]),
    Q_fan=V_actual,
    k_leak=leak_params.get("leak_k", 0),
    alpha=leak_params.get("leak_alpha", 1.0),
)

st.subheader("Результаты расчёта подсоса")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Расход подсоса", f"{result['leak_value']:.1f} {result['leak_unit']}")
with col2:
    st.metric("Доля подсоса", f"{result['leak_fraction']*100:.1f}%")
with col3:
    if result["leak_fraction"] > 0:
        m_air = m_gas * result["leak_fraction"]
        st.metric("Массовый расход воздуха", f"{m_air:.2f} кг/с")

if result.get("warning"):
    st.warning(result["warning"])

st.info(
    "ℹ️ Связь «производительность дымососа — подсосы воздуха» является **оценочной** "
    "без характеристики сети и вентиляторной кривой. "
    "Для точного расчёта необходимы натурные измерения."
)
