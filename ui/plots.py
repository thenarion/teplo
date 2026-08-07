"""
Графики чувствительности для Streamlit.
Используют plotly.
"""
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from calc import gas_properties as gp
from calc import hx_sizing
from calc import antifreeze


def plot_heat_duty_vs_fan_flow(T_afterburner, T_out, T_ambient, flow_type,
                                leak_percent, T_fan, M, V_range):
    """Q = f(Q_fan) — тепловая нагрузка от расхода дымососа."""
    Q_values = []
    for V in V_range:
        if flow_type == "normal":
            m = gp.actual_to_mass_flow(
                gp.normal_to_actual(V, T_fan), T_fan, M=M
            )
        else:
            m = gp.actual_to_mass_flow(V, T_fan, M=M)

        m_air = m * leak_percent / 100
        m_total = m + m_air
        cp = gp.cp_flue_gas(T_afterburner)
        cp_air_val = gp.cp_air(T_ambient)

        if m_total > 0:
            T_mix = (m * cp * T_afterburner + m_air * cp_air_val * T_ambient) / (
                m * cp + m_air * cp_air_val
            )
        else:
            T_mix = T_afterburner

        cp_avg = (gp.cp_flue_gas(T_mix) + gp.cp_flue_gas(T_out)) / 2
        Q = m_total * cp_avg * 1000 * (T_mix - T_out) / 1000  # кВт
        Q_values.append(Q)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=list(V_range), y=Q_values, mode='lines+markers'))
    fig.update_layout(
        title="Тепловая нагрузка от расхода дымососа",
        xaxis_title="Расход дымососа, м³/ч",
        yaxis_title="Тепловая нагрузка, кВт",
        template="plotly_white",
    )
    return fig


def plot_T_mix_vs_leak(T_afterburner, T_ambient, m_gas, cp_gas, cp_air, leak_range):
    """T_mix = f(leak%) — температура после циклонов от подсоса."""
    T_values = []
    for leak in leak_range:
        m_air = m_gas * leak / 100
        if m_gas + m_air > 0:
            T_mix = (m_gas * cp_gas * T_afterburner + m_air * cp_air * T_ambient) / (
                m_gas * cp_gas + m_air * cp_air
            )
        else:
            T_mix = T_afterburner
        T_values.append(T_mix)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=list(leak_range), y=T_values, mode='lines+markers',
                             line=dict(color='firebrick')))
    fig.update_layout(
        title="Температура после циклонов от подсоса воздуха",
        xaxis_title="Подсос воздуха, %",
        yaxis_title="Температура смеси, °C",
        template="plotly_white",
    )
    return fig


def plot_area_vs_U(Q_kW, F, lmtd_val, U_range):
    """A = f(U) — площадь от коэффициента теплопередачи."""
    Q_W = Q_kW * 1000
    A_values = [hx_sizing.heat_transfer_area(Q_W, U, F, lmtd_val) for U in U_range]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=list(U_range), y=A_values, mode='lines+markers',
                             line=dict(color='green')))
    fig.update_layout(
        title="Площадь теплообмена от U",
        xaxis_title="U, Вт/(м²·К)",
        yaxis_title="Площадь, м²",
        template="plotly_white",
    )
    return fig


def plot_area_vs_T_out(m_total, cp_avg_func, T_in, F, U, lmtd_cold_in, T_out_range):
    """A = f(T_out) — площадь от целевой температуры газа."""
    A_values = []
    for T_out in T_out_range:
        if T_out >= T_in:
            A_values.append(0)
            continue
        cp = cp_avg_func(T_in, T_out)
        Q = m_total * cp * 1000 * (T_in - T_out)
        lmtd_val = hx_sizing.lmtd(T_in, T_out, lmtd_cold_in, lmtd_cold_in + 20)
        if lmtd_val > 0:
            A = hx_sizing.heat_transfer_area(Q, U, F, lmtd_val)
        else:
            A = 0
        A_values.append(A)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=list(T_out_range), y=A_values, mode='lines+markers',
                             line=dict(color='orange')))
    fig.update_layout(
        title="Площадь теплообмена от целевой температуры газа",
        xaxis_title="T после теплообменника, °C",
        yaxis_title="Площадь, м²",
        template="plotly_white",
    )
    return fig


def plot_area_vs_T_ambient(Q_kW, F, U, T_gas_in, T_gas_out, T_amb_range):
    """A = f(T_ambient) — площадь от температуры окружающего воздуха."""
    A_values = []
    for T_amb in T_amb_range:
        lmtd_val = hx_sizing.lmtd(T_gas_in, T_gas_out, T_amb, T_amb + 20)
        if lmtd_val > 0:
            A = hx_sizing.heat_transfer_area(Q_kW * 1000, U, F, lmtd_val)
        else:
            A = 0
        A_values.append(A)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=list(T_amb_range), y=A_values, mode='lines+markers',
                             line=dict(color='purple')))
    fig.update_layout(
        title="Площадь теплообмена от температуры воздуха",
        xaxis_title="T окружающего воздуха, °C",
        yaxis_title="Площадь, м²",
        template="plotly_white",
    )
    return fig


def plot_air_flow_vs_dT(Q_kW, T_air_in, dT_range):
    """V_air = f(dT_air) — расход воздуха от нагрева."""
    from calc import gas_properties as gp
    cp = gp.cp_air(T_air_in + 10)
    V_values = []
    for dT in dT_range:
        if dT > 0:
            m = Q_kW / (cp * dT)
            rho = gp.air_density(T_air_in + dT / 2)
            V = m * 3600 / rho
        else:
            V = 0
        V_values.append(V)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=list(dT_range), y=V_values, mode='lines+markers',
                             line=dict(color='teal')))
    fig.update_layout(
        title="Расход охлаждающего воздуха от нагрева",
        xaxis_title="ΔT воздуха, K",
        yaxis_title="Расход воздуха, м³/ч",
        template="plotly_white",
    )
    return fig


def plot_glycol_concentration(T_min_range, glycol_type):
    """C_glycol = f(T_min_ambient) — концентрация от температуры."""
    conc_values = []
    for T in T_min_range:
        result = antifreeze.recommend_antifreeze_concentration(T, glycol_type)
        conc_values.append(result["concentration"])

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=list(T_min_range), y=conc_values, mode='lines+markers',
                             line=dict(color='darkblue')))
    fig.update_layout(
        title="Концентрация антифриза от минимальной температуры",
        xaxis_title="T min окружающего воздуха, °C",
        yaxis_title="Концентрация гликоля, %",
        template="plotly_white",
    )
    return fig
