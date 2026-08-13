import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import json

st.set_page_config(
    page_title="FPL Defensive Stats",
    layout="wide",
    initial_sidebar_state="expanded"
)


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
    url = "http://198.244.151.163:8000/fpl_players"
    df = pd.read_parquet(url)
    if 'av_rating_alt' in df.columns:
        df['av_rating_alt'] = pd.to_numeric(df['av_rating_alt'], errors='coerce').fillna(0.0)


    if 'clean_sheets' in df.columns and 'min_played' in df.columns:
        df['CS_90'] = np.where(df['min_played'] > 0, (df['clean_sheets'] / df['min_played'] * 90).round(2), 0.0)
    elif 'CS_90' not in df.columns:
        df['CS_90'] = 0.0

    if 'goals_conceded' in df.columns and 'min_played' in df.columns:
        df['GC_90'] = np.where(df['min_played'] > 0, (df['goals_conceded'] / df['min_played'] * 90).round(2), 0.0)
    elif 'GC_90' not in df.columns:
        df['GC_90'] = 0.0

    if 'expected_goals_conceded_per_90' in df.columns:
        df['xGC_90'] = np.where(df.get('xGC_90', 0) > 0, df['xGC_90'], df['expected_goals_conceded_per_90'].fillna(0.0).round(2))
    elif 'xGC_90' not in df.columns:
        df['xGC_90'] = 0.0

    df['xGP_90'] = (df['xGC_90'] - df['GC_90']).round(2)

    for def_col in ['Clr_90', 'Blk_90', 'Int_90', 'Tck_90', 'Rec_90', 'clean_sheets', 'goals_conceded', 'yellow_cards', 'red_cards', 'CS_90', 'GC_90', 'xGC_90', 'DC_90']:
        if def_col not in df.columns:
            df[def_col] = 0.0

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

rating_series = df[df['av_rating_alt'] > 0]['av_rating_alt'].dropna() if 'av_rating_alt' in df.columns else pd.Series(dtype=float)
r_min = float(rating_series.min()) if not rating_series.empty else 0.0
r_max = float(rating_series.max()) if not rating_series.empty else 10.0


GB = {
    'f_cost_ds':     _slider_bounds(_get_min('now_cost', 4.0), _get_max('now_cost', 15.0)),
    'f_matches_ds':  (int(_get_min('matches_played', 0)), max(int(_get_max('matches_played', 38)), int(_get_min('matches_played', 0)) + 1)),
    'f_rating_ds':   _slider_bounds(r_min, r_max),
    'f_avg_mins_ds': _slider_bounds(_get_min('avg_mins'), _get_max('avg_mins', 90.0)),
    'f_60min_ds':    _slider_bounds(_get_min('60_min'), _get_max('60_min', 100.0)),
    'f_selected_ds': _slider_bounds(_get_min('selected_by_percent'), _get_max('selected_by_percent', 100.0)),
    'f_activity_ds': _slider_bounds(0.0, 100.0),
    'f_cs_ds':       _slider_bounds(0.0, _get_max_sane('CS_90')),
    'f_dc_ds':       _slider_bounds(0.0, _get_max_sane('DC_90')),
    'f_clr_ds':      _slider_bounds(0.0, _get_max_sane('Clr_90')),
    'f_blk_ds':      _slider_bounds(0.0, _get_max_sane('Blk_90')),
    'f_int_ds':      _slider_bounds(0.0, _get_max_sane('Int_90')),
    'f_tck_ds':      _slider_bounds(0.0, _get_max_sane('Tck_90')),
    'f_rec_ds':      _slider_bounds(0.0, _get_max_sane('Rec_90')),
    'f_tchs_ds':     _slider_bounds(0.0, _get_max_sane('Touches_90')),
    'f_pass_ds':     _slider_bounds(0.0, _get_max('Pass_pct', 100.0)),
}


