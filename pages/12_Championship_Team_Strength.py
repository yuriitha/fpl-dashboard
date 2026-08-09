import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import json
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

st.set_page_config(
    page_title="Championship Team Strength",
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
    </style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)
def load_data():
    url = "http://194.99.22.193:8000/team_strength_model"
    df = pd.read_parquet(url)
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"Помилка завантаження: {e}")
    st.stop()

# Get teams and colors
team_colors = {}
team_code_to_name = {}

# Populate team_colors by team name to avoid collisions where different teams share the same code
for _, row in df[['home_team', 'home_color']].dropna().drop_duplicates().iterrows():
    if row['home_team'] not in team_colors: team_colors[row['home_team']] = row['home_color']
for _, row in df[['away_team', 'away_color']].dropna().drop_duplicates().iterrows():
    if row['away_team'] not in team_colors: team_colors[row['away_team']] = row['away_color']

# For team_code_to_name, we prioritize Championship teams to ensure codes resolve to the expected Championship team
ch_teams_all = df[df['league'] == 'Championship']
for _, row in ch_teams_all[['home_team_code', 'home_team']].dropna().drop_duplicates().iterrows():
    team_code_to_name[row['home_team_code']] = row['home_team']
for _, row in ch_teams_all[['away_team_code', 'away_team']].dropna().drop_duplicates().iterrows():
    team_code_to_name[row['away_team_code']] = row['away_team']

# Fallback for teams not in Championship (using first occurrence)
for _, row in df[['home_team_code', 'home_team']].dropna().drop_duplicates().iterrows():
    if row['home_team_code'] not in team_code_to_name: team_code_to_name[row['home_team_code']] = row['home_team']
for _, row in df[['away_team_code', 'away_team']].dropna().drop_duplicates().iterrows():
    if row['away_team_code'] not in team_code_to_name: team_code_to_name[row['away_team_code']] = row['away_team']

all_seasons = sorted([s for s in df['season'].dropna().unique() if s != "2009/10"])

# Sidebar
if st.sidebar.button("Reset All Filters", width="stretch", type="primary"):
    keys_to_delete = [k for k in st.session_state.keys() if k.startswith('ts_')]
    for key in keys_to_delete:
        del st.session_state[key]
    st.rerun()

# Seasons Filter
season_range = st.sidebar.select_slider(
    "Seasons",
    options=all_seasons,
    value=(all_seasons[-2], all_seasons[-1]) if len(all_seasons) >= 2 else (all_seasons[-1], all_seasons[-1]),
    key="ts_ch_seasons"
)

s_start, s_end = season_range
ch_df = df[(df['league'] == 'Championship') & (df['season'] >= s_start) & (df['season'] <= s_end)]
all_teams = sorted([t for t in set(ch_df['home_team_code'].dropna()).union(set(ch_df['away_team_code'].dropna())) if t and str(t).strip()])

# Session state
if 'ts_ch_pills_teams' not in st.session_state or st.session_state.get('ts_ch_prev_all_teams') != all_teams:
    st.session_state.ts_ch_pills_teams = all_teams
    st.session_state.ts_ch_prev_all_teams = all_teams

search_name = st.sidebar.text_input("Search Team", placeholder="Enter team name...", key="ts_ch_search_name")

# Filter Header Helper
def filter_header(label, options, key_prefix):
    cols = st.sidebar.columns([1.4, 0.8, 0.8])
    cols[0].markdown(f"<p style='font-size:0.875rem;margin-bottom:0'>{label}</p>", unsafe_allow_html=True)
    if cols[1].button("All", key=f"btn_all_{key_prefix}", width="stretch"):
        st.session_state[f"ts_{key_prefix}"] = options
        st.rerun()
    if cols[2].button("None", key=f"btn_none_{key_prefix}", width="stretch"):
        st.session_state[f"ts_{key_prefix}"] = []
        st.rerun()

filter_header("Teams", all_teams, "ch_pills_teams")
selected_teams = st.sidebar.pills(
    "Teams", options=all_teams, key="ts_ch_pills_teams",
    selection_mode="multi", label_visibility="collapsed"
)

