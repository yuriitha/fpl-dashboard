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
    max_risk = st.slider("Max Risk Tolerance (%)", 0, 100, 100, 5, help="Gray out predictions that exceed this risk level.")

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
    
    # Calculate best picks
    optimal_pick = max(ev_matrix.keys(), key=lambda k: ev_matrix[k])
    
    # Safest Alternative (Absolute lowest risk, excluding optimal)
    other_safe_keys = [k for k in risk_matrix.keys() if k != optimal_pick]
    safe_pick = min(other_safe_keys, key=lambda k: risk_matrix[k]) if other_safe_keys else None
    
    # Differential Alternative (Best EV among non-popular, excluding optimal and safe)
    diff_keys = [k for k in ev_matrix.keys() if k not in popular and k != optimal_pick and k != safe_pick]
    diff_pick = max(diff_keys, key=lambda k: ev_matrix[k]) if diff_keys else None

    visible_keys = [k for k, r in risk_matrix.items() if r <= max_risk]
    best_visible_pick = max(visible_keys, key=lambda k: ev_matrix[k]) if visible_keys else None
    
    st.markdown(f"<h3 style='text-align: left; margin-top: 15px; margin-bottom: 5px;'>{home_team} ({xg_h}) vs {away_team} ({xg_a})</h3>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    c2.warning(f"**⚖️ Optimal Pick:** {optimal_pick} (EV: {ev_matrix[optimal_pick]:.2f} | Risk: {risk_matrix.get(optimal_pick, 'N/A')}%)")
    
    if safe_pick:
        c1.success(f"**🛡️ Safest Alternative:** {safe_pick} (EV: {ev_matrix[safe_pick]:.2f} | Risk: {risk_matrix[safe_pick]}%)")
    else:
        c1.success("**🛡️ Safest Alternative:** N/A")
        
    if diff_pick:
        c3.info(f"**🎁 Differential Alt:** {diff_pick} (EV: {ev_matrix[diff_pick]:.2f} | Risk: {risk_matrix.get(diff_pick, 'N/A')}%)")
    else:
        c3.info("**🎁 Differential Alt:** N/A")
    
    html = '<table class="predictor-matrix" style="margin-top: 10px;">'
    
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
            
            cell_style = f"background-color: {color}; font-size: 1.5rem; font-weight: 700;"
            if risk is not None and risk > max_risk:
                cell_style += " opacity: 0.25; filter: grayscale(80%);"
                
            if key == best_visible_pick:
                cell_style += " border: 3px solid gold; box-shadow: inset 0px 0px 10px rgba(255, 215, 0, 0.8);"
                
            risk_html = f'<br><span style="font-size: 0.95rem; opacity: 0.7; font-weight: normal;">{risk}%</span>' if risk is not None else ''
            html += f'<td style="{cell_style}" class="{cell_class}">{ev:.2f}{risk_html}</td>'
        
        html += '</tr>'
        
    html += '</table>'
    st.markdown(html, unsafe_allow_html=True)
