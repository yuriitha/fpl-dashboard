import streamlit as st
import pandas as pd
import json

st.set_page_config(page_title="FPL Players Stats", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
        [data-testid="stTable"] th, [data-testid="stDataFrame"] th { text-align: center !important; }
        [data-testid="stDataFrame"] td { text-align: center !important; }
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 0.5rem !important; }

        [data-testid="stSidebar"] button {
            width: 60px !important; min-width: 60px !important; max-width: 60px !important;
            justify-content: center !important; padding: 0px !important;
            font-size: 0.75rem !important; height: 26px !important;
        }
        [data-testid="stSidebar"] button[kind="primary"] { width: 100% !important; max-width: none !important; }
        [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] button {
            width: 100% !important; max-width: none !important; min-width: 0px !important;
            height: 18px !important; min-height: 18px !important; font-size: 0.6rem !important;
            padding: 0px !important; line-height: 1 !important; border: none !important;
        }
        [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] { gap: 0.1rem !important; }
        [data-testid="stSidebar"] [data-testid="stPills"] > div,
        [data-testid="stSidebar"] div[role="group"] {
            display: flex !important; justify-content: center !important;
            flex-wrap: wrap !important; width: 100% !important;
        }
        [data-testid="stSlider"] [data-testid="stTickBar"] { height: 2px !important; }
        [data-testid="stSlider"] [data-basejs="slider"] > div { height: 4px !important; }
    </style>
