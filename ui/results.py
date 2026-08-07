"""
Отображение результатов расчёта в Streamlit.
"""
import streamlit as st


def show_warning_box(warnings: list):
    """Отображение списка предупреждений."""
    if not warnings:
        return
    for w in warnings:
        st.warning(w)


def show_info_cards(data: dict, columns: int = 3):
    """
    Отображение карточек с ключевыми показателями.
    data: dict {label: value}
    """
    cols = st.columns(columns)
    for i, (label, value) in enumerate(data.items()):
        with cols[i % columns]:
            if isinstance(value, float):
                st.metric(label, f"{value:.2f}")
            elif isinstance(value, int):
                st.metric(label, f"{value}")
            else:
                st.metric(label, str(value))


def show_gas_properties_results(density, mass_flow, V_actual, warnings=None):
    """Результаты расчёта свойств газов."""
    st.subheader("Свойства газов")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Плотность газа", f"{density:.3f} кг/м³")
    with col2:
        st.metric("Массовый расход", f"{mass_flow:.2f} кг/с")
    with col3:
        st.metric("Фактический расход", f"{V_actual:.0f} м³/ч")
    if warnings:
        show_warning_box(warnings)


def show_leak_results(leak_result: dict, Q_gas_m3h: float):
    """Результаты расчёта подсоса."""
    st.subheader("Подсос воздуха")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Расход подсоса", f"{leak_result['leak_value']:.1f} {leak_result['leak_unit']}")
    with col2:
        st.metric("Доля подсоса", f"{leak_result['leak_fraction']*100:.1f}%")
    if leak_result.get("warning"):
        st.warning(leak_result["warning"])


def show_mixing_results(T_mix, T_gas, T_air, leak_fraction, warnings=None):
    """Результаты смешения в циклонах."""
    st.subheader("Смешение в циклонах")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("T газов до циклонов", f"{T_gas:.0f} °C")
    with col2:
        st.metric("T после смешения", f"{T_mix:.0f} °C",
                  delta=f"{T_mix - T_gas:.0f} °C")
    with col3:
        st.metric("T воздуха", f"{T_air:.0f} °C")
    if warnings:
        show_warning_box(warnings)


def show_heat_balance_results(Q_kW, Q_MW, fraction_air, warnings=None):
    """Результаты теплового баланса."""
    st.subheader("Тепловая нагрузка")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Q", f"{Q_kW:.0f} кВт")
    with col2:
        st.metric("Q", f"{Q_MW:.2f} МВт")
    with col3:
        st.metric("Доля подсосного воздуха", f"{fraction_air*100:.1f}%")
    if warnings:
        show_warning_box(warnings)


def show_area_results(area_data: dict, margin_pct: float):
    """Результаты расчёта площади."""
    st.subheader("Площадь теплообмена")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("A min (лучший случай)", f"{area_data['A_min']:.1f} м²")
    with col2:
        st.metric("A design", f"{area_data['A_design']:.1f} м²")
    with col3:
        st.metric("A max (худший случай)", f"{area_data['A_max']:.1f} м²")

    st.caption(
        f"U: {area_data['U_min']}–{area_data['U_max']} Вт/(м²·К), "
        f"запас поверхности: {margin_pct}%"
    )


def show_lmtd_results(lmtd_val, dT1, dT2, F, warnings=None):
    """Результаты LMTD."""
    st.subheader("Температурный напор")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("LMTD", f"{lmtd_val:.1f} K")
    with col2:
        st.metric("ΔT₁", f"{dT1:.1f} K")
    with col3:
        st.metric("ΔT₂", f"{dT2:.1f} K")
    st.caption(f"Коэффициент F = {F}")
    if warnings:
        show_warning_box(warnings)


