import sys
from pathlib import Path

# Чтобы импорт calc работал при запуске из корня проекта
sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st

from calc.variant1_gas_air import (
    Variant1Inputs,
    calculate_variant1,
    CalcError as CalcErrorV1,
)

from calc.variant2_gas_liquid_avo import (
    Variant2Inputs,
    calculate_variant2,
    CalcError as CalcErrorV2,
    recommend_glycol_concentration,
)


# ------------------------------------------------------------------
# Вспомогательные функции интерфейса
# ------------------------------------------------------------------
def fmt(x: float, nd: int = 1, unit: str = "") -> str:
    try:
        s = f"{float(x):,.{nd}f}".replace(",", " ")
    except Exception:
        s = str(x)
    return f"{s} {unit}".strip()


def metrics_grid(items, ncols: int = 4) -> None:
    if not items:
        return

    for i in range(0, len(items), ncols):
        cols = st.columns(ncols)
        for j, item in enumerate(items[i:i + ncols]):
            label, value, help_text = item
            with cols[j]:
                st.metric(label=label, value=value, help=help_text)


def render_variant1_result(res) -> None:
    for msg in res.messages:
        st.warning(msg)

    st.subheader("Основные результаты варианта 1")

    metrics_grid(
        [
            (
                "Площадь теплообмена",
                fmt(res.area_req_m2, 0, "м²"),
                "Требуемая площадь газовоздушного теплообменника по методу LMTD: A = Q / (U · F · ΔT_lm).",
            ),
            (
                "Расход воздуха от вентилятора",
                fmt(res.air_volume_flow_amb_m3h, 0, "м³/ч"),
                "Фактический объёмный расход воздуха при температуре окружающей среды, который нужно подать вентилятором.",
            ),
            (
                "Мощность двигателя вентилятора",
                fmt(res.fan_motor_power_kw, 1, "кВт"),
                "Ориентировочная мощность электродвигателя воздушного вентилятора с учётом КПД и запаса.",
            ),
            (
                "Габариты ТО, D × L",
                f"{res.shell_diameter_m:.2f} × {res.length_overall_m:.2f} м",
                "Ориентировочный диаметр корпуса и габаритная длина трубной секции газовоздушного теплообменника.",
            ),
            (
                "Масса теплообменника",
                fmt(res.mass_total_t, 2, "т"),
                "Ориентировочная масса металлоконструкции газовоздушного теплообменника без изоляции и вентиляторов.",
            ),
        ],
        ncols=5,
    )

    with st.expander("Тепловой режим варианта 1", expanded=False):
        metrics_grid(
            [
                (
                    "Тепловая нагрузка Q",
                    fmt(res.heat_duty_kw, 0, "кВт"),
                    "Теплота, снимаемая с дымовых газов в газовоздушном теплообменнике.",
                ),
                (
                    "T газов после подсоса",
                    fmt(res.t_gas_after_leak_c, 0, "°C"),
                    "Температура газов перед теплообменником после подсоса воздуха на циклонах.",
                ),
                (
                    "T газов на выходе",
                    fmt(res.t_gas_out_c, 0, "°C"),
                    "Заданная температура газов после теплообменника.",
                ),
                (
                    "T воздуха на выходе",
                    fmt(res.t_air_out_c, 0, "°C"),
                    "Заданная температура нагретого воздуха.",
                ),
                (
                    "LMTD",
                    fmt(res.lmtd_k, 1, "K"),
                    "Среднелогарифмический температурный напор.",
                ),
                (
                    "Эффективность ε",
                    fmt(res.effectiveness, 3, ""),
                    "Отношение фактического теплообмена к максимально возможному.",
                ),
                (
                    "NTU",
                    fmt(res.ntu, 2, ""),
                    "Число единиц переноса: NTU = UA / C_min.",
                ),
                (
                    "UA",
                    fmt(res.ua_w_per_k, 0, "Вт/K"),
                    "Общая теплопроводность аппарата: U · A.",
                ),
            ],
            ncols=4,
        )

    with st.expander("Конструкция и аэродинамика варианта 1", expanded=False):
        metrics_grid(
            [
                (
                    "Число труб",
                    f"{int(res.n_tubes)} шт.",
                    "Предварительное число труб в трубном пучке.",
                ),
                (
                    "Длина трубной части",
                    fmt(res.tube_length_m, 2, "м"),
                    "Расчётная длина трубной части до добавки на камеры и патрубки.",
                ),
                (
                    "Скорость газов в трубах",
                    fmt(res.gas_velocity_ms, 1, "м/с"),
                    "Средняя скорость газового потока в трубах.",
                ),
                (
                    "Сопротивление газового тракта",
                    fmt(res.gas_pressure_drop_pa, 0, "Па"),
                    "Ориентировочное сопротивление трубного хода газов.",
                ),
                (
                    "Конструктивная площадь",
                    fmt(res.area_provided_m2, 0, "м²"),
                    "Фактическая площадь теплообмена, полученная после выбора числа и длины труб.",
                ),
                (
                    "Диаметр корпуса",
                    fmt(res.shell_diameter_m, 2, "м"),
                    "Ориентировочный диаметр корпуса теплообменника.",
                ),
            ],
            ncols=3,
        )


