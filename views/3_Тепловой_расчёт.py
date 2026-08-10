"""
Страница 3: Тепловой расчёт.
"""
import streamlit as st
import numpy as np
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ui.inputs import (render_sidebar, get_params, get_leak_params,
                        render_leak_inputs, render_cooling_params, get_cooling_params,
                        load_defaults)
from ui.results import (show_warning_box, show_mixing_results,
                         show_heat_balance_results, show_area_results,
                         show_lmtd_results)
from ui.plots import (plot_T_mix_vs_leak, plot_area_vs_U,
                       plot_heat_duty_vs_fan_flow)
from calc import gas_properties as gp
from calc import mixing
from calc import heat_balance
from calc import hx_sizing
from calc import air_leakage

render_sidebar()

st.header("Тепловой расчёт")

defaults = load_defaults()
params = get_params()
leak_params = get_leak_params()
M = defaults.get("M_flue_gas", 29.0)

# Расход газов
if params["flow_type"] == "normal":
    V_actual = gp.normal_to_actual(params["V_fan"], params["T_fan"])
else:
    V_actual = params["V_fan"]

m_gas = gp.actual_to_mass_flow(V_actual, params["T_fan"], M=M)

# Подсос воздуха
rho_air = gp.air_density(params["T_ambient"])
leak_result = air_leakage.calculate_leak(
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
leak_fraction = leak_result["leak_fraction"]
m_air = m_gas * leak_fraction
m_total = m_gas + m_air

# Смешение в циклонах
cp_gas = gp.cp_flue_gas(params["T_afterburner"])
cp_air_val = gp.cp_air(params["T_ambient"])

T_mix = mixing.mixed_gas_temperature(
    m_gas, params["T_afterburner"],
    m_air, params["T_ambient"],
    cp_gas, cp_air_val
)
mix_warnings = mixing.validate_mixing(
    params["T_afterburner"], params["T_ambient"], T_mix, leak_fraction
)

show_mixing_results(T_mix, params["T_afterburner"], params["T_ambient"],
                    leak_fraction, mix_warnings)

st.divider()

# Тепловая нагрузка
cp_avg = heat_balance.avg_cp(T_mix, params["T_out_target"])
Q_W = heat_balance.heat_duty(m_total, cp_avg, T_mix, params["T_out_target"])
Q_kW = Q_W / 1000
Q_MW = Q_W / 1e6

contrib = heat_balance.heat_duty_leak_contribution(
    m_gas, m_air,
    params["T_afterburner"], T_mix,
    params["T_out_target"], params["T_ambient"]
)
show_heat_balance_results(Q_kW, Q_MW, contrib["fraction_air"])

st.divider()

# Параметры ТА
render_cooling_params()
cooling_params = get_cooling_params()

if params["cooling_type"] == "liquid":
    T_cold_in = 60
    T_cold_out = T_cold_in + 10
else:
    T_cold_in = params["T_ambient"]
    T_cold_out = T_cold_in + 20

lmtd_val = hx_sizing.lmtd(T_mix, params["T_out_target"], T_cold_in, T_cold_out)
dT1 = T_mix - T_cold_out
dT2 = params["T_out_target"] - T_cold_in
lmtd_warnings = hx_sizing.validate_lmtd(T_mix, params["T_out_target"],
                                         T_cold_in, T_cold_out)
show_lmtd_results(lmtd_val, dT1, dT2, cooling_params["F_lmtd"], lmtd_warnings)

st.divider()

area_data = hx_sizing.area_for_u_range(
    Q_W, cooling_params["F_lmtd"], lmtd_val,
    cooling_params["U_min"], cooling_params["U_design"], cooling_params["U_max"]
)
margin = cooling_params["surface_margin"]
show_area_results(area_data, margin)

A_design_margin = area_data["A_design"] * (1 + margin / 100)
st.metric("Площадь с запасом", f"{A_design_margin:.1f} м²")

st.divider()

# Графики
st.subheader("Графики чувствительности")
tab1, tab2, tab3 = st.tabs(["T смеси от подсоса", "Площадь от U", "Q от расхода"])

with tab1:
    leak_range = np.linspace(0, 50, 50)
    fig = plot_T_mix_vs_leak(
        params["T_afterburner"], params["T_ambient"],
        m_gas, cp_gas, cp_air_val, leak_range
    )
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    U_range = np.linspace(20, 150, 50)
    fig = plot_area_vs_U(Q_kW, cooling_params["F_lmtd"], lmtd_val, U_range)
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    V_range = np.linspace(5000, 50000, 50)
    fig = plot_heat_duty_vs_fan_flow(
        params["T_afterburner"], params["T_out_target"],
        params["T_ambient"], params["flow_type"],
        leak_fraction * 100, params["T_fan"], M, V_range
    )
    st.plotly_chart(fig, use_container_width=True)
