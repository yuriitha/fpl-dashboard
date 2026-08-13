import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import plotly.graph_objects as go
import json


st.set_page_config(
    page_title="FPL Rating Graph",
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
        .league-origin-wrapper [data-testid="stPills"] {
            display: grid !important;
            grid-template-columns: 1fr 1fr 1fr !important;
            gap: 4px !important;
            width: 100% !important;
        }
        .league-origin-wrapper button {
            width: 100% !important; min-width: 0px !important; max-width: none !important;
            text-align: center !important; justify-content: center !important;
            padding: 0px 2px !important; font-size: 0.7rem !important;
        }
    </style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=300)
def load_data():
    url = "http://198.244.151.163:8000/fpl_players"
    df = pd.read_parquet(url)
    if 'av_rating_alt' in df.columns:
        df['av_rating_alt'] = pd.to_numeric(df['av_rating_alt'], errors='coerce').fillna(0.0)
    sort_cols = [c for c in ['now_cost', 'M Price'] if c in df.columns]
    if sort_cols:
        df = df.sort_values(by=sort_cols, ascending=[False] * len(sort_cols))

    for h2_col in ['av_rating_alt_h2', 'xGI_norm_h2', 'avg_mins_h2', '60_min_h2', 'matches_played_h2']:
        if h2_col not in df.columns:
            base_col = h2_col.replace('_h2', '')
            df[h2_col] = df[base_col] if base_col in df.columns else 0.0


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

rating_series = df[df['av_rating_alt'] > 0]['av_rating_alt'].dropna()
r_min = float(rating_series.min()) if not rating_series.empty else 0.0
r_max = float(rating_series.max()) if not rating_series.empty and rating_series.max() > 0 else 10.0

def _slider_bounds(min_val, max_val, default_span=1.0):
    mn = float(min_val)
    mx = float(max_val)
    if mn >= mx:
        mx = mn + default_span
    return (mn, mx)


GB = {
    'f_cost':     _slider_bounds(df['now_cost'].min(),            df['now_cost'].max(), 1.0),
    'f_matches':  (int(df['matches_played'].min()),        max(int(df['matches_played'].max()), int(df['matches_played'].min()) + 1)),
    'f_rating':   _slider_bounds(r_min,                           r_max, 1.0),
    'f_avg_mins': _slider_bounds(df['avg_mins'].min(),            df['avg_mins'].max(), 1.0),
    'f_60min':    _slider_bounds(df['60_min'].min(),              df['60_min'].max(), 1.0),
    'f_selected': _slider_bounds(df['selected_by_percent'].min(), df['selected_by_percent'].max(), 1.0),
    'f_activity': _slider_bounds(df['transfer_activity_pct'].min(), df['transfer_activity_pct'].max(), 100.0),
}

DEFAULTS = {
    'f_cost':     GB['f_cost'],
    'f_matches':  (6,    GB['f_matches'][1]),
    'f_rating':   GB['f_rating'],
    'f_avg_mins': (35.0, GB['f_avg_mins'][1]),
    'f_60min':    GB['f_60min'],
    'f_selected': GB['f_selected'],
    'f_activity': GB['f_activity'],
}


if 'pills_teams_gr'  not in st.session_state: st.session_state.pills_teams_gr  = default_teams
if 'pills_pos_gr'    not in st.session_state: st.session_state.pills_pos_gr    = [p for p in sorted_positions if p != 'GK']
if 'pills_pl_pos_gr' not in st.session_state: st.session_state.pills_pl_pos_gr = all_pl_pos


def _pills_snapshot():
    snap = {
        'pos':    tuple(sorted(st.session_state.get('pills_pos_gr',   [p for p in sorted_positions if p != 'GK']) or [])),
        'teams':  tuple(sorted(st.session_state.get('pills_teams_gr', default_teams) or [])),
        'search': st.session_state.get('search_name_gr', ''),
    }
    for i, line in enumerate(pl_lines):
        avail = [p for p in line if p in actual_pl_pos]
        snap[f'pl_{i}'] = tuple(sorted(st.session_state.get(f'pills_pl_line_gr_{i}', avail)))
    return snap

