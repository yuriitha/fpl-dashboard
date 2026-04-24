import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import json

st.set_page_config(
    page_title="Team Strength",
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
    # Завантаження даних аналогічно FPL_Main_Info.py
    url = "http://194.99.22.193:8000/team_strength_model" 
    
    try:
        df = pd.read_parquet(url)
    except Exception as e:
        # Fallback на локальний файл (з абсолютним шляхом), якщо ендпоінт ще не створений або недоступний
        import os
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        file_path = os.path.join(base_path, "team_strength_model_v2.parquet")
        df = pd.read_parquet(file_path)
        
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"Помилка завантаження: {e}")
    st.stop()

# Get teams and colors
team_colors = {}
for _, row in df[['home_team', 'home_color']].dropna().drop_duplicates().iterrows():
    if row['home_team'] not in team_colors: team_colors[row['home_team']] = row['home_color']
for _, row in df[['away_team', 'away_color']].dropna().drop_duplicates().iterrows():
    if row['away_team'] not in team_colors: team_colors[row['away_team']] = row['away_color']

all_teams = sorted(list(set(df['home_team'].dropna()).union(set(df['away_team'].dropna()))))
all_seasons = sorted([s for s in df['season'].dropna().unique() if s != "2013/14"])

# Session state
if 'ts_pills_teams' not in st.session_state: st.session_state.ts_pills_teams = all_teams

# Sidebar
if st.sidebar.button("Reset All Filters", use_container_width=True, type="primary"):
    keys_to_delete = [k for k in st.session_state.keys() if k.startswith('ts_')]
    for key in keys_to_delete:
        del st.session_state[key]
    st.rerun()

search_name = st.sidebar.text_input("Search Team", placeholder="Enter team name...", key="ts_search_name")

