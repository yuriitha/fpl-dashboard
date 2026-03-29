import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(
    page_title="FPL Players",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========================== ЗАВАНТАЖЕННЯ ДАНИХ ==========================
@st.cache_data(ttl=300)
def load_data():
    url = "http://194.99.22.193:8000/fpl_players"
    return pd.read_parquet(url)

df = load_data()

# ========================== РОЗРАХУНОК ВІКУ ==========================
def calculate_age(birth_date):
    if pd.isna(birth_date):
        return None
    try:
        birth = pd.to_datetime(birth_date)
        today = datetime.today()
        age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
        return age
    except:
        return None

if 'birth_date' in df.columns:
    df['Age'] = df['birth_date'].apply(calculate_age)
    df = df.drop(columns=['birth_date'])

# ========================== ПОРЯДОК КОЛОНОК ==========================
desired_order = [
    "id", "full_name", "Age", "element_type", "Play Pos", "team_short_name",
    "now_cost", "points_per_game",
    "top_10k", "top_100k", "transfers_in_event", "transfers_out_event",
    "min_played", "matches_played", "matches_started", "avg_mins", 
    "60_min", "returns", "av_rating", "av_rating_alt",
    "news", "news_added"
]

desired_order = [col for col in desired_order if col in df.columns]
df = df[desired_order]

# Сортування за замовчуванням
if 'av_rating_alt' in df.columns:
    df = df.sort_values(by="av_rating_alt", ascending=False).reset_index(drop=True)

# ========================== УМОВНЕ ФОРМАТУВАННЯ ==========================
def conditional_formatting(df):
    """Повертає Styler з гарним форматуванням"""
    styled = df.style

    # Градієнт для Avg Rating Alt (найважливіша колонка)
    if 'av_rating_alt' in df.columns:
        styled = styled.background_gradient(
            cmap='RdYlGn', 
            subset=['av_rating_alt'],
            vmin=5.0,
            vmax=8.0
        ).applymap(
            lambda x: 'font-weight: bold; color: darkgreen' if x >= 7.5 else '',
            subset=['av_rating_alt']
        )

    # Градієнт для Avg Rating
    if 'av_rating' in df.columns:
        styled = styled.background_gradient(
            cmap='RdYlGn', 
            subset=['av_rating'],
            vmin=5.0,
            vmax=8.0
        )

    # Градієнт для Avg Mins
    if 'avg_mins' in df.columns:
        styled = styled.background_gradient(
            cmap='RdYlGn', 
            subset=['avg_mins'],
            vmin=30,
            vmax=90
        )

    # Градієнт для 60+ Min %
    if '60_min' in df.columns:
        styled = styled.background_gradient(
            cmap='RdYlGn', 
            subset=['60_min'],
            vmin=0,
            vmax=100
        )

    # Градієнт для Returns %
    if 'returns' in df.columns:
        styled = styled.background_gradient(
            cmap='RdYlGn', 
            subset=['returns'],
            vmin=0,
            vmax=30
        )

    # Форматування чисел
    styled = styled.format({
        "avg_mins": "{:.1f}",
        "60_min": "{:.1f}",
        "returns": "{:.1f}",
        "av_rating": "{:.2f}",
        "av_rating_alt": "{:.2f}",
        "now_cost": "{:.1f}",
        "points_per_game": "{:.1f}",
    })

    return styled

# ========================== ФІЛЬТРИ (без змін) ==========================
st.sidebar.header("Filters")

positions = sorted(df['element_type'].unique())
selected_positions = st.sidebar.multiselect("Position", options=positions, default=positions)

teams = sorted(df['team_short_name'].unique())
selected_teams = st.sidebar.multiselect("Team", options=teams, default=teams)

min_cost = float(df['now_cost'].min())
max_cost = float(df['now_cost'].max())
cost_range = st.sidebar.slider("Price (£m)", min_value=min_cost, max_value=max_cost, value=(min_cost, max_cost), step=0.1)

min_ownership = float(df['top_100k'].min())
max_ownership = float(df['top_100k'].max())
ownership_range = st.sidebar.slider(
    "Top 100k Ownership %", 
    min_value=min_ownership, 
    max_value=max_ownership, 
    value=(min_ownership, max_ownership), 
    step=0.5
)

st.sidebar.subheader("Performance Filters")

if 'matches_played' in df.columns:
    min_matches = int(df['matches_played'].min())
    max_matches = int(df['matches_played'].max())
    matches_range = st.sidebar.slider("Matches Played", min_value=min_matches, max_value=max_matches, value=(7, max_matches))

if 'avg_mins' in df.columns:
    min_avg = float(df['avg_mins'].min())
    max_avg = float(df['avg_mins'].max())
    avg_mins_range = st.sidebar.slider("Avg Minutes", min_value=min_avg, max_avg=max_avg, value=(min_avg, max_avg), step=1.0)

if '60_min' in df.columns:
    min_60 = float(df['60_min'].min())
    max_60 = float(df['60_min'].max())
    sixty_range = st.sidebar.slider("60+ Min %", min_value=min_60, max_value=max_60, value=(min_60, max_60), step=0.5)

if 'returns' in df.columns:
    min_ret = float(df['returns'].min())
    max_ret = float(df['returns'].max())
    returns_range = st.sidebar.slider("Returns %", min_value=min_ret, max_value=max_ret, value=(min_ret, max_ret), step=0.1)

# ========================== ЗАСТОСУВАННЯ ФІЛЬТРІВ ==========================
filtered_df = df.copy()

if selected_positions:
    filtered_df = filtered_df[filtered_df['element_type'].isin(selected_positions)]
if selected_teams:
    filtered_df = filtered_df[filtered_df['team_short_name'].isin(selected_teams)]
if cost_range:
    filtered_df = filtered_df[(filtered_df['now_cost'] >= cost_range[0]) & (filtered_df['now_cost'] <= cost_range[1])]
if ownership_range:
    filtered_df = filtered_df[(filtered_df['top_100k'] >= ownership_range[0]) & (filtered_df['top_100k'] <= ownership_range[1])]

if 'matches_played' in df.columns:
    filtered_df = filtered_df[(filtered_df['matches_played'] >= matches_range[0]) & (filtered_df['matches_played'] <= matches_range[1])]
if 'avg_mins' in df.columns:
    filtered_df = filtered_df[(filtered_df['avg_mins'] >= avg_mins_range[0]) & (filtered_df['avg_mins'] <= avg_mins_range[1])]
if '60_min' in df.columns:
    filtered_df = filtered_df[(filtered_df['60_min'] >= sixty_range[0]) & (filtered_df['60_min'] <= sixty_range[1])]
if 'returns' in df.columns:
    filtered_df = filtered_df[(filtered_df['returns'] >= returns_range[0]) & (filtered_df['returns'] <= returns_range[1])]

# ========================== ТАБЛИЦЯ З ФОРМАТУВАННЯМ ==========================
st.subheader(f"Знайдено гравців: {len(filtered_df)}")

# Застосовуємо стилізацію
styled_df = conditional_formatting(filtered_df)

st.dataframe(
    styled_df,
    use_container_width=True,
    hide_index=True,
    height=720,
    column_config={
        "id": st.column_config.NumberColumn("ID", disabled=True, width=5),
        "full_name": st.column_config.TextColumn("Player", width="medium"),
        "Age": st.column_config.NumberColumn("Age", width=5),
        "element_type": st.column_config.TextColumn("Pos", width=5),
        "Play Pos": st.column_config.TextColumn("Play Pos", width=5),
        "team_short_name": st.column_config.TextColumn("Team", width=5),
        "now_cost": st.column_config.NumberColumn("Price", format="%.1f", width=5),
        "points_per_game": st.column_config.NumberColumn("Pts/Game", format="%.1f", width=5),
        "top_10k": st.column_config.NumberColumn("Top 10k %", format="%.1f", width=5),
        "top_100k": st.column_config.NumberColumn("Top 100k %", format="%.1f", width=5),
        "transfers_in_event": st.column_config.NumberColumn("In", width=5),
        "transfers_out_event": st.column_config.NumberColumn("Out", width=5),
        "min_played": st.column_config.NumberColumn("Min Played", width=5),
        "matches_played": st.column_config.NumberColumn("Matches", width=5),
        "matches_started": st.column_config.NumberColumn("Started", width=5),
        "avg_mins": st.column_config.NumberColumn("Avg Mins", format="%.1f", width=5),
        "60_min": st.column_config.NumberColumn("60+ Min %", format="%.1f", width=5),
        "returns": st.column_config.NumberColumn("Returns %", format="%.1f", width=5),
        "av_rating": st.column_config.NumberColumn("Avg Rating", format="%.2f", width=5),
        "av_rating_alt": st.column_config.NumberColumn("Avg Rating Alt", format="%.2f", width=5),
        "news": st.column_config.TextColumn("News", width="auto"),
        "news_added": st.column_config.TextColumn("Updated", width="auto"),
    }
)

st.caption(f"Останнє оновлення: {pd.Timestamp.now('Europe/Kiev').strftime('%Y-%m-%d %H:%M')}")