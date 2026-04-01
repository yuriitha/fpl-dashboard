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
    # URL вашого API
    url = "http://194.99.22.193:8000/fpl_players"
    df = pd.read_parquet(url)
    
    # Сортування за xGI_norm для стартового вигляду
    if 'xGI_norm' in df.columns:
        df = df.sort_values(by="xGI_norm", ascending=False)
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"Помилка завантаження: {e}")
    st.stop()

# ========================== ФІЛЬТРИ В САЙДБАРІ ==========================
st.sidebar.header("Main Filters") 

# Позиції
positions = sorted(df['element_type'].unique()) if 'element_type' in df.columns else []
selected_positions = st.sidebar.multiselect("Pos", options=positions, default=[p for p in positions if p != "GK"])

# Команди
teams = sorted(df['team_short_name'].unique()) if 'team_short_name' in df.columns else []
selected_teams = st.sidebar.multiselect("Team", options=teams, default=teams)

# Ціна
c_min = float(df['now_cost'].min()) if 'now_cost' in df.columns else 4.0
c_max = float(df['now_cost'].max()) if 'now_cost' in df.columns else 15.0
f_cost = st.sidebar.slider("Price", c_min, c_max, (c_min, c_max), 0.1)

# Матчі
m_min = int(df['matches_played'].min()) if 'matches_played' in df.columns else 0
m_max = int(df['matches_played'].max()) if 'matches_played' in df.columns else 38
f_matches = st.sidebar.slider("Matches Played", m_min, m_max, (min(5, m_max), m_max))

# Середні хвилини та 60 хв
am_min = float(df['avg_mins'].min()) if 'avg_mins' in df.columns else 0.0
am_max = float(df['avg_mins'].max()) if 'avg_mins' in df.columns else 90.0
f_avg_mins = st.sidebar.slider("Average Mins", am_min, am_max, (am_min, am_max), 1.0)

min_60 = float(df['60_min'].min()) if '60_min' in df.columns else 0.0
max_60 = float(df['60_min'].max()) if '60_min' in df.columns else 100.0
f_60min = st.sidebar.slider("60 Min %", min_60, max_60, (min(37.0, max_60), max_60), 0.5)

# Додаткові показники (Advanced)
with st.sidebar.expander("Advanced Stats Filters", expanded=True):
    def get_max(col): return float(df[col].max()) if col in df.columns else 1.0
    
    f_xg = st.slider("xG/90", 0.0, get_max('xG_90'), (0.0, get_max('xG_90')), 0.05)
    f_xa = st.slider("xA/90", 0.0, get_max('xA_90'), (0.0, get_max('xA_90')), 0.05)
    f_xgi = st.slider("xGI_n/90", 0.0, get_max('xGI_norm'), (0.0, get_max('xGI_norm')), 0.1)
    f_sh = st.slider("Sh/90", 0.0, get_max('Sh_90'), (0.0, get_max('Sh_90')), 0.5)
    f_kp = st.slider("KP/90", 0.0, get_max('KP_90'), (0.0, get_max('KP_90')), 0.1)

# ========================== ЗАСТОСУВАННЯ ФІЛЬТРІВ ==========================
mask = (
    df['element_type'].isin(selected_positions) &
    df['team_short_name'].isin(selected_teams) &
    (df['now_cost'] >= f_cost[0]) & (df['now_cost'] <= f_cost[1]) &
    (df['matches_played'] >= f_matches[0]) & (df['matches_played'] <= f_matches[1]) &
    (df['avg_mins'] >= f_avg_mins[0]) & (df['avg_mins'] <= f_avg_mins[1]) &
    (df['60_min'] >= f_60min[0]) & (df['60_min'] <= f_60min[1]) &
    (df['xG_90'] >= f_xg[0]) & (df['xG_90'] <= f_xg[1]) &
    (df['xA_90'] >= f_xa[0]) & (df['xA_90'] <= f_xa[1]) &
    (df['xGI_norm'] >= f_xgi[0]) & (df['xGI_norm'] <= f_xgi[1]) &
    (df['Sh_90'] >= f_sh[0]) & (df['Sh_90'] <= f_sh[1]) &
    (df['KP_90'] >= f_kp[0]) & (df['KP_90'] <= f_kp[1])
)
filtered_df = df[mask].copy()

