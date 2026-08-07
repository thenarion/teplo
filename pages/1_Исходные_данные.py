"""
Страница 1: Исходные данные.
"""
import streamlit as st
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ui.inputs import render_sidebar, get_params, render_leak_inputs, get_leak_params, load_defaults
from calc import gas_properties as gp

st.set_page_config(page_title="Исходные данные", layout="wide")

render_sidebar()

st.header("Исходные данные")

params = get_params()
defaults = load_defaults()
M = defaults.get("M_flue_gas", 29.0)

# Определяем фактический расход
if params["flow_type"] == "normal":
    V_actual = gp.normal_to_actual(params["V_fan"], params["T_fan"])
else:
    V_actual = params["V_fan"]

rho = gp.gas_density(params["T_fan"], M=M)
m_gas = gp.actual_to_mass_flow(V_actual, params["T_fan"], M=M)

st.subheader("Свойства газов")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Плотность газов на дымососе", f"{rho:.3f} кг/м³")
with col2:
    st.metric("Массовый расход газов", f"{m_gas:.2f} кг/с")
with col3:
    st.metric("Фактический расход", f"{V_actual:.0f} м³/ч")
with col4:
    cp = gp.cp_flue_gas(params["T_afterburner"])
    st.metric("Cp газов (при T дожигателя)", f"{cp:.3f} кДж/(кг·К)")

st.divider()

render_leak_inputs()

st.divider()
st.subheader("Допущения расчёта")
st.markdown(f"""
- Идеальная газовая модель
- Молярная масса дымовых газов: {M} кг/кмоль
- Атмосферное давление (101 325 Па), если не задано иное
- Теплоёмкость газов зависит от температуры (полиномиальная аппроксимация)
- Для подсоса через неплотности: коэффициент расхода Cd = 0.6–0.8
""")
