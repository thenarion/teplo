"""
Страница Streamlit: Тепловой баланс сжигания топлива в барабанной печи.
Включает оценку полноты выгорания и тепловую нагрузку.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
import os

# Добавляем пути к модулям
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from calc.thermal_balance_calc import (
    ThermalBalanceInput,
    calculate_thermal_balance,
    get_summary_table,
    get_flue_gas_params,
    get_burnout_params,
)
from utils.pdf_export import export_to_pdf, export_to_pdf_simple


# =========================================================
# НАСТРОЙКА СТРАНИЦЫ
# =========================================================
st.set_page_config(
    page_title="Тепловой баланс",
    page_icon="🔥",
    layout="wide",
)

st.title("🔥 Тепловой баланс сжигания топлива")
st.markdown("Расчёт теплового баланса для вращающейся барабанной печи")

# =========================================================
# БОКОВАЯ ПАНЕЛЬ - ВХОДНЫЕ ДАННЫЕ
# =========================================================
with st.sidebar:
    st.header("⚙️ Исходные данные")

    st.subheader("Топливо")
    fuel_feed = st.number_input(
        "Подача влажного топлива, кг/ч",
        min_value=100.0,
        max_value=100000.0,
        value=3660.0,
        step=100.0,
        format="%.0f",
    )

    moisture = st.slider(
        "Влажность, %",
        min_value=10.0,
        max_value=90.0,
        value=50.0,
        step=1.0,
    ) / 100.0

    q_net_ar = st.number_input(
        "Низшая теплота сгорания, МДж/кг",
        min_value=1.0,
        max_value=50.0,
        value=12.42,
        step=0.5,
        format="%.2f",
    )

    ash_content = st.slider(
        "Зольность, %",
        min_value=0.0,
        max_value=60.0,
        value=20.0,
        step=1.0,
    ) / 100.0

    st.subheader("Режим горения")
    excess_air = st.slider(
        "Коэффициент избытка воздуха (α)",
        min_value=1.0,
        max_value=3.0,
        value=1.40,
        step=0.05,
        format="%.2f",
    )

    flue_gas_temp = st.number_input(
        "Температура дымовых газов на выходе, °C",
        min_value=100.0,
        max_value=1200.0,
        value=700.0,
        step=50.0,
        format="%.0f",
    )

    ambient_temp = st.number_input(
        "Температура наружного воздуха, °C",
        min_value=-50.0,
        max_value=50.0,
        value=10.0,
        step=5.0,
        format="%.0f",
    )

    st.subheader("Горелка")
    burner_power = st.number_input(
        "Мощность горелки (макс), МВт",
        min_value=0.0,
        max_value=20.0,
        value=1.6,
        step=0.1,
        format="%.1f",
    )

    burner_min_power = st.number_input(
        "Мощность горелки (мин), МВт",
        min_value=0.0,
        max_value=20.0,
        value=0.4,
        step=0.1,
        format="%.1f",
    )

    st.subheader("Геометрия барабана")
    drum_length = st.number_input(
        "Длина барабана, м",
        min_value=1.0,
        max_value=20.0,
        value=10.0,
        step=0.5,
        format="%.1f",
    )

    drum_diameter = st.number_input(
        "Диаметр барабана, м",
        min_value=0.5,
        max_value=3.0,
        value=1.9,
        step=0.1,
        format="%.1f",
    )

    residence_time = st.number_input(
        "Время пребывания отхода, мин",
        min_value=5.0,
        max_value=120.0,
        value=40.0,
        step=5.0,
        format="%.0f",
    )

    bulk_density = st.number_input(
        "Насыпная плотность отхода, кг/м³",
        min_value=100.0,
        max_value=1000.0,
        value=400.0,
        step=50.0,
        format="%.0f",
    )

    st.subheader("Дополнительно")
    wall_loss_pct = st.slider(
        "Потери через футеровку, %",
        min_value=2.0,
        max_value=20.0,
        value=8.0,
        step=1.0,
    ) / 100.0

    unburned_pct = st.slider(
        "Недожог, %",
        min_value=0.0,
        max_value=15.0,
        value=3.0,
        step=0.5,
    ) / 100.0

    ash_temp = st.number_input(
        "Температура золы на выходе, °C",
        min_value=100.0,
        max_value=1000.0,
        value=600.0,
        step=50.0,
        format="%.0f",
    )

    max_heat_load = st.number_input(
        "Макс. тепловая нагрузка, кВт/м³",
        min_value=50.0,
        max_value=500.0,
        value=200.0,
        step=10.0,
        format="%.0f",
    )

# =========================================================
# РАСЧЁТ
# =========================================================
inp = ThermalBalanceInput(
    fuel_feed=fuel_feed,
    moisture=moisture,
    q_net_ar=q_net_ar,
    ash_content=ash_content,
    excess_air=excess_air,
    flue_gas_temp=flue_gas_temp,
    ambient_temp=ambient_temp,
    burner_power=burner_power,
    burner_min_power=burner_min_power,
    wall_loss_pct=wall_loss_pct,
    unburned_pct=unburned_pct,
    ash_temp=ash_temp,
    drum_length=drum_length,
    drum_diameter=drum_diameter,
    residence_time=residence_time,
    bulk_density=bulk_density,
    max_heat_load=max_heat_load,
)

# Выполняем расчёт
res = calculate_thermal_balance(inp)

# Получаем таблицы
summary_table = get_summary_table(res)
flue_gas_params = get_flue_gas_params(res)
burnout_params = get_burnout_params(res)

# =========================================================
# ОСНОВНАЯ ЧАСТЬ - РЕЗУЛЬТАТЫ
# =========================================================

# Ключевые метрики
st.header("📊 Ключевые показатели")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric(
        "Тепловыделение топлива",
        f"{res.q_fuel:.3f} МВт",
        delta=None,
    )

with col2:
    st.metric(
        "Полезное тепло",
        f"{res.q_useful_with_burner:.3f} МВт",
        delta=f"+{res.input.burner_power:.1f} МВт горелка",
    )

with col3:
    st.metric(
        "КПД установки",
        f"{res.efficiency_with_burner*100:.1f}%",
        delta=f"{res.efficiency_no_burner*100:.1f}% без горелки",
        delta_color="off",
    )

with col4:
    st.metric(
        "Полнота выгорания",
        f"{res.burnout.burnout_efficiency*100:.1f}%",
        delta=f"запас ×{res.burnout.time_ratio:.2f}",
        delta_color="normal" if res.burnout.time_ratio >= 1.0 else "inverse",
    )

with col5:
    heat_load_status = "✅" if res.burnout.heat_load_ok else "❌"
    st.metric(
        f"Тепловая нагрузка {heat_load_status}",
        f"{res.burnout.heat_load:.0f} кВт/м³",
        delta=f"лимит {max_heat_load:.0f} кВт/м³",
        delta_color="normal" if res.burnout.heat_load_ok else "inverse",
    )

st.divider()

# =========================================================
# ПРЕДУПРЕЖДЕНИЯ
# =========================================================
warnings = []

if not res.burnout.fill_ratio_ok:
    warnings.append(f"⚠️ Степень заполнения барабана {res.burnout.fill_ratio*100:.1f}% превышает допустимую {inp.max_fill_ratio*100:.0f}%")

if not res.burnout.time_ok:
    warnings.append(f"⚠️ Время пребывания {inp.residence_time:.0f} мин меньше необходимого {res.burnout.t_required:.0f} мин")

if not res.burnout.heat_load_ok:
    warnings.append(f"⚠️ Тепловая нагрузка {res.burnout.heat_load:.0f} кВт/м³ превышает допустимую {inp.max_heat_load:.0f} кВт/м³")

if warnings:
    st.warning("\n".join(warnings))
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

# Вкладка 1: Массовый баланс
with tab1:
    st.subheader("Массовый баланс")

    mass_df = pd.DataFrame({
        "Компонент": [
            "Влажный помёт (всего)",
            "Вода",
            "Сухое вещество",
            "Зола",
            "Горючая масса",
        ],
        "Масса, кг/ч": [
            res.fuel_feed,
            res.water_mass,
            res.dry_mass,
            res.ash_mass,
            res.combustible_mass,
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

    # Диаграмма массового баланса
    fig_mass = px.pie(
        mass_df[1:],
        values="Масса, кг/ч",
        names="Компонент",
        title="Состав топлива",
        hole=0.3,
    )
    st.plotly_chart(fig_mass, use_container_width=True)

# Вкладка 2: Тепловой баланс
with tab2:
    st.subheader("Сводная таблица теплового баланса")

    balance_df = pd.DataFrame(summary_table)
    st.dataframe(balance_df, use_container_width=True, hide_index=True)

    # Диаграмма теплового баланса
    fig_heat = go.Figure()

    fig_heat.add_trace(go.Bar(
        x=["Приход"],
        y=[res.q_fuel],
        name="Тепло от топлива",
        marker_color="green",
    ))

    fig_heat.add_trace(go.Bar(
        x=["Приход"],
        y=[res.input.burner_power],
        name="Тепло от горелки",
        marker_color="lightgreen",
    ))

    fig_heat.add_trace(go.Bar(
        x=["Расход"],
        y=[res.q_flue_gas],
        name="Уходящие газы",
        marker_color="red",
    ))

    fig_heat.add_trace(go.Bar(
        x=["Расход"],
        y=[res.q_wall],
        name="Потери через футеровку",
        marker_color="orange",
    ))

    fig_heat.add_trace(go.Bar(
        x=["Расход"],
        y=[res.q_ash],
        name="Потери с золой",
        marker_color="yellow",
    ))

    fig_heat.add_trace(go.Bar(
        x=["Расход"],
        y=[res.q_unburned],
        name="Недожог",
        marker_color="gray",
    ))

    fig_heat.add_trace(go.Bar(
        x=["Расход"],
        y=[res.q_useful_with_burner],
        name="Полезное тепло",
        marker_color="blue",
    ))

    fig_heat.update_layout(
        title="Тепловой баланс, МВт",
        barmode="stack",
        yaxis_title="МВт",
    )

    st.plotly_chart(fig_heat, use_container_width=True)

# Вкладка 3: Воздух и газы
with tab3:
    st.subheader("Расход воздуха и дымовых газов")

    air_df = pd.DataFrame({
        "Параметр": [
            "Теоретический объём воздуха (на кг)",
            "Теоретический объём (на всю подачу)",
            f"Фактический объём воздуха (α={inp.excess_air:.2f})",
            "Масса воздуха",
            "Объём дымовых газов (н.у.)",
            "Масса дымовых газов",
            f"Объём газов при {inp.flue_gas_temp:.0f}°C",
            "Объём газов при 150°C",
        ],
        "Значение": [
            f"{res.v_air_theoretical_per_kg:.2f} Нм³/кг",
            f"{res.v_air_theoretical_total:.0f} Нм³/ч",
            f"{res.v_air_actual:.0f} Нм³/ч",
            f"{res.m_air:.0f} кг/ч",
            f"{res.v_flue:.0f} Нм³/ч",
            f"{res.m_flue:.0f} кг/ч",
            f"{res.v_flue_actual_hot:.0f} м³/ч",
            f"{res.v_flue_actual_cold:.0f} м³/ч",
        ],
    })

    st.dataframe(air_df, use_container_width=True, hide_index=True)

# Вкладка 4: Полнота выгорания
with tab4:
    st.subheader("Оценка полноты выгорания")

    # Индикатор
    b = res.burnout
    if b.overall_ok:
        st.success(f"✅ Отход успевает выгореть. Полнота выгорания: {b.burnout_efficiency*100:.1f}%")
    else:
        st.error(f"❌ Отход НЕ успевает полностью выгореть. Полнота выгорания: {b.burnout_efficiency*100:.1f}%")

    # Таблица параметров
    burnout_df = pd.DataFrame(burnout_params)
    st.dataframe(burnout_df, use_container_width=True, hide_index=True)

    # Диаграмма стадий выгорания
    st.subheader("Стадии выгорания")

    stages_df = pd.DataFrame({
        "Стадия": ["Сушка", "Нагрев", "Горение", "Дожигание"],
        "Время, мин": [b.t_drying, b.t_heating, b.t_combustion, b.t_burnout],
    })

    fig_stages = px.bar(
        stages_df,
        x="Стадия",
        y="Время, мин",
        title="Время по стадиям выгорания",
        color="Стадия",
        color_discrete_sequence=["#FF6B6B", "#FFA500", "#4ECDC4", "#45B7D1"],
    )

    # Добавляем линию фактического времени пребывания
    fig_stages.add_hline(
        y=inp.residence_time,
        line_dash="dash",
        line_color="red",
        annotation_text=f"Фактическое время: {inp.residence_time:.0f} мин",
    )

    # Добавляем линию необходимого времени
    fig_stages.add_hline(
        y=b.t_required,
        line_dash="dot",
        line_color="orange",
        annotation_text=f"Необходимое время: {b.t_required:.0f} мин",
    )

    st.plotly_chart(fig_stages, use_container_width=True)

    # График зависимости полноты выгорания от времени пребывания
    st.subheader("Зависимость полноты выгорания от времени пребывания")

    time_range = list(range(10, 130, 5))
    burnout_list = []

    for t in time_range:
        inp_temp = ThermalBalanceInput(
            fuel_feed=fuel_feed,
            moisture=moisture,
            q_net_ar=q_net_ar,
            ash_content=ash_content,
            excess_air=excess_air,
            flue_gas_temp=flue_gas_temp,
            ambient_temp=ambient_temp,
            burner_power=burner_power,
            burner_min_power=burner_min_power,
            wall_loss_pct=wall_loss_pct,
            unburned_pct=unburned_pct,
            ash_temp=ash_temp,
            drum_length=drum_length,
            drum_diameter=drum_diameter,
            residence_time=float(t),
            bulk_density=bulk_density,
            max_heat_load=max_heat_load,
        )
        res_temp = calculate_thermal_balance(inp_temp)
        burnout_list.append(res_temp.burnout.burnout_efficiency * 100)

    fig_burnout = go.Figure()

    fig_burnout.add_trace(go.Scatter(
        x=time_range,
        y=burnout_list,
        mode="lines+markers",
        name="Полнота выгорания, %",
        line=dict(color="green", width=2),
    ))

    fig_burnout.add_vline(
        x=inp.residence_time,
        line_dash="dash",
        line_color="red",
        annotation_text=f"Текущее время: {inp.residence_time:.0f} мин",
    )

    fig_burnout.add_hline(
        y=95,
        line_dash="dot",
        line_color="orange",
        annotation_text="Целевая полнота: 95%",
    )

    fig_burnout.update_layout(
        title="Полнота выгорания vs время пребывания",
        xaxis_title="Время пребывания, мин",
        yaxis_title="Полнота выгорания, %",
        yaxis_range=[50, 100],
    )

    st.plotly_chart(fig_burnout, use_container_width=True)

# Вкладка 5: Параметры для теплообменника
with tab5:
    st.subheader("Параметры дымовых газов для теплообменника")

    gas_df = pd.DataFrame(flue_gas_params)
    st.dataframe(gas_df, use_container_width=True, hide_index=True)

    st.info("""
    **Рекомендации:**
    - Температура газов на выходе из теплообменника: 150–200°C
    - Теплоноситель: вода или антифриз (в зависимости от климата)
    - При температуре ниже 150°C возможна кислотная роса
    - Для рукавных фильтров: температура не выше 200°C
    """)

# =========================================================
# ВЫВОДЫ
# =========================================================
st.divider()
st.header("📝 Выводы")

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("Автотермичность")
    if res.q_useful_no_burner > 0:
        st.success(f"""
        ✅ Процесс **автотермичный**.
        
        Тепловыделение: {res.q_fuel:.3f} МВт
        Потери: {res.q_loss_total:.3f} МВт
        """)
    else:
        st.error(f"""
        ❌ Процесс **НЕ автотермичный**.
        
        Тепловыделение: {res.q_fuel:.3f} МВт
        Потери: {res.q_loss_total:.3f} МВт
        """)

with col2:
    st.subheader("Полнота выгорания")
    b = res.burnout
    if b.overall_ok:
        st.success(f"""
        ✅ Отход **успевает выгореть**.
        
        Полнота: {b.burnout_efficiency*100:.1f}%
        Запас времени: ×{b.time_ratio:.2f}
        Степень заполнения: {b.fill_ratio*100:.1f}%
        """)
    else:
        st.error(f"""
        ❌ Отход **НЕ успевает выгореть**.
        
        Полнота: {b.burnout_efficiency*100:.1f}%
        Запас времени: ×{b.time_ratio:.2f}
        Степень заполнения: {b.fill_ratio*100:.1f}%
        """)

with col3:
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
        
        Рекомендуется уменьшить подачу или увеличить объём барабана.
        """)

