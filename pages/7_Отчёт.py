"""
Страница 7: Отчёт и экспорт.
"""
import streamlit as st
import json
import pandas as pd
from datetime import datetime
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ui.inputs import render_sidebar, get_params, get_leak_params, load_defaults
from calc import gas_properties as gp
from calc import mixing
from calc import heat_balance
from calc import air_leakage
from calc import hx_sizing

st.set_page_config(page_title="Отчёт", layout="wide")
render_sidebar()

st.header("Отчёт и экспорт")

defaults = load_defaults()
params = get_params()
leak_params = get_leak_params()
M = defaults.get("M_flue_gas", 29.0)

# Пересчитываем
if params["flow_type"] == "normal":
    V_actual = gp.normal_to_actual(params["V_fan"], params["T_fan"])
else:
    V_actual = params["V_fan"]

m_gas = gp.actual_to_mass_flow(V_actual, params["T_fan"], M=M)

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
cp_gas = gp.cp_flue_gas(params["T_afterburner"])
T_mix = mixing.mixed_gas_temperature(m_gas, params["T_afterburner"], m_air, params["T_ambient"], cp_gas, gp.cp_air(params["T_ambient"]))
cp_avg = heat_balance.avg_cp(T_mix, params["T_out_target"])
Q_kW = heat_balance.heat_duty_kW(m_total, cp_avg, T_mix, params["T_out_target"])
Q_MW = Q_kW / 1000

U_design = st.session_state.get("U_design", 60)
F = st.session_state.get("F_lmtd", 0.9)
margin = st.session_state.get("surface_margin", 25)
if params["cooling_type"] == "liquid":
    T_cold_in, T_cold_out = 60, 70
else:
    T_cold_in, T_cold_out = params["T_ambient"], params["T_ambient"] + 20
lmtd_val = hx_sizing.lmtd(T_mix, params["T_out_target"], T_cold_in, T_cold_out)
area_data = hx_sizing.area_for_u_range(Q_W if (Q_W := Q_kW * 1000) else 1, F, lmtd_val,
                                         st.session_state.get("U_min", 30), U_design,
                                         st.session_state.get("U_max", 120))
A_design_margin = area_data["A_design"] * (1 + margin / 100)

# Отображение
st.subheader("Исходные данные")
col1, col2 = st.columns(2)
with col1:
    st.write(f"- Температура после дожигателя: **{params['T_afterburner']} °C**")
    st.write(f"- Расход дымососа: **{params['V_fan']} м³/ч** ({params['flow_type']})")
    st.write(f"- Температура на дымососе: **{params['T_fan']} °C**")
    st.write(f"- Температура окружающего воздуха: **{params['T_ambient']} °C**")
with col2:
    st.write(f"- Целевая температура после ТА: **{params['T_out_target']} °C**")
    st.write(f"- Тип охлаждения: **{params['cooling_type']}**")
    st.write(f"- Подсос воздуха: **{leak_fraction*100:.1f}%**")
    st.write(f"- Молярная масса газов: **{M} кг/кмоль**")

st.divider()

st.subheader("Результаты расчёта")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Массовый расход газов", f"{m_gas:.2f} кг/с")
    st.metric("Массовый расход воздуха", f"{m_air:.2f} кг/с")
    st.metric("Общий массовый расход", f"{m_total:.2f} кг/с")
with col2:
    st.metric("T после смешения", f"{T_mix:.0f} °C")
    st.metric("LMTD", f"{lmtd_val:.0f} K")
    st.metric("Тепловая нагрузка", f"{Q_kW:.0f} кВт ({Q_MW:.2f} МВт)")
with col3:
    st.metric("Площадь ТА (design)", f"{area_data['A_design']:.1f} м²")
    st.metric("Площадь с запасом", f"{A_design_margin:.1f} м²")
    st.metric("U design", f"{U_design} Вт/(м²·К)")

st.divider()

# Экспорт
st.subheader("Экспорт результатов")

report_data = {
    "Дата расчёта": datetime.now().strftime("%Y-%m-%d %H:%M"),
    "Исходные данные": {
        "T после дожигателя, °C": params["T_afterburner"],
        "Расход дымососа, м³/ч": params["V_fan"],
        "Тип расхода": params["flow_type"],
        "T на дымососе, °C": params["T_fan"],
        "T окружающего воздуха, °C": params["T_ambient"],
        "T после теплообменника, °C": params["T_out_target"],
        "Тип охлаждения": params["cooling_type"],
        "Подсос воздуха, %": leak_fraction * 100,
    },
    "Результаты": {
        "Массовый расход газов, кг/с": round(m_gas, 2),
        "Массовый расход воздуха, кг/с": round(m_air, 2),
        "T после смешения, °C": round(T_mix, 1),
        "Тепловая нагрузка, кВт": round(Q_kW, 1),
        "Тепловая нагрузка, МВт": round(Q_MW, 3),
        "LMTD, K": round(lmtd_val, 1),
        "Площадь ТА, м²": round(area_data["A_design"], 1),
        "Площадь с запасом, м²": round(A_design_margin, 1),
        "U design, Вт/(м²·К)": U_design,
        "F (LMTD)": F,
        "Запас поверхности, %": margin,
    },
}

col1, col2 = st.columns(2)
with col1:
    json_str = json.dumps(report_data, ensure_ascii=False, indent=2)
    st.download_button("Скачать JSON", data=json_str,
                       file_name="heat_exchanger_report.json", mime="application/json")
with col2:
    flat = {}
    for v in report_data.values():
        if isinstance(v, dict):
            flat.update(v)
    df = pd.DataFrame([flat])
    csv = df.to_csv(index=False, encoding="utf-8-sig")
    st.download_button("Скачать CSV", data=csv,
                       file_name="heat_exchanger_report.csv", mime="text/csv")