# Apply team search filter
final_teams = selected_teams if selected_teams else []
if search_name:
    final_teams = [t for t in final_teams if search_name.lower() in t.lower() or search_name.lower() in team_code_to_name.get(t, "").lower()]

# JS Injection for sidebar layout to gray out unselected
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
            }});
        }} catch(e) {{}}
    }}
    setInterval(forceLayout, 300);
}}).call(this);
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
                
            # Apply power transformation to make differences more expressive near the transparency point
            intensity = intensity ** power
            
            dynamic_alpha = intensity * alpha
            styles.append(f'background-color: rgba({int(r*255)}, {int(g*255)}, {int(b*255)}, {dynamic_alpha:.3f})')
    return styles

light_blues = mcolors.LinearSegmentedColormap.from_list("LightBlues", ["#ffffff", "#00BFFF"])
orange_blue = mcolors.LinearSegmentedColormap.from_list("OrangeBlue", ["#ff8c00", "#ffffff", "#00BFFF"])

# === MAIN CONTENT ===
col1, col2 = st.columns([0.35, 0.65])

# Current Ratings Table
with col1:
    st.subheader("Current Team Ratings", anchor=False)
    
    current_season = all_seasons[-1]
    curr_season_df = df[(df['league'] == 'Championship') & (df['season'] == current_season)]
    current_season_teams = sorted(list(set(curr_season_df['home_team_code'].dropna()).union(set(curr_season_df['away_team_code'].dropna()))))
    
    df_played = df.dropna(subset=['match_result'])
    latest_home = df_played.sort_values('match_date').groupby('home_team_code').last()[['match_date', 'home_rating_att_post', 'home_rating_def_post']]
    latest_away = df_played.sort_values('match_date').groupby('away_team_code').last()[['match_date', 'away_rating_att_post', 'away_rating_def_post']]
    
    df_unplayed = df[df['match_result'].isna()]
    first_unplayed_home = df_unplayed.sort_values('match_date').groupby('home_team_code').first()[['match_date', 'home_rating_att', 'home_rating_def']]
    first_unplayed_away = df_unplayed.sort_values('match_date').groupby('away_team_code').first()[['match_date', 'away_rating_att', 'away_rating_def']]
    
    current_ratings = []
    for t_code in current_season_teams:
        
        uh = first_unplayed_home.loc[t_code] if t_code in first_unplayed_home.index else None
        ua = first_unplayed_away.loc[t_code] if t_code in first_unplayed_away.index else None
        
        att, def_rating = None, None
        
        # 1. Try to get pre-match ratings from the FIRST unplayed match
        if uh is not None and ua is not None:
            if uh['match_date'] < ua['match_date']:
                att, def_rating = uh['home_rating_att'], uh['home_rating_def']
            else:
                att, def_rating = ua['away_rating_att'], ua['away_rating_def']
        elif uh is not None:
            att, def_rating = uh['home_rating_att'], uh['home_rating_def']
        elif ua is not None:
            att, def_rating = ua['away_rating_att'], ua['away_rating_def']
            
        # 2. If no unplayed matches, fallback to post-match ratings of the LAST played match
        if pd.isna(att) or pd.isna(def_rating):
            h = latest_home.loc[t_code] if t_code in latest_home.index else None
            a = latest_away.loc[t_code] if t_code in latest_away.index else None
            
            if h is not None and a is not None:
                if h['match_date'] > a['match_date']:
                    att, def_rating = h['home_rating_att_post'], h['home_rating_def_post']
                else:
                    att, def_rating = a['away_rating_att_post'], a['away_rating_def_post']
            elif h is not None:
                att, def_rating = h['home_rating_att_post'], h['home_rating_def_post']
            elif a is not None:
                att, def_rating = a['away_rating_att_post'], a['away_rating_def_post']
            
        if pd.notna(att) and pd.notna(def_rating):
            current_ratings.append({
                'Team': team_code_to_name.get(t_code, t_code),
                'Attack Rating': att,
                'Defense Rating': def_rating,
                'Overall Rating': att - def_rating
            })
            
    if current_ratings:
        df_ratings = pd.DataFrame(current_ratings).sort_values('Overall Rating', ascending=False).reset_index(drop=True)
        df_ratings.index = df_ratings.index + 1
        df_ratings.reset_index(inplace=True)
        df_ratings.rename(columns={'index': 'Pos', 'Attack Rating': 'Attack', 'Defense Rating': 'Defense', 'Overall Rating': 'Overall'}, inplace=True)

        df_ratings_styled = df_ratings.style \
            .apply(soft_gradient, cmap_name='YlGn', alpha=0.6, transparent_at='min', power=0.6, subset=['Attack']) \
            .apply(soft_gradient, cmap_name='YlGn_r', alpha=0.6, transparent_at='max', power=0.6, subset=['Defense']) \
            .apply(soft_gradient, cmap_name='RdYlGn', alpha=0.6, transparent_at='mid', power=0.6, subset=['Overall']) \
            .format(precision=3)
        
        st.dataframe(
            df_ratings_styled,
            hide_index=True,
            width="stretch",
            height=878, # Adjusted for 24 teams
            column_config={
                'Pos': st.column_config.NumberColumn("Pos", width=30),
                'Team': st.column_config.TextColumn("Team"),
                'Attack': st.column_config.NumberColumn("Attack", format="%.3f", width=65),
                'Defense': st.column_config.NumberColumn("Defense", format="%.3f", width=65),
                'Overall': st.column_config.NumberColumn("Overall", format="%.3f", width=65),
            }
        )
    else:
        st.info("No teams selected.")