DEFAULTS = {
    'f_cost_ds':     GB['f_cost_ds'],
    'f_matches_ds':  (max(GB['f_matches_ds'][0], 5), GB['f_matches_ds'][1]),
    'f_rating_ds':   GB['f_rating_ds'],
    'f_avg_mins_ds': GB['f_avg_mins_ds'],
    'f_60min_ds':    (max(GB['f_60min_ds'][0], 40.5), GB['f_60min_ds'][1]),
    'f_selected_ds': GB['f_selected_ds'],
    'f_activity_ds': GB['f_activity_ds'],
    'f_cs_ds':       GB['f_cs_ds'],
    'f_dc_ds':       GB['f_dc_ds'],
    'f_clr_ds':      GB['f_clr_ds'],
    'f_blk_ds':      GB['f_blk_ds'],
    'f_int_ds':      GB['f_int_ds'],
    'f_tck_ds':      GB['f_tck_ds'],
    'f_rec_ds':      GB['f_rec_ds'],
    'f_tchs_ds':     GB['f_tchs_ds'],
    'f_pass_ds':     GB['f_pass_ds'],
}


if 'pills_teams_ds'  not in st.session_state: st.session_state.pills_teams_ds  = all_teams
if 'pills_pos_ds'    not in st.session_state: st.session_state.pills_pos_ds    = [p for p in sorted_positions if p in ['DEF', 'MID']]
if 'pills_pl_pos_ds' not in st.session_state: st.session_state.pills_pl_pos_ds = all_pl_pos


def _pills_snapshot():
    snap = {
        'pos':    tuple(sorted(st.session_state.get('pills_pos_ds',   [p for p in sorted_positions if p in ['DEF', 'MID']]) or [])),
        'teams':  tuple(sorted(st.session_state.get('pills_teams_ds', all_teams) or [])),
        'search': st.session_state.get('search_name_ds', ''),
    }
    for i, line in enumerate(pl_lines):
        avail = [p for p in line if p in actual_pl_pos]
        snap[f'pl_{i}'] = tuple(sorted(st.session_state.get(f'pills_pl_line_ds_{i}', avail)))
    return snap

def _safe_range(key, default):
    val = st.session_state.get(key, default)
    if isinstance(val, (tuple, list)) and len(val) == 2:
        if val[0] < val[1]:
            return val
    return default

def get_available(exclude_key=None):
    """Повертає підмножину df за всіма фільтрами, крім exclude_key."""
    cv_pos      = st.session_state.get('pills_pos_ds',   [p for p in sorted_positions if p in ['DEF', 'MID']]) or []
    cv_teams    = st.session_state.get('pills_teams_ds', all_teams) or []
    cv_search   = st.session_state.get('search_name_ds', '')

    cv_pl_pos = []
    for i, line in enumerate(pl_lines):
        avail = [p for p in line if p in actual_pl_pos]
        cv_pl_pos.extend(st.session_state.get(f'pills_pl_line_ds_{i}', avail))

    mask = pd.Series([True] * len(df), index=df.index)
    if exclude_key != 'pills_pos_ds':   mask &= df['element_type'].isin(cv_pos)
    if exclude_key != 'pills_teams_ds': mask &= df['team_short_name'].isin(cv_teams)
    if exclude_key != 'pills_pl_ds':
        if cv_pl_pos:
            if len(cv_pl_pos) == len(all_pl_pos):
                mask &= (df['Play Pos'].isin(cv_pl_pos) | df['Play Pos'].isna())
            else:
                mask &= df['Play Pos'].isin(cv_pl_pos)
    if exclude_key != 'search_name_ds': mask &= df['full_name'].str.contains(cv_search, case=False, na=False)

    _slider_cols = {
        'f_matches_ds':  ('matches_played',        DEFAULTS['f_matches_ds']),
        'f_60min_ds':    ('60_min',                DEFAULTS['f_60min_ds']),
        'f_cost_ds':     ('now_cost',              DEFAULTS['f_cost_ds']),
        'f_avg_mins_ds': ('avg_mins',              DEFAULTS['f_avg_mins_ds']),
        'f_rating_ds':   ('av_rating_alt',         DEFAULTS['f_rating_ds']),
        'f_selected_ds': ('selected_by_percent',   DEFAULTS['f_selected_ds']),
        'f_activity_ds': ('transfer_activity_pct', DEFAULTS['f_activity_ds']),
        'f_cs_ds':       ('CS_90',                 DEFAULTS['f_cs_ds']),
        'f_dc_ds':       ('DC_90',                 DEFAULTS['f_dc_ds']),
        'f_clr_ds':      ('Clr_90',                DEFAULTS['f_clr_ds']),
        'f_blk_ds':      ('Blk_90',                DEFAULTS['f_blk_ds']),
        'f_int_ds':      ('Int_90',                DEFAULTS['f_int_ds']),
        'f_tck_ds':      ('Tck_90',                DEFAULTS['f_tck_ds']),
        'f_rec_ds':      ('Rec_90',                DEFAULTS['f_rec_ds']),
        'f_tchs_ds':     ('Touches_90',            DEFAULTS['f_tchs_ds']),
        'f_pass_ds':     ('Pass_pct',              DEFAULTS['f_pass_ds']),
    }
    for k, (col_name, d) in _slider_cols.items():
        if k != exclude_key and col_name in df.columns:
            val = _safe_range(k, d)
            mask &= (df[col_name] >= val[0]) & (df[col_name] <= val[1])

    return df[mask]

