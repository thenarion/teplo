"""
Страница 5: Жидкостное охлаждение.
"""
import streamlit as st
import numpy as np
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ui.inputs import render_sidebar, get_params, load_defaults
from ui.results import show_liquid_cooling_results, show_warning_box
from ui.plots import plot_glycol_concentration
from ui.schema_diagrams import show_liquid_cooling_scheme
from calc import liquid_cooling
from calc import antifreeze
from calc import gas_properties as gp
from calc import mixing
from calc import heat_balance
from calc import air_leakage

render_sidebar()

st.header("Жидкостное охлаждение антифризом")

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
cp_gas = gp.cp_flue_gas(params["T_afterburner"])
T_mix = mixing.mixed_gas_temperature(m_gas, params["T_afterburner"], m_air, params["T_ambient"], cp_gas, gp.cp_air(params["T_ambient"]))
cp_avg = heat_balance.avg_cp(T_mix, params["T_out_target"])
Q_kW = heat_balance.heat_duty_kW(m_total, cp_avg, T_mix, params["T_out_target"])

st.info(
    "Для жидкостного охлаждения дымовые газы нагревают промежуточный контур с антифризом, "
    "который затем охлаждается в dry cooler / АВО наружным воздухом."
)

# Параметры контура
st.subheader("Параметры контура")
col1, col2 = st.columns(2)
with col1:
    T_liquid_in = st.number_input("T антифриза на входе в газо-жидкостной ТА, °C",
                                   value=60, min_value=20, max_value=120, key="liq_T_in")
with col2:
    dT_liquid = st.number_input("ΔT антифриза, K",
                                 value=int(defaults.get("dT_liquid", 10)),
                                 min_value=3, max_value=30, key="liq_dT")

col1, col2 = st.columns(2)
with col1:
    glycol_type = st.selectbox("Тип антифриза",
                                ["propylene", "ethylene"],
                                format_func=lambda x: "Пропиленгликоль" if x == "propylene"
                                          else "Этиленгликоль", key="liq_glycol_type")
with col2:
    T_min_amb = st.number_input("T min наружная (для подбора), °C",
                                 value=int(defaults.get("T_ambient_min", -30)),
                                 min_value=-60, max_value=0, key="liq_T_min_amb")

# Подбор концентрации
conc_result = antifreeze.recommend_antifreeze_concentration(
    T_min_amb, glycol_type, safety_margin=10.0
)

st.subheader("Рекомендуемая концентрация антифриза")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Концентрация", f"{conc_result['concentration']:.0f}%")
with col2:
    st.metric("T замерзания", f"{conc_result['freeze_temp']:.0f} °C")
with col3:
    st.metric("T расчётная min", f"{conc_result['target_temp']:.0f} °C")

if conc_result["warnings"]:
    show_warning_box(conc_result["warnings"])

concentration = st.slider(
    "Концентрация гликоля, %", 10, 60,
    value=int(conc_result["concentration"]) if conc_result["concentration"] > 0 else 25,
    step=5, key="liq_concentration",
)

st.divider()

# Параметры теплообменников
st.subheader("Параметры теплообменников")
col1, col2, col3 = st.columns(3)
with col1:
    U_gas_liquid = st.number_input("U газ-жидкость, Вт/(м²·К)",
                                    value=int(st.session_state.get("U_design", 60)),
                                    min_value=20, max_value=200,
                                    help="40-150 для оребрённых труб", key="liq_U_gl")
with col2:
    U_dry_cooler = st.number_input("U dry cooler (жидк-воздух), Вт/(м²·К)",
                                    value=60,
                                    min_value=20, max_value=200,
                                    help="30-80 для оребрённых труб", key="liq_U_dc")
with col3:
    dT_air_cooler = st.number_input("ΔT воздуха в АВО, K",
                                     value=int(defaults.get("dT_air_dry_cooler", 30)),
                                     min_value=5, max_value=60,
                                     help="Нагрев наружного воздуха", key="liq_dT_air")

st.divider()

# Расчёт
result = liquid_cooling.liquid_cooling_calculate(
    Q_kW=Q_kW,
    T_gas_in_C=T_mix,
    T_gas_out_C=params["T_out_target"],
    T_liquid_in_C=T_liquid_in,
    dT_liquid_K=dT_liquid,
    glycol_type=glycol_type,
    concentration_pct=concentration,
    T_min_ambient=T_min_amb,
    T_max_ambient=defaults.get("T_ambient_max", 35),
    U_gas_liquid=U_gas_liquid,
    U_dry_cooler=U_dry_cooler,
    F=st.session_state.get("F_lmtd", 0.9),
    margin_pct=st.session_state.get("surface_margin", 25),
    dT_air_cooler=dT_air_cooler,
)

show_liquid_cooling_results(result)

st.divider()

st.subheader("Концентрация антифриза от температуры")
T_range = np.linspace(-50, 0, 50)
fig = plot_glycol_concentration(T_range, glycol_type)
st.plotly_chart(fig, use_container_width=True)

st.divider()
show_liquid_cooling_scheme()
