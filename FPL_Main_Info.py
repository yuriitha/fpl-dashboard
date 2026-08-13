import streamlit as st
import pandas as pd
import json

st.set_page_config(page_title="FPL Players Stats", layout="wide", initial_sidebar_state="expanded")

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

        /* Запобігаємо мерехтінню: CSS-правило на базі стабільного батька, якому JS призначає клас */
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
    sort_cols = [c for c in ['now_cost', 'M Price'] if c in df.columns]
    if sort_cols:
        df = df.sort_values(by=sort_cols, ascending=[False] * len(sort_cols))
    import numpy as np


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

display_columns = [
    "full_name", "Age", "element_type", "Play Pos", "team_short_name", "now_cost",
    "M Price", "Foot", "selected_by_percent", "min_played",
    "matches_played", "matches_started", "avg_mins", "60_min", "goals_scored",
    "assists", "av_rating", "av_rating_alt", "points_per_game", "transfers_in_event",
    "transfers_out_event", "transfers_in_24", "transfers_out_24", "news", "news_added"
]


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

rating_series = df['av_rating_alt'].dropna()
r_min = 0.0
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
    'f_matches':  GB['f_matches'],
    'f_rating':   GB['f_rating'],
    'f_avg_mins': GB['f_avg_mins'],
    'f_60min':    GB['f_60min'],
    'f_selected': GB['f_selected'],
    'f_activity': GB['f_activity'],
}


if 'pills_teams'  not in st.session_state: st.session_state.pills_teams  = all_teams
if 'pills_pos'    not in st.session_state: st.session_state.pills_pos    = sorted_positions
if 'pills_pl_pos' not in st.session_state: st.session_state.pills_pl_pos = all_pl_pos


def _pills_snapshot():
    """Знімок стану pills-фільтрів та search для виявлення змін.
    Слайдери в snapshot не включаємо - вони завжди перераховуються при будь-якій зміні pills."""
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
    """Безпечне читання діапазону зі session_state. Якщо значення не tuple/list або min >= max — повертає default."""
    val = st.session_state.get(key, default)
    if isinstance(val, (tuple, list)) and len(val) == 2:
        if val[0] < val[1]:
            return val
    return default


def get_available(exclude_key=None):
    """Повертає підмножину df за всіма фільтрами, крім exclude_key."""
    cv_pos      = st.session_state.get('pills_pos',   sorted_positions) or []
    cv_teams    = st.session_state.get('pills_teams', all_teams) or []
    cv_matches  = _safe_range('f_matches',  DEFAULTS['f_matches'])
    cv_60min    = _safe_range('f_60min',    DEFAULTS['f_60min'])
    cv_cost     = _safe_range('f_cost',     DEFAULTS['f_cost'])
    cv_avg_mins = _safe_range('f_avg_mins', DEFAULTS['f_avg_mins'])
    cv_selected = _safe_range('f_selected', DEFAULTS['f_selected'])
    cv_activity = _safe_range('f_activity', DEFAULTS['f_activity'])
    cv_rating   = _safe_range('f_rating',   DEFAULTS['f_rating'])
    cv_search   = st.session_state.get('search_name', '')

    cv_pl_pos = []
    for i, line in enumerate(pl_lines):
        avail = [p for p in line if p in actual_pl_pos]
        cv_pl_pos.extend(st.session_state.get(f'pills_pl_line_{i}', avail))

    mask = pd.Series([True] * len(df), index=df.index)
    if exclude_key != 'pills_pos':   mask &= df['element_type'].isin(cv_pos)
    if exclude_key != 'pills_teams': mask &= df['team_short_name'].isin(cv_teams)
    if exclude_key != 'pills_pl':
        if cv_pl_pos:
            if len(cv_pl_pos) == len(all_pl_pos):
                mask &= (df['Play Pos'].isin(cv_pl_pos) | df['Play Pos'].isna())
            else:
                mask &= df['Play Pos'].isin(cv_pl_pos)
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
    if exclude_key != 'f_activity':
        mask &= (df['transfer_activity_pct'] >= cv_activity[0]) & (df['transfer_activity_pct'] <= cv_activity[1])
    if exclude_key != 'f_rating':
        mask &= (df['av_rating_alt'] >= cv_rating[0]) & (df['av_rating_alt'] <= cv_rating[1])
    if exclude_key != 'search':
        mask &= df['full_name'].str.contains(cv_search, case=False, na=False)
    return df[mask]


