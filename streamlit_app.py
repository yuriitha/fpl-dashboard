import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(
    page_title="FPL Players",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========================== ЗАВАНТАЖЕННЯ ДАНИХ ==========================
@st.cache_data(ttl=600)
def load_data():
    return pd.read_parquet("/opt/sofascore-scraper/fpl_players.parquet")

df = load_data()

# ========================== ВСТАНОВЛЕННЯ ПОРЯДКУ КОЛОНОК ==========================
desired_order = [
    "id", 
    "full_name", 
    "Age", 
    "element_type", 
    "Play Pos",           # нова колонка
    "team_short_name", 
    "Foot",               # нова колонка
    "now_cost", 
    "M Price",            # нова колонка
    "points_per_game", 
    "selected_by_percent", 
    "top_10k", 
    "top_100k", 
    "transfers_in_event", 
    "transfers_out_event", 
    "news", 
    "news_added",
    "Contract"            # нова колонка в кінці
]

# Залишаємо тільки ті колонки, які реально є в df
desired_order = [col for col in desired_order if col in df.columns]
df = df[desired_order]

# ========================== ФІЛЬТРИ У Сайдбарі ==========================
st.sidebar.header("Filters")

positions = sorted(df['element_type'].unique())
selected_positions = st.sidebar.multiselect("Position", options=positions, default=positions)

teams = sorted(df['team_short_name'].unique())
selected_teams = st.sidebar.multiselect("Team", options=teams, default=teams)

min_cost = float(df['now_cost'].min())
max_cost = float(df['now_cost'].max())
cost_range = st.sidebar.slider("Price (£m)", min_value=min_cost, max_value=max_cost, value=(min_cost, max_cost), step=0.1)

search_name = st.sidebar.text_input("Search by name", "")

# ========================== ЗАСТОСУВАННЯ ФІЛЬТРІВ ==========================
filtered_df = df.copy()

if selected_positions:
    filtered_df = filtered_df[filtered_df['element_type'].isin(selected_positions)]

if selected_teams:
    filtered_df = filtered_df[filtered_df['team_short_name'].isin(selected_teams)]

if cost_range:
    filtered_df = filtered_df[
        (filtered_df['now_cost'] >= cost_range[0]) & 
        (filtered_df['now_cost'] <= cost_range[1])
    ]

if search_name:
    filtered_df = filtered_df[
        filtered_df['full_name'].str.contains(search_name, case=False, na=False)
    ]

# ========================== ВІДОБРАЖЕННЯ ТАБЛИЦІ ==========================
st.subheader(f"Знайдено гравців: {len(filtered_df)}")

st.dataframe(
    filtered_df,
    use_container_width=True,
    hide_index=True,
    height=720,
    column_config={
        "id": st.column_config.NumberColumn("ID", disabled=True, width=5),
        "full_name": st.column_config.TextColumn("Player", width="medium"),
        "Age": st.column_config.NumberColumn("Age", width=5),
        "element_type": st.column_config.TextColumn("Pos", width=5),
        "Play Pos": st.column_config.TextColumn("Play Pos", width=5),
        "team_short_name": st.column_config.TextColumn("Team", width=5),
        "Foot": st.column_config.TextColumn("Foot", width=5),
        "now_cost": st.column_config.NumberColumn("Price", format="%.1f", width=5),
        "M Price": st.column_config.NumberColumn("M Price", format="%.1f", width=5),
        "points_per_game": st.column_config.NumberColumn("Pts/Game", format="%.1f", width=5),
        "selected_by_percent": st.column_config.NumberColumn("Selected %", format="%.1f", width=5),
        "top_10k": st.column_config.NumberColumn("Top 10k %", format="%.1f", width=5),
        "top_100k": st.column_config.NumberColumn("Top 100k %", format="%.1f", width=5),
        "transfers_in_event": st.column_config.NumberColumn("In", width=5),
        "transfers_out_event": st.column_config.NumberColumn("Out", width=5),
        "news": st.column_config.TextColumn("News", width="auto"),
        "news_added": st.column_config.TextColumn("Updated", width=20),
        "Contract": st.column_config.TextColumn("Contract", width=5),
    }
)

st.caption(f"Останнє оновлення: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}")