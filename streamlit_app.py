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
    if 'av_rating_alt' in df.columns:
        df = df.sort_values(by="av_rating_alt", ascending=False)
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"Помилка завантаження: {e}")
    st.stop()

# ========================== ФІЛЬТРИ В САЙДБАРІ ==========================
st.sidebar.header("Filters")

# Позиції та Команди
positions = sorted(df['element_type'].unique())
selected_positions = st.sidebar.multiselect("Pos", options=positions, default=positions)

teams = sorted(df['team_short_name'].unique())
selected_teams = st.sidebar.multiselect("Team", options=teams, default=teams)

# Числові фільтри з дефолтними значеннями
# 1. Matches Played (Default: 5+)
m_min, m_max = int(df['matches_played'].min()), int(df['matches_played'].max())
f_matches = st.sidebar.slider("Min Matches", m_min, m_max, (5, m_max))

# 2. 60 Min % (Default: 37.0+)
min_60 = float(df['60_min'].min())
max_60 = float(df['60_min'].max())
f_60min = st.sidebar.slider("60 Min %", min_60, max_60, (37.0, max_60), 0.5)

# 3. Price
c_min, c_max = float(df['now_cost'].min()), float(df['now_cost'].max())
f_cost = st.sidebar.slider("Price", c_min, c_max, (c_min, c_max), 0.1)

# 4. Ownerships (Крок 0.1)
s_min, s_max = float(df['selected_by_percent'].min()), float(df['selected_by_percent'].max())
f_selected = st.sidebar.slider("Selected %", s_min, s_max, (s_min, s_max), 0.1)

o_min, o_max = float(df['top_100k'].min()), float(df['top_100k'].max())
f_top100k = st.sidebar.slider("Top 100k %", o_min, o_max, (o_min, o_max), 0.1)

# 5. Avg Mins (Крок 1)
am_min, am_max = float(df['avg_mins'].min()), float(df['avg_mins'].max())
f_avg_mins = st.sidebar.slider("Avg Mins", am_min, am_max, (am_min, am_max), 1.0)

# ========================== ЗАСТОСУВАННЯ ФІЛЬТРІВ ==========================
mask = (
    df['element_type'].isin(selected_positions) &
    df['team_short_name'].isin(selected_teams) &
    (df['matches_played'] >= f_matches[0]) & (df['matches_played'] <= f_matches[1]) &
    (df['60_min'] >= f_60min[0]) & (df['60_min'] <= f_60min[1]) &
    (df['now_cost'] >= f_cost[0]) & (df['now_cost'] <= f_cost[1]) &
    (df['selected_by_percent'] >= f_selected[0]) & (df['selected_by_percent'] <= f_selected[1]) &
    (df['top_100k'] >= f_top100k[0]) & (df['top_100k'] <= f_top100k[1]) &
    (df['avg_mins'] >= f_avg_mins[0]) & (df['avg_mins'] <= f_avg_mins[1])
)
filtered_df = df[mask]

# ========================== КОЛОНКИ ТА ВІДОБРАЖЕННЯ ==========================
# Список колонок для відображення (БЕЗ 'id')
display_columns = [
    "full_name", "Age", "element_type", "Play Pos", "team_short_name", "now_cost", 
    "Foot", "selected_by_percent", "top_10k", "top_100k", "min_played", 
    "matches_played", "matches_started", "avg_mins", "60_min", "goals_scored", 
    "assists", "av_rating", "av_rating_alt", "transfers_in_event", 
    "transfers_out_event", "news", "news_added"
]

st.subheader(f"Players: {len(filtered_df)}")

# Використовуємо максимально стислі назви та ширину
st.dataframe(
    filtered_df[display_columns],
    use_container_width=True,
    hide_index=True,
    height=800,
    column_config={
        "full_name": st.column_config.TextColumn("Player", width="medium", pinned=True),
        "Age": st.column_config.NumberColumn("Ag", width="small", format="%d"),
        "element_type": st.column_config.TextColumn("Pos", width="small"),
        "Play Pos": st.column_config.TextColumn("P.Pos", width="small"),
        "team_short_name": st.column_config.TextColumn("Tm", width="small"),
        "now_cost": st.column_config.NumberColumn("£", width="small", format="%.1f"),
        "Foot": st.column_config.TextColumn("Ft", width="small"),
        "selected_by_percent": st.column_config.NumberColumn("Sel", width="small", format="%.1f"),
        "top_10k": st.column_config.NumberColumn("10k", width="small", format="%.1f"),
        "top_100k": st.column_config.NumberColumn("100k", width="small", format="%.1f"),
        "min_played": st.column_config.NumberColumn("Min", width="small"),
        "matches_played": st.column_config.NumberColumn("MP", width="small"),
        "matches_started": st.column_config.NumberColumn("GS", width="small"),
        "avg_mins": st.column_config.NumberColumn("AvgM", width="small", format="%d"),
        "60_min": st.column_config.NumberColumn("60%", width="small", format="%.1f"),
        "goals_scored": st.column_config.NumberColumn("G", width="small"),
        "assists": st.column_config.NumberColumn("A", width="small"),
        "av_rating": st.column_config.NumberColumn("Rt", width="small", format="%.2f"),
        "av_rating_alt": st.column_config.NumberColumn("RtA", width="small", format="%.2f"),
        "transfers_in_event": st.column_config.NumberColumn("In", width="small"),
        "transfers_out_event": st.column_config.NumberColumn("Out", width="small"),
        "news": st.column_config.TextColumn("News", width="medium"),
        "news_added": st.column_config.TextColumn("Upd", width="small"),
    }
)