def render_variant2_result(res) -> None:
    for msg in res.messages:
        st.warning(msg)

    st.subheader("Основные результаты варианта 2")

    st.info(res.recommendation_text)

    metrics_grid(
        [
            (
                "Площадь ТО на печи",
                fmt(res.gl_area_req_m2, 0, "м²"),
                "Требуемая площадь газо-жидкостного теплообменника, установленного после циклонов.",
            ),
            (
                "Габариты ТО на печи",
                f"{res.gl_shell_diameter_m:.2f} × {res.gl_length_overall_m:.2f} м",
                "Ориентировочный диаметр корпуса и длина газо-жидкостного теплообменника на печи.",
            ),
            (
                "Масса ТО на печи",
                fmt(res.gl_mass_t, 2, "т"),
                "Ориентировочная масса газо-жидкостного теплообменника на печи.",
            ),
            (
                "Расход жидкости",
                fmt(res.liq_volume_flow_m3h, 1, "м³/ч"),
                "Объёмный расход теплоносителя через газо-жидкостный теплообменник и контур.",
            ),
            (
                "Мощность насоса",
                fmt(res.pump_motor_kw, 2, "кВт"),
                "Ориентировочная мощность электродвигателя циркуляционного насоса жидкостного контура.",
            ),
        ],
        ncols=5,
    )

    metrics_grid(
        [
            (
                "Площадь АВО",
                fmt(res.avo_area_req_m2, 0, "м²"),
                "Требуемая площадь теплообмена воздушного охладителя. Для оребрённых аппаратов должна соответствовать типу используемой поверхности.",
            ),
            (
                "Габариты АВО",
                f"фронт ≈ {res.avo_front_side_m:.2f} × {res.avo_front_side_m:.2f} м; глубина ≈ {res.avo_depth_m:.2f} м",
                "Очень приближённые габариты АВО по площади фронта и объёму пакета.",
            ),
            (
                "Масса АВО",
                fmt(res.avo_mass_t, 2, "т"),
                "Ориентировочная масса АВО по удельной массе на единицу площади теплообмена.",
            ),
            (
                "Расход воздуха АВО",
                fmt(res.avo_air_volume_flow_m3h, 0, "м³/ч"),
                "Требуемый объёмный расход воздуха через АВО при расчётной температуре окружающей среды.",
            ),
            (
                "Мощность вентилятора АВО",
                fmt(res.avo_fan_motor_kw, 2, "кВт"),
                "Ориентировочная мощность электродвигателя вентилятора АВО с учётом КПД и запаса.",
            ),
        ],
        ncols=5,
    )

    metrics_grid(
        [
            (
                "Общая масса оборудования",
                fmt(res.total_mass_t, 2, "т"),
                "Суммарная ориентировочная масса газо-жидкостного ТО и АВО.",
            ),
            (
                "Суммарная мощность приводов",
                fmt(res.total_power_kw, 2, "кВт"),
                "Суммарная ориентировочная мощность насоса и вентилятора АВО.",
            ),
            (
                "Тепловая нагрузка",
                fmt(res.heat_duty_kw, 0, "кВт"),
                "Теплота, снимаемая с дымовых газов и отводимая через жидкостный контур в АВО.",
            ),
            (
                "T газов после подсоса",
                fmt(res.t_gas_after_leak_c, 0, "°C"),
                "Температура газов перед газо-жидкостным ТО с учётом подсоса на циклонах.",
            ),
            (
                "T жидкости в ТО",
                f"{res.t_liq_in_c:.1f} / {res.t_liq_out_c:.1f} °C",
                "Температура жидкости на входе и выходе из газо-жидкостного теплообменника.",
            ),
        ],
        ncols=5,
    )

    with st.expander("Теплоноситель и свойства", expanded=True):
        metrics_grid(
            [
                (
                    "Теплоноситель",
                    res.fluid_type,
                    "Выбранный тип гликоля: этиленгликоль или пропиленгликоль.",
                ),
                (
                    "Выбранная концентрация",
                    fmt(res.selected_concentration_pct, 0, "%"),
                    "Массовая концентрация гликоля, использованная в тепловом расчёте.",
                ),
                (
                    "Рекомендуемая концентрация",
                    fmt(res.recommended_concentration_pct, 0, "%"),
                    "Минимальная массовая концентрация по отдельной минимальной эксплуатационной температуре.",
                ),
                (
                    "T замерзания выбранного раствора",
                    fmt(res.freeze_point_selected_c, 1, "°C"),
                    "Ориентировочная температура замерзания раствора выбранной концентрации.",
                ),
                (
                    "Плотность жидкости",
                    fmt(res.liq_density_kgm3, 0, "кг/м³"),
                    "Плотность теплоносителя при средней температуре жидкостного контура.",
                ),
                (
                    "cp жидкости",
                    fmt(res.liq_cp_kjkgk, 3, "кДж/(кг·K)"),
                    "Теплоёмкость теплоносителя при средней температуре жидкостного контура.",
                ),
                (
                    "Вязкость жидкости",
                    fmt(res.liq_viscosity_mpas, 2, "мПа·с"),
                    "Ориентировочная динамическая вязкость теплоносителя при средней температуре.",
                ),
                (
                    "Массовый расход жидкости",
                    fmt(res.liq_mass_flow_kgs, 2, "кг/с"),
                    "Массовый расход теплоносителя, обеспечивающий съём расчётной тепловой нагрузки.",
                ),
            ],
            ncols=4,
        )

    with st.expander("Газо-жидкостный ТО на печи", expanded=False):
        metrics_grid(
            [
                (
                    "Требуемая площадь",
                    fmt(res.gl_area_req_m2, 0, "м²"),
                    "Площадь газо-жидкостного теплообменника по LMTD.",
                ),
                (
                    "Конструктивная площадь",
                    fmt(res.gl_area_provided_m2, 0, "м²"),
                    "Площадь, полученная после выбора числа и длины труб.",
                ),
                (
                    "LMTD",
                    fmt(res.gl_lmtd_k, 1, "K"),
                    "Среднелогарифмический напор для газо-жидкостного теплообменника.",
                ),
                (
                    "U",
                    fmt(res.gl_U_Wm2K, 0, "Вт/(м²·K)"),
                    "Коэффициент теплопередачи газо-жидкостного ТО.",
                ),
                (
                    "Число труб",
                    f"{int(res.gl_n_tubes)} шт.",
                    "Предварительное число труб в газо-жидкостном ТО.",
                ),
                (
                    "Длина трубной части",
                    fmt(res.gl_tube_length_m, 2, "м"),
                    "Расчётная длина трубной части газо-жидкостного ТО.",
                ),
                (
                    "Скорость газов",
                    fmt(res.gl_gas_velocity_ms, 1, "м/с"),
                    "Средняя скорость газов в трубах газо-жидкостного ТО.",
                ),
                (
                    "Сопротивление газов",
                    fmt(res.gl_gas_pressure_drop_pa, 0, "Па"),
                    "Ориентировочное сопротивление газового тракта газо-жидкостного ТО.",
                ),
            ],
            ncols=4,
        )

    with st.expander("АВО и насос", expanded=False):
        metrics_grid(
            [
                (
                    "Площадь АВО требуемая",
                    fmt(res.avo_area_req_m2, 0, "м²"),
                    "Требуемая площадь теплообмена АВО.",
                ),
                (
                    "Площадь АВО конструктивная",
                    fmt(res.avo_area_provided_m2, 0, "м²"),
                    "Площадь АВО, полученная после выбора числа и длины труб.",
                ),
                (
                    "LMTD АВО",
                    fmt(res.avo_lmtd_k, 1, "K"),
                    "Среднелогарифмический напор в АВО.",
                ),
                (
                    "U АВО",
                    fmt(res.avo_U_Wm2K, 0, "Вт/(м²·K)"),
                    "Коэффициент теплопередачи АВО. Для оребрённых теплообменников должен соответствовать выбранной поверхности.",
                ),
                (
                    "T воздуха на выходе АВО",
                    fmt(res.avo_air_out_c, 1, "°C"),
                    "Температура воздуха после АВО при заданном нагреве воздуха.",
                ),
                (
                    "Скорость жидкости в трубах АВО",
                    fmt(res.avo_liquid_velocity_ms, 2, "м/с"),
                    "Средняя скорость теплоносителя в трубах АВО.",
                ),
                (
                    "Площадь фронта АВО",
                    fmt(res.avo_face_area_m2, 2, "м²"),
                    "Требуемая площадь фронта АВО по расчётному расходу воздуха и заданной скорости во фронте.",
                ),
                (
                    "Объём пакета АВО",
                    fmt(res.avo_volume_m3, 2, "м³"),
                    "Ориентировочный объём теплообменного пакета АВО.",
                ),
                (
                    "Гидравлическая мощность насоса",
                    fmt(res.pump_hydraulic_kw, 2, "кВт"),
                    "Гидравлическая мощность: Qv · Δp.",
                ),
                (
                    "Мощность насоса на валу",
                    fmt(res.pump_shaft_kw, 2, "кВт"),
                    "Мощность на валу насоса с учётом КПД.",
                ),
                (
                    "Мощность двигателя насоса",
                    fmt(res.pump_motor_kw, 2, "кВт"),
                    "Мощность электродвигателя насоса с запасом.",
                ),
                (
                    "Мощность вентилятора АВО",
                    fmt(res.avo_fan_motor_kw, 2, "кВт"),
                    "Мощность электродвигателя вентилятора АВО с запасом.",
                ),
            ],
            ncols=4,
        )


