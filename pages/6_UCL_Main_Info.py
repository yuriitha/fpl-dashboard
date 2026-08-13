import json
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="UCL Players Stats",
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
            padding-top: 2.5rem !important;
            padding-bottom: 1rem !important;
            max-width: 100% !important;
        }
        [data-testid="stTable"] th, [data-testid="stDataFrame"] th { text-align: center !important; }
        [data-testid="stDataFrame"] td { text-align: center !important; }

        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
            gap: 0.4rem !important;
        }

        [data-testid="stSidebar"] button[kind="primary"] {
            width: 100% !important; max-width: none !important;
        }

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
    url = "http://198.244.151.163:8000/ucl_players"
    df = pd.read_parquet(url)
    sort_cols = [c for c in ['Price', 'TM Value'] if c in df.columns]
    if sort_cols:
        df = df.sort_values(by=sort_cols, ascending=[False] * len(sort_cols))
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"Помилка завантаження: {e}")
    st.stop()

display_columns = [
    "Player", "Age", "Pos", "Pl Pos", "Team", "Team Name", "Price", "Foot",
    "TM Value", "Selected", "Mins", "G", "A",
    "POTM", "PPM", "Value", "In", "Out", "In 24", "Out 24"
]

all_teams = sorted(df['Team'].dropna().unique().tolist())
pos_order = ['GK', 'DEF', 'MID', 'FW']
actual_pos = df['Pos'].dropna().unique().tolist()
sorted_positions = [p for p in pos_order if p in actual_pos] + sorted([p for p in actual_pos if p not in pos_order])

pl_lines = [
    ['GK'],
    ['RB', 'CB', 'LB'],
    ['RM', 'DM', 'CM', 'LM'],
    ['RW', 'AM', 'LW'],
    ['SS', 'CF']
]
defined_pl_pos = [item for sublist in pl_lines for item in sublist]
actual_pl_pos = df['Pl Pos'].dropna().unique().tolist()
others = sorted([p for p in actual_pl_pos if p not in defined_pl_pos])
if others:
    pl_lines.append(others)
all_pl_pos = [p for line in pl_lines for p in line if p in actual_pl_pos]

def _slider_bounds(min_val, max_val, default_span=1.0):
    mn = 0.0 if pd.isna(min_val) else float(min_val)
    mx = 0.0 if pd.isna(max_val) else float(max_val)
    if mn >= mx:
        mx = mn + default_span
    return (mn, mx)

GB = {
    'f_cost':     _slider_bounds(df['Price'].min(),    df['Price'].max(), 1.0),
    'f_mins':     (int(df['Mins'].min() if not pd.isna(df['Mins'].min()) else 0), max(int(df['Mins'].max() if not pd.isna(df['Mins'].max()) else 1), int(df['Mins'].min() if not pd.isna(df['Mins'].min()) else 0) + 1)),
    'f_selected': _slider_bounds(df['Selected'].min(), df['Selected'].max(), 1.0),
    'f_ppm':      _slider_bounds(df['PPM'].min(),      df['PPM'].max(), 1.0),
}

DEFAULTS = {
    'f_cost':     GB['f_cost'],
    'f_mins':     GB['f_mins'],
    'f_selected': GB['f_selected'],
    'f_ppm':      GB['f_ppm'],
}

if 'pills_teams'  not in st.session_state: st.session_state.pills_teams  = all_teams
if 'pills_pos'    not in st.session_state: st.session_state.pills_pos    = sorted_positions
if 'pills_pl_pos' not in st.session_state: st.session_state.pills_pl_pos = all_pl_pos

def _pills_snapshot():
    snap = {
        'pos':    tuple(sorted(st.session_state.get('pills_pos',   sorted_positions) or [])),
        'teams':  tuple(sorted(st.session_state.get('pills_teams', all_teams) or [])),
        'search': st.session_state.get('search_name', ''),
    }
    for i, line in enumerate(pl_lines):
        avail = [p for p in line if p in actual_pl_pos]
        snap[f'pl_{i}'] = tuple(sorted(st.session_state.get(f'pills_pl_line_{i}', avail)))
    return snap

def _safe_range(key, default):
    val = st.session_state.get(key, default)
    if isinstance(val, (tuple, list)) and len(val) == 2:
        if val[0] < val[1]:
            return val
    return default

