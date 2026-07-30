import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import plotly.graph_objects as go
import json

# Налаштування сторінки
st.set_page_config(
    page_title="FPL Players Form (Last 10 Games)",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
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

        /* Запобігаємо мерехтінню: CSS-правило на базі стабільного батька, якому JS призначає клас */
        .playing-pos-wrapper button {
            width: 48px !important; min-width: 48px !important; max-width: 48px !important;
        }
    </style>
""", unsafe_allow_html=True)


# ========================== ЗАВАНТАЖЕННЯ ДАНИХ ==========================
@st.cache_data(ttl=300)
def load_data():
    url = "http://194.99.22.193:8000/fpl_players"
    df = pd.read_parquet(url)
    
    # Використовуємо показники за останні 10 ігор
    rating_col = 'av_rating_alt_10'
    if rating_col in df.columns:
        df[rating_col] = pd.to_numeric(df[rating_col], errors='coerce')
        df = df.sort_values(by=rating_col, ascending=False)
    
    # Calculate Transfer Activity (Logarithmic Scale)
    if 'transfers_in_24' in df.columns and 'transfers_out_24' in df.columns:
        df['transfer_activity'] = df['transfers_in_24'] + df['transfers_out_24']
        log_act = np.log1p(df['transfer_activity'])
        max_log = log_act.max()
        if max_log > 0:
            df['transfer_activity_pct'] = (log_act / max_log) * 100.0
        else:
            df['transfer_activity_pct'] = 0.0
    else:
        df['transfer_activity_pct'] = 0.0
        
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"Помилка завантаження: {e}")
    st.stop()


# ========================== ПІДГОТОВКА ==========================
all_teams = sorted(df['team_short_name'].unique().tolist())
default_teams = all_teams
pos_order = ['GK', 'DEF', 'MID', 'FW']
actual_pos = df['element_type'].unique().tolist()
sorted_positions = [p for p in pos_order if p in actual_pos] + sorted([p for p in actual_pos if p not in pos_order])

pl_lines = [['GK'], ['RB', 'CB', 'LB'], ['RM', 'DM', 'CM', 'LM'], ['RW', 'AM', 'LW'], ['SS', 'CF']]
defined_pl_pos = [p for line in pl_lines for p in line]
actual_pl_pos = df['Play Pos'].dropna().unique().tolist()
others = sorted([p for p in actual_pl_pos if p not in defined_pl_pos])
if others: pl_lines.append(others)
all_pl_pos = [p for line in pl_lines for p in line if p in actual_pl_pos]

rating_col = 'av_rating_alt_10'
xgi_col = 'xGI_norm_10'

# Перевірка наявності колонок
if rating_col not in df.columns:
    st.error(f"Колонка {rating_col} не знайдена в даних. Можливо, потрібно оновити паркет файл.")
    st.stop()

rating_series = df[df[rating_col] > 0][rating_col].dropna()
r_min = float(rating_series.min()) if not rating_series.empty else 0.0
r_max = float(rating_series.max()) if not rating_series.empty else 10.0

# Глобальні межі шкали (незмінні)
GB = {
    'f_cost':     (float(df['now_cost'].min()),            float(df['now_cost'].max())),
    'f_matches':  (int(df['matches_played'].min()),        int(df['matches_played'].max())),
    'f_rating':   (r_min,                                  r_max),
    'f_avg_mins': (float(df['avg_mins'].min()),            float(df['avg_mins'].max())),
    'f_60min':    (float(df['60_min'].min()),              float(df['60_min'].max())),
    'f_selected': (float(df['selected_by_percent'].min()), float(df['selected_by_percent'].max())),
    'f_top10k':   (float(df['top_10k'].min()),             float(df['top_10k'].max())),
    'f_top100k':  (float(df['top_100k'].min()),            float(df['top_100k'].max())),
    'f_activity': (float(df['transfer_activity_pct'].min()), float(df['transfer_activity_pct'].max())),
}
# Дефолтні значення повзунків (нижня межа захищена)
DEFAULTS = {
    'f_cost':     GB['f_cost'],
    'f_matches':  (5,    GB['f_matches'][1]),
    'f_rating':   GB['f_rating'],
    'f_avg_mins': GB['f_avg_mins'],
    'f_60min':    (37.0, GB['f_60min'][1]),
    'f_selected': GB['f_selected'],
    'f_top10k':   GB['f_top10k'],
    'f_top100k':  GB['f_top100k'],
    'f_activity': (40.0, GB['f_activity'][1]),
}

# ========================== SESSION STATE ==========================
if 'pills_teams_form'  not in st.session_state: st.session_state.pills_teams_form  = default_teams
if 'pills_pos_form'    not in st.session_state: st.session_state.pills_pos_form    = [p for p in sorted_positions if p != 'GK']
if 'pills_pl_pos_form' not in st.session_state: st.session_state.pills_pl_pos_form = all_pl_pos


# ========================== ХЕЛПЕРИ ==========================
def _pills_snapshot():
    snap = {
        'pos':    tuple(sorted(st.session_state.get('pills_pos_form',   [p for p in sorted_positions if p != 'GK']) or [])),
        'teams':  tuple(sorted(st.session_state.get('pills_teams_form', default_teams) or [])),
        'search': st.session_state.get('search_name_form', ''),
    }
    for i, line in enumerate(pl_lines):
        avail = [p for p in line if p in actual_pl_pos]
        snap[f'pl_{i}'] = tuple(sorted(st.session_state.get(f'pills_pl_line_form_{i}', avail)))
    return snap

def _safe_range(key, default):
    val = st.session_state.get(key, default)
    if isinstance(val, (tuple, list)) and len(val) == 2:
        return val
    return default

def get_available(exclude_key=None):
    cv_pos      = st.session_state.get('pills_pos_form',   [p for p in sorted_positions if p != 'GK']) or []
    cv_teams    = st.session_state.get('pills_teams_form', default_teams) or []
    cv_matches  = _safe_range('f_matches_form',  DEFAULTS['f_matches'])
    cv_60min    = _safe_range('f_60min_form',    DEFAULTS['f_60min'])
    cv_cost     = _safe_range('f_cost_form',     DEFAULTS['f_cost'])
    cv_avg_mins = _safe_range('f_avg_mins_form', DEFAULTS['f_avg_mins'])
    cv_selected = _safe_range('f_selected_form', DEFAULTS['f_selected'])
    cv_top100k  = _safe_range('f_top100k_form',  DEFAULTS['f_top100k'])
    cv_activity = _safe_range('f_activity_form', DEFAULTS['f_activity'])
    cv_rating   = _safe_range('f_rating_form',   DEFAULTS['f_rating'])
    cv_search   = st.session_state.get('search_name_form', '')

    cv_pl_pos = []
    for i, line in enumerate(pl_lines):
        avail = [p for p in line if p in actual_pl_pos]
        cv_pl_pos.extend(st.session_state.get(f'pills_pl_line_form_{i}', avail))

    mask = pd.Series([True] * len(df), index=df.index)
    if exclude_key != 'pills_pos_form':   mask &= df['element_type'].isin(cv_pos)
    if exclude_key != 'pills_teams_form': mask &= df['team_short_name'].isin(cv_teams)
    if exclude_key != 'pills_pl_form':
        if cv_pl_pos:
            if len(cv_pl_pos) == len(all_pl_pos):
                mask &= (df['Play Pos'].isin(cv_pl_pos) | df['Play Pos'].isna())
            else:
                mask &= df['Play Pos'].isin(cv_pl_pos)
    if exclude_key != 'f_matches_form':
        mask &= (df['matches_played'] >= cv_matches[0]) & (df['matches_played'] <= cv_matches[1])
    if exclude_key != 'f_60min_form':
        mask &= (df['60_min'] >= cv_60min[0]) & (df['60_min'] <= cv_60min[1])
    if exclude_key != 'f_cost_form':
        mask &= (df['now_cost'] >= cv_cost[0]) & (df['now_cost'] <= cv_cost[1])
    if exclude_key != 'f_avg_mins_form':
        mask &= (df['avg_mins'] >= cv_avg_mins[0]) & (df['avg_mins'] <= cv_avg_mins[1])
    if exclude_key != 'f_selected_form':
        mask &= (df['selected_by_percent'] >= cv_selected[0]) & (df['selected_by_percent'] <= cv_selected[1])
    if exclude_key != 'f_top100k_form':
        mask &= (df['top_100k'] >= cv_top100k[0]) & (df['top_100k'] <= cv_top100k[1])
    if exclude_key != 'f_activity_form':
        mask &= (df['transfer_activity_pct'] >= cv_activity[0]) & (df['transfer_activity_pct'] <= cv_activity[1])
    if exclude_key != 'f_rating_form':
        mask &= (df[rating_col] >= cv_rating[0]) & (df[rating_col] <= cv_rating[1])
    if exclude_key != 'search_form':
        mask &= df['full_name'].str.contains(cv_search, case=False, na=False)
    return df[mask]

def get_base_df(exclude_key=None):
    cv_pos    = st.session_state.get('pills_pos_form',   [p for p in sorted_positions if p != 'GK']) or []
    cv_teams  = st.session_state.get('pills_teams_form', default_teams) or []
    cv_search = st.session_state.get('search_name_form', '')

    cv_pl_pos = []
    for i, line in enumerate(pl_lines):
        avail = [p for p in line if p in actual_pl_pos]
        cv_pl_pos.extend(st.session_state.get(f'pills_pl_line_form_{i}', avail))

    mask = (
        df['element_type'].isin(cv_pos) &
        df['team_short_name'].isin(cv_teams) &
        df['full_name'].str.contains(cv_search, case=False, na=False)
    )
    if cv_pl_pos:
        if len(cv_pl_pos) == len(all_pl_pos):
            mask &= (df['Play Pos'].isin(cv_pl_pos) | df['Play Pos'].isna())
        else:
            mask &= df['Play Pos'].isin(cv_pl_pos)

    _slider_cols = {
        'f_matches_form':  ('matches_played',      DEFAULTS['f_matches']),
        'f_60min_form':    ('60_min',              DEFAULTS['f_60min']),
        'f_cost_form':     ('now_cost',            DEFAULTS['f_cost']),
        'f_avg_mins_form': ('avg_mins',            DEFAULTS['f_avg_mins']),
        'f_selected_form': ('selected_by_percent', DEFAULTS['f_selected']),
        'f_top10k_form':   ('top_10k',             DEFAULTS['f_top10k']),
        'f_top100k_form':  ('top_100k',            DEFAULTS['f_top100k']),
        'f_activity_form': ('transfer_activity_pct', DEFAULTS['f_activity']),
        'f_rating_form':   (rating_col,            DEFAULTS['f_rating']),
    }
    for k, (col_name, d) in _slider_cols.items():
        if k != exclude_key:
            mask &= (df[col_name] >= d[0]) & (df[col_name] <= d[1])

    return df[mask]

def auto_update_slider(key, base_key, col, cast=float, only_positive=False):
    hash_key = f'_hash_{key}'
    current_hash = str(_pills_snapshot())
    prev_hash = st.session_state.get(hash_key)

    if prev_hash == current_hash and key in st.session_state:
        return

    series = get_base_df(key)[col].dropna()
    if only_positive:
        series = series[series > 0]

    if series.empty:
        st.session_state[hash_key] = current_hash
        if key not in st.session_state:
            st.session_state[key] = DEFAULTS[base_key]
        return

    avail_min = cast(series.min())
    avail_max = cast(series.max())
    def_lower = cast(DEFAULTS[base_key][0])
    gb_upper  = cast(GB[base_key][1])

    new_lower = max(def_lower, avail_min)
    new_upper = min(gb_upper, avail_max)

    if new_lower > new_upper:
        new_lower = def_lower
        new_upper = gb_upper

    st.session_state[key] = (new_lower, new_upper)
    st.session_state[hash_key] = current_hash

def filter_header(label, options, key_prefix):
    cols = st.sidebar.columns([1.4, 0.8, 0.8])
    cols[0].markdown(f"<p style='font-size:0.875rem;margin-bottom:0'>{label}</p>", unsafe_allow_html=True)
    if cols[1].button("All", key=f"btn_all_{key_prefix}", use_container_width=True):
        st.session_state[f"pills_{key_prefix}"] = options
        if key_prefix == "pl_pos_form":
            for i, line in enumerate(pl_lines):
                st.session_state[f"pills_pl_line_form_{i}"] = [p for p in options if p in line]
        st.rerun()
    if cols[2].button("None", key=f"btn_none_{key_prefix}", use_container_width=True):
        st.session_state[f"pills_{key_prefix}"] = []
        if key_prefix == "pl_pos_form":
            for i, line in enumerate(pl_lines):
                st.session_state[f"pills_pl_line_form_{i}"] = []
        st.rerun()

def inject_sidebar_layout(inactive_all: list):
    js = f"""
    <script>
    (function() {{
        var inactiveList = {json.dumps(inactive_all)};
        
        function forceLayout() {{
            try {{
                var doc = window.parent.document;
                var sidebar = doc.querySelector('[data-testid="stSidebar"]');
                if (!sidebar) return;
                
                var btns = sidebar.querySelectorAll('button');
                
                var plHeader = null;
                var ps = sidebar.querySelectorAll('p');
                ps.forEach(function(p) {{
                    if (p.innerText.trim() === 'Playing Position') {{ plHeader = p; }}
                }});
                var headerBottom = plHeader ? plHeader.getBoundingClientRect().bottom : 99999;
                
                btns.forEach(function(b) {{
                    var txt = b.innerText.trim();
                    if (!txt) return;
                    
                    if (txt === "Reset All Filters" || txt === "All" || txt === "None") return;
                    
                    var p = b.parentElement;
                    for (var i = 0; i < 3; i++) {{
                        if (p && p.tagName === 'DIV') {{
                            p.style.setProperty('display', 'flex', 'important');
                            p.style.setProperty('justify-content', 'center', 'important');
                            p.style.setProperty('flex-wrap', 'wrap', 'important');
                            p.style.setProperty('width', '100%', 'important');
                            p = p.parentElement;
                        }}
                    }}
                    
                    if (b.getBoundingClientRect().top > headerBottom) {{
                        b.style.setProperty('width', '48px', 'important');
                        b.style.setProperty('min-width', '48px', 'important');
                        b.style.setProperty('max-width', '48px', 'important');
                        
                        var stPills = b.closest('[data-testid="stPills"]');
                        if (stPills) {{
                            var wrapper = stPills.closest('.stElementContainer') || stPills.closest('[data-testid="stElementContainer"]');
                            if (wrapper && !wrapper.classList.contains('playing-pos-wrapper')) {{
                                wrapper.classList.add('playing-pos-wrapper');
                            }}
                        }}
                    }} else {{
                        b.style.setProperty('width', '60px', 'important');
                        b.style.setProperty('min-width', '60px', 'important');
                        b.style.setProperty('max-width', '60px', 'important');
                    }}
                    
                    var expectedOpacity = inactiveList.includes(txt) ? '0.3' : '';
                    if (b.style.opacity !== expectedOpacity) {{
                        b.style.opacity = expectedOpacity;
                    }}
                }});
            }} catch(e) {{}}
        }}
        
        setInterval(forceLayout, 300);
    }})();
    </script>
    """
    st.components.v1.html(js, height=0, scrolling=False)

# ========================== АВТОоновлення СЛАЙДЕРІВ ==========================
auto_update_slider('f_cost_form',     'f_cost',     'now_cost',            float)
auto_update_slider('f_matches_form',  'f_matches',  'matches_played',      int)
auto_update_slider('f_rating_form',   'f_rating',   rating_col,            float, only_positive=True)
auto_update_slider('f_avg_mins_form', 'f_avg_mins', 'avg_mins',            float)
auto_update_slider('f_60min_form',    'f_60min',    '60_min',              float)
auto_update_slider('f_selected_form', 'f_selected', 'selected_by_percent', float)
auto_update_slider('f_top10k_form',   'f_top10k',   'top_10k',             float)
auto_update_slider('f_top100k_form',  'f_top100k',  'top_100k',            float)
auto_update_slider('f_activity_form', 'f_activity', 'transfer_activity_pct', float)

# ========================== САЙДБАР ==========================
if st.sidebar.button("Reset All Filters", use_container_width=True, type="primary"):
    keys_to_delete = [k for k in st.session_state.keys() if '_form' in k]
    for key in keys_to_delete:
        del st.session_state[key]
    st.rerun()

search_name = st.sidebar.text_input("Search Player", placeholder="Enter name...", key="search_name_form")

# --- 1. FPL POSITION ---
avail_pos = set(get_available('pills_pos_form')['element_type'].unique())
filter_header("FPL Position", sorted_positions, "pos_form")
selected_positions = st.sidebar.pills(
    "FPL Position", options=sorted_positions, key="pills_pos_form",
    selection_mode="multi", label_visibility="collapsed"
)

# --- 2. FPL PRICE ---
f_cost = st.sidebar.slider(
    "FPL Price", GB['f_cost'][0], GB['f_cost'][1], step=0.1, format="%.1f", key="f_cost_form"
)

# --- 3. TEAM ---
avail_teams = set(get_available('pills_teams_form')['team_short_name'].unique())
filter_header("Team", all_teams, "teams_form")
selected_teams = st.sidebar.pills(
    "Team", options=all_teams, key="pills_teams_form",
    selection_mode="multi", label_visibility="collapsed"
)

# --- 4. PLAYING POSITION ---
avail_pl = set(get_available('pills_pl_form')['Play Pos'].dropna().unique())
filter_header("Playing Position", all_pl_pos, "pl_pos_form")
selected_pl_pos = []

for idx, line in enumerate(pl_lines):
    available_in_line = [p for p in line if p in actual_pl_pos]
    if not available_in_line:
        continue
    line_key = f"pills_pl_line_form_{idx}"
    if line_key not in st.session_state:
        st.session_state[line_key] = [p for p in st.session_state.pills_pl_pos_form if p in available_in_line]

    line_res = st.sidebar.pills(
        label=f"pl_line_{idx}", options=available_in_line, key=line_key,
        selection_mode="multi", label_visibility="collapsed"
    )
    if line_res:
        selected_pl_pos.extend(line_res)

# --- ЗБІР УСІХ НЕАКТИВНИХ ОПЦІЙ ДЛЯ JS ---
all_inactive = []
all_inactive.extend([p for p in sorted_positions if p not in avail_pos])
all_inactive.extend([t for t in all_teams if t not in avail_teams])
all_inactive.extend([p for p in all_pl_pos if p not in avail_pl])

inject_sidebar_layout(all_inactive)

# --- PERFORMANCE STATS ---
with st.sidebar.expander("Performance Stats", expanded=False):
    f_matches  = st.slider("Matches",      GB['f_matches'][0],  GB['f_matches'][1],  value=_safe_range('f_matches_form',  DEFAULTS['f_matches']),  step=1,    key="f_matches_form")
    f_rating   = st.slider("Rating (L10)", GB['f_rating'][0],   GB['f_rating'][1],   value=_safe_range('f_rating_form',   DEFAULTS['f_rating']),   step=0.05, format="%.2f", key="f_rating_form")
    f_avg_mins = st.slider("Average Mins", GB['f_avg_mins'][0], GB['f_avg_mins'][1], value=_safe_range('f_avg_mins_form', DEFAULTS['f_avg_mins']), step=1.0,  key="f_avg_mins_form")
    f_60min    = st.slider("60 Min %",     GB['f_60min'][0],    GB['f_60min'][1],    value=_safe_range('f_60min_form',    DEFAULTS['f_60min']),    step=0.5,  key="f_60min_form")

# --- MARKET & POPULARITY ---
with st.sidebar.expander("Market & Popularity", expanded=False):
    f_selected = st.slider("Selected %",  GB['f_selected'][0], GB['f_selected'][1], value=_safe_range('f_selected_form', DEFAULTS['f_selected']), step=0.1, key="f_selected_form")
    f_top10k   = st.slider("Top 10k %",  GB['f_top10k'][0],   GB['f_top10k'][1],   value=_safe_range('f_top10k_form',   DEFAULTS['f_top10k']),   step=0.1, key="f_top10k_form")
    f_top100k  = st.slider("Top 100k %", GB['f_top100k'][0],  GB['f_top100k'][1],  value=_safe_range('f_top100k_form',  DEFAULTS['f_top100k']),  step=0.1, key="f_top100k_form")
    f_activity = st.slider("Transfer Activity", GB['f_activity'][0], GB['f_activity'][1], value=_safe_range('f_activity_form', DEFAULTS['f_activity']), step=1.0, format="%d%%", key="f_activity_form")

# --- LEAGUE ORIGIN FILTER ---
if 'league_status' not in df.columns:
    df['league_status'] = "Premier League"

selected_league_origin = st.sidebar.pills(
    "League Origin",
    options=["All", "Premier League", "Other Leagues"],
    default="All",
    key="pills_league_origin_form",
    label_visibility="collapsed"
)

# ========================== ЗАСТОСУВАННЯ ФІЛЬТРІВ ==========================
if selected_pl_pos and len(selected_pl_pos) == len(all_pl_pos):
    play_pos_mask = df['Play Pos'].isin(selected_pl_pos) | df['Play Pos'].isna()
else:
    play_pos_mask = df['Play Pos'].isin(selected_pl_pos if selected_pl_pos else [])

if selected_league_origin == "Premier League":
    league_mask = (df['league_status'] == "Premier League")
elif selected_league_origin == "Other Leagues":
    league_mask = (df['league_status'] == "Other Leagues")
else:
    league_mask = pd.Series([True] * len(df), index=df.index)

mask = (
    df['element_type'].isin(selected_positions if selected_positions else []) &
    df['team_short_name'].isin(selected_teams  if selected_teams  else []) &
    play_pos_mask &
    league_mask &
    (df[rating_col]            >= f_rating[0])   & (df[rating_col]            <= f_rating[1]) &
    (df['matches_played']      >= f_matches[0])  & (df['matches_played']      <= f_matches[1]) &
    (df['60_min']              >= f_60min[0])    & (df['60_min']              <= f_60min[1]) &
    (df['now_cost']            >= f_cost[0])     & (df['now_cost']            <= f_cost[1]) &
    (df['selected_by_percent'] >= f_selected[0]) & (df['selected_by_percent'] <= f_selected[1]) &
    (df['top_10k']             >= f_top10k[0])   & (df['top_10k']             <= f_top10k[1]) &
    (df['top_100k']            >= f_top100k[0])  & (df['top_100k']            <= f_top100k[1]) &
    (df['transfer_activity_pct'] >= f_activity[0]) & (df['transfer_activity_pct'] <= f_activity[1]) &
    (df['avg_mins']            >= f_avg_mins[0]) & (df['avg_mins']            <= f_avg_mins[1]) &
    (df['full_name'].str.contains(search_name, case=False, na=False))
)
plot_df = df[mask].copy()

# ========================== ЛОГІКА РОЗМІРУ (ПРОЦЕНТИЛІ) ==========================
if not plot_df.empty:
    plot_df['p_top100k'] = plot_df['top_100k'].rank(pct=True)
    plot_df['p_avgmins'] = plot_df['avg_mins'].rank(pct=True)
    
    plot_df['combined_rank'] = (plot_df['p_top100k'] + plot_df['p_avgmins']) / 2
    # Підносимо до квадрату, щоб створити експоненційну різницю між мінімумом і максимумом
    plot_df['size_for_plot'] = (plot_df['combined_rank'] ** 2) * 100 + 10

    # Використовуємо квадратний корінь замість логарифма для більш помірного розтягування (вдвічі слабшого)
    plot_df['rating_sqrt'] = plot_df[rating_col] ** 0.5
    plot_df['xGI_sqrt'] = plot_df[xgi_col] ** 0.5

    min_mins_for_label = 60
    plot_df['label_text'] = np.where(
        (plot_df['avg_mins'] >= min_mins_for_label) | (plot_df['top_100k'] > 7.0),
        plot_df['web_name'],
        ""
    )

    # ========================== ВІЗУАЛІЗАЦІЯ ==========================
    st.subheader(f"xGI vs Rating - Last 10 Games (Players: {len(plot_df)})")

    fig = px.scatter(
        plot_df,
        x="rating_sqrt",
        y="xGI_sqrt",
        color="element_type",
        symbol="league_status",
        symbol_map={"Premier League": "circle", "Other Leagues": "diamond"},
        size="size_for_plot",
        hover_name="full_name",
        hover_data={
            "element_type": True,
            "team_short_name": True,
            "league_status": True,
            "now_cost": ":.1f",
            rating_col: ":.2f",
            xgi_col: ":.2f",
            "avg_mins": ":.0f",
            "top_100k": ":.1f",
            "web_name": False,
            "matches_played": False,
            "size_for_plot": False,
            "combined_rank": False,
            "rating_sqrt": False,
            "xGI_sqrt": False,
            "label_text": False
        },
        text="label_text",
        labels={
            "rating_sqrt": "Average Rating (L10)",
            "xGI_sqrt": "Expected Goal Involvement (L10)",
            "element_type": "Position",
            "team_short_name": "Team",
            "league_status": "League Origin",
            "now_cost": "Price",
            rating_col: "Rating (L10)",
            xgi_col: "xGI (L10)",
            "avg_mins": "Avg Mins",
            "top_100k": "Top 100K %"
        },
        template="plotly_dark",
        size_max=20
    )

    fig.update_traces(
        textposition='bottom center',
        textfont=dict(
            size=10
        ),
        marker=dict(
            opacity=0.75,
            line=dict(width=0.8, color='white')
        )
    )

    # Динамічні сітки для перетворених шкал (кожні 0.1)
    r_min, r_max = plot_df[rating_col].min(), plot_df[rating_col].max()
    if pd.isna(r_min) or pd.isna(r_max):
        r_min, r_max = 4.0, 10.0
    r_start = np.floor(r_min * 10) / 10
    r_end = np.ceil(r_max * 10) / 10
    r_ticks = np.arange(r_start, r_end + 0.05, 0.1).round(1)
            
    x_min, x_max = plot_df[xgi_col].min(), plot_df[xgi_col].max()
    if pd.isna(x_min) or pd.isna(x_max):
        x_min, x_max = 0.0, 1.5
    x_start = np.floor(x_min * 10) / 10
    x_end = np.ceil(x_max * 10) / 10
    x_ticks = np.arange(x_start, x_end + 0.05, 0.1).round(1)

    fig.update_layout(
        height=800,
        margin=dict(l=0, r=0, t=40, b=0),
        xaxis=dict(
            title="Average Rating (Last 10 Games)",
            gridcolor='rgba(255,255,255,0.1)',
            tickmode='array',
            tickvals=r_ticks ** 0.5,
            ticktext=r_ticks
        ),
        yaxis=dict(
            title="Expected Goal Involvement (Last 10 Games)",
            gridcolor='rgba(255,255,255,0.1)',
            tickmode='array',
            tickvals=x_ticks ** 0.5,
            ticktext=x_ticks
        ),
        legend_title_text='', 
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(0,0,0,0.5)"
        )
    )

    st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("Немає даних для обраних фільтрів.")
