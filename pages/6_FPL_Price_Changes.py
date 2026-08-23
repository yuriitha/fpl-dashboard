import streamlit as st
import pandas as pd
import numpy as np
import json

st.set_page_config(
    page_title="FPL Price Changes",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown('''
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

        .playing-pos-wrapper button {
            width: 48px !important; min-width: 48px !important; max-width: 48px !important;
        }
    </style>
''', unsafe_allow_html=True)


@st.cache_data(ttl=300)
def load_data():
    url = "http://198.244.151.163:8000/fpl_players"
    try:
        df = pd.read_parquet(url)
    except Exception:
        import os
        local_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "streamlit", "fpl_players.parquet")
        if os.path.exists(local_path):
            df = pd.read_parquet(local_path)
        else:
            raise

    # Fallback to load ownership if missing or zeroed
    needs_ownership = False
    if 'top_10k' not in df.columns or 'top_100k' not in df.columns:
        needs_ownership = True
    elif (df['top_10k'] == 0).all() and (df['top_100k'] == 0).all():
        needs_ownership = True

    if needs_ownership:
        import os
        ownership_paths = [
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "streamlit", "fpl_ownership.csv"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "fpl_ownership.csv"),
            "fpl_ownership.csv",
            "streamlit/fpl_ownership.csv"
        ]
        for op in ownership_paths:
            if os.path.exists(op):
                try:
                    df_own = pd.read_csv(op)
                    if 'fpl_id' in df_own.columns and 'id' in df.columns:
                        d10 = dict(zip(df_own['fpl_id'], df_own['top_10k']))
                        d100 = dict(zip(df_own['fpl_id'], df_own['top_100k']))
                        df['top_10k'] = df['id'].map(d10).fillna(0.0)
                        df['top_100k'] = df['id'].map(d100).fillna(0.0)
                except Exception:
                    pass
                break

    for c in ['top_10k', 'top_100k', 'transfers_in_24', 'transfers_out_24',
              'price_change_percent', 'price_change_hourly_rate',
              'pp1', 'likelihood1', 'pp2', 'likelihood2', 'pp3', 'likelihood3']:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0)
        else:
            df[c] = 0.0

    if 'price_change_locked_until' in df.columns:
        df['price_change_locked_until'] = df['price_change_locked_until'].fillna("").astype(str).replace({'None': '', 'nan': '', 'NaN': ''})
    else:
        df['price_change_locked_until'] = ""

    if 'price_change_calibrating' in df.columns:
        df['price_change_calibrating'] = df['price_change_calibrating'].fillna(False).astype(bool)
    else:
        df['price_change_calibrating'] = False

    sort_cols = [c for c in ['price_change_percent', 'price_change_hourly_rate', 'now_cost'] if c in df.columns]
    if sort_cols:
        df = df.sort_values(by=sort_cols, ascending=[False, False, False][:len(sort_cols)])

    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"Помилка завантаження: {e}")
    st.stop()

display_columns = [
    "full_name",
    "Age",
    "element_type",
    "Play Pos",
    "team_short_name",
    "now_cost",
    "selected_by_percent",
    "top_10k",
    "top_100k",
    "transfers_in_24",
    "transfers_out_24",
    "price_change_percent",
    "price_change_hourly_rate",
    "pp1",
    "likelihood1",
    "pp2",
    "likelihood2",
    "pp3",
    "likelihood3",
    "price_change_locked_until",
    "price_change_calibrating"
]

all_teams = sorted(df['team_short_name'].unique().tolist())
pos_order = ['GK', 'DEF', 'MID', 'FW']
actual_pos = df['element_type'].unique().tolist()
sorted_positions = [p for p in pos_order if p in actual_pos] + sorted([p for p in actual_pos if p not in pos_order])

pl_lines = [['GK'], ['RB', 'CB', 'LB'], ['RM', 'DM', 'CM', 'LM'], ['RW', 'AM', 'LW'], ['SS', 'CF']]
defined_pl_pos = [p for line in pl_lines for p in line]
actual_pl_pos = df['Play Pos'].dropna().unique().tolist()
others = sorted([p for p in actual_pl_pos if p not in defined_pl_pos])
if others:
    pl_lines.append(others)
all_pl_pos = [p for line in pl_lines for p in line if p in actual_pl_pos]


def _slider_bounds(min_val, max_val, default_span=1.0):
    mn = float(min_val)
    mx = float(max_val)
    if mn >= mx:
        mx = mn + default_span
    return (mn, mx)


