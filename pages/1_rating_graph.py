import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import plotly.graph_objects as go

# Налаштування сторінки
st.set_page_config(
    page_title="FPL Rating Graph",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========================== ЗАВАНТАЖЕННЯ ДАНИХ ==========================
@st.cache_data(ttl=300)
def load_data():
    url = "http://194.99.22.193:8000/fpl_players"
    df = pd.read_parquet(url)
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"Помилка завантаження: {e}")
    st.stop()

# ========================== ФІЛЬТРИ В САЙДБАРІ ==========================
st.sidebar.header("Graph Filters")

positions = sorted(df['element_type'].unique())
selected_pos = st.sidebar.multiselect("Pos", options=positions, default=positions)

teams = sorted(df['team_short_name'].unique())
selected_teams = st.sidebar.multiselect("Team", options=teams, default=teams)

c_min, c_max = float(df['now_cost'].min()), float(df['now_cost'].max())
f_cost = st.sidebar.slider("FPL Price", c_min, c_max, (c_min, c_max), 0.1)

m_min, m_max = int(df['matches_played'].min()), int(df['matches_played'].max())
f_matches = st.sidebar.slider("Matches", m_min, m_max, (5, m_max))

s_min, s_max = float(df['selected_by_percent'].min()), float(df['selected_by_percent'].max())
f_selected = st.sidebar.slider("Selected %", s_min, s_max, (s_min, s_max), 0.1)

o_min, o_max = float(df['top_100k'].min()), float(df['top_100k'].max())
f_top100k = st.sidebar.slider("Top 100k %", o_min, o_max, (o_min, o_max), 0.1)

am_min, am_max = float(df['avg_mins'].min()), float(df['avg_mins'].max())
f_avg_mins = st.sidebar.slider("Average Mins", am_min, am_max, (am_min, am_max), 1.0)

min_60 = float(df['60_min'].min())
max_60 = float(df['60_min'].max())
f_60min = st.sidebar.slider("60 Min %", min_60, max_60, (37.0, max_60), 0.5)

r_min, r_max = float(df['av_rating_alt'].min()), float(df['av_rating_alt'].max())
f_rating = st.sidebar.slider("Rating", r_min, r_max, (r_min, r_max), 0.1)

xgi_min, xgi_max = float(df['xGI_norm'].min()), float(df['xGI_norm'].max())
f_xgi = st.sidebar.slider("xGI", xgi_min, xgi_max, (xgi_min, xgi_max), 0.05)

# ========================== ПІДГОТОВКА ДАНИХ ==========================
mask = (
    df['element_type'].isin(selected_pos) &
    df['team_short_name'].isin(selected_teams) &
    (df['now_cost'] >= f_cost[0]) & (df['now_cost'] <= f_cost[1]) &
    (df['matches_played'] >= f_matches[0]) & (df['matches_played'] <= f_matches[1]) &
    (df['60_min'] >= f_60min[0]) & (df['60_min'] <= f_60min[1]) &
    (df['av_rating_alt'] >= f_rating[0]) & (df['av_rating_alt'] <= f_rating[1]) &
    (df['xGI_norm'] >= f_xgi[0]) & (df['xGI_norm'] <= f_xgi[1])
)
plot_df = df[mask].copy()

# ========================== ЛОГІКА РОЗМІРУ (ПРОЦЕНТИЛІ) ==========================
if not plot_df.empty:
    plot_df['p_top100k'] = plot_df['top_100k'].rank(pct=True)
    plot_df['p_avgmins'] = plot_df['avg_mins'].rank(pct=True)
    
    plot_df['combined_rank'] = (plot_df['p_top100k'] + plot_df['p_avgmins']) / 2
    plot_df['size_for_plot'] = plot_df['combined_rank'] * 20 + 5 

    min_mins_for_label = 60
    plot_df['label_text'] = np.where(
        (plot_df['avg_mins'] >= min_mins_for_label) | (plot_df['combined_rank'] > 0.85),
        plot_df['web_name'],
        ""
    )

    # ========================== ВІЗУАЛІЗАЦІЯ ==========================
    st.subheader(f"xGI vs Rating (Players: {len(plot_df)})")

    fig = px.scatter(
        plot_df,
        x="av_rating_alt",
        y="xGI_norm",
        color="element_type",
        size="size_for_plot",
        hover_name="full_name",
        hover_data={
            "web_name": True,
            "team_short_name": True,
            "top_100k": ":.1f",
            "avg_mins": ":.0f",
            "matches_played": True,
            "size_for_plot": False,
            "combined_rank": False
        },
        text="label_text",
        labels={
            "av_rating_alt": "Average Rating",
            "xGI_norm": "Expected Goal Involvement",
            "element_type": ""  # Прибираємо текст в легенді
        },
        template="plotly_dark",
        size_max=25
    )

    fig.update_traces(
        textposition='bottom center',
        marker=dict(
            opacity=0.75,
            line=dict(width=0.8, color='white')
        )
    )

    fig.update_layout(
        height=800,
        margin=dict(l=0, r=0, t=40, b=0),
        xaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
        legend_title_text='', # Додатково гарантуємо порожній заголовок легенди
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(0,0,0,0.5)"
        )
    )

    st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("Немає даних для обраних фільтрів.")