def render_comparison(res1, res2) -> None:
    st.subheader("Сравнительный анализ двух вариантов охлаждения")

    mass1 = res1.mass_total_t
    power1 = res1.fan_motor_power_kw

    mass2 = res2.total_mass_t
    power2 = res2.total_power_kw

    metrics_grid(
        [
            (
                "Масса варианта 1",
                fmt(mass1, 2, "т"),
                "Ориентировочная масса газовоздушного теплообменника.",
            ),
            (
                "Масса варианта 2",
                fmt(mass2, 2, "т"),
                "Ориентировочная масса газо-жидкостного ТО и АВО.",
            ),
            (
                "Мощность варианта 1",
                fmt(power1, 2, "кВт"),
                "Ориентировочная мощность вентилятора воздушного теплообменника.",
            ),
            (
                "Мощность варианта 2",
                fmt(power2, 2, "кВт"),
                "Ориентировочная мощность насоса и вентилятора АВО.",
            ),
        ],
        ncols=4,
    )

    st.markdown(
        f"""
        | Показатель | Вариант 1: газовоздушный | Вариант 2: жидкостный + АВО |
        |---|---:|---:|
        | Тепловая нагрузка, кВт | {res1.heat_duty_kw:,.0f} | {res2.heat_duty_kw:,.0f} |
        | Площадь ТО на печи, м² | {res1.area_req_m2:,.0f} | {res2.gl_area_req_m2:,.0f} |
        | Площадь АВО, м² | — | {res2.avo_area_req_m2:,.0f} |
        | Общая масса оборудования, т | {mass1:,.2f} | {mass2:,.2f} |
        | Суммарная мощность приводов, кВт | {power1:,.2f} | {power2:,.2f} |
        """
    )

    max_mass = max(mass1, mass2, 1e-6)
    max_power = max(power1, power2, 1e-6)

    score1 = mass1 / max_mass + power1 / max_power
    score2 = mass2 / max_mass + power2 / max_power

    if score1 < score2 * 0.98:
        conclusion = (
            "По формальным критериям массы оборудования и потребляемой мощности приводов более целесообразен "
            "Вариант 1: газовоздушный теплообменник. Он проще, обычно имеет меньшую массу и меньше вспомогательных потребителей, "
            "если нагретый воздух можно использовать технологически или безопасно сбросить."
        )
        st.success(conclusion)
    elif score2 < score1 * 0.98:
        conclusion = (
            "По формальным критериям массы оборудования и потребляемой мощности приводов более целесообразен "
            "Вариант 2: газо-жидкостный теплообменник с АВО. Он может быть предпочтителен, если тепло нужно вынести из зоны печи, "
            "использовать промежуточный контур, обеспечить гибкую трассировку или стабилизировать температурный режим."
        )
        st.success(conclusion)
    else:
        if mass1 < mass2 and power1 > power2:
            conclusion = (
                "Вариант 1 имеет меньшую массу, но большую установленную мощность привода. "
                "Если приоритет — минимальная масса и простота, выбираем Вариант 1. "
                "Если приоритет — снижение установленной мощности или эксплуатационных затрат, предпочтительнее Вариант 2."
            )
        elif mass2 < mass1 and power2 > power1:
            conclusion = (
                "Вариант 2 имеет меньшую массу, но большую установленную мощность привода. "
                "Если приоритет — минимальная масса и вынос теплоотвода, выбираем Вариант 2. "
                "Если приоритет — минимальная мощность, предпочтительнее Вариант 1."
            )
        else:
            conclusion = (
                "Оба варианта сопоставимы по формальным критериям массы и мощности. "
                "Итоговый выбор следует делать по стоимости жизненного цикла, компоновке, требованиям эксплуатации, "
                "наличию потребителя нагретого воздуха, допустимым температурам и надёжности."
            )
        st.info(conclusion)

    st.markdown(
        """
        ### Дополнительные факторы выбора
        - **Вариант 1** обычно проще, дешевле по капитальным затратам и не имеет жидкостного контура.
        - **Вариант 2** позволяет вынести АВО отдельно от печи, использовать трубопроводы, гибче размещать оборудование и применять незамерзающие растворы.
        - Для выбора по фактическим эксплуатационным затратам нужно знать график работы, стоимость электроэнергии и требования к использованию сбросного тепла.
        - При низких температурах уходящих газов нужно отдельно проверять кислотную и водяную точку росы.
        """
    )


