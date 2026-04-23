import streamlit as st
import pandas as pd

# Налаштування сторінки
st.set_page_config(
    page_title="FPL Players Stats",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS для максимальної компактності та однакової ширини пігулок
st.markdown("""
    <style>
        [data-testid="stTable"] th, [data-testid="stDataFrame"] th { text-align: center !important; }
        [data-testid="stDataFrame"] td { text-align: center !important; }
        
        /* Максимальна компактність */
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 0.5rem !important; }

        /* 1. Задаємо ширину всім кнопкам у сайдбарі (для пігулок) */
        [data-testid="stSidebar"] button {
            width: 60px !important;
            min-width: 60px !important;
            max-width: 60px !important;
            justify-content: center !important;
            padding: 0px !important;
            font-size: 0.75rem !important;
            height: 26px !important;
        }

        /* 2. ВИКЛЮЧЕННЯ: Кнопка Reset (Primary) має бути на всю ширину */
        [data-testid="stSidebar"] button[kind="primary"] {
            width: 100% !important;
            max-width: none !important;
        }

        /* 3. ВИКЛЮЧЕННЯ: Кнопки All/None у колонках мають бути на всю ширину своєї колонки */
        [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] button {
            width: 100% !important;
            max-width: none !important;
            min-width: 0px !important;
            height: 18px !important;
            min-height: 18px !important;
            font-size: 0.6rem !important;
            padding: 0px !important;
            line-height: 1 !important;
            border: none !important;
        }

        /* 4. Зменшуємо проміжок між колонками All/None */
        [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] {
            gap: 0.1rem !important;
        }


        /* 5. Центрування ТІЛЬКИ для пігулок (Pills) */
        [data-testid="stSidebar"] [data-testid="stPills"] > div,
        [data-testid="stSidebar"] div[role="group"] {
            display: flex !important;
            justify-content: center !important;
            flex-wrap: wrap !important;
            width: 100% !important;
        }

        /* Тонкі лінії слайдерів */
        [data-testid="stSlider"] [data-testid="stTickBar"] { height: 2px !important; }
        [data-testid="stSlider"] [data-basejs="slider"] > div { height: 4px !important; }
    </style>
""", unsafe_allow_html=True)

# Допоміжна функція для заголовків фільтрів з кнопками All/None
def filter_header(label, options, key_prefix):
    cols = st.sidebar.columns([1.4, 0.8, 0.8])
    cols[0].markdown(f"<p style='font-size: 0.875rem; margin-bottom: 0px;'>{label}</p>", unsafe_allow_html=True)
    
    # Кнопка All тепер напряму змінює стан віджета
    if cols[1].button("All", key=f"btn_all_{key_prefix}", use_container_width=True):
        st.session_state[f"pills_{key_prefix}"] = options
        if key_prefix == "pl_pos":
            for i, line in enumerate(pl_lines):
                st.session_state[f"pills_pl_line_{i}"] = [p for p in options if p in line]
        st.rerun()
    
    if cols[2].button("None", key=f"btn_none_{key_prefix}", use_container_width=True):
        st.session_state[f"pills_{key_prefix}"] = []
        if key_prefix == "pl_pos":
            for i, line in enumerate(pl_lines):
                st.session_state[f"pills_pl_line_{i}"] = []
        st.rerun()

# ========================== ЗАВАНТАЖЕННЯ ДАНИХ ==========================
@st.cache_data(ttl=300)
def load_data():
    url = "http://194.99.22.193:8000/fpl_players"
    df = pd.read_parquet(url)
    if 'av_rating_alt' in df.columns:
        df['av_rating_alt'] = pd.to_numeric(df['av_rating_alt'], errors='coerce')
        df = df.sort_values(by="av_rating_alt", ascending=False)
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"Помилка завантаження: {e}")
    st.stop()

# ========================== ПІДГОТОВКА СПИСКУ КОЛОНОК ==========================
# ОЦЕ ТЕ, ЧОГО НЕ ВИСТАЧАЛО (Причина NameError)
display_columns = [
    "full_name", "Age", "element_type", "Play Pos", "team_short_name", "now_cost", 
    "Foot", "selected_by_percent", "top_10k", "top_100k", "min_played", 
    "matches_played", "matches_started", "avg_mins", "60_min", "goals_scored", 
    "assists", "av_rating", "av_rating_alt", "points_per_game", "transfers_in_event", 
    "transfers_out_event", "transfers_in_24", "transfers_out_24", "news", "news_added"
]

# ========================== ФІЛЬТРИ В САЙДБАРІ ==========================
# ========================== ПІДГОТОВКА ДАНИХ ДЛЯ ФІЛЬТРІВ ==========================
all_teams = sorted(df['team_short_name'].unique().tolist())
pos_order = ['GK', 'DEF', 'MID', 'FW']
actual_pos = df['element_type'].unique().tolist()
sorted_positions = [p for p in pos_order if p in actual_pos] + sorted([p for p in actual_pos if p not in pos_order])

