import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(
    page_title="FPL Players Stats",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========================== ЗАВАНТАЖЕННЯ ДАНИХ ==========================
@st.cache_data(ttl=300)
def load_data():
    url = "http://194.99.22.193:8000/fpl_players"
    df = pd.read_parquet(url)
    
    # Сортування за замовчуванням (як ви просили)
    if 'av_rating_alt' in df.columns:
        df = df.sort_values(by="av_rating_alt", ascending=False)
    
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"Помилка завантаження даних: {e}")
    st.stop()

# ========================== ПОРЯДОК ТА НАЙМЕНУВАННЯ КОЛОНОК ==========================
# Словник: ключ - назва в parquet, значення - назва в таблиці (UI)
columns_to_display = {
    "id": "ID",
    "full_name": "Player",
    "Age": "Age",
    "element_type": "Pos",
    "Play Pos": "Play Pos",
    "team_short_name": "Team",
    "now_cost": "Price",
    "Foot": "Foot",
    "selected_by_percent": "Selected",
    "top_10k": "Top 10K",
    "top_100k": "Top 100k %",
    "min_played": "Mins",
    "matches_played": "Matches",
    "matches_started": "Starts",
    "avg_mins": "Avg Mins",
    "60_min": "60 Min %",
    "goals_scored": "Goals",
    "assists": "Assists",
    "av_rating": "Avg Rating",
    "av_rating_alt": "Avg Rating Alt",
    "transfers_in_event": "In",
    "transfers_out_event": "Out",
    "news": "News",
    "news_added": "Updated"
}

# Відфільтровуємо лише ті колонки, які існують в df та вказані в списку
existing_cols = [col for col in columns_to_display.keys() if col in df.columns]
display_df = df[existing_cols].copy()

# ========================== ФІЛЬТРИ В САЙДБАРІ ==========================
st.sidebar.header("Filters")

# Фільтр по позиціях
positions = sorted(display_df['element_type'].unique()) if 'element_type' in display_df.columns else []
selected_positions = st.sidebar.multiselect("Position", options=positions, default=positions)

# Фільтр по командах
teams = sorted(display_df['team_short_name'].unique()) if 'team_short_name' in display_df.columns else []
selected_teams = st.sidebar.multiselect("Team", options=teams, default=teams)

# Фільтр по ціні
min_c, max_c = float(display_df['now_cost'].min()), float(display_df['now_cost'].max())
cost_range = st.sidebar.slider("Price (£m)", min_c, max_c, (min_c, max_c), 0.1)

# Фільтр по зіграних матчах
min_m, max_m = int(display_df['matches_played'].min()), int(display_df['matches_played'].max())
matches_range = st.sidebar.slider("Matches Played", min_m, max_m, (0, max_m))

# ========================== ЗАСТОСУВАННЯ ФІЛЬТРІВ ==========================
mask = (
    display_df['element_type'].isin(selected_positions) &
    display_df['team_short_name'].isin(selected_teams) &
    (display_df['now_cost'] >= cost_range[0]) & (display_df['now_cost'] <= cost_range[1]) &
    (display_df['matches_played'] >= matches_range[0]) & (display_df['matches_played'] <= matches_range[1])
)
filtered_df = display_df[mask]

# ========================== ВІДОБРАЖЕННЯ ТАБЛИЦІ ==========================
st.subheader(f"Гравців знайдено: {len(filtered_df)}")

# Налаштування ширини та формату комірок (column_config)
# width=None або маленьке число дозволяє Streamlit стиснути колонку під контент
st.dataframe(
    filtered_df,
    use_container_width=True,
    hide_index=True,
    height=800,
    column_config={
        "id": st.column_config.NumberColumn("ID", width="small"),
        "full_name": st.column_config.TextColumn("Player", width="medium", pinned=True),
        "Age": st.column_config.NumberColumn("Age", width="small", format="%d"),
        "element_type": st.column_config.TextColumn("Pos", width="small"),
        "Play Pos": st.column_config.TextColumn("Play Pos", width="small"),
        "team_short_name": st.column_config.TextColumn("Team", width="small"),
        "now_cost": st.column_config.NumberColumn("Price", width="small", format="%.1f"),
        "Foot": st.column_config.TextColumn("Foot", width="small"),
        "selected_by_percent": st.column_config.NumberColumn("Selected", width="small", format="%.1f%%"),
        "top_10k": st.column_config.NumberColumn("Top 10K", width="small", format="%.1f%%"),
        "top_100k": st.column_config.NumberColumn("Top 100k %", width="small", format="%.1f%%"),
        "min_played": st.column_config.NumberColumn("Mins", width="small"),
        "matches_played": st.column_config.NumberColumn("Matches", width="small"),
        "matches_started": st.column_config.NumberColumn("Starts", width="small"),
        "avg_mins": st.column_config.NumberColumn("Avg Mins", width="small", format="%.0f"),
        "60_min": st.column_config.NumberColumn("60 Min %", width="small", format="%.1f"),
        "goals_scored": st.column_config.NumberColumn("Goals", width="small"),
        "assists": st.column_config.NumberColumn("Assists", width="small"),
        "av_rating": st.column_config.NumberColumn("Avg Rating", width="small", format="%.2f"),
        "av_rating_alt": st.column_config.NumberColumn("Avg Rating Alt", width="small", format="%.2f"),
        "transfers_in_event": st.column_config.NumberColumn("In", width="small"),
        "transfers_out_event": st.column_config.NumberColumn("Out", width="small"),
        "news": st.column_config.TextColumn("News", width="large"),
        "news_added": st.column_config.TextColumn("Updated", width="medium"),
    }
)

st.caption(f"Last sync: {datetime.now().strftime('%Y-%m-%d %H:%M')}")