# Upcoming Matches Table
with col2:
    st.subheader("Upcoming Matches", anchor=False)
    df_future = df[(df['match_result'].isna()) & (df['league'] == 'Championship')].copy()
    if not df_future.empty:
        cols = ['match_date', 'home_team', 'away_team', 'home_team_code', 'away_team_code', 'home_xg', 'away_xg', 'home_xg_odds', 'away_xg_odds', 'home_delta', 'away_delta']
        df_future = df_future[cols].sort_values('match_date')
        
        df_future = df_future.drop(columns=['home_team_code', 'away_team_code'])
            
        xg_cols = ['home_xg', 'away_xg', 'home_xg_odds', 'away_xg_odds']
        xg_min = df_future[xg_cols].min().min()
        xg_max = df_future[xg_cols].max().max()

        df_future_styled = df_future.style \
            .apply(soft_gradient, cmap_name=light_blues, alpha=0.6, fixed_min=xg_min, fixed_max=xg_max, transparent_at='min', power=0.6, subset=xg_cols) \
            .apply(soft_gradient, cmap_name=orange_blue, alpha=0.6, fixed_min=-0.45, fixed_max=0.45, transparent_at='mid', power=0.6, subset=['home_delta', 'away_delta']) \
            .format(precision=2)
            
        st.dataframe(
            df_future_styled,
            hide_index=True,
            width="stretch",
            height=len(df_future) * 35 + 40,
            column_config={
                'match_date': st.column_config.DatetimeColumn("Date", format="DD/MM/YYYY HH:mm"),
                'home_team': st.column_config.TextColumn("Home"),
                'away_team': st.column_config.TextColumn("Away"),
                'home_xg': st.column_config.NumberColumn("Model xG (H)", format="%.2f", width=50),
                'away_xg': st.column_config.NumberColumn("Model xG (A)", format="%.2f", width=50),
                'home_xg_odds': st.column_config.NumberColumn("Odds xG (H)", format="%.2f", width=50),
                'away_xg_odds': st.column_config.NumberColumn("Odds xG (A)", format="%.2f", width=50),
                'home_delta': st.column_config.NumberColumn("Delta (H)", format="%.2f", width=50),
                'away_delta': st.column_config.NumberColumn("Delta (A)", format="%.2f", width=50),
            }
        )
    else:
        st.info("No upcoming matches found.")

# Charts
st.subheader("Historical Ratings", anchor=False)

