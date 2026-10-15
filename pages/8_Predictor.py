import streamlit as st
import json
import os
import sys
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import matplotlib as mpl
import requests
import math
import numpy as np

st.set_page_config(page_title="Predictor", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
.predictor-matrix {
    border-collapse: collapse;
    width: 100%;
    margin-bottom: 15px;
}
.predictor-matrix th, .predictor-matrix td {
    border: 1px solid var(--secondary-background-color);
    text-align: center;
    padding: 3px 5px;
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
.legend-container {
    display: flex;
    flex-wrap: wrap;
    gap: 15px;
    font-size: 0.85rem;
    color: #888888;
    margin-bottom: 12px;
    padding: 6px 12px;
    background: var(--secondary-background-color);
    border-radius: 6px;
}
</style>
""", unsafe_allow_html=True)

# Helper for Dixon-Coles and Poisson probability
def dixon_coles_adjustment(h, a, xg_home, xg_away, rho=-0.15):
    if h == 0 and a == 0:
        return max(0.0, 1.0 - rho * xg_home * xg_away)
    elif h == 1 and a == 0:
        return max(0.0, 1.0 + rho * xg_home)
    elif h == 0 and a == 1:
        return max(0.0, 1.0 + rho * xg_away)
    elif h == 1 and a == 1:
        return max(0.0, 1.0 - rho)
    return 1.0

def poisson_pmf(k, lam):
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return (lam ** k) * math.exp(-lam) / math.factorial(k)

def compute_prob_matrix(xg_h, xg_a, max_g=6):
    probs = np.zeros((max_g + 1, max_g + 1))
    total_p = 0.0
    for h in range(max_g + 1):
        for a in range(max_g + 1):
            p = poisson_pmf(h, xg_h) * poisson_pmf(a, xg_a) * dixon_coles_adjustment(h, a, xg_h, xg_a, rho=-0.15)
            probs[h, a] = p
            total_p += p
    if total_p > 0:
        probs /= total_p
    return {f"{h}-{a}": round(float(probs[h, a]) * 100, 1) for h in range(max_g + 1) for a in range(max_g + 1)}

# Load Data
API_BASE = "http://198.244.151.163:8000"
TOURNAMENTS = {
    'UCL': f'{API_BASE}/predictor_ucl',
    'UEL': f'{API_BASE}/predictor_uel',
    'UECL': f'{API_BASE}/predictor_uecl',
    'UWCL': f'{API_BASE}/predictor_uwcl'
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

# UI Controls
col1, col2, col3, col4 = st.columns([2.5, 2.5, 2.5, 2.5])
with col1:
    selected_tournament = st.selectbox("Select Tournament", available_tournaments, label_visibility="collapsed")
with col2:
    color_by = st.selectbox(
        "Color Heatmap By",
        ["Color by EV (Expected Points)", "Color by Score Probability (%)"],
        index=0,
        label_visibility="collapsed"
    )
with col3:
    display_mode = st.selectbox(
        "Cell Display",
        ["Show: EV + Prob + Risk", "Show: Prob + EV", "Show: Prob Only", "Show: EV Only"],
        index=0,
        label_visibility="collapsed"
    )
with col4:
    max_risk = st.slider("Max Risk Tolerance (%)", 0, 100, 45, 5, help="Gray out predictions that exceed this risk level.", label_visibility="collapsed")

data = data_cache[selected_tournament]
last_updated = data.get("last_updated", "Unknown")

st.markdown(f"<p style='text-align: right; font-size: 0.8rem; color: #888888; margin-top: -1.0rem; margin-bottom: 0.5rem;'>Data updated: <b>{last_updated}</b></p>", unsafe_allow_html=True)

# Legend
st.markdown("""
<div class="legend-container">
    <span><b>Top number:</b> EV (Expected Value / Очікувані очки)</span>
    <span><b>P:</b> Ймовірність точного рахунку (Score Probability %)</span>
    <span><b>R:</b> Ризик отримати 0 очок (Zero Points Risk %)</span>
    <span><u><b>Underlined:</b></u> Популярний вибір UEFA</span>
    <span style="border: 1px solid gold; padding: 0 4px; border-radius: 3px;"><b>Gold Box:</b> Оптимальний вибір у межах ризику</span>
</div>
""", unsafe_allow_html=True)

matches = data.get("matches", [])

if not matches:
    st.info("No matches found for this tournament.")
    st.stop()

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
    
    # Get precalculated prob_matrix or compute dynamically on the fly
    prob_matrix = match.get('prob_matrix')
    if not prob_matrix:
        prob_matrix = compute_prob_matrix(xg_h, xg_a)
        
    popular = match.get('popular_scores', [])
    
    ev_values = list(ev_matrix.values())
    min_ev = min(ev_values)
    max_ev = max(ev_values)

    prob_values = list(prob_matrix.values())
    min_prob = min(prob_values)
    max_prob = max(prob_values)
    
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
    
    st.markdown(f"<h3 style='text-align: left; margin-top: 10px; margin-bottom: 2px;'>{home_team} ({xg_h}) vs {away_team} ({xg_a})</h3>", unsafe_allow_html=True)
    
    def format_pick_tag(label, pick_key):
        if not pick_key:
            return f"{label}: N/A"
        ev_v = ev_matrix.get(pick_key, 0)
        p_v = prob_matrix.get(pick_key, 0)
        r_v = risk_matrix.get(pick_key, 'N/A')
        return f"{label}: {pick_key} (EV: {ev_v:.2f} | Prob: {p_v}% | Risk: {r_v}%)"
    
    safe_text = format_pick_tag("Safest Alt", safe_pick)
    opt_text = format_pick_tag("Optimal Pick", optimal_pick)
    diff_text = format_pick_tag("Differential Alt", diff_pick)
    
    tags_html = f'''
    <div style="display: flex; justify-content: space-between; font-size: 0.9rem; margin-bottom: 5px;">
        <span style="color: #4CAF50; font-weight: 600;">{safe_text}</span>
        <span style="color: #FFC107; font-weight: 600;">{opt_text}</span>
        <span style="color: #2196F3; font-weight: 600;">{diff_text}</span>
    </div>
    '''
    st.markdown(tags_html, unsafe_allow_html=True)
    
    html = '<table class="predictor-matrix" style="margin-top: 5px;">'
    
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
            prob = prob_matrix.get(key, 0)
            risk = risk_matrix.get(key, None)
            
            # Heatmap color selection
            if "Probability" in color_by:
                color = get_color(prob, min_prob, max_prob)
            else:
                color = get_color(ev, min_ev, max_ev)
                
            is_pop = key in popular
            cell_class = "popular-score" if is_pop else ""
            
            cell_style = f"background-color: {color};"
            if risk is not None and risk > max_risk:
                cell_style += " opacity: 0.25; filter: grayscale(80%);"
                
            if key == best_visible_pick:
                cell_style += " border: 3px solid gold; box-shadow: inset 0px 0px 10px rgba(255, 215, 0, 0.8);"
                
            # Content based on display_mode
            if display_mode == "Show: Prob Only":
                cell_content = f'''
                <div style="font-size: 1.35rem; font-weight: 800; line-height: 1.1;">{prob:.1f}%</div>
                '''
            elif display_mode == "Show: EV Only":
                risk_sub = f'<div style="font-size: 0.8rem; opacity: 0.7; margin-top: 2px;">{risk}%</div>' if risk is not None else ''
                cell_content = f'''
                <div style="font-size: 1.35rem; font-weight: 800; line-height: 1.1;">{ev:.2f}</div>
                {risk_sub}
                '''
            elif display_mode == "Show: Prob + EV":
                cell_content = f'''
                <div style="font-size: 1.35rem; font-weight: 800; line-height: 1.1;">{prob:.1f}%</div>
                <div style="font-size: 0.8rem; opacity: 0.85; margin-top: 2px;">EV: {ev:.2f}</div>
                '''
            else:  # Default: "Show: EV + Prob + Risk"
                risk_str = f"{risk}%" if risk is not None else "N/A"
                cell_content = f'''
                <div style="font-size: 1.35rem; font-weight: 800; line-height: 1.1;">{ev:.2f}</div>
                <div style="font-size: 0.8rem; margin-top: 2px; line-height: 1.15; white-space: nowrap;">
                    <span title="Score Probability (Ймовірність рахунку)" style="font-weight: 700;">P: {prob:.1f}%</span>
                    <span style="opacity: 0.35;"> | </span>
                    <span title="Risk of 0 pts (Ризик 0 очок)" style="opacity: 0.75; font-weight: 400;">R: {risk_str}</span>
                </div>
                '''
                
            html += f'<td style="{cell_style}" class="{cell_class}">{cell_content}</td>'
        
        html += '</tr>'
        
    html += '</table>'
    st.markdown(html, unsafe_allow_html=True)
