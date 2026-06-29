import streamlit as st
import anthropic
from dotenv import load_dotenv
load_dotenv()
import pandas as pd
import json
import importlib
from datetime import datetime, date
import sys
from pathlib import Path as _P

# Locate trial_data.py and add to path
def _find_trial_data_path():
    app_dir = _P(__file__).parent
    for candidate in [app_dir / "src" / "trial_data.py",
                      app_dir / "trial_data.py",
                      _P("src/trial_data.py"),
                      _P("trial_data.py")]:
        if candidate.exists():
            return candidate
    return None

_td_path = _find_trial_data_path()
if _td_path and str(_td_path.parent) not in sys.path:
    sys.path.insert(0, str(_td_path.parent))

from pdf_generator import generate_executive_summary_pdf, generate_email_pdf

try:
    import trial_data as _td_module
    importlib.reload(_td_module)
    TRIALS = _td_module.TRIALS
    TMF_ZONES = _td_module.TMF_ZONES
    FLAG_RULES = _td_module.FLAG_RULES
except Exception as _e:
    st.error(f"Failed to load trial_data.py: {_e}")
    st.stop()

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="TMF Intelligence | TrialAxis CRO",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

/* Override Streamlit red primary button to navy */
.stButton > button[kind="primary"] {
    background-color: #1A3F6F !important;
    border-color: #1A3F6F !important;
    color: white !important;
    border-radius: 8px !important;
}
.stButton > button[kind="primary"]:hover {
    background-color: #0F2942 !important;
    border-color: #0F2942 !important;
}

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.main { background: #F8F9FC; }

.stApp { background: #F8F9FC; }

/* Header */
.tmf-header {
    background: linear-gradient(135deg, #0F2942 0%, #1A3F6F 100%);
    padding: 2rem 2.5rem;
    border-radius: 12px;
    margin-bottom: 1.5rem;
    color: white;
}
.tmf-header h1 { font-size: 1.6rem; font-weight: 700; margin: 0; letter-spacing: -0.02em; }
.tmf-header p { font-size: 0.85rem; opacity: 0.7; margin: 0.25rem 0 0; }
.tmf-badge {
    display: inline-block;
    background: rgba(255,255,255,0.15);
    border: 1px solid rgba(255,255,255,0.25);
    color: white;
    font-size: 0.7rem;
    font-weight: 600;
    padding: 3px 10px;
    border-radius: 20px;
    margin-top: 0.5rem;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}

/* Metric cards */
.metric-card {
    background: white;
    border-radius: 10px;
    padding: 1.25rem 1.5rem;
    border: 1px solid #E5E7EB;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.metric-label { font-size: 0.72rem; font-weight: 600; color: #6B7280; text-transform: uppercase; letter-spacing: 0.06em; }
.metric-value { font-size: 2rem; font-weight: 700; color: #0F2942; line-height: 1.1; margin-top: 0.2rem; }
.metric-sub { font-size: 0.78rem; color: #9CA3AF; margin-top: 0.15rem; }

/* Flag badges */
.flag-critical {
    background: #FEE2E2; color: #DC2626;
    padding: 3px 10px; border-radius: 20px;
    font-size: 0.72rem; font-weight: 600;
    display: inline-block;
}
.flag-warning {
    background: #FEF3C7; color: #D97706;
    padding: 3px 10px; border-radius: 20px;
    font-size: 0.72rem; font-weight: 600;
    display: inline-block;
}
.flag-ok {
    background: #D1FAE5; color: #059669;
    padding: 3px 10px; border-radius: 20px;
    font-size: 0.72rem; font-weight: 600;
    display: inline-block;
}
.flag-review {
    background: #FEF3C7; color: #B45309;
    padding: 3px 10px; border-radius: 20px;
    font-size: 0.72rem; font-weight: 600;
    display: inline-block;
}

/* Risk badges */
.risk-high { background: #FEE2E2; color: #DC2626; padding: 2px 8px; border-radius: 4px; font-size: 0.72rem; font-weight: 600; }
.risk-medium { background: #FEF3C7; color: #D97706; padding: 2px 8px; border-radius: 4px; font-size: 0.72rem; font-weight: 600; }
.risk-low { background: #D1FAE5; color: #059669; padding: 2px 8px; border-radius: 4px; font-size: 0.72rem; font-weight: 600; }

/* Study card */
.study-card {
    background: white;
    border: 1px solid #E5E7EB;
    border-left: 4px solid #1A3F6F;
    border-radius: 10px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 0.75rem;
    cursor: pointer;
    transition: box-shadow 0.15s;
}
.study-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
.study-card h4 { font-size: 0.95rem; font-weight: 600; color: #0F2942; margin: 0 0 0.3rem; }
.study-card p { font-size: 0.8rem; color: #6B7280; margin: 0; }

/* Section headers */
.section-header {
    font-size: 0.7rem;
    font-weight: 700;
    color: #9CA3AF;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin: 1.5rem 0 0.75rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #E5E7EB;
}

/* Chat bubbles */
.chat-user {
    background: #0F2942;
    color: white;
    padding: 0.75rem 1rem;
    border-radius: 12px 12px 4px 12px;
    margin: 0.5rem 0;
    font-size: 0.88rem;
    max-width: 80%;
    margin-left: auto;
}
.chat-claude {
    background: white;
    border: 1px solid #E5E7EB;
    color: #1F2937;
    padding: 0.75rem 1rem;
    border-radius: 12px 12px 12px 4px;
    margin: 0.5rem 0;
    font-size: 0.88rem;
    max-width: 90%;
    line-height: 1.6;
}

/* Document table rows */
.doc-row {
    display: flex;
    align-items: center;
    padding: 0.6rem 0;
    border-bottom: 1px solid #F3F4F6;
    font-size: 0.83rem;
}

/* Email draft */
.email-box {
    background: white;
    border: 1px solid #E5E7EB;
    border-radius: 10px;
    padding: 1.5rem;
    font-size: 0.85rem;
    line-height: 1.7;
    white-space: pre-wrap;
    font-family: 'Inter', sans-serif;
    color: #1F2937;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #0F2942 !important;
}
section[data-testid="stSidebar"] * { color: white !important; }
section[data-testid="stSidebar"] .stRadio label { font-size: 0.88rem !important; }

div[data-testid="stMarkdownContainer"] h3 { color: #0F2942; }
</style>
""", unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────────
def get_client():
    return anthropic.Anthropic()

def count_flags(trial):
    docs = trial["tmf_documents"]
    critical = sum(1 for d in docs.values() if d["status"] in ["Missing", "Expired"])
    warning = sum(1 for d in docs.values() if d["status"] == "Needs Review")
    return critical, warning

def completeness_pct(trial):
    docs = trial["tmf_documents"]
    complete = sum(1 for d in docs.values() if d["status"] == "Complete")
    return round(complete / len(docs) * 100)

def flag_badge(status):
    if status == "Complete":
        return '<span class="flag-ok">✓ Complete</span>'
    elif status == "Missing":
        return '<span class="flag-critical">✗ Missing</span>'
    elif status == "Expired":
        return '<span class="flag-critical">⚠ Expired</span>'
    elif status == "Needs Review":
        return '<span class="flag-review">~ Review</span>'
    return status

def risk_badge(risk):
    r = risk.lower()
    return f'<span class="risk-{r}">{risk}</span>'

def build_trial_context():
    """Build a rich text context of all trials for Claude"""
    context = "TMF INTELLIGENCE SYSTEM — TRIAL DATABASE\n\n"
    for nct, t in TRIALS.items():
        context += f"{'='*60}\n"
        context += f"STUDY: {t['short_name']} ({nct})\n"
        context += f"Drug: {t['drug']} | Sponsor: {t['sponsor']}\n"
        context += f"Phase: {t['phase']} | Condition: {t['condition']}\n"
        context += f"Design: {t['design']} | Duration: {t['duration']}\n"
        context += f"Countries: {', '.join(t['countries'])}\n"
        context += f"Protocol Date: {t['protocol_date']} | Latest: {t['latest_amendment']} ({t['latest_amendment_date']})\n"
        if t.get('patients_screened'):
            context += f"Patients Screened: {t['patients_screened']} | Randomized: {t.get('patients_randomized', 'N/A')}\n"
        context += f"\nPRIMARY OBJECTIVE: {t['primary_objective']}\n"
        context += f"PRIMARY ENDPOINT: {t['primary_endpoint']}\n"
        context += f"\nINCLUSION CRITERIA:\n"
        for c in t['inclusion_criteria']:
            context += f"  • {c}\n"
        context += f"\nEXCLUSION CRITERIA:\n"
        for c in t['exclusion_criteria']:
            context += f"  • {c}\n"
        context += f"\nAMENDMENT HISTORY ({len(t['amendment_history'])} versions):\n"
        for a in t['amendment_history']:
            context += f"  • {a['version']} — {a['date']} ({a['patients_at_time']})\n"
        crit, warn = count_flags(t)
        context += f"\nTMF STATUS: {completeness_pct(t)}% complete | {crit} critical flags | {warn} warnings\n"
        context += f"Risk Level: {t['risk_level']}\n"
        context += f"Notes: {t['notes']}\n\n"
    return context

# ── Computed stats ───────────────────────────────────────────────────────────
total_critical = sum(count_flags(t)[0] for t in TRIALS.values())
total_warning = sum(count_flags(t)[1] for t in TRIALS.values())
avg_complete = round(sum(completeness_pct(t) for t in TRIALS.values()) / len(TRIALS))

# ── Homepage gate ─────────────────────────────────────────────────────────────
if "entered" not in st.session_state:
    st.session_state["entered"] = False

if not st.session_state["entered"]:
    st.markdown("""
    <style>
    section[data-testid="stSidebar"] { display: none !important; }
    .block-container { padding: 0 !important; max-width: 100% !important; }
    header { display: none !important; }
    .stApp { background: white !important; }

    /* Brand colors:
       Navy:  #1B3A5C
       Orange: #E8622A
       Light grey: #F5F5F5
    */

    .alim-hero {
        background: #1B3A5C;
        padding: 3rem 4rem 2.5rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 2rem;
        flex-wrap: wrap;
    }
    .alim-hero-left { flex: 1; min-width: 280px; }
    .alim-logo {
        font-size: 1.5rem;
        font-weight: 800;
        color: white;
        letter-spacing: -0.02em;
        margin-bottom: 1.5rem;
        opacity: 0.9;
    }
    .alim-logo span { color: #E8622A; }
    .alim-eyebrow {
        font-size: 0.72rem;
        font-weight: 700;
        color: #E8622A;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        margin-bottom: 0.75rem;
    }
    .alim-headline {
        font-size: 2.8rem;
        font-weight: 900;
        color: white;
        line-height: 1.0;
        letter-spacing: -0.04em;
        margin-bottom: 0.5rem;
    }
    .alim-headline span { color: #E8622A; }
    .alim-tagline {
        font-size: 1rem;
        color: rgba(255,255,255,0.6);
        margin-bottom: 2rem;
        font-weight: 400;
    }

    .alim-stats {
        display: flex;
        gap: 1.5rem;
        flex-wrap: wrap;
    }
    .alim-stat {
        text-align: center;
        border-left: 3px solid #E8622A;
        padding-left: 1rem;
    }
    .alim-stat .n {
        font-size: 2rem;
        font-weight: 800;
        color: white;
        line-height: 1;
    }
    .alim-stat .n.orange { color: #E8622A; }
    .alim-stat .l {
        font-size: 0.65rem;
        color: rgba(255,255,255,0.45);
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 600;
        margin-top: 3px;
    }

    .alim-orange-bar {
        background: #E8622A;
        height: 6px;
        width: 100%;
    }

    .alim-body {
        background: white;
        padding: 2.5rem 4rem;
    }
    .alim-section-title {
        font-size: 0.7rem;
        font-weight: 700;
        color: #1B3A5C;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        margin-bottom: 1.25rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #E8622A;
        display: inline-block;
    }
    .alim-capabilities {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 1rem;
        margin-bottom: 2rem;
    }
    .alim-cap {
        background: #F7F9FB;
        border: 1px solid #E5EAF0;
        border-top: 3px solid #1B3A5C;
        border-radius: 4px;
        padding: 1rem 1.25rem;
    }
    .alim-cap .cap-icon { font-size: 1.2rem; margin-bottom: 0.4rem; }
    .alim-cap .cap-title {
        font-size: 0.82rem;
        font-weight: 700;
        color: #1B3A5C;
        margin-bottom: 0.25rem;
    }
    .alim-cap .cap-desc {
        font-size: 0.72rem;
        color: #6B7280;
        line-height: 1.5;
    }

    .alim-footer-bar {
        background: #1B3A5C;
        padding: 1rem 4rem;
        font-size: 0.7rem;
        color: rgba(255,255,255,0.35);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .stButton > button {
        background: #E8622A !important;
        color: white !important;
        border: none !important;
        border-radius: 4px !important;
        font-weight: 700 !important;
        font-size: 0.9rem !important;
        padding: 0.75rem 2rem !important;
        letter-spacing: 0.03em !important;
        width: 100% !important;
        text-transform: uppercase !important;
    }
    .stButton > button:hover {
        background: #C94E1E !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # HERO SECTION
    st.markdown(f"""
    <div class="alim-hero">
        <div class="alim-hero-left">
            <div class="alim-logo">Trial<span>Axis</span></div>
            <div class="alim-eyebrow">AI-Powered Internal Tool</div>
            <div class="alim-headline">TMF<br><span>Intelligence</span><br>System</div>
            <div class="alim-tagline">Smarter trial document management. Powered by Claude AI.</div>
            <div class="alim-stats">
                <div class="alim-stat">
                    <div class="n">{len(TRIALS)}</div>
                    <div class="l">Active Trials</div>
                </div>
                <div class="alim-stat">
                    <div class="n">{avg_complete}%</div>
                    <div class="l">TMF Complete</div>
                </div>
                <div class="alim-stat">
                    <div class="n orange">{total_critical}</div>
                    <div class="l">Critical Flags</div>
                </div>
                <div class="alim-stat">
                    <div class="n orange">{total_warning}</div>
                    <div class="l">Warnings</div>
                </div>
            </div>
        </div>
    </div>
    <div class="alim-orange-bar"></div>
    """, unsafe_allow_html=True)

    # CAPABILITIES SECTION
    st.markdown("""
    <div class="alim-body">
        <div class="alim-section-title">Platform Capabilities</div>
        <div class="alim-capabilities">
            <div class="alim-cap">
                <div class="cap-icon">📊</div>
                <div class="cap-title">Study Overview</div>
                <div class="cap-desc">Search and drill into any GI trial — endpoints, amendments, criteria</div>
            </div>
            <div class="alim-cap">
                <div class="cap-icon">📁</div>
                <div class="cap-title">TMF Tracker</div>
                <div class="cap-desc">Document completeness per study with colour-coded status</div>
            </div>
            <div class="alim-cap">
                <div class="cap-icon">🚨</div>
                <div class="cap-title">Flags Dashboard</div>
                <div class="cap-desc">All critical issues and warnings across the full portfolio</div>
            </div>
            <div class="alim-cap">
                <div class="cap-icon">💬</div>
                <div class="cap-title">Query Studies</div>
                <div class="cap-desc">Ask Claude anything — compare endpoints, criteria, amendments</div>
            </div>
            <div class="alim-cap">
                <div class="cap-icon">✉️</div>
                <div class="cap-title">Draft Communications</div>
                <div class="cap-desc">Auto-generate site coordinator follow-up emails in one click</div>
            </div>
            <div class="alim-cap">
                <div class="cap-icon">📋</div>
                <div class="cap-title">Executive Summary</div>
                <div class="cap-desc">Audit-ready portfolio summaries generated instantly</div>
            </div>
        </div>
    </div>
    <div class="alim-footer-bar">
        <span>TrialAxis CRO Internal Tool &nbsp;·&nbsp; Not for external distribution</span>
        <span>Powered by Claude API &nbsp;·&nbsp; ICH E6 GCP &nbsp;·&nbsp; ClinicalTrials.gov</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1.5, 1, 1.5])
    with col2:
        if st.button("ENTER DASHBOARD →", use_container_width=True):
            st.session_state["entered"] = True
            st.rerun()
    st.stop()

# ── Sidebar (shown only after homepage) ──────────────────────────────────────
# Fix dashboard button colors back to navy
st.markdown("""
<style>
.stButton > button {
    background-color: #1A3F6F !important;
    border-color: #1A3F6F !important;
    color: white !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}
.stButton > button:hover {
    background-color: #0F2942 !important;
    border-color: #0F2942 !important;
}
section[data-testid="stSidebar"] .stButton > button {
    background: rgba(255,255,255,0.12) !important;
    border: 1px solid rgba(255,255,255,0.25) !important;
    color: white !important;
    font-size: 0.8rem !important;
    border-radius: 6px !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,0.2) !important;
}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 🧬 TMF Intelligence")
    st.markdown('<p style="font-size:0.75rem;opacity:0.6;margin-top:-0.5rem;">Powered by Claude API</p>', unsafe_allow_html=True)
    st.markdown("---")
    module = st.radio(
        "Navigate",
        ["📊 Study Overview", "📁 TMF Tracker", "🚨 Flags Dashboard", "💬 Query Studies", "✉️ Draft Communications", "📋 Executive Summary", "📥 Ingestion Tracker"],
        label_visibility="collapsed"
    )
    st.markdown("---")
    if st.button("← Back to Home", use_container_width=True):
        st.session_state["entered"] = False
        st.rerun()
    st.markdown(f'<p style="font-size:0.72rem;opacity:0.4;margin-top:0.75rem">{len(TRIALS)} GI Trials · ClinicalTrials.gov<br>ICH E6 GCP Compliant</p>', unsafe_allow_html=True)

# ── Dashboard header ──────────────────────────────────────────────────────────
st.markdown(f"""
<div class="tmf-header">
    <h1>Trial Master File Intelligence System</h1>
    <p>GI Clinical Trials Portfolio — TrialAxis CRO Internal</p>
    <span class="tmf-badge">Claude API · {len(TRIALS)} Active Studies · ICH E6 GCP Compliant</span>
</div>
""", unsafe_allow_html=True)

# ── Top metrics ───────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f'<div class="metric-card"><div class="metric-label">Active Studies</div><div class="metric-value">{len(TRIALS)}</div><div class="metric-sub">GI / IBD Portfolio</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="metric-card"><div class="metric-label">Avg TMF Completeness</div><div class="metric-value">{avg_complete}%</div><div class="metric-sub">Across all trials</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="metric-card"><div class="metric-label">Critical Flags</div><div class="metric-value" style="color:#DC2626">{total_critical}</div><div class="metric-sub">Require immediate action</div></div>', unsafe_allow_html=True)
with c4:
    st.markdown(f'<div class="metric-card"><div class="metric-label">Warnings</div><div class="metric-value" style="color:#D97706">{total_warning}</div><div class="metric-sub">Review within 14 days</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# MODULE 1 — STUDY OVERVIEW (two-panel layout)
# ══════════════════════════════════════════════════════════════════════════════
if module == "📊 Study Overview":

    # Extra CSS for two-panel layout
    st.markdown("""
    <style>
    .study-list-panel {
        background: white;
        border: 1px solid #E5E7EB;
        border-radius: 10px;
        padding: 0.75rem;
        height: 520px;
        overflow-y: auto;
    }
    .study-list-item {
        padding: 0.65rem 0.75rem;
        border-radius: 8px;
        cursor: pointer;
        border-left: 3px solid transparent;
        margin-bottom: 4px;
        transition: background 0.1s;
    }
    .study-list-item:hover { background: #F3F4F6; }
    .study-list-item.active {
        background: #EFF6FF;
        border-left-color: #1A3F6F;
    }
    .study-list-item h5 {
        font-size: 0.82rem; font-weight: 600;
        color: #0F2942; margin: 0 0 2px;
    }
    .study-list-item p {
        font-size: 0.72rem; color: #6B7280; margin: 0;
    }
    .detail-panel {
        background: white;
        border: 1px solid #E5E7EB;
        border-radius: 10px;
        padding: 1.5rem;
        height: 520px;
        overflow-y: auto;
    }
    .amend-table { width: 100%; border-collapse: collapse; font-size: 0.8rem; margin-top: 0.5rem; }
    .amend-table th { background: #F9FAFB; color: #6B7280; font-weight: 600;
        padding: 6px 10px; text-align: left; border-bottom: 1px solid #E5E7EB; font-size: 0.72rem; text-transform: uppercase; }
    .amend-table td { padding: 6px 10px; border-bottom: 1px solid #F3F4F6; color: #374151; vertical-align: top; }
    .amend-table tr:last-child td { border-bottom: none; }
    </style>
    """, unsafe_allow_html=True)

    search = st.text_input("🔍 Search", placeholder="Drug, condition, sponsor, phase, country...")

    filtered = {}
    for tax_id, t in TRIALS.items():
        if not search:
            filtered[tax_id] = t
        else:
            s = search.lower()
            searchable = f"{t['drug']} {t['condition']} {t['sponsor']} {t['phase']} {' '.join(t['countries'])} {t['short_name']}".lower()
            if s in searchable:
                filtered[tax_id] = t

    if not filtered:
        st.info("No studies match your search.")
    else:
        # Default to first study
        if "selected_study" not in st.session_state:
            st.session_state["selected_study"] = list(filtered.keys())[0]

        selected_nct = st.session_state.get("selected_study")

        # Two-column layout: list left, detail right
        left_col, right_col = st.columns([1, 2])

        # LEFT PANEL — scrollable study cards with chevron button
        with left_col:
            st.markdown("""
            <style>
            .study-scroll-wrap {
                border: 1px solid #E5E7EB; border-radius: 10px;
                overflow-y: auto; max-height: 480px;
                background: #F9FAFB; padding: 6px 6px 2px 6px;
            }
            .srow { display:flex; align-items:center; gap:6px; margin-bottom:5px; }
            .scard-info { flex:1; background:white; border:1px solid #E5E7EB;
                border-left:3px solid #CBD5E1; border-radius:7px; padding:5px 10px; }
            .scard-info.active { background:#EFF6FF; border-color:#BFDBFE; border-left-color:#1A3F6F; }
            .scard-drug  { font-size:0.8rem; font-weight:600; color:#0F2942; }
            .scard-meta  { font-size:0.68rem; color:#6B7280; margin-top:1px; }
            .scard-flags { font-size:0.67rem; margin-top:2px; }
            .chev-wrap div[data-testid="stButton"] > button {
                background:#1A3F6F !important; color:white !important;
                border:none !important; border-radius:6px !important;
                padding:4px 9px !important; font-size:0.8rem !important;
                font-weight:700 !important; line-height:1 !important;
                height:auto !important; min-height:unset !important;
                width:auto !important; box-shadow:none !important;
            }
            .chev-wrap div[data-testid="stButton"] > button:hover { background:#E8622A !important; }
            </style>
            """, unsafe_allow_html=True)

            st.markdown('<div class="study-scroll-wrap">', unsafe_allow_html=True)
            for tax_id, t in filtered.items():
                crit, warn = count_flags(t)
                comp = completeness_pct(t)
                is_active = tax_id == selected_nct
                active_cls = "scard-info active" if is_active else "scard-info"
                flag_html = ""
                if crit: flag_html += f'<span style="color:#DC2626">⚠ {crit} critical</span>&nbsp;'
                if warn: flag_html += f'<span style="color:#D97706">~ {warn} warnings</span>'
                if not flag_html: flag_html = '<span style="color:#059669">✓ Clean</span>'
                card_col, btn_col = st.columns([5, 1])
                with card_col:
                    st.markdown(f"""
                    <div class="{active_cls}">
                      <div class="scard-drug">{t['drug']}</div>
                      <div class="scard-meta">{t['phase']} · {t['condition']} · {comp}% complete</div>
                      <div class="scard-flags">{flag_html}</div>
                    </div>""", unsafe_allow_html=True)
                with btn_col:
                    st.markdown('<div class="chev-wrap">', unsafe_allow_html=True)
                    if st.button("›", key=f"sel_{tax_id}"):
                        st.session_state["selected_study"] = tax_id
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # RIGHT PANEL — study detail
        with right_col:
            if selected_nct and selected_nct in TRIALS:
                t = TRIALS[selected_nct]
                comp = completeness_pct(t)
                crit, warn = count_flags(t)

                # Pre-compute all values to avoid nested f-string issues
                drug = t['drug']
                short_name = t['short_name']
                nct_id = t['tax_id']
                phase = t['phase']
                condition = t['condition']
                sponsor = t['sponsor']
                countries = ', '.join(t['countries'])
                endpoint = t['primary_endpoint']
                risk = risk_badge(t['risk_level'])

                incl_html = "".join(f"<div style='margin-bottom:4px;font-size:0.78rem'>&#10003; {c}</div>" for c in t['inclusion_criteria'])
                excl_html = "".join(f"<div style='margin-bottom:4px;font-size:0.78rem'>&#10007; {c}</div>" for c in t['exclusion_criteria'])
                amend_rows = "".join(f"<tr><td>{a['version']}</td><td>{a['date']}</td><td>{a['patients_at_time']}</td></tr>" for a in t['amendment_history'])

                st.markdown(f"#### {drug} &nbsp; <small style='color:#6B7280;font-weight:400'>{short_name} · {nct_id}</small>", unsafe_allow_html=True)

                mc1, mc2, mc3 = st.columns(3)
                mc1.metric("Phase", phase)
                mc2.metric("Completeness", f"{comp}%")
                mc3.metric("Risk", t['risk_level'])

                st.markdown(f"**Condition:** {condition} &nbsp;|&nbsp; **Sponsor:** {sponsor} &nbsp;|&nbsp; **Countries:** {countries}")
                st.markdown(f"**Primary Endpoint:** {endpoint}")

                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown("**Inclusion Criteria**")
                    st.markdown(incl_html, unsafe_allow_html=True)
                with col_b:
                    st.markdown("**Exclusion Criteria**")
                    st.markdown(excl_html, unsafe_allow_html=True)

                st.markdown("**Amendment History**")
                amend_df = pd.DataFrame(t['amendment_history'])
                amend_df.columns = ["Version", "Date", "Patients at Time"]
                st.dataframe(amend_df, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# MODULE 2 — TMF TRACKER
# ══════════════════════════════════════════════════════════════════════════════
elif module == "📁 TMF Tracker":
    st.markdown("### TMF Document Tracker")

    selected = st.selectbox("Select Study", options=list(TRIALS.keys()),
        format_func=lambda x: f"{x} — {TRIALS[x]['short_name']} — {TRIALS[x]['drug']}")

    t = TRIALS[selected]
    comp = completeness_pct(t)
    crit, warn = count_flags(t)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Completeness", f"{comp}%")
    col2.metric("Total Documents", len(t['tmf_documents']))
    col3.metric("Critical", crit, delta=f"{crit} need action", delta_color="inverse")
    col4.metric("Warnings", warn)

    st.markdown('<div class="section-header">Document Status</div>', unsafe_allow_html=True)

    rows = []
    for doc, info in t['tmf_documents'].items():
        rows.append({
            "Document": doc,
            "Status": info["status"],
            "Date Filed": info["date"] or "—",
            "Version / Notes": info["version"] or "—"
        })

    df = pd.DataFrame(rows)

    def style_status(val):
        if val == "Complete":
            return "background-color: #D1FAE5; color: #059669; font-weight: 600"
        elif val in ["Missing", "Expired"]:
            return "background-color: #FEE2E2; color: #DC2626; font-weight: 600"
        elif val == "Needs Review":
            return "background-color: #FEF3C7; color: #D97706; font-weight: 600"
        return ""

    styled = df.style.map(style_status, subset=["Status"])
    st.dataframe(styled, use_container_width=True, hide_index=True)

    if crit > 0 or warn > 0:
        st.markdown('<div class="section-header">Required Actions</div>', unsafe_allow_html=True)
        for doc, info in t['tmf_documents'].items():
            if info['status'] in ["Missing", "Expired"]:
                st.error(f"**{doc}** — {FLAG_RULES['Missing']['action']}")
            elif info['status'] == "Needs Review":
                st.warning(f"**{doc}** — {FLAG_RULES['Needs Review']['action']}")


# ══════════════════════════════════════════════════════════════════════════════
# MODULE 3 — FLAGS DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
elif module == "🚨 Flags Dashboard":
    st.markdown("### Flags Dashboard — All Studies")

    severity_filter = st.multiselect("Filter by severity", ["Critical", "Warning"], default=["Critical", "Warning"])

    all_flags = []
    for nct, t in TRIALS.items():
        for doc, info in t['tmf_documents'].items():
            if info['status'] in ["Missing", "Expired"] and "Critical" in severity_filter:
                all_flags.append({
                    "Study": t['short_name'],
                    "Drug": t['drug'],
                    "Document": doc,
                    "Status": info['status'],
                    "Severity": "Critical",
                    "Version/Notes": info['version'] or "—",
                    "Action": FLAG_RULES[info['status']]['action']
                })
            elif info['status'] == "Needs Review" and "Warning" in severity_filter:
                all_flags.append({
                    "Study": t['short_name'],
                    "Drug": t['drug'],
                    "Document": doc,
                    "Status": info['status'],
                    "Severity": "Warning",
                    "Version/Notes": info['version'] or "—",
                    "Action": FLAG_RULES['Needs Review']['action']
                })

    if not all_flags:
        st.success("No flags matching selected filters.")
    else:
        st.markdown(f"**{len(all_flags)} flags** across {len(TRIALS)} studies")
        df_flags = pd.DataFrame(all_flags)

        def style_sev(val):
            if val == "Critical":
                return "background-color: #FEE2E2; color: #DC2626; font-weight: 600"
            return "background-color: #FEF3C7; color: #D97706; font-weight: 600"

        styled_flags = df_flags.style.map(style_sev, subset=["Severity"]).map(style_sev, subset=["Status"])
        st.dataframe(styled_flags, use_container_width=True, hide_index=True)

        st.markdown('<div class="section-header">By Study</div>', unsafe_allow_html=True)
        for nct, t in TRIALS.items():
            crit, warn = count_flags(t)
            if (crit > 0 and "Critical" in severity_filter) or (warn > 0 and "Warning" in severity_filter):
                with st.expander(f"{t['drug']} — {t['short_name']}  |  {crit} critical · {warn} warnings"):
                    for doc, info in t['tmf_documents'].items():
                        if info['status'] in ["Missing", "Expired"] and "Critical" in severity_filter:
                            st.error(f"**{doc}** [{info['status']}] — {info.get('version') or 'No version on file'}")
                        elif info['status'] == "Needs Review" and "Warning" in severity_filter:
                            st.warning(f"**{doc}** [Needs Review] — {info.get('version') or '—'}")


# ══════════════════════════════════════════════════════════════════════════════
# MODULE 4 — QUERY STUDIES
# ══════════════════════════════════════════════════════════════════════════════
elif module == "💬 Query Studies":
    st.markdown("### Query Studies with Claude")
    st.markdown("Ask any question across all 5 GI trials. Claude reads the actual protocol content and answers.")

    # Initialise session state
    if "query_history" not in st.session_state:
        st.session_state.query_history = []
    if "active_query" not in st.session_state:
        st.session_state.active_query = ""

    example_queries = [
        "Compare the primary endpoints across all 5 studies",
        "Which studies cover Crohn's disease?",
        "Which study has the most amendments and why?",
        "What are the common exclusion criteria across all trials?",
        "Which sponsors are running multinational trials?",
        "Summarize the amendment history for the Teva study",
        "Which studies use endoscopy as a primary endpoint?",
        "Compare inclusion criteria between UC-only and CD studies"
    ]

    st.markdown('<div class="section-header">Example Queries — click to load</div>', unsafe_allow_html=True)
    cols = st.columns(4)
    for i, eq in enumerate(example_queries):
        with cols[i % 4]:
            if st.button(eq, key=f"eq_{i}", use_container_width=True):
                st.session_state["active_query"] = eq
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # Text area — value driven from session state
    # No key= so Streamlit re-renders it fresh when active_query changes
    query = st.text_area(
        "Your question",
        value=st.session_state["active_query"],
        height=80,
        placeholder="Ask anything about the trials..."
    )

    col_ask, col_clear = st.columns([3, 1])
    with col_ask:
        ask_clicked = st.button("Ask Claude →", type="primary", use_container_width=True)
    with col_clear:
        if st.button("Clear", use_container_width=True):
            st.session_state["active_query"] = ""
            st.session_state.query_history = []
            st.rerun()

    if ask_clicked and query.strip():
        st.session_state["active_query"] = query  # persist before rerun
        with st.spinner("Claude is reading the protocols..."):
            trial_context = build_trial_context()
            system_prompt = f"""You are a clinical trial intelligence assistant for TrialAxis CRO, a specialized GI CRO.
You have deep knowledge of the following clinical trial protocols from the TMF database.
Answer questions accurately and concisely based on the trial data provided.
When comparing studies, use tables where helpful.
Always cite the study name and NCT ID when referencing specific data.

TRIAL DATABASE:
{trial_context}"""

            client = get_client()
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1000,
                system=system_prompt,
                messages=[{"role": "user", "content": query}]
            )
            answer = response.content[0].text
            st.session_state.query_history.append({"q": query, "a": answer})
            # Keep query visible after submission
            st.session_state["active_query"] = query

    if st.session_state.query_history:
        st.markdown('<div class="section-header">Conversation</div>', unsafe_allow_html=True)
        for item in reversed(st.session_state.query_history):
            st.markdown(f'<div class="chat-user">{item["q"]}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="chat-claude">{item["a"]}</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# MODULE 5 — DRAFT COMMUNICATIONS
# ══════════════════════════════════════════════════════════════════════════════
elif module == "✉️ Draft Communications":
    st.markdown("### Draft Communications")
    st.markdown("Select a flagged issue — Claude drafts a professional follow-up communication instantly.")

    selected = st.selectbox("Select Study", options=list(TRIALS.keys()),
        format_func=lambda x: f"{x} — {TRIALS[x]['short_name']} — {TRIALS[x]['drug']}")

    t = TRIALS[selected]
    flagged_docs = {doc: info for doc, info in t['tmf_documents'].items()
                   if info['status'] != "Complete"}

    if not flagged_docs:
        st.success("No outstanding items for this study.")
    else:
        doc_selected = st.selectbox("Select flagged document", options=list(flagged_docs.keys()),
            format_func=lambda x: f"{x} [{flagged_docs[x]['status']}]")

        col1, col2 = st.columns(2)
        with col1:
            recipient_type = st.selectbox("Draft to", ["Site Coordinator", "Principal Investigator", "Central Lab", "Sponsor Contact", "Vendor"])
            tone = st.selectbox("Tone", ["Professional / Formal", "Collaborative / Friendly", "Urgent"])
        with col2:
            recipient_email = st.text_input("Recipient email address", placeholder="e.g. coordinator@site.com")
            sender_name = st.text_input("Your name", placeholder="e.g. Jane Smith, TMF Associate")
            sender_email = st.text_input("Your email", placeholder="e.g. jsmith@trialaxis.com")

        if st.button("Draft Communication →", type="primary"):
            doc_info = flagged_docs[doc_selected]
            with st.spinner("Drafting..."):
                client = get_client()
                prompt = f"""Draft a professional email for a TrialAxis CRO TMF Associate.

Study: {t['drug']} — {t['short_name']} ({t['tax_id']})
Sponsor: {t['sponsor']}
Document: {doc_selected}
Status: {doc_info['status']}
Notes: {doc_info.get('version') or 'No additional notes'}
Recipient: {recipient_type}
Tone: {tone}

Write a complete email with:
- Subject line starting with "Subject:"
- Greeting, body, deadline (5 business days), sign-off
Sign from: {sender_name}, TrialAxis CRO TMF Associate ({sender_email})
Under 200 words. No placeholders."""

                response = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=1000,
                    messages=[{"role": "user", "content": prompt}]
                )
                draft = response.content[0].text
                subject = f"TMF Action Required — {doc_selected} | {t['short_name']}"
                for line in draft.split('\n'):
                    if line.lower().startswith('subject:'):
                        subject = line.replace('Subject:', '').replace('subject:', '').strip()
                        break
                st.session_state["email_draft"] = draft
                st.session_state["email_subject"] = subject
                st.session_state["email_recipient"] = recipient_email

        if "email_draft" in st.session_state:
            draft = st.session_state["email_draft"]
            subject = st.session_state.get("email_subject", "TMF Follow-up")
            st.markdown('<div class="section-header">Drafted Communication</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="email-box">{draft}</div>', unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            col1, col2 = st.columns([1, 3])
            with col1:
                today_str = datetime.now().strftime("%B %d, %Y")
                email_pdf = generate_email_pdf(
                    draft, f"{t['drug']} — {t['short_name']}", doc_selected, today_str
                )
                st.download_button(
                    "⬇ Download PDF", data=email_pdf,
                    file_name=f"TMF_Comms_{t['tax_id']}_{doc_selected.replace(' ','_')}.pdf",
                    mime="application/pdf", use_container_width=True
                )
            with col2:
                if st.button("↺ Clear Draft", use_container_width=True):
                    del st.session_state["email_draft"]
                    st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# MODULE 6 — EXECUTIVE SUMMARY
# ══════════════════════════════════════════════════════════════════════════════
elif module == "📋 Executive Summary":
    st.markdown("### Executive Summary Generator")
    st.markdown("Generate an audit-ready executive summary — for a single study or the full portfolio.")

    scope = st.radio("Summary scope", ["Single Study", "Full Portfolio"])

    if scope == "Single Study":
        selected = st.selectbox("Select Study", options=list(TRIALS.keys()),
            format_func=lambda x: f"{x} — {TRIALS[x]['short_name']} — {TRIALS[x]['drug']}")
        t = TRIALS[selected]
        context = f"Generate a summary for: {t['drug']} ({t['tax_id']})\n\n"
        context += build_trial_context()
        summary_title = f"{t['drug']} — {t['short_name']}"
    else:
        context = build_trial_context()
        summary_title = "Full GI Portfolio"

    audience = st.selectbox("Audience", ["VP of Clinical Operations", "Audit Team", "Sponsor Update", "Internal Team"])
    include_flags = st.checkbox("Include open flags", value=True)
    include_recommendations = st.checkbox("Include recommendations", value=True)

    if st.button("Generate Executive Summary →", type="primary"):
        with st.spinner("Claude is generating your summary..."):
            client = get_client()

            today = datetime.now().strftime("%B %d, %Y")
            prompt = f"""Generate a professional executive summary for {summary_title} as of {today}.
Audience: {audience}
Include flags: {include_flags}
Include recommendations: {include_recommendations}

Format as a clean executive summary with:
1. Portfolio/Study Overview (2-3 sentences)
2. TMF Completeness Status (table or bullets per study)
3. Critical Flags & Risks (if include_flags=True)
4. Amendment Activity
5. Upcoming Actions & Deadlines
6. Recommendations (if requested)

Keep it concise — this is a one-page summary for a senior audience.
Use professional clinical trial language appropriate for {audience}.

TRIAL DATA:
{context}"""

            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            summary = response.content[0].text
            st.session_state["exec_summary"] = summary
            st.session_state["exec_meta"] = {"title": summary_title, "today": today, "audience": audience}

        # Render outside spinner so it persists
        if "exec_summary" in st.session_state:
            summary = st.session_state["exec_summary"]
            meta = st.session_state["exec_meta"]

            # Header bar
            st.markdown(f"""
            <div style="background:#1B3A5C;border-radius:8px 8px 0 0;padding:0.75rem 1.5rem;">
                <div style="font-size:0.68rem;font-weight:700;color:rgba(255,255,255,0.5);text-transform:uppercase;letter-spacing:0.1em;">
                    Executive Summary &nbsp;·&nbsp; {meta['today']} &nbsp;·&nbsp; {meta['audience']}
                </div>
                <div style="font-size:0.9rem;font-weight:600;color:white;margin-top:2px">{meta['title']}</div>
            </div>
            """, unsafe_allow_html=True)

            # Content — rendered as markdown so tables, bold, headers all work
            with st.container():
                st.markdown(f"""
<div style="background:white;border:1px solid #E5E7EB;border-top:none;border-radius:0 0 8px 8px;padding:1.5rem 2rem;">
""", unsafe_allow_html=True)
                st.markdown(summary)
                st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            col1, col2 = st.columns([1, 3])
            with col1:
                pdf_bytes = generate_executive_summary_pdf(
                    summary, meta['title'], meta['audience'], meta['today']
                )
                st.download_button(
                    "⬇ Download PDF",
                    data=pdf_bytes,
                    file_name=f"ExecSummary_{meta['title'].replace(' ','_')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            with col2:
                if st.button("↺ Clear & Reset", use_container_width=True):
                    del st.session_state["exec_summary"]
                    st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# MODULE 7 — INGESTION TRACKER
# ══════════════════════════════════════════════════════════════════════════════
elif module == "📥 Ingestion Tracker":
    import csv
    from pathlib import Path as _Path

    _root        = _Path(__file__).parent
    _audit_log   = _root / "logs" / "ingestion_audit.log"
    _unreg_dir   = _root / "data" / "pdfs" / "unregistered"
    _inbox_dir   = _root / "TMF_Ingestion_Agent" / "inbox"

    # ── Load audit log ────────────────────────────────────────────────────────
    _audit_rows = []
    if _audit_log.exists():
        with open(_audit_log, newline="", encoding="utf-8") as _f:
            _reader = csv.DictReader(_f)
            _audit_rows = list(_reader)

    _ingested         = [r for r in _audit_rows if r.get("action") == "INGESTED"]
    _duplicates       = [r for r in _audit_rows if r.get("action") == "DUPLICATE"]
    _unregistered_log = [r for r in _audit_rows if r.get("action") == "UNREGISTERED"]
    _failed           = [r for r in _audit_rows if r.get("action") == "FAILED"]

    # ── Files on disk ─────────────────────────────────────────────────────────
    _unreg_files = sorted(_unreg_dir.glob("*.pdf")) if _unreg_dir.exists() else []
    _inbox_files = sorted(_inbox_dir.glob("*.pdf")) if _inbox_dir.exists() else []

    st.markdown("### 📥 Ingestion Tracker")
    st.markdown('<p style="color:#6B7280;font-size:0.85rem;margin-top:-0.5rem;">File pipeline status — inbox, unregistered holds, and full audit history</p>', unsafe_allow_html=True)
    st.markdown("---")

    # ── Metric row ────────────────────────────────────────────────────────────
    _mc1, _mc2, _mc3, _mc4, _mc5 = st.columns(5)
    _mc1.markdown(f'<div class="metric-card"><div class="metric-label">Ingested</div><div class="metric-value" style="color:#059669">{len(_ingested)}</div><div class="metric-sub">Added to portfolio</div></div>', unsafe_allow_html=True)
    _mc2.markdown(f'<div class="metric-card"><div class="metric-label">Awaiting Registry</div><div class="metric-value" style="color:#D97706">{len(_unreg_files)}</div><div class="metric-sub">In unregistered/</div></div>', unsafe_allow_html=True)
    _mc3.markdown(f'<div class="metric-card"><div class="metric-label">In Inbox</div><div class="metric-value" style="color:#1A3F6F">{len(_inbox_files)}</div><div class="metric-sub">Pending processing</div></div>', unsafe_allow_html=True)
    _mc4.markdown(f'<div class="metric-card"><div class="metric-label">Duplicates</div><div class="metric-value" style="color:#6B7280">{len(_duplicates)}</div><div class="metric-sub">Already indexed</div></div>', unsafe_allow_html=True)
    _mc5.markdown(f'<div class="metric-card"><div class="metric-label">Failed</div><div class="metric-value" style="color:#DC2626">{len(_failed)}</div><div class="metric-sub">Pipeline errors</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Unregistered files on disk (action required) ──────────────────────────
    st.markdown('<div class="section-header">⚠ Awaiting Registry Entry</div>', unsafe_allow_html=True)
    if _unreg_files:
        for _f in _unreg_files:
            _size_kb = _f.stat().st_size // 1024
            _matches = [r for r in reversed(_audit_rows) if r.get("source_file") == _f.name]
            _last    = _matches[0] if _matches else {}
            _doc_type = _last.get("document_type", "—")
            _ref      = _last.get("protocol_no", "—")
            _title    = _last.get("study_title") or "—"
            _sponsor  = _last.get("sponsor", "—")
            _ts       = _last.get("timestamp", "—")
            st.markdown(f"""
<div style="background:#FFFBEB;border:1px solid #FDE68A;border-left:4px solid #D97706;border-radius:8px;padding:0.9rem 1.2rem;margin-bottom:0.6rem;">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;">
    <div>
      <span style="font-weight:600;color:#92400E;font-size:0.9rem;">{_f.name}</span>
      <span style="margin-left:0.75rem;font-size:0.72rem;background:#FEF3C7;color:#B45309;padding:2px 8px;border-radius:10px;font-weight:600;">{_doc_type}</span>
    </div>
    <span style="font-size:0.75rem;color:#9CA3AF;">{_size_kb} KB</span>
  </div>
  <div style="font-size:0.8rem;color:#6B7280;margin-top:0.35rem;">
    <b>Title:</b> {_title} &nbsp;|&nbsp; <b>Ref:</b> {_ref} &nbsp;|&nbsp; <b>Sponsor:</b> {_sponsor}
  </div>
  <div style="font-size:0.75rem;color:#9CA3AF;margin-top:0.2rem;">Last attempted: {_ts} &nbsp;·&nbsp; Add to Excel registry and rerun ingest_protocol.py</div>
</div>""", unsafe_allow_html=True)
    else:
        st.markdown('<p style="color:#059669;font-size:0.85rem;">✓ No files awaiting registration</p>', unsafe_allow_html=True)

    # ── Inbox ─────────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">📬 Inbox — Pending Processing</div>', unsafe_allow_html=True)
    if _inbox_files:
        for _f in _inbox_files:
            _size_kb = _f.stat().st_size // 1024
            _mtime   = datetime.fromtimestamp(_f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            st.markdown(f"""
<div style="background:#EFF6FF;border:1px solid #BFDBFE;border-left:4px solid #1A3F6F;border-radius:8px;padding:0.9rem 1.2rem;margin-bottom:0.6rem;">
  <div style="display:flex;justify-content:space-between;">
    <span style="font-weight:600;color:#1E40AF;font-size:0.9rem;">{_f.name}</span>
    <span style="font-size:0.75rem;color:#9CA3AF;">{_size_kb} KB</span>
  </div>
  <div style="font-size:0.75rem;color:#9CA3AF;margin-top:0.2rem;">Arrived: {_mtime} &nbsp;·&nbsp; Run ingest_protocol.py to process</div>
</div>""", unsafe_allow_html=True)
    else:
        st.markdown('<p style="color:#6B7280;font-size:0.85rem;">Inbox is empty</p>', unsafe_allow_html=True)

    # ── Full audit log table ──────────────────────────────────────────────────
    st.markdown('<div class="section-header">📋 Audit Log</div>', unsafe_allow_html=True)
    if _audit_rows:
        _STATUS_COLOR = {
            "INGESTED":     ("#D1FAE5", "#059669"),
            "DUPLICATE":    ("#F3F4F6", "#6B7280"),
            "UNREGISTERED": ("#FEF3C7", "#D97706"),
            "FAILED":       ("#FEE2E2", "#DC2626"),
        }
        _df_rows = []
        for _r in reversed(_audit_rows):
            _action = _r.get("action", "")
            _df_rows.append({
                "Timestamp":    _r.get("timestamp", ""),
                "File":         _r.get("source_file", ""),
                "Type":         _r.get("document_type", ""),
                "Protocol Ref": _r.get("protocol_no", ""),
                "Study Title":  _r.get("study_title", ""),
                "Sponsor":      _r.get("sponsor", ""),
                "TAX ID":       _r.get("tax_id") or "—",
                "Status":       _action,
                "Location":     _r.get("final_location", "").replace(str(_root), "").lstrip("/\\"),
                "Error":        _r.get("error", ""),
            })
        _df = pd.DataFrame(_df_rows)

        def _color_status(val):
            _bg, _fg = _STATUS_COLOR.get(val, ("#F3F4F6", "#374151"))
            return f"background-color:{_bg};color:{_fg};font-weight:600;"

        st.dataframe(
            _df.style.map(_color_status, subset=["Status"]),
            use_container_width=True,
            hide_index=True,
            height=min(420, 55 + len(_df_rows) * 35),
        )

        _csv_bytes = _df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇ Export Audit Log (CSV)",
            data=_csv_bytes,
            file_name=f"ingestion_audit_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )
    else:
        st.info("No audit records yet. Run ingest_protocol.py to start tracking.")