pl_lines = [
    ['GK'], ['RB', 'CB', 'LB'], ['RM', 'DM', 'CM', 'LM'], ['RW', 'AM', 'LW'], ['SS', 'CF']
]
defined_pl_pos = [item for sublist in pl_lines for item in sublist]
actual_pl_pos = df['Play Pos'].dropna().unique().tolist()
others = sorted([p for p in actual_pl_pos if p not in defined_pl_pos])
if others: pl_lines.append(others)
all_pl_pos = [p for line in pl_lines for p in line if p in actual_pl_pos]

# --- ІНІЦІАЛІЗАЦІЯ СТАНУ (Базові значення без лічильників) ---
if "pills_teams" not in st.session_state: st.session_state.pills_teams = all_teams
if "pills_pos" not in st.session_state: st.session_state.pills_pos = sorted_positions
if "pills_pl_pos" not in st.session_state: st.session_state.pills_pl_pos = all_pl_pos

# Функція для отримання маски БЕЗ врахування одного конкретного фільтра
def get_mask(exclude=None):
    m = pd.Series(True, index=df.index)
    
    # 1. Search
    search = st.session_state.get("search_name", "")
    if exclude != "search" and search:
        m &= df['full_name'].str.contains(search, case=False, na=False)
    
    # 2. Position
    sel_pos = st.session_state.get("pills_pos", sorted_positions)
    if exclude != "pos":
        m &= df['element_type'].isin(sel_pos)
        
    # 3. Team
    sel_teams = st.session_state.get("pills_teams", all_teams)
    if exclude != "teams":
        m &= df['team_short_name'].isin(sel_teams)
        
    # 4. Sliders
    for key, col in [
        ("f_cost", "now_cost"), ("f_rating", "av_rating_alt"), 
        ("f_matches", "matches_played"), ("f_60min", "60_min"),
        ("f_avg_mins", "avg_mins"), ("f_selected", "selected_by_percent"),
        ("f_top100k", "top_100k")
    ]:
        if exclude != key:
            val = st.session_state.get(key)
            if val:
                m &= (df[col] >= val[0]) & (df[col] <= val[1])
            elif key == "f_matches": m &= (df[col] >= 5) # Default
            elif key == "f_60min": m &= (df[col] >= 37.0) # Default
            
    # 5. Play Pos
    sel_pl = st.session_state.get("pills_pl_pos", all_pl_pos)
    sel_pl = [p.split(" (")[0] for p in sel_pl]
    if exclude != "pl_pos":
        m &= df['Play Pos'].isin(sel_pl)
        
    return m

# ========================== САЙДБАР (ВІДОБРАЖЕННЯ) ==========================
st.sidebar.button("Reset All Filters", use_container_width=True, type="primary", on_click=lambda: st.session_state.clear())

search_name = st.sidebar.text_input("Search Player", placeholder="Enter name...", key="search_name")

# --- ДИНАМІЧНИЙ РОЗРАХУНОК ДЛЯ ПІГУЛОК ---
# (Залишаємо чисті назви без лічильників)
def get_clean_options(options, col, exclude_key):
    return options

# 1. Position Pills
pos_options = sorted_positions
filter_header("FPL Position", sorted_positions, "pos")
st.sidebar.pills("FPL Position", options=pos_options, key="pills_pos", selection_mode="multi", label_visibility="collapsed")

# 2. Team Pills
team_options = all_teams
filter_header("Team", all_teams, "teams")
st.sidebar.pills("Team", options=team_options, key="pills_teams", selection_mode="multi", label_visibility="collapsed")

# --- ДИНАМІЧНИЙ РОЗРАХУНОК ДЛЯ СЛАЙДЕРІВ (Option A) ---
def render_adaptive_slider(label, col, key, step=0.1, is_int=False, fmt=None):
    m = get_mask(exclude=key)
    data = df[m][col].dropna()
    if data.empty:
        low, high = float(df[col].min()), float(df[col].max())
    else:
        low, high = float(data.min()), float(data.max())
    
    full_min, full_max = float(df[col].min()), float(df[col].max())
    if is_int:
        low, high, full_min, full_max = int(low), int(high), int(full_min), int(full_max)
        
    # Якщо фільтри змінилися - підтягуємо значення
    if key not in st.session_state:
        st.session_state[key] = (low, high)
    
    return st.sidebar.slider(label, full_min, full_max, value=(low, high), step=step, key=key, format=fmt)

f_cost = render_adaptive_slider("FPL Price", "now_cost", "f_cost", 0.1, fmt="%.1f")

# --- 4. PLAYING POSITION ---
filter_header("Playing Position", all_pl_pos, "pl_pos")
st.sidebar.pills("Playing Position", options=all_pl_pos, key="pills_pl_pos", selection_mode="multi", label_visibility="collapsed")
selected_pl_pos = st.session_state.pills_pl_pos