# ========================== СТИЛІЗАЦІЯ ТА ВІДОБРАЖЕННЯ ==========================
# Оновлений порядок стовпчиків: Selected тепер між now_cost та top_100k
display_columns = [
    "full_name", "element_type", "Play Pos", "team_short_name", "now_cost", 
    "selected_by_percent", "top_100k", "min_played", "matches_played", "matches_started", 
    "avg_mins", "60_min", "av_rating_alt", 
    "G_90", "xG_90", "xGoT_90", "A_90", "xA_90", "xGI_norm", 
    "Sh_90", "ShoT_90", "KP_90", "Touches_90", "Pass_pct", "BC_90", "PBC_90"
]

# Перевірка наявності колонок
existing_cols = [c for c in display_columns if c in filtered_df.columns]

# Створення стилізованого DataFrame
styled_df = filtered_df[existing_cols].style \
    .background_gradient(cmap='YlGn', subset=[c for c in ['top_100k'] if c in existing_cols]) \
    .background_gradient(cmap='RdYlGn', subset=[c for c in ['avg_mins', 'av_rating_alt', '60_min'] if c in existing_cols]) \
    .background_gradient(cmap='YlGn', subset=[c for c in ['G_90', 'xG_90', 'xGoT_90','A_90', 'xA_90', 'xGI_norm', 'Sh_90', 'ShoT_90', 'KP_90'] if c in existing_cols]) \
    .background_gradient(cmap='GnBu', subset=[c for c in ['Touches_90', 'Pass_pct', 'BC_90', 'PBC_90'] if c in existing_cols]) \
    .format(precision=2)

st.subheader(f"Attacking Stats: {len(filtered_df)} players")

st.dataframe(
    styled_df,
    use_container_width=True,
    hide_index=True,
    height=800,
    column_config={
        "full_name": st.column_config.TextColumn("Player", pinned=True, width="medium"),
        "element_type": st.column_config.TextColumn("Pos", width=45),
        "Play Pos": st.column_config.TextColumn("Pl Pos", width=45),
        "team_short_name": st.column_config.TextColumn("Team", width=45),
        "now_cost": st.column_config.NumberColumn("Price", format="%.1f", width=45),
        "selected_by_percent": st.column_config.NumberColumn("Selected", format="%.1f%%", width=55),
        "top_100k": st.column_config.NumberColumn("Top 100K", format="%.1f%%", width=55),
        "min_played": st.column_config.NumberColumn("Mins", width=45),
        "matches_played": st.column_config.NumberColumn("MP", width=35),
        "matches_started": st.column_config.NumberColumn("GS", width=35),
        "avg_mins": st.column_config.NumberColumn("AvgMins", width=40),
        "60_min": st.column_config.NumberColumn("60% Mins", width=50, format="%.1f"),
        "av_rating_alt": st.column_config.NumberColumn("RatA", format="%.2f", width=45),
	"G_90": st.column_config.NumberColumn("G/90", width=40),
        "xG_90": st.column_config.NumberColumn("xG/90", width=40),
        "xGoT_90": st.column_config.NumberColumn("xGoT/90", width=40),
        "A_90": st.column_config.NumberColumn("A/90", width=40),
        "xA_90": st.column_config.NumberColumn("xA/90", width=40),
        "xGI_norm": st.column_config.NumberColumn("xGI_n/90", width=50),
        "Sh_90": st.column_config.NumberColumn("Sh/90", width=40),
        "ShoT_90": st.column_config.NumberColumn("ShoT/90", width=40),
        "KP_90": st.column_config.NumberColumn("KP/90", width=40),
        "Touches_90": st.column_config.NumberColumn("Touches/90", width=50),
        "Pass_pct": st.column_config.NumberColumn("Pass%", width=45),
        "BC_90": st.column_config.NumberColumn("BC/90", width=40),
        "PBC_90": st.column_config.NumberColumn("PBC/90", width=40),
    }
)