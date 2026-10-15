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
    text-shadow: 0px 1px 2px rgba(0, 0, 0, 0.4);
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

def calculate_smart_ev(ev, prob, risk):
    safety = (100.0 - risk) / 100.0
    return ev * safety * (1.0 + prob / 100.0)

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
col1, col2, col3, col4, col5 = st.columns([1.8, 2.8, 2.6, 2.8, 2.0])
with col1:
    selected_tournament = st.selectbox("Select Tournament", available_tournaments, label_visibility="collapsed")
with col2:
    pick_strategy = st.selectbox(
        "Pick Strategy",
        ["🧠 Збалансована (Smart EV)", "🎯 Класична (Max EV)"],
        index=0,
        help="Стратегія вибору рекомендованого рахунку (Smart EV враховує ризик та точний рахунок)",
        label_visibility="collapsed"
    )
with col3:
    color_by = st.selectbox(
        "Color Heatmap By",
        ["Color by EV (Expected Points)", "Color by Smart EV", "Color by Score Probability (%)"],
        index=0,
        label_visibility="collapsed"
    )
with col4:
    display_mode = st.selectbox(
        "Cell Display",
        ["Show: EV + Smart + P + R", "Show: EV + Prob + Risk", "Show: Smart EV + Prob", "Show: Prob + EV", "Show: Prob Only", "Show: EV Only"],
        index=0,
        label_visibility="collapsed"
    )
with col5:
    max_risk = st.slider("Max Risk Tolerance (%)", 0, 100, 45, 5, help="Затінити прогнози, ризик яких перевищує поріг.", label_visibility="collapsed")

data = data_cache[selected_tournament]
last_updated = data.get("last_updated", "Unknown")

st.markdown(f"<p style='text-align: right; font-size: 0.8rem; color: #888888; margin-top: -1.0rem; margin-bottom: 0.5rem;'>Data updated: <b>{last_updated}</b></p>", unsafe_allow_html=True)

# Legend
st.markdown("""
<div class="legend-container">
    <span><b>EV:</b> Очікувані очки (Expected Points)</span>
    <span><span style="background: rgba(15, 23, 42, 0.7); color: #38BDF8; padding: 1px 5px; border-radius: 3px; font-weight: 700; border: 1px solid rgba(56, 189, 248, 0.3);">S-EV</span> Smart EV (Збалансоване очікування)</span>
    <span><b>P:</b> Ймовірність точного рахунку %</span>
    <span><b>R:</b> Ризик 0 очок %</span>
    <span><u><b>Підкреслено:</b></u> Популярний UEFA</span>
    <span style="border: 1px solid gold; padding: 0 4px; border-radius: 3px;"><b>Gold Box:</b> Оптимальний вибір</span>
</div>
""", unsafe_allow_html=True)

matches = data.get("matches", [])

if not matches:
    st.info("No matches found for this tournament.")
    st.stop()

# ========================== TOP 3 CAPTAIN PICKS (BOOSTER 2X) ==========================
def calculate_captain_score(ev, prob, risk):
    return calculate_smart_ev(ev, prob, risk)

captain_candidates = []
for m in matches:
    ht = m.get('home_team', 'Home')
    at = m.get('away_team', 'Away')
    ev_m = m.get('ev_matrix', {})
    risk_m = m.get('risk_matrix', {})
    prob_m = m.get('prob_matrix')
    if not prob_m:
        prob_m = compute_prob_matrix(m.get('xg_home', 0), m.get('xg_away', 0))
    pops = m.get('popular_scores', [])

    # Filter candidate scorelines by max_risk
    cand_scores = [s for s in ev_m if risk_m.get(s, 100.0) <= max_risk]
    if not cand_scores:
        cand_scores = list(ev_m.keys())

    if cand_scores:
        best_s = max(cand_scores, key=lambda s: calculate_captain_score(ev_m.get(s, 0), prob_m.get(s, 0), risk_m.get(s, 50.0)))
        ev_val = ev_m.get(best_s, 0)
        prob_val = prob_m.get(best_s, 0)
        risk_val = risk_m.get(best_s, 50.0)
        safety_val = round(100.0 - risk_val, 1)
        cs_val = calculate_captain_score(ev_val, prob_val, risk_val)

        captain_candidates.append({
            'home_team': ht,
            'away_team': at,
            'score': best_s,
            'captain_score': round(cs_val, 2),
            'ev': round(ev_val, 2),
            'prob': round(prob_val, 1),
            'risk': round(risk_val, 1),
            'safety': safety_val,
            'is_pop': best_s in pops
        })

