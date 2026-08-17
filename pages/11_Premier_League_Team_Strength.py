import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import json
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from datetime import datetime, timezone, timedelta

st.set_page_config(
    page_title="Team Strength",
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
        
        /* Real-time Theme-Reactive Fixture Projection Tables */
        .proj-table-container {
            overflow-x: auto;
            width: 100%;
            border: 1px solid rgba(128, 128, 128, 0.2);
            border-radius: 8px;
            margin-bottom: 1.4rem;
            background: var(--secondary-background-color, transparent);
        }
        .proj-table {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
            font-size: 0.78rem;
            text-align: center;
            color: var(--text-color, inherit);
        }
        .proj-table thead tr {
            background: var(--background-color, transparent);
            border-bottom: 2px solid rgba(128, 128, 128, 0.25);
        }
        .proj-table th {
            padding: 5px 2px;
            font-weight: 600;
            min-width: 50px;
            background: var(--background-color, inherit);
            color: var(--text-color, inherit);
            border-right: 1px solid rgba(128, 128, 128, 0.2);
            border-bottom: 2px solid rgba(128, 128, 128, 0.25);
            font-size: 0.76rem;
        }
        .proj-table th.team-th {
            padding: 5px 8px;
            font-weight: 600;
            font-size: 0.88rem;
            text-align: center;
            width: 200px;
            min-width: 200px;
            max-width: 200px;
            position: sticky;
            left: 0;
            z-index: 2;
            background: var(--background-color, inherit);
        }
        .proj-table th.avg-th {
            padding: 5px 4px;
            font-weight: 600;
            width: 98px;
            min-width: 98px;
            max-width: 98px;
            font-size: 0.78rem;
        }
        .proj-table tbody tr {
            background: var(--secondary-background-color, transparent);
            border-bottom: 1px solid rgba(128, 128, 128, 0.15);
        }
        .proj-table tbody tr:nth-child(even) {
            background: var(--background-color, transparent);
        }
        .proj-table td {
            padding: 3px 2px;
            min-width: 50px;
            border-right: 1px solid rgba(128, 128, 128, 0.15);
            border-bottom: 1px solid rgba(128, 128, 128, 0.15);
            color: var(--text-color, inherit);
        }
        .proj-table td.team-td {
            padding: 4px 8px;
            font-weight: 550;
            font-size: 0.97rem;
            text-align: center;
            width: 200px;
            min-width: 200px;
            max-width: 200px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            position: sticky;
            left: 0;
            z-index: 1;
            background: var(--secondary-background-color, inherit);
            line-height: 1.2;
        }
        .proj-table tbody tr:nth-child(even) td.team-td {
            background: var(--background-color, inherit);
        }
        .proj-table td.avg-td {
            padding: 4px 4px;
            font-weight: 600;
            font-size: 0.80rem;
            width: 98px;
            min-width: 98px;
            max-width: 98px;
            background: var(--secondary-background-color, inherit);
            line-height: 1.15;
        }
        .proj-table tbody tr:nth-child(even) td.avg-td {
            background: var(--background-color, inherit);
        }
        .proj-table .cell-val {
            font-weight: 600;
            font-size: 0.80rem;
            line-height: 1.1;
            color: var(--text-color, inherit);
        }
        .proj-table .cell-opp {
            font-size: 0.63rem;
            opacity: 0.72;
            margin-top: 1.5px;
            line-height: 1.05;
            color: var(--text-color, inherit);
        }
        
        .proj-table th.gw-th {
            position: relative;
            padding: 4px 2px !important;
            user-select: none;
        }
        .proj-table .gw-th-content {
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
            gap: 2px;
        }
        .proj-table .gw-title {
            font-weight: 600;
        }
        .proj-table .gw-remove-btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 13px;
            height: 13px;
            border-radius: 50%;
            border: none;
            background: transparent;
            color: var(--text-color, inherit);
            opacity: 0;
            cursor: pointer;
            font-size: 13px;
            font-weight: bold;
            line-height: 1;
            padding: 0;
            margin: 0;
            transition: opacity 0.15s ease, background 0.15s ease, color 0.15s ease, transform 0.15s ease;
        }
        .proj-table th.gw-th:hover .gw-remove-btn {
            opacity: 0.55;
        }
        .proj-table .gw-remove-btn:hover {
            opacity: 1 !important;
            background: rgba(255, 77, 79, 0.25) !important;
            color: #ff4d4f !important;
            transform: scale(1.2);
        }
        
        /* Refresh reset button styling */
        div[data-testid="column"]:has(div[data-testid="stButton"]) {
            display: flex !important;
            flex-direction: column !important;
            justify-content: flex-end !important;
            min-width: 0 !important;
        }
        div[data-testid="column"]:has(div[data-testid="stButton"]) > div[data-testid="stVerticalBlock"] {
            display: flex !important;
            flex-direction: column !important;
            justify-content: flex-end !important;
            height: 100% !important;
            gap: 0px !important;
        }
        div[data-testid="column"]:has(div[data-testid="stButton"]) div[data-testid="stButton"] {
            margin-top: auto !important;
            margin-bottom: 0px !important;
            padding-bottom: 0px !important;
            width: 100% !important;
        }
        div[data-testid="column"]:has(div[data-testid="stButton"]) button {
            height: 38px !important;
            min-height: 38px !important;
            max-height: 38px !important;
            padding: 0px !important;
            margin: 0px !important;
            width: 100% !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            border-radius: 6px !important;
            border: 1px solid rgba(128, 128, 128, 0.25) !important;
            background: transparent !important;
            transition: all 0.2s ease !important;
            box-sizing: border-box !important;
            overflow: hidden !important;
        }
        div[data-testid="column"]:has(div[data-testid="stButton"]) button * {
            font-size: 1.60rem !important;
            line-height: 1 !important;
            margin: 0 !important;
            padding: 0 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            width: 100% !important;
            height: 100% !important;
            transform: scale(1.22);
            transition: transform 0.25s ease !important;
        }
        div[data-testid="column"]:has(div[data-testid="stButton"]) button:hover {
            border-color: rgba(0, 180, 255, 0.7) !important;
            background: rgba(0, 180, 255, 0.08) !important;
        }
        div[data-testid="column"]:has(div[data-testid="stButton"]) button:hover * {
            transform: scale(1.35) rotate(90deg);
        }
    </style>