def show_gas_air_cooling_results(result: dict):
    """Результаты газовоздушного охлаждения."""
    st.subheader("Газовоздушное охлаждение")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Расход воздуха", f"{result['V_air_m3h']:.0f} м³/ч ({result['m_air_kgs']:.2f} кг/с)")
        st.metric("T воздуха на выходе", f"{result['T_air_out_C']:.0f} °C")
    with col2:
        st.metric("Площадь теплообмена", f"{result['area_m2']:.1f} м²")
        st.metric("LMTD", f"{result['LMTD']:.0f} K")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Вентиляторы", f"{result.get('n_fans', 1)} шт")
    with col2:
        st.metric("Мощность вентиляторов", f"{result['P_fan_kW']:.1f} кВт")
    with col3:
        st.metric("Фронтальная площадь воздуха", f"{result['A_front_air_m2']:.1f} м²")
    show_warning_box(result.get("warnings", []))


def show_liquid_cooling_results(result: dict):
    """Результаты жидкостного охлаждения."""
    st.subheader("Жидкостное охлаждение")

    # Антифриз
    st.markdown("**Антифриз**")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        glycol_name = "Пропиленгликоль" if result["glycol_type"] == "propylene" else "Этиленгликоль"
        st.metric("Тип", glycol_name)
    with col2:
        st.metric("Концентрация", f"{result['concentration_pct']:.0f}%")
    with col3:
        st.metric("T замерзания", f"{result['freeze_temp']:.0f} °C")
    with col4:
        st.metric("Теплоёмкость", f"{result['cp_liquid']:.2f} кДж/(кг·К)")

    # Расход
    st.markdown("**Расход антифриза**")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Массовый расход", f"{result['m_liquid_kgs']:.2f} кг/с")
    with col2:
        st.metric("Объёмный расход", f"{result['V_liquid_m3h']:.1f} м³/ч")
    with col3:
        st.metric("Мощность насоса", f"{result['P_pump_kW']:.1f} кВт")

    # Температуры
    col1, col2 = st.columns(2)
    with col1:
        st.metric("T антифриза на входе", f"{result['T_liquid_in_C']:.0f} °C")
    with col2:
        st.metric("T антифриза на выходе", f"{result['T_liquid_out_C']:.0f} °C")

    # Газо-жидкостный ТА
    st.markdown("**Газо-жидкостный теплообменник (дымовые газы → антифриз)**")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("LMTD", f"{result['LMTD_gas_liquid']:.0f} K")
    with col2:
        st.metric("Площадь", f"{result['area_gas_liquid_m2']:.1f} м²")
    with col3:
        st.metric("Площадь с запасом", f"{result['area_gas_liquid_with_margin_m2']:.1f} м²")

    # Dry cooler
    dc = result["dry_cooler"]
    st.markdown("**Dry cooler / АВО (антифриз → наружный воздух)**")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("LMTD dry cooler", f"{dc['LMTD']:.0f} K")
        st.metric("Площадь ТА", f"{dc['area_m2']:.1f} м²")
    with col2:
        st.metric("Расход воздуха", f"{dc['V_air_m3h']:.0f} м³/ч ({dc['m_air_kgs']:.1f} кг/с)")
        st.metric("T воздуха на выходе", f"{dc['T_air_out_C']:.0f} °C")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Вентиляторы", f"{dc['n_fans']} шт")
    with col2:
        st.metric("Мощность вентиляторов", f"{dc['P_fans_kW']:.1f} кВт")
    with col3:
        st.metric("Фронтальная площадь", f"{dc['A_front_m2']:.1f} м²")

    show_warning_box(result.get("warnings", []))


def show_sizing_results(dimensions: dict):
    """Результаты оценки габаритов."""
    st.subheader("Габариты теплообменника")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Объём пучка", f"{dimensions['V_bundle_m3']:.2f} м³")
    with col2:
        st.metric("Ширина", f"{dimensions['W_m']:.2f} м")
    with col3:
        st.metric("Высота", f"{dimensions['H_m']:.2f} м")
    with col4:
        st.metric("Длина", f"{dimensions['L_m']:.2f} м")
    st.metric("Ориентировочная масса", f"{dimensions['mass_kg']:.0f} кг")