captain_candidates.sort(key=lambda x: x['captain_score'], reverse=True)
top_captains = captain_candidates[:3]

if top_captains:
    cap_cols = st.columns(len(top_captains))
    ranks = [
        {"icon": "🥇", "title": "ТОП-1 КАПІТАН", "border": "#FFD700", "badge_bg": "rgba(255, 215, 0, 0.15)", "text_color": "#FFD700"},
        {"icon": "🥈", "title": "ТОП-2 КАПІТАН", "border": "#C0C0C0", "badge_bg": "rgba(192, 192, 192, 0.15)", "text_color": "#C0C0C0"},
        {"icon": "🥉", "title": "ТОП-3 КАПІТАН", "border": "#CD7F32", "badge_bg": "rgba(205, 127, 50, 0.15)", "text_color": "#CD7F32"},
    ]
    
    for idx, (col, cap) in enumerate(zip(cap_cols, top_captains)):
        r = ranks[idx]
        with col:
            pop_badge = '<span style="font-size: 0.75rem; background: rgba(56, 189, 248, 0.2); color: #38BDF8; padding: 2px 6px; border-radius: 4px; margin-left: 6px;">Популярний UEFA</span>' if cap['is_pop'] else '<span style="font-size: 0.75rem; background: rgba(76, 175, 80, 0.2); color: #4CAF50; padding: 2px 6px; border-radius: 4px; margin-left: 6px;">Диференціал (+5)</span>'
            
            card_html = f'''<div style="border: 2px solid {r['border']}; border-radius: 10px; padding: 12px 14px; background: var(--secondary-background-color); box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1); margin-bottom: 12px;">
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
    <span style="font-weight: 800; font-size: 0.95rem; color: {r['text_color']};">{r['icon']} {r['title']}</span>
    <span style="font-size: 0.85rem; font-weight: 700; color: #38BDF8;" title="Індекс якості капітана (EV * Safety * (1+Prob))">⭐ {cap['captain_score']:.2f}</span>
</div>
<div style="font-size: 1.05rem; font-weight: 700; margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="{cap['home_team']} vs {cap['away_team']}">
    {cap['home_team']} vs {cap['away_team']}
</div>
<div style="display: flex; align-items: baseline; gap: 8px; margin-bottom: 8px;">
    <span style="font-size: 1.8rem; font-weight: 900; color: var(--text-color);">{cap['score']}</span>
    {pop_badge}
</div>
<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 4px; font-size: 0.85rem; padding-top: 6px; border-top: 1px solid rgba(128, 128, 128, 0.2);">
    <div><span style="opacity: 0.7;">Очікувані (EV):</span> <b>{cap['ev']:.2f}</b></div>
    <div><span style="opacity: 0.7;">Ймовірність (P):</span> <b>{cap['prob']}%</b></div>
    <div><span style="opacity: 0.7;">Надійність:</span> <b>{cap['safety']}%</b></div>
    <div><span style="opacity: 0.7;">Ризик нуля (R):</span> <b>{cap['risk']}%</b></div>
</div>
</div>'''
            st.markdown(card_html, unsafe_allow_html=True)
            
    with st.expander("ℹ️ Як обирається ТОП-3 для капітанства (Booster 2x)?"):
        st.markdown("""
        **Правила капітанства у Predictor:**
        * У кожному турі бали за один обраний матч **подвоюються ($2\\times$)**.
        * Якщо матч закінчиться з нулем очок, бустер втрачається марно ($0 \\times 2 = 0$). Тому для капітана критично мати не лише високий EV, але й **високу надійність (низький ризик нуля)** та **високий шанс точного рахунку** для джекпоту.
        
        **Формула Captain Score (Індекс капітана):**
        $$\\text{Captain Score} = EV \\times \\left(\\frac{100 - \\text{Risk}}{100}\\right) \\times \\left(1 + \\frac{\\text{Prob}}{100}\\right)$$
        
        * **1 результат на матч**: у кожному матчі визначається лише один найкращий прогноз, після чого матчі ранжуються між собою (матчі не повторюються).
        * **Врахування ризику**: опції з високим ризиком повного нуля отримують суттєвий штраф за рахунок множника надійності $\\text{Safety}$.
        * **Бонус за точний рахунок**: чим вища ймовірність точного рахунку, тим більший потенціал зірвати максимальні $20$–$30$ балів.
        """)

