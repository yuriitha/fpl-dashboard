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
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 0.1rem !important; }

        /* 1. Задаємо ширину всім кнопкам у сайдбарі (для пігулок) */
        [data-testid="stSidebar"] button {
            width: 72px !important;
            min-width: 72px !important;
            max-width: 72px !important;
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

        /* Стиль для заголовків фільтрів та слайдерів */
        .filter-label, [data-testid="stSlider"] label {
            font-weight: 600 !important;
            font-size: 0.8rem !important;
            margin-top: 0.4rem !important;
            color: inherit !important;
        }

        /* Центрування для тактичної схеми Playing Position */
        [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] {
            justify-content: center !important;
        }

        /* Тонкі лінії слайдерів */
        [data-testid="stSlider"] [data-testid="stTickBar"] { height: 2px !important; }
        [data-testid="stSlider"] [data-basejs="slider"] > div { height: 4px !important; }
    </style>
""", unsafe_allow_html=True)

# Допоміжна функція для заголовків фільтрів з кнопками All/None
def filter_header(label, options, key_prefix):
    cols = st.sidebar.columns([1.4, 0.8, 0.8])
    cols[0].markdown(f"<p class='filter-label'>{label}</p>", unsafe_allow_html=True)
    
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
# --- ПІДГОТОВКА СПИСКІВ ---
all_teams = sorted(df['team_short_name'].unique().tolist())
pos_order = ['GK', 'DEF', 'MID', 'FW']
actual_pos = df['element_type'].unique().tolist()
sorted_positions = [p for p in pos_order if p in actual_pos] + sorted([p for p in actual_pos if p not in pos_order])

pl_lines = [
    ['GK'], 
    ['RB', 'CB', 'LB'], 
    ['RM', 'DM', 'CM', 'LM'], 
    ['RW', 'AM', 'LW'], 
    ['SS', 'CF']
]
defined_pl_pos = [item for sublist in pl_lines for item in sublist]
actual_pl_pos = df['Play Pos'].dropna().unique().tolist()
others = sorted([p for p in actual_pl_pos if p not in defined_pl_pos])
if others: pl_lines.append(others)
all_pl_pos = [p for line in pl_lines for p in line if p in actual_pl_pos]

# --- ІНІЦІАЛІЗАЦІЯ СТАНУ ---
if "pills_teams" not in st.session_state: st.session_state.pills_teams = all_teams
if "pills_pos" not in st.session_state: st.session_state.pills_pos = sorted_positions
if "pills_pl_pos" not in st.session_state: st.session_state.pills_pl_pos = all_pl_pos

# --- САЙДБАР ---
if st.sidebar.button("Reset All Filters", use_container_width=True, type="primary"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

search_name = st.sidebar.text_input("Search Player", placeholder="Enter name...")

# --- 1. FPL POSITION ---
filter_header("FPL Position", sorted_positions, "pos")
selected_positions = st.sidebar.pills("FPL Position", options=sorted_positions, key="pills_pos", selection_mode="multi", label_visibility="collapsed")

# --- 2. FPL PRICE ---
c_min, c_max = float(df['now_cost'].min()), float(df['now_cost'].max())
f_cost = st.sidebar.slider("FPL Price", c_min, c_max, (c_min, c_max), 0.1, key="f_cost")

# --- 3. TEAM ---
filter_header("Team", all_teams, "teams")
selected_teams = st.sidebar.pills("Team", options=all_teams, key="pills_teams", selection_mode="multi", label_visibility="collapsed")

# --- 4. PLAYING POSITION ---
filter_header("Playing Position", all_pl_pos, "pl_pos")
selected_pl_pos = []
for idx, line in enumerate(pl_lines):
    available_in_line = [p for p in line if p in actual_pl_pos]
    if available_in_line:
        line_key = f"pills_pl_line_{idx}"
        
        # Ініціалізація, якщо ключа ще немає
        if line_key not in st.session_state:
            st.session_state[line_key] = [p for p in st.session_state.pills_pl_pos if p in available_in_line]

        line_res = st.sidebar.pills(
            label=f"pl_line_{idx}",
            options=available_in_line,
            key=line_key,
            selection_mode="multi",
            label_visibility="collapsed"
        )
        if line_res:
            selected_pl_pos.extend(line_res)

# --- ДОДАТКОВІ ФІЛЬТРИ В ЕКСПАНДЕРАХ ---
with st.sidebar.expander("Performance Stats", expanded=False):
    m_min, m_max = int(df['matches_played'].min()), int(df['matches_played'].max())
    f_matches = st.slider("Matches", m_min, m_max, (5, m_max), key="f_matches")

    rating_series = df[df['av_rating_alt'] > 0]['av_rating_alt'].dropna()
    r_min, r_max = (float(rating_series.min()), float(rating_series.max())) if not rating_series.empty else (0.0, 10.0)
    f_rating = st.slider("Rating", r_min, r_max, (r_min, r_max), 0.05, format="%.2f", key="f_rating")

    am_min, am_max = float(df['avg_mins'].min()), float(df['avg_mins'].max())
    f_avg_mins = st.slider("Average Mins", am_min, am_max, (am_min, am_max), 1.0, key="f_avg_mins")

    min_60, max_60 = float(df['60_min'].min()), float(df['60_min'].max())
    f_60min = st.slider("60 Min %", min_60, max_60, (37.0, max_60), 0.5, key="f_60min")

with st.sidebar.expander("Market & Popularity", expanded=False):
    s_min, s_max = float(df['selected_by_percent'].min()), float(df['selected_by_percent'].max())
    f_selected = st.slider("Selected %", s_min, s_max, (s_min, s_max), 0.1, key="f_selected")

    o_min, o_max = float(df['top_100k'].min()), float(df['top_100k'].max())
    f_top100k = st.slider("Top 100k %", o_min, o_max, (o_min, o_max), 0.1, key="f_top100k")

# ========================== ЗАСТОСУВАННЯ ФІЛЬТРІВ ==========================
mask = (
    df['element_type'].isin(selected_positions if selected_positions else []) &
    df['team_short_name'].isin(selected_teams if selected_teams else []) &
    df['Play Pos'].isin(selected_pl_pos if selected_pl_pos else []) &
    (df['av_rating_alt'] >= f_rating[0]) & (df['av_rating_alt'] <= f_rating[1]) &
    (df['matches_played'] >= f_matches[0]) & (df['matches_played'] <= f_matches[1]) &
    (df['60_min'] >= f_60min[0]) & (df['60_min'] <= f_60min[1]) &
    (df['now_cost'] >= f_cost[0]) & (df['now_cost'] <= f_cost[1]) &
    (df['selected_by_percent'] >= f_selected[0]) & (df['selected_by_percent'] <= f_selected[1]) &
    (df['top_100k'] >= f_top100k[0]) & (df['top_100k'] <= f_top100k[1]) &
    (df['avg_mins'] >= f_avg_mins[0]) & (df['avg_mins'] <= f_avg_mins[1]) &
    (df['full_name'].str.contains(search_name, case=False, na=False))
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