def get_base_df(exclude_key=None):
    """Базовий набір даних для розрахунку діапазонів слайдерів."""
    cv_pos    = st.session_state.get('pills_pos_ds',   [p for p in sorted_positions if p in ['DEF', 'MID']]) or []
    cv_teams  = st.session_state.get('pills_teams_ds', all_teams) or []
    cv_search = st.session_state.get('search_name_ds', '')

    cv_pl_pos = []
    for i, line in enumerate(pl_lines):
        avail = [p for p in line if p in actual_pl_pos]
        cv_pl_pos.extend(st.session_state.get(f'pills_pl_line_ds_{i}', avail))

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
        'f_matches_ds':  ('matches_played',        DEFAULTS['f_matches_ds']),
        'f_60min_ds':    ('60_min',                DEFAULTS['f_60min_ds']),
        'f_cost_ds':     ('now_cost',              DEFAULTS['f_cost_ds']),
        'f_avg_mins_ds': ('avg_mins',              DEFAULTS['f_avg_mins_ds']),
        'f_rating_ds':   ('av_rating_alt',         DEFAULTS['f_rating_ds']),
        'f_selected_ds': ('selected_by_percent',   DEFAULTS['f_selected_ds']),
        'f_activity_ds': ('transfer_activity_pct', DEFAULTS['f_activity_ds']),
        'f_cs_ds':       ('CS_90',                 DEFAULTS['f_cs_ds']),
        'f_dc_ds':       ('DC_90',                 DEFAULTS['f_dc_ds']),
        'f_clr_ds':      ('Clr_90',                DEFAULTS['f_clr_ds']),
        'f_blk_ds':      ('Blk_90',                DEFAULTS['f_blk_ds']),
        'f_int_ds':      ('Int_90',                DEFAULTS['f_int_ds']),
        'f_tck_ds':      ('Tck_90',                DEFAULTS['f_tck_ds']),
        'f_rec_ds':      ('Rec_90',                DEFAULTS['f_rec_ds']),
        'f_tchs_ds':     ('Touches_90',            DEFAULTS['f_tchs_ds']),
        'f_pass_ds':     ('Pass_pct',              DEFAULTS['f_pass_ds']),
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
        if key_prefix == "pl_pos_ds":
            for i, line in enumerate(pl_lines):
                st.session_state[f"pills_pl_line_ds_{i}"] = [p for p in options if p in line]
        st.rerun()
    if cols[2].button("None", key=f"btn_none_{key_prefix}", width="stretch"):
        st.session_state[f"pills_{key_prefix}"] = []
        if key_prefix == "pl_pos_ds":
            for i, line in enumerate(pl_lines):
                st.session_state[f"pills_pl_line_ds_{i}"] = []
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
                    if (p.innerText.trim() === 'Playing Position') {{  plHeader = p; }}
                }} );
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
                    }}  else {{
                        b.style.setProperty('width', '60px', 'important');
                        b.style.setProperty('min-width', '60px', 'important');
                        b.style.setProperty('max-width', '60px', 'important');
                    }}
                    var expectedOpacity = inactiveList.includes(txt) ? '0.3' : '';
                    if (b.style.opacity !== expectedOpacity) {{
                        b.style.opacity = expectedOpacity;
                    }}
                }} );
            }}  catch(e) {{ }}
        }}
        setInterval(forceLayout, 300);
    }} )();
    </script>
    """
    st.components.v1.html(js, height=0, scrolling=False)


auto_update_slider('f_cost_ds',     'now_cost',            float)
auto_update_slider('f_matches_ds',  'matches_played',      int)
auto_update_slider('f_rating_ds',   'av_rating_alt',       float, only_positive=True)
auto_update_slider('f_avg_mins_ds', 'avg_mins',            float)
auto_update_slider('f_60min_ds',    '60_min',              float)
auto_update_slider('f_selected_ds', 'selected_by_percent', float)
auto_update_slider('f_activity_ds', 'transfer_activity_pct', float)
auto_update_slider('f_cs_ds',       'CS_90',               float)
auto_update_slider('f_dc_ds',       'DC_90',               float)
auto_update_slider('f_clr_ds',      'Clr_90',              float)
auto_update_slider('f_blk_ds',      'Blk_90',              float)
auto_update_slider('f_int_ds',      'Int_90',              float)
auto_update_slider('f_tck_ds',      'Tck_90',              float)
auto_update_slider('f_rec_ds',      'Rec_90',              float)
auto_update_slider('f_tchs_ds',     'Touches_90',          float)
auto_update_slider('f_pass_ds',     'Pass_pct',            float)


if st.sidebar.button("Reset All Filters", width="stretch", type="primary"):
    keys_to_delete = [k for k in st.session_state.keys() if '_ds' in k]
    for key in keys_to_delete:
        del st.session_state[key]
    st.rerun()

search_name = st.sidebar.text_input("Search Player", placeholder="Enter name...", key="search_name_ds")


avail_pos = set(get_available('pills_pos_ds')['element_type'].unique())
filter_header("FPL Position", sorted_positions, "pos_ds")
selected_positions = st.sidebar.pills(
    "FPL Position", options=sorted_positions, key="pills_pos_ds",
    selection_mode="multi", label_visibility="collapsed"
)


f_cost = st.sidebar.slider(
    "FPL Price", GB['f_cost_ds'][0], GB['f_cost_ds'][1], step=0.1, format="%.1f", key="f_cost_ds"
)


avail_teams = set(get_available('pills_teams_ds')['team_short_name'].unique())
filter_header("Team", all_teams, "teams_ds")
selected_teams = st.sidebar.pills(
    "Team", options=all_teams, key="pills_teams_ds",
    selection_mode="multi", label_visibility="collapsed"
)


avail_pl = set(get_available('pills_pl_ds')['Play Pos'].dropna().unique()) if 'Play Pos' in df.columns else set()
filter_header("Playing Position", all_pl_pos, "pl_pos_ds")
selected_pl_pos = []

for idx, line in enumerate(pl_lines):
    available_in_line = [p for p in line if p in actual_pl_pos]
    if not available_in_line:
        continue
    line_key = f"pills_pl_line_ds_{idx}"
    if line_key not in st.session_state:
        st.session_state[line_key] = [p for p in st.session_state.pills_pl_pos_ds if p in available_in_line]

    line_res = st.sidebar.pills(
        label=f"pl_line_{idx}", options=available_in_line, key=line_key,
        selection_mode="multi", label_visibility="collapsed"
    )
    if line_res:
        selected_pl_pos.extend(line_res)


all_inactive = []
all_inactive.extend([p for p in sorted_positions if p not in avail_pos])
all_inactive.extend([t for t in all_teams if t not in avail_teams])
all_inactive.extend([p for p in all_pl_pos if p not in avail_pl])

inject_sidebar_layout(all_inactive)


with st.sidebar.expander("Performance Stats", expanded=False):
    f_matches  = st.slider("Matches",      GB['f_matches_ds'][0],  GB['f_matches_ds'][1],  step=1,    key="f_matches_ds")
    f_rating   = st.slider("Rating",       GB['f_rating_ds'][0],   GB['f_rating_ds'][1],   step=0.05, format="%.2f", key="f_rating_ds")
    f_avg_mins = st.slider("Average Mins", GB['f_avg_mins_ds'][0], GB['f_avg_mins_ds'][1], step=1.0,  key="f_avg_mins_ds")
    f_60min    = st.slider("60 Min %",     GB['f_60min_ds'][0],    GB['f_60min_ds'][1],    step=0.5,  key="f_60min_ds")


with st.sidebar.expander("Market & Popularity", expanded=False):
    f_selected = st.slider("Selected %",        GB['f_selected_ds'][0], GB['f_selected_ds'][1], step=0.1, key="f_selected_ds")
    f_activity = st.slider("Transfer Activity", GB['f_activity_ds'][0], GB['f_activity_ds'][1], step=1.0, format="%d%%", key="f_activity_ds")


with st.sidebar.expander("Defensive Stats", expanded=True):
    f_cs   = st.slider("CS/90",           GB['f_cs_ds'][0],   GB['f_cs_ds'][1],   step=0.05, key="f_cs_ds")
    f_dc   = st.slider("DC/90",           GB['f_dc_ds'][0],   GB['f_dc_ds'][1],   step=0.5,  key="f_dc_ds")
    f_clr  = st.slider("Clearances/90",   GB['f_clr_ds'][0],  GB['f_clr_ds'][1],  step=0.5,  key="f_clr_ds")
    f_blk  = st.slider("Blocks/90",       GB['f_blk_ds'][0],  GB['f_blk_ds'][1],  step=0.1,  key="f_blk_ds")
    f_int  = st.slider("Interceptions/90",GB['f_int_ds'][0],  GB['f_int_ds'][1],  step=0.1,  key="f_int_ds")
    f_tck  = st.slider("Tackles/90",      GB['f_tck_ds'][0],  GB['f_tck_ds'][1],  step=0.1,  key="f_tck_ds")
    f_rec  = st.slider("Recoveries/90",   GB['f_rec_ds'][0],  GB['f_rec_ds'][1],  step=0.5,  key="f_rec_ds")
    f_tchs = st.slider("Touches/90",      GB['f_tchs_ds'][0], GB['f_tchs_ds'][1], step=0.5,  key="f_tchs_ds")
    f_pass = st.slider("Pass%",           GB['f_pass_ds'][0], GB['f_pass_ds'][1], step=1.0,  key="f_pass_ds")


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
    ('av_rating_alt',         f_rating,   GB['f_rating_ds']),
    ('matches_played',        f_matches,  GB['f_matches_ds']),
    ('60_min',                f_60min,    GB['f_60min_ds']),
    ('now_cost',              f_cost,     GB['f_cost_ds']),
    ('selected_by_percent',   f_selected, GB['f_selected_ds']),
    ('transfer_activity_pct', f_activity, GB['f_activity_ds']),
    ('CS_90',                 f_cs,       GB['f_cs_ds']),
    ('DC_90',                 f_dc,       GB['f_dc_ds']),
    ('Clr_90',                f_clr,      GB['f_clr_ds']),
    ('Blk_90',                f_blk,      GB['f_blk_ds']),
    ('Int_90',                f_int,      GB['f_int_ds']),
    ('Tck_90',                f_tck,      GB['f_tck_ds']),
    ('Rec_90',                f_rec,      GB['f_rec_ds']),
    ('Touches_90',            f_tchs,     GB['f_tchs_ds']),
    ('Pass_pct',              f_pass,     GB['f_pass_ds']),
    ('avg_mins',              f_avg_mins, GB['f_avg_mins_ds']),
]

for col_name, val, limit in filter_vars:
    if col_name in df.columns:
        mask &= (df[col_name] >= val[0])
        if val[1] < limit[1] - 1e-4:
            mask &= (df[col_name] <= val[1])

filtered_df = df[mask].copy()
sort_cols = [c for c in ['now_cost', 'M Price'] if c in filtered_df.columns]
if sort_cols:
    filtered_df = filtered_df.sort_values(by=sort_cols, ascending=[False] * len(sort_cols))


display_columns = [
    "full_name", "Age", "element_type", "Play Pos", "team_short_name", "now_cost", "M Price",
    "selected_by_percent", "min_played", "matches_played",
    "avg_mins", "60_min", "av_rating_alt",
    "CS_90",
    "DC_90", "Clr_90", "Blk_90", "Int_90", "Tck_90", "Rec_90", "Aerial_pct", "Duel_pct",
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


def warm_honey_gradient(s, min_alpha=0.06, max_alpha=0.28, max_cap=None):
    if s.empty:
        return ['' for _ in s]
    s_min, s_max = s.min(), s.max()
    if max_cap is not None and not pd.isna(s_max):
        s_max = min(s_max, max_cap)
    if pd.isna(s_min) or pd.isna(s_max) or s_min >= s_max:
        return ['' for _ in s]

    styles = []
    for val in s:
        if pd.isna(val):
            styles.append('')
        else:
            val_clamped = min(val, s_max)
            norm_val = (val_clamped - s_min) / (s_max - s_min)
            r = int(215 + norm_val * (240 - 215))
            g = int(180 + norm_val * (145 - 180))
            b = int(90  + norm_val * (35  - 90))
            alpha = min_alpha + norm_val * (max_alpha - min_alpha)
            styles.append(f'background-color: rgba({r}, {g}, {b}, {alpha:.2f})')
    return styles


def soft_blue_gradient(s, min_alpha=0.05, max_alpha=0.28, max_cap=None):
    if s.empty:
        return ['' for _ in s]
    s_min, s_max = s.min(), s.max()
    if max_cap is not None and not pd.isna(s_max):
        s_max = min(s_max, max_cap)
    if pd.isna(s_min) or pd.isna(s_max) or s_min >= s_max:
        return ['' for _ in s]

    styles = []
    for val in s:
        if pd.isna(val):
            styles.append('')
        else:
            val_clamped = min(val, s_max)
            norm_val = (val_clamped - s_min) / (s_max - s_min)
            r = int(60  + norm_val * (0   - 60))
            g = int(130 + norm_val * (165 - 130))
            b = int(200 + norm_val * (235 - 200))
            alpha = min_alpha + norm_val * (max_alpha - min_alpha)
            styles.append(f'background-color: rgba({r}, {g}, {b}, {alpha:.2f})')
    return styles


styled_df = filtered_df[existing_cols].style\
    .apply(warm_honey_gradient, subset=[c for c in ['avg_mins', 'av_rating_alt', '60_min'] if c in existing_cols])\
    .apply(soft_gradient, cmap_name='YlGn', alpha=0.25, subset=[c for c in ['CS_90', 'DC_90', 'Clr_90', 'Blk_90', 'Int_90', 'Tck_90', 'Rec_90', 'Aerial_pct', 'Duel_pct'] if c in existing_cols])\
    .apply(soft_blue_gradient, subset=[c for c in ['Touches_90', 'Pass_pct'] if c in existing_cols])\
    .format(precision=2)

st.subheader(f"Defensive Stats: {len(filtered_df)} players", anchor=False)

base_widths = {}
for col in existing_cols:
    if not filtered_df.empty and col in filtered_df.columns:
        val_series = filtered_df[col].dropna().astype(str)
        max_val_len = int(val_series.str.len().max()) if not val_series.empty else 1
    else:
        max_val_len = 1

    bw = max_val_len * 7
    if col == "full_name":
        bw = min(bw, 140)
    else:
        bw = min(bw, 48)
    base_widths[col] = max(bw, 12)

inv_weights = {col: 1.0 / (w ** 0.5) for col, w in base_widths.items()}
sum_inv_weights = sum(inv_weights.values())
TOTAL_PADDING_BUDGET = 650

smart_column_config = {}
format_map = {
    "full_name":           ("TextColumn", None, "Player"),
    "Age":                 ("NumberColumn", "%d", "Age"),
    "element_type":        ("TextColumn", None, "Pos"),
    "Play Pos":            ("TextColumn", None, "Pl Pos"),
    "team_short_name":     ("TextColumn", None, "Team"),
    "now_cost":            ("NumberColumn", "%.1f", "Price"),
    "M Price":             ("NumberColumn", "%.1f", "TM Price"),
    "selected_by_percent": ("NumberColumn", "%.1f%%", "Sel %"),
    "min_played":          ("NumberColumn", None, "Mins"),
    "matches_played":      ("NumberColumn", None, "MP"),
    "avg_mins":            ("NumberColumn", "%d", "AvMins"),
    "60_min":              ("NumberColumn", "%.1f", "60m %"),
    "av_rating_alt":       ("NumberColumn", "%.2f", "RatA"),
    "CS_90":               ("NumberColumn", "%.2f", "CS/90"),
    "DC_90":               ("NumberColumn", "%.2f", "DC/90"),
    "Clr_90":              ("NumberColumn", "%.2f", "Clr/90"),
    "Blk_90":              ("NumberColumn", "%.2f", "Blk/90"),
    "Int_90":              ("NumberColumn", "%.2f", "Int/90"),
    "Tck_90":              ("NumberColumn", "%.2f", "Tck/90"),
    "Rec_90":              ("NumberColumn", "%.2f", "Rec/90"),
    "Aerial_pct":          ("NumberColumn", "%.1f", "Air%"),
    "Duel_pct":            ("NumberColumn", "%.1f", "Duel%"),
    "Touches_90":          ("NumberColumn", "%.2f", "Tchs/90"),
    "Pass_pct":            ("NumberColumn", "%.1f", "Pass%"),
    "yellow_cards":        ("NumberColumn", "%d", "YC"),
    "YC_90":               ("NumberColumn", "%.2f", "YC/90"),
    "red_cards":           ("NumberColumn", "%d", "RC"),
    "RC_90":               ("NumberColumn", "%.2f", "RC/90"),
}

for col in existing_cols:
    bw = base_widths[col]
    bonus = (inv_weights[col] / sum_inv_weights) * TOTAL_PADDING_BUDGET
    calc_w = int(round(bw + bonus))

    if col == "full_name":
        calc_w = max(calc_w, 140)
    else:
        calc_w = max(calc_w, 48)

    col_type, col_fmt, col_label = format_map.get(col, ("Column", None, col))

    kwargs = {"label": col_label, "width": calc_w}
    if col == "full_name":
        kwargs["pinned"] = True
    if col_fmt:
        kwargs["format"] = col_fmt

    if col_type == "NumberColumn":
        smart_column_config[col] = st.column_config.NumberColumn(**kwargs)
    elif col_type == "TextColumn":
        smart_column_config[col] = st.column_config.TextColumn(**kwargs)
    else:
        smart_column_config[col] = st.column_config.Column(**kwargs)

st.dataframe(
    styled_df,
    width="stretch",
    hide_index=True,
    height=800,
    column_config=smart_column_config
)
