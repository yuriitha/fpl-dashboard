import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import json

st.set_page_config(
    page_title="FPL GK Stats",
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
    if 'av_rating_alt' in df.columns:
        df['av_rating_alt'] = pd.to_numeric(df['av_rating_alt'], errors='coerce').fillna(0.0)

    # Розрахунок/безпечне отримання воротарських метрик при відсутності в parquet
    if 'clean_sheets' in df.columns and 'min_played' in df.columns:
        df['CS_90'] = np.where(df['min_played'] > 0, (df['clean_sheets'] / df['min_played'] * 90).round(2), 0.0)
    elif 'CS_90' not in df.columns:
        df['CS_90'] = 0.0

    if 'goals_conceded' in df.columns and 'min_played' in df.columns:
        df['GC_90'] = np.where(df['min_played'] > 0, (df['goals_conceded'] / df['min_played'] * 90).round(2), 0.0)
    elif 'GC_90' not in df.columns:
        df['GC_90'] = 0.0

    if 'saves' in df.columns and 'min_played' in df.columns:
        df['Svs_90'] = np.where(df['min_played'] > 0, (df['saves'] / df['min_played'] * 90).round(2), 0.0)
    elif 'Svs_90' not in df.columns:
        df['Svs_90'] = 0.0

    if 'expected_goals_conceded_per_90' in df.columns:
        df['xGC_90'] = np.where(df.get('xGC_90', 0) > 0, df['xGC_90'], df['expected_goals_conceded_per_90'].fillna(0.0).round(2))
    elif 'xGC_90' not in df.columns:
        df['xGC_90'] = 0.0

    df['xGP_90'] = (df['xGC_90'] - df['GC_90']).round(2)

    for gk_col in ['saves', 'penalties_saved', 'clean_sheets', 'goals_conceded', 'yellow_cards', 'red_cards', 'Svs_90', 'CS_90', 'GC_90', 'xGC_90', 'xGP_90', 'gk_value']:
        if gk_col not in df.columns:
            df[gk_col] = 0.0

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
    'f_cost_gks':     _slider_bounds(_get_min('now_cost', 4.0), _get_max('now_cost', 15.0)),
    'f_matches_gks':  (int(_get_min('matches_played', 0)), max(int(_get_max('matches_played', 38)), int(_get_min('matches_played', 0)) + 1)),
    'f_rating_gks':   _slider_bounds(r_min, r_max),
    'f_avg_mins_gks': _slider_bounds(_get_min('avg_mins'), _get_max('avg_mins', 90.0)),
    'f_60min_gks':    _slider_bounds(_get_min('60_min'), _get_max('60_min', 100.0)),
    'f_selected_gks': _slider_bounds(_get_min('selected_by_percent'), _get_max('selected_by_percent', 100.0)),
    'f_activity_gks': _slider_bounds(0.0, 100.0),
    'f_svs_gks':      _slider_bounds(0.0, _get_max_sane('Svs_90')),
    'f_cs_gks':       _slider_bounds(0.0, _get_max_sane('CS_90')),
    'f_xgc_gks':      _slider_bounds(0.0, _get_max_sane('xGC_90')),
    'f_xgp_gks':      _slider_bounds(_get_min_sane('xGP_90', -2.0), _get_max_sane('xGP_90', 2.0)),
    'f_tchs_gks':     _slider_bounds(0.0, _get_max_sane('Touches_90')),
    'f_pass_gks':     _slider_bounds(0.0, _get_max('Pass_pct', 100.0)),
}

# Дефолтні значення повзунків
DEFAULTS = {
    'f_cost_gks':     GB['f_cost_gks'],
    'f_matches_gks':  (max(GB['f_matches_gks'][0], 5), GB['f_matches_gks'][1]),
    'f_rating_gks':   GB['f_rating_gks'],
    'f_avg_mins_gks': GB['f_avg_mins_gks'],
    'f_60min_gks':    (max(GB['f_60min_gks'][0], 40.5), GB['f_60min_gks'][1]),
    'f_selected_gks': GB['f_selected_gks'],
    'f_activity_gks': GB['f_activity_gks'],
    'f_svs_gks':      GB['f_svs_gks'],
    'f_cs_gks':       GB['f_cs_gks'],
    'f_xgc_gks':      GB['f_xgc_gks'],
    'f_xgp_gks':      GB['f_xgp_gks'],
    'f_tchs_gks':     GB['f_tchs_gks'],
    'f_pass_gks':     GB['f_pass_gks'],
}