# ------------------------------------------------------------------
# Инициализация session_state
# ------------------------------------------------------------------
if "res1" not in st.session_state:
    st.session_state.res1 = None
if "err1" not in st.session_state:
    st.session_state.err1 = None
if "res2" not in st.session_state:
    st.session_state.res2 = None
if "err2" not in st.session_state:
    st.session_state.err2 = None


st.title("Теплообменный аппарат барабанной печи")
st.markdown(
    """
    **Схема:** камера сгорания → дожигатель → блок циклонов → теплообменный аппарат.  
    Общие исходные данные по газовому контуру задаются один раз ниже и используются обоими вариантами.
    """
)


# ------------------------------------------------------------------
# Общие исходные данные выше вкладок
# ------------------------------------------------------------------
st.subheader("Общие исходные данные по газовому контуру")

c1, c2, c3 = st.columns(3)

with c1:
    t_gas_in = st.number_input(
        "Температура дымовых газов перед циклонами, °C",
        min_value=-50.0,
        max_value=2000.0,
        value=600.0,
        step=10.0,
        key="common_t_gas_in",
        help="Температура газов до подсоса воздуха в циклонах.",
    )

    gas_flow = st.number_input(
        "Расход дымовых газов, Нм³/ч",
        min_value=0.0,
        value=10000.0,
        step=100.0,
        key="common_gas_flow",
        help="Нормальный объёмный расход дымовых газов при 0 °C и 101.325 кПа.",
    )

with c2:
    t_amb_calc = st.number_input(
        "Температура окружающей среды для расчёта, °C",
        min_value=-60.0,
        max_value=60.0,
        value=25.0,
        step=1.0,
        key="common_t_amb_calc",
        help=(
            "Расчётная температура окружающей среды для варианта 1 и для АВО в варианте 2. "
            "Не используется для подбора концентрации гликоля. Для концентрации есть отдельное поле в варианте 2."
        ),
    )

    leak_pct = st.number_input(
        "Подсос воздуха в циклонах, %",
        min_value=0.0,
        max_value=500.0,
        value=10.0,
        step=1.0,
        key="common_leak_pct",
        help="Подсос атмосферного воздуха на циклонах перед теплообменным аппаратом.",
    )

    leak_basis = st.selectbox(
        "База для подсоса воздуха",
        options=["Объём (н.у.)", "Масса"],
        key="common_leak_basis",
        help="Если выбран объём, проценты берутся от нормального объёма газов. Если масса — от массового расхода газов.",
    )

with c3:
    t_gas_out_common = st.number_input(
        "Температура газов после ТО на печи, °C",
        min_value=-50.0,
        max_value=2000.0,
        value=200.0,
        step=10.0,
        key="common_t_gas_out",
        help="Целевая температура дымовых газов после теплообменника на печи. Общая для обоих вариантов.",
    )

with st.expander("Общие свойства газов и воздуха"):
    p1, p2, p3, p4 = st.columns(4)

    with p1:
        cp_gas = st.number_input(
            "cp дымовых газов, кДж/(кг·K)",
            min_value=0.5,
            max_value=3.0,
            value=1.08,
            step=0.01,
            format="%.3f",
            key="common_cp_gas",
            help="Средняя теплоёмкость дымовых газов.",
        )

    with p2:
        cp_air = st.number_input(
            "cp воздуха, кДж/(кг·K)",
            min_value=0.5,
            max_value=3.0,
            value=1.005,
            step=0.01,
            format="%.3f",
            key="common_cp_air",
            help="Теплоёмкость воздуха.",
        )

    with p3:
        rho_gas_n = st.number_input(
            "Плотность газов при н.у., кг/Нм³",
            min_value=0.5,
            max_value=3.0,
            value=1.30,
            step=0.01,
            format="%.3f",
            key="common_rho_gas_n",
            help="Плотность дымовых газов при нормальных условиях.",
        )

    with p4:
        rho_air_n = st.number_input(
            "Плотность воздуха при н.у., кг/Нм³",
            min_value=0.5,
            max_value=3.0,
            value=1.293,
            step=0.01,
            format="%.3f",
            key="common_rho_air_n",
            help="Плотность воздуха при нормальных условиях.",
        )


