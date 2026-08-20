# 1. Импортируем библиотеки
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# 2. Настраиваем страницу
st.set_page_config(
    page_title="Анализ эффективности работы интернет-магазина", 
    layout="wide"
    )
st.title("Анализ эффективности работы интернет-магазина")

# 3. Загружаем данные с помощью функции @st.cache_data
def cache_data():
    df_orders = pd.read_csv("orders.csv")
    df_items = pd.read_csv("items.csv")
    df_users = pd.read_csv("users.csv")
    return df_orders, df_items, df_users

try:
    df_orders, df_items, df_users = cache_data()
    st.success("✅ Данные успешно загружены!")
except FileNotFoundError as e:
    st.error(f"❌ Не найден CSV-файл: {e}")
    st.stop()

# 4. Объединение таблиц
orders_users = df_orders.merge(df_users, on="user_id", how="left", validate="m:1")
df_clean = orders_users.merge(df_items, on="item_id", how="left", validate="m:1")

# 5. Очистка данных (типы, пропуски)
initial_rows = len(df_clean)

# Категориальные
cat_cols = ["user_name", "city", "user_segment", "item_name", "category", "supplier"]
for col in cat_cols:
    if col in df_clean.columns:
        df_clean[col] = df_clean[col].fillna("Unknown").astype("string")

# Числовые
num_cols = ["quantity", "price_per_unit", "base_price"]
for col in num_cols:
    if col in df_clean.columns:
        df_clean[col] = pd.to_numeric(df_clean[col], errors="coerce")
        df_clean = df_clean.dropna(subset=[col])

# Даты
date_cols = ["order_date", "registration_date"]
for col in date_cols:
    if col in df_clean.columns:
        df_clean[col] = pd.to_datetime(df_clean[col], errors="coerce")
        df_clean = df_clean.dropna(subset=[col])

# ID
id_cols = ["order_id", "user_id", "item_id"]
for col in id_cols:
    if col in df_clean.columns:
        df_clean[col] = df_clean[col].astype("string")

# 6. Создаём новые колонки "revenue" и "weekday" после очистки 

if "quantity" in df_clean.columns and "price_per_unit" in df_clean.columns:
    df_clean["revenue"] = df_clean["quantity"] * df_clean["price_per_unit"]
else:
    st.error("Не найдены колонки quantity или price_per_unit")
    st.stop()

# Создаём weekday на полном датасете
if "weekday" not in df_clean.columns:
    df_clean["weekday"] = df_clean["order_date"].dt.weekday

final_rows = len(df_clean)
rows_lost = initial_rows - final_rows

# 7. Выведем подзаголовок и фильтр по категории
st.subheader("📋 Сырые данные")
st.dataframe(df_clean.head())

with st.sidebar:
    st.header("Фильтры")
    selected_category = st.selectbox(
        "Выберите категорию:",
        options=df_clean["category"].unique()
    )

filtered_df = df_clean[df_clean["category"] == selected_category]

st.subheader(f"📋 Данные по категории: {selected_category}")
st.dataframe(filtered_df.head())

# 8. Метрики (по выбранной категории) 
st.subheader("Ключевые показатели")
orders_count = filtered_df["order_id"].nunique() # Общее количество заказов
total_revenue = filtered_df["revenue"].sum() # Общую выручку
unique_users = filtered_df["user_id"].nunique() # Количество уникальных пользователей
avg_check = total_revenue / orders_count if orders_count > 0 else 0 # Средний чек (общая выручка / общее количество заказов)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Заказы", f"{orders_count:.0f} шт")
col2.metric("Выручка", f"{total_revenue:,.0f} ₽")
col3.metric("Пользователи", f"{unique_users:.0f} чел")
col4.metric("Средний чек", f"{avg_check:.2f} ₽")

# 9. Создаем графики
st.subheader("📊 Визуализация")
col1, col2 = st.columns(2)