def _safe_range(key, default):
    val = st.session_state.get(key, default)
    if isinstance(val, (tuple, list)) and len(val) == 2:
        if val[0] < val[1]:
            return val
    return default

def get_available(exclude_key=None):
    cv_pos      = st.session_state.get('pills_pos_gr',   [p for p in sorted_positions if p != 'GK']) or []
    cv_teams    = st.session_state.get('pills_teams_gr', default_teams) or []
    cv_matches  = _safe_range('f_matches_gr',  DEFAULTS['f_matches'])
    cv_60min    = _safe_range('f_60min_gr',    DEFAULTS['f_60min'])
    cv_cost     = _safe_range('f_cost_gr',     DEFAULTS['f_cost'])
    cv_avg_mins = _safe_range('f_avg_mins_gr', DEFAULTS['f_avg_mins'])
    cv_selected = _safe_range('f_selected_gr', DEFAULTS['f_selected'])
    cv_activity = _safe_range('f_activity_gr', DEFAULTS['f_activity'])
    cv_rating   = _safe_range('f_rating_gr',   DEFAULTS['f_rating'])
    cv_search   = st.session_state.get('search_name_gr', '')

    cv_pl_pos = []
    for i, line in enumerate(pl_lines):
        avail = [p for p in line if p in actual_pl_pos]
        cv_pl_pos.extend(st.session_state.get(f'pills_pl_line_gr_{i}', avail))

    mask = pd.Series([True] * len(df), index=df.index) & (df['av_rating_alt'] > 0)
    if exclude_key != 'pills_pos_gr':   mask &= df['element_type'].isin(cv_pos)
    if exclude_key != 'pills_teams_gr': mask &= df['team_short_name'].isin(cv_teams)
    if exclude_key != 'pills_pl_gr':
        if cv_pl_pos:
            if len(cv_pl_pos) == len(all_pl_pos):
                mask &= (df['Play Pos'].isin(cv_pl_pos) | df['Play Pos'].isna())
            else:
                mask &= df['Play Pos'].isin(cv_pl_pos)
    if exclude_key != 'f_matches_gr':
        mask &= (df['matches_played'] >= cv_matches[0]) & (df['matches_played'] <= cv_matches[1])
    if exclude_key != 'f_60min_gr':
        mask &= (df['60_min'] >= cv_60min[0]) & (df['60_min'] <= cv_60min[1])
    if exclude_key != 'f_cost_gr':
        mask &= (df['now_cost'] >= cv_cost[0]) & (df['now_cost'] <= cv_cost[1])
    if exclude_key != 'f_avg_mins_gr':
        mask &= (df['avg_mins'] >= cv_avg_mins[0]) & (df['avg_mins'] <= cv_avg_mins[1])
    if exclude_key != 'f_selected_gr':
        mask &= (df['selected_by_percent'] >= cv_selected[0]) & (df['selected_by_percent'] <= cv_selected[1])
    if exclude_key != 'f_activity_gr':
        mask &= (df['transfer_activity_pct'] >= cv_activity[0]) & (df['transfer_activity_pct'] <= cv_activity[1])
    if exclude_key != 'f_rating_gr':
        mask &= (df['av_rating_alt'] >= cv_rating[0]) & (df['av_rating_alt'] <= cv_rating[1])
    if exclude_key != 'search_gr':
        mask &= df['full_name'].str.contains(cv_search, case=False, na=False)
    return df[mask]

