import streamlit as st
import pandas as pd

# Налаштування сторінки
st.set_page_config(
    page_title="UCL Players Stats",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS для максимальної компактності та відцентрування
st.markdown("""
    <style>
        [data-testid="stTable"] th, [data-testid="stDataFrame"] th { text-align: center !important; }
        [data-testid="stDataFrame"] td { text-align: center !important; }
        
        [data-testid="stVerticalBlock"] {
            gap: 0.4rem !important;
        }

        [data-testid="stHorizontalBlock"] {
            gap: 0.1rem !important;
        }
    </style>
""", unsafe_allow_html=True)

# ========================== ЗАВАНТАЖЕННЯ ДАНИХ ==========================
@st.cache_data(ttl=300)
def load_data():
    url = "http://194.99.22.193:8000/ucl_players"
    df = pd.read_parquet(url)
    if 'Price' in df.columns:
        df = df.sort_values(by="Price", ascending=False)
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"Помилка завантаження: {e}")
    st.stop()

# ========================== ПІДГОТОВКА СПИСКУ КОЛОНОК ==========================
display_columns = [
    "Player", "Age", "Pos", "Pl Pos", "Team", "Team Name", "Price", "Foot", 
    "TM Value", "Selected", "Top 1K", "Top 5K", "Captain", "Mins", "G", "A", 
    "POTM", "PPM", "Value", "In", "Out", "In 24", "Out 24", "Status", "Training Status"
]

# ========================== ФІЛЬТРИ В САЙДБАРІ ==========================
st.sidebar.header("UCL Main Info") 

# --- 1. TEAM ---
all_teams = sorted(df['Team'].unique())
selected_teams = []
for i in range(0, len(all_teams), 4):
    batch = all_teams[i:i+4]
    res = st.sidebar.pills(
        label="Team" if i == 0 else f"team_group_{i}", 
        options=batch, 
        default=batch, 
        selection_mode="multi",
        label_visibility="visible" if i == 0 else "collapsed"
    )
    if res:
        selected_teams.extend(res)

# --- 2. UCL POSITION ---
pos_order = ['GK', 'DEF', 'MID', 'FW']
actual_pos = df['Pos'].unique().tolist()
sorted_positions = [p for p in pos_order if p in actual_pos] + sorted([p for p in actual_pos if p not in pos_order])

selected_positions = st.sidebar.pills(
    "UCL Position", 
    options=sorted_positions, 
    default=sorted_positions, 
    selection_mode="multi"
)

# --- 3. PLAYING POSITION ---
pl_lines = [
    ['GK'],
    ['RB', 'CB', 'LB'],
    ['RM', 'DM', 'CM', 'LM'],
    ['RW', 'AM', 'LW'],
    ['SS', 'CF']
]
defined_pl_pos = [item for sublist in pl_lines for item in sublist]
actual_pl_pos = df['Pl Pos'].dropna().unique().tolist()
others = sorted([p for p in actual_pl_pos if p not in defined_pl_pos])
if others:
    pl_lines.append(others)

selected_pl_pos = []
for idx, line in enumerate(pl_lines):
    available_in_line = [p for p in line if p in actual_pl_pos]
    if available_in_line:
        line_res = st.sidebar.pills(
            label="Playing Position" if idx == 0 else f"pl_line_{idx}",
            options=available_in_line,
            default=available_in_line,
            selection_mode="multi",
            label_visibility="visible" if idx == 0 else "collapsed"
        )
        if line_res:
            selected_pl_pos.extend(line_res)

# --- СЛАЙДЕРИ UCL ---
c_min, c_max = float(df['Price'].min()), float(df['Price'].max())
f_cost = st.sidebar.slider("UCL Price", c_min, c_max, (c_min, c_max), 0.1)