# График 1: Топ‑10 товаров по выручке
with col1:
    st.subheader("Топ‑10 товаров по выручке")
    top_items = (
        df_clean.groupby("item_name")["revenue"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
    )
    fig, ax = plt.subplots(figsize=(5, 3.5))
    top_items.plot(kind="barh", ax=ax, color="#4C72B0")
    ax.set_xlabel("Выручка, ₽")
    ax.set_ylabel("")
    ax.set_title("")
    ax.invert_yaxis()
    ax.grid(axis="x", linestyle="--", alpha=0.3)
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

# График 2: Выручка по категориям товаров (pie chart)
with col2:
    st.subheader("Доля категорий в общей выручке")
    revenue_by_category = df_clean.groupby("category")["revenue"].sum()
    
    if len(revenue_by_category) > 6:
        top_cat = revenue_by_category.nlargest(6)
        other_sum = revenue_by_category.sum() - top_cat.sum()
        revenue_by_category = top_cat.copy()
        revenue_by_category["Прочее"] = other_sum

    if not revenue_by_category.empty:
        fig, ax = plt.subplots(figsize=(4, 4))
        wedges, texts, autotexts = ax.pie(
            revenue_by_category,
            labels=revenue_by_category.index,
            autopct="%1.0f%%",
            startangle=90,
            colors=plt.cm.Set2.colors,
            textprops={"fontsize": 7}
        )
        for t in autotexts:
            t.set_color('white')
            t.set_fontsize(8)
        ax.set_title("")
        plt.tight_layout()
        st.pyplot(fig)
        plt.close(fig)
    else:
        st.write("Нет данных")

# График 3: Зависимость количества заказов от дня недели (столбчатая диаграмма)
st.subheader("Количество заказов по дням недели")
# Полный список дней: 0=Пн, ..., 6=Вс
all_days = list(range(7))
day_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

# Считаем заказы по дням только для выбранной категории
orders_by_weekday = filtered_df.groupby("weekday")["order_id"].count()

# Создаём Series со всеми днями, заполняя отсутствующие нулями
orders_all_days = pd.Series(0, index=all_days)
orders_all_days.update(orders_by_weekday)  # перезаписываем только те дни, где есть данные

# Привязываем названия дней к индексам
orders_all_days.index = day_names

fig, ax = plt.subplots(figsize=(6, 3.5))
orders_all_days.plot(kind="bar", ax=ax, color="#DD8452", rot=0)

ax.set_xlabel("День недели", fontsize=9)
ax.set_ylabel("Количество заказов", fontsize=9)
ax.set_title("")
ax.tick_params(axis="x", labelsize=9)
ax.grid(axis="y", linestyle="--", alpha=0.3)

plt.tight_layout()
st.pyplot(fig)
plt.close(fig)


# 10. Аналитические выводы
st.subheader("📊 Аналитические выводы и рекомендации")

revenue_by_category = df_clean.groupby("category")["revenue"].sum().sort_values(ascending=False)
top_category = revenue_by_category.idxmax()

orders_by_weekday = df_clean.groupby("weekday")["order_id"].count()
peak_day_num = orders_by_weekday.idxmax()
day_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
peak_day_name = day_names[peak_day_num]

top_item = df_clean.groupby("item_name")["revenue"].sum().idxmax()

st.markdown(
    f"""
    ### Ключевые факты
    - Категория **«{top_category}»** — основной драйвер выручки.  
    - Максимальная активность клиентов — в **{peak_day_name}**.  
    - Лидер продаж: **«{top_item}»**.

    ### Рекомендации
    - В **{peak_day_name}** стоит усилить персонал и контролировать запасы ключевых позиций.  
    - Для категории **«{top_category}»** можно рассмотреть промо‑акции или кросс‑продажи сопутствующих товаров.  
    - Стоит проанализировать менее популярные категории: возможно, часть ассортимента стоит оптимизировать.
    """
)