def get_base_df(exclude_key=None):
    """
    Базовий набір даних для розрахунку діапазонів слайдерів.
    Застосовує: pills + search + DEFAULTS інших слайдерів (крім exclude_key).
    Використовує DEFAULTS (не поточні значення) — це уникає циркулярних залежностей між слайдерами.
    """
    cv_pos    = st.session_state.get('pills_pos',   sorted_positions) or []
    cv_teams  = st.session_state.get('pills_teams', all_teams) or []
    cv_search = st.session_state.get('search_name', '')

    cv_pl_pos = []
    for i, line in enumerate(pl_lines):
        avail = [p for p in line if p in actual_pl_pos]
        cv_pl_pos.extend(st.session_state.get(f'pills_pl_line_{i}', avail))

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
        'f_matches':  ('matches_played',      DEFAULTS['f_matches']),
        'f_60min':    ('60_min',              DEFAULTS['f_60min']),
        'f_cost':     ('now_cost',            DEFAULTS['f_cost']),
        'f_avg_mins': ('avg_mins',            DEFAULTS['f_avg_mins']),
        'f_selected': ('selected_by_percent', DEFAULTS['f_selected']),
        'f_activity': ('transfer_activity_pct', DEFAULTS['f_activity']),
        'f_rating':   ('av_rating_alt',       DEFAULTS['f_rating']),
    }
    for k, (col_name, d) in _slider_cols.items():
        if k != exclude_key:
            mask &= (df[col_name] >= d[0]) & (df[col_name] <= d[1])

    return df[mask]