def _get_max(col, default=1.0):
    return float(df[col].max()) if col in df.columns and not df[col].dropna().empty else default


def _get_min(col, default=0.0):
    return float(df[col].min()) if col in df.columns and not df[col].dropna().empty else default


GB = {
    'f_cost_pc':     _slider_bounds(_get_min('now_cost', 4.0), _get_max('now_cost', 15.0)),
    'f_selected_pc': _slider_bounds(_get_min('selected_by_percent', 0.0), _get_max('selected_by_percent', 100.0)),
    'f_top10k_pc':   _slider_bounds(_get_min('top_10k', 0.0), _get_max('top_10k', 100.0)),
    'f_top100k_pc':  _slider_bounds(_get_min('top_100k', 0.0), _get_max('top_100k', 100.0)),
    'f_progress_pc': _slider_bounds(_get_min('price_change_percent', -100.0), _get_max('price_change_percent', 100.0)),
    'f_hrate_pc':    _slider_bounds(_get_min('price_change_hourly_rate', -50.0), _get_max('price_change_hourly_rate', 50.0)),
    'f_proj1_pc':    _slider_bounds(_get_min('pp1', -100.0), _get_max('pp1', 100.0)),
    'f_proj2_pc':    _slider_bounds(_get_min('pp2', -100.0), _get_max('pp2', 100.0)),
    'f_proj3_pc':    _slider_bounds(_get_min('pp3', -100.0), _get_max('pp3', 100.0)),
}

DEFAULTS = {
    'f_cost_pc':     GB['f_cost_pc'],
    'f_selected_pc': GB['f_selected_pc'],
    'f_top10k_pc':   GB['f_top10k_pc'],
    'f_top100k_pc':  GB['f_top100k_pc'],
    'f_progress_pc': GB['f_progress_pc'],
    'f_hrate_pc':    GB['f_hrate_pc'],
    'f_proj1_pc':    GB['f_proj1_pc'],
    'f_proj2_pc':    GB['f_proj2_pc'],
    'f_proj3_pc':    GB['f_proj3_pc'],
}

if 'pills_teams_pc' not in st.session_state:
    st.session_state.pills_teams_pc = all_teams
if 'pills_pos_pc' not in st.session_state:
    st.session_state.pills_pos_pc = sorted_positions
if 'pills_pl_pos_pc' not in st.session_state:
    st.session_state.pills_pl_pos_pc = all_pl_pos


def _pills_snapshot():
    snap = {
        'pos':    tuple(sorted(st.session_state.get('pills_pos_pc',   sorted_positions) or [])),
        'teams':  tuple(sorted(st.session_state.get('pills_teams_pc', all_teams) or [])),
        'search': st.session_state.get('search_name_pc', ''),
    }
    for i, line in enumerate(pl_lines):
        avail = [p for p in line if p in actual_pl_pos]
        snap[f'pl_{i}'] = tuple(sorted(st.session_state.get(f'pills_pl_line_pc_{i}', avail)))
    return snap


def _safe_range(key, default):
    val = st.session_state.get(key, default)
    if isinstance(val, (tuple, list)) and len(val) == 2:
        if val[0] < val[1]:
            return val
    return default


