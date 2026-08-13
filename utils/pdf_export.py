"""
Экспорт результатов теплового баланса в PDF.
Использует fpdf2 с поддержкой Unicode (кириллица).
"""

from fpdf import FPDF
from datetime import datetime
import os
import io


def _make_charts(res) -> dict:
    """
    Генерирует plotly-графики и возвращает PNG-байты.
    Возвращает dict с ключами: mass, heat, stages (bytes или None).
    """
    try:
        import plotly.graph_objects as go
        import plotly.express as px
        import pandas as pd
    except ImportError:
        return {"mass": None, "heat": None, "stages": None}

    charts = {"mass": None, "heat": None, "stages": None}
    inp = res.input
    b = res.burnout

    # 1. Круговая диаграмма состава топлива
    try:
        mass_df = pd.DataFrame({
            "Компонент": ["Вода", "Зола", "Горючая масса"],
            "Масса, кг/ч": [res.water_mass, res.ash_mass, res.combustible_mass],
        })
        fig = px.pie(mass_df, values="Масса, кг/ч", names="Компонент",
                     title="Состав топлива", hole=0.3,
                     color="Компонент",
                     color_discrete_map={"Вода": "#3498db", "Зола": "#95a5a6", "Горючая масса": "#e74c3c"})
        fig.update_layout(width=600, height=400, font=dict(size=12),
                         template="plotly_white")
        charts["mass"] = fig.to_image(format="png", engine="kaleido")
    except Exception:
        pass

    # 2. Столбчатая диаграмма теплового баланса
    try:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=["Приход"], y=[res.q_fuel_actual],
                             name="Тепло от топлива", marker_color="green"))
        fig.add_trace(go.Bar(x=["Приход"], y=[inp.burner_power],
                             name="Тепло от горелки", marker_color="lightgreen"))
        fig.add_trace(go.Bar(x=["Расход"], y=[res.q_flue_gas],
                             name="Уходящие газы", marker_color="red"))
        fig.add_trace(go.Bar(x=["Расход"], y=[res.q_wall],
                             name="Потери через футеровку", marker_color="orange"))
        fig.add_trace(go.Bar(x=["Расход"], y=[res.q_ash],
                             name="Потери с золой", marker_color="yellow"))
        fig.add_trace(go.Bar(x=["Расход"], y=[res.q_useful_with_burner],
                             name="Полезное тепло", marker_color="blue"))
        fig.update_layout(title="Тепловой баланс, МВт", barmode="stack",
                          yaxis_title="МВт", width=700, height=400, font=dict(size=12))
        charts["heat"] = fig.to_image(format="png", engine="kaleido")
    except Exception:
        pass

    # 3. Диаграмма стадий выгорания
    if b:
        try:
            stages_df = pd.DataFrame({
                "Стадия": ["Сушка", "Нагрев", "Горение", "Дожигание"],
                "Время, мин": [b.t_drying, b.t_heating, b.t_combustion, b.t_burnout],
            })
            fig = px.bar(stages_df, x="Стадия", y="Время, мин",
                         title="Время по стадиям выгорания", color="Стадия",
                         color_discrete_sequence=["#FF6B6B", "#FFA500", "#4ECDC4", "#45B7D1"])
            fig.add_hline(y=b.residence_time, line_dash="dash", line_color="red",
                          annotation_text=f"Факт. время: {b.residence_time:.0f} мин")
            fig.add_hline(y=b.t_required, line_dash="dot", line_color="orange",
                          annotation_text=f"Необходимое: {b.t_required:.0f} мин")
            fig.update_layout(width=700, height=400, font=dict(size=12))
            charts["stages"] = fig.to_image(format="png", engine="kaleido")
        except Exception:
            pass

    return charts


def get_font_path() -> str:
    """Находит путь к шрифту с поддержкой кириллицы."""
    # Список возможных путей к шрифтам
    font_candidates = [
        # Локальная папка проекта
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "fonts", "DejaVuSans.ttf"),
        # Windows
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/times.ttf",
        # Linux
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        # macOS
        "/System/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]

    for path in font_candidates:
        if os.path.exists(path):
            return path

    # Если шрифт не найден, возвращаем None
    return None