def auto_update_slider(key, col, cast=float, only_positive=False):
    """
    Оновлює session_state[key] при зміні pills/search.
    Діапазон рахується ЛИШЕ на основі pills — без міжслайдерних залежностей.
    """
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
    """
    100% надійний JS, який використовує геометрію екрану та обхід DOM замість CSS-класів.
    1. Центрує всі кнопки, розтягуючи їхніх батьків.
    2. Зменшує розмір ТІЛЬКИ тих кнопок, що знаходяться візуально нижче тексту "Playing Position".
    3. Затемнює неактивні пігулки.
    """
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

                // 1. Знаходимо заголовок Playing Position для орієнтації
                var plHeader = null;
                var ps = sidebar.querySelectorAll('p');
                ps.forEach(function(p) {{
                    if (p.innerText.trim() === 'Playing Position') {{  plHeader = p; }}
                }} );
                var headerBottom = plHeader ? plHeader.getBoundingClientRect().bottom : 99999;

                btns.forEach(function(b) {{
                    var txt = b.innerText.trim();
                    if (!txt) return;

                    // Ігноруємо базові кнопки
                    if (txt === "Reset All Filters" || txt === "All" || txt === "None") return;

                    // --- Відцентровуємо контейнери ---
                    // Піднімаємось на 3 рівні вгору і робим всі обгортки flex + center
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

                    // --- Зменшуємо розмір Playing Position ---
                    if (b.getBoundingClientRect().top > headerBottom) {{
                        b.style.setProperty('width', '48px', 'important');
                        b.style.setProperty('min-width', '48px', 'important');
                        b.style.setProperty('max-width', '48px', 'important');

                        // Додаємо стабільний клас для батьківського контейнера, щоб уникнути мерехтіння
                        var stPills = b.closest('[data-testid="stPills"]');
                        if (stPills) {{
                            var wrapper = stPills.closest('.stElementContainer') || stPills.closest('[data-testid="stElementContainer"]');
                            if (wrapper && !wrapper.classList.contains('playing-pos-wrapper')) {{
                                wrapper.classList.add('playing-pos-wrapper');
                            }}
                        }}
                    }}  else {{
                        // Гарантуємо 60px для інших
                        b.style.setProperty('width', '60px', 'important');
                        b.style.setProperty('min-width', '60px', 'important');
                        b.style.setProperty('max-width', '60px', 'important');
                    }}

                    // --- Затемнення ---
                    var expectedOpacity = inactiveList.includes(txt) ? '0.3' : '';
                    if (b.style.opacity !== expectedOpacity) {{
                        b.style.opacity = expectedOpacity;
                    }}
                }} );
            }}  catch(e) {{ }}
        }}

        // Використовуємо setInterval для постійного насаджування стилів, перебиваючи React
        setInterval(forceLayout, 300);
    }} )();
    </script>
    """
    st.components.v1.html(js, height=0, scrolling=False)


auto_update_slider('f_cost',     'now_cost',            float)
auto_update_slider('f_matches',  'matches_played',      int)
auto_update_slider('f_rating',   'av_rating_alt',       float)
auto_update_slider('f_avg_mins', 'avg_mins',            float)
auto_update_slider('f_60min',    '60_min',              float)
auto_update_slider('f_selected', 'selected_by_percent', float)
auto_update_slider('f_activity', 'transfer_activity_pct', float)


if st.sidebar.button("Reset All Filters", width="stretch", type="primary"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

search_name = st.sidebar.text_input("Search Player", placeholder="Enter name...", key="search_name")


avail_pos = set(get_available('pills_pos')['element_type'].unique())
filter_header("FPL Position", sorted_positions, "pos")
selected_positions = st.sidebar.pills(
    "FPL Position", options=sorted_positions, key="pills_pos",
    selection_mode="multi", label_visibility="collapsed"
)


f_cost = st.sidebar.slider(
    "FPL Price", GB['f_cost'][0], GB['f_cost'][1], step=0.1, format="%.1f", key="f_cost"
)


avail_teams = set(get_available('pills_teams')['team_short_name'].unique())
filter_header("Team", all_teams, "teams")
selected_teams = st.sidebar.pills(
    "Team", options=all_teams, key="pills_teams",
    selection_mode="multi", label_visibility="collapsed"
)


avail_pl = set(get_available('pills_pl')['Play Pos'].dropna().unique())
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


all_inactive = []
all_inactive.extend([p for p in sorted_positions if p not in avail_pos])
all_inactive.extend([t for t in all_teams if t not in avail_teams])
all_inactive.extend([p for p in all_pl_pos if p not in avail_pl])

inject_sidebar_layout(all_inactive)


with st.sidebar.expander("Performance Stats", expanded=False):
    f_matches  = st.slider("Matches",      GB['f_matches'][0],  GB['f_matches'][1],  step=1,    key="f_matches")
    f_rating   = st.slider("Rating",       GB['f_rating'][0],   GB['f_rating'][1],   step=0.05, format="%.2f", key="f_rating")
    f_avg_mins = st.slider("Average Mins", GB['f_avg_mins'][0], GB['f_avg_mins'][1], step=1.0,  key="f_avg_mins")
    f_60min    = st.slider("60 Min %",     GB['f_60min'][0],    GB['f_60min'][1],    step=0.5,  key="f_60min")


with st.sidebar.expander("Market & Popularity", expanded=False):
    f_selected = st.slider("Selected %",  GB['f_selected'][0], GB['f_selected'][1], step=0.1, key="f_selected")
    f_activity = st.slider("Transfer Activity", GB['f_activity'][0], GB['f_activity'][1], step=1.0, format="%d%%", key="f_activity")


if selected_pl_pos and len(selected_pl_pos) == len(all_pl_pos):
    play_pos_mask = df['Play Pos'].isin(selected_pl_pos) | df['Play Pos'].isna()
else:
    play_pos_mask = df['Play Pos'].isin(selected_pl_pos if selected_pl_pos else [])

mask = (
    df['element_type'].isin(selected_positions if selected_positions else []) &
    df['team_short_name'].isin(selected_teams  if selected_teams  else []) &
    play_pos_mask &
    (df['av_rating_alt']       >= f_rating[0])   & (df['av_rating_alt']       <= f_rating[1]) &
    (df['matches_played']      >= f_matches[0])  & (df['matches_played']      <= f_matches[1]) &
    (df['60_min']              >= f_60min[0])    & (df['60_min']              <= f_60min[1]) &
    (df['now_cost']            >= f_cost[0])     & (df['now_cost']            <= f_cost[1]) &
    (df['selected_by_percent'] >= f_selected[0]) & (df['selected_by_percent'] <= f_selected[1]) &
    (df['transfer_activity_pct'] >= f_activity[0]) & (df['transfer_activity_pct'] <= f_activity[1]) &
    (df['avg_mins']            >= f_avg_mins[0]) & (df['avg_mins']            <= f_avg_mins[1]) &
    (df['full_name'].str.contains(search_name, case=False, na=False))
)
filtered_df = df[mask].copy()
sort_cols = [c for c in ['now_cost', 'M Price'] if c in filtered_df.columns]
if sort_cols:
    filtered_df = filtered_df.sort_values(by=sort_cols, ascending=[False] * len(sort_cols))


st.subheader(f"Players filtered: {len(filtered_df)}", anchor=False)
existing_display_cols = [c for c in display_columns if c in filtered_df.columns]

base_widths = {}
for col in existing_display_cols:
    if col == "news":
        continue
    if not filtered_df.empty and col in filtered_df.columns:
        val_series = filtered_df[col].dropna().astype(str)
        max_val_len = int(val_series.str.len().max()) if not val_series.empty else 1
    else:
        max_val_len = 1

    bw = max_val_len * 7
    if col == "full_name":
        bw = min(bw, 140)
    elif col == "news_added":
        bw = min(bw, 110)
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
    "Foot":                ("TextColumn", None, "Foot"),
    "selected_by_percent": ("NumberColumn", "%.1f%%", "Sel %"),
    "min_played":          ("NumberColumn", None, "Mins"),
    "matches_played":      ("NumberColumn", None, "MP"),
    "matches_started":     ("NumberColumn", None, "GS"),
    "avg_mins":            ("NumberColumn", "%d", "AvMins"),
    "60_min":              ("NumberColumn", "%.1f", "60m %"),
    "goals_scored":        ("NumberColumn", None, "G"),
    "assists":             ("NumberColumn", None, "A"),
    "av_rating":           ("NumberColumn", "%.2f", "Rat"),
    "av_rating_alt":       ("NumberColumn", "%.2f", "RatA"),
    "points_per_game":     ("NumberColumn", "%.1f", "PPM"),
    "transfers_in_event":  ("NumberColumn", None, "In"),
    "transfers_out_event": ("NumberColumn", None, "Out"),
    "transfers_in_24":     ("NumberColumn", None, "In 24"),
    "transfers_out_24":    ("NumberColumn", None, "Out 24"),
    "news":                ("TextColumn", None, "News"),
    "news_added":          ("TextColumn", None, "Updated"),
}

for col in existing_display_cols:
    col_type, col_fmt, col_label = format_map.get(col, ("Column", None, col))

    if col == "news":
        calc_w = 185
    else:
        bw = base_widths[col]
        bonus = (inv_weights[col] / sum_inv_weights) * TOTAL_PADDING_BUDGET
        calc_w = int(round(bw + bonus))

        if col == "full_name":
            calc_w = max(calc_w, 140)
        elif col == "news_added":
            calc_w = max(calc_w, 110)
        else:
            calc_w = max(calc_w, 48)

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
    filtered_df[existing_display_cols],
    width="stretch", hide_index=True, height=800,
    column_config=smart_column_config
)