def get_available(exclude_key=None):
    cv_pos = st.session_state.get('pills_pos_pc', sorted_positions) or []
    cv_teams = st.session_state.get('pills_teams_pc', all_teams) or []
    cv_search = st.session_state.get('search_name_pc', '')
    cv_cost = _safe_range('f_cost_pc', DEFAULTS['f_cost_pc'])
    cv_selected = _safe_range('f_selected_pc', DEFAULTS['f_selected_pc'])
    cv_top10k = _safe_range('f_top10k_pc', DEFAULTS['f_top10k_pc'])
    cv_top100k = _safe_range('f_top100k_pc', DEFAULTS['f_top100k_pc'])
    cv_progress = _safe_range('f_progress_pc', DEFAULTS['f_progress_pc'])
    cv_hrate = _safe_range('f_hrate_pc', DEFAULTS['f_hrate_pc'])
    cv_proj1 = _safe_range('f_proj1_pc', DEFAULTS['f_proj1_pc'])
    cv_proj2 = _safe_range('f_proj2_pc', DEFAULTS['f_proj2_pc'])
    cv_proj3 = _safe_range('f_proj3_pc', DEFAULTS['f_proj3_pc'])

    cv_pl_pos = []
    for i, line in enumerate(pl_lines):
        avail = [p for p in line if p in actual_pl_pos]
        cv_pl_pos.extend(st.session_state.get(f'pills_pl_line_pc_{i}', avail))

    mask = pd.Series([True] * len(df), index=df.index)
    if exclude_key != 'pills_pos_pc':
        mask &= df['element_type'].isin(cv_pos)
    if exclude_key != 'pills_teams_pc':
        mask &= df['team_short_name'].isin(cv_teams)
    if exclude_key != 'pills_pl_pc':
        if cv_pl_pos:
            if len(cv_pl_pos) == len(all_pl_pos):
                mask &= (df['Play Pos'].isin(cv_pl_pos) | df['Play Pos'].isna())
            else:
                mask &= df['Play Pos'].isin(cv_pl_pos)
    if exclude_key != 'f_cost_pc':
        mask &= (df['now_cost'] >= cv_cost[0]) & (df['now_cost'] <= cv_cost[1])
    if exclude_key != 'f_selected_pc':
        mask &= (df['selected_by_percent'] >= cv_selected[0]) & (df['selected_by_percent'] <= cv_selected[1])
    if exclude_key != 'f_top10k_pc':
        mask &= (df['top_10k'] >= cv_top10k[0]) & (df['top_10k'] <= cv_top10k[1])
    if exclude_key != 'f_top100k_pc':
        mask &= (df['top_100k'] >= cv_top100k[0]) & (df['top_100k'] <= cv_top100k[1])
    if exclude_key != 'f_progress_pc':
        mask &= (df['price_change_percent'] >= cv_progress[0]) & (df['price_change_percent'] <= cv_progress[1])
    if exclude_key != 'f_hrate_pc':
        mask &= (df['price_change_hourly_rate'] >= cv_hrate[0]) & (df['price_change_hourly_rate'] <= cv_hrate[1])
    if exclude_key != 'f_proj1_pc':
        mask &= (df['pp1'] >= cv_proj1[0]) & (df['pp1'] <= cv_proj1[1])
    if exclude_key != 'f_proj2_pc':
        mask &= (df['pp2'] >= cv_proj2[0]) & (df['pp2'] <= cv_proj2[1])
    if exclude_key != 'f_proj3_pc':
        mask &= (df['pp3'] >= cv_proj3[0]) & (df['pp3'] <= cv_proj3[1])
    if exclude_key != 'search_name_pc':
        mask &= df['full_name'].str.contains(cv_search, case=False, na=False)
    return df[mask]


def get_base_df(exclude_key=None):
    cv_pos = st.session_state.get('pills_pos_pc', sorted_positions) or []
    cv_teams = st.session_state.get('pills_teams_pc', all_teams) or []
    cv_search = st.session_state.get('search_name_pc', '')

    cv_pl_pos = []
    for i, line in enumerate(pl_lines):
        avail = [p for p in line if p in actual_pl_pos]
        cv_pl_pos.extend(st.session_state.get(f'pills_pl_line_pc_{i}', avail))

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

    return df[mask]


def auto_update_slider(key, col, cast=float):
    hash_key = f'_hash_{key}'
    current_hash = str(_pills_snapshot())
    prev_hash = st.session_state.get(hash_key)

    if prev_hash == current_hash and key in st.session_state:
        return

    series = get_base_df(key)[col].dropna()

    if series.empty:
        st.session_state[hash_key] = current_hash
        if key not in st.session_state:
            st.session_state[key] = DEFAULTS[key]
        return

    avail_min = cast(series.min())
    avail_max = cast(series.max())
    def_lower = cast(DEFAULTS[key][0])
    gb_upper = cast(GB[key][1])

    new_lower = max(def_lower, avail_min)
    new_upper = min(gb_upper, avail_max)

    if new_lower >= new_upper:
        new_lower = def_lower
        new_upper = gb_upper

    st.session_state[key] = (new_lower, new_upper)
    st.session_state[hash_key] = current_hash


def filter_header(label, options, key_prefix):
    cols = st.sidebar.columns([1.4, 0.8, 0.8])
    cols[0].markdown(f"<p style='font-size:0.875rem;margin-bottom:0'>{label}</p>", unsafe_allow_html=True)
    if cols[1].button("All", key=f"btn_all_{key_prefix}", width="stretch"):
        st.session_state[f"pills_{key_prefix}"] = options
        if "pl_pos" in key_prefix:
            for i, line in enumerate(pl_lines):
                st.session_state[f"pills_pl_line_pc_{i}"] = [p for p in options if p in line]
        st.rerun()
    if cols[2].button("None", key=f"btn_none_{key_prefix}", width="stretch"):
        st.session_state[f"pills_{key_prefix}"] = []
        if "pl_pos" in key_prefix:
            for i, line in enumerate(pl_lines):
                st.session_state[f"pills_pl_line_pc_{i}"] = []
        st.rerun()


