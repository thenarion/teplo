"""
Страница Streamlit: Тепловой баланс сжигания топлива в барабанной печи.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from calc.thermal_balance_calc import (
    ThermalBalanceInput,
    MATERIAL_TYPES,
    calculate_thermal_balance,
    get_summary_table,
    get_flue_gas_params,
    get_burnout_params,
)
from utils.pdf_export import export_to_pdf, export_to_pdf_simple


st.title("🔥 Тепловой баланс сжигания топлива")
st.markdown("Расчёт теплового баланса для вращающейся барабанной печи")

# =========================================================
# БОКОВАЯ ПАНЕЛЬ
# =========================================================
with st.sidebar:
    st.header("⚙️ Исходные данные")

    st.subheader("Топливо")
    fuel_feed = st.number_input(
        "Подача влажного топлива, кг/ч",
        min_value=100.0, max_value=100000.0,
        value=3660.0, step=100.0, format="%.0f",
    )

    moisture = st.slider(
        "Влажность, %",
        min_value=10.0, max_value=90.0,
        value=50.0, step=1.0,
    ) / 100.0

    q_net_ar = st.number_input(
        "Низшая теплота сгорания, МДж/кг",
        min_value=1.0, max_value=50.0,
        value=12.42, step=0.5, format="%.2f",
    )

    ash_content = st.slider(
        "Зольность, %",
        min_value=0.0, max_value=60.0,
        value=20.0, step=1.0,
    ) / 100.0

    bulk_density = st.number_input(
        "Насыпная плотность, кг/м³",
        min_value=100.0, max_value=1000.0,
        value=400.0, step=50.0, format="%.0f",
    )

    st.subheader("Режим горения")
    excess_air = st.slider(
        "Коэффициент избытка воздуха (α)",
        min_value=1.0, max_value=3.0,
        value=1.40, step=0.05, format="%.2f",
    )

    flue_gas_temp = st.number_input(
        "Температура дымовых газов на выходе, °C",
        min_value=100.0, max_value=1200.0,
        value=700.0, step=50.0, format="%.0f",
    )

    ambient_temp = st.number_input(
        "Температура наружного воздуха, °C",
        min_value=-50.0, max_value=50.0,
        value=10.0, step=5.0, format="%.0f",
    )

    st.subheader("Горелка")
    burner_power = st.number_input(
        "Мощность горелки (макс), МВт",
        min_value=0.0, max_value=20.0,
        value=1.6, step=0.1, format="%.1f",
    )

    burner_min_power = st.number_input(
        "Мощность горелки (мин), МВт",
        min_value=0.0, max_value=20.0,
        value=0.4, step=0.1, format="%.1f",
    )

    st.subheader("Геометрия барабана")
    drum_length = st.number_input(
        "Длина барабана, м",
        min_value=1.0, max_value=20.0,
        value=10.0, step=0.5, format="%.1f",
    )

    drum_diameter = st.number_input(
        "Диаметр барабана, м",
        min_value=0.5, max_value=3.0,
        value=1.9, step=0.1, format="%.1f",
    )

    drum_angle = st.slider(
        "Угол наклона барабана, °",
        min_value=0.5, max_value=5.0,
        value=2.0, step=0.5, format="%.1f",
    )

    drum_rpm = st.slider(
        "Скорость вращения, об/мин",
        min_value=0.5, max_value=3.0,
        value=1.5, step=0.1, format="%.1f",
    )

    st.subheader("Тип материала")
    material_keys = list(MATERIAL_TYPES.keys())
    material_names = [MATERIAL_TYPES[k]["name"] for k in material_keys]

    material_idx = st.selectbox(
        "Тип материала",
        range(len(material_names)),
        format_func=lambda x: material_names[x],
        index=3,
    )

    selected_material_key = material_keys[material_idx]
    selected_material = MATERIAL_TYPES[selected_material_key]

    if selected_material_key == "custom":
        material_coeff = st.slider(
            "Коэффициент материала A",
            min_value=0.10, max_value=0.80,
            value=0.50, step=0.05, format="%.2f",
        )
    else:
        material_coeff = st.slider(
            f"Коэффициент A ({selected_material['A_min']:.2f}–{selected_material['A_max']:.2f})",
            min_value=selected_material["A_min"],
            max_value=selected_material["A_max"],
            value=selected_material["A_default"],
            step=0.05, format="%.2f",
        )

    st.caption(f"📋 {selected_material['description']}")

    st.subheader("Дополнительно")
    wall_loss_pct = st.slider(
        "Потери через футеровку, %",
        min_value=2.0, max_value=20.0,
        value=8.0, step=1.0,
    ) / 100.0

    ash_temp = st.number_input(
        "Температура золы на выходе, °C",
        min_value=100.0, max_value=1000.0,
        value=600.0, step=50.0, format="%.0f",
    )

    max_heat_load = st.number_input(
        "Макс. тепловая нагрузка, кВт/м³",
        min_value=50.0, max_value=500.0,
        value=200.0, step=10.0, format="%.0f",
    )

# =========================================================
# РАСЧЁТ
# =========================================================
inp = ThermalBalanceInput(
    fuel_feed=fuel_feed,
    moisture=moisture,
    q_net_ar=q_net_ar,
    ash_content=ash_content,
    bulk_density=bulk_density,
    excess_air=excess_air,
    flue_gas_temp=flue_gas_temp,
    ambient_temp=ambient_temp,
    burner_power=burner_power,
    burner_min_power=burner_min_power,
    wall_loss_pct=wall_loss_pct,
    ash_temp=ash_temp,
    drum_length=drum_length,
    drum_diameter=drum_diameter,
    drum_angle=drum_angle,
    drum_rpm=drum_rpm,
    material_type=selected_material_key,
    material_coeff=material_coeff,
    max_heat_load=max_heat_load,
)

res = calculate_thermal_balance(inp)

summary_table = get_summary_table(res)
flue_gas_params = get_flue_gas_params(res)
burnout_params = get_burnout_params(res)

# =========================================================
# КЛЮЧЕВЫЕ МЕТРИКИ
# =========================================================
st.header("📊 Ключевые показатели")

col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    st.metric("Время пребывания", f"{res.burnout.residence_time:.0f} мин")

with col2:
    st.metric("Полнота выгорания", f"{res.burnout.burnout_efficiency*100:.1f}%")

with col3:
    st.metric("T на выходе", f"{inp.flue_gas_temp:.0f}°C")

with col4:
    st.metric("Тепловыделение (факт)", f"{res.q_fuel_actual:.2f} МВт")

with col5:
    heat_ok = "✅" if res.burnout.heat_load_ok else "❌"
    st.metric(f"Тепловая нагрузка {heat_ok}", f"{res.burnout.heat_load:.0f} кВт/м³")

with col6:
    st.metric("T адиабатного горения", f"{res.t_adiabatic:.0f}°C")

st.divider()

# =========================================================
# ПРЕДУПРЕЖДЕНИЯ
# =========================================================
warnings = []

if not res.burnout.fill_ratio_ok:
    warnings.append(f"⚠️ Степень заполнения {res.burnout.fill_ratio*100:.1f}% > допустимой {inp.max_fill_ratio*100:.0f}%")

if not res.burnout.time_ok:
    warnings.append(f"⚠️ Время пребывания {res.burnout.residence_time:.0f} мин < необходимого {res.burnout.t_required:.0f} мин")

if not res.burnout.heat_load_ok:
    warnings.append(f"⚠️ Тепловая нагрузка {res.burnout.heat_load:.0f} кВт/м³ > допустимой {inp.max_heat_load:.0f} кВт/м³")

if res.t_adiabatic > 1400:
    warnings.append(f"⚠️ Высокая температура адиабатного горения: {res.t_adiabatic:.0f}°C")

if warnings:
    for w in warnings:
        st.warning(w)
else:
    st.success("✅ Все параметры в допустимых пределах")

# =========================================================
# ТАБЛИЦЫ
# =========================================================
st.header("📋 Результаты расчёта")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Массовый баланс",
    "Тепловой баланс",
    "Воздух и газы",
    "Полнота выгорания",
    "Параметры для теплообменника",
])

with tab1:
    st.subheader("Массовый баланс")

    mass_df = pd.DataFrame({
        "Компонент": [
            "Влажный помёт (всего)", "Вода", "Сухое вещество", "Зола", "Горючая масса",
        ],
        "Масса, кг/ч": [
            res.fuel_feed, res.water_mass, res.dry_mass, res.ash_mass, res.combustible_mass,
        ],
        "Доля, %": [
            100.0,
            res.water_mass / res.fuel_feed * 100,
            res.dry_mass / res.fuel_feed * 100,
            res.ash_mass / res.fuel_feed * 100,
            res.combustible_mass / res.fuel_feed * 100,
        ],
    })

    st.dataframe(mass_df, use_container_width=True, hide_index=True)

    pie_df = pd.DataFrame({
        "Компонент": ["Вода", "Зола", "Горючая масса"],
        "Масса, кг/ч": [res.water_mass, res.ash_mass, res.combustible_mass],
    })
    fig_mass = px.pie(
        pie_df, values="Масса, кг/ч", names="Компонент",
        title="Состав топлива", hole=0.3,
        color="Компонент",
        color_discrete_map={"Вода": "#3498db", "Зола": "#95a5a6", "Горючая масса": "#e74c3c"},
    )
    st.plotly_chart(fig_mass, use_container_width=True)

with tab2:
    st.subheader("Сводная таблица теплового баланса")

    balance_df = pd.DataFrame(summary_table)
    st.dataframe(balance_df, use_container_width=True, hide_index=True)

    fig_heat = go.Figure()

    fig_heat.add_trace(go.Bar(
        x=["Приход"], y=[res.q_fuel_actual],
        name="Тепло от топлива (факт)", marker_color="green",
    ))
    fig_heat.add_trace(go.Bar(
        x=["Приход"], y=[res.input.burner_power],
        name="Тепло от горелки", marker_color="lightgreen",
    ))
    fig_heat.add_trace(go.Bar(
        x=["Расход"], y=[res.q_flue_gas],
        name="Уходящие газы", marker_color="red",
    ))
    fig_heat.add_trace(go.Bar(
        x=["Расход"], y=[res.q_wall],
        name="Потери через футеровку", marker_color="orange",
    ))
    fig_heat.add_trace(go.Bar(
        x=["Расход"], y=[res.q_ash],
        name="Потери с золой", marker_color="yellow",
    ))
    fig_heat.add_trace(go.Bar(
        x=["Расход"], y=[res.q_useful_with_burner],
        name="Полезное тепло", marker_color="blue",
    ))

    fig_heat.update_layout(
        title="Тепловой баланс, МВт",
        barmode="stack",
        yaxis_title="МВт",
    )

    st.plotly_chart(fig_heat, use_container_width=True)

with tab3:
    st.subheader("Расход воздуха и дымовых газов")

    air_df = pd.DataFrame({
        "Параметр": [
            "Теоретический объём воздуха (на кг)",
            "Фактический объём воздуха",
            "Масса воздуха",
            "Объём дымовых газов (н.у.)",
            "Масса дымовых газов",
            f"Объём газов при {inp.flue_gas_temp:.0f}°C",
            "Объём газов при 150°C",
        ],
        "Значение": [
            f"{res.v_air_theoretical_per_kg:.2f} Нм³/кг",
            f"{res.v_air_actual:.0f} Нм³/ч",
            f"{res.m_air:.0f} кг/ч",
            f"{res.v_flue:.0f} Нм³/ч",
            f"{res.m_flue:.0f} кг/ч",
            f"{res.v_flue_actual_hot:.0f} м³/ч",
            f"{res.v_flue_actual_cold:.0f} м³/ч",
        ],
    })

    st.dataframe(air_df, use_container_width=True, hide_index=True)

with tab4:
    st.subheader("Оценка полноты выгорания")

    b = res.burnout
    if b.overall_ok:
        st.success(f"✅ Отход успевает выгореть. Полнота: {b.burnout_efficiency*100:.1f}%")
    else:
        st.error(f"❌ Отход НЕ успевает полностью выгореть. Полнота: {b.burnout_efficiency*100:.1f}%")

    burnout_df = pd.DataFrame(burnout_params)
    st.dataframe(burnout_df, use_container_width=True, hide_index=True)

    # Диаграмма стадий
    st.subheader("Стадии выгорания")

    stages_df = pd.DataFrame({
        "Стадия": ["Сушка", "Нагрев", "Горение", "Дожигание"],
        "Время, мин": [b.t_drying, b.t_heating, b.t_combustion, b.t_burnout],
    })

    fig_stages = px.bar(
        stages_df, x="Стадия", y="Время, мин",
        title="Время по стадиям выгорания",
        color="Стадия",
        color_discrete_sequence=["#FF6B6B", "#FFA500", "#4ECDC4", "#45B7D1"],
    )

    fig_stages.add_hline(
        y=b.residence_time, line_dash="dash", line_color="red",
        annotation_text=f"Фактическое время: {b.residence_time:.0f} мин",
    )
    fig_stages.add_hline(
        y=b.t_required, line_dash="dot", line_color="orange",
        annotation_text=f"Необходимое время: {b.t_required:.0f} мин",
    )

    st.plotly_chart(fig_stages, use_container_width=True)

with tab5:
    st.subheader("Параметры дымовых газов для теплообменника")

    gas_df = pd.DataFrame(flue_gas_params)
    st.dataframe(gas_df, use_container_width=True, hide_index=True)

# =========================================================
# ВЫВОДЫ
# =========================================================
st.divider()
st.header("📝 Выводы")

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("Время пребывания")
    b = res.burnout
    if b.time_ok:
        st.success(f"""
        ✅ Время пребывания **достаточное**.
        
        Фактическое: {b.residence_time:.0f} мин  
        Необходимое: {b.t_required:.0f} мин  
        Запас: ×{b.time_ratio:.2f}
        """)
    else:
        st.error(f"""
        ❌ Время пребывания **недостаточное**.
        
        Фактическое: {b.residence_time:.0f} мин  
        Необходимое: {b.t_required:.0f} мин  
        Дефицит: ×{b.time_ratio:.2f}
        """)

with col2:
    st.subheader("Тепловая нагрузка")
    b = res.burnout
    if b.heat_load_ok:
        st.success(f"""
        ✅ Тепловая нагрузка **в норме**.
        
        Фактическая: {b.heat_load:.0f} кВт/м³  
        Допустимая: {inp.max_heat_load:.0f} кВт/м³
        """)
    else:
        st.error(f"""
        ❌ Тепловая нагрузка **превышена**.
        
        Фактическая: {b.heat_load:.0f} кВт/м³  
        Допустимая: {inp.max_heat_load:.0f} кВт/м³
        """)

with col3:
    st.subheader("Температура горения")
    st.info(f"""
    🌡️ T на выходе: **{inp.flue_gas_temp:.0f}°C**  
    
    T адиабатного горения: **{res.t_adiabatic:.0f}°C**  
    
    *Оценка температуры в зоне горения*
    """)

# =========================================================
# ЭКСПОРТ
# =========================================================
st.divider()
st.header("📄 Экспорт отчёта")

col1, col2 = st.columns(2)

with col1:
    try:
        pdf_bytes = export_to_pdf(res, summary_table, flue_gas_params)
        st.download_button(
            label="📥 Скачать PDF",
            data=pdf_bytes,
            file_name="thermal_balance.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    except Exception as e:
        st.warning(f"PDF экспорт недоступен: {e}")

with col2:
    txt_bytes = export_to_pdf_simple(res, summary_table, flue_gas_params)
    st.download_button(
        label="📥 Скачать TXT",
        data=txt_bytes,
        file_name="thermal_balance.txt",
        mime="text/plain",
        use_container_width=True,
    )

st.divider()
st.caption("Расчёт выполнен с использованием упрощённых формул. Для точного расчёта требуется лабораторный анализ топлива.")