# Seasons Filter
season_range = st.sidebar.select_slider(
    "Seasons",
    options=all_seasons,
    value=(all_seasons[0], all_seasons[-1]),
    key="ts_seasons"
)

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
    final_teams = [t for t in final_teams if search_name.lower() in t.lower()]

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
}})();
</script>
"""
st.components.v1.html(js, height=0, scrolling=False)

# === MAIN CONTENT ===
col1, col2 = st.columns([1, 1])

# Current Ratings Table
with col1:
    st.subheader("Current Team Ratings")
    df_played = df.dropna(subset=['match_result'])
    latest_home = df_played.sort_values('match_date').groupby('home_team').last()[['match_date', 'home_rating_att_post', 'home_rating_def_post']]
    latest_away = df_played.sort_values('match_date').groupby('away_team').last()[['match_date', 'away_rating_att_post', 'away_rating_def_post']]
    
    current_ratings = []
    for t in all_teams:
        if final_teams and t not in final_teams: continue
        h = latest_home.loc[t] if t in latest_home.index else None
        a = latest_away.loc[t] if t in latest_away.index else None
        
        att, def_rating = None, None
        if h is not None and a is not None:
            if h['match_date'] > a['match_date']:
                att, def_rating = h['home_rating_att_post'], h['home_rating_def_post']
            else:
                att, def_rating = a['away_rating_att_post'], a['away_rating_def_post']
        elif h is not None:
            att, def_rating = h['home_rating_att_post'], h['home_rating_def_post']
        elif a is not None:
            att, def_rating = a['away_rating_att_post'], a['away_rating_def_post']
            
        if att is not None and def_rating is not None:
            current_ratings.append({
                'Team': t,
                'Attack Rating': att,
                'Defense Rating': def_rating,
                'Overall Rating': att - def_rating
            })
            
    if current_ratings:
        df_ratings = pd.DataFrame(current_ratings).sort_values('Overall Rating', ascending=False)
        st.dataframe(
            df_ratings,
            hide_index=True,
            use_container_width=True,
            height=400,
            column_config={
                'Team': st.column_config.TextColumn("Team"),
                'Attack Rating': st.column_config.NumberColumn("Attack Rating", format="%.3f"),
                'Defense Rating': st.column_config.NumberColumn("Defense Rating", format="%.3f"),
                'Overall Rating': st.column_config.NumberColumn("Overall Rating", format="%.3f"),
            }
        )
    else:
        st.info("No teams selected.")

# Upcoming Matches Table
with col2:
    st.subheader("Upcoming Matches")
    df_future = df[df['match_result'].isna()].copy()
    if not df_future.empty:
        cols = ['match_date', 'home_team', 'away_team', 'home_xg', 'away_xg', 'home_xg_odds', 'away_xg_odds', 'home_delta', 'away_delta']
        df_future = df_future[cols].sort_values('match_date')
        
        if final_teams:
            df_future = df_future[df_future['home_team'].isin(final_teams) | df_future['away_team'].isin(final_teams)]
            
        st.dataframe(
            df_future,
            hide_index=True,
            use_container_width=True,
            height=400,
            column_config={
                'match_date': st.column_config.DatetimeColumn("Date", format="DD/MM/YYYY HH:mm"),
                'home_team': st.column_config.TextColumn("Home"),
                'away_team': st.column_config.TextColumn("Away"),
                'home_xg': st.column_config.NumberColumn("xG (H)", format="%.2f"),
                'away_xg': st.column_config.NumberColumn("xG (A)", format="%.2f"),
                'home_xg_odds': st.column_config.NumberColumn("Odds xG (H)", format="%.2f"),
                'away_xg_odds': st.column_config.NumberColumn("Odds xG (A)", format="%.2f"),
                'home_delta': st.column_config.NumberColumn("Delta (H)", format="%.2f"),
                'away_delta': st.column_config.NumberColumn("Delta (A)", format="%.2f"),
            }
        )
    else:
        st.info("No upcoming matches found.")

# Charts
st.subheader("Historical Ratings")

# Prepare historical data
hist_home = df_played[['match_date', 'season', 'home_team', 'home_rating_att_post', 'home_rating_def_post', 'home_color']].rename(
    columns={'match_date':'date', 'season':'season', 'home_team':'team', 'home_rating_att_post':'att', 'home_rating_def_post':'def', 'home_color':'color'}
)
hist_away = df_played[['match_date', 'season', 'away_team', 'away_rating_att_post', 'away_rating_def_post', 'away_color']].rename(
    columns={'match_date':'date', 'season':'season', 'away_team':'team', 'away_rating_att_post':'att', 'away_rating_def_post':'def', 'away_color':'color'}
)

df_hist = pd.concat([hist_home, hist_away]).sort_values('date')
df_hist = df_hist[df_hist['season'] != "2013/14"] # Exclude first season

if season_range:
    s_start, s_end = season_range
    df_hist = df_hist[(df_hist['season'] >= s_start) & (df_hist['season'] <= s_end)]

if final_teams:
    df_hist = df_hist[df_hist['team'].isin(final_teams)]

if not df_hist.empty:
    df_hist['total'] = df_hist['att'] - df_hist['def']

    def create_chart(df, y_col, title):
        fig = go.Figure()
        for t in df['team'].unique():
            tdf = df[df['team'] == t]
            color = team_colors.get(t, '#888888')
            fig.add_trace(go.Scatter(
                x=tdf['date'], y=tdf[y_col],
                mode='lines',
                name=t,
                line=dict(color=color, width=2),
                hovertemplate=f"<b>{t}</b><br>Date: %{{x}}<br>Rating: %{{y:.3f}}<extra></extra>"
            ))
        fig.update_layout(
            title=title,
            xaxis_title="Date",
            yaxis_title="Rating",
            height=500,
            hovermode="x unified",
            margin=dict(l=20, r=20, t=40, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        return fig

    st.plotly_chart(create_chart(df_hist, 'total', "Overall Rating (Attack - Defense)"), use_container_width=True)
    st.plotly_chart(create_chart(df_hist, 'att', "Attack Rating"), use_container_width=True)
    st.plotly_chart(create_chart(df_hist, 'def', "Defense Rating"), use_container_width=True)
else:
    st.info("No historical data available for selected filters.")
