import streamlit as st
import json
import os
import matplotlib.cm as cm
import matplotlib.colors as mcolors

st.set_page_config(page_title="Predictor", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
.predictor-matrix {
    border-collapse: collapse;
    width: 100%;
    margin-bottom: 30px;
    font-size: 0.9rem;
}
.predictor-matrix th, .predictor-matrix td {
    border: 1px solid #444;
    text-align: center;
    padding: 10px;
}
.predictor-matrix th {
    background-color: #2e2e2e;
    color: #fff;
    font-weight: bold;
}
.predictor-matrix td {
    color: #fff;
    font-weight: 500;
    text-shadow: 1px 1px 2px rgba(0,0,0,0.8);
}
.popular-score {
    font-weight: 900 !important;
    text-decoration: underline;
    font-size: 1.05rem;
}
.away-team-header {
    writing-mode: vertical-rl;
    transform: rotate(180deg);
    white-space: nowrap;
    padding: 10px;
}
</style>
""", unsafe_allow_html=True)

# Load Data
BASE_DIR = r"e:\Documents\python\opt\streamlit"
TOURNAMENTS = {
    'UCL': 'predictor_ucl_out.json',
    'UEL': 'predictor_uel_out.json',
    'UECL': 'predictor_uecl_out.json'
}

available_tournaments = []
data_cache = {}

for name, filename in TOURNAMENTS.items():
    filepath = os.path.join(BASE_DIR, filename)
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data_cache[name] = json.load(f)
                available_tournaments.append(name)
        except Exception:
            pass

if not available_tournaments:
    st.warning("No predictor data available. Please check the backend service.")
    st.stop()

# UI
st.title("European Predictor")

selected_tournament = st.selectbox("Select Tournament", available_tournaments)

data = data_cache[selected_tournament]
last_updated = data.get("last_updated", "Unknown")

st.markdown(f"<p style='text-align: right; font-size: 0.8rem; color: #888888; margin-top: -3.5rem; margin-bottom: 1.0rem;'>Data updated: <b>{last_updated}</b></p>", unsafe_allow_html=True)

matches = data.get("matches", [])

if not matches:
    st.info("No matches found for this tournament.")
    st.stop()

# Helper for color mapping
cmap = cm.get_cmap('RdYlGn')
def get_color(val, min_val, max_val):
    if max_val == min_val:
        norm_val = 0.5
    else:
        norm_val = (val - min_val) / (max_val - min_val)
    rgba = cmap(norm_val)
    return mcolors.to_hex(rgba)

for match in matches:
    home_team = match['home_team']
    away_team = match['away_team']
    xg_h = match['xg_home']
    xg_a = match['xg_away']
    ev_matrix = match['ev_matrix']
    popular = match.get('popular_scores', [])
    
    ev_values = list(ev_matrix.values())
    min_ev = min(ev_values)
    max_ev = max(ev_values)
    
    st.markdown(f"### {home_team} ({xg_h}) vs {away_team} ({xg_a})")
    
    html = '<table class="predictor-matrix">'
    
    # Top headers
    html += f'<tr><th colspan="2" rowspan="2" style="background-color: transparent; border: none;"></th><th colspan="7" style="font-size: 1.1rem;">{home_team} Goals</th></tr>'
    html += '<tr>'
    for h in range(7):
        html += f'<th>{h}</th>'
    html += '</tr>'
    
    # Rows
    for a in range(7):
        html += '<tr>'
        if a == 0:
            html += f'<th rowspan="7" class="away-team-header" style="font-size: 1.1rem;">{away_team} Goals</th>'
        html += f'<th>{a}</th>'
        
        for h in range(7):
            key = f"{h}-{a}"
            ev = ev_matrix.get(key, 0)
            
            color = get_color(ev, min_ev, max_ev)
            is_pop = key in popular
            
            cell_class = "popular-score" if is_pop else ""
            html += f'<td style="background-color: {color};" class="{cell_class}">{ev:.2f}</td>'
        
        html += '</tr>'
        
    html += '</table>'
    st.markdown(html, unsafe_allow_html=True)