def get_base_df(exclude_key=None):
    cv_pos    = st.session_state.get('pills_pos_gr',   [p for p in sorted_positions if p != 'GK']) or []
    cv_teams  = st.session_state.get('pills_teams_gr', default_teams) or []
    cv_search = st.session_state.get('search_name_gr', '')

    cv_pl_pos = []
    for i, line in enumerate(pl_lines):
        avail = [p for p in line if p in actual_pl_pos]
        cv_pl_pos.extend(st.session_state.get(f'pills_pl_line_gr_{i}', avail))

    mask = (
        (df['av_rating_alt'] > 0) &
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
        'f_matches_gr':  ('matches_played',      DEFAULTS['f_matches']),
        'f_60min_gr':    ('60_min',              DEFAULTS['f_60min']),
        'f_cost_gr':     ('now_cost',            DEFAULTS['f_cost']),
        'f_avg_mins_gr': ('avg_mins',            DEFAULTS['f_avg_mins']),
        'f_selected_gr': ('selected_by_percent', DEFAULTS['f_selected']),
        'f_activity_gr': ('transfer_activity_pct', DEFAULTS['f_activity']),
        'f_rating_gr':   ('av_rating_alt',       DEFAULTS['f_rating']),
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
    if cols[1].button("All", key=f"btn_all_{key_prefix}", width="stretch"):
        st.session_state[f"pills_{key_prefix}"] = options
        if key_prefix == "pl_pos_gr":
            for i, line in enumerate(pl_lines):
                st.session_state[f"pills_pl_line_gr_{i}"] = [p for p in options if p in line]
        st.rerun()
    if cols[2].button("None", key=f"btn_none_{key_prefix}", width="stretch"):
        st.session_state[f"pills_{key_prefix}"] = []
        if key_prefix == "pl_pos_gr":
            for i, line in enumerate(pl_lines):
                st.session_state[f"pills_pl_line_gr_{i}"] = []
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

                    if (txt === "Reset All Filters" || txt === "None") return;
                    if ((b.closest && b.closest('.league-origin-wrapper')) || txt === "Premier League" || txt === "Other Leagues") {{
                        b.style.setProperty('width', '100%', 'important');
                        b.style.setProperty('min-width', '0px', 'important');
                        b.style.setProperty('max-width', 'none', 'important');
                        b.style.setProperty('justify-content', 'center', 'important');
                        b.style.setProperty('text-align', 'center', 'important');
                        b.style.setProperty('padding', '0px 2px', 'important');
                        b.style.setProperty('font-size', '0.7rem', 'important');

                        var pCont = b.closest('[data-testid="stPills"]');
                        if (pCont) {{
                            pCont.style.setProperty('display', 'grid', 'important');
                            pCont.style.setProperty('grid-template-columns', '1fr 1fr 1fr', 'important');
                            pCont.style.setProperty('gap', '4px', 'important');
                            pCont.style.setProperty('width', '100%', 'important');
                        }}
                        return;
                    }}

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


auto_update_slider('f_cost_gr',     'f_cost',     'now_cost',            float)
auto_update_slider('f_matches_gr',  'f_matches',  'matches_played',      int)
auto_update_slider('f_rating_gr',   'f_rating',   'av_rating_alt',       float)
auto_update_slider('f_avg_mins_gr', 'f_avg_mins', 'avg_mins',            float)
auto_update_slider('f_60min_gr',    'f_60min',    '60_min',              float)
auto_update_slider('f_selected_gr', 'f_selected', 'selected_by_percent', float)
auto_update_slider('f_activity_gr', 'f_activity', 'transfer_activity_pct', float)


if st.sidebar.button("Reset All Filters", width="stretch", type="primary"):
    keys_to_delete = [k for k in st.session_state.keys() if '_gr' in k]
    for key in keys_to_delete:
        del st.session_state[key]
    st.rerun()

search_name = st.sidebar.text_input("Search Player", placeholder="Enter name...", key="search_name_gr")


avail_pos = set(get_available('pills_pos_gr')['element_type'].unique())
filter_header("FPL Position", sorted_positions, "pos_gr")
selected_positions = st.sidebar.pills(
    "FPL Position", options=sorted_positions, key="pills_pos_gr",
    selection_mode="multi", label_visibility="collapsed"
)


f_cost = st.sidebar.slider(
    "FPL Price", GB['f_cost'][0], GB['f_cost'][1], step=0.1, format="%.1f", key="f_cost_gr"
)


avail_teams = set(get_available('pills_teams_gr')['team_short_name'].unique())
filter_header("Team", all_teams, "teams_gr")
selected_teams = st.sidebar.pills(
    "Team", options=all_teams, key="pills_teams_gr",
    selection_mode="multi", label_visibility="collapsed"
)


avail_pl = set(get_available('pills_pl_gr')['Play Pos'].dropna().unique())
filter_header("Playing Position", all_pl_pos, "pl_pos_gr")
selected_pl_pos = []

for idx, line in enumerate(pl_lines):
    available_in_line = [p for p in line if p in actual_pl_pos]
    if not available_in_line:
        continue
    line_key = f"pills_pl_line_gr_{idx}"
    if line_key not in st.session_state:
        st.session_state[line_key] = [p for p in st.session_state.pills_pl_pos_gr if p in available_in_line]

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
    f_matches  = st.slider("Matches",      GB['f_matches'][0],  GB['f_matches'][1],  step=1,    key="f_matches_gr")
    f_rating   = st.slider("Rating",       GB['f_rating'][0],   GB['f_rating'][1],   step=0.05, format="%.2f", key="f_rating_gr")
    f_avg_mins = st.slider("Average Mins", GB['f_avg_mins'][0], GB['f_avg_mins'][1], step=1.0,  key="f_avg_mins_gr")
    f_60min    = st.slider("60 Min %",     GB['f_60min'][0],    GB['f_60min'][1],    step=0.5,  key="f_60min_gr")


with st.sidebar.expander("Market & Popularity", expanded=False):
    f_selected = st.slider("Selected %",  GB['f_selected'][0], GB['f_selected'][1], step=0.1, key="f_selected_gr")
    f_activity = st.slider("Transfer Activity", GB['f_activity'][0], GB['f_activity'][1], step=1.0, format="%d%%", key="f_activity_gr")

st.sidebar.markdown('<div class="league-origin-wrapper">', unsafe_allow_html=True)
selected_league_origin = st.sidebar.pills(
    "League Origin",
    options=["All", "Premier League", "Other Leagues"],
    default="Premier League",
    key="pills_league_origin_gr",
    label_visibility="collapsed"
)
st.sidebar.markdown('</div>', unsafe_allow_html=True)


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
    (df['av_rating_alt'] > 0) &
    df['element_type'].isin(selected_positions if selected_positions else []) &
    df['team_short_name'].isin(selected_teams  if selected_teams  else []) &
    play_pos_mask &
    league_mask &
    (df['av_rating_alt']       >= f_rating[0])   & (df['av_rating_alt']       <= f_rating[1]) &
    (df['matches_played']      >= f_matches[0])  & (df['matches_played']      <= f_matches[1]) &
    (df['60_min']              >= f_60min[0])    & (df['60_min']              <= f_60min[1]) &
    (df['now_cost']            >= f_cost[0])     & (df['now_cost']            <= f_cost[1]) &
    (df['selected_by_percent'] >= f_selected[0]) & (df['selected_by_percent'] <= f_selected[1]) &
    (df['transfer_activity_pct'] >= f_activity[0]) & (df['transfer_activity_pct'] <= f_activity[1]) &
    (df['avg_mins']            >= f_avg_mins[0]) & (df['avg_mins']            <= f_avg_mins[1]) &
    (df['full_name'].str.contains(search_name, case=False, na=False))
)
plot_df = df[mask].copy()