# --- ДОДАТКОВІ ФІЛЬТРИ В ЕКСПАНДЕРАХ ---
with st.sidebar.expander("Performance Stats", expanded=False):
    f_matches = render_adaptive_slider("Matches", "matches_played", "f_matches", 1, is_int=True)
    f_rating = render_adaptive_slider("Rating", "av_rating_alt", "f_rating", 0.05, fmt="%.2f")
    f_avg_mins = render_adaptive_slider("Average Mins", "avg_mins", "f_avg_mins", 1.0)
    f_60min = render_adaptive_slider("60 Min %", "60_min", "f_60min", 0.5, fmt="%.1f")

with st.sidebar.expander("Market & Popularity", expanded=False):
    f_selected = render_adaptive_slider("Selected %", "selected_by_percent", "f_selected", 0.1, fmt="%.1f")
    f_top100k = render_adaptive_slider("Top 100k %", "top_100k", "f_top100k", 0.1, fmt="%.1f")

# ========================== ЗАСТОСУВАННЯ ФІЛЬТРІВ ==========================
mask = (
    df['element_type'].isin(st.session_state.get("pills_pos", sorted_positions)) &
    df['team_short_name'].isin(st.session_state.get("pills_teams", all_teams)) &
    df['Play Pos'].isin(st.session_state.get("pills_pl_pos", all_pl_pos)) &
    (df['av_rating_alt'] >= st.session_state.f_rating[0]) & (df['av_rating_alt'] <= st.session_state.f_rating[1]) &
    (df['matches_played'] >= st.session_state.f_matches[0]) & (df['matches_played'] <= st.session_state.f_matches[1]) &
    (df['60_min'] >= st.session_state.f_60min[0]) & (df['60_min'] <= st.session_state.f_60min[1]) &
    (df['now_cost'] >= st.session_state.f_cost[0]) & (df['now_cost'] <= st.session_state.f_cost[1]) &
    (df['selected_by_percent'] >= st.session_state.f_selected[0]) & (df['selected_by_percent'] <= st.session_state.f_selected[1]) &
    (df['top_100k'] >= st.session_state.f_top100k[0]) & (df['top_100k'] <= st.session_state.f_top100k[1]) &
    (df['avg_mins'] >= st.session_state.f_avg_mins[0]) & (df['avg_mins'] <= st.session_state.f_avg_mins[1]) &
    (df['full_name'].str.contains(st.session_state.get("search_name", ""), case=False, na=False))
)
filtered_df = df[mask].copy()

# ========================== ВІДОБРАЖЕННЯ ТАБЛИЦІ ==========================
st.subheader(f"Players filtered: {len(filtered_df)}")

st.dataframe(
    filtered_df[display_columns],
    use_container_width=True,
    hide_index=True,
    height=800,
    column_config={
        "full_name": st.column_config.TextColumn("Player", width="medium", pinned=True),
        "Age": st.column_config.NumberColumn("Age", width=35, format="%d"),
        "element_type": st.column_config.TextColumn("Pos", width=45),
        "Play Pos": st.column_config.TextColumn("Pl Pos", width=45),
        "team_short_name": st.column_config.TextColumn("Team", width=45),
        "now_cost": st.column_config.NumberColumn("Price", width=40, format="%.1f"),
        "Foot": st.column_config.TextColumn("Foot", width=45),
        "selected_by_percent": st.column_config.NumberColumn("Selected", width=50, format="%.1f"),
        "top_10k": st.column_config.NumberColumn("Top 10k", width=50, format="%.1f"),
        "top_100k": st.column_config.NumberColumn("Top 100k", width=50, format="%.1f"),
        "min_played": st.column_config.NumberColumn("Mins", width=45),
        "matches_played": st.column_config.NumberColumn("MP", width=35),
        "matches_started": st.column_config.NumberColumn("GS", width=35),
        "avg_mins": st.column_config.NumberColumn("AvgMins", width=40, format="%d"),
        "60_min": st.column_config.NumberColumn("60% Mins", width=45, format="%.1f"),
        "goals_scored": st.column_config.NumberColumn("G", width=30),
        "assists": st.column_config.NumberColumn("A", width=30),
        "av_rating": st.column_config.NumberColumn("Rat", width=40, format="%.2f"),
        "av_rating_alt": st.column_config.NumberColumn("RatA", width=40, format="%.2f"),
        "points_per_game": st.column_config.NumberColumn("PPM", width=40, format="%.1f"),
        "transfers_in_event": st.column_config.NumberColumn("In", width=60),
        "transfers_out_event": st.column_config.NumberColumn("Out", width=60),
        "transfers_in_24": st.column_config.NumberColumn("In 24", width=50),
        "transfers_out_24": st.column_config.NumberColumn("Out 24", width=50),
        "news": st.column_config.TextColumn("News", width="medium"),
        "news_added": st.column_config.TextColumn("Updated", width=175),
    }
)