def inject_sidebar_layout(inactive_all: list):
    js = f'''
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
                    }} else {{
                        b.style.setProperty('width', '60px', 'important');
                        b.style.setProperty('min-width', '60px', 'important');
                        b.style.setProperty('max-width', '60px', 'important');
                    }}

                    var expectedOpacity = inactiveList.includes(txt) ? '0.3' : '';
                    if (b.style.opacity !== expectedOpacity) {{
                        b.style.opacity = expectedOpacity;
                    }}
                }} );
            }} catch(e) {{}}
        }}

        setInterval(forceLayout, 300);
    }} )();
    </script>
    '''
    st.components.v1.html(js, height=0, scrolling=False)


# Автооновлення слайдерів
auto_update_slider('f_cost_pc', 'now_cost', cast=float)
auto_update_slider('f_selected_pc', 'selected_by_percent', cast=float)
auto_update_slider('f_top10k_pc', 'top_10k', cast=float)
auto_update_slider('f_top100k_pc', 'top_100k', cast=float)
auto_update_slider('f_progress_pc', 'price_change_percent', cast=float)
auto_update_slider('f_hrate_pc', 'price_change_hourly_rate', cast=float)
auto_update_slider('f_proj1_pc', 'pp1', cast=float)
auto_update_slider('f_proj2_pc', 'pp2', cast=float)
auto_update_slider('f_proj3_pc', 'pp3', cast=float)


# ========================== САЙДБАР ==========================