""", unsafe_allow_html=True)

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

display_columns = [
    "full_name", "Age", "element_type", "Play Pos", "team_short_name", "now_cost",
    "Foot", "selected_by_percent", "top_10k", "top_100k", "min_played",
    "matches_played", "matches_started", "avg_mins", "60_min", "goals_scored",
    "assists", "av_rating", "av_rating_alt", "points_per_game", "transfers_in_event",
    "transfers_out_event", "transfers_in_24", "transfers_out_24", "news", "news_added"
]

# ========================== ПІДГОТОВКА ==========================
all_teams = sorted(df['team_short_name'].unique().tolist())
pos_order = ['GK', 'DEF', 'MID', 'FW']
actual_pos = df['element_type'].unique().tolist()
sorted_positions = [p for p in pos_order if p in actual_pos] + sorted([p for p in actual_pos if p not in pos_order])

pl_lines = [['GK'], ['RB', 'CB', 'LB'], ['RM', 'DM', 'CM', 'LM'], ['RW', 'AM', 'LW'], ['SS', 'CF']]
defined_pl_pos = [p for line in pl_lines for p in line]
actual_pl_pos = df['Play Pos'].dropna().unique().tolist()
others = sorted([p for p in actual_pl_pos if p not in defined_pl_pos])
if others: pl_lines.append(others)
all_pl_pos = [p for line in pl_lines for p in line if p in actual_pl_pos]

# --- GLOBAL BOUNDS (незмінні межі шкали слайдерів) ---
rating_series = df[df['av_rating_alt'] > 0]['av_rating_alt'].dropna()
r_min = float(rating_series.min()) if not rating_series.empty else 0.0
r_max = float(rating_series.max()) if not rating_series.empty else 10.0

GB = {
    'f_cost':     (float(df['now_cost'].min()),          float(df['now_cost'].max())),
    'f_matches':  (int(df['matches_played'].min()),      int(df['matches_played'].max())),
    'f_rating':   (r_min,                                r_max),
    'f_avg_mins': (float(df['avg_mins'].min()),          float(df['avg_mins'].max())),
    'f_60min':    (float(df['60_min'].min()),            float(df['60_min'].max())),
    'f_selected': (float(df['selected_by_percent'].min()), float(df['selected_by_percent'].max())),
    'f_top100k':  (float(df['top_100k'].min()),          float(df['top_100k'].max())),
}

# --- ДЕФОЛТНІ значення (початковий вибір повзунків) ---
DEFAULTS = {
    'f_cost':     GB['f_cost'],
    'f_matches':  (5,    GB['f_matches'][1]),
    'f_rating':   GB['f_rating'],
    'f_avg_mins': GB['f_avg_mins'],
    'f_60min':    (37.0, GB['f_60min'][1]),
    'f_selected': GB['f_selected'],
    'f_top100k':  GB['f_top100k'],
}

# ========================== ІНІЦІАЛІЗАЦІЯ СТАНУ ==========================
if 'pills_teams' not in st.session_state:   st.session_state.pills_teams = all_teams
if 'pills_pos'   not in st.session_state:   st.session_state.pills_pos   = sorted_positions
if 'pills_pl_pos' not in st.session_state:  st.session_state.pills_pl_pos = all_pl_pos

# ========================== ДОПОМІЖНІ ФУНКЦІЇ ==========================
def get_available(exclude_key=None):
    """Повертає підмножину df, відфільтровану за ВСІМА фільтрами, крім exclude_key."""
    cv_pos      = st.session_state.get('pills_pos',   sorted_positions) or []
    cv_teams    = st.session_state.get('pills_teams', all_teams) or []
    cv_matches  = st.session_state.get('f_matches',   DEFAULTS['f_matches'])
    cv_60min    = st.session_state.get('f_60min',     DEFAULTS['f_60min'])
    cv_cost     = st.session_state.get('f_cost',      DEFAULTS['f_cost'])
    cv_avg_mins = st.session_state.get('f_avg_mins',  DEFAULTS['f_avg_mins'])
    cv_selected = st.session_state.get('f_selected',  DEFAULTS['f_selected'])
    cv_top100k  = st.session_state.get('f_top100k',   DEFAULTS['f_top100k'])
    cv_rating   = st.session_state.get('f_rating',    DEFAULTS['f_rating'])
    cv_search   = st.session_state.get('search_name', '')

    cv_pl_pos = []
    for i, line in enumerate(pl_lines):
        avail_in_line = [p for p in line if p in actual_pl_pos]
        cv_pl_pos.extend(st.session_state.get(f'pills_pl_line_{i}', avail_in_line))

    mask = pd.Series([True] * len(df), index=df.index)
    if exclude_key != 'pills_pos':   mask &= df['element_type'].isin(cv_pos)
    if exclude_key != 'pills_teams': mask &= df['team_short_name'].isin(cv_teams)
    if exclude_key != 'pills_pl':
        if cv_pl_pos: mask &= df['Play Pos'].isin(cv_pl_pos)
    if exclude_key != 'f_matches':
        mask &= (df['matches_played'] >= cv_matches[0]) & (df['matches_played'] <= cv_matches[1])
    if exclude_key != 'f_60min':
        mask &= (df['60_min'] >= cv_60min[0]) & (df['60_min'] <= cv_60min[1])
    if exclude_key != 'f_cost':
        mask &= (df['now_cost'] >= cv_cost[0]) & (df['now_cost'] <= cv_cost[1])
    if exclude_key != 'f_avg_mins':
        mask &= (df['avg_mins'] >= cv_avg_mins[0]) & (df['avg_mins'] <= cv_avg_mins[1])
    if exclude_key != 'f_selected':
        mask &= (df['selected_by_percent'] >= cv_selected[0]) & (df['selected_by_percent'] <= cv_selected[1])
    if exclude_key != 'f_top100k':
        mask &= (df['top_100k'] >= cv_top100k[0]) & (df['top_100k'] <= cv_top100k[1])
    if exclude_key != 'f_rating':
        mask &= (df['av_rating_alt'] >= cv_rating[0]) & (df['av_rating_alt'] <= cv_rating[1])
    if exclude_key != 'search':
        mask &= df['full_name'].str.contains(cv_search, case=False, na=False)
    return df[mask]

def auto_update_slider(key, col, exclude_key, cast=float, only_positive=False):
    """
    Оновлює session_state[key] на основі доступних даних.
    Нижній повзунок: тільки підіймається, не падає нижче DEFAULTS[key][0].
    Верхній повзунок: адаптується.
    """
    avail_df = get_available(exclude_key)
    series = avail_df[col].dropna()
    if only_positive: series = series[series > 0]
    if series.empty: return

    avail_min = cast(series.min())
    avail_max = cast(series.max())
    default_lower = cast(DEFAULTS[key][0])
    curr = st.session_state.get(key, DEFAULTS[key])

    # Нижній: підіймаємо якщо треба, але не падаємо нижче дефолту автоматично
    new_lower = max(cast(curr[0]), avail_min)
    # Верхній: стискаємо до доступного максимуму
    new_upper = min(cast(curr[1]), avail_max)
    # Захист від інвертованого діапазону
    if new_lower > new_upper:
        new_lower = max(avail_min, default_lower)
        new_upper = avail_max

    st.session_state[key] = (new_lower, new_upper)

def pills_inactive_js(pill_options_all, available_options, container_index):
    """Inject JS to visually grey out unavailable pill options."""
    inactive = [o for o in pill_options_all if o not in available_options]
    if not inactive: return
    inactive_json = json.dumps(inactive)
    st.markdown(f"""
    <script>
    (function() {{
        const inactive = {inactive_json};
        function mark() {{
            const parent = window.parent ? window.parent.document : document;
            const pillGroups = parent.querySelectorAll('[data-testid="stSidebar"] [data-testid="stPills"]');
            const group = pillGroups[{container_index}];
            if (!group) {{ setTimeout(mark, 200); return; }}
            group.querySelectorAll('button[data-baseweb="button"]').forEach(btn => {{
                const txt = btn.innerText.trim();
                btn.style.opacity = inactive.includes(txt) ? '0.3' : '';
                btn.style.pointerEvents = 'auto';
            }});
        }}
        setTimeout(mark, 300);
    }})();
    </script>
    """, unsafe_allow_html=True)

def filter_header(label, options, key_prefix):
    cols = st.sidebar.columns([1.4, 0.8, 0.8])
    cols[0].markdown(f"<p style='font-size: 0.875rem; margin-bottom: 0px;'>{label}</p>", unsafe_allow_html=True)
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

# ========================== ПОПЕРЕДНЄ ОНОВЛЕННЯ СЛАЙДЕРІВ ==========================
# Оновлюємо значення ДО рендерингу, щоб слайдери показували актуальні межі
auto_update_slider('f_cost',     'now_cost',          'f_cost',     float)
auto_update_slider('f_rating',   'av_rating_alt',     'f_rating',   float, only_positive=True)
auto_update_slider('f_matches',  'matches_played',    'f_matches',  int)
auto_update_slider('f_avg_mins', 'avg_mins',          'f_avg_mins', float)
auto_update_slider('f_60min',    '60_min',            'f_60min',    float)
auto_update_slider('f_selected', 'selected_by_percent','f_selected', float)
auto_update_slider('f_top100k',  'top_100k',          'f_top100k',  float)

# ========================== САЙДБАР ==========================
if st.sidebar.button("Reset All Filters", use_container_width=True, type="primary"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

search_name = st.sidebar.text_input("Search Player", placeholder="Enter name...", key="search_name")

# --- 1. FPL POSITION ---
avail_pos = set(get_available('pills_pos')['element_type'].unique())
filter_header("FPL Position", sorted_positions, "pos")
selected_positions = st.sidebar.pills(
    "FPL Position", options=sorted_positions, key="pills_pos",
    selection_mode="multi", label_visibility="collapsed"
)
pills_inactive_js(sorted_positions, list(avail_pos), 0)

# --- 2. FPL PRICE ---
f_cost = st.sidebar.slider(
    "FPL Price", GB['f_cost'][0], GB['f_cost'][1],
    step=0.1, format="%.1f", key="f_cost"
)

# --- 3. TEAM ---
avail_teams = set(get_available('pills_teams')['team_short_name'].unique())
filter_header("Team", all_teams, "teams")
selected_teams = st.sidebar.pills(
    "Team", options=all_teams, key="pills_teams",
    selection_mode="multi", label_visibility="collapsed"
)
pills_inactive_js(all_teams, list(avail_teams), 1)

# --- 4. PLAYING POSITION ---
avail_pl = set(get_available('pills_pl')['Play Pos'].dropna().unique())
filter_header("Playing Position", all_pl_pos, "pl_pos")
selected_pl_pos = []
pill_group_idx = 2
for idx, line in enumerate(pl_lines):
    available_in_line = [p for p in line if p in actual_pl_pos]
    if available_in_line:
        line_key = f"pills_pl_line_{idx}"
        if line_key not in st.session_state:
            st.session_state[line_key] = [p for p in st.session_state.pills_pl_pos if p in available_in_line]
        line_res = st.sidebar.pills(
            label=f"pl_line_{idx}", options=available_in_line, key=line_key,
            selection_mode="multi", label_visibility="collapsed"
        )
        pills_inactive_js(available_in_line, [p for p in available_in_line if p in avail_pl], pill_group_idx)
        pill_group_idx += 1
        if line_res: selected_pl_pos.extend(line_res)

# --- PERFORMANCE STATS ---
with st.sidebar.expander("Performance Stats", expanded=False):
    f_matches = st.slider(
        "Matches", GB['f_matches'][0], GB['f_matches'][1],
        step=1, key="f_matches"
    )
    f_rating = st.slider(
        "Rating", GB['f_rating'][0], GB['f_rating'][1],
        step=0.05, format="%.2f", key="f_rating"
    )
    f_avg_mins = st.slider(
        "Average Mins", GB['f_avg_mins'][0], GB['f_avg_mins'][1],
        step=1.0, key="f_avg_mins"
    )
    f_60min = st.slider(
        "60 Min %", GB['f_60min'][0], GB['f_60min'][1],
        step=0.5, key="f_60min"
    )

# --- MARKET & POPULARITY ---
with st.sidebar.expander("Market & Popularity", expanded=False):
    f_selected = st.slider(
        "Selected %", GB['f_selected'][0], GB['f_selected'][1],
        step=0.1, key="f_selected"
    )
    f_top100k = st.slider(
        "Top 100k %", GB['f_top100k'][0], GB['f_top100k'][1],
        step=0.1, key="f_top100k"
    )

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