tab1, tab2, tab3 = st.tabs(
    [
        "Вариант 1: газовоздушный",
        "Вариант 2: газожидкостный + АВО",
        "Сравнение вариантов",
    ]
)


# ------------------------------------------------------------------
# Вкладка 1
# ------------------------------------------------------------------
with tab1:
    st.subheader("Вариант 1: газовоздушный теплообмен")

    v1c1, v1c2, v1c3 = st.columns(3)

    with v1c1:
        v1_t_air_out = st.number_input(
            "Температура нагретого воздуха, °C",
            min_value=-50.0,
            max_value=2000.0,
            value=150.0,
            step=10.0,
            key="v1_t_air_out",
            help="Требуемая температура воздуха после газовоздушного теплообменника.",
        )

        v1_U = st.number_input(
            "U газовоздушного ТО, Вт/(м²·K)",
            min_value=1.0,
            max_value=2000.0,
            value=40.0,
            step=5.0,
            key="v1_U",
            help="Коэффициент теплопередачи для газ–воздух. Для гладких труб часто 20–60 Вт/(м²·K).",
        )

        v1_F = st.number_input(
            "Поправка LMTD, F",
            min_value=0.1,
            max_value=1.0,
            value=0.95,
            step=0.01,
            key="v1_F",
            help="Поправка на схему течения. 1 — противоток, обычно 0.85–0.95 для перекрёстного тока.",
        )

    with v1c2:
        v1_fan_dp = st.number_input(
            "Полное давление вентилятора, Па",
            min_value=0.0,
            value=1200.0,
            step=100.0,
            key="v1_fan_dp",
            help="Суммарное сопротивление воздушного тракта.",
        )

        v1_fan_eff = st.number_input(
            "КПД вентилятора",
            min_value=0.05,
            max_value=1.0,
            value=0.65,
            step=0.01,
            key="v1_fan_eff",
            help="Ориентировочный КПД вентилятора.",
        )

        v1_motor_margin = st.number_input(
            "Запас мощности двигателя",
            min_value=1.0,
            max_value=3.0,
            value=1.15,
            step=0.05,
            key="v1_motor_margin",
            help="Коэффициент запаса к мощности вентилятора.",
        )

    with st.expander("Конструкция газовоздушного ТО"):
        g1, g2, g3 = st.columns(3)

        with g1:
            v1_target_v = st.number_input(
                "Целевая скорость газов в трубах, м/с",
                min_value=0.0,
                max_value=60.0,
                value=15.0,
                step=1.0,
                key="v1_target_v",
                help="Рекомендуется 8–20 м/с.",
            )

            v1_tube_od = st.number_input(
                "Наружный диаметр труб, мм",
                min_value=5.0,
                max_value=500.0,
                value=32.0,
                step=1.0,
                key="v1_tube_od",
            )

            v1_tube_wall = st.number_input(
                "Толщина стенки труб, мм",
                min_value=0.5,
                max_value=50.0,
                value=2.0,
                step=0.5,
                key="v1_tube_wall",
            )

        with g2:
            v1_tube_max_l = st.number_input(
                "Максимальная длина труб, м",
                min_value=0.3,
                max_value=20.0,
                value=3.0,
                step=0.1,
                key="v1_tube_max_l",
            )

            v1_tube_min_l = st.number_input(
                "Минимальная длина труб, м",
                min_value=0.1,
                max_value=20.0,
                value=0.5,
                step=0.1,
                key="v1_tube_min_l",
            )

            v1_pitch = st.number_input(
                "Шаг труб, t/d",
                min_value=1.05,
                max_value=3.0,
                value=1.30,
                step=0.05,
                key="v1_pitch",
            )

            v1_layout = st.number_input(
                "Коэффициент заполнения трубной доски",
                min_value=0.50,
                max_value=0.95,
                value=0.85,
                step=0.01,
                key="v1_layout",
            )

        with g3:
            v1_shell_th = st.number_input(
                "Толщина стенки корпуса, мм",
                min_value=1.0,
                max_value=100.0,
                value=4.0,
                step=1.0,
                key="v1_shell_th",
            )

            v1_tubesheet_th = st.number_input(
                "Толщина трубной доски, мм",
                min_value=5.0,
                max_value=300.0,
                value=20.0,
                step=1.0,
                key="v1_tubesheet_th",
            )

            v1_mass_factor = st.number_input(
                "Коэффициент добавочной массы",
                min_value=1.0,
                max_value=3.0,
                value=1.25,
                step=0.05,
                key="v1_mass_factor",
            )

            v1_steel_density = st.number_input(
                "Плотность стали, кг/м³",
                min_value=1000.0,
                max_value=10000.0,
                value=7850.0,
                step=50.0,
                key="v1_steel_density",
            )

    def build_var1_inputs() -> Variant1Inputs:
        return Variant1Inputs(
            t_gas_in_c=float(t_gas_in),
            gas_flow_nm3h=float(gas_flow),
            t_amb_c=float(t_amb_calc),
            leakage_pct=float(leak_pct),
            t_gas_out_c=float(t_gas_out_common),
            t_air_out_c=float(v1_t_air_out),
            leakage_basis=leak_basis,
            cp_gas_kjkgk=float(cp_gas),
            cp_air_kjkgk=float(cp_air),
            rho_gas_n_kgm3=float(rho_gas_n),
            rho_air_n_kgm3=float(rho_air_n),
            U_Wm2K=float(v1_U),
            lmtd_correction=float(v1_F),
            fan_dp_pa=float(v1_fan_dp),
            fan_eff=float(v1_fan_eff),
            motor_margin=float(v1_motor_margin),
            target_gas_velocity_ms=float(v1_target_v),
            tube_od_mm=float(v1_tube_od),
            tube_wall_mm=float(v1_tube_wall),
            tube_max_length_m=float(v1_tube_max_l),
            tube_min_length_m=float(v1_tube_min_l),
            pitch_ratio=float(v1_pitch),
            layout_eff=float(v1_layout),
            shell_thickness_mm=float(v1_shell_th),
            tubesheet_thickness_mm=float(v1_tubesheet_th),
            mass_factor=float(v1_mass_factor),
            steel_density=float(v1_steel_density),
        )

    if st.button("Рассчитать вариант 1", key="btn_calc_var1", type="primary"):
        st.session_state.res1 = None
        st.session_state.err1 = None

        try:
            inp1 = build_var1_inputs()
            st.session_state.res1 = calculate_variant1(inp1)
        except CalcErrorV1 as e:
            st.session_state.err1 = str(e)
        except Exception as e:
            st.session_state.err1 = str(e)

    if st.session_state.err1:
        st.error(f"Ошибка варианта 1: {st.session_state.err1}")

    if st.session_state.res1:
        render_variant1_result(st.session_state.res1)