POSITION_COLOR_MAP = {
    "GK":  "#E5A823",  # Deep Amber Gold
    "DEF": "#00A3E0",  # Ocean Cyan
    "MID": "#00B359",  # Rich Emerald
    "FW":  "#D92552"   # Deep Crimson
}


if not plot_df.empty:
    plot_df['p_selected'] = plot_df['selected_by_percent'].rank(pct=True)
    plot_df['p_avgmins'] = plot_df['avg_mins'].rank(pct=True)

    plot_df['combined_rank'] = (plot_df['p_selected'] + plot_df['p_avgmins']) / 2

    plot_df['size_for_plot'] = (plot_df['combined_rank'] ** 2) * 100 + 10


    plot_df['rating_sqrt'] = plot_df['av_rating_alt'] ** 0.5
    plot_df['xGI_sqrt'] = plot_df['xGI_norm'] ** 0.5

    min_mins_for_label = 60
    plot_df['label_text'] = np.where(
        (plot_df['avg_mins'] >= min_mins_for_label) | (plot_df['selected_by_percent'] > 10.0),
        plot_df['web_name'],
        ""
    )


    st.subheader(f"xGI vs Rating — 12-Month Performance (Players: {len(plot_df)})", anchor=False)

    fig = px.scatter(
        plot_df,
        x="rating_sqrt",
        y="xGI_sqrt",
        color="element_type",
        color_discrete_map=POSITION_COLOR_MAP,
        symbol="league_status",
        symbol_map={"Premier League": "circle", "Other Leagues": "diamond"},
        size="size_for_plot",
        hover_name="full_name",
        hover_data={
            "element_type": True,
            "team_short_name": True,
            "league_status": True,
            "now_cost": ":.1f",
            "av_rating_alt": ":.2f",
            "xGI_norm": ":.2f",
            "avg_mins": ":.0f",
            "selected_by_percent": ":.1f",
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
            "rating_sqrt": "Average Rating",
            "xGI_sqrt": "Expected Goal Involvement",
            "element_type": "Position",
            "team_short_name": "Team",
            "league_status": "League Origin",
            "now_cost": "Price",
            "av_rating_alt": "Rating",
            "xGI_norm": "xGI",
            "avg_mins": "AvMins",
            "selected_by_percent": "Sel %"
        },
        template="plotly_dark",
        size_max=20
    )

    fig.update_traces(
        textposition='bottom center',
        textfont=dict(size=10),
        marker=dict(opacity=0.75, line=dict(width=0.8, color='white'))
    )


    r_min, r_max = plot_df['av_rating_alt'].min(), plot_df['av_rating_alt'].max()
    if pd.isna(r_max) or r_max < 6.5:
        r_max = 10.0
    r_start = 6.5
    r_end = np.ceil(r_max * 10) / 10
    if r_end < r_start: r_end = r_start + 0.5
    r_ticks = np.arange(r_start, r_end + 0.05, 0.1).round(1)

    x_min, x_max = plot_df['xGI_norm'].min(), plot_df['xGI_norm'].max()
    if pd.isna(x_min) or pd.isna(x_max):
        x_min, x_max = 0.0, 1.2
    x_start = max(0.0, np.floor(x_min * 10) / 10)
    x_end = min(1.20, np.ceil(x_max * 10) / 10)
    if x_end < x_start: x_end = 1.20
    x_ticks = np.arange(x_start, x_end + 0.05, 0.1).round(1)

    fig.update_layout(
        height=800,
        margin=dict(l=0, r=0, t=40, b=0),
        xaxis=dict(
            title="Average Rating",
            gridcolor='rgba(255,255,255,0.1)',
            tickmode='array',
            tickvals=r_ticks ** 0.5,
            ticktext=r_ticks,
            range=[r_start ** 0.5, (r_end + 0.02) ** 0.5]
        ),
        yaxis=dict(
            title="Expected Goal Involvement",
            gridcolor='rgba(255,255,255,0.1)',
            tickmode='array',
            tickvals=x_ticks ** 0.5,
            ticktext=x_ticks,
            range=[x_start ** 0.5, (x_end + 0.02) ** 0.5]
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

    st.plotly_chart(fig, width="stretch")


    has_h2_rating = (df['av_rating_alt_h2'] > 0) if 'av_rating_alt_h2' in df.columns else (df['av_rating_alt'] > 0)
    mask_h2 = mask & has_h2_rating
    plot_df_h2 = df[mask_h2].copy()

    if not plot_df_h2.empty:
        plot_df_h2['p_selected'] = plot_df_h2['selected_by_percent'].rank(pct=True)
        plot_df_h2['p_avgmins'] = plot_df_h2['avg_mins_h2'].rank(pct=True) if 'avg_mins_h2' in plot_df_h2.columns else plot_df_h2['avg_mins'].rank(pct=True)
        plot_df_h2['combined_rank'] = (plot_df_h2['p_selected'] + plot_df_h2['p_avgmins']) / 2
        plot_df_h2['size_for_plot'] = (plot_df_h2['combined_rank'] ** 2) * 100 + 10

        plot_df_h2['rating_sqrt'] = plot_df_h2['av_rating_alt_h2'] ** 0.5
        plot_df_h2['xGI_sqrt'] = plot_df_h2['xGI_norm_h2'] ** 0.5

        plot_df_h2['label_text'] = np.where(
            (plot_df_h2['avg_mins'] >= 20) | (plot_df_h2['selected_by_percent'] > 10.0),
            plot_df_h2['web_name'],
            ""
        )

        st.markdown("<br><hr>", unsafe_allow_html=True)
        st.subheader(f"xGI vs Rating — 6-Month Performance (Players: {len(plot_df_h2)})", anchor=False)

        fig_h2 = px.scatter(
            plot_df_h2,
            x="rating_sqrt",
            y="xGI_sqrt",
            color="element_type",
            color_discrete_map=POSITION_COLOR_MAP,
            symbol="league_status",
            symbol_map={"Premier League": "circle", "Other Leagues": "diamond"},
            size="size_for_plot",
            hover_name="full_name",
            hover_data={
                "element_type": True,
                "team_short_name": True,
                "league_status": True,
                "now_cost": ":.1f",
                "av_rating_alt_h2": ":.2f",
                "xGI_norm_h2": ":.2f",
                "avg_mins_h2": ":.0f",
                "top_100k": ":.1f",
                "web_name": False,
                "matches_played_h2": False,
                "size_for_plot": False,
                "combined_rank": False,
                "rating_sqrt": False,
                "xGI_sqrt": False,
                "label_text": False
            },
            text="label_text",
            labels={
                "rating_sqrt": "Average Rating (6M)",
                "xGI_sqrt": "Expected Goal Involvement (6M)",
                "element_type": "Position",
                "team_short_name": "Team",
                "league_status": "League Origin",
                "now_cost": "Price",
                "av_rating_alt_h2": "Rating (6M)",
                "xGI_norm_h2": "xGI (6M)",
                "avg_mins_h2": "AvMins (6M)",
                "top_100k": "Top 100K %"
            },
            template="plotly_dark",
            size_max=20
        )

        fig_h2.update_traces(
            textposition='bottom center',
            textfont=dict(size=10),
            marker=dict(opacity=0.75, line=dict(width=0.8, color='white'))
        )

        r_min2, r_max2 = plot_df_h2['av_rating_alt_h2'].min(), plot_df_h2['av_rating_alt_h2'].max()
        if pd.isna(r_max2) or r_max2 < 6.5:
            r_max2 = 10.0
        r_start2 = 6.5
        r_end2 = np.ceil(r_max2 * 10) / 10
        if r_end2 < r_start2: r_end2 = r_start2 + 0.5
        r_ticks2 = np.arange(r_start2, r_end2 + 0.05, 0.1).round(1)

        x_min2, x_max2 = plot_df_h2['xGI_norm_h2'].min(), plot_df_h2['xGI_norm_h2'].max()
        if pd.isna(x_min2) or pd.isna(x_max2):
            x_min2, x_max2 = 0.0, 1.2
        x_start2 = max(0.0, np.floor(x_min2 * 10) / 10)
        x_end2 = min(1.20, np.ceil(x_max2 * 10) / 10)
        if x_end2 < x_start2: x_end2 = 1.20
        x_ticks2 = np.arange(x_start2, x_end2 + 0.05, 0.1).round(1)

        fig_h2.update_layout(
            height=800,
            margin=dict(l=0, r=0, t=40, b=0),
            xaxis=dict(
                title="Average Rating (6 Months)",
                gridcolor='rgba(255,255,255,0.1)',
                tickmode='array',
                tickvals=r_ticks2 ** 0.5,
                ticktext=r_ticks2,
                range=[r_start2 ** 0.5, (r_end2 + 0.02) ** 0.5]
            ),
            yaxis=dict(
                title="Expected Goal Involvement (6 Months)",
                gridcolor='rgba(255,255,255,0.1)',
                tickmode='array',
                tickvals=x_ticks2 ** 0.5,
                ticktext=x_ticks2,
                range=[x_start2 ** 0.5, (x_end2 + 0.02) ** 0.5]
            ),
            legend_title_text='',
            legend=dict(
                yanchor="top", y=0.99, xanchor="left", x=0.01,
                bgcolor="rgba(0,0,0,0.5)"
            )
        )

        st.plotly_chart(fig_h2, width="stretch")

else:
    st.warning("Немає даних для обраних фільтрів.")