class ThermalBalancePDF(FPDF):
    """PDF-документ для теплового баланса."""

    def __init__(self):
        super().__init__()
        self.font_path = get_font_path()
        self.font_name = "DejaVu"

        if self.font_path:
            self.add_font(self.font_name, "", self.font_path, uni=True)
            self.add_font(self.font_name, "B", self.font_path, uni=True)
        else:
            self.font_name = "Helvetica"

    def header(self):
        """Заголовок страницы."""
        self.set_font(self.font_name, "B", 14)
        self.cell(0, 10, "Тепловой баланс сжигания топлива", ln=True, align="C")
        self.set_font(self.font_name, "", 9)
        self.cell(0, 5, f"Дата расчёта: {datetime.now().strftime('%d.%m.%Y %H:%M')}", ln=True, align="C")
        self.ln(5)

    def footer(self):
        """Подвал страницы."""
        self.set_y(-15)
        self.set_font(self.font_name, "", 8)
        self.cell(0, 10, f"Страница {self.page_no()}/{{nb}}", align="C")

    def section_title(self, title: str):
        """Заголовок раздела."""
        self.set_font(self.font_name, "B", 12)
        self.cell(0, 8, title, ln=True)
        self.ln(2)

    def add_table(self, headers: list, data: list, col_widths: list = None):
        """Добавляет таблицу."""
        if col_widths is None:
            col_widths = [self.w / (len(headers) + 1)] * len(headers)

        # Заголовки
        self.set_font(self.font_name, "B", 9)
        for i, header in enumerate(headers):
            self.cell(col_widths[i], 7, str(header), border=1, align="C")
        self.ln()

        # Данные
        self.set_font(self.font_name, "", 9)
        for row in data:
            for i, cell in enumerate(row):
                self.cell(col_widths[i], 6, str(cell), border=1)
            self.ln()

        self.ln(3)

    def add_text(self, text: str, size: int = 10):
        """Добавляет текст."""
        self.set_font(self.font_name, "", size)
        self.multi_cell(0, 5, text)
        self.ln(2)

    def add_image_bytes(self, img_bytes: bytes, w: int = 170):
        """Добавляет PNG-изображение из байтов."""
        self.image(io.BytesIO(img_bytes), w=w)
        self.ln(5)


