"""
Страница 6: Габариты.
"""
import streamlit as st
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ui.inputs import render_sidebar, get_params, load_defaults
from calc import gas_properties as gp
from calc import mixing
from calc import heat_balance
from calc import air_leakage
from calc import hx_sizing
from calc import sizing

render_sidebar()

st.header("Оценка габаритов теплообменника")

defaults = load_defaults()
params = get_params()
M = defaults.get("M_flue_gas", 29.0)

# Пересчитываем на лету
if params["flow_type"] == "normal":
    V_actual = gp.normal_to_actual(params["V_fan"], params["T_fan"])
else:
    V_actual = params["V_fan"]

m_gas = gp.actual_to_mass_flow(V_actual, params["T_fan"], M=M)
leak_frac = st.session_state.get("leak_percent", 10) / 100.0
leak_mode = st.session_state.get("leak_mode", "percent")
if leak_mode != "percent":
    leak_frac = st.session_state.get("_leak_fraction", 0.1)
m_air = m_gas * leak_frac
m_total = m_gas + m_air
T_mix = mixing.mixed_gas_temperature(m_gas, params["T_afterburner"], m_air, params["T_ambient"],
                                      gp.cp_flue_gas(params["T_afterburner"]), gp.cp_air(params["T_ambient"]))
cp_avg = heat_balance.avg_cp(T_mix, params["T_out_target"])
Q_W = heat_balance.heat_duty(m_total, cp_avg, T_mix, params["T_out_target"])

U_design = st.session_state.get("U_design", 60)
F = st.session_state.get("F_lmtd", 0.9)
margin = st.session_state.get("surface_margin", 25)

if params["cooling_type"] == "liquid":
    T_cold_in, T_cold_out = 60, 70
else:
    T_cold_in, T_cold_out = params["T_ambient"], params["T_ambient"] + 20

lmtd_val = hx_sizing.lmtd(T_mix, params["T_out_target"], T_cold_in, T_cold_out)
area_design = hx_sizing.heat_transfer_area(Q_W, U_design, F, lmtd_val)
A_with_margin = area_design * (1 + margin / 100)

st.subheader("Параметры оценки")
col1, col2, col3 = st.columns(3)
with col1:
    a_specific = st.number_input("Удельная поверхность, м²/м³",
                                  value=int(defaults.get("a_specific", 40)),
                                  min_value=10, max_value=100, key="sz_a_spec")
with col2:
    L_depth = st.number_input("Глубина модуля, м",
                               value=1.5, min_value=0.5, max_value=5.0, step=0.1, key="sz_L")
with col3:
    v_gas = st.number_input("Скорость газа, м/с",
                             value=8.0, min_value=3.0, max_value=15.0, step=0.5, key="sz_v_gas")

st.divider()

st.subheader("Теплообменный аппарат")

flow_cs = sizing.gas_flow_cross_section(V_actual, v_gas)
dims = sizing.estimate_dimensions(A_with_margin, flow_cs["A_flow_m2"], a_specific, L_depth)

col1, col2 = st.columns(2)
with col1:
    st.markdown("**Газовый тракт**")
    st.metric("Расход газа", f"{V_actual:.0f} м³/ч")
    st.metric("Площадь сечения", f"{flow_cs['A_flow_m2']:.2f} м²")
    st.metric("Эквивалентный диаметр", f"{flow_cs['D_eq_m']:.2f} м")
with col2:
    st.markdown("**Теплообменная часть**")
    st.metric("Поверхность ТА (с запасом)", f"{A_with_margin:.1f} м²")
    st.metric("Объём пучка", f"{dims['V_bundle_m3']:.2f} м³")
    st.metric("Фронтальная площадь", f"{dims['A_front_m2']:.2f} м²")

st.markdown("**Габариты модуля**")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Ширина", f"{dims['W_m']:.2f} м")
with col2:
    st.metric("Высота", f"{dims['H_m']:.2f} м")
with col3:
    st.metric("Длина (глубина)", f"{dims['L_m']:.2f} м")
with col4:
    st.metric("Масса", f"{dims['mass_kg']:.0f} кг")

st.divider()
st.subheader("Порядок величин")
st.markdown("""
Для ориентира при расходе 15 000–30 000 м³/ч:
- Массовый расход: 3,5–7 кг/с
- Тепловая нагрузка: 2–6 МВт
- Площадь ТА: 100–700 м²
- Аппарат — **промышленный модульный**, не компактный бытовой
""")
