import streamlit as st
import json
import os
import sys
import matplotlib.cm as cm
import matplotlib.colors as mcolors

st.set_page_config(page_title="Predictor", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
.predictor-matrix {
    border-collapse: collapse;
    width: 100%;
    margin-bottom: 30px;
}
.predictor-matrix th, .predictor-matrix td {
    border: 1px solid var(--secondary-background-color);
    text-align: center;
    padding: 2px 5px;
}
.predictor-matrix th {
    background-color: var(--secondary-background-color);
    color: var(--text-color);
    font-weight: bold;
}
.predictor-matrix td {
    color: var(--text-color);
    font-weight: 500;
}
.popular-score {
    font-weight: 900 !important;
    text-decoration: underline;
    font-size: 1.05rem;
}
.away-team-header-container {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    min-height: 120px;
}
.away-team-header {
    writing-mode: vertical-rl;
    text-orientation: mixed;
    transform: rotate(180deg);
    white-space: nowrap;
}
</style>
""", unsafe_allow_html=True)

import requests

# Load Data
API_BASE = "http://198.244.151.163:8000"
TOURNAMENTS = {
    'UCL': f'{API_BASE}/predictor_ucl',
    'UEL': f'{API_BASE}/predictor_uel',
    'UECL': f'{API_BASE}/predictor_uecl'
}

available_tournaments = []
data_cache = {}

for name, url in TOURNAMENTS.items():
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data_cache[name] = response.json()
            available_tournaments.append(name)
    except Exception as e:
        # Silently fail if endpoint isn't ready or tournament isn't available
        pass

if not available_tournaments:
    st.warning("No predictor data available. Checked API endpoints. Please make sure the endpoints are added to your FastAPI backend.")
    st.stop()

# UI
col1, col2 = st.columns([1, 4])
with col1:
    selected_tournament = st.selectbox("Select Tournament", available_tournaments, label_visibility="collapsed")

data = data_cache[selected_tournament]
last_updated = data.get("last_updated", "Unknown")

st.markdown(f"<p style='text-align: right; font-size: 0.8rem; color: #888888; margin-top: -2.5rem; margin-bottom: 1.0rem;'>Data updated: <b>{last_updated}</b></p>", unsafe_allow_html=True)

matches = data.get("matches", [])

if not matches:
    st.info("No matches found for this tournament.")
    st.stop()

import matplotlib as mpl

# Helper for color mapping
try:
    cmap = mpl.colormaps['RdYlGn']
except AttributeError:
    cmap = cm.get_cmap('RdYlGn')

def get_color(val, min_val, max_val):
    if max_val == min_val:
        norm_val = 0.5
    else:
        norm_val = (val - min_val) / (max_val - min_val)
    r, g, b, _ = cmap(norm_val)
    return f"rgba({int(r*255)}, {int(g*255)}, {int(b*255)}, 0.45)"

for match in matches:
    home_team = match['home_team']
    away_team = match['away_team']
    xg_h = match['xg_home']
    xg_a = match['xg_away']
    ev_matrix = match['ev_matrix']
    risk_matrix = match.get('risk_matrix', {})
    popular = match.get('popular_scores', [])
    
    ev_values = list(ev_matrix.values())
    min_ev = min(ev_values)
    max_ev = max(ev_values)
    
    st.markdown(f"<h3 style='text-align: left; margin-bottom: 0px;'>{home_team} ({xg_h}) vs {away_team} ({xg_a})</h3>", unsafe_allow_html=True)
    
    html = '<table class="predictor-matrix">'
    
    # Top headers
    html += f'<tr><th colspan="2" rowspan="2" style="background-color: transparent; border: none;"></th><th colspan="7" style="font-size: 1.6rem; padding: 10px;">{home_team}</th></tr>'
    html += '<tr>'
    for h in range(7):
        html += f'<th style="font-size: 1.4rem;">{h}</th>'
    html += '</tr>'
    
    # Rows
    for a in range(7):
        html += '<tr>'
        if a == 0:
            html += f'<th rowspan="7" style="padding: 0; font-size: 1.6rem;"><div class="away-team-header-container"><div class="away-team-header">{away_team}</div></div></th>'
        html += f'<th style="font-size: 1.4rem;">{a}</th>'
        
        for h in range(7):
            key = f"{h}-{a}"
            ev = ev_matrix.get(key, 0)
            risk = risk_matrix.get(key, None)
            
            color = get_color(ev, min_ev, max_ev)
            is_pop = key in popular
            
            cell_class = "popular-score" if is_pop else ""
            risk_html = f'<br><span style="font-size: 0.95rem; opacity: 0.7; font-weight: normal;">{risk}%</span>' if risk is not None else ''
            html += f'<td style="background-color: {color}; font-size: 1.5rem; font-weight: 700;" class="{cell_class}">{ev:.2f}{risk_html}</td>'
        
        html += '</tr>'
        
    html += '</table>'
    st.markdown(html, unsafe_allow_html=True)
