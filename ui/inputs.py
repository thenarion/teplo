"""
Модули ввода данных для Streamlit.
Все виджеты используют фиксированные key для сохранения состояния между страницами.
"""
import streamlit as st
import yaml
from pathlib import Path


@st.cache_data
def load_defaults() -> dict:
    """Загрузка значений по умолчанию из YAML."""
    defaults_path = Path(__file__).parent.parent / "data" / "defaults.yaml"
    with open(defaults_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get(key: str, default=None):
    """Чтение значения из session_state с fallback на default."""
    return st.session_state.get(key, default)


def render_sidebar():
    """
    Рендерит sidebar с основными параметрами.
    Вызывается на каждой странице. Виджеты с одинаковыми key
    автоматически синхронизируются через session_state.
    """
    defaults = load_defaults()

    st.sidebar.header("Исходные данные")

    st.sidebar.number_input(
        "Температура после дожигателя, °C",
        min_value=600, max_value=1300,
        value=int(defaults.get("T_afterburner", 900)),
        step=10, help="Диапазон: 800–1100 °C",
        key="T_afterburner",
    )

    st.sidebar.number_input(
        "Расход дымовых газов на дымососе, м³/ч",
        min_value=1000, max_value=100000,
        value=int(defaults.get("V_fan", 25000)),
        step=500, help="Диапазон: 15 000–30 000 м³/ч",
        key="V_fan",
    )

    st.sidebar.selectbox(
        "Тип расхода дымососа",
        options=["normal", "actual"],
        format_func=lambda x: "Нормальный (Нм³/ч, 0°C)" if x == "normal"
                  else "Фактический (м³/ч, при рабочих условиях)",
        index=0 if defaults.get("flow_type") == "normal" else 1,
        key="flow_type",
    )

    st.sidebar.number_input(
        "Температура газов на дымососе, °C",
        min_value=20, max_value=400,
        value=int(defaults.get("T_fan", 150)),
        step=5, help="Нужна для перевода объёма в массу",
        key="T_fan",
    )

    st.sidebar.divider()

    st.sidebar.number_input(
        "Температура окружающего воздуха, °C",
        min_value=-50, max_value=50,
        value=int(defaults.get("T_ambient", 20)),
        step=5,
        key="T_ambient",
    )

    st.sidebar.number_input(
        "Требуемая температура газов после теплообменника, °C",
        min_value=80, max_value=400,
        value=int(defaults.get("T_out_target", 150)),
        step=10, help="Диапазон: 100–300 °C",
        key="T_out_target",
    )

    st.sidebar.selectbox(
        "Тип охлаждения",
        options=["liquid", "gas_air"],
        format_func=lambda x: "Жидкостное (антифриз)" if x == "liquid"
                  else "Газовоздушное (воздух)",
        index=0 if defaults.get("cooling_type") == "liquid" else 1,
        key="cooling_type",
    )


def render_leak_inputs():
    """
    Рендерит виджеты подсоса воздуха на странице.
    Использует фиксированные key.
    """
    defaults = load_defaults()

    st.subheader("Подсос воздуха в циклонах")

    st.selectbox(
        "Режим расчёта подсоса",
        options=["percent", "m3h", "o2", "temperature", "orifice", "empirical"],
        format_func=lambda x: {
            "percent": "Ручной ввод (%)",
            "m3h": "Ручной ввод (м³/ч)",
            "o2": "По O₂ до/после циклонов",
            "temperature": "По температурам до/после циклонов",
            "orifice": "По площади неплотностей и разрежению",
            "empirical": "Эмпирическая модель (от дымососа)",
        }[x],
        index=0,
        key="leak_mode",
    )

    mode = get("leak_mode", "percent")

    if mode == "percent":
        st.slider("Подсос воздуха, %", 0, 100,
                  value=int(defaults.get("leak_percent", 10)),
                  key="leak_percent")

    elif mode == "m3h":
        st.number_input("Подсос воздуха, м³/ч", 0, 50000,
                        value=int(defaults.get("leak_m3h", 2500)), step=100,
                        key="leak_m3h")

    elif mode == "o2":
        col1, col2 = st.columns(2)
        with col1:
            st.number_input("O₂ до циклонов, %", 0.0, 20.9,
                            value=float(defaults.get("O2_before", 8.0)), step=0.5,
                            key="O2_before")
        with col2:
            st.number_input("O₂ после циклонов, %", 0.0, 20.9,
                            value=float(defaults.get("O2_after", 10.0)), step=0.5,
                            key="O2_after")

    elif mode == "temperature":
        col1, col2, col3 = st.columns(3)
        with col1:
            st.number_input("T до циклонов, °C", 100, 1300,
                            value=int(defaults.get("T_before_cyclone", 900)), step=10,
                            key="T_before_cyclone")
        with col2:
            st.number_input("T после циклонов, °C", 20, 1200,
                            value=int(defaults.get("T_after_cyclone", 800)), step=10,
                            key="T_after_cyclone")
        with col3:
            st.number_input("T воздуха, °C", -50, 50, 20, step=5,
                            key="T_ambient_for_leak")

    elif mode == "orifice":
        col1, col2 = st.columns(2)
        with col1:
            st.number_input("Площадь неплотностей, м²", 0.0001, 1.0,
                            value=float(defaults.get("leak_A", 0.01)),
                            step=0.001, format="%.4f", key="leak_A")
        with col2:
            st.number_input("Разрежение, Па", 0, 10000,
                            value=int(defaults.get("leak_dp", 1000)), step=50,
                            key="leak_dp")
        st.slider("Коэффициент расхода Cd", 0.4, 1.0,
                  value=float(defaults.get("leak_Cd", 0.65)), step=0.05,
                  key="leak_Cd")

    elif mode == "empirical":
        col1, col2 = st.columns(2)
        with col1:
            st.number_input("Коэффициент k", 0.001, 1.0,
                            value=float(defaults.get("leak_k", 0.05)),
                            step=0.01, format="%.3f", key="leak_k")
        with col2:
            st.number_input("Показатель alpha", 0.5, 2.0,
                            value=float(defaults.get("leak_alpha", 1.0)), step=0.1,
                            key="leak_alpha")
        st.info("Эмпирическая модель: Q_leak = k × Q_fan^alpha. "
                "Требует калибровки по натурным измерениям.")


def render_cooling_params():
    """Рендерит параметры теплообменника."""
    defaults = load_defaults()

    st.subheader("Параметры теплообменника")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.number_input("U min, Вт/(м²·К)",
                        value=int(defaults.get("U_min", 30)),
                        min_value=10, max_value=200, key="U_min")
    with col2:
        st.number_input("U design, Вт/(м²·К)",
                        value=int(defaults.get("U_design", 60)),
                        min_value=10, max_value=300, key="U_design")
    with col3:
        st.number_input("U max, Вт/(м²·К)",
                        value=int(defaults.get("U_max", 120)),
                        min_value=10, max_value=500, key="U_max")

    col1, col2 = st.columns(2)
    with col1:
        st.slider("Коэффициент F (LMTD)", 0.5, 1.0,
                  value=float(defaults.get("F_lmtd", 0.9)), step=0.05,
                  key="F_lmtd")
    with col2:
        st.slider("Запас поверхности, %", 0, 50,
                  value=int(defaults.get("surface_margin", 25)), step=5,
                  key="surface_margin")


def get_params() -> dict:
    """Возвращает текущие параметры из session_state."""
    return {
        "T_afterburner": get("T_afterburner", 900),
        "V_fan": get("V_fan", 25000),
        "flow_type": get("flow_type", "normal"),
        "T_fan": get("T_fan", 150),
        "T_ambient": get("T_ambient", 20),
        "T_out_target": get("T_out_target", 150),
        "cooling_type": get("cooling_type", "liquid"),
    }


def get_leak_params() -> dict:
    """Возвращает текущие параметры подсоса из session_state."""
    return {
        "leak_mode": get("leak_mode", "percent"),
        "leak_percent": get("leak_percent", 10),
        "leak_m3h": get("leak_m3h", 2500),
        "O2_before": get("O2_before", 8.0),
        "O2_after": get("O2_after", 10.0),
        "T_before_cyclone": get("T_before_cyclone", 900),
        "T_after_cyclone": get("T_after_cyclone", 800),
        "T_ambient_for_leak": get("T_ambient_for_leak", 20),
        "leak_A": get("leak_A", 0.01),
        "leak_dp": get("leak_dp", 1000),
        "leak_Cd": get("leak_Cd", 0.65),
        "leak_k": get("leak_k", 0.05),
        "leak_alpha": get("leak_alpha", 1.0),
    }


def get_cooling_params() -> dict:
    """Возвращает параметры теплообменника из session_state."""
    return {
        "U_min": get("U_min", 30),
        "U_design": get("U_design", 60),
        "U_max": get("U_max", 120),
        "F_lmtd": get("F_lmtd", 0.9),
        "surface_margin": get("surface_margin", 25),
    }
