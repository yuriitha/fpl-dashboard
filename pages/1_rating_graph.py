import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="xGI vs Rating", layout="wide")

# Завантаження даних
@st.cache_data(ttl=300)
def load_data():
    url = "http://194.99.22.193:8000/fpl_players"
    return pd.read_parquet(url)

df = load_data()

# Фільтри
st.sidebar.header("Фільтри графіка")

positions = sorted(df['element_type'].unique())
selected_pos = st.sidebar.multiselect("Позиція", options=positions, default=positions)

teams = sorted(df['team_short_name'].unique())
selected_teams = st.sidebar.multiselect("Команда", options=teams, default=teams)

min_cost, max_cost = float(df['now_cost'].min()), float(df['now_cost'].max())
cost_range = st.sidebar.slider("Ціна (?m)", min_value=min_cost, max_value=max_cost, 
                               value=(min_cost, max_cost), step=0.1)

# Застосування фільтрів
plot_df = df.copy()
if selected_pos:
    plot_df = plot_df[plot_df['element_type'].isin(selected_pos)]
if selected_teams:
    plot_df = plot_df[plot_df['team_short_name'].isin(selected_teams)]
plot_df = plot_df[(plot_df['now_cost'] >= cost_range[0]) & (plot_df['now_cost'] <= cost_range[1])]

# Графік
if not plot_df.empty:
    fig = px.scatter(
        plot_df,
        x="av_rating_alt",
        y="xGI_norm",
        color="element_type",
        size="now_cost",
        hover_name="full_name",
        hover_data=["team_short_name", "G_90", "xG_90", "xGI_90", "matches_played"],
        title="xGI_norm vs Avg Rating Alt",
        labels={
            "av_rating_alt": "Average Rating Alt (весь сезон)",
            "xGI_norm": "xGI_norm",
            "element_type": "Позиція"
        },
        template="plotly_white"
    )

    fig.update_traces(marker=dict(opacity=0.8, line=dict(width=0.5)))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Немає даних для відображення графіка")

# Таблиця
st.subheader("Дані гравців")
st.dataframe(
    plot_df[["full_name", "team_short_name", "element_type", "now_cost", 
             "av_rating_alt", "xGI_norm", "xGI_90", "G_90"]].round(2),
    use_container_width=True,
    hide_index=True
)

st.caption(f"Останнє оновлення: {pd.Timestamp.now('Europe/Kiev').strftime('%Y-%m-%d %H:%M')}")