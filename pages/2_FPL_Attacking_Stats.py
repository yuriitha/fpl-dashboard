import streamlit as st
import pandas as pd
import numpy as np

# Налаштування сторінки
st.set_page_config(
    page_title="FPL Attacking Stats",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS для відцентрування заголовків та даних
st.markdown("""
    <style>
        [data-testid="stTable"] th, [data-testid="stDataFrame"] th {
            text-align: center !important;
        }
        [data-testid="stDataFrame"] td {
            text-align: center !important;
        }
    </style>
""", unsafe_allow_html=True)

# ========================== ЗАВАНТАЖЕННЯ ДАНИХ ==========================
@st.cache_data(ttl=300)
def load_data():
    # Використовуємо ту саму URL, що й на головній
    url = "http://194.99.22.193:8000/fpl_players"
    df = pd.read_parquet(url)
    
    # Сортування за xGI_norm за замовчуванням (атакувальна сторінка все ж таки)
    if 'xGI_norm' in df.columns:
        df = df.sort_values(by="xGI_norm", ascending=False)
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"Помилка завантаження: {e}")
    st.stop()

# ========================== ФІЛЬТРИ В САЙДБАРІ ==========================
st.sidebar.header("Attacking Filters") 

positions = sorted(df['element_type'].unique())
selected_positions = st.sidebar.multiselect("Pos", options=positions, default=[p for p in positions if p != "GK"])

teams = sorted(df['team_short_name'].unique())
selected_teams = st.sidebar.multiselect("Team", options=teams, default=teams)

c_min, c_max = float(df['now_cost'].min()), float(df['now_cost'].max())
f_cost = st.sidebar.slider("FPL Price", c_min, c_max, (c_min, c_max), 0.1)

m_min, m_max = int(df['matches_played'].min()), int(df['matches_played'].max())
f_matches = st.sidebar.slider("Matches", m_min, m_max, (5, m_max))

s_min, s_max = float(df['selected_by_percent'].min()), float(df['selected_by_percent'].max())
f_selected = st.sidebar.slider("Selected %", s_min, s_max, (s_min, s_max), 0.1)

o_min, o_max = float(df['top_100k'].min()), float(df['top_100k'].max())
f_top100k = st.sidebar.slider("Top 100k %", o_min, o_max, (o_min, o_max), 0.1)

am_min, am_max = float(df['avg_mins'].min()), float(df['avg_mins'].max())
f_avg_mins = st.sidebar.slider("Average Mins", am_min, am_max, (am_min, am_max), 1.0)

min_60 = float(df['60_min'].min())
max_60 = float(df['60_min'].max())
f_60min = st.sidebar.slider("60 Min %", min_60, max_60, (37.0, max_60), 0.5)

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
filtered_df = df[mask].copy()

# ========================== КОЛОНКИ ТА ВІДОБРАЖЕННЯ ==========================
# Список колонок згідно ТЗ
display_columns = [
    "full_name", "element_type", "Play Pos", "team_short_name", "now_cost", 
    "top_100k", "min_played", "matches_played", "matches_started", 
    "G_90", "xG_90", "A_90", "xA_90", "xGI_norm", "Sh_90", "ShoT_90", 
    "Touches_90", "Pass_pct", "KP_90", "BC_90", "PBC_90"
]

st.subheader(f"Attacking Stats: {len(filtered_df)} players")

# Налаштування конфігурації колонок
st.dataframe(
    filtered_df[display_columns],
    use_container_width=True,
    hide_index=True,
    height=800,
    column_config={
        "full_name": st.column_config.TextColumn("Player", pinned=True, width="medium"),
        "element_type": st.column_config.TextColumn("Pos", width=45),
        "Play Pos": st.column_config.TextColumn("Pl Pos", width=45),
        "team_short_name": st.column_config.TextColumn("Team", width=45),
        "now_cost": st.column_config.NumberColumn("Price", format="%.1f", width=45),
        "top_100k": st.column_config.NumberColumn("Top 100K", format="%.1f", width=55),
        "min_played": st.column_config.NumberColumn("Mins", width=50),
        "matches_played": st.column_config.NumberColumn("MP", width=35),
        "matches_started": st.column_config.NumberColumn("GS", width=35),
        "G_90": st.column_config.NumberColumn("G/90", format="%.2f", width=45),
        "xG_90": st.column_config.NumberColumn("xG/90", format="%.2f", width=45),
        "A_90": st.column_config.NumberColumn("A/90", format="%.2f", width=45),
        "xA_90": st.column_config.NumberColumn("xA/90", format="%.2f", width=45),
        "xGI_norm": st.column_config.NumberColumn("xGI_n/90", format="%.2f", width=55),
        "Sh_90": st.column_config.NumberColumn("Sh/90", format="%.2f", width=45),
        "ShoT_90": st.column_config.NumberColumn("ShoT/90", format="%.2f", width=45),
        "Touches_90": st.column_config.NumberColumn("Touches/90", format="%.1f", width=55),
        "Pass_pct": st.column_config.NumberColumn("Pass%", format="%.1f", width=45),
        "KP_90": st.column_config.NumberColumn("KP/90", format="%.2f", width=45),
        "BC_90": st.column_config.NumberColumn("BC/90", format="%.1f", width=45),
        "PBC_90": st.column_config.NumberColumn("PBC/90", format="%.1f", width=45),
    }
)
