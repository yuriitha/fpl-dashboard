import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="xGI vs Rating", layout="wide")

st.title("📈 xGI_norm vs Avg Rating Alt")

# ========================== ЗАВАНТАЖЕННЯ ДАНИХ ==========================
@st.cache_data(ttl=300)
def load_data():
    url = "http://194.99.22.193:8000/fpl_players"
    return pd.read_parquet(url)

df = load_data()

# ========================== ФІЛЬТРИ ==========================
st.sidebar.header("Фільтри графіка")

positions = sorted(df['element_type'].unique())
selected_pos = st.sidebar.multiselect("Позиція", options=positions, default=positions)

teams = sorted(df['team_short_name'].unique())
selected_teams = st.sidebar.multiselect("Команда", options=teams, default=teams)

min_cost = float(df['now_cost'].min())
max_cost = float(df['now_cost'].max())
cost_range = st.sidebar.slider("Ціна (£m)", 
                               min_value=min_cost, 
                               max_value=max_cost, 
                               value=(min_cost, max_cost), 
                               step=0.1)

st.sidebar.subheader("Додаткові фільтри")

if 'av_rating_alt' in df.columns:
    min_rating = float(df['av_rating_alt'].min())
    max_rating = float(df['av_rating_alt'].max())
    rating_range = st.sidebar.slider("Avg Rating Alt", 
                                     min_value=min_rating, 
                                     max_value=max_rating, 
                                     value=(min_rating, max_rating), 
                                     step=0.1)

if 'xGI_norm' in df.columns:
    min_xgi = float(df['xGI_norm'].min())
    max_xgi = float(df['xGI_norm'].max())
    xgi_range = st.sidebar.slider("xGI_norm", 
                                  min_value=min_xgi, 
                                  max_value=max_xgi, 
                                  value=(min_xgi, max_xgi), 
                                  step=0.05)

if 'matches_played' in df.columns:
    min_matches = int(df['matches_played'].min())
    max_matches = int(df['matches_played'].max())
    matches_range = st.sidebar.slider("Matches Played", 
                                      min_value=min_matches, 
                                      max_value=max_matches, 
                                      value=(7, max_matches), 
                                      step=1)

if '60_min' in df.columns:
    min_60 = float(df['60_min'].min())
    max_60 = float(df['60_min'].max())
    sixty_range = st.sidebar.slider("60+ Min %", 
                                    min_value=min_60, 
                                    max_value=max_60, 
                                    value=(30.0, max_60), 
                                    step=1.0)

# ========================== ЗАСТОСУВАННЯ ФІЛЬТРІВ ==========================
plot_df = df.copy()

if selected_pos:
    plot_df = plot_df[plot_df['element_type'].isin(selected_pos)]
if selected_teams:
    plot_df = plot_df[plot_df['team_short_name'].isin(selected_teams)]
if cost_range:
    plot_df = plot_df[(plot_df['now_cost'] >= cost_range[0]) & (plot_df['now_cost'] <= cost_range[1])]

if 'av_rating_alt' in df.columns:
    plot_df = plot_df[(plot_df['av_rating_alt'] >= rating_range[0]) & 
                      (plot_df['av_rating_alt'] <= rating_range[1])]

if 'xGI_norm' in df.columns:
    plot_df = plot_df[(plot_df['xGI_norm'] >= xgi_range[0]) & 
                      (plot_df['xGI_norm'] <= xgi_range[1])]

if 'matches_played' in df.columns:
    plot_df = plot_df[(plot_df['matches_played'] >= matches_range[0]) & 
                      (plot_df['matches_played'] <= matches_range[1])]

if '60_min' in df.columns:
    plot_df = plot_df[(plot_df['60_min'] >= sixty_range[0]) & 
                      (plot_df['60_min'] <= sixty_range[1])]

# ========================== ГРАФІК ==========================
if not plot_df.empty:
    plot_df = plot_df.copy()
    
    # === КРАЩЕ МАСШТАБУВАННЯ РОЗМІРУ КРУЖЕЧКІВ ===
    # М’якше притискання малих значень + clip для уникнення нуля
    plot_df['size_for_plot'] = np.power(plot_df['avg_mins'].clip(lower=0.1), 0.55)
    
    # Поріг для відображення підпису web_name
    min_mins_for_label = 48
    plot_df['label_text'] = np.where(
        plot_df['avg_mins'] >= min_mins_for_label,
        plot_df['web_name'],
        ""
    )

    # Визначаємо колір тексту залежно від теми Streamlit
    theme_base = st.get_option("theme.base")  # 'light' або 'dark'
    text_color = "white" if theme_base == "dark" else "black"

    # Створюємо графік
    fig = px.scatter(
        plot_df,
        x="av_rating_alt",
        y="xGI_norm",
        color="element_type",
        size="size_for_plot",
        hover_name="full_name",
        hover_data=["web_name", "team_short_name", "G_90", "xG_90", "xGI_90", 
                    "matches_played", "60_min", "avg_mins"],
        text="label_text",
        title="xGI_norm vs Avg Rating Alt",
        labels={
            "av_rating_alt": "Average Rating",
            "xGI_norm": "xGI_norm",
            "element_type": "Pos"
        },
        template="plotly_white" if theme_base == "light" else "plotly_dark"
    )

    fig = go.Figure(fig)

    max_size_value = plot_df['size_for_plot'].max() 

    # Налаштування маркерів і тексту
    max_size = plot_df['size_for_plot'].max()

    fig.update_traces(
        mode='markers+text',
        textposition='top center',
        textfont=dict(size=10, color=text_color),   # ← динамічний колір
        marker=dict(
            opacity=0.82,
            line=dict(width=0.6, color='DarkSlateGrey')
        ),
        # Правильне масштабування розміру
        marker_sizeref = max_size_value / 28,
        marker_sizemin = 3.5
    )

    fig.update_layout(
        height=720,
        legend_title="Позиція"
    )

    st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("Немає даних, що відповідають обраним фільтрам.")

# ========================== ТАБЛИЦЯ ==========================
st.subheader("Дані гравців")
st.dataframe(
    plot_df[["web_name", "full_name", "team_short_name", "element_type", "now_cost", 
             "av_rating_alt", "xGI_norm", "xGI_90", "avg_mins", "G_90"]].round(2),
    use_container_width=True,
    hide_index=True
)

st.caption(f"Останнє оновлення: {pd.Timestamp.now('Europe/Kiev').strftime('%Y-%m-%d %H:%M')}")