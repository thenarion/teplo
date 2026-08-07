"""
Экспорт результатов теплового баланса в PDF.
Использует fpdf2 с поддержкой Unicode (кириллица).
"""

from fpdf import FPDF
from datetime import datetime
import os


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

    # =========================================================
    # ИСХОДНЫЕ ДАННЫЕ
    # =========================================================
    pdf.section_title("1. Исходные данные")

    input_data = [
        ["Подача влажного топлива", f"{inp.fuel_feed:.0f} кг/ч"],
        ["Влажность", f"{inp.moisture*100:.0f}%"],
        ["Низшая теплота сгорания (Q_net)", f"{inp.q_net_ar:.2f} МДж/кг"],
        ["Зольность на рабочую массу", f"{inp.ash_content*100:.0f}%"],
        ["Коэффициент избытка воздуха (α)", f"{inp.excess_air:.2f}"],
        ["Температура дымовых газов на выходе", f"{inp.flue_gas_temp:.0f}°C"],
        ["Температура наружного воздуха", f"{inp.ambient_temp:.0f}°C"],
        ["Мощность горелки (макс)", f"{inp.burner_power:.1f} МВт"],
        ["Длина барабана", f"{inp.drum_length:.1f} м"],
        ["Диаметр барабана", f"{inp.drum_diameter:.1f} м"],
        ["Время пребывания отхода", f"{inp.residence_time:.0f} мин"],
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

    # =========================================================
    # ТЕПЛОТА СГОРАНИЯ
    # =========================================================
    pdf.section_title("3. Теплота сгорания")

    heat_data = [
        ["Низшая теплота сгорания (Q_net)", f"{res.q_net_ar:.2f} МДж/кг"],
        ["Тепловыделение от топлива", f"{res.q_fuel:.3f} МВт"],
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
        ["Фактическое время пребывания", f"{inp.residence_time:.1f} мин"],
        ["Коэффициент запаса времени", f"{b.time_ratio:.2f}"],
        ["Полнота выгорания", f"{b.burnout_efficiency*100:.1f}%"],
        ["Удельная тепловая нагрузка", f"{b.heat_load:.0f} кВт/м³"],
    ]

    pdf.add_table(
        ["Параметр", "Значение"],
        burnout_data,
        col_widths=[100, 80]
    )

    # =========================================================
    # ВЫВОДЫ
    # =========================================================
    pdf.section_title("7. Выводы")

    conclusions = f"""
Процесс {'полностью автотермичный' if res.q_useful_no_burner > 0 else 'НЕ автотермичный'}.
Тепловыделение от топлива: {res.q_fuel:.3f} МВт.
Полезное тепло без горелки: {res.q_useful_no_burner:.3f} МВт.
Полезное тепло с горелкой: {res.q_useful_with_burner:.3f} МВт.
КПД установки (без горелки): {res.efficiency_no_burner*100:.1f}%.
КПД установки (с горелкой): {res.efficiency_with_burner*100:.1f}%.

Полнота выгорания: {b.burnout_efficiency*100:.1f}%.
Удельная тепловая нагрузка: {b.heat_load:.0f} кВт/м³ (лимит {inp.max_heat_load:.0f} кВт/м³).
Степень заполнения барабана: {b.fill_ratio*100:.1f}%.

Вывод: {'Отход успевает выгореть' if b.overall_ok else 'Отход НЕ успевает полностью выгореть'}.
"""
    pdf.add_text(conclusions.strip())

    raw = pdf.output(dest="S")
    return bytes(raw) if isinstance(raw, bytearray) else raw


def export_to_pdf_simple(res, summary_table: list, flue_gas_params: list) -> bytes:
    """
    Упрощённый экспорт в PDF (fallback если fpdf2 не установлен).
    Возвращает текстовый отчёт.
    """
    lines = []
    lines.append("=" * 60)
    lines.append("ТЕПЛОВОЙ БАЛАНС СЖИГАНИЯ ТОПЛИВА")
    lines.append("=" * 60)
    lines.append(f"Дата расчёта: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    lines.append("")

    inp = res.input
    lines.append("1. ИСХОДНЫЕ ДАННЫЕ")
    lines.append(f"  Подача топлива: {inp.fuel_feed:.0f} кг/ч")
    lines.append(f"  Влажность: {inp.moisture*100:.0f}%")
    lines.append(f"  Q_gross: {inp.q_net_ar:.1f} МДж/кг")
    lines.append(f"  Зольность: {inp.ash_content*100:.0f}%")
    lines.append(f"  Избыток воздуха (α): {inp.excess_air:.2f}")
    lines.append(f"  T газов на выходе: {inp.flue_gas_temp:.0f}°C")
    lines.append(f"  T наружного воздуха: {inp.ambient_temp:.0f}°C")
    lines.append("")

    lines.append("2. МАССОВЫЙ БАЛАНС")
    lines.append(f"  Вода: {res.water_mass:.0f} кг/ч")
    lines.append(f"  Сухое вещество: {res.dry_mass:.0f} кг/ч")
    lines.append(f"  Зола: {res.ash_mass:.0f} кг/ч")
    lines.append(f"  Горючая масса: {res.combustible_mass:.0f} кг/ч")
    lines.append("")

    lines.append("3. ТЕПЛОТА СГОРАНИЯ")
    lines.append(f"  Q_net: {res.q_net_ar:.2f} МДж/кг")
    lines.append("")

    lines.append("4. ТЕПЛОВОЙ ПРИХОД")
    lines.append(f"  Тепло от топлива: {res.q_fuel:.2f} МВт")
    lines.append(f"  Тепло от горелки: {inp.burner_power:.2f} МВт")
    lines.append(f"  Итого: {res.q_input_with_burner:.2f} МВт")
    lines.append("")

    lines.append("5. РАСХОД ВОЗДУХА")
    lines.append(f"  Объём воздуха: {res.v_air_actual:.0f} Нм³/ч")
    lines.append(f"  Масса воздуха: {res.m_air:.0f} кг/ч")
    lines.append(f"  Объём газов: {res.v_flue:.0f} Нм³/ч")
    lines.append("")

    lines.append("6. ТЕПЛОВОЙ БАЛАНС")
    for row in summary_table:
        lines.append(f"  {row['Статья']:40s} {row['МВт']:>10s} {row['%']:>10s}")
    lines.append("")

    lines.append("7. ВЫВОДЫ")
    lines.append(f"  Полезное тепло (без горелки): {res.q_useful_no_burner:.2f} МВт")
    lines.append(f"  Полезное тепло (с горелкой): {res.q_useful_with_burner:.2f} МВт")
    lines.append(f"  КПД (без горелки): {res.efficiency_no_burner*100:.1f}%")
    lines.append(f"  КПД (с горелкой): {res.efficiency_with_burner*100:.1f}%")

    return "\n".join(lines).encode("utf-8")