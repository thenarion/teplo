"""
Расчёт ТДУ — термодеструкционной установки.
Навигация через st.navigation() — sidebar показывает только страницы текущего раздела.
"""
import streamlit as st

st.set_page_config(
    page_title="Расчёт ТДУ",
    page_icon="🔥",
    layout="wide",
)

# --- Определяем страницы ---
def menu_page():
    st.title("Расчёт ТДУ")
    st.markdown("Инженерный расчётный инструмент для термодеструкционной установки барабанного типа.")
    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.subheader("Расчёт теплообменника")
            st.markdown("""
            - Исходные данные и подсосы воздуха
            - Тепловая нагрузка и LMTD
            - Газовоздушное / жидкостное охлаждение
            - Габариты и экспорт отчёта
            """)
            if st.button("Перейти →", use_container_width=True, key="btn_hx"):
                st.session_state["section"] = "hx"
                st.rerun()

    with col2:
        with st.container(border=True):
            st.subheader("Тепловой баланс сжигания")
            st.markdown("""
            - Массовый баланс топлива
            - Теплота сгорания и КПД
            - Расход воздуха и дымовых газов
            - Экспорт в PDF
            """)
            if st.button("Перейти →", use_container_width=True, key="btn_tb"):
                st.session_state["section"] = "tb"
                st.rerun()


# --- Страницы теплообменника ---
hx_pages = [
    st.Page("views/1_Исходные_данные.py", title="Исходные данные", icon="1️⃣"),
    st.Page("views/2_Подсосы_воздуха.py", title="Подсосы воздуха", icon="2️⃣"),
    st.Page("views/3_Тепловой_расчёт.py", title="Тепловой расчёт", icon="3️⃣"),
    st.Page("views/4_Газовоздушное_охлаждение.py", title="Газовоздушное охлаждение", icon="4️⃣"),
    st.Page("views/5_Жидкостное_охлаждение.py", title="Жидкостное охлаждение", icon="5️⃣"),
    st.Page("views/6_Габариты.py", title="Габариты", icon="6️⃣"),
    st.Page("views/7_Отчёт.py", title="Отчёт", icon="7️⃣"),
]

# --- Страницы теплового баланса ---
tb_pages = [
    st.Page("views/8_Тепловой_баланс.py", title="Тепловой баланс", icon="📊"),
]

# --- Кнопка «Назад» добавляется во все страницы через sidebar ---
# (уже есть в render_sidebar() и в thermal_balance)

# --- Навигация ---
section = st.session_state.get("section", "menu")

if section == "hx":
    # Добавляем кнопку «← Меню» первой
    menu_btn = st.Page(menu_page, title="← Меню", icon="🏠", url_path="menu")
    pages = [menu_btn] + hx_pages
elif section == "tb":
    menu_btn = st.Page(menu_page, title="← Меню", icon="🏠", url_path="menu")
    pages = [menu_btn] + tb_pages
else:
    pages = [st.Page(menu_page, title="Меню", url_path="menu")]

nav = st.navigation(pages, position="sidebar")
nav.run()