def export_to_pdf(res, summary_table: list, flue_gas_params: list, filename: str = "thermal_balance.pdf") -> bytes:
    """
    Экспортирует результаты теплового баланса в PDF.
    """
    pdf = ThermalBalancePDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    inp = res.input
    b = res.burnout

    # Генерируем графики
    charts = _make_charts(res)

    # =========================================================
    # ИСХОДНЫЕ ДАННЫЕ
    # =========================================================
    pdf.section_title("1. Исходные данные")

    input_data = [
        ["Подача влажного топлива", f"{inp.fuel_feed:.0f} кг/ч"],
        ["Влажность", f"{inp.moisture*100:.0f}%"],
        ["Низшая теплота сгорания (Q_net)", f"{inp.q_net_ar:.2f} МДж/кг"],
        ["База теплоты сгорания", {
            "as_received": "Рабочая масса (с водой и золой)",
            "dry": "Сухая масса (без воды)",
            "daf": "Горючая масса (без воды и золы)",
        }.get(inp.q_basis, inp.q_basis)],
        ["Зольность на рабочую массу", f"{inp.ash_content*100:.0f}%"],
        ["Коэффициент избытка воздуха (α)", f"{inp.excess_air:.2f}"],
        ["Температура дымовых газов на выходе", f"{inp.flue_gas_temp:.0f}°C"],
        ["Температура наружного воздуха", f"{inp.ambient_temp:.0f}°C"],
        ["Мощность горелки (макс)", f"{inp.burner_power:.1f} МВт"],
        ["Длина барабана", f"{inp.drum_length:.1f} м"],
        ["Диаметр барабана", f"{inp.drum_diameter:.1f} м"],
        ["Время пребывания отхода", f"{b.residence_time:.0f} мин"],
        ["Насыпная плотность отхода", f"{inp.bulk_density:.0f} кг/м³"],
    ]

    pdf.add_table(
        ["Параметр", "Значение"],
        input_data,
        col_widths=[100, 80]
    )

    # =========================================================
    # МАССОВЫЙ БАЛАНС
    # =========================================================
    pdf.section_title("2. Массовый баланс")

    mass_data = [
        ["Влажный помёт (всего)", f"{res.fuel_feed:.0f} кг/ч", "100%"],
        ["Вода", f"{res.water_mass:.0f} кг/ч", f"{res.water_mass/res.fuel_feed*100:.0f}%"],
        ["Сухое вещество", f"{res.dry_mass:.0f} кг/ч", f"{res.dry_mass/res.fuel_feed*100:.0f}%"],
        ["Зола", f"{res.ash_mass:.0f} кг/ч", f"{res.ash_mass/res.fuel_feed*100:.0f}%"],
        ["Горючая масса", f"{res.combustible_mass:.0f} кг/ч", f"{res.combustible_mass/res.fuel_feed*100:.0f}%"],
    ]

    pdf.add_table(
        ["Компонент", "Масса", "Доля"],
        mass_data,
        col_widths=[70, 50, 40]
    )

    if charts["mass"]:
        pdf.add_image_bytes(charts["mass"], w=120)

    # =========================================================
    # ТЕПЛОТА СГОРАНИЯ
    # =========================================================
    pdf.section_title("3. Теплота сгорания")

    heat_data = [
        ["Низшая теплота сгорания (Q_net)", f"{res.q_net_ar:.2f} МДж/кг"],
        ["Тепловыделение от топлива", f"{res.q_fuel_actual:.3f} МВт"],
    ]

    pdf.add_table(
        ["Параметр", "Значение"],
        heat_data,
        col_widths=[100, 80]
    )

    # =========================================================
    # РАСХОД ВОЗДУХА И ДЫМОВЫХ ГАЗОВ
    # =========================================================
    pdf.section_title("4. Расход воздуха и дымовых газов")

    air_data = [
        ["Теоретический объём воздуха (на кг)", f"{res.v_air_theoretical_per_kg:.2f} Нм³/кг"],
        ["Фактический объём воздуха (α={:.2f})".format(inp.excess_air), f"{res.v_air_actual:.0f} Нм³/ч"],
        ["Масса воздуха", f"{res.m_air:.0f} кг/ч"],
        ["Объём дымовых газов (н.у.)", f"{res.v_flue:.0f} Нм³/ч"],
        ["Масса дымовых газов", f"{res.m_flue:.0f} кг/ч"],
    ]

    pdf.add_table(
        ["Параметр", "Значение"],
        air_data,
        col_widths=[100, 80]
    )

    # =========================================================
    # СВОДНАЯ ТАБЛИЦА ТЕПЛОВОГО БАЛАНСА
    # =========================================================
    pdf.section_title("5. Сводная таблица теплового баланса")

    balance_data = [[row["Статья"], row["МВт"], row["%"]] for row in summary_table]

    pdf.add_table(
        ["Статья", "МВт", "%"],
        balance_data,
        col_widths=[90, 40, 40]
    )

    if charts["heat"]:
        pdf.add_image_bytes(charts["heat"], w=150)

    # =========================================================
    # ПОЛНОТА ВЫГОРАНИЯ
    # =========================================================
    pdf.section_title("6. Полнота выгорания")

    burnout_data = [
        ["Объём барабана", f"{b.drum_volume:.2f} м³"],
        ["Масса отхода в барабане", f"{b.mass_in_drum:.0f} кг"],
        ["Степень заполнения", f"{b.fill_ratio*100:.1f}%"],
        ["Время сушки", f"{b.t_drying:.1f} мин"],
        ["Время нагрева", f"{b.t_heating:.1f} мин"],
        ["Время горения", f"{b.t_combustion:.1f} мин"],
        ["Время дожигания", f"{b.t_burnout:.1f} мин"],
        ["Необходимое время выгорания", f"{b.t_required:.1f} мин"],
        ["Фактическое время пребывания", f"{b.residence_time:.1f} мин"],
        ["Коэффициент запаса времени", f"{b.time_ratio:.2f}"],
        ["Полнота выгорания", f"{b.burnout_efficiency*100:.1f}%"],
        ["Удельная тепловая нагрузка", f"{b.heat_load:.0f} кВт/м³"],
    ]

    pdf.add_table(
        ["Параметр", "Значение"],
        burnout_data,
        col_widths=[100, 80]
    )

    if charts["stages"]:
        pdf.add_image_bytes(charts["stages"], w=150)

    # =========================================================
    # ВЫВОДЫ
    # =========================================================
    pdf.section_title("7. Выводы")

    conclusions = f"""
Автотермичность: {'Да' if res.q_useful_no_burner > 0 else 'Нет'}
Тепловыделение от топлива: {res.q_fuel_actual:.3f} МВт
Полезное тепло без горелки: {res.q_useful_no_burner:.3f} МВт
КПД установки: {res.efficiency_with_burner*100:.1f}%

Время пребывания: {b.residence_time:.1f} мин (необходимо {b.t_required:.1f} мин)
Запас времени: ×{b.time_ratio:.2f}
Время пребывания достаточное: {'Да' if b.time_ok else 'Нет'}

Степень заполнения: {b.fill_ratio*100:.1f}% (допустимая {inp.max_fill_ratio*100:.0f}%)
Степень заполнения в норме: {'Да' if b.fill_ratio_ok else 'Нет'}

Тепловая нагрузка: {b.heat_load:.0f} кВт/м³ (допустимая {inp.max_heat_load:.0f} кВт/м³)
Тепловая нагрузка в норме: {'Да' if b.heat_load_ok else 'Нет'}

Полнота выгорания: {b.burnout_efficiency*100:.1f}%
Оценка: {b.burnout_status_ru}
"""
    pdf.add_text(conclusions.strip())
    
    # Общий вывод
    if b.overall_ok:
        pdf.add_text("ОБЩИЙ ВЫВОД: Отход успевает полностью выгореть. Установка работает в штатном режиме.")
    else:
        reasons = []
        if not b.time_ok:
            reasons.append("недостаточное время пребывания")
        if not b.fill_ratio_ok:
            reasons.append("превышена степень заполнения")
        if not b.heat_load_ok:
            reasons.append("превышена тепловая нагрузка")
        if b.burnout_efficiency < 0.90:
            reasons.append(f"полнота выгорания ниже 90% (фактически {b.burnout_efficiency*100:.1f}%)")
        pdf.add_text("ОБЩИЙ ВЫВОД: Отход НЕ успевает полностью выгореть.")
        pdf.add_text(f"Причины: {', '.join(reasons)}.")

    raw = pdf.output(dest="S")
    return bytes(raw) if isinstance(raw, bytearray) else raw



