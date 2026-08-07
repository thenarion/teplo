"""
Страница 4: Газовоздушное охлаждение.
"""
import streamlit as st
import numpy as np
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ui.inputs import render_sidebar, get_params, load_defaults
from ui.results import show_gas_air_cooling_results, show_sizing_results
from ui.plots import plot_air_flow_vs_dT
from ui.schema_diagrams import show_gas_air_cooling_scheme
from calc import gas_air_cooling
from calc import gas_properties as gp
from calc import mixing
from calc import heat_balance
from calc import air_leakage
from calc import hx_sizing
from calc import sizing

st.set_page_config(page_title="Газовоздушное охлаждение", layout="wide")
render_sidebar()

st.header("Газовоздушное охлаждение")

defaults = load_defaults()
params = get_params()
M = defaults.get("M_flue_gas", 29.0)

# Пересчитываем всё на лету из sidebar
if params["flow_type"] == "normal":
    V_actual = gp.normal_to_actual(params["V_fan"], params["T_fan"])
else:
    V_actual = params["V_fan"]

m_gas = gp.actual_to_mass_flow(V_actual, params["T_fan"], M=M)

leak_frac = st.session_state.get("leak_percent", 10) / 100.0
leak_mode = st.session_state.get("leak_mode", "percent")

# Если режим не percent, берём из session_state leak_fraction если есть
if leak_mode != "percent":
    leak_frac = st.session_state.get("_leak_fraction", 0.1)
else:
    leak_frac = st.session_state.get("leak_percent", 10) / 100.0

m_air = m_gas * leak_frac
cp_gas = gp.cp_flue_gas(params["T_afterburner"])
cp_air_val = gp.cp_air(params["T_ambient"])
T_mix = mixing.mixed_gas_temperature(m_gas, params["T_afterburner"], m_air, params["T_ambient"], cp_gas, cp_air_val)
m_total = m_gas + m_air
cp_avg = heat_balance.avg_cp(T_mix, params["T_out_target"])
Q_kW = heat_balance.heat_duty_kW(m_total, cp_avg, T_mix, params["T_out_target"])

st.info("Для газовоздушного охлаждения дымовые газы охлаждаются наружным воздухом через теплообменник.")

st.subheader("Параметры расчёта")
col1, col2, col3 = st.columns(3)
with col1:
    dT_air = st.number_input("Нагрев воздуха, K",
                              value=int(defaults.get("dT_air_cooling", 40)),
                              min_value=10, max_value=100, key="ga_dT_air")
with col2:
    v_air = st.number_input("Скорость воздуха, м/с",
                             value=float(defaults.get("v_air", 3.0)),
                             min_value=1.0, max_value=10.0, step=0.5, key="ga_v_air")
with col3:
    U_gas_air = st.number_input("U газ-воздух, Вт/(м²·К)",
                                 value=int(st.session_state.get("U_design", 60)),
                                 min_value=10, max_value=200, key="ga_U")

result = gas_air_cooling.gas_air_cooling_calculate(
    Q_kW=Q_kW,
    T_gas_in_C=T_mix,
    T_gas_out_C=params["T_out_target"],
    T_air_in_C=params["T_ambient"],
    dT_air=dT_air, v_air=v_air, U=U_gas_air,
    F=st.session_state.get("F_lmtd", 0.9),
    v_gas=8.0, V_gas_m3h=V_actual,
)

show_gas_air_cooling_results(result)

st.divider()
st.subheader("Габариты газовоздушного теплообменника")
a_specific = defaults.get("a_specific", 40)
dims = sizing.estimate_dimensions(result["area_m2"], result["A_front_gas_m2"], a_specific)
show_sizing_results(dims)

if result["A_front_gas_m2"] > 0:
    st.subheader("Газовый тракт")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Площадь проходного сечения", f"{result['A_front_gas_m2']:.2f} м²")
    with col2:
        D_eq = sizing.gas_flow_cross_section(V_actual, 8.0)["D_eq_m"]
        st.metric("Эквивалентный диаметр", f"{D_eq:.2f} м")

st.divider()
st.subheader("Графики")
dT_range = np.linspace(5, 50, 50)
fig = plot_air_flow_vs_dT(Q_kW, params["T_ambient"], dT_range)
st.plotly_chart(fig, use_container_width=True)

st.divider()
show_gas_air_cooling_scheme()
