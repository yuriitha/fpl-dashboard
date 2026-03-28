import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(
    page_title="FPL Players",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========================== ЗАВАНТАЖЕННЯ ДАНИХ З API ==========================
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

# Якщо колонка 'birth_date' все ще є — використовуємо її, інакше Age вже має бути в parquet
if 'birth_date' in df.columns:
    df['Age'] = df['birth_date'].apply(calculate_age)
    df = df.drop(columns=['birth_date'])
else:
    # Якщо Age вже є в parquet — нічого не робимо
    pass

# ========================== ВСТАНОВЛЕННЯ ПОРЯДКУ КОЛОНОК ==========================
desired_order = [
    "id", "full_name", "Age", "element_type", "Play Pos", "team_short_name",
    "Foot", "now_cost", "M Price", "points_per_game", "selected_by_percent",
    "top_10k", "top_100k", "transfers_in_event", "transfers_out_event",
    "news", "news_added", "Contract"
]

desired_order = [col for col in desired_order if col in df.columns]
df = df[desired_order]

# ========================== ФІЛЬТРИ ==========================
st.sidebar.header("Filters")

positions = sorted(df['element_type'].unique())
selected_positions = st.sidebar.multiselect("Position", options=positions, default=positions)

teams = sorted(df['team_short_name'].unique())
selected_teams = st.sidebar.multiselect("Team", options=teams, default=teams)

min_cost = float(df['now_cost'].min())
max_cost = float(df['now_cost'].max())
cost_range = st.sidebar.slider("Price (£m)", min_value=min_cost, max_value=max_cost, value=(min_cost, max_cost), step=0.1)

search_name = st.sidebar.text_input("Search by name", "")

# ========================== ЗАСТОСУВАННЯ ФІЛЬТРІВ ==========================
filtered_df = df.copy()

if selected_positions:
    filtered_df = filtered_df[filtered_df['element_type'].isin(selected_positions)]

if selected_teams:
    filtered_df = filtered_df[filtered_df['team_short_name'].isin(selected_teams)]

if cost_range:
    filtered_df = filtered_df[
        (filtered_df['now_cost'] >= cost_range[0]) & 
        (filtered_df['now_cost'] <= cost_range[1])
    ]

if search_name:
    filtered_df = filtered_df[
        filtered_df['full_name'].str.contains(search_name, case=False, na=False)
    ]

# ========================== ТАБЛИЦЯ ==========================
st.subheader(f"Знайдено гравців: {len(filtered_df)}")

st.dataframe(
    filtered_df,
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
        "Foot": st.column_config.TextColumn("Foot", width=5),
        "now_cost": st.column_config.NumberColumn("Price", format="%.1f", width=5),
        "M Price": st.column_config.NumberColumn("M Price", format="%.1f", width=5),
        "points_per_game": st.column_config.NumberColumn("Pts/Game", format="%.1f", width=5),
        "selected_by_percent": st.column_config.NumberColumn("Selected %", format="%.1f", width=5),
        "top_10k": st.column_config.NumberColumn("Top 10k %", format="%.1f", width=5),
        "top_100k": st.column_config.NumberColumn("Top 100k %", format="%.1f", width=5),
        "transfers_in_event": st.column_config.NumberColumn("In", width=5),
        "transfers_out_event": st.column_config.NumberColumn("Out", width=5),
        "news": st.column_config.TextColumn("News", width="auto"),
        "news_added": st.column_config.TextColumn("Updated", width="auto"),
        "Contract": st.column_config.TextColumn("Contract", width="small"),
    }
)

st.caption(f"Останнє оновлення: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}")