st.markdown("<hr style='margin: 12px 0 16px 0; opacity: 0.3;'>", unsafe_allow_html=True)

# Helper for color mapping (Soft Indigo / Sapphire Intensity Gradient)
def get_color(val, min_val, max_val):
    if max_val == min_val:
        norm_val = 0.5
    else:
        norm_val = max(0.0, min(1.0, (val - min_val) / (max_val - min_val)))
    
    # Smooth, eye-friendly intensity scaling (Tailwind Blue-500: rgb(59, 130, 246))
    # Unlikely scores: gentle 0.05 opacity (blends calmly with background)
    # Top optimal scores: rich 0.55 opacity (highlights cleanly without eye strain)
    alpha = 0.05 + 0.50 * (norm_val ** 1.4)
    return f"rgba(59, 130, 246, {alpha:.3f})"

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
        
    smart_ev_matrix = {
        k: calculate_smart_ev(ev_matrix.get(k, 0), prob_matrix.get(k, 0), risk_matrix.get(k, 50.0))
        for k in ev_matrix
    }
        
    popular = match.get('popular_scores', [])
    
    ev_values = list(ev_matrix.values())
    min_ev = min(ev_values) if ev_values else 0
    max_ev = max(ev_values) if ev_values else 0

    prob_values = list(prob_matrix.values())
    min_prob = min(prob_values) if prob_values else 0
    max_prob = max(prob_values) if prob_values else 0
    
    smart_ev_values = list(smart_ev_matrix.values())
    min_smart_ev = min(smart_ev_values) if smart_ev_values else 0
    max_smart_ev = max(smart_ev_values) if smart_ev_values else 0
    
    # Calculate best picks
    is_smart_strategy = "Smart EV" in pick_strategy
    optimal_pick_ev = max(ev_matrix.keys(), key=lambda k: ev_matrix[k])
    optimal_pick_smart = max(smart_ev_matrix.keys(), key=lambda k: smart_ev_matrix[k])
    
    primary_optimal = optimal_pick_smart if is_smart_strategy else optimal_pick_ev
    
    # Safest Alternative (Absolute lowest risk, excluding optimal)
    other_safe_keys = [k for k in risk_matrix.keys() if k != primary_optimal]
    safe_pick = min(other_safe_keys, key=lambda k: risk_matrix[k]) if other_safe_keys else None
    
    # Differential Alternative (Best among non-popular, excluding optimal and safe)
    diff_keys = [k for k in ev_matrix.keys() if k not in popular and k != primary_optimal and k != safe_pick]
    if is_smart_strategy:
        diff_pick = max(diff_keys, key=lambda k: smart_ev_matrix[k]) if diff_keys else None
    else:
        diff_pick = max(diff_keys, key=lambda k: ev_matrix[k]) if diff_keys else None

    visible_keys = [k for k, r in risk_matrix.items() if r <= max_risk]
    if is_smart_strategy:
        best_visible_pick = max(visible_keys, key=lambda k: smart_ev_matrix[k]) if visible_keys else None
    else:
        best_visible_pick = max(visible_keys, key=lambda k: ev_matrix[k]) if visible_keys else None
    
    st.markdown(f"<h3 style='text-align: left; margin-top: 10px; margin-bottom: 2px;'>{home_team} ({xg_h}) vs {away_team} ({xg_a})</h3>", unsafe_allow_html=True)
    
    def format_pick_tag(label, pick_key):
        if not pick_key:
            return f"{label}: N/A"
        ev_v = ev_matrix.get(pick_key, 0)
        sev_v = smart_ev_matrix.get(pick_key, 0)
        p_v = prob_matrix.get(pick_key, 0)
        r_v = risk_matrix.get(pick_key, 'N/A')
        return f"{label}: {pick_key} (EV: {ev_v:.2f} | Smart: {sev_v:.2f} | P: {p_v}% | R: {r_v}%)"
    
    safe_text = format_pick_tag("🛡️ Safest Alt", safe_pick)
    opt_label = "🧠 Optimal (Smart)" if is_smart_strategy else "🎯 Optimal (Max EV)"
    opt_text = format_pick_tag(opt_label, best_visible_pick or primary_optimal)
    diff_text = format_pick_tag("⚡ Differential", diff_pick)

    alt_tag_html = ""
    if optimal_pick_smart != optimal_pick_ev:
        alt_label = "🎯 Max EV Pick" if is_smart_strategy else "🧠 Smart Pick"
        alt_key = optimal_pick_ev if is_smart_strategy else optimal_pick_smart
        alt_text = format_pick_tag(alt_label, alt_key)
        alt_tag_html = f'<span style="color: #BA68C8; font-weight: 600;">{alt_text}</span>'
    
    tags_parts = [
        f'<span style="color: #4CAF50; font-weight: 600;">{safe_text}</span>',
        f'<span style="color: #FFC107; font-weight: 700; border-bottom: 2px solid gold;">{opt_text}</span>'
    ]
    if alt_tag_html:
        tags_parts.append(alt_tag_html)
    tags_parts.append(f'<span style="color: #38BDF8; font-weight: 600;">{diff_text}</span>')
    
    tags_html = f'<div style="display: flex; flex-wrap: wrap; justify-content: space-between; gap: 8px; font-size: 0.88rem; margin-bottom: 6px;">{"".join(tags_parts)}</div>'
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
            smart_ev = smart_ev_matrix.get(key, 0)
            
            # Heatmap color selection
            if "Probability" in color_by:
                color = get_color(prob, min_prob, max_prob)
            elif "Smart EV" in color_by:
                color = get_color(smart_ev, min_smart_ev, max_smart_ev)
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
            risk_str = f"{risk}%" if risk is not None else "N/A"
            if display_mode == "Show: EV + Smart + P + R":
                cell_content = f'''
                <div style="font-size: 1.25rem; font-weight: 800; line-height: 1.1;">{ev:.2f}</div>
                <div style="margin-top: 2px;"><span style="display: inline-block; background: rgba(15, 23, 42, 0.7); color: #38BDF8; padding: 1px 5px; border-radius: 4px; font-weight: 700; font-size: 0.74rem; border: 1px solid rgba(56, 189, 248, 0.25);">S-EV: {smart_ev:.2f}</span></div>
                <div style="font-size: 0.74rem; margin-top: 2px; line-height: 1.1; white-space: nowrap;">
                    <span title="Score Probability (P)" style="font-weight: 700;">P: {prob:.1f}%</span>
                    <span style="opacity: 0.35;"> | </span>
                    <span title="Risk of 0 pts (R)" style="opacity: 0.75;">R: {risk_str}</span>
                </div>
                '''
            elif display_mode == "Show: Smart EV + Prob":
                cell_content = f'''
                <div style="font-size: 1.25rem; font-weight: 800; line-height: 1.1; color: #38BDF8;">{smart_ev:.2f}</div>
                <div style="font-size: 0.78rem; margin-top: 2px; line-height: 1.15; white-space: nowrap;">
                    <span title="Score Probability" style="font-weight: 700;">P: {prob:.1f}%</span>
                    <span style="opacity: 0.35;"> | </span>
                    <span title="Raw EV" style="opacity: 0.85;">EV: {ev:.2f}</span>
                </div>
                '''
            elif display_mode == "Show: Prob Only":
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