# ------------------------------------------------------------------
# Вкладка 2
# ------------------------------------------------------------------
with tab2:
    st.subheader("Вариант 2: газожидкостный теплообменник + АВО")

    v2c1, v2c2, v2c3 = st.columns(3)

    with v2c1:
        v2_fluid = st.selectbox(
            "Жидкость для охлаждения",
            options=["Этиленгликоль", "Пропиленгликоль"],
            key="v2_fluid",
            help="Этиленгликоль обычно дешевле, но токсичнее. Пропиленгликоль безопаснее.",
        )

        v2_conc_mode = st.radio(
            "Способ выбора концентрации",
            options=[
                "Автоматически по минимальной температуре",
                "Вручную",
            ],
            key="v2_conc_mode",
        )

        v2_design_min = st.number_input(
            "Минимальная температура эксплуатации для подбора концентрации, °C",
            min_value=-80.0,
            max_value=50.0,
            value=-20.0,
            step=1.0,
            key="v2_design_min",
            help=(
                "Отдельная величина для подбора концентрации раствора. "
                "Не привязана к расчётной температуре окружающей среды для теплотехнического расчёта."
            ),
        )

        v2_safety = st.number_input(
            "Запас по замерзанию, K",
            min_value=0.0,
            max_value=20.0,
            value=3.0,
            step=1.0,
            key="v2_safety",
            help="Раствор подбирается так, чтобы температура замерзания была ниже минимальной эксплуатационной на этот запас.",
        )

        if v2_conc_mode == "Вручную":
            v2_manual_conc = st.number_input(
                "Массовая концентрация гликоля, %",
                min_value=0.0,
                max_value=100.0,
                value=40.0,
                step=1.0,
                key="v2_manual_conc",
                help="Массовая концентрация гликоля в растворе.",
            )
        else:
            v2_manual_conc = 40.0

        try:
            rec_conc, rec_fp, rec_text = recommend_glycol_concentration(
                fluid_type=v2_fluid,
                design_min_temp_c=float(v2_design_min),
                safety_k=float(v2_safety),
            )
            st.info(
                f"Рекомендация: {rec_conc:.0f} масс.% | "
                f"T замерзания ≈ {rec_fp:.1f} °C | "
                f"{rec_text}"
            )
        except Exception as e:
            st.warning(f"Не удалось выдать рекомендацию по концентрации: {e}")

    with v2c2:
        v2_t_liq_in = st.number_input(
            "Температура жидкости на входе в ТО на печи, °C",
            min_value=-50.0,
            max_value=500.0,
            value=50.0,
            step=5.0,
            key="v2_t_liq_in",
            help="Охлаждённая жидкость после АВО поступает в газо-жидкостный ТО на печи.",
        )

        v2_t_liq_out = st.number_input(
            "Температура жидкости на выходе из ТО на печи, °C",
            min_value=-50.0,
            max_value=500.0,
            value=70.0,
            step=5.0,
            key="v2_t_liq_out",
            help="Нагретая жидкость после газо-жидкостного ТО уходит в АВО.",
        )

        v2_U_gl = st.number_input(
            "U газо-жидкостного ТО, Вт/(м²·K)",
            min_value=1.0,
            max_value=2000.0,
            value=80.0,
            step=5.0,
            key="v2_U_gl",
            help="Коэффициент теплопередачи газ–жидкость. Часто 50–150 Вт/(м²·K) для гладких труб, зависит от газового сопротивления.",
        )

        v2_F_gl = st.number_input(
            "Поправка LMTD газо-жидкостного ТО",
            min_value=0.1,
            max_value=1.0,
            value=0.95,
            step=0.01,
            key="v2_F_gl",
        )

        v2_pump_dp = st.number_input(
            "Сопротивление жидкостного контура, кПа",
            min_value=0.0,
            value=150.0,
            step=10.0,
            key="v2_pump_dp",
            help="Суммарное сопротивление: ТО на печи, АВО, трубопроводы, арматура. Для рабочего проекта нужен гидравлический расчёт.",
        )

        v2_pump_eff = st.number_input(
            "КПД насоса",
            min_value=0.05,
            max_value=1.0,
            value=0.60,
            step=0.01,
            key="v2_pump_eff",
        )

        v2_pump_margin = st.number_input(
            "Запас мощности насоса",
            min_value=1.0,
            max_value=3.0,
            value=1.15,
            step=0.05,
            key="v2_pump_margin",
        )

    with v2c3:
        v2_U_avo = st.number_input(
            "U АВО, Вт/(м²·K)",
            min_value=1.0,
            max_value=2000.0,
            value=30.0,
            step=5.0,
            key="v2_U_avo",
            help="Коэффициент теплопередачи АВО. Для оребрённых аппаратов должен соответствовать выбранной площади поверхности.",
        )

        v2_F_avo = st.number_input(
            "Поправка LMTD АВО",
            min_value=0.1,
            max_value=1.0,
            value=0.90,
            step=0.01,
            key="v2_F_avo",
        )

        v2_air_dt = st.number_input(
            "Нагрев воздуха в АВО, ΔT °C",
            min_value=1.0,
            max_value=100.0,
            value=15.0,
            step=1.0,
            key="v2_air_dt",
            help="На сколько градусов нагревается воздух в АВО. Больше ΔT — меньше расход воздуха, но меньше температурный напор.",
        )

        v2_face_vel = st.number_input(
            "Скорость воздуха во фронте АВО, м/с",
            min_value=0.1,
            max_value=10.0,
            value=2.5,
            step=0.1,
            key="v2_face_vel",
            help="Ориентировочная допустимая скорость воздуха в живом сечении АВО.",
        )

        v2_avo_dp = st.number_input(
            "Давление вентилятора АВО, Па",
            min_value=0.0,
            value=250.0,
            step=50.0,
            key="v2_avo_dp",
            help="Сопротивление воздушного тракта АВО.",
        )

        v2_avo_eff = st.number_input(
            "КПД вентилятора АВО",
            min_value=0.05,
            max_value=1.0,
            value=0.60,
            step=0.01,
            key="v2_avo_eff",
        )

        v2_avo_margin = st.number_input(
            "Запас мощности вентилятора АВО",
            min_value=1.0,
            max_value=3.0,
            value=1.15,
            step=0.05,
            key="v2_avo_margin",
        )

    with st.expander("Конструкция газо-жидкостного ТО"):
        q1, q2, q3 = st.columns(3)

        with q1:
            v2_target_gas_v = st.number_input(
                "Целевая скорость газов в трубах, м/с",
                min_value=0.0,
                max_value=60.0,
                value=12.0,
                step=1.0,
                key="v2_target_gas_v",
            )

            v2_tube_od = st.number_input(
                "Наружный диаметр труб, мм",
                min_value=5.0,
                max_value=500.0,
                value=32.0,
                step=1.0,
                key="v2_tube_od",
            )

            v2_tube_wall = st.number_input(
                "Толщина стенки труб, мм",
                min_value=0.5,
                max_value=50.0,
                value=2.0,
                step=0.5,
                key="v2_tube_wall",
            )

        with q2:
            v2_tube_max_l = st.number_input(
                "Максимальная длина труб, м",
                min_value=0.3,
                max_value=20.0,
                value=3.0,
                step=0.1,
                key="v2_tube_max_l",
            )

            v2_tube_min_l = st.number_input(
                "Минимальная длина труб, м",
                min_value=0.1,
                max_value=20.0,
                value=0.5,
                step=0.1,
                key="v2_tube_min_l",
            )

            v2_pitch = st.number_input(
                "Шаг труб, t/d",
                min_value=1.05,
                max_value=3.0,
                value=1.30,
                step=0.05,
                key="v2_pitch",
            )

            v2_layout = st.number_input(
                "Коэффициент заполнения трубной доски",
                min_value=0.50,
                max_value=0.95,
                value=0.85,
                step=0.01,
                key="v2_layout",
            )

        with q3:
            v2_shell_th = st.number_input(
                "Толщина стенки корпуса, мм",
                min_value=1.0,
                max_value=100.0,
                value=4.0,
                step=1.0,
                key="v2_shell_th",
            )

            v2_tubesheet_th = st.number_input(
                "Толщина трубной доски, мм",
                min_value=5.0,
                max_value=300.0,
                value=20.0,
                step=1.0,
                key="v2_tubesheet_th",
            )

            v2_mass_factor = st.number_input(
                "Коэффициент добавочной массы",
                min_value=1.0,
                max_value=3.0,
                value=1.25,
                step=0.05,
                key="v2_mass_factor",
            )

            v2_steel_density = st.number_input(
                "Плотность стали, кг/м³",
                min_value=1000.0,
                max_value=10000.0,
                value=7850.0,
                step=50.0,
                key="v2_steel_density",
            )

    with st.expander("Конструкция АВО"):
        a1, a2, a3 = st.columns(3)

        with a1:
            v2_fin_area = st.number_input(
                "Удельная площадь оребрения, м²/м",
                min_value=1.0,
                max_value=200.0,
                value=20.0,
                step=1.0,
                key="v2_fin_area",
                help="Площадь теплообмена на один погонный метр оребрённой трубы.",
            )

            v2_liq_vel = st.number_input(
                "Целевая скорость жидкости в трубах АВО, м/с",
                min_value=0.0,
                max_value=10.0,
                value=1.5,
                step=0.1,
                key="v2_liq_vel",
                help="Для жидкостей часто 0.5–2.5 м/с.",
            )

            v2_avo_tube_od = st.number_input(
                "Наружный диаметр труб АВО, мм",
                min_value=5.0,
                max_value=200.0,
                value=25.0,
                step=1.0,
                key="v2_avo_tube_od",
            )

        with a2:
            v2_avo_tube_wall = st.number_input(
                "Толщина стенки труб АВО, мм",
                min_value=0.5,
                max_value=50.0,
                value=2.0,
                step=0.5,
                key="v2_avo_tube_wall",
            )

            v2_avo_min_l = st.number_input(
                "Минимальная длина труб АВО, м",
                min_value=0.1,
                max_value=20.0,
                value=0.5,
                step=0.1,
                key="v2_avo_min_l",
            )

            v2_avo_max_l = st.number_input(
                "Максимальная длина труб АВО, м",
                min_value=0.3,
                max_value=20.0,
                value=3.0,
                step=0.1,
                key="v2_avo_max_l",
            )

        with a3:
            v2_specific_vol = st.number_input(
                "Удельный объём АВО, м³/м²",
                min_value=0.0001,
                max_value=1.0,
                value=0.003,
                step=0.001,
                format="%.4f",
                key="v2_specific_vol",
                help="Ориентировочный объём пакета АВО на единицу площади теплообмена.",
            )

            v2_specific_mass = st.number_input(
                "Удельная масса АВО, кг/м²",
                min_value=0.1,
                max_value=500.0,
                value=12.0,
                step=1.0,
                key="v2_specific_mass",
                help="Ориентировочная масса АВО на единицу площади теплообмена.",
            )

    def build_var2_inputs() -> Variant2Inputs:
        return Variant2Inputs(
            t_gas_in_c=float(t_gas_in),
            gas_flow_nm3h=float(gas_flow),
            t_amb_c=float(t_amb_calc),
            leakage_pct=float(leak_pct),
            t_gas_out_c=float(t_gas_out_common),
            t_liq_in_c=float(v2_t_liq_in),
            t_liq_out_c=float(v2_t_liq_out),
            leakage_basis=leak_basis,
            fluid_type=v2_fluid,
            concentration_mode=v2_conc_mode,
            manual_concentration_pct=float(v2_manual_conc),
            design_min_temp_c=float(v2_design_min),
            freeze_safety_k=float(v2_safety),
            cp_gas_kjkgk=float(cp_gas),
            cp_air_kjkgk=float(cp_air),
            rho_gas_n_kgm3=float(rho_gas_n),
            rho_air_n_kgm3=float(rho_air_n),
            U_gas_liquid_Wm2K=float(v2_U_gl),
            lmtd_correction_gas_liquid=float(v2_F_gl),
            target_gas_velocity_ms=float(v2_target_gas_v),
            tube_od_mm=float(v2_tube_od),
            tube_wall_mm=float(v2_tube_wall),
            tube_max_length_m=float(v2_tube_max_l),
            tube_min_length_m=float(v2_tube_min_l),
            pitch_ratio=float(v2_pitch),
            layout_eff=float(v2_layout),
            shell_thickness_mm=float(v2_shell_th),
            tubesheet_thickness_mm=float(v2_tubesheet_th),
            mass_factor=float(v2_mass_factor),
            steel_density=float(v2_steel_density),
            pump_dp_kpa=float(v2_pump_dp),
            pump_eff=float(v2_pump_eff),
            pump_motor_margin=float(v2_pump_margin),
            U_avo_Wm2K=float(v2_U_avo),
            lmtd_correction_avo=float(v2_F_avo),
            avo_air_dt_c=float(v2_air_dt),
            avo_face_velocity_ms=float(v2_face_vel),
            avo_dp_pa=float(v2_avo_dp),
            avo_fan_eff=float(v2_avo_eff),
            avo_motor_margin=float(v2_avo_margin),
            fin_area_per_m=float(v2_fin_area),
            avo_specific_volume_m3_per_m2=float(v2_specific_vol),
            avo_specific_mass_kg_per_m2=float(v2_specific_mass),
            target_liquid_velocity_ms=float(v2_liq_vel),
            avo_tube_od_mm=float(v2_avo_tube_od),
            avo_tube_wall_mm=float(v2_avo_tube_wall),
            avo_min_tube_length_m=float(v2_avo_min_l),
            avo_max_tube_length_m=float(v2_avo_max_l),
        )

    if st.button("Рассчитать вариант 2", key="btn_calc_var2", type="primary"):
        st.session_state.res2 = None
        st.session_state.err2 = None

        try:
            inp2 = build_var2_inputs()
            st.session_state.res2 = calculate_variant2(inp2)
        except CalcErrorV2 as e:
            st.session_state.err2 = str(e)
        except Exception as e:
            st.session_state.err2 = str(e)

    if st.session_state.err2:
        st.error(f"Ошибка варианта 2: {st.session_state.err2}")

    if st.session_state.res2:
        render_variant2_result(st.session_state.res2)


# ------------------------------------------------------------------
# Вкладка 3: сравнение
# ------------------------------------------------------------------
with tab3:
    st.subheader("Сравнительный анализ двух вариантов")

    if st.button("Рассчитать оба варианта и сравнить", key="btn_compare", type="primary"):
        st.session_state.res1 = None
        st.session_state.res2 = None
        st.session_state.err1 = None
        st.session_state.err2 = None

        try:
            inp1 = build_var1_inputs()
            st.session_state.res1 = calculate_variant1(inp1)
        except Exception as e:
            st.session_state.err1 = str(e)

        try:
            inp2 = build_var2_inputs()
            st.session_state.res2 = calculate_variant2(inp2)
        except Exception as e:
            st.session_state.err2 = str(e)

    if st.session_state.err1:
        st.error(f"Ошибка варианта 1: {st.session_state.err1}")

    if st.session_state.err2:
        st.error(f"Ошибка варианта 2: {st.session_state.err2}")

    if st.session_state.res1 and st.session_state.res2:
        render_comparison(st.session_state.res1, st.session_state.res2)
    else:
        st.info(
            "Нажмите 'Рассчитать оба варианта и сравнить', либо сначала рассчитайте Вариант 1 и Вариант 2 в соответствующих вкладках."
        )