# =========================================================
# РЕКОМЕНДАЦИИ
# =========================================================
st.divider()
st.header("💡 Рекомендации")

recommendations = []

if not res.burnout.time_ok:
    required_increase = res.burnout.t_required / inp.residence_time
    recommendations.append(f"⏱️ Увеличить время пребывания до {res.burnout.t_required:.0f} мин (×{required_increase:.2f})")
    recommendations.append(f"   или уменьшить подачу до {inp.fuel_feed / required_increase:.0f} кг/ч")

if not res.burnout.fill_ratio_ok:
    recommendations.append(f"📦 Уменьшить степень заполнения: уменьшить подачу или увеличить объём барабана")

if not res.burnout.heat_load_ok:
    max_feed = inp.fuel_feed * (inp.max_heat_load / res.burnout.heat_load)
    recommendations.append(f"🔥 Уменьшить подачу до {max_feed:.0f} кг/ч для снижения тепловой нагрузки")

if res.burnout.overall_ok and res.q_useful_no_burner > 0:
    recommendations.append("✅ Все параметры в норме. Установка работает в допустимом режиме.")

if recommendations:
    for rec in recommendations:
        st.markdown(f"- {rec}")
else:
    st.info("Рекомендации не требуются.")

# =========================================================
# ЭКСПОРТ В PDF
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

# =========================================================
# ПОДВАЛ
# =========================================================
st.divider()
st.caption("Расчёт выполнен с использованием упрощённых формул. Для точного расчёта требуется лабораторный анализ топлива.")