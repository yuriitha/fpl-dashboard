import streamlit as st
import pandas as pd


st.set_page_config(
    page_title="UCL Players Stats",
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
            padding-top: 2.5rem !important;
            padding-bottom: 1rem !important;
            max-width: 100% !important;
        }
        [data-testid="stTable"] th, [data-testid="stDataFrame"] th { text-align: center !important; }
        [data-testid="stDataFrame"] td { text-align: center !important; }

        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
            gap: 0.4rem !important;
        }

        [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] {
            gap: 0.1rem !important;
        }
    </style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=300)
def load_data():
    url = "http://198.244.151.163:8000/ucl_players"
    df = pd.read_parquet(url)
    sort_cols = [c for c in ['Price', 'TM Value'] if c in df.columns]
    if sort_cols:
        df = df.sort_values(by=sort_cols, ascending=[False] * len(sort_cols))
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"Помилка завантаження: {e}")
    st.stop()


display_columns = [
    "Player", "Age", "Pos", "Pl Pos", "Team", "Team Name", "Price", "Foot",
    "TM Value", "Selected", "Mins", "G", "A",
    "POTM", "PPM", "Value", "In", "Out", "In 24", "Out 24"
]


st.sidebar.header("UCL Main Info")


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


pos_order = ['GK', 'DEF', 'MID', 'FW']
actual_pos = df['Pos'].unique().tolist()
sorted_positions = [p for p in pos_order if p in actual_pos] + sorted([p for p in actual_pos if p not in pos_order])

selected_positions = st.sidebar.pills(
    "UCL Position",
    options=sorted_positions,
    default=sorted_positions,
    selection_mode="multi"
)


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


c_min, c_max = float(df['Price'].min()), float(df['Price'].max())
f_cost = st.sidebar.slider("UCL Price", c_min, c_max, (c_min, c_max), 0.1)

m_min, m_max = int(df['Mins'].min()), int(df['Mins'].max())
f_mins = st.sidebar.slider("Minutes played", m_min, m_max, (1, m_max))

s_min, s_max = float(df['Selected'].min()), float(df['Selected'].max())
f_selected = st.sidebar.slider("Selected %", s_min, s_max, (s_min, s_max), 0.1)

ppm_min, ppm_max = float(df['PPM'].min()), float(df['PPM'].max())
f_ppm = st.sidebar.slider("PPM (Points Per Match)", ppm_min, ppm_max, (ppm_min, ppm_max), 0.1)


mask = (
    df['Pos'].isin(selected_positions if selected_positions else []) &
    df['Team'].isin(selected_teams if selected_teams else []) &
    df['Pl Pos'].isin(selected_pl_pos if selected_pl_pos else []) &
    (df['Price'] >= f_cost[0]) & (df['Price'] <= f_cost[1]) &
    (df['Mins'] >= f_mins[0]) & (df['Mins'] <= f_mins[1]) &
    (df['Selected'] >= f_selected[0]) & (df['Selected'] <= f_selected[1]) &
    (df['PPM'] >= f_ppm[0]) & (df['PPM'] <= f_ppm[1])
)
filtered_df = df[mask].copy()
sort_cols = [c for c in ['Price', 'TM Value'] if c in filtered_df.columns]
if sort_cols:
    filtered_df = filtered_df.sort_values(by=sort_cols, ascending=[False] * len(sort_cols))


st.subheader(f"UCL Players filtered: {len(filtered_df)}", anchor=False)

existing_display_cols = [c for c in display_columns if c in filtered_df.columns]

st.dataframe(
    filtered_df[existing_display_cols],
    width="stretch",
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
    }
)