def get_available(exclude_key=None):
    cv_pos      = st.session_state.get('pills_pos',   sorted_positions) or []
    cv_teams    = st.session_state.get('pills_teams', all_teams) or []
    cv_cost     = _safe_range('f_cost',     DEFAULTS['f_cost'])
    cv_mins     = _safe_range('f_mins',     DEFAULTS['f_mins'])
    cv_selected = _safe_range('f_selected', DEFAULTS['f_selected'])
    cv_ppm      = _safe_range('f_ppm',      DEFAULTS['f_ppm'])
    cv_search   = st.session_state.get('search_name', '')

    cv_pl_pos = []
    for i, line in enumerate(pl_lines):
        avail = [p for p in line if p in actual_pl_pos]
        cv_pl_pos.extend(st.session_state.get(f'pills_pl_line_{i}', avail))

    mask = pd.Series([True] * len(df), index=df.index)
    if exclude_key != 'pills_pos':   mask &= df['Pos'].isin(cv_pos)
    if exclude_key != 'pills_teams': mask &= df['Team'].isin(cv_teams)
    if exclude_key != 'pills_pl':
        if cv_pl_pos:
            if len(cv_pl_pos) == len(all_pl_pos):
                mask &= (df['Pl Pos'].isin(cv_pl_pos) | df['Pl Pos'].isna())
            else:
                mask &= df['Pl Pos'].isin(cv_pl_pos)
    if exclude_key != 'f_cost':
        mask &= (df['Price'] >= cv_cost[0]) & (df['Price'] <= cv_cost[1])
    if exclude_key != 'f_mins':
        mask &= (df['Mins'] >= cv_mins[0]) & (df['Mins'] <= cv_mins[1])
    if exclude_key != 'f_selected':
        mask &= (df['Selected'] >= cv_selected[0]) & (df['Selected'] <= cv_selected[1])
    if exclude_key != 'f_ppm':
        mask &= (df['PPM'] >= cv_ppm[0]) & (df['PPM'] <= cv_ppm[1])
    if exclude_key != 'search':
        mask &= df['Player'].str.contains(cv_search, case=False, na=False)
    return df[mask]

def get_base_df(exclude_key=None):
    cv_pos    = st.session_state.get('pills_pos',   sorted_positions) or []
    cv_teams  = st.session_state.get('pills_teams', all_teams) or []
    cv_search = st.session_state.get('search_name', '')

    cv_pl_pos = []
    for i, line in enumerate(pl_lines):
        avail = [p for p in line if p in actual_pl_pos]
        cv_pl_pos.extend(st.session_state.get(f'pills_pl_line_{i}', avail))

    mask = (
        df['Pos'].isin(cv_pos) &
        df['Team'].isin(cv_teams) &
        df['Player'].str.contains(cv_search, case=False, na=False)
    )
    if cv_pl_pos:
        if len(cv_pl_pos) == len(all_pl_pos):
            mask &= (df['Pl Pos'].isin(cv_pl_pos) | df['Pl Pos'].isna())
        else:
            mask &= df['Pl Pos'].isin(cv_pl_pos)

    _slider_cols = {
        'f_cost':     ('Price',    DEFAULTS['f_cost']),
        'f_mins':     ('Mins',     DEFAULTS['f_mins']),
        'f_selected': ('Selected', DEFAULTS['f_selected']),
        'f_ppm':      ('PPM',      DEFAULTS['f_ppm']),
    }
    for k, (col_name, d) in _slider_cols.items():
        if k != exclude_key:
            mask &= (df[col_name] >= d[0]) & (df[col_name] <= d[1])

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
        if key_prefix == "pl_pos":
            for i, line in enumerate(pl_lines):
                st.session_state[f"pills_pl_line_{i}"] = [p for p in options if p in line]
        st.rerun()
    if cols[2].button("None", key=f"btn_none_{key_prefix}", width="stretch"):
        st.session_state[f"pills_{key_prefix}"] = []
        if key_prefix == "pl_pos":
            for i, line in enumerate(pl_lines):
                st.session_state[f"pills_pl_line_{i}"] = []
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

auto_update_slider('f_cost',     'Price',    float)
auto_update_slider('f_mins',     'Mins',     int)
auto_update_slider('f_selected', 'Selected', float)
auto_update_slider('f_ppm',      'PPM',      float)