# ========================== SESSION STATE ==========================
if 'pills_teams_gks'  not in st.session_state: st.session_state.pills_teams_gks  = all_teams
if 'pills_pos_gks'    not in st.session_state: st.session_state.pills_pos_gks    = [p for p in sorted_positions if p == 'GK']
if 'pills_pl_pos_gks' not in st.session_state: st.session_state.pills_pl_pos_gks = all_pl_pos

# ========================== ХЕЛПЕРИ ==========================
def _pills_snapshot():
    snap = {
        'pos':    tuple(sorted(st.session_state.get('pills_pos_gks',   [p for p in sorted_positions if p == 'GK']) or [])),
        'teams':  tuple(sorted(st.session_state.get('pills_teams_gks', all_teams) or [])),
        'search': st.session_state.get('search_name_gks', ''),
    }
    for i, line in enumerate(pl_lines):
        avail = [p for p in line if p in actual_pl_pos]
        snap[f'pl_{i}'] = tuple(sorted(st.session_state.get(f'pills_pl_line_gks_{i}', avail)))
    return snap

def _safe_range(key, default):
    val = st.session_state.get(key, default)
    if isinstance(val, (tuple, list)) and len(val) == 2:
        if val[0] < val[1]:
            return val
    return default

def get_available(exclude_key=None):
    """Повертає підмножину df за всіма фільтрами, крім exclude_key."""
    cv_pos      = st.session_state.get('pills_pos_gks',   [p for p in sorted_positions if p == 'GK']) or []
    cv_teams    = st.session_state.get('pills_teams_gks', all_teams) or []
    cv_search   = st.session_state.get('search_name_gks', '')

    cv_pl_pos = []
    for i, line in enumerate(pl_lines):
        avail = [p for p in line if p in actual_pl_pos]
        cv_pl_pos.extend(st.session_state.get(f'pills_pl_line_gks_{i}', avail))

    mask = pd.Series([True] * len(df), index=df.index)
    if exclude_key != 'pills_pos_gks':   mask &= df['element_type'].isin(cv_pos)
    if exclude_key != 'pills_teams_gks': mask &= df['team_short_name'].isin(cv_teams)
    if exclude_key != 'pills_pl_gks':
        if cv_pl_pos:
            if len(cv_pl_pos) == len(all_pl_pos):
                mask &= (df['Play Pos'].isin(cv_pl_pos) | df['Play Pos'].isna())
            else:
                mask &= df['Play Pos'].isin(cv_pl_pos)
    if exclude_key != 'search_name_gks': mask &= df['full_name'].str.contains(cv_search, case=False, na=False)

    _slider_cols = {
        'f_matches_gks':  ('matches_played',        DEFAULTS['f_matches_gks']),
        'f_60min_gks':    ('60_min',                DEFAULTS['f_60min_gks']),
        'f_cost_gks':     ('now_cost',              DEFAULTS['f_cost_gks']),
        'f_avg_mins_gks': ('avg_mins',              DEFAULTS['f_avg_mins_gks']),
        'f_rating_gks':   ('av_rating_alt',         DEFAULTS['f_rating_gks']),
        'f_selected_gks': ('selected_by_percent',   DEFAULTS['f_selected_gks']),
        'f_activity_gks': ('transfer_activity_pct', DEFAULTS['f_activity_gks']),
        'f_svs_gks':      ('Svs_90',                DEFAULTS['f_svs_gks']),
        'f_cs_gks':       ('CS_90',                 DEFAULTS['f_cs_gks']),
        'f_xgc_gks':      ('xGC_90',                DEFAULTS['f_xgc_gks']),
        'f_xgp_gks':      ('xGP_90',                DEFAULTS['f_xgp_gks']),
        'f_tchs_gks':     ('Touches_90',            DEFAULTS['f_tchs_gks']),
        'f_pass_gks':     ('Pass_pct',              DEFAULTS['f_pass_gks']),
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
    cv_pos    = st.session_state.get('pills_pos_gks',   [p for p in sorted_positions if p == 'GK']) or []
    cv_teams  = st.session_state.get('pills_teams_gks', all_teams) or []
    cv_search = st.session_state.get('search_name_gks', '')

    cv_pl_pos = []
    for i, line in enumerate(pl_lines):
        avail = [p for p in line if p in actual_pl_pos]
        cv_pl_pos.extend(st.session_state.get(f'pills_pl_line_gks_{i}', avail))

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
        'f_matches_gks':  ('matches_played',        DEFAULTS['f_matches_gks']),
        'f_60min_gks':    ('60_min',                DEFAULTS['f_60min_gks']),
        'f_cost_gks':     ('now_cost',              DEFAULTS['f_cost_gks']),
        'f_avg_mins_gks': ('avg_mins',              DEFAULTS['f_avg_mins_gks']),
        'f_rating_gks':   ('av_rating_alt',         DEFAULTS['f_rating_gks']),
        'f_selected_gks': ('selected_by_percent',   DEFAULTS['f_selected_gks']),
        'f_activity_gks': ('transfer_activity_pct', DEFAULTS['f_activity_gks']),
        'f_svs_gks':      ('Svs_90',                DEFAULTS['f_svs_gks']),
        'f_cs_gks':       ('CS_90',                 DEFAULTS['f_cs_gks']),
        'f_xgc_gks':      ('xGC_90',                DEFAULTS['f_xgc_gks']),
        'f_xgp_gks':      ('xGP_90',                DEFAULTS['f_xgp_gks']),
        'f_tchs_gks':     ('Touches_90',            DEFAULTS['f_tchs_gks']),
        'f_pass_gks':     ('Pass_pct',              DEFAULTS['f_pass_gks']),
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
        if key_prefix == "pl_pos_gks":
            for i, line in enumerate(pl_lines):
                st.session_state[f"pills_pl_line_gks_{i}"] = [p for p in options if p in line]
        st.rerun()
    if cols[2].button("None", key=f"btn_none_{key_prefix}", width="stretch"):
        st.session_state[f"pills_{key_prefix}"] = []
        if key_prefix == "pl_pos_gks":
            for i, line in enumerate(pl_lines):
                st.session_state[f"pills_pl_line_gks_{i}"] = []
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
auto_update_slider('f_cost_gks',     'now_cost',            float)
auto_update_slider('f_matches_gks',  'matches_played',      int)
auto_update_slider('f_rating_gks',   'av_rating_alt',       float, only_positive=True)
auto_update_slider('f_avg_mins_gks', 'avg_mins',            float)
auto_update_slider('f_60min_gks',    '60_min',              float)
auto_update_slider('f_selected_gks', 'selected_by_percent', float)
auto_update_slider('f_activity_gks', 'transfer_activity_pct', float)
auto_update_slider('f_svs_gks',      'Svs_90',              float)
auto_update_slider('f_cs_gks',       'CS_90',               float)
auto_update_slider('f_xgc_gks',      'xGC_90',              float)
auto_update_slider('f_xgp_gks',      'xGP_90',              float)
auto_update_slider('f_tchs_gks',     'Touches_90',          float)
auto_update_slider('f_pass_gks',     'Pass_pct',            float)

# ========================== САЙДБАР ==========================
if st.sidebar.button("Reset All Filters", width="stretch", type="primary"):
    keys_to_delete = [k for k in st.session_state.keys() if '_gks' in k]
    for key in keys_to_delete:
        del st.session_state[key]
    st.rerun()

search_name = st.sidebar.text_input("Search Player", placeholder="Enter name...", key="search_name_gks")

# --- 1. FPL POSITION ---
avail_pos = set(get_available('pills_pos_gks')['element_type'].unique())
filter_header("FPL Position", sorted_positions, "pos_gks")
selected_positions = st.sidebar.pills(
    "FPL Position", options=sorted_positions, key="pills_pos_gks",
    selection_mode="multi", label_visibility="collapsed"
)

# --- 2. FPL PRICE ---
f_cost = st.sidebar.slider(
    "FPL Price", GB['f_cost_gks'][0], GB['f_cost_gks'][1], step=0.1, format="%.1f", key="f_cost_gks"
)

# --- 3. TEAM ---
avail_teams = set(get_available('pills_teams_gks')['team_short_name'].unique())
filter_header("Team", all_teams, "teams_gks")
selected_teams = st.sidebar.pills(
    "Team", options=all_teams, key="pills_teams_gks",
    selection_mode="multi", label_visibility="collapsed"
)

# --- 4. PLAYING POSITION ---
avail_pl = set(get_available('pills_pl_gks')['Play Pos'].dropna().unique()) if 'Play Pos' in df.columns else set()
filter_header("Playing Position", all_pl_pos, "pl_pos_gks")
selected_pl_pos = []

for idx, line in enumerate(pl_lines):
    available_in_line = [p for p in line if p in actual_pl_pos]
    if not available_in_line:
        continue
    line_key = f"pills_pl_line_gks_{idx}"
    if line_key not in st.session_state:
        st.session_state[line_key] = [p for p in st.session_state.pills_pl_pos_gks if p in available_in_line]

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
    f_matches  = st.slider("Matches",      GB['f_matches_gks'][0],  GB['f_matches_gks'][1],  step=1,    key="f_matches_gks")
    f_rating   = st.slider("Rating",       GB['f_rating_gks'][0],   GB['f_rating_gks'][1],   step=0.05, format="%.2f", key="f_rating_gks")
    f_avg_mins = st.slider("Average Mins", GB['f_avg_mins_gks'][0], GB['f_avg_mins_gks'][1], step=1.0,  key="f_avg_mins_gks")
    f_60min    = st.slider("60 Min %",     GB['f_60min_gks'][0],    GB['f_60min_gks'][1],    step=0.5,  key="f_60min_gks")

# --- MARKET & POPULARITY ---
with st.sidebar.expander("Market & Popularity", expanded=False):
    f_selected = st.slider("Selected %",        GB['f_selected_gks'][0], GB['f_selected_gks'][1], step=0.1, key="f_selected_gks")
    f_activity = st.slider("Transfer Activity", GB['f_activity_gks'][0], GB['f_activity_gks'][1], step=1.0, format="%d%%", key="f_activity_gks")

# --- GOALKEEPER STATS ---
with st.sidebar.expander("Goalkeeper Stats", expanded=True):
    f_svs  = st.slider("Saves/90",   GB['f_svs_gks'][0], GB['f_svs_gks'][1], step=0.05, key="f_svs_gks")
    f_cs   = st.slider("CS/90",      GB['f_cs_gks'][0],  GB['f_cs_gks'][1],  step=0.05, key="f_cs_gks")
    f_xgc  = st.slider("xGC/90",     GB['f_xgc_gks'][0], GB['f_xgc_gks'][1], step=0.05, key="f_xgc_gks")
    f_xgp  = st.slider("xGP/90",     GB['f_xgp_gks'][0], GB['f_xgp_gks'][1], step=0.05, key="f_xgp_gks")
    f_tchs = st.slider("Touches/90", GB['f_tchs_gks'][0], GB['f_tchs_gks'][1], step=0.5, key="f_tchs_gks")
    f_pass = st.slider("Pass%",      GB['f_pass_gks'][0], GB['f_pass_gks'][1], step=1.0, key="f_pass_gks")

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
    ('av_rating_alt',         f_rating,   GB['f_rating_gks']),
    ('matches_played',        f_matches,  GB['f_matches_gks']),
    ('60_min',                f_60min,    GB['f_60min_gks']),
    ('now_cost',              f_cost,     GB['f_cost_gks']),
    ('selected_by_percent',   f_selected, GB['f_selected_gks']),
    ('transfer_activity_pct', f_activity, GB['f_activity_gks']),
    ('Svs_90',                f_svs,      GB['f_svs_gks']),
    ('CS_90',                 f_cs,       GB['f_cs_gks']),
    ('xGC_90',                f_xgc,      GB['f_xgc_gks']),
    ('xGP_90',                f_xgp,      GB['f_xgp_gks']),
    ('Touches_90',            f_tchs,     GB['f_tchs_gks']),
    ('Pass_pct',              f_pass,     GB['f_pass_gks']),
    ('avg_mins',              f_avg_mins, GB['f_avg_mins_gks']),
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
    "full_name", "Age", "element_type", "Play Pos", "team_short_name", "now_cost", "M Price",
    "selected_by_percent", "min_played", "matches_played", 
    "avg_mins", "60_min", "av_rating_alt", 
    "CS_90", "xGC_90", "xGP_90",
    "Svs_90", "penalties_saved",
    "Touches_90", "Pass_pct", "yellow_cards", "YC_90", "red_cards", "RC_90"
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
    .apply(soft_gradient, cmap_name='RdYlGn', alpha=0.25, subset=[c for c in ['avg_mins', 'av_rating_alt', '60_min'] if c in existing_cols]) \
    .apply(soft_gradient, cmap_name='YlGn', alpha=0.25, subset=[c for c in ['CS_90', 'Svs_90', 'penalties_saved', 'xGP_90'] if c in existing_cols]) \
    .apply(soft_gradient, cmap_name='RdYlGn', alpha=0.25, reverse=True, subset=[c for c in ['xGC_90'] if c in existing_cols]) \
    .apply(soft_gradient, cmap_name='Blues', alpha=0.25, subset=[c for c in ['Touches_90', 'Pass_pct'] if c in existing_cols]) \
    .format(precision=2)

st.subheader(f"Goalkeeper Stats: {len(filtered_df)} players", anchor=False)

st.dataframe(
    styled_df,
    width="stretch",
    hide_index=True,
    height=800,
    column_config={
        "full_name":           st.column_config.TextColumn("Player",        width="medium", pinned=True),
        "Age":                 st.column_config.NumberColumn("Age",         width=40,  format="%d"),
        "element_type":        st.column_config.TextColumn("Pos",           width=45),
        "Play Pos":            st.column_config.TextColumn("Pl Pos",        width=45),
        "team_short_name":     st.column_config.TextColumn("Team",          width=45),
        "now_cost":            st.column_config.NumberColumn("Price",       width=40,  format="%.1f"),
        "M Price":             st.column_config.NumberColumn("TM Price",    width=55,  format="%.1f"),
        "selected_by_percent": st.column_config.NumberColumn("Selected",    width=55,  format="%.1f%%"),
        "min_played":          st.column_config.NumberColumn("Mins",        width=45),
        "matches_played":      st.column_config.NumberColumn("MP",          width=35),
        "avg_mins":            st.column_config.NumberColumn("AvgMins",     width=40,  format="%d"),
        "60_min":              st.column_config.NumberColumn("60Mins%",     width=50,  format="%.1f"),
        "av_rating_alt":       st.column_config.NumberColumn("RatA",        width=40,  format="%.2f"),
        "CS_90":               st.column_config.NumberColumn("CS/90",       width=40,  format="%.2f"),
        "xGC_90":              st.column_config.NumberColumn("xGC/90",      width=45,  format="%.2f"),
        "xGP_90":              st.column_config.NumberColumn("xGP/90",      width=45,  format="%.2f"),
        "Svs_90":              st.column_config.NumberColumn("Svs/90",      width=45,  format="%.2f"),
        "penalties_saved":     st.column_config.NumberColumn("PS",          width=35,  format="%d"),
        "Touches_90":          st.column_config.NumberColumn("Tchs/90",     width=50,  format="%.2f"),
        "Pass_pct":            st.column_config.NumberColumn("Pass%",       width=45,  format="%.1f"),
        "yellow_cards":        st.column_config.NumberColumn("YC",          width=35,  format="%d"),
        "YC_90":               st.column_config.NumberColumn("YC/90",       width=40,  format="%.2f"),
        "red_cards":           st.column_config.NumberColumn("RC",          width=35,  format="%d"),
        "RC_90":               st.column_config.NumberColumn("RC/90",       width=40,  format="%.2f"),
    }
)