if st.sidebar.button("Reset All Filters", width="stretch", type="primary"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# 1. Search Player
search_name = st.sidebar.text_input("Search Player", placeholder="Enter name...", key="search_name_pc")

# 2. FPL Position
avail_pos = set(get_available('pills_pos_pc')['element_type'].unique())
filter_header("FPL Position", sorted_positions, "pos_pc")
selected_positions = st.sidebar.pills(
    "FPL Position", options=sorted_positions, key="pills_pos_pc",
    selection_mode="multi", label_visibility="collapsed"
)

# 3. FPL Price
f_cost = st.sidebar.slider(
    "FPL Price", GB['f_cost_pc'][0], GB['f_cost_pc'][1],
    _safe_range('f_cost_pc', DEFAULTS['f_cost_pc']),
    step=0.1, format="%.1f", key="f_cost_pc"
)

# 4. Team
avail_teams = set(get_available('pills_teams_pc')['team_short_name'].unique())
filter_header("Team", all_teams, "teams_pc")
selected_teams = st.sidebar.pills(
    "Team", options=all_teams, key="pills_teams_pc",
    selection_mode="multi", label_visibility="collapsed"
)

# 5. Playing Position
avail_pl = set(get_available('pills_pl_pc')['Play Pos'].dropna().unique())
filter_header("Playing Position", all_pl_pos, "pl_pos_pc")
selected_pl_pos = []

for idx, line in enumerate(pl_lines):
    available_in_line = [p for p in line if p in actual_pl_pos]
    if not available_in_line:
        continue
    line_key = f"pills_pl_line_pc_{idx}"
    if line_key not in st.session_state:
        st.session_state[line_key] = [p for p in st.session_state.pills_pl_pos_pc if p in available_in_line]

    line_res = st.sidebar.pills(
        label=f"pl_line_pc_{idx}", options=available_in_line, key=line_key,
        selection_mode="multi", label_visibility="collapsed"
    )
    if line_res:
        selected_pl_pos.extend(line_res)

all_inactive = []
all_inactive.extend([p for p in sorted_positions if p not in avail_pos])
all_inactive.extend([t for t in all_teams if t not in avail_teams])
all_inactive.extend([p for p in all_pl_pos if p not in avail_pl])
inject_sidebar_layout(all_inactive)

# 6. Ownership Block (Selected %, Top 10K %, Top 100K %)
with st.sidebar.expander("Ownership", expanded=False):
    f_selected = st.slider("Selected %", GB['f_selected_pc'][0], GB['f_selected_pc'][1], _safe_range('f_selected_pc', DEFAULTS['f_selected_pc']), step=0.1, key="f_selected_pc")
    f_top10k = st.slider("Top 10K %", GB['f_top10k_pc'][0], GB['f_top10k_pc'][1], _safe_range('f_top10k_pc', DEFAULTS['f_top10k_pc']), step=0.1, key="f_top10k_pc")
    f_top100k = st.slider("Top 100K %", GB['f_top100k_pc'][0], GB['f_top100k_pc'][1], _safe_range('f_top100k_pc', DEFAULTS['f_top100k_pc']), step=0.1, key="f_top100k_pc")

# 7. Price Changes Block (Progress, HRate, Proj1 %, Proj2 %, Proj3 %)
with st.sidebar.expander("Price Projections", expanded=False):
    f_progress = st.slider("Progress %", GB['f_progress_pc'][0], GB['f_progress_pc'][1], _safe_range('f_progress_pc', DEFAULTS['f_progress_pc']), step=0.5, key="f_progress_pc")
    f_hrate = st.slider("Hourly Rate (HRate)", GB['f_hrate_pc'][0], GB['f_hrate_pc'][1], _safe_range('f_hrate_pc', DEFAULTS['f_hrate_pc']), step=1.0, key="f_hrate_pc")
    f_proj1 = st.slider("Proj1 %", GB['f_proj1_pc'][0], GB['f_proj1_pc'][1], _safe_range('f_proj1_pc', DEFAULTS['f_proj1_pc']), step=0.5, key="f_proj1_pc")
    f_proj2 = st.slider("Proj2 %", GB['f_proj2_pc'][0], GB['f_proj2_pc'][1], _safe_range('f_proj2_pc', DEFAULTS['f_proj2_pc']), step=0.5, key="f_proj2_pc")
    f_proj3 = st.slider("Proj3 %", GB['f_proj3_pc'][0], GB['f_proj3_pc'][1], _safe_range('f_proj3_pc', DEFAULTS['f_proj3_pc']), step=0.5, key="f_proj3_pc")


# ========================== ФІЛЬТРАЦІЯ ==========================

if selected_pl_pos:
    if len(selected_pl_pos) == len(all_pl_pos):
        play_pos_mask = (df['Play Pos'].isin(selected_pl_pos) | df['Play Pos'].isna())
    else:
        play_pos_mask = df['Play Pos'].isin(selected_pl_pos)
else:
    play_pos_mask = pd.Series([False] * len(df), index=df.index)

mask = (
    df['element_type'].isin(selected_positions if selected_positions else []) &
    df['team_short_name'].isin(selected_teams if selected_teams else []) &
    play_pos_mask &
    (df['now_cost'] >= f_cost[0]) & (df['now_cost'] <= f_cost[1]) &
    (df['price_change_percent'] >= f_progress[0]) & (df['price_change_percent'] <= f_progress[1]) &
    (df['price_change_hourly_rate'] >= f_hrate[0]) & (df['price_change_hourly_rate'] <= f_hrate[1]) &
    (df['pp1'] >= f_proj1[0]) & (df['pp1'] <= f_proj1[1]) &
    (df['pp2'] >= f_proj2[0]) & (df['pp2'] <= f_proj2[1]) &
    (df['pp3'] >= f_proj3[0]) & (df['pp3'] <= f_proj3[1]) &
    (df['selected_by_percent'] >= f_selected[0]) & (df['selected_by_percent'] <= f_selected[1]) &
    (df['top_10k'] >= f_top10k[0]) & (df['top_10k'] <= f_top10k[1]) &
    (df['top_100k'] >= f_top100k[0]) & (df['top_100k'] <= f_top100k[1]) &
    (df['full_name'].str.contains(search_name, case=False, na=False))
)

filtered_df = df[mask].copy()

sort_cols = [c for c in ['price_change_percent', 'price_change_hourly_rate', 'now_cost'] if c in filtered_df.columns]
if sort_cols:
    filtered_df = filtered_df.sort_values(by=sort_cols, ascending=[False, False, False][:len(sort_cols)])

st.subheader(f"Players filtered: {len(filtered_df)}", anchor=False)
existing_display_cols = [c for c in display_columns if c in filtered_df.columns]

format_map = {
    "full_name":                ("TextColumn", None, "Player"),
    "Age":                      ("NumberColumn", "%d", "Age"),
    "element_type":             ("TextColumn", None, "Pos"),
    "Play Pos":                 ("TextColumn", None, "Pl Pos"),
    "team_short_name":          ("TextColumn", None, "Team"),
    "now_cost":                 ("NumberColumn", "%.1f", "Price"),
    "selected_by_percent":      ("NumberColumn", "%.1f%%", "Sel %"),
    "top_10k":                  ("NumberColumn", "%.1f%%", "Top10K"),
    "top_100k":                 ("NumberColumn", "%.1f%%", "Top100K"),
    "transfers_in_24":          ("NumberColumn", None, "In 24"),
    "transfers_out_24":         ("NumberColumn", None, "Out 24"),
    "price_change_percent":     ("NumberColumn", "%.1f", "Progress"),
    "price_change_hourly_rate": ("NumberColumn", "%d", "HRate"),
    "pp1":                      ("NumberColumn", "%.1f", "Proj1 %"),
    "likelihood1":              ("NumberColumn", "%d", "Likely1"),
    "pp2":                      ("NumberColumn", "%.1f", "Proj2 %"),
    "likelihood2":              ("NumberColumn", "%d", "Likely2"),
    "pp3":                      ("NumberColumn", "%.1f", "Proj3 %"),
    "likelihood3":              ("NumberColumn", "%d", "Likely3"),
    "price_change_locked_until":("TextColumn", None, "Locked"),
    "price_change_calibrating": ("CheckboxColumn", None, "Calibrating"),
}

base_widths = {}
for col in existing_display_cols:
    col_label = format_map.get(col, ("", "", col))[2]
    if not filtered_df.empty and col in filtered_df.columns:
        val_series = filtered_df[col].dropna().astype(str)
        val_nonzero = val_series[val_series.str.strip() != '']
        max_val_len = int(val_nonzero.str.len().max()) if not val_nonzero.empty else len(col_label)
        max_val_len = max(max_val_len, len(col_label))
    else:
        max_val_len = len(col_label)

    bw = max_val_len * 6
    if col == "full_name":
        bw = 160
    elif col == "price_change_locked_until":
        bw = min(bw, 100)
    elif col == "price_change_calibrating":
        bw = min(bw, 55)
    elif col in ["top_10k", "top_100k", "selected_by_percent"]:
        bw = max(bw, 44)
    elif col in ["transfers_in_24", "transfers_out_24"]:
        bw = max(bw, 38)
    elif col in ["price_change_percent", "pp1", "pp2", "pp3"]:
        bw = max(bw, 44)
    else:
        bw = min(bw, 36)
    base_widths[col] = max(bw, 10)

inv_weights = {col: 1.0 / (w ** 0.5) for col, w in base_widths.items()}
sum_inv_weights = sum(inv_weights.values())
TOTAL_PADDING_BUDGET = 150

smart_column_config = {}

for col in existing_display_cols:
    col_type, col_fmt, col_label = format_map.get(col, ("Column", None, col))

    bw = base_widths[col]
    bonus = (inv_weights[col] / sum_inv_weights) * TOTAL_PADDING_BUDGET
    calc_w = int(round(bw + bonus))

    if col == "full_name":
        calc_w = 160
    elif col == "price_change_locked_until":
        calc_w = max(calc_w, 95)
    elif col == "price_change_calibrating":
        calc_w = max(calc_w, 55)
    elif col in ["top_10k", "top_100k", "selected_by_percent"]:
        calc_w = max(calc_w, 44)
    elif col in ["transfers_in_24", "transfers_out_24"]:
        calc_w = max(calc_w, 38)
    elif col in ["price_change_percent", "pp1", "pp2", "pp3"]:
        calc_w = max(calc_w, 46)
    else:
        calc_w = max(calc_w, 36)

    kwargs = {"label": col_label, "width": calc_w}
    if col == "full_name":
        kwargs["pinned"] = True
    if col_fmt:
        kwargs["format"] = col_fmt

    if col_type == "NumberColumn":
        smart_column_config[col] = st.column_config.NumberColumn(**kwargs)
    elif col_type == "TextColumn":
        smart_column_config[col] = st.column_config.TextColumn(**kwargs)
    elif col_type == "CheckboxColumn":
        smart_column_config[col] = st.column_config.CheckboxColumn(**kwargs)
    else:
        smart_column_config[col] = st.column_config.Column(**kwargs)

st.dataframe(
    filtered_df[existing_display_cols],
    width="stretch",
    hide_index=True,
    height=800,
    column_config=smart_column_config
)