# Prepare historical data
hist_home = df_played[['match_date', 'season', 'league', 'home_team', 'home_team_code', 'home_rating_att_post', 'home_rating_def_post']].rename(
    columns={'match_date':'date', 'season':'season', 'league':'league', 'home_team':'team_name', 'home_team_code':'team_code', 'home_rating_att_post':'att', 'home_rating_def_post':'def'}
)
hist_away = df_played[['match_date', 'season', 'league', 'away_team', 'away_team_code', 'away_rating_att_post', 'away_rating_def_post']].rename(
    columns={'match_date':'date', 'season':'season', 'league':'league', 'away_team':'team_name', 'away_team_code':'team_code', 'away_rating_att_post':'att', 'away_rating_def_post':'def'}
)

df_hist = pd.concat([hist_home, hist_away]).sort_values('date')
df_hist = df_hist[df_hist['season'] != "2009/10"] # Exclude first season
df_hist = df_hist[df_hist['league'] == 'Championship'] # Only Championship matches

if season_range:
    s_start, s_end = season_range
    df_hist = df_hist[(df_hist['season'] >= s_start) & (df_hist['season'] <= s_end)]

if final_teams:
    df_hist = df_hist[df_hist['team_code'].isin(final_teams)]

if not df_hist.empty:
    df_hist['total'] = df_hist['att'] - df_hist['def']

    # Compute global X indices per season so all teams in the same season align on X-axis
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

        # Sort teams by their latest rating so hover entries appear in descending order of strength
        is_defense = (title == "Defense Rating")
        latest_ratings = {}
        for t in df['team_name'].unique():
            tdf_t = df[df['team_name'] == t].dropna(subset=[y_col]).sort_values('x_pos')
            if not tdf_t.empty:
                latest_ratings[t] = tdf_t[y_col].iloc[-1]
            else:
                latest_ratings[t] = 999 if is_defense else -999

        sorted_teams = sorted(df['team_name'].unique(), key=lambda t: latest_ratings.get(t, 999 if is_defense else -999), reverse=not is_defense)

        for t_name in sorted_teams:
            tdf = df[df['team_name'] == t_name].sort_values('x_pos').copy()
            tdf_clean = tdf.dropna(subset=[y_col])
            
            if tdf_clean.empty:
                continue

            # Знаходимо кінці відрізків для підписів назв команд
            next_x = tdf['x_pos'].shift(-1)
            is_end = (next_x - tdf['x_pos'] > 1.5) | next_x.isna()
            endpoints = tdf[is_end]
            
            # Вставляємо NaN для проміжків у x_pos > 1.5, щоб розірвати лінію при пропусках
            gaps = tdf['x_pos'].diff() > 1.5
            if gaps.any():
                insertions = []
                for idx, row in tdf[gaps].iterrows():
                    nan_row = row.copy()
                    nan_row[y_col] = np.nan
                    nan_row['x_pos'] = row['x_pos'] - 0.5
                    insertions.append(nan_row)
                if insertions:
                    tdf = pd.concat([tdf, pd.DataFrame(insertions)]).sort_values('x_pos')
            
            color = team_colors.get(t_name, '#888888')
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
                hovertemplate=f"<b>{t_code}</b> (%{{customdata[0]}})<br>Rating: %{{y:.3f}}<extra>%{{customdata[2]}}</extra>",
                showlegend=False
            ))
            
            # Додаємо назву команди (код) в кінці кожного відрізка
            for _, ep in endpoints.iterrows():
                fig.add_annotation(
                    x=ep['x_pos'],
                    y=ep[y_col],
                    text=t_code,
                    showarrow=False,
                    font=dict(color=color, size=11, family="Arial, sans-serif"),
                    xanchor='left',
                    xshift=5
                )

        # Вертикальні лінії для початку та кінця сезонів
        for sb in season_start_boundaries:
            fig.add_vline(x=sb, line_dash="dash", line_color="rgba(150, 150, 150, 0.5)", line_width=1)
        if season_boundaries:
            fig.add_vline(x=season_boundaries[-1], line_dash="dash", line_color="rgba(150, 150, 150, 0.5)", line_width=1)

        yaxis_config = dict(title="Rating", nticks=20)
        if title == "Defense Rating":
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

    st.plotly_chart(create_chart(df_hist, 'total', "Overall Rating (Attack - Defense)"), width="stretch")
    st.plotly_chart(create_chart(df_hist, 'att', "Attack Rating"), width="stretch")
    st.plotly_chart(create_chart(df_hist, 'def', "Defense Rating"), width="stretch")

    js_hover_sorter = r"""
    <script>
    (function() {
        function sortHoverBoxes() {
            try {
                var doc = window.parent.document;
                var hoverlayers = doc.querySelectorAll('.hoverlayer');
                hoverlayers.forEach(function(hoverlayer) {
                    var groups = hoverlayer.querySelector('.groups');
                    if (!groups) return;
                    var traces = Array.from(groups.querySelectorAll('g.traces'));

                    var chartContainer = hoverlayer.closest('.js-plotly-plot');
                    var isDefense = false;
                    if (chartContainer) {
                        var tEl = chartContainer.querySelector('.gtitle');
                        if (tEl && tEl.textContent.includes('Defense Rating')) {
                            isDefense = true;
                        }
                    }

                    var activeItems = [];
                    var activeYs = [];

                    traces.forEach(function(t) {
                        var txt = t.innerText || t.textContent || '';
                        var mGw = txt.match(/GW\s*\d+/);
                        var mVal = txt.match(/Rating:\s*([0-9.-]+)/);
                        var tr = t.getAttribute('transform') || '';
                        var mY = tr.match(/translate\(([^,]+),\s*([0-9.-]+)\)/);
                        
                        if (mVal && mY) {
                            var yVal = parseFloat(mY[2]);
                            var rVal = parseFloat(mVal[1]);
                            if (yVal > 0 && !isNaN(rVal)) {
                                var gwStr = mGw ? mGw[0] : '';
                                activeItems.push({ node: t, val: rVal, xVal: mY[1], yVal: yVal, gwStr: gwStr });
                            }
                        }
                    });

                    // Filter out traces from adjacent season at season boundary
                    var gwCounts = {};
                    activeItems.forEach(function(item) {
                        if (item.gwStr) gwCounts[item.gwStr] = (gwCounts[item.gwStr] || 0) + 1;
                    });
                    var majorityGw = null;
                    var maxCount = 0;
                    for (var gw in gwCounts) {
                        if (gwCounts[gw] > maxCount) {
                            maxCount = gwCounts[gw];
                            majorityGw = gw;
                        }
                    }
                    if (majorityGw) {
                        activeItems = activeItems.filter(function(item) { return item.gwStr === majorityGw; });
                    }

                    // Hide non-matching traces from DOM
                    traces.forEach(function(t) {
                        var isKeeper = activeItems.some(function(item) { return item.node === t; });
                        if (!isKeeper) {
                            t.style.display = 'none';
                        } else {
                            t.style.display = '';
                        }
                    });

                    if (activeItems.length > 0 && activeItems[0].gwStr) {
                        var titleEl = hoverlayer.querySelector('text.legendtitletext');
                        if (titleEl) {
                            titleEl.innerHTML = '<tspan style="font-weight:bold">' + activeItems[0].gwStr + '</tspan>';
                        }
                    }

                    if (activeItems.length > 1) {
                        var activeYs = activeItems.map(function(item) { return item.yVal; }).sort(function(a, b) { return a - b; });

                        activeItems.sort(function(a, b) {
                            return isDefense ? (a.val - b.val) : (b.val - a.val);
                        });

                        activeItems.forEach(function(item, idx) {
                            var newTr = 'translate(' + item.xVal + ',' + activeYs[idx] + ')';
                            item.node.setAttribute('transform', newTr);
                            groups.appendChild(item.node);
                        });
                    }
                });
            } catch(e) {}
        }
        setInterval(sortHoverBoxes, 50);
    })();
    </script>
    """
    st.components.v1.html(js_hover_sorter, height=0, scrolling=False)
else:
    st.info("No historical data available for selected filters.")