""", unsafe_allow_html=True)

import requests

@st.cache_data(ttl=300)
def load_data():
    url = "http://198.244.151.163:8000/team_strength_model"
    df = pd.read_parquet(url)

    last_update_str = ""
    try:
        meta_url = "http://198.244.151.163:8000/team_strength_metadata"
        meta_resp = requests.get(meta_url, timeout=3)
        if meta_resp.status_code == 200:
            meta_json = meta_resp.json()
            
            divisions = meta_json.get("divisions", {})
            div_data = divisions.get("England__Premier League__1", {})
            dt_raw = div_data.get("last_scraped") or meta_json.get("last_scraped_at") or meta_json.get("last_processed_date")
            
            if dt_raw:
                dt_obj = pd.to_datetime(dt_raw)
                last_update_str = dt_obj.strftime("%d/%m/%Y %H:%M")
    except Exception:
        pass

    if not last_update_str and 'match_date' in df.columns:
        played = df.dropna(subset=['match_result'])
        if not played.empty:
            last_update_str = pd.to_datetime(played['match_date'].max()).strftime("%d/%m/%Y %H:%M")

    return df, last_update_str

@st.cache_data(ttl=300)
def load_fixtures_model():
    url = "http://198.244.151.163:8000/fpl_fixtures_model"
    try:
        df_fix = pd.read_parquet(url)
        return df_fix
    except Exception:
        import os
        local_path = os.path.join(os.path.dirname(__file__), "..", "..", "streamlit", "fpl_fixtures_model.parquet")
        if os.path.exists(local_path):
            return pd.read_parquet(local_path)
        return pd.DataFrame()

try:
    df, last_update_str = load_data()
except Exception as e:
    st.error(f"Помилка завантаження: {e}")
    st.stop()


def get_active_theme():
    try:
        if hasattr(st, 'context') and hasattr(st.context, 'theme'):
            t_obj = st.context.theme
            if isinstance(t_obj, dict):
                t_type = t_obj.get('type') or t_obj.get('base')
                if t_type:
                    return str(t_type).lower()
            elif hasattr(t_obj, 'type') and t_obj.type:
                return str(t_obj.type).lower()
            elif hasattr(t_obj, 'base') and t_obj.base:
                return str(t_obj.base).lower()
    except Exception:
        pass

    try:
        base_opt = st.get_option('theme.base')
        if base_opt:
            return str(base_opt).lower()
    except Exception:
        pass

    return 'dark'


team_colors_light = {}
team_colors_dark = {}

has_light_dark = 'home_color_light' in df.columns and 'home_color_dark' in df.columns

if has_light_dark:
    for _, row in df[['home_team', 'home_color_light', 'home_color_dark']].dropna(subset=['home_team']).drop_duplicates(subset=['home_team']).iterrows():
        t = row['home_team']
        if pd.notna(row['home_color_light']) and t not in team_colors_light:
            team_colors_light[t] = row['home_color_light']
        if pd.notna(row['home_color_dark']) and t not in team_colors_dark:
            team_colors_dark[t] = row['home_color_dark']

    for _, row in df[['away_team', 'away_color_light', 'away_color_dark']].dropna(subset=['away_team']).drop_duplicates(subset=['away_team']).iterrows():
        t = row['away_team']
        if pd.notna(row['away_color_light']) and t not in team_colors_light:
            team_colors_light[t] = row['away_color_light']
        if pd.notna(row['away_color_dark']) and t not in team_colors_dark:
            team_colors_dark[t] = row['away_color_dark']
else:
    h_col = 'home_color' if 'home_color' in df.columns else None
    a_col = 'away_color' if 'away_color' in df.columns else None
    if h_col:
        for _, row in df[['home_team', h_col]].dropna().drop_duplicates().iterrows():
            team_colors_light[row['home_team']] = row[h_col]
            team_colors_dark[row['home_team']] = row[h_col]
    if a_col:
        for _, row in df[['away_team', a_col]].dropna().drop_duplicates().iterrows():
            if row['away_team'] not in team_colors_light: team_colors_light[row['away_team']] = row[a_col]
            if row['away_team'] not in team_colors_dark: team_colors_dark[row['away_team']] = row[a_col]

is_light = (get_active_theme() == 'light')
team_colors = team_colors_light if is_light else team_colors_dark
team_code_to_name = {}


pl_teams_all = df[df['league'] == 'Premier League']
for _, row in pl_teams_all[['home_team_code', 'home_team']].dropna().drop_duplicates().iterrows():
    team_code_to_name[row['home_team_code']] = row['home_team']
for _, row in pl_teams_all[['away_team_code', 'away_team']].dropna().drop_duplicates().iterrows():
    team_code_to_name[row['away_team_code']] = row['away_team']


for _, row in df[['home_team_code', 'home_team']].dropna().drop_duplicates().iterrows():
    if row['home_team_code'] not in team_code_to_name: team_code_to_name[row['home_team_code']] = row['home_team']
for _, row in df[['away_team_code', 'away_team']].dropna().drop_duplicates().iterrows():
    if row['away_team_code'] not in team_code_to_name: team_code_to_name[row['away_team_code']] = row['away_team']

all_seasons = sorted([s for s in df['season'].dropna().unique() if s != "2009/10"])


if st.sidebar.button("Reset All Filters", width="stretch", type="primary"):
    keys_to_delete = [k for k in st.session_state.keys() if k.startswith('ts_')]
    for key in keys_to_delete:
        del st.session_state[key]
    st.rerun()


season_range = st.sidebar.select_slider(
    "Seasons",
    options=all_seasons,
    value=(all_seasons[-2], all_seasons[-1]) if len(all_seasons) >= 2 else (all_seasons[-1], all_seasons[-1]),
    key="ts_pl_seasons"
)

s_start, s_end = season_range
pl_df = df[(df['league'] == 'Premier League') & (df['season'] >= s_start) & (df['season'] <= s_end)]
all_teams = sorted([t for t in set(pl_df['home_team_code'].dropna()).union(set(pl_df['away_team_code'].dropna())) if t and str(t).strip()])


if 'ts_pl_pills_teams' not in st.session_state or st.session_state.get('ts_pl_prev_all_teams') != all_teams:
    st.session_state.ts_pl_pills_teams = all_teams
    st.session_state.ts_pl_prev_all_teams = all_teams

search_name = st.sidebar.text_input("Search Team", placeholder="Enter team name...", key="ts_pl_search_name")


def filter_header(label, options, key_prefix):
    cols = st.sidebar.columns([1.4, 0.8, 0.8])
    cols[0].markdown(f"<p style='font-size:0.875rem;margin-bottom:0'>{label}</p>", unsafe_allow_html=True)
    if cols[1].button("All", key=f"btn_all_{key_prefix}", width="stretch"):
        st.session_state[f"ts_{key_prefix}"] = options
        st.rerun()
    if cols[2].button("None", key=f"btn_none_{key_prefix}", width="stretch"):
        st.session_state[f"ts_{key_prefix}"] = []
        st.rerun()

filter_header("Teams", all_teams, "pl_pills_teams")
selected_teams = st.sidebar.pills(
    "Teams", options=all_teams, key="ts_pl_pills_teams",
    selection_mode="multi", label_visibility="collapsed"
)


final_teams = selected_teams if selected_teams else []
if search_name:
    final_teams = [t for t in final_teams if search_name.lower() in t.lower() or search_name.lower() in team_code_to_name.get(t, "").lower()]


inactive_teams = [t for t in all_teams if t not in final_teams]
js = f"""
<script>
(function() {{
    var inactiveList = {json.dumps(inactive_teams)};
    function forceLayout() {{
        try {{
            var doc = window.parent.document;
            var sidebar = doc.querySelector('[data-testid="stSidebar"]');
            if (!sidebar) return;
            var btns = sidebar.querySelectorAll('button');
            btns.forEach(function(b) {{
                var txt = b.innerText.trim();
                if (!txt || txt === "Reset All Filters" || txt === "All" || txt === "None") return;
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

def soft_gradient(s, cmap_name='Blues', alpha=0.5, fixed_min=None, fixed_max=None, transparent_at='min', power=0.7):
    if s.empty:
        return ['' for _ in s]
    s_min = fixed_min if fixed_min is not None else s.min()
    s_max = fixed_max if fixed_max is not None else s.max()
    if pd.isna(s_min) or pd.isna(s_max) or s_min == s_max:
        return ['' for _ in s]

    if isinstance(cmap_name, str):
        cmap = plt.get_cmap(cmap_name)
    else:
        cmap = cmap_name

    norm = mcolors.Normalize(vmin=s_min, vmax=s_max)

    styles = []
    for val in s:
        if pd.isna(val):
            styles.append('')
        else:
            clamped = max(min(val, s_max), s_min)
            norm_val = norm(clamped)
            r, g, b, _ = cmap(norm_val)

            if transparent_at == 'min':
                intensity = norm_val
            elif transparent_at == 'max':
                intensity = 1.0 - norm_val
            elif transparent_at == 'mid':
                intensity = abs(norm_val - 0.5) * 2
            else:
                intensity = 1.0


            dynamic_alpha = intensity * alpha
            styles.append(f'background-color: rgba({int(r*255)}, {int(g*255)}, {int(b*255)}, {dynamic_alpha:.3f})')
    return styles


def soft_honey_blue_gradient(s, min_alpha=0.04, max_alpha=0.60, reverse=False):
    if s.empty or s.nunique() <= 1:
        return ['' for _ in s]

    ranks = s.rank(ascending=not reverse, method='min')
    r_min, r_max = ranks.min(), ranks.max()
    if r_min == r_max:
        return ['' for _ in s]

    norm_ranks = (ranks - r_min) / (r_max - r_min)

    styles = []
    for norm_val in norm_ranks:
        if pd.isna(norm_val):
            styles.append('')
        else:
            if norm_val >= 0.5:
                t = (norm_val - 0.5) * 2.0
                # Blue (#00B4FF -> rgb(0, 180, 255))
                r = int(245 + t * (0   - 245))
                g = int(245 + t * (180 - 245))
                b = int(245 + t * (255 - 245))
                alpha = min_alpha + t * (max_alpha - min_alpha)
            else:
                t = (0.5 - norm_val) * 2.0
                # Honey Orange (#F58C19 -> rgb(245, 140, 25))
                r = int(245 + t * (245 - 245))
                g = int(245 + t * (140 - 245))
                b = int(245 + t * (25  - 245))
                alpha = min_alpha + t * (max_alpha - min_alpha)
            styles.append(f'background-color: rgba({r}, {g}, {b}, {alpha:.2f})')
    return styles

light_blues = mcolors.LinearSegmentedColormap.from_list("LightBlues", ["#ffffff", "#00B4FF"])
honey_blue = mcolors.LinearSegmentedColormap.from_list("HoneyBlue", ["#F58C19", "#ffffff", "#00B4FF"])


col1, col2 = st.columns([0.30, 0.70])


with col1:
    st.subheader("Current Team Ratings", anchor=False)

    current_season = all_seasons[-1]
    curr_season_df = df[(df['league'] == 'Premier League') & (df['season'] == current_season)]
    current_season_teams = sorted(list(set(curr_season_df['home_team_code'].dropna()).union(set(curr_season_df['away_team_code'].dropna()))))

    df_played = df.dropna(subset=['match_result'])
    latest_home = df_played.sort_values('match_date').groupby('home_team_code').last()[['match_date', 'home_rating_att_post', 'home_rating_def_post', 'home_rating_att', 'home_rating_def']]
    latest_away = df_played.sort_values('match_date').groupby('away_team_code').last()[['match_date', 'away_rating_att_post', 'away_rating_def_post', 'away_rating_att', 'away_rating_def']]

    df_unplayed = df[df['match_result'].isna()]
    first_unplayed_home = df_unplayed.sort_values('match_date').groupby('home_team_code').first()[['match_date', 'home_rating_att', 'home_rating_def']]
    first_unplayed_away = df_unplayed.sort_values('match_date').groupby('away_team_code').first()[['match_date', 'away_rating_att', 'away_rating_def']]

    current_ratings = []
    for t_code in current_season_teams:

        uh = first_unplayed_home.loc[t_code] if t_code in first_unplayed_home.index else None
        ua = first_unplayed_away.loc[t_code] if t_code in first_unplayed_away.index else None

        att, def_rating = None, None


        if uh is not None and ua is not None:
            if uh['match_date'] < ua['match_date']:
                att, def_rating = uh['home_rating_att'], uh['home_rating_def']
            else:
                att, def_rating = ua['away_rating_att'], ua['away_rating_def']
        elif uh is not None:
            att, def_rating = uh['home_rating_att'], uh['home_rating_def']
        elif ua is not None:
            att, def_rating = ua['away_rating_att'], ua['away_rating_def']


        if pd.isna(att) or pd.isna(def_rating):
            h = latest_home.loc[t_code] if t_code in latest_home.index else None
            a = latest_away.loc[t_code] if t_code in latest_away.index else None

            if h is not None and a is not None:
                if h['match_date'] > a['match_date']:
                    att = h['home_rating_att_post'] if pd.notna(h['home_rating_att_post']) else h['home_rating_att']
                    def_rating = h['home_rating_def_post'] if pd.notna(h['home_rating_def_post']) else h['home_rating_def']
                else:
                    att = a['away_rating_att_post'] if pd.notna(a['away_rating_att_post']) else a['away_rating_att']
                    def_rating = a['away_rating_def_post'] if pd.notna(a['away_rating_def_post']) else a['away_rating_def']
            elif h is not None:
                att = h['home_rating_att_post'] if pd.notna(h['home_rating_att_post']) else h['home_rating_att']
                def_rating = h['home_rating_def_post'] if pd.notna(h['home_rating_def_post']) else h['home_rating_def']
            elif a is not None:
                att = a['away_rating_att_post'] if pd.notna(a['away_rating_att_post']) else a['away_rating_att']
                def_rating = a['away_rating_def_post'] if pd.notna(a['away_rating_def_post']) else a['away_rating_def']

        if pd.notna(att) and pd.notna(def_rating):
            current_ratings.append({
                'Team': team_code_to_name.get(t_code, t_code),
                'Attack Rating': att,
                'Defence Rating': def_rating,
                'Overall Rating': att - def_rating
            })

    if current_ratings:
        df_ratings = pd.DataFrame(current_ratings).sort_values('Overall Rating', ascending=False).reset_index(drop=True)
        df_ratings.index = df_ratings.index + 1
        df_ratings.reset_index(inplace=True)
        df_ratings.rename(columns={'index': 'Pos', 'Attack Rating': 'Attack', 'Defence Rating': 'Defence', 'Overall Rating': 'Overall'}, inplace=True)

        df_ratings_styled = df_ratings.style\
            .apply(soft_honey_blue_gradient, subset=['Attack'])\
            .apply(soft_honey_blue_gradient, reverse=True, subset=['Defence'])\
            .apply(soft_honey_blue_gradient, subset=['Overall'])\
            .format(precision=2)

        # Smart widths for df_ratings
        ratings_cols = ['Pos', 'Team', 'Attack', 'Defence', 'Overall']
        base_widths_ratings = {}
        for c in ratings_cols:
            if not df_ratings.empty and c in df_ratings.columns:
                val_series = df_ratings[c].dropna().astype(str)
                max_val_len = int(val_series.str.len().max()) if not val_series.empty else 1
            else:
                max_val_len = 1
            max_len = max(max_val_len, len(c))
            bw = max_len * 7.5
            if c == 'Team':
                bw = min(bw, 140)
            elif c == 'Pos':
                bw = min(bw, 30)
            else:
                bw = min(bw, 55)
            base_widths_ratings[c] = max(bw, 25)

        inv_w_r = {c: 1.0 / (w ** 0.5) for c, w in base_widths_ratings.items()}
        sum_inv_w_r = sum(inv_w_r.values())
        BUDGET_RATINGS = 80

        column_config_ratings = {}
        for c in ratings_cols:
            bw = base_widths_ratings[c]
            bonus = (inv_w_r[c] / sum_inv_w_r) * BUDGET_RATINGS
            calc_w = int(round(bw + bonus))
            if c == 'Pos':
                column_config_ratings[c] = st.column_config.NumberColumn("Pos", width=max(calc_w, 35))
            elif c == 'Team':
                column_config_ratings[c] = st.column_config.TextColumn("Team", width=max(calc_w, 110))
            elif c == 'Attack':
                column_config_ratings[c] = st.column_config.NumberColumn("Attack", format="%.2f", width=max(calc_w, 60))
            elif c == 'Defence':
                column_config_ratings[c] = st.column_config.NumberColumn("Defence", format="%.2f", width=max(calc_w, 60))
            elif c == 'Overall':
                column_config_ratings[c] = st.column_config.NumberColumn("Overall", format="%.2f", width=max(calc_w, 60))

        st.dataframe(
            df_ratings_styled,
            hide_index=True,
            width="stretch",
            height=738,
            column_config=column_config_ratings
        )
    else:
        st.info("No teams selected.")


with col2:
    head_col1, head_col2 = st.columns([0.5, 0.5])
    with head_col1:
        st.subheader("Current Matches", anchor=False)
    with head_col2:
        if last_update_str:
            st.markdown(f"<p style='text-align: right; font-size: 0.8rem; color: #888888; margin-top: 0.6rem; margin-bottom: 0;'>Data updated: <b>{last_update_str}</b></p>", unsafe_allow_html=True)
    threshold = pd.Timestamp.now() - pd.Timedelta(hours=48)
    df_future = df[
        (df['league'] == 'Premier League') & 
        (df['match_result'].isna() | (df['match_date'] >= threshold))
    ].copy()
    if not df_future.empty:
        df_future['score'] = df_future['match_result'].apply(
            lambda x: str(x).strip().split()[0] if pd.notna(x) and str(x).strip() and str(x).strip().lower() not in ('none', 'nan') else " "
        )
        if 'home_cs_odds' not in df_future.columns or df_future['home_cs_odds'].isna().all():
            df_future['home_cs_odds'] = np.exp(-df_future['away_xg_odds']) * 100
        else:
            df_future['home_cs_odds'] = df_future['home_cs_odds'].fillna(np.exp(-df_future['away_xg_odds']) * 100)

        if 'away_cs_odds' not in df_future.columns or df_future['away_cs_odds'].isna().all():
            df_future['away_cs_odds'] = np.exp(-df_future['home_xg_odds']) * 100
        else:
            df_future['away_cs_odds'] = df_future['away_cs_odds'].fillna(np.exp(-df_future['home_xg_odds']) * 100)

        cols = ['match_date', 'home_team', 'away_team', 'score', 'home_xg', 'away_xg', 'home_xg_odds', 'away_xg_odds', 'home_delta', 'away_delta', 'home_cs_odds', 'away_cs_odds']
        df_future = df_future[cols].sort_values('match_date')

        xg_cols = ['home_xg', 'away_xg', 'home_xg_odds', 'away_xg_odds']
        xg_min = df_future[xg_cols].min().min()
        xg_max = df_future[xg_cols].max().max()

        cs_cols = ['home_cs_odds', 'away_cs_odds']
        cs_min = df_future[cs_cols].min().min()
        cs_max = df_future[cs_cols].max().max()

        df_future_styled = df_future.style\
            .apply(soft_gradient, cmap_name=light_blues, alpha=0.75, fixed_min=xg_min, fixed_max=xg_max, transparent_at='min', power=0.6, subset=xg_cols)\
            .apply(soft_gradient, cmap_name=honey_blue, alpha=0.75, fixed_min=-0.45, fixed_max=0.45, transparent_at='mid', power=0.6, subset=['home_delta', 'away_delta'])\
            .apply(soft_gradient, cmap_name=light_blues, alpha=0.75, fixed_min=cs_min, fixed_max=cs_max, transparent_at='min', power=0.6, subset=cs_cols)\
            .format(precision=2)\
            .format(precision=1, subset=cs_cols)

        # Smart widths for df_future
        base_widths_matches = {}
        team_max_len = max(
            int(df_future['home_team'].dropna().astype(str).str.len().max()) if not df_future.empty else 1,
            int(df_future['away_team'].dropna().astype(str).str.len().max()) if not df_future.empty else 1,
            len('Home'), len('Away')
        )
        team_bw = max(min(team_max_len * 7.5, 130), 85)

        for c in cols:
            if c in ('home_team', 'away_team'):
                base_widths_matches[c] = team_bw
            elif c == 'match_date':
                base_widths_matches[c] = 105
            elif c == 'score':
                base_widths_matches[c] = 45
            elif 'delta' in c:
                base_widths_matches[c] = 48
            elif 'cs' in c:
                base_widths_matches[c] = 48
            else:
                base_widths_matches[c] = 52

        inv_w_m = {c: 1.0 / (w ** 0.5) for c, w in base_widths_matches.items()}
        sum_inv_w_m = sum(inv_w_m.values())
        BUDGET_MATCHES = 160

        widths_matches = {}
        for c in cols:
            bw = base_widths_matches[c]
            bonus = (inv_w_m[c] / sum_inv_w_m) * BUDGET_MATCHES
            calc_w = int(round(bw + bonus))
            if c in ('home_team', 'away_team'):
                calc_w = max(calc_w, 90)
            elif c == 'match_date':
                calc_w = max(calc_w, 110)
            elif c == 'score':
                calc_w = max(calc_w, 50)
            else:
                calc_w = max(calc_w, 55)
            widths_matches[c] = calc_w

        # Ensure Home and Away have identical widths
        equal_team_w = max(widths_matches['home_team'], widths_matches['away_team'])
        widths_matches['home_team'] = equal_team_w
        widths_matches['away_team'] = equal_team_w

        column_config_matches = {
            'match_date':   st.column_config.DatetimeColumn("Date", format="DD/MM/YYYY HH:mm", width=widths_matches['match_date']),
            'home_team':    st.column_config.TextColumn("Home", width=widths_matches['home_team']),
            'away_team':    st.column_config.TextColumn("Away", width=widths_matches['away_team']),
            'score':        st.column_config.TextColumn("Score", width=widths_matches['score']),
            'home_xg':      st.column_config.NumberColumn("Model xG (H)", format="%.2f", width=widths_matches['home_xg']),
            'away_xg':      st.column_config.NumberColumn("Model xG (A)", format="%.2f", width=widths_matches['away_xg']),
            'home_xg_odds': st.column_config.NumberColumn("Odds xG (H)", format="%.2f", width=widths_matches['home_xg_odds']),
            'away_xg_odds': st.column_config.NumberColumn("Odds xG (A)", format="%.2f", width=widths_matches['away_xg_odds']),
            'home_delta':   st.column_config.NumberColumn("Delta (H)", format="%.2f", width=widths_matches['home_delta']),
            'away_delta':   st.column_config.NumberColumn("Delta (A)", format="%.2f", width=widths_matches['away_delta']),
            'home_cs_odds': st.column_config.NumberColumn("CS (H)", format="%.1f", width=widths_matches['home_cs_odds']),
            'away_cs_odds': st.column_config.NumberColumn("CS (A)", format="%.1f", width=widths_matches['away_cs_odds']),
        }

        st.dataframe(
            df_future_styled,
            hide_index=True,
            width="stretch",
            height=len(df_future) * 35 + 40,
            column_config=column_config_matches
        )
    else:
        st.info("No current matches found.")


def build_projection_table_html(df_model, metric_type='xg', view_mode='Absolute', gws=range(1, 13), selected_teams=None):
    # Mapping between short code and model name
    short_to_model = {}
    model_to_short = {}
    for _, r in df_model[['team_h_short', 'team_h_model']].drop_duplicates().iterrows():
        short_to_model[r['team_h_short']] = r['team_h_model']
        model_to_short[r['team_h_model']] = r['team_h_short']
    for _, r in df_model[['team_a_short', 'team_a_model']].drop_duplicates().iterrows():
        short_to_model[r['team_a_short']] = r['team_a_model']
        model_to_short[r['team_a_model']] = r['team_a_short']

    all_teams_model = sorted(list(set(df_model['team_h_model'].dropna()).union(set(df_model['team_a_model'].dropna()))))
    
    if selected_teams:
        teams_to_show = [
            t for t in all_teams_model 
            if t in selected_teams or model_to_short.get(t, '') in selected_teams or any(t.lower() in str(st_name).lower() for st_name in selected_teams)
        ]
        if not teams_to_show:
            teams_to_show = all_teams_model
    else:
        teams_to_show = all_teams_model

    rows = []
    all_vals = []
    is_rel = (view_mode == 'Relative')

    for t_model in teams_to_show:
        t_short = model_to_short.get(t_model, t_model)
        row = {'Team': t_model, 'TeamShort': t_short, 'cells': {}}
        vals_list = []
        for gw in gws:
            matches = df_model[(df_model['event'] == gw) & ((df_model['team_h_model'] == t_model) | (df_model['team_a_model'] == t_model))]
            if matches.empty:
                row['cells'][gw] = {'val': None, 'val_str': '—', 'opp_str': '-'}
            else:
                m_vals = []
                opps = []
                for _, m in matches.iterrows():
                    if m['team_h_model'] == t_model:
                        if is_rel:
                            v = m['home_xg_rel'] if (metric_type == 'xg' and 'home_xg_rel' in m) else (m['home_cs_rel'] if 'home_cs_rel' in m else 1.0)
                        else:
                            v = m['home_xg'] if metric_type == 'xg' else m['home_cs']
                        opp = f"{m['team_a_short']} (H)"
                    else:
                        if is_rel:
                            v = m['away_xg_rel'] if (metric_type == 'xg' and 'away_xg_rel' in m) else (m['away_cs_rel'] if 'away_cs_rel' in m else 1.0)
                        else:
                            v = m['away_xg'] if metric_type == 'xg' else m['away_cs']
                        opp = f"{m['team_h_short']} (A)"
                    m_vals.append(v)
                    opps.append(opp)
                
                if metric_type == 'xg':
                    tot_val = sum(m_vals)
                    val_str = f"{tot_val:.2f}"
                else:
                    if is_rel:
                        tot_val = m_vals[0] if len(m_vals) == 1 else (np.prod(m_vals))
                        val_str = f"{tot_val:.2f}"
                    else:
                        tot_val = m_vals[0] if len(m_vals) == 1 else (np.prod([x/100 for x in m_vals])*100)
                        val_str = f"{tot_val:.1f}%"
                
                opp_str = ", ".join(opps)
                
                vals_list.append(tot_val)
                all_vals.append(tot_val)
                row['cells'][gw] = {'val': tot_val, 'val_str': val_str, 'opp_str': opp_str}
        
        if is_rel:
            decay_weights = np.array([0.95 ** i for i in range(len(vals_list))])
            sum_weights = float(np.sum(decay_weights)) if len(vals_list) > 0 else 1.0
            avg_val = float(np.sum(np.array(vals_list) * decay_weights) / sum_weights) if len(vals_list) > 0 else 1.0
            avg_str = f"{avg_val:.2f}"
        else:
            avg_val = float(np.mean(vals_list)) if vals_list else 0.0
            avg_str = f"{avg_val:.2f}" if metric_type == 'xg' else f"{avg_val:.1f}%"
            
        row['avg_val'] = avg_val
        row['avg_str'] = avg_str
        rows.append(row)

    rows = sorted(rows, key=lambda x: x['avg_val'], reverse=True)

    # Unified global table scaling across all cells in the entire table
    valid_vals = np.array([v for v in all_vals if v is not None])
    if len(valid_vals) > 0 and np.max(valid_vals) > np.min(valid_vals):
        p5 = float(np.percentile(valid_vals, 5))
        p95 = float(np.percentile(valid_vals, 95))
        median_val = 1.00 if is_rel else float(np.median(valid_vals))
    else:
        if is_rel:
            p5, p95, median_val = (0.6, 1.5, 1.00)
        else:
            p5, p95, median_val = (0.8, 2.2, 1.4) if metric_type == 'xg' else (10.0, 40.0, 25.0)

    def get_color(val):
        if val is None or pd.isna(val):
            return "transparent"
        if val >= median_val:
            denom = (p95 - median_val) if p95 > median_val else 1.0
            t = min(1.0, max(0.0, (val - median_val) / denom))
            alpha = 0.08 + (t ** 0.85) * 0.62
            return f"rgba(0, 180, 255, {alpha:.2f})"
        else:
            denom = (median_val - p5) if median_val > p5 else 1.0
            t = min(1.0, max(0.0, (median_val - val) / denom))
            alpha = 0.08 + (t ** 0.85) * 0.56
            return f"rgba(245, 140, 25, {alpha:.2f})"

    avg_header = "W.Avg" if is_rel else "Avg"

    html = [
        '<div class="proj-table-container">',
        f'<table class="proj-table" data-metric-type="{metric_type}" data-view-mode="{view_mode}" style="table-layout: fixed; width: 100%;">',
        '<colgroup>',
        '<col style="width: 200px;">',
    ]
    for gw in gws:
        html.append(f'<col data-gw="{gw}">')
    html.append('<col style="width: 98px;">')
    html.append('</colgroup>')
    html.append('<thead><tr>')
    html.append('<th class="team-th">Team</th>')
    for gw in gws:
        html.append(
            f'<th class="gw-th" data-gw="{gw}">'
            f'<div class="gw-th-content">'
            f'<span class="gw-title">GW {gw}</span>'
            f'<button type="button" class="gw-remove-btn" data-gw="{gw}" title="Hide GW {gw}">&times;</button>'
            f'</div>'
            f'</th>'
        )
    html.append(f'<th class="avg-th">{avg_header}</th>')
    html.append('</tr></thead><tbody>')

    for r in rows:
        avg_val_formatted = f"{r['avg_val']:.4f}"
        html.append(f'<tr data-team="{r["Team"]}" data-avg-val="{avg_val_formatted}">')
        html.append(f'<td class="team-td">{r["Team"]}</td>')
        
        for gw in gws:
            cell = r['cells'][gw]
            cell_bg = get_color(cell['val'])
            val_attr = f"{cell['val']:.4f}" if cell['val'] is not None else ""
            html.append(f'<td data-gw="{gw}" data-val="{val_attr}" style="background-color: {cell_bg};">')
            html.append(f'<div class="cell-val">{cell["val_str"]}</div>')
            html.append(f'<div class="cell-opp">{cell["opp_str"]}</div>')
            html.append('</td>')
            
        html.append(f'<td class="avg-td">{r["avg_str"]}</td>')
        html.append('</tr>')

    html.append('</tbody></table></div>')
    return "\n".join(html)


def get_current_active_gw(df_fix):
    """
    Dynamically determines the current active/upcoming Gameweek based on kickoff_time and match status.
    """
    try:
        now_utc = datetime.now(timezone.utc)
        if df_fix is None or df_fix.empty or 'kickoff_time' not in df_fix.columns:
            return 1
        
        df_temp = df_fix.dropna(subset=['event', 'kickoff_time']).copy()
        if df_temp.empty:
            return 1
            
        df_temp['kickoff_dt'] = pd.to_datetime(df_temp['kickoff_time'], errors='coerce')
        df_temp = df_temp.dropna(subset=['kickoff_dt'])
        if df_temp.empty:
            return 1
            
        if 'finished' in df_temp.columns:
            gw_agg = df_temp.groupby('event').agg(
                last_ko=('kickoff_dt', 'max'),
                all_finished=('finished', 'all')
            ).reset_index()
        else:
            gw_agg = df_temp.groupby('event').agg(
                last_ko=('kickoff_dt', 'max')
            ).reset_index()
            gw_agg['all_finished'] = False
            
        gw_agg['event'] = gw_agg['event'].astype(int)
        gw_agg = gw_agg.sort_values('event')
        
        for _, row in gw_agg.iterrows():
            gw = int(row['event'])
            last_ko = row['last_ko']
            if pd.isna(last_ko.tzinfo):
                last_ko = last_ko.replace(tzinfo=timezone.utc)
                
            gw_end_estimate = last_ko + timedelta(hours=2.5)
            if not row['all_finished'] and now_utc <= gw_end_estimate:
                return gw
            if now_utc <= gw_end_estimate:
                return gw
                
        unfinished = gw_agg[gw_agg['all_finished'] == False]
        if not unfinished.empty:
            return int(unfinished['event'].min())
            
        return 1
    except Exception:
        return 1


# ========================== FIXTURES PROJECTIONS (xG & CLEAN SHEETS) ==========================
try:
    df_fixtures = load_fixtures_model()
except Exception:
    df_fixtures = pd.DataFrame()

if not df_fixtures.empty:
    st.markdown("<hr style='margin: 1.8rem 0 1.2rem 0; opacity: 0.2;'>", unsafe_allow_html=True)
    
    st.markdown("""
        <style>
        /* Compact selectboxes in header */
        [data-testid="column"]:has(div[data-testid="stSelectbox"]) {
            min-width: 0 !important;
        }
        [data-testid="column"] [data-testid="stSelectbox"] {
            min-width: 0 !important;
        }
        [data-testid="column"] [data-baseweb="select"] {
            min-width: 0 !important;
            height: 38px !important;
        }
        [data-testid="column"] [data-baseweb="select"] > div {
            padding-left: 6px !important;
            padding-right: 2px !important;
            font-size: 0.81rem !important;
        }
        [data-testid="column"] label p {
            font-size: 0.75rem !important;
            white-space: nowrap !important;
            margin-bottom: 2px !important;
            line-height: 1.2 !important;
        }
        
        /* Refresh reset button styling & pixel-perfect alignment */
        [data-testid="column"]:has(div[data-testid="stButton"]) {
            min-width: 0 !important;
        }
        [data-testid="column"]:has(div[data-testid="stButton"]) div[data-testid="stButton"] {
            margin-top: 27px !important;
            margin-bottom: 0px !important;
            padding: 0px !important;
            width: 100% !important;
        }
        [data-testid="column"]:has(div[data-testid="stButton"]) button {
            height: 38px !important;
            min-height: 38px !important;
            max-height: 38px !important;
            padding: 0px !important;
            margin: 0px !important;
            width: 100% !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            border-radius: 6px !important;
            border: none !important;
            border-color: transparent !important;
            background: transparent !important;
            box-shadow: none !important;
            outline: none !important;
            box-sizing: border-box !important;
            overflow: hidden !important;
        }
        [data-testid="column"]:has(div[data-testid="stButton"]) button p,
        [data-testid="column"]:has(div[data-testid="stButton"]) button span,
        [data-testid="column"]:has(div[data-testid="stButton"]) button div {
            font-size: 1.85rem !important;
            line-height: 1 !important;
            margin: 0 !important;
            padding: 0 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            width: 100% !important;
            height: 100% !important;
            transform: scale(1.28);
        }
        [data-testid="column"]:has(div[data-testid="stButton"]) button:hover {
            border-color: transparent !important;
            border: none !important;
            background: transparent !important;
            box-shadow: none !important;
        }
        [data-testid="column"]:has(div[data-testid="stButton"]) button:hover p {
            transform: scale(1.36) rotate(90deg);
            transition: transform 0.25s ease !important;
        }
        </style>
    """, unsafe_allow_html=True)

    hdr_c1, hdr_c2, hdr_c3, hdr_c4, hdr_c5 = st.columns([0.69, 0.095, 0.065, 0.11, 0.04], gap="small")
    with hdr_c1:
        st.subheader("Expected Goals", anchor=False)
    with hdr_c2:
        view_mode = st.selectbox(
            "Table View",
            options=["Absolute", "Relative"],
            index=0,
            key="ts_view_mode_select"
        )
    with hdr_c3:
        gw_count_options = list(range(3, 17))
        default_count_idx = gw_count_options.index(12) if 12 in gw_count_options else len(gw_count_options) - 1
        num_gws = st.selectbox(
            "GWs To Show",
            options=gw_count_options,
            index=default_count_idx,
            key="ts_gw_count_select"
        )
    with hdr_c4:
        active_start_gw = get_current_active_gw(df_fixtures)
        max_start = 38 - num_gws + 1
        default_gw_idx = max(0, min(active_start_gw - 1, max_start - 1))
        gw_opts = [f"GW {i}-{i + num_gws - 1}" for i in range(1, max_start + 1)]
        
        selected_gw_str = st.selectbox(
            "GW Range",
            options=gw_opts,
            index=default_gw_idx,
            key=f"ts_gw_range_select_{num_gws}_{active_start_gw}"
        )
    with hdr_c5:
        if st.button("🔄", help="Reset all removed Gameweeks", key="ts_reset_gw_btn"):
            st.rerun()
        
    start_gw = int(selected_gw_str.split()[1].split('-')[0])
    end_gw = start_gw + num_gws - 1
    gws_window = list(range(start_gw, end_gw + 1))
    
    html_xg = build_projection_table_html(df_fixtures, metric_type='xg', view_mode=view_mode, gws=gws_window, selected_teams=final_teams)
    st.markdown(html_xg, unsafe_allow_html=True)
    
    st.subheader("Clean Sheets %" if view_mode == 'Absolute' else "Clean Sheets (Relative)", anchor=False)
    html_cs = build_projection_table_html(df_fixtures, metric_type='cs', view_mode=view_mode, gws=gws_window, selected_teams=final_teams)
    st.markdown(html_cs, unsafe_allow_html=True)


st.subheader("Historical Ratings", anchor=False)


hist_home = df_played[['match_date', 'season', 'league', 'home_team', 'home_team_code', 'home_rating_att_post', 'home_rating_def_post']].rename(
    columns={'match_date':'date', 'season':'season', 'league':'league', 'home_team':'team_name', 'home_team_code':'team_code', 'home_rating_att_post':'att', 'home_rating_def_post':'def'}
)
hist_away = df_played[['match_date', 'season', 'league', 'away_team', 'away_team_code', 'away_rating_att_post', 'away_rating_def_post']].rename(
    columns={'match_date':'date', 'season':'season', 'league':'league', 'away_team':'team_name', 'away_team_code':'team_code', 'away_rating_att_post':'att', 'away_rating_def_post':'def'}
)

df_hist = pd.concat([hist_home, hist_away]).sort_values('date')
df_hist = df_hist[df_hist['season'] != "2009/10"]
df_hist = df_hist[df_hist['league'] == 'Premier League']

if season_range:
    s_start, s_end = season_range
    df_hist = df_hist[(df_hist['season'] >= s_start) & (df_hist['season'] <= s_end)]

if final_teams:
    df_hist = df_hist[df_hist['team_code'].isin(final_teams)]

if not df_hist.empty:
    df_hist['total'] = df_hist['att'] - df_hist['def']


    selected_seasons = sorted(df_hist['season'].unique())
    season_offsets = {}
    curr_offset = 0
    season_boundaries = []
    season_start_boundaries = []
    tick_vals = []
    tick_text = []

    for s in selected_seasons:
        s_df = df_hist[df_hist['season'] == s]
        max_m = s_df.groupby('team_name').size().max() if not s_df.empty else 38
        start_x = curr_offset + 0.5
        end_x = curr_offset + max_m + 0.5
        mid_x = (start_x + end_x) / 2

        season_start_boundaries.append(start_x)
        season_boundaries.append(end_x)
        tick_vals.append(mid_x)
        tick_text.append(s)

        season_offsets[s] = (curr_offset, max_m)
        curr_offset += max_m

    df_hist = df_hist.sort_values('date').copy()
    df_hist['match_in_season'] = df_hist.groupby(['team_name', 'season'])['date'].rank(method='first').astype(int)
    df_hist['offset'] = df_hist['season'].map(lambda s: season_offsets[s][0] if s in season_offsets else 0)
    df_hist['x_pos'] = df_hist['offset'] + df_hist['match_in_season']

    def create_chart(df, y_col, title):
        fig = go.Figure()
        all_annotations = []


        is_defense = (title in ["Defence Rating", "Defense Rating"])
        latest_ratings = {}
        for t in df['team_name'].unique():
            tdf_t = df[df['team_name'] == t].dropna(subset=[y_col]).sort_values('x_pos')
            if not tdf_t.empty:
                latest_ratings[t] = tdf_t[y_col].iloc[-1]
            else:
                latest_ratings[t] = 999 if is_defense else -999

        sorted_teams = sorted(df['team_name'].unique(), key=lambda t: latest_ratings.get(t, 999 if is_defense else -999), reverse=not is_defense)
        is_light = (get_active_theme() == 'light')
        active_team_colors = team_colors_light if is_light else team_colors_dark

        for t_name in sorted_teams:
            tdf = df[df['team_name'] == t_name].sort_values('x_pos').copy()
            tdf_clean = tdf.dropna(subset=[y_col])

            if tdf_clean.empty:
                continue


            team_seasons = sorted(tdf['season'].dropna().unique())
            endpoints_list = []
            for s in team_seasons:
                if s not in selected_seasons:
                    continue
                s_idx = selected_seasons.index(s)
                is_last_selected_season = (s_idx == len(selected_seasons) - 1)
                next_selected_season = selected_seasons[s_idx + 1] if not is_last_selected_season else None

                if is_last_selected_season or (next_selected_season not in team_seasons):
                    s_clean = tdf_clean[tdf_clean['season'] == s]
                    if not s_clean.empty:
                        endpoints_list.append(s_clean.iloc[-1])

            endpoints = pd.DataFrame(endpoints_list) if endpoints_list else pd.DataFrame()

            season_changed = (tdf['season'] != tdf['season'].shift(1)) & tdf['season'].shift(1).notna()
            gap_occurred = (tdf['x_pos'].diff() > 1.5)
            break_lines = season_changed | gap_occurred

            if break_lines.any():
                insertions = []
                for idx, row in tdf[break_lines].iterrows():
                    nan_row = row.copy()
                    nan_row[y_col] = np.nan
                    nan_row['x_pos'] = row['x_pos'] - 0.5
                    insertions.append(nan_row)
                if insertions:
                    tdf = pd.concat([tdf, pd.DataFrame(insertions)]).sort_values('x_pos')

            color = active_team_colors.get(t_name, '#888888')
            t_code = tdf['team_code'].dropna().iloc[0] if not tdf['team_code'].dropna().empty else t_name

            date_str = tdf['date'].dt.strftime('%d/%m/%Y').fillna('')
            season_str = tdf['season'].fillna('')
            gw_str = "GW " + tdf['match_in_season'].astype(int).astype(str)
            customdata = np.column_stack((date_str, season_str, gw_str))

            fig.add_trace(go.Scatter(
                x=tdf['x_pos'], y=tdf[y_col],
                mode='lines',
                name=t_code,
                line=dict(color=color, width=2),
                customdata=customdata,
                hovertemplate=f"<b>{t_code}</b> (%{{customdata[0]}})<br>Rating: %{{y:.3f}} <extra>%{{customdata[2]}}</extra>",
                showlegend=False
            ))

            for _, ep in endpoints.iterrows():
                if pd.notna(ep[y_col]):
                    all_annotations.append({
                        'x': ep['x_pos'],
                        'y': ep[y_col],
                        'text': t_code,
                        'color': color
                    })


        if all_annotations:
            ann_df = pd.DataFrame(all_annotations)
            y_min = df[y_col].min()
            y_max = df[y_col].max()
            y_span = (y_max - y_min) if (pd.notna(y_max) and pd.notna(y_min) and y_max > y_min) else 1.0


            min_gap = max(0.015, y_span * 0.020)
            max_shift = min_gap * 2.5
            is_reversed = (title in ["Defence Rating", "Defense Rating"])

            for x_val, group in ann_df.groupby('x'):
                if len(group) == 1:
                    r = group.iloc[0]
                    fig.add_annotation(
                        x=r['x'], y=r['y'], text=r['text'],
                        showarrow=False,
                        font=dict(color=r['color'], size=11, family="Arial, sans-serif"),
                        xanchor='left', xshift=5
                    )
                else:
                    if is_reversed:
                        y_sorted = group.sort_values('y', ascending=True)
                    else:
                        y_sorted = group.sort_values('y', ascending=False)

                    y_vals = y_sorted['y'].values.copy()

                    if is_reversed:
                        for i in range(1, len(y_vals)):
                            if y_vals[i] - y_vals[i-1] < min_gap:
                                y_vals[i] = y_vals[i-1] + min_gap
                    else:
                        for i in range(1, len(y_vals)):
                            if y_vals[i-1] - y_vals[i] < min_gap:
                                y_vals[i] = y_vals[i-1] - min_gap

                    shift_center = y_vals.mean() - y_sorted['y'].values.mean()
                    y_vals -= shift_center


                    shifts = y_vals - y_sorted['y'].values
                    shifts_clamped = np.clip(shifts, -max_shift, max_shift)
                    final_y = y_sorted['y'].values + shifts_clamped

                    for idx, (_, r) in enumerate(y_sorted.iterrows()):
                        adj_y = final_y[idx]
                        fig.add_annotation(
                            x=r['x'], y=adj_y, text=r['text'],
                            showarrow=False,
                            font=dict(color=r['color'], size=11, family="Arial, sans-serif"),
                            xanchor='left', xshift=5
                        )


        for sb in season_start_boundaries:
            fig.add_vline(x=sb, line_dash="dash", line_color="rgba(150, 150, 150, 0.5)", line_width=1)
        if season_boundaries:
            fig.add_vline(x=season_boundaries[-1], line_dash="dash", line_color="rgba(150, 150, 150, 0.5)", line_width=1)

        yaxis_config = dict(title="Rating", nticks=20)
        if title in ["Defence Rating", "Defense Rating"]:
            yaxis_config['autorange'] = "reversed"

        fig.update_layout(
            title=title,
            xaxis=dict(
                tickmode='array',
                tickvals=tick_vals,
                ticktext=tick_text,
                title="",
                showgrid=False
            ),
            yaxis=yaxis_config,
            height=800,
            hovermode="x unified",
            margin=dict(l=20, r=80, t=40, b=20),
            showlegend=False
        )
        return fig

    st.plotly_chart(create_chart(df_hist, 'total', "Overall Rating (Attack - Defence)"), width="stretch")
    st.plotly_chart(create_chart(df_hist, 'att', "Attack Rating"), width="stretch")
    st.plotly_chart(create_chart(df_hist, 'def', "Defence Rating"), width="stretch")

    light_map = {code: team_colors_light.get(name, team_colors_dark.get(name, '#888888')) for code, name in team_code_to_name.items()}
    dark_map = {code: team_colors_dark.get(name, team_colors_light.get(name, '#888888')) for code, name in team_code_to_name.items()}
    for name, color in team_colors_light.items(): light_map[name] = color
    for name, color in team_colors_dark.items(): dark_map[name] = color
    light_map_json = json.dumps(light_map)
    dark_map_json = json.dumps(dark_map)

    js_hover_sorter = f"""
    <script>
    (function() {{
        var teamColorsLight = {light_map_json};
        var teamColorsDark = {dark_map_json};

        function getDetectedTheme() {{
            try {{
                var doc = window.parent.document;
                var app = doc.querySelector('.stApp') || doc.body;
                if (!app) return 'dark';

                var bg = window.getComputedStyle(app).backgroundColor;
                if (bg) {{
                    var m = bg.match(/rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)/);
                    if (m) {{
                        var r = parseInt(m[1], 10);
                        var g = parseInt(m[2], 10);
                        var b = parseInt(m[3], 10);
                        var lum = 0.299 * r + 0.587 * g + 0.114 * b;
                        return lum > 140 ? 'light' : 'dark';
                    }}
                }}
            }} catch(e) {{}}
            return 'dark';
        }}

        function updateChartColors() {{
            try {{
                var doc = window.parent.document;
                var currentTheme = getDetectedTheme();
                var colorsMap = (currentTheme === 'light') ? teamColorsLight : teamColorsDark;

                var chartContainers = doc.querySelectorAll('.js-plotly-plot');
                chartContainers.forEach(function(plotEl) {{
                    if (!plotEl.data || !plotEl.layout) return;

                    var plotlyGlobal = window.parent.Plotly || window.Plotly;
                    var needsTraceUpdate = false;
                    var newColors = [];

                    plotEl.data.forEach(function(trace) {{
                        var c = colorsMap[trace.name] || (trace.line ? trace.line.color : '#888888');
                        newColors.push(c);
                        if (trace.line && trace.line.color !== c) {{
                            trace.line.color = c;
                            needsTraceUpdate = true;
                        }}
                    }});

                    var needsAnnUpdate = false;
                    if (plotEl.layout.annotations) {{
                        plotEl.layout.annotations.forEach(function(ann) {{
                            var annCode = ann.text;
                            if (colorsMap[annCode]) {{
                                var targetCol = colorsMap[annCode];
                                if (!ann.font || ann.font.color !== targetCol) {{
                                    ann.font = Object.assign({{}}, ann.font || {{}}, {{ color: targetCol }});
                                    needsAnnUpdate = true;
                                }}
                            }}
                        }});
                    }}

                    if ((needsTraceUpdate || needsAnnUpdate) && plotlyGlobal) {{
                        try {{
                            plotlyGlobal.react(plotEl, plotEl.data, plotEl.layout);
                        }} catch(err) {{
                            try {{
                                if (needsTraceUpdate) plotlyGlobal.restyle(plotEl, {{ 'line.color': newColors }});
                                if (needsAnnUpdate) plotlyGlobal.relayout(plotEl, {{ annotations: plotEl.layout.annotations }});
                            }} catch(err2) {{}}
                        }}
                    }}
                }});
            }} catch(e) {{}}
        }}

        function sortHoverBoxes() {{
            try {{
                var doc = window.parent.document;
                var hoverlayers = doc.querySelectorAll('.hoverlayer');
                hoverlayers.forEach(function(hoverlayer) {{
                    var groups = hoverlayer.querySelector('.groups');
                    if (!groups) return;
                    var traces = Array.from(groups.querySelectorAll('g.traces'));

                    var chartContainer = hoverlayer.closest('.js-plotly-plot');
                    var isDefense = false;
                    if (chartContainer) {{
                        var tEl = chartContainer.querySelector('.gtitle');
                        if (tEl && (tEl.textContent.includes('Defence Rating') || tEl.textContent.includes('Defense Rating'))) {{
                            isDefense = true;
                        }}
                    }}

                    var activeItems = [];
                    var activeYs = [];

                    traces.forEach(function(t) {{
                        var txt = t.innerText || t.textContent || '';
                        var mGw = txt.match(/GW\\s*\\d+/);
                        var mVal = txt.match(/Rating:\\s*([0-9.-]+)/);
                        var tr = t.getAttribute('transform') || '';
                        var mY = tr.match(/translate\\(([^,]+),\\s*([0-9.-]+)\\)/);

                        if (mVal && mY) {{
                            var yVal = parseFloat(mY[2]);
                            var rVal = parseFloat(mVal[1]);
                            if (yVal > 0 && !isNaN(rVal)) {{
                                var gwStr = mGw ? mGw[0] : '';
                                activeItems.push({{ node: t, val: rVal, xVal: mY[1], yVal: yVal, gwStr: gwStr }});
                            }}
                        }}
                    }});

                    // Filter out traces from adjacent season at season boundary
                    var gwCounts = {{}};
                    activeItems.forEach(function(item) {{
                        if (item.gwStr) gwCounts[item.gwStr] = (gwCounts[item.gwStr] || 0) + 1;
                    }});
                    var majorityGw = null;
                    var maxCount = 0;
                    for (var gw in gwCounts) {{
                        if (gwCounts[gw] > maxCount) {{
                            maxCount = gwCounts[gw];
                            majorityGw = gw;
                        }}
                    }}
                    if (majorityGw) {{
                        activeItems = activeItems.filter(function(item) {{ return item.gwStr === majorityGw; }});
                    }}

                    // Hide non-matching traces from DOM
                    traces.forEach(function(t) {{
                        var isKeeper = activeItems.some(function(item) {{ return item.node === t; }});
                        if (!isKeeper) {{
                            t.style.display = 'none';
                        }} else {{
                            t.style.display = '';
                        }}
                    }});

                    if (activeItems.length > 0 && activeItems[0].gwStr) {{
                        var titleEl = hoverlayer.querySelector('text.legendtitletext');
                        if (titleEl) {{
                            titleEl.innerHTML = '<tspan style="font-weight:bold">' + activeItems[0].gwStr + '</tspan>';
                        }}
                    }}

                    if (activeItems.length > 1) {{
                        var activeYs = activeItems.map(function(item) {{ return item.yVal; }}).sort(function(a, b) {{ return a - b; }});

                        activeItems.sort(function(a, b) {{
                            return isDefense ? (a.val - b.val) : (b.val - a.val);
                        }});

                        activeItems.forEach(function(item, idx) {{
                            var newTr = 'translate(' + item.xVal + ',' + activeYs[idx] + ')';
                            item.node.setAttribute('transform', newTr);
                            groups.appendChild(item.node);
                        }});
                    }}
                }});
            }} catch(e) {{}}
        }}

        // ========================== LIVE PROJECTION TABLES GW REMOVAL & RESET ==========================
        function removeGwColumn(gw) {{
            try {{
                var doc = window.parent.document || document;
                var tables = doc.querySelectorAll('.proj-table');
                tables.forEach(function(table) {{
                    var cols = table.querySelectorAll('colgroup col[data-gw="' + gw + '"]');
                    cols.forEach(function(c) {{ c.style.display = 'none'; }});
                    
                    var ths = table.querySelectorAll('thead th[data-gw="' + gw + '"]');
                    ths.forEach(function(th) {{ th.style.display = 'none'; }});
                    
                    var tds = table.querySelectorAll('tbody td[data-gw="' + gw + '"]');
                    tds.forEach(function(td) {{ td.style.display = 'none'; }});
                    
                    recalculateTable(table);
                }});
            }} catch(e) {{
                console.error("Error removing GW column:", e);
            }}
        }}

        function resetAllGwColumns() {{
            try {{
                var doc = window.parent.document || document;
                var tables = doc.querySelectorAll('.proj-table');
                tables.forEach(function(table) {{
                    var cols = table.querySelectorAll('colgroup col[data-gw]');
                    cols.forEach(function(c) {{ c.style.display = ''; }});
                    
                    var ths = table.querySelectorAll('thead th[data-gw]');
                    ths.forEach(function(th) {{ th.style.display = ''; }});
                    
                    var tds = table.querySelectorAll('tbody td[data-gw]');
                    tds.forEach(function(td) {{ td.style.display = ''; }});
                    
                    recalculateTable(table);
                }});
            }} catch(e) {{
                console.error("Error resetting GW columns:", e);
            }}
        }}

        function recalculateTable(table) {{
            var isRel = (table.getAttribute('data-view-mode') === 'Relative');
            var isXg = (table.getAttribute('data-metric-type') === 'xg');
            var tbody = table.querySelector('tbody');
            if (!tbody) return;
            var rows = Array.from(tbody.querySelectorAll('tr'));
            
            var ths = Array.from(table.querySelectorAll('thead th.gw-th'));
            var visibleGws = ths.filter(function(th) {{
                return th.style.display !== 'none';
            }}).map(function(th) {{
                return th.getAttribute('data-gw');
            }});
            
            rows.forEach(function(row) {{
                var vals = [];
                visibleGws.forEach(function(gw) {{
                    var td = row.querySelector('td[data-gw="' + gw + '"]');
                    if (td) {{
                        var valAttr = td.getAttribute('data-val');
                        if (valAttr !== null && valAttr !== '' && valAttr !== 'null') {{
                            var num = parseFloat(valAttr);
                            if (!isNaN(num)) {{
                                vals.push(num);
                            }}
                        }}
                    }}
                }});
                
                var avgVal = 0.0;
                var avgStr = '—';
                
                if (vals.length > 0) {{
                    if (isRel) {{
                        var sumWeighted = 0.0;
                        var sumWeights = 0.0;
                        for (var i = 0; i < vals.length; i++) {{
                            var w = Math.pow(0.95, i);
                            sumWeighted += vals[i] * w;
                            sumWeights += w;
                        }}
                        avgVal = sumWeights > 0 ? (sumWeighted / sumWeights) : 1.0;
                        avgStr = avgVal.toFixed(2);
                    }} else {{
                        var sum = 0.0;
                        for (var i = 0; i < vals.length; i++) {{
                            sum += vals[i];
                        }}
                        avgVal = sum / vals.length;
                        if (isXg) {{
                            avgStr = avgVal.toFixed(2);
                        }} else {{
                            avgStr = avgVal.toFixed(1) + '%';
                        }}
                    }}
                }}
                
                row.setAttribute('data-avg-val', avgVal.toFixed(4));
                var avgTd = row.querySelector('.avg-td');
                if (avgTd) {{
                    avgTd.textContent = avgStr;
                }}
            }});
            
            rows.sort(function(a, b) {{
                var vA = parseFloat(a.getAttribute('data-avg-val')) || 0;
                var vB = parseFloat(b.getAttribute('data-avg-val')) || 0;
                return vB - vA;
            }});
            
            rows.forEach(function(r) {{
                tbody.appendChild(r);
            }});
        }}

        // Attach delegated listener on parent document
        try {{
            var doc = window.parent.document || document;
            if (!doc.__gwTableListenersAttached) {{
                doc.__gwTableListenersAttached = true;
                doc.addEventListener('click', function(e) {{
                    var removeBtn = e.target.closest('.gw-remove-btn');
                    if (removeBtn) {{
                        e.preventDefault();
                        e.stopPropagation();
                        var gw = removeBtn.getAttribute('data-gw') || removeBtn.closest('th')?.getAttribute('data-gw');
                        if (gw) {{
                            removeGwColumn(gw);
                        }}
                        return;
                    }}

                    var resetBtn = e.target.closest('button[key="ts_reset_gw_btn"]') || e.target.closest('button');
                    if (resetBtn && (resetBtn.innerText.includes('🔄') || resetBtn.getAttribute('key') === 'ts_reset_gw_btn')) {{
                        resetAllGwColumns();
                    }}
                }});
            }}
        }} catch(e) {{}}

        function alignRefreshButton() {{
            try {{
                var doc = window.parent.document || document;
                var btns = doc.querySelectorAll('.stButton button, [data-testid="stButton"] button');
                btns.forEach(function(btn) {{
                    if (btn.innerText && btn.innerText.includes('🔄')) {{
                        var btnDiv = btn.closest('.stButton') || btn.closest('[data-testid="stButton"]');
                        if (btnDiv) {{
                            btnDiv.style.setProperty('margin-top', '27px', 'important');
                            btnDiv.style.setProperty('margin-bottom', '0px', 'important');
                            btnDiv.style.setProperty('padding-top', '0px', 'important');
                            btnDiv.style.setProperty('padding-bottom', '0px', 'important');
                        }}
                        btn.style.setProperty('height', '38px', 'important');
                        btn.style.setProperty('min-height', '38px', 'important');
                        btn.style.setProperty('max-height', '38px', 'important');
                        btn.style.setProperty('padding', '0px', 'important');
                        btn.style.setProperty('margin', '0px', 'important');
                        btn.style.setProperty('display', 'flex', 'important');
                        btn.style.setProperty('align-items', 'center', 'important');
                        btn.style.setProperty('justify-content', 'center', 'important');
                        btn.style.setProperty('overflow', 'hidden', 'important');
                        btn.style.setProperty('border', 'none', 'important');
                        btn.style.setProperty('border-color', 'transparent', 'important');
                        btn.style.setProperty('background', 'transparent', 'important');
                        btn.style.setProperty('box-shadow', 'none', 'important');
                        btn.style.setProperty('outline', 'none', 'important');
                        
                        var pEl = btn.querySelector('p') || btn.querySelector('div') || btn.querySelector('span');
                        if (pEl) {{
                            pEl.style.setProperty('font-size', '1.85rem', 'important');
                            pEl.style.setProperty('line-height', '1', 'important');
                            pEl.style.setProperty('margin', '0px', 'important');
                            pEl.style.setProperty('padding', '0px', 'important');
                            pEl.style.setProperty('display', 'flex', 'important');
                            pEl.style.setProperty('align-items', 'center', 'important');
                            pEl.style.setProperty('justify-content', 'center', 'important');
                            pEl.style.setProperty('transform', 'scale(1.28)', 'important');
                        }}
                    }}
                }});
            }} catch(e) {{}}
        }}

        setInterval(function() {{
            sortHoverBoxes();
            updateChartColors();
            alignRefreshButton();
        }}, 60);
    }})();
    </script>
    """
    st.components.v1.html(js_hover_sorter, height=0, scrolling=False)
else:
    st.info("No historical data available for selected filters.")