if st.sidebar.button("Reset All Filters", width="stretch", type="primary"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

search_name = st.sidebar.text_input("Search Player", placeholder="Enter name...", key="search_name")

avail_pos = set(get_available('pills_pos')['Pos'].dropna().unique())
filter_header("UCL Position", sorted_positions, "pos")
selected_positions = st.sidebar.pills(
    "UCL Position", options=sorted_positions, key="pills_pos",
    selection_mode="multi", label_visibility="collapsed"
)

f_cost = st.sidebar.slider(
    "UCL Price", GB['f_cost'][0], GB['f_cost'][1], step=0.1, format="%.1f", key="f_cost"
)

avail_teams = set(get_available('pills_teams')['Team'].dropna().unique())
filter_header("Team", all_teams, "teams")
selected_teams = st.sidebar.pills(
    "Team", options=all_teams, key="pills_teams",
    selection_mode="multi", label_visibility="collapsed"
)

avail_pl = set(get_available('pills_pl')['Pl Pos'].dropna().unique())
filter_header("Playing Position", all_pl_pos, "pl_pos")
selected_pl_pos = []

for idx, line in enumerate(pl_lines):
    available_in_line = [p for p in line if p in actual_pl_pos]
    if not available_in_line:
        continue
    line_key = f"pills_pl_line_{idx}"
    if line_key not in st.session_state:
        st.session_state[line_key] = [p for p in st.session_state.pills_pl_pos if p in available_in_line]

    line_res = st.sidebar.pills(
        label=f"pl_line_{idx}", options=available_in_line, key=line_key,
        selection_mode="multi", label_visibility="collapsed"
    )
    if line_res:
        selected_pl_pos.extend(line_res)

f_mins = st.sidebar.slider(
    "Minutes played", GB['f_mins'][0], GB['f_mins'][1], step=1, key="f_mins"
)

f_selected = st.sidebar.slider(
    "Selected %", GB['f_selected'][0], GB['f_selected'][1], step=0.1, key="f_selected"
)

f_ppm = st.sidebar.slider(
    "PPM (Points Per Match)", GB['f_ppm'][0], GB['f_ppm'][1], step=0.1, format="%.1f", key="f_ppm"
)

all_inactive = []
all_inactive.extend([p for p in sorted_positions if p not in avail_pos])
all_inactive.extend([t for t in all_teams if t not in avail_teams])
all_inactive.extend([p for p in all_pl_pos if p not in avail_pl])

inject_sidebar_layout(all_inactive)

if selected_pl_pos and len(selected_pl_pos) == len(all_pl_pos):
    play_pos_mask = df['Pl Pos'].isin(selected_pl_pos) | df['Pl Pos'].isna()
else:
    play_pos_mask = df['Pl Pos'].isin(selected_pl_pos if selected_pl_pos else [])

mask = (
    df['Pos'].isin(selected_positions if selected_positions else []) &
    df['Team'].isin(selected_teams if selected_teams else []) &
    play_pos_mask &
    (df['Price'] >= f_cost[0]) & (df['Price'] <= f_cost[1]) &
    (df['Mins'] >= f_mins[0]) & (df['Mins'] <= f_mins[1]) &
    (df['Selected'] >= f_selected[0]) & (df['Selected'] <= f_selected[1]) &
    (df['PPM'] >= f_ppm[0]) & (df['PPM'] <= f_ppm[1]) &
    (df['Player'].str.contains(search_name, case=False, na=False))
)
filtered_df = df[mask].copy()
sort_cols = [c for c in ['Price', 'TM Value'] if c in filtered_df.columns]
if sort_cols:
    filtered_df = filtered_df.sort_values(by=sort_cols, ascending=[False] * len(sort_cols))


st.subheader(f"UCL Players filtered: {len(filtered_df)}", anchor=False)

existing_display_cols = [c for c in display_columns if c in filtered_df.columns]

base_widths = {}
for col in existing_display_cols:
    if not filtered_df.empty and col in filtered_df.columns:
        val_series = filtered_df[col].dropna().astype(str)
        max_val_len = int(val_series.str.len().max()) if not val_series.empty else 1
    else:
        max_val_len = 1

    bw = max_val_len * 7
    if col == "Player":
        bw = min(bw, 140)
    elif col == "Team Name":
        bw = min(bw, 110)
    else:
        bw = min(bw, 50)
    base_widths[col] = max(bw, 12)

inv_weights = {col: 1.0 / (w ** 0.5) for col, w in base_widths.items()}
sum_inv_weights = sum(inv_weights.values())
TOTAL_PADDING_BUDGET = 550

smart_column_config = {}
format_map = {
    "Price": ("NumberColumn", "%.1f", "Price"),
    "TM Value": ("NumberColumn", "%.1f", "TM Value"),
    "Selected": ("NumberColumn", "%.1f", "Sel %"),
    "PPM": ("NumberColumn", "%.1f", "PPM"),
    "Value": ("NumberColumn", "%.1f", "Value"),
    "Age": ("NumberColumn", None, "Age"),
    "Mins": ("NumberColumn", None, "Mins"),
    "G": ("NumberColumn", None, "G"),
    "A": ("NumberColumn", None, "A"),
    "POTM": ("NumberColumn", None, "POTM"),
    "In": ("NumberColumn", None, "In"),
    "Out": ("NumberColumn", None, "Out"),
    "In 24": ("NumberColumn", None, "In 24"),
    "Out 24": ("NumberColumn", None, "Out 24"),
    "Player": ("TextColumn", None, "Player"),
    "Pos": ("TextColumn", None, "Pos"),
    "Pl Pos": ("TextColumn", None, "Pl Pos"),
    "Team": ("TextColumn", None, "Team"),
    "Team Name": ("TextColumn", None, "Team Name"),
    "Foot": ("TextColumn", None, "Foot"),
}

for col in existing_display_cols:
    bw = base_widths[col]
    bonus = (inv_weights[col] / sum_inv_weights) * TOTAL_PADDING_BUDGET
    calc_w = int(round(bw + bonus))

    if col == "Player":
        calc_w = max(calc_w, 140)
    elif col == "Team Name":
        calc_w = max(calc_w, 120)
    else:
        calc_w = max(calc_w, 52)

    col_type, col_fmt, col_label = format_map.get(col, ("Column", None, col))

    kwargs = {"label": col_label, "width": calc_w}
    if col == "Player":
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
    filtered_df[existing_display_cols],
    width="stretch",
    hide_index=True,
    height=800,
    column_config=smart_column_config
)