def export_to_pdf_simple(res, summary_table: list, flue_gas_params: list) -> bytes:
    """
    Упрощённый экспорт в текстовый отчёт.
    """
    lines = []
    lines.append("=" * 60)
    lines.append("ТЕПЛОВОЙ БАЛАНС СЖИГАНИЯ ТОПЛИВА")
    lines.append("=" * 60)
    lines.append(f"Дата расчёта: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    lines.append("")

    inp = res.input
    b = res.burnout

    lines.append("1. ИСХОДНЫЕ ДАННЫЕ")
    lines.append(f"  Подача топлива: {inp.fuel_feed:.0f} кг/ч")
    lines.append(f"  Влажность: {inp.moisture*100:.0f}%")
    lines.append(f"  Q_net: {inp.q_net_ar:.2f} МДж/кг")
    lines.append(f"  Зольность: {inp.ash_content*100:.0f}%")
    lines.append(f"  Избыток воздуха (α): {inp.excess_air:.2f}")
    lines.append(f"  T наружного воздуха: {inp.ambient_temp:.0f}°C")
    
    q_basis_names = {
        "as_received": "Рабочая масса (с водой и золой)",
        "dry": "Сухая масса (без воды)",
        "daf": "Горючая масса (без воды и золы)",
    }
    lines.append(f"  База теплоты сгорания: {q_basis_names.get(inp.q_basis, inp.q_basis)}")
    
    lines.append(f"  Длина барабана: {inp.drum_length:.1f} м")
    lines.append(f"  Диаметр барабана: {inp.drum_diameter:.1f} м")
    lines.append(f"  Угол наклона: {inp.drum_angle:.1f}°")
    lines.append(f"  Скорость вращения: {inp.drum_rpm:.1f} об/мин")
    lines.append(f"  Коэффициент материала: {inp.material_coeff:.2f}")
    lines.append("")

    lines.append("2. ВРЕМЯ ПРЕБЫВАНИЯ И ПОЛНОТА ВЫГОРАНИЯ")
    lines.append(f"  Скорость движения материала: {b.material_velocity:.3f} м/мин")
    lines.append(f"  Время пребывания: {b.residence_time:.1f} мин")
    lines.append(f"  Степень заполнения: {b.fill_ratio*100:.1f}%")
    lines.append(f"  Необходимое время выгорания: {b.t_required:.1f} мин")
    lines.append(f"  Коэффициент запаса времени: {b.time_ratio:.2f}")
    lines.append(f"  Коэффициент диаметра: {b.k_diameter:.3f}")
    lines.append(f"  Полнота выгорания: {b.burnout_efficiency*100:.1f}%")
    lines.append(f"  Удельная тепловая нагрузка: {b.heat_load:.0f} кВт/м³")
    lines.append("")

    lines.append("3. ТЕПЛОВОЙ БАЛАНС")
    lines.append(f"  Тепловыделение номинальное: {res.q_fuel_nominal:.3f} МВт")
    lines.append(f"  Тепловыделение фактическое: {res.q_fuel_actual:.3f} МВт")
    lines.append(f"  Температура на выходе (расчётная): {inp.flue_gas_temp:.0f}°C")
    lines.append("")

    for row in summary_table:
        lines.append(f"  {row['Статья']:40s} {row['МВт']:>12s} {row['%']:>10s}")
    lines.append("")

    lines.append("4. ВЫВОДЫ")
    lines.append(f"  Автотермичность: {'Да' if res.q_useful_no_burner > 0 else 'Нет'}")
    lines.append("")
    
    lines.append("  4.1. Время пребывания:")
    lines.append(f"    Фактическое: {b.residence_time:.1f} мин")
    lines.append(f"    Необходимое: {b.t_required:.1f} мин")
    lines.append(f"    Запас: ×{b.time_ratio:.2f}")
    lines.append(f"    Достаточное: {'Да' if b.time_ok else 'Нет'}")
    lines.append("")
    
    lines.append("  4.2. Степень заполнения:")
    lines.append(f"    Фактическая: {b.fill_ratio*100:.1f}%")
    lines.append(f"    Допустимая: {inp.max_fill_ratio*100:.0f}%")
    lines.append(f"    В норме: {'Да' if b.fill_ratio_ok else 'Нет'}")
    lines.append("")
    
    lines.append("  4.3. Тепловая нагрузка:")
    lines.append(f"    Фактическая: {b.heat_load:.0f} кВт/м³")
    lines.append(f"    Допустимая: {inp.max_heat_load:.0f} кВт/м³")
    lines.append(f"    В норме: {'Да' if b.heat_load_ok else 'Нет'}")
    lines.append("")
    
    lines.append("  4.4. Полнота выгорания:")
    lines.append(f"    Значение: {b.burnout_efficiency*100:.1f}%")
    lines.append(f"    Оценка: {b.burnout_status_ru}")
    lines.append("")
    
    lines.append("  4.5. Общий вывод:")
    if b.overall_ok:
        lines.append("    Отход успевает полностью выгореть.")
        lines.append("    Установка работает в штатном режиме.")
    else:
        reasons = []
        if not b.time_ok:
            reasons.append("недостаточное время пребывания")
        if not b.fill_ratio_ok:
            reasons.append("превышена степень заполнения")
        if not b.heat_load_ok:
            reasons.append("превышена тепловая нагрузка")
        if b.burnout_efficiency < 0.90:
            reasons.append(f"полнота выгорания ниже 90%")
        lines.append("    Отход НЕ успевает полностью выгореть.")
        lines.append(f"    Причины: {', '.join(reasons)}")

    return "\n".join(lines).encode("utf-8")


# Упрощённый экспорт в PDF (fallback если fpdf2 не установлен).
# Возвращает текстовый отчёт.