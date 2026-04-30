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

# CSS для відцентрування заголовків та даних і стилізації сайдбару
st.markdown("""
    <style>
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
if st.sidebar.button("Reset All Filters", use_container_width=True, type="primary"):
    keys_to_delete = [k for k in st.session_state.keys() if k.startswith('ts_')]
    for key in keys_to_delete:
        del st.session_state[key]
    st.rerun()

# Seasons Filter
season_range = st.sidebar.select_slider(
    "Seasons",
    options=all_seasons,
    value=(all_seasons[-1], all_seasons[-1]),
    key="ts_seasons"
)

s_start, s_end = season_range
ch_df = df[(df['league'] == 'Championship') & (df['season'] >= s_start) & (df['season'] <= s_end)]
all_teams = sorted(list(set(ch_df['home_team_code'].dropna()).union(set(ch_df['away_team_code'].dropna()))))

# Session state
if 'ts_pills_teams' not in st.session_state: 
    st.session_state.ts_pills_teams = all_teams
else:
    st.session_state.ts_pills_teams = [t for t in st.session_state.ts_pills_teams if t in all_teams]

search_name = st.sidebar.text_input("Search Team", placeholder="Enter team name...", key="ts_search_name")

# Filter Header Helper
def filter_header(label, options, key_prefix):
    cols = st.sidebar.columns([1.4, 0.8, 0.8])
    cols[0].markdown(f"<p style='font-size:0.875rem;margin-bottom:0'>{label}</p>", unsafe_allow_html=True)
    if cols[1].button("All", key=f"btn_all_{key_prefix}", use_container_width=True):
        st.session_state[f"ts_{key_prefix}"] = options
        st.rerun()
    if cols[2].button("None", key=f"btn_none_{key_prefix}", use_container_width=True):
        st.session_state[f"ts_{key_prefix}"] = []
        st.rerun()

filter_header("Teams", all_teams, "pills_teams")
selected_teams = st.sidebar.pills(
    "Teams", options=all_teams, key="ts_pills_teams",
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

def soft_gradient(s, cmap_name='Blues', alpha=0.5, fixed_min=None, fixed_max=None, transparent_at='min'):
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

light_blues = mcolors.LinearSegmentedColormap.from_list("LightBlues", ["#ffffff", "#00BFFF"])
orange_blue = mcolors.LinearSegmentedColormap.from_list("OrangeBlue", ["#ff8c00", "#ffffff", "#00BFFF"])

# === MAIN CONTENT ===
col1, col2 = st.columns([0.35, 0.65])

# Current Ratings Table
with col1:
    st.subheader("Current Team Ratings")
    
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
            .apply(soft_gradient, cmap_name='YlGn', alpha=0.6, transparent_at='min', subset=['Attack']) \
            .apply(soft_gradient, cmap_name='YlGn_r', alpha=0.6, transparent_at='max', subset=['Defense']) \
            .apply(soft_gradient, cmap_name='RdYlGn', alpha=0.6, transparent_at='mid', subset=['Overall']) \
            .format(precision=3)
        
        st.dataframe(
            df_ratings_styled,
            hide_index=True,
            use_container_width=True,
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
    st.subheader("Upcoming Matches")
    df_future = df[(df['match_result'].isna()) & (df['league'] == 'Championship')].copy()
    if not df_future.empty:
        cols = ['match_date', 'home_team', 'away_team', 'home_team_code', 'away_team_code', 'home_xg', 'away_xg', 'home_xg_odds', 'away_xg_odds', 'home_delta', 'away_delta']
        df_future = df_future[cols].sort_values('match_date')
        
        df_future = df_future.drop(columns=['home_team_code', 'away_team_code'])
            
        xg_cols = ['home_xg', 'away_xg', 'home_xg_odds', 'away_xg_odds']
        xg_min = df_future[xg_cols].min().min()
        xg_max = df_future[xg_cols].max().max()

        df_future_styled = df_future.style \
            .apply(soft_gradient, cmap_name=light_blues, alpha=0.6, fixed_min=xg_min, fixed_max=xg_max, transparent_at='min', subset=xg_cols) \
            .apply(soft_gradient, cmap_name=orange_blue, alpha=0.6, fixed_min=-0.45, fixed_max=0.45, transparent_at='mid', subset=['home_delta', 'away_delta']) \
            .format(precision=2)
            
        st.dataframe(
            df_future_styled,
            hide_index=True,
            use_container_width=True,
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
st.subheader("Historical Ratings")

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

    def create_chart(df, y_col, title):
        fig = go.Figure()
        for t_name in df['team_name'].unique():
            tdf = df[df['team_name'] == t_name].sort_values('date').copy()
            tdf_clean = tdf.dropna(subset=[y_col])
            
            # Знаходимо кінці відрізків для підписів
            if not tdf_clean.empty:
                next_date = tdf_clean['date'].shift(-1)
                is_end = (next_date - tdf_clean['date'] > pd.Timedelta(days=30)) | next_date.isna()
                endpoints = tdf_clean[is_end]
            else:
                endpoints = pd.DataFrame()
            
            # Вставляємо NaN для проміжків > 30 днів, щоб розірвати лінію
            gaps = tdf['date'].diff() > pd.Timedelta(days=30)
            if gaps.any():
                insertions = []
                for idx, row in tdf[gaps].iterrows():
                    nan_row = row.copy()
                    nan_row[y_col] = np.nan
                    nan_row['date'] = row['date'] - pd.Timedelta(hours=1)
                    insertions.append(nan_row)
                if insertions:
                    tdf = pd.concat([tdf, pd.DataFrame(insertions)]).sort_values('date')
            
            color = team_colors.get(t_name, '#888888')
            t_code = tdf['team_code'].dropna().iloc[0] if not tdf['team_code'].dropna().empty else t_name
            
            fig.add_trace(go.Scatter(
                x=tdf['date'], y=tdf[y_col],
                mode='lines',
                name=t_code,
                line=dict(color=color, width=2),
                hovertemplate=f"<b>{t_code}</b> ({t_name})<br>Date: %{{x}}<br>Rating: %{{y:.3f}}<extra></extra>",
                showlegend=False
            ))
            
            # Додаємо назву команди (код) в кінці кожного відрізка
            for _, ep in endpoints.iterrows():
                fig.add_annotation(
                    x=ep['date'],
                    y=ep[y_col],
                    text=t_code,
                    showarrow=False,
                    font=dict(color=color, size=11, family="Arial, sans-serif"),
                    xanchor='left',
                    xshift=5
                )

        yaxis_config = dict(title="Rating", nticks=20)
        if title == "Defense Rating":
            yaxis_config['autorange'] = "reversed"

        fig.update_layout(
            title=title,
            xaxis_title="Date",
            yaxis=yaxis_config,
            height=800,
            hovermode="x unified",
            margin=dict(l=20, r=80, t=40, b=20),
            showlegend=False
        )
        return fig

    st.plotly_chart(create_chart(df_hist, 'total', "Overall Rating (Attack - Defense)"), use_container_width=True)
    st.plotly_chart(create_chart(df_hist, 'att', "Attack Rating"), use_container_width=True)
    st.plotly_chart(create_chart(df_hist, 'def', "Defense Rating"), use_container_width=True)
else:
    st.info("No historical data available for selected filters.")
