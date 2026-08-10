import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import json

st.set_page_config(
    page_title="FPL Players Form",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS для відцентрування заголовків та даних, стилізації сайдбару та компактності
st.markdown("""
    <style>
        html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stDataFrame"] {
            overscroll-behavior: none !important;
        }
        [data-testid="stHeaderActionElements"], a.header-anchor {
            display: none !important;
        }
        .block-container {
            padding-top: 1.5rem !important;
            padding-bottom: 1rem !important;
            max-width: 100% !important;
        }
        [data-testid="stTable"] th, [data-testid="stDataFrame"] th {
            text-align: center !important;
        }
        [data-testid="stDataFrame"] td {
            text-align: center !important;
        }
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

        .playing-pos-wrapper button {
            width: 48px !important; min-width: 48px !important; max-width: 48px !important;
        }
    </style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)
def load_data():
    url = "http://194.99.22.193:8000/fpl_players"
    df = pd.read_parquet(url)

    pct_cols = [
        'min_played_1y', 'min_played_3y',
        'pct_goals_1y', 'pct_goals_3y',
        'pct_assists_1y', 'pct_assists_3y',
        'pct_xg_1y', 'pct_xg_3y',
        'pct_xgot_1y', 'pct_xgot_3y',
        'pct_xa_1y', 'pct_xa_3y',
        'pct_shots_1y', 'pct_shots_3y',
        'pct_clearances_1y', 'pct_clearances_3y',
        'pct_blocks_1y', 'pct_blocks_3y',
        'pct_interceptions_1y', 'pct_interceptions_3y',
        'pct_tackles_1y', 'pct_tackles_3y',
        'pct_recoveries_1y', 'pct_recoveries_3y'
    ]

    for col in pct_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
        else:
            df[col] = 0.0

    if 'av_rating_alt' in df.columns:
        df['av_rating_alt'] = pd.to_numeric(df['av_rating_alt'], errors='coerce').fillna(0.0)

    sort_cols = [c for c in ['now_cost', 'M Price'] if c in df.columns]
    if sort_cols:
        df = df.sort_values(by=sort_cols, ascending=[False] * len(sort_cols))
    
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
pos_order = ['GK', 'DEF', 'MID', 'FW']
actual_pos = df['element_type'].unique().tolist()
sorted_positions = [p for p in pos_order if p in actual_pos] + sorted([p for p in actual_pos if p not in pos_order])

pl_lines = [['GK'], ['RB', 'CB', 'LB'], ['RM', 'DM', 'CM', 'LM'], ['RW', 'AM', 'LW'], ['SS', 'CF']]
defined_pl_pos = [p for line in pl_lines for p in line]
actual_pl_pos = df['Play Pos'].dropna().unique().tolist()
others = sorted([p for p in actual_pl_pos if p not in defined_pl_pos])
if others: pl_lines.append(others)
all_pl_pos = [p for line in pl_lines for p in line if p in actual_pl_pos]

def _slider_bounds(min_val, max_val, default_span=1.0):
    mn = float(min_val)
    mx = float(max_val)
    if mn >= mx:
        mx = mn + default_span
    return (mn, mx)

def _get_max(col, default=1.0): return float(df[col].max()) if col in df.columns else default
def _get_min(col, default=0.0): return float(df[col].min()) if col in df.columns else default

if 'matches_played' in df.columns and '60_min' in df.columns:
    sane_df = df[(df['matches_played'] >= 5) & (df['60_min'] >= 40.5)]
else:
    sane_df = df

def _get_max_sane(col, default=1.0):
    return float(sane_df[col].max()) if (col in sane_df.columns and not sane_df.empty) else _get_max(col, default)

def _get_min_sane(col, default=0.0):
    return float(sane_df[col].min()) if (col in sane_df.columns and not sane_df.empty) else _get_min(col, default)

rating_series = df[df['av_rating_alt'] > 0]['av_rating_alt'].dropna() if 'av_rating_alt' in df.columns else pd.Series(dtype=float)
r_min = float(rating_series.min()) if not rating_series.empty else 0.0
r_max = float(rating_series.max()) if not rating_series.empty else 10.0

# Глобальні межі шкали (незмінні)
GB = {
    'f_cost_form':     _slider_bounds(_get_min('now_cost', 4.0), _get_max('now_cost', 15.0)),
    'f_matches_form':  (int(_get_min('matches_played', 0)), max(int(_get_max('matches_played', 38)), int(_get_min('matches_played', 0)) + 1)),
    'f_rating_form':   _slider_bounds(r_min, r_max),
    'f_mins1y_form':   _slider_bounds(_get_min('min_played_1y'), _get_max('min_played_1y', 4000.0)),
    'f_mins3y_form':   _slider_bounds(_get_min('min_played_3y'), _get_max('min_played_3y', 12000.0)),
    'f_selected_form': _slider_bounds(_get_min('selected_by_percent'), _get_max('selected_by_percent', 100.0)),
    'f_activity_form': _slider_bounds(0.0, 100.0),
    'f_g1y_form':      _slider_bounds(0.0, _get_max_sane('pct_goals_1y')),
    'f_xg1y_form':     _slider_bounds(0.0, _get_max_sane('pct_xg_1y')),
    'f_a1y_form':      _slider_bounds(0.0, _get_max_sane('pct_assists_1y')),
    'f_xa1y_form':     _slider_bounds(0.0, _get_max_sane('pct_xa_1y')),
    'f_g3y_form':      _slider_bounds(0.0, _get_max_sane('pct_goals_3y')),
    'f_xg3y_form':     _slider_bounds(0.0, _get_max_sane('pct_xg_3y')),
    'f_a3y_form':      _slider_bounds(0.0, _get_max_sane('pct_assists_3y')),
    'f_xa3y_form':     _slider_bounds(0.0, _get_max_sane('pct_xa_3y')),
}

# Дефолтні значення повзунків
DEFAULTS = {
    'f_cost_form':     GB['f_cost_form'],
    'f_matches_form':  GB['f_matches_form'],
    'f_rating_form':   GB['f_rating_form'],
    'f_mins1y_form':   GB['f_mins1y_form'],
    'f_mins3y_form':   GB['f_mins3y_form'],
    'f_selected_form': GB['f_selected_form'],
    'f_activity_form': GB['f_activity_form'],
    'f_g1y_form':      GB['f_g1y_form'],
    'f_xg1y_form':     GB['f_xg1y_form'],
    'f_a1y_form':      GB['f_a1y_form'],
    'f_xa1y_form':     GB['f_xa1y_form'],
    'f_g3y_form':      GB['f_g3y_form'],
    'f_xg3y_form':     GB['f_xg3y_form'],
    'f_a3y_form':      GB['f_a3y_form'],
    'f_xa3y_form':     GB['f_xa3y_form'],
}

# ========================== SESSION STATE ==========================
if 'pills_teams_form'  not in st.session_state: st.session_state.pills_teams_form  = all_teams
if 'pills_pos_form'    not in st.session_state: st.session_state.pills_pos_form    = [p for p in sorted_positions if p != 'GK']
if 'pills_pl_pos_form' not in st.session_state: st.session_state.pills_pl_pos_form = all_pl_pos

# ========================== ХЕЛПЕРИ ==========================
def _pills_snapshot():
    snap = {
        'pos':    tuple(sorted(st.session_state.get('pills_pos_form',   [p for p in sorted_positions if p != 'GK']) or [])),
        'teams':  tuple(sorted(st.session_state.get('pills_teams_form', all_teams) or [])),
        'search': st.session_state.get('search_name_form', ''),
    }
    for i, line in enumerate(pl_lines):
        avail = [p for p in line if p in actual_pl_pos]
        snap[f'pl_{i}'] = tuple(sorted(st.session_state.get(f'pills_pl_line_form_{i}', avail)))
    return snap

def _safe_range(key, default):
    val = st.session_state.get(key, default)
    if isinstance(val, (tuple, list)) and len(val) == 2:
        if val[0] < val[1]:
            return val
    return default

def get_available(exclude_key=None):
    """Повертає підмножину df за всіма фільтрами, крім exclude_key."""
    cv_pos      = st.session_state.get('pills_pos_form',   [p for p in sorted_positions if p != 'GK']) or []
    cv_teams    = st.session_state.get('pills_teams_form', all_teams) or []
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
    if exclude_key != 'search_name_form': mask &= df['full_name'].str.contains(cv_search, case=False, na=False)

    _slider_cols = {
        'f_matches_form':  ('matches_played',        DEFAULTS['f_matches_form']),
        'f_mins1y_form':   ('min_played_1y',         DEFAULTS['f_mins1y_form']),
        'f_mins3y_form':   ('min_played_3y',         DEFAULTS['f_mins3y_form']),
        'f_cost_form':     ('now_cost',              DEFAULTS['f_cost_form']),
        'f_rating_form':   ('av_rating_alt',         DEFAULTS['f_rating_form']),
        'f_selected_form': ('selected_by_percent',   DEFAULTS['f_selected_form']),
        'f_activity_form': ('transfer_activity_pct', DEFAULTS['f_activity_form']),
        'f_g1y_form':      ('pct_goals_1y',          DEFAULTS['f_g1y_form']),
        'f_xg1y_form':     ('pct_xg_1y',             DEFAULTS['f_xg1y_form']),
        'f_a1y_form':      ('pct_assists_1y',        DEFAULTS['f_a1y_form']),
        'f_xa1y_form':     ('pct_xa_1y',             DEFAULTS['f_xa1y_form']),
        'f_g3y_form':      ('pct_goals_3y',          DEFAULTS['f_g3y_form']),
        'f_xg3y_form':     ('pct_xg_3y',             DEFAULTS['f_xg3y_form']),
        'f_a3y_form':      ('pct_assists_3y',        DEFAULTS['f_a3y_form']),
        'f_xa3y_form':     ('pct_xa_3y',             DEFAULTS['f_xa3y_form']),
    }
    for k, (col_name, d) in _slider_cols.items():
        if k != exclude_key and col_name in df.columns:
            val = _safe_range(k, d)
            if val[0] > GB[k][0] + 1e-4:
                mask &= (df[col_name] >= val[0])
            if val[1] < GB[k][1] - 1e-4:
                mask &= (df[col_name] <= val[1])

    return df[mask]

def get_base_df(exclude_key=None):
    """Базовий набір даних для розрахунку діапазонів слайдерів."""
    cv_pos    = st.session_state.get('pills_pos_form',   [p for p in sorted_positions if p != 'GK']) or []
    cv_teams  = st.session_state.get('pills_teams_form', all_teams) or []
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
        'f_matches_form':  ('matches_played',        DEFAULTS['f_matches_form']),
        'f_mins1y_form':   ('min_played_1y',         DEFAULTS['f_mins1y_form']),
        'f_mins3y_form':   ('min_played_3y',         DEFAULTS['f_mins3y_form']),
        'f_cost_form':     ('now_cost',              DEFAULTS['f_cost_form']),
        'f_rating_form':   ('av_rating_alt',         DEFAULTS['f_rating_form']),
        'f_selected_form': ('selected_by_percent',   DEFAULTS['f_selected_form']),
        'f_activity_form': ('transfer_activity_pct', DEFAULTS['f_activity_form']),
        'f_g1y_form':      ('pct_goals_1y',          DEFAULTS['f_g1y_form']),
        'f_xg1y_form':     ('pct_xg_1y',             DEFAULTS['f_xg1y_form']),
        'f_a1y_form':      ('pct_assists_1y',        DEFAULTS['f_a1y_form']),
        'f_xa1y_form':     ('pct_xa_1y',             DEFAULTS['f_xa1y_form']),
        'f_g3y_form':      ('pct_goals_3y',          DEFAULTS['f_g3y_form']),
        'f_xg3y_form':     ('pct_xg_3y',             DEFAULTS['f_xg3y_form']),
        'f_a3y_form':      ('pct_assists_3y',        DEFAULTS['f_a3y_form']),
        'f_xa3y_form':     ('pct_xa_3y',             DEFAULTS['f_xa3y_form']),
    }
    for k, (col_name, d) in _slider_cols.items():
        if k != exclude_key and col_name in df.columns:
            mask &= (df[col_name] >= d[0]) & (df[col_name] <= d[1])

    return df[mask]

def auto_update_slider(key, col, cast=float, only_positive=False):
    if col not in df.columns or key not in DEFAULTS:
        return
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
            st.session_state[key] = DEFAULTS[key]
        return

    avail_min = cast(series.min())
    avail_max = cast(series.max())
    def_lower = cast(DEFAULTS[key][0])
    gb_upper  = cast(GB[key][1])

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
    if cols[1].button("All", key=f"btn_all_{key_prefix}", width="stretch"):
        st.session_state[f"pills_{key_prefix}"] = options
        if key_prefix == "pl_pos_form":
            for i, line in enumerate(pl_lines):
                st.session_state[f"pills_pl_line_form_{i}"] = [p for p in options if p in line]
        st.rerun()
    if cols[2].button("None", key=f"btn_none_{key_prefix}", width="stretch"):
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
                var buttons = window.parent.document.querySelectorAll('[data-testid="stSidebar"] button');
                buttons.forEach(function(b) {{
                    var txt = b.innerText.trim();
                    if (txt === "All" || txt === "None" || txt === "Reset All Filters") return;
                    if (txt.length === 2 && ["GK", "RB", "CB", "LB", "RM", "DM", "CM", "LM", "RW", "AM", "LW", "SS", "CF"].includes(txt)) {{
                        b.classList.add('playing-pos-button');
                        b.parentElement.classList.add('playing-pos-wrapper');
                        b.style.setProperty('width', '48px', 'important');
                        b.style.setProperty('min-width', '48px', 'important');
                        b.style.setProperty('max-width', '48px', 'important');
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
auto_update_slider('f_cost_form',     'now_cost',            float)
auto_update_slider('f_matches_form',  'matches_played',      int)
auto_update_slider('f_rating_form',   'av_rating_alt',       float, only_positive=True)
auto_update_slider('f_mins1y_form',   'min_played_1y',       float)
auto_update_slider('f_mins3y_form',   'min_played_3y',       float)
auto_update_slider('f_selected_form', 'selected_by_percent', float)
auto_update_slider('f_activity_form', 'transfer_activity_pct', float)
auto_update_slider('f_g1y_form',      'pct_goals_1y',        float)
auto_update_slider('f_xg1y_form',     'pct_xg_1y',           float)
auto_update_slider('f_a1y_form',      'pct_assists_1y',      float)
auto_update_slider('f_xa1y_form',     'pct_xa_1y',           float)
auto_update_slider('f_g3y_form',      'pct_goals_3y',        float)
auto_update_slider('f_xg3y_form',     'pct_xg_3y',           float)
auto_update_slider('f_a3y_form',      'pct_assists_3y',      float)
auto_update_slider('f_xa3y_form',     'pct_xa_3y',           float)

# ========================== САЙДБАР ==========================
if st.sidebar.button("Reset All Filters", width="stretch", type="primary"):
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
    "FPL Price", GB['f_cost_form'][0], GB['f_cost_form'][1], step=0.1, format="%.1f", key="f_cost_form"
)

# --- 3. TEAM ---
avail_teams = set(get_available('pills_teams_form')['team_short_name'].unique())
filter_header("Team", all_teams, "teams_form")
selected_teams = st.sidebar.pills(
    "Team", options=all_teams, key="pills_teams_form",
    selection_mode="multi", label_visibility="collapsed"
)

# --- 4. PLAYING POSITION ---
avail_pl = set(get_available('pills_pl_form')['Play Pos'].dropna().unique()) if 'Play Pos' in df.columns else set()
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
    f_matches = st.slider("Matches", GB['f_matches_form'][0], GB['f_matches_form'][1], step=1, key="f_matches_form")
    f_mins1y  = st.slider("Mins 1y",  GB['f_mins1y_form'][0],  GB['f_mins1y_form'][1],  step=50.0, key="f_mins1y_form")
    f_mins3y  = st.slider("Mins 3y",  GB['f_mins3y_form'][0],  GB['f_mins3y_form'][1],  step=100.0, key="f_mins3y_form")

# --- MARKET & POPULARITY ---
with st.sidebar.expander("Market & Popularity", expanded=False):
    f_selected = st.slider("Selected %",        GB['f_selected_form'][0], GB['f_selected_form'][1], step=0.1, key="f_selected_form")
    f_activity = st.slider("Transfer Activity", GB['f_activity_form'][0], GB['f_activity_form'][1], step=1.0, format="%d%%", key="f_activity_form")

# --- 1-YEAR PERCENTAGES ---
with st.sidebar.expander("1-Year Percentages", expanded=True):
    f_g1y  = st.slider("G 1y %",  GB['f_g1y_form'][0],  GB['f_g1y_form'][1],  step=0.5, format="%.1f%%", key="f_g1y_form")
    f_xg1y = st.slider("xG 1y %", GB['f_xg1y_form'][0], GB['f_xg1y_form'][1], step=0.5, format="%.1f%%", key="f_xg1y_form")
    f_a1y  = st.slider("A 1y %",  GB['f_a1y_form'][0],  GB['f_a1y_form'][1],  step=0.5, format="%.1f%%", key="f_a1y_form")
    f_xa1y = st.slider("xA 1y %", GB['f_xa1y_form'][0], GB['f_xa1y_form'][1], step=0.5, format="%.1f%%", key="f_xa1y_form")

# --- 3-YEAR PERCENTAGES ---
with st.sidebar.expander("3-Year Percentages", expanded=False):
    f_g3y  = st.slider("G 3y %",  GB['f_g3y_form'][0],  GB['f_g3y_form'][1],  step=0.5, format="%.1f%%", key="f_g3y_form")
    f_xg3y = st.slider("xG 3y %", GB['f_xg3y_form'][0], GB['f_xg3y_form'][1], step=0.5, format="%.1f%%", key="f_xg3y_form")
    f_a3y  = st.slider("A 3y %",  GB['f_a3y_form'][0],  GB['f_a3y_form'][1],  step=0.5, format="%.1f%%", key="f_a3y_form")
    f_xa3y = st.slider("xA 3y %", GB['f_xa3y_form'][0], GB['f_xa3y_form'][1], step=0.5, format="%.1f%%", key="f_xa3y_form")

# ========================== ЗАСТОСУВАННЯ ФІЛЬТРІВ ==========================
if selected_pl_pos and len(selected_pl_pos) == len(all_pl_pos):
    play_pos_mask = df['Play Pos'].isin(selected_pl_pos) | df['Play Pos'].isna()
else:
    play_pos_mask = df['Play Pos'].isin(selected_pl_pos if selected_pl_pos else [])

mask = (
    df['element_type'].isin(selected_positions if selected_positions else []) &
    df['team_short_name'].isin(selected_teams  if selected_teams  else []) &
    play_pos_mask &
    (df['full_name'].str.contains(search_name, case=False, na=False))
)

filter_vars = [
    ('matches_played',        f_matches,  GB['f_matches_form']),
    ('min_played_1y',         f_mins1y,   GB['f_mins1y_form']),
    ('min_played_3y',         f_mins3y,   GB['f_mins3y_form']),
    ('now_cost',              f_cost,     GB['f_cost_form']),
    ('selected_by_percent',   f_selected, GB['f_selected_form']),
    ('transfer_activity_pct', f_activity, GB['f_activity_form']),
    ('pct_goals_1y',          f_g1y,      GB['f_g1y_form']),
    ('pct_xg_1y',             f_xg1y,     GB['f_xg1y_form']),
    ('pct_assists_1y',        f_a1y,      GB['f_a1y_form']),
    ('pct_xa_1y',             f_xa1y,     GB['f_xa1y_form']),
    ('pct_goals_3y',          f_g3y,      GB['f_g3y_form']),
    ('pct_xg_3y',             f_xg3y,     GB['f_xg3y_form']),
    ('pct_assists_3y',        f_a3y,      GB['f_a3y_form']),
    ('pct_xa_3y',             f_xa3y,     GB['f_xa3y_form']),
]

for col_name, val, limit in filter_vars:
    if col_name in df.columns:
        if val[0] > limit[0] + 1e-4:
            mask &= (df[col_name] >= val[0])
        if val[1] < limit[1] - 1e-4:
            mask &= (df[col_name] <= val[1])

filtered_df = df[mask].copy()
sort_cols = [c for c in ['now_cost', 'M Price'] if c in filtered_df.columns]
if sort_cols:
    filtered_df = filtered_df.sort_values(by=sort_cols, ascending=[False] * len(sort_cols))

# ========================== СТИЛІЗАЦІЯ ТА ВІДОБРАЖЕННЯ ==========================
display_columns = [
    "full_name", "Age", "element_type", "Play Pos", "team_short_name", "now_cost", "M Price", "selected_by_percent",
    "min_played_1y", "pct_mins_avail_1y", "pct_goals_1y", "pct_xg_1y", "pct_xgot_1y", "pct_assists_1y", "pct_xa_1y", "pct_shots_1y", "pct_bcc_1y",
    "pct_clearances_1y", "pct_blocks_1y", "pct_interceptions_1y", "pct_tackles_1y", "pct_recoveries_1y",
    "min_played_3y", "pct_mins_avail_3y", "pct_goals_3y", "pct_xg_3y", "pct_xgot_3y", "pct_assists_3y", "pct_xa_3y", "pct_shots_3y", "pct_bcc_3y",
    "pct_clearances_3y", "pct_blocks_3y", "pct_interceptions_3y", "pct_tackles_3y", "pct_recoveries_3y"
]

existing_cols = [c for c in display_columns if c in filtered_df.columns]

def soft_gradient(s, cmap_name='Blues', alpha=0.25, max_cap=None, reverse=False):
    if s.empty:
        return ['' for _ in s]
    s_min, s_max = s.min(), s.max()
    if max_cap is not None and not pd.isna(s_max):
        s_max = min(s_max, max_cap)
    if pd.isna(s_min) or pd.isna(s_max) or s_min >= s_max:
        return ['' for _ in s]
    
    cmap = plt.get_cmap(cmap_name)
    norm = mcolors.Normalize(vmin=s_min, vmax=s_max)
    
    styles = []
    for val in s:
        if pd.isna(val):
            styles.append('')
        else:
            val_clamped = min(val, s_max) if max_cap is not None else val
            norm_val = norm(val_clamped)
            if reverse:
                norm_val = 1.0 - norm_val
            r, g, b, _ = cmap(norm_val)
            styles.append(f'background-color: rgba({int(r*255)}, {int(g*255)}, {int(b*255)}, {alpha})')
    return styles

styled_df = filtered_df[existing_cols].style \
    .apply(soft_gradient, cmap_name='YlGn', alpha=0.25, subset=[c for c in ['pct_mins_avail_1y', 'pct_goals_1y', 'pct_xg_1y', 'pct_xgot_1y', 'pct_assists_1y', 'pct_xa_1y', 'pct_mins_avail_3y', 'pct_goals_3y', 'pct_xg_3y', 'pct_xgot_3y', 'pct_assists_3y', 'pct_xa_3y'] if c in existing_cols]) \
    .apply(soft_gradient, cmap_name='Blues', alpha=0.25, subset=[c for c in ['pct_shots_1y', 'pct_bcc_1y', 'pct_clearances_1y', 'pct_blocks_1y', 'pct_interceptions_1y', 'pct_tackles_1y', 'pct_recoveries_1y', 'pct_shots_3y', 'pct_bcc_3y', 'pct_clearances_3y', 'pct_blocks_3y', 'pct_interceptions_3y', 'pct_tackles_3y', 'pct_recoveries_3y'] if c in existing_cols])

st.subheader(f"FPL Players Form: {len(filtered_df)} players", anchor=False)

st.dataframe(
    styled_df,
    width="stretch",
    hide_index=True,
    height=800,
    column_config={
        "full_name":            st.column_config.TextColumn("Player",        width="medium", pinned=True),
        "Age":                  st.column_config.NumberColumn("Age",         width=35,  format="%d"),
        "element_type":         st.column_config.TextColumn("Pos",           width=40),
        "Play Pos":             st.column_config.TextColumn("Pl Pos",        width=40),
        "team_short_name":      st.column_config.TextColumn("Team",          width=40),
        "now_cost":             st.column_config.NumberColumn("Price",       width=40,  format="%.1f"),
        "M Price":              st.column_config.NumberColumn("TM Price",    width=50,  format="%.1f"),
        "selected_by_percent":  st.column_config.NumberColumn("Selected",    width=55,  format="%.1f%%"),
        "min_played_1y":        st.column_config.NumberColumn("Mins 1y",     width=45,  format="%d"),
        "pct_mins_avail_1y":    st.column_config.NumberColumn("Avail 1y",    width=48,  format="%.1f"),
        "pct_goals_1y":         st.column_config.NumberColumn("G 1y",        width=40,  format="%.1f"),
        "pct_xg_1y":            st.column_config.NumberColumn("xG 1y",       width=40,  format="%.1f"),
        "pct_xgot_1y":          st.column_config.NumberColumn("xGOT 1y",     width=48,  format="%.1f"),
        "pct_assists_1y":       st.column_config.NumberColumn("A 1y",        width=40,  format="%.1f"),
        "pct_xa_1y":            st.column_config.NumberColumn("xA 1y",       width=40,  format="%.1f"),
        "pct_shots_1y":         st.column_config.NumberColumn("Sh 1y",       width=40,  format="%.1f"),
        "pct_bcc_1y":           st.column_config.NumberColumn("BCC 1y",      width=42,  format="%.1f"),
        "pct_clearances_1y":    st.column_config.NumberColumn("Clr 1y",      width=40,  format="%.1f"),
        "pct_blocks_1y":        st.column_config.NumberColumn("Blk 1y",      width=40,  format="%.1f"),
        "pct_interceptions_1y": st.column_config.NumberColumn("Int 1y",      width=40,  format="%.1f"),
        "pct_tackles_1y":       st.column_config.NumberColumn("Tck 1y",      width=40,  format="%.1f"),
        "pct_recoveries_1y":    st.column_config.NumberColumn("Rec 1y",      width=40,  format="%.1f"),
        "min_played_3y":        st.column_config.NumberColumn("Mins 3y",     width=45,  format="%d"),
        "pct_mins_avail_3y":    st.column_config.NumberColumn("Avail 3y",    width=48,  format="%.1f"),
        "pct_goals_3y":         st.column_config.NumberColumn("G 3y",        width=40,  format="%.1f"),
        "pct_xg_3y":            st.column_config.NumberColumn("xG 3y",       width=40,  format="%.1f"),
        "pct_xgot_3y":          st.column_config.NumberColumn("xGOT 3y",     width=48,  format="%.1f"),
        "pct_assists_3y":       st.column_config.NumberColumn("A 3y",        width=40,  format="%.1f"),
        "pct_xa_3y":            st.column_config.NumberColumn("xA 3y",       width=40,  format="%.1f"),
        "pct_shots_3y":         st.column_config.NumberColumn("Sh 3y",       width=40,  format="%.1f"),
        "pct_bcc_3y":           st.column_config.NumberColumn("BCC 3y",      width=42,  format="%.1f"),
        "pct_clearances_3y":    st.column_config.NumberColumn("Clr 3y",      width=40,  format="%.1f"),
        "pct_blocks_3y":        st.column_config.NumberColumn("Blk 3y",      width=40,  format="%.1f"),
        "pct_interceptions_3y": st.column_config.NumberColumn("Int 3y",      width=40,  format="%.1f"),
        "pct_tackles_3y":       st.column_config.NumberColumn("Tck 3y",      width=40,  format="%.1f"),
        "pct_recoveries_3y":    st.column_config.NumberColumn("Rec 3y",      width=40,  format="%.1f"),
    }
)