# Matches: дефолт = 1 (використовуємо Mins як аналог активності, якщо немає matches_played)
# Якщо у вас є колонка з кількістю матчів, замініть 'Mins' на неї. 
# Поки що фільтруємо по хвилинах > 0 як ознаку гри.
m_min, m_max = int(df['Mins'].min()), int(df['Mins'].max())
f_mins = st.sidebar.slider("Minutes played", m_min, m_max, (1, m_max))

s_min, s_max = float(df['Selected'].min()), float(df['Selected'].max())
f_selected = st.sidebar.slider("Selected %", s_min, s_max, (s_min, s_max), 0.1)

t5_min, t5_max = float(df['Top 5K'].min()), float(df['Top 5K'].max())
f_top5k = st.sidebar.slider("Top 5K %", t5_min, t5_max, (t5_min, t5_max), 0.1)

ppm_min, ppm_max = float(df['PPM'].min()), float(df['PPM'].max())
f_ppm = st.sidebar.slider("PPM (Points Per Match)", ppm_min, ppm_max, (ppm_min, ppm_max), 0.1)

# ========================== ЗАСТОСУВАННЯ ФІЛЬТРІВ ==========================
mask = (
    df['Pos'].isin(selected_positions if selected_positions else []) &
    df['Team'].isin(selected_teams if selected_teams else []) &
    df['Pl Pos'].isin(selected_pl_pos if selected_pl_pos else []) &
    (df['Price'] >= f_cost[0]) & (df['Price'] <= f_cost[1]) &
    (df['Mins'] >= f_mins[0]) & (df['Mins'] <= f_mins[1]) &
    (df['Selected'] >= f_selected[0]) & (df['Selected'] <= f_selected[1]) &
    (df['Top 5K'] >= f_top5k[0]) & (df['Top 5K'] <= f_top5k[1]) &
    (df['PPM'] >= f_ppm[0]) & (df['PPM'] <= f_ppm[1])
)
filtered_df = df[mask].copy()

# ========================== ВІДОБРАЖЕННЯ ТАБЛИЦІ ==========================
st.subheader(f"UCL Players filtered: {len(filtered_df)}")

st.dataframe(
    filtered_df[display_columns],
    use_container_width=True,
    hide_index=True,
    height=800,
    column_config={
        "Player": st.column_config.TextColumn("Player", width="medium", pinned=True),
        "Age": st.column_config.NumberColumn("Age", width=35),
        "Pos": st.column_config.TextColumn("Pos", width=45),
        "Pl Pos": st.column_config.TextColumn("Pl Pos", width=45),
        "Team": st.column_config.TextColumn("Team", width=45),
        "Team Name": st.column_config.TextColumn("Team Name", width=100),
        "Price": st.column_config.NumberColumn("Price", width=40, format="%.1f"),
        "TM Value": st.column_config.NumberColumn("TM Value", width=50, format="%.1f"),
        "Selected": st.column_config.NumberColumn("Sel %", width=45, format="%.1f"),
        "Top 1K": st.column_config.NumberColumn("Top 1K", width=45, format="%.1f"),
        "Top 5K": st.column_config.NumberColumn("Top 5K", width=45, format="%.1f"),
	"Captain": st.column_config.NumberColumn("Cap", width=45, format="%.1f"),
        "Mins": st.column_config.NumberColumn("Mins", width=40),
        "G": st.column_config.NumberColumn("G", width=35),
        "A": st.column_config.NumberColumn("A", width=35),
        "POTM": st.column_config.NumberColumn("POTM", width=40),
        "PPM": st.column_config.NumberColumn("PPM", width=40, format="%.1f"),
	"Value": st.column_config.NumberColumn("Value", width=40, format="%.1f"),
        "In": st.column_config.NumberColumn("In", width=60),
        "Out": st.column_config.NumberColumn("Out", width=60),
        "In 24": st.column_config.NumberColumn("In 24", width=50),
        "Out 24": st.column_config.NumberColumn("Out 24", width=50),
        "Status": st.column_config.TextColumn("Status", width=85),
	"Training Status": st.column_config.TextColumn("Training Status", width="medium"),
    }
)
