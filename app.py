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
    for tax_id, t in TRIALS.items():
        context += f"{'='*60}\n"
        context += f"TAX STUDY ID: {tax_id}\n"
        context += f"STUDY NAME: {t['short_name']}\n"
        context += f"PROTOCOL NUMBER: {t.get('protocol_no', 'N/A')}\n"
        context += f"NCT ID: {t.get('nct_id', 'N/A')}\n"
        context += f"EUDRACT: {t.get('eudract', 'N/A')}\n"
        context += f"Drug: {t['drug']} | Sponsor: {t['sponsor']}\n"
        context += f"Phase: {t['phase']} | Condition: {t['condition']}\n"
        context += f"Design: {t['design']} | Duration: {t['duration']}\n"
        context += f"Countries: {', '.join(t['countries'])}\n"
        context += f"Protocol Date: {t['protocol_date']} | Latest Amendment: {t['latest_amendment']} ({t['latest_amendment_date']})\n"
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

    # TOP CTA — keep dashboard entry visible without scrolling
    st.markdown("<div style='height: 1.25rem;'></div>", unsafe_allow_html=True)
    cta_col1, cta_col2, cta_col3 = st.columns([0.04, 0.18, 0.78])
    with cta_col2:
        if st.button("ENTER DASHBOARD →", use_container_width=True, key="enter_dashboard_top"):
            st.session_state["entered"] = True
            st.rerun()
    st.markdown("<div style='height: 1.25rem;'></div>", unsafe_allow_html=True)

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
    st.markdown(f'<div class="metric-card"><div class="metric-label">Warnings</div><div class="metric-value" style="color:#D97706">{total_warning}</div><div class="metric-sub">Needs review</div></div>', unsafe_allow_html=True)

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
    for tax_id, t in TRIALS.items():
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
        for tax_id, t in TRIALS.items():
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
    st.markdown(
        "Ask questions across registered studies. The system automatically uses the right source: "
        "structured study data for portfolio comparisons and indexed protocol content for detailed protocol questions."
    )

    # Version marker clears old example-button/session history after this code update.
    QUERY_UI_VERSION = "query_ui_v4_auto_router_no_examples"
    if st.session_state.get("query_ui_version") != QUERY_UI_VERSION:
        st.session_state["query_ui_version"] = QUERY_UI_VERSION
        st.session_state["query_history"] = []
        st.session_state["query_input"] = ""

    if "query_history" not in st.session_state:
        st.session_state.query_history = []

    def clear_query_state():
        st.session_state.query_history = []
        st.session_state["query_input"] = ""

    def should_use_protocol_documents(user_query: str) -> bool:
        """
        Internal router only. Do not expose source choices to end users.
        Default to the structured trial database for comparisons and known fields.
        Use protocol-document RAG only for detailed protocol-text questions.
        """
        q = user_query.lower()

        structured_terms = [
            "compare", "comparison", "across studies", "across registered", "all studies",
            "primary endpoint", "primary endpoints", "primary objective", "primary objectives",
            "endpoint comparison", "objective comparison", "sponsor", "drug", "compound",
            "phase", "indication", "condition", "country", "countries", "protocol number",
            "tax study id", "tax id", "eudract", "nct", "amendment history",
            "latest amendment", "tmf completeness", "critical flags", "warnings", "risk level"
        ]
        if any(term in q for term in structured_terms):
            return False

        protocol_detail_terms = [
            "detailed inclusion", "detailed exclusion", "inclusion criteria", "exclusion criteria",
            "eligibility criteria", "visit schedule", "schedule of assessments", "assessment schedule",
            "concomitant medication", "concomitant medications", "prohibited medication",
            "prohibited medications", "dose interruption", "dose modification", "dose adjustment",
            "safety assessment", "safety assessments", "safety monitoring", "adverse event",
            "serious adverse event", "sae", "open label extension", "open-label extension", "ole",
            "randomization stratification", "screening period", "washout", "follow-up visit",
            "follow up visit", "laboratory assessments", "ecg", "endoscopy requirement"
        ]
        return any(term in q for term in protocol_detail_terms)

    query = st.text_area(
        "Your question",
        key="query_input",
        height=80,
        placeholder="Ask a question about the registered trials..."
    )

    col_ask, col_clear = st.columns([3, 1])
    with col_ask:
        ask_clicked = st.button("Ask Claude →", type="primary", use_container_width=True)
    with col_clear:
        st.button("Clear", use_container_width=True, on_click=clear_query_state)

    if ask_clicked and query.strip():
        with st.spinner("Claude is analyzing the trial intelligence system..."):
            trial_context = build_trial_context()
            use_protocol_documents = should_use_protocol_documents(query)

            if use_protocol_documents:
                try:
                    from query_engine import query_trials
                    answer = query_trials(query, conversation_history=[])
                    st.session_state.query_history.append({
                        "q": query,
                        "a": answer,
                        "source": "Protocol documents"
                    })
                    st.rerun()
                except Exception:
                    # Silent fallback to structured database so end users do not see internal routing details.
                    use_protocol_documents = False

            system_prompt = f"""You are a clinical trial intelligence assistant for TrialAxis CRO.
You have access to the structured TMF portfolio database below.

CRITICAL IDENTIFIER RULES:
- TAX Study ID (e.g. TAX-2026-001) is the internal TrialAxis registry key.
- Protocol Number (e.g. APD334-210) is the sponsor's protocol identifier.
- NCT ID (e.g. NCT04607837) is the ClinicalTrials.gov identifier.
- Do NOT confuse TAX Study ID with Protocol Number — they are different fields.
- When asked for a protocol number, return the Protocol Number field, not the TAX Study ID.
- Always cite the study name, TAX Study ID, and protocol number when available.

ANSWERING RULES:
- For comparison questions, use all registered studies in the structured trial database unless the user names specific studies.
- For questions about primary endpoints, primary objectives, sponsor, drug, phase, indication, countries, amendment history, TMF completeness, flags, or risk level, answer from the structured fields.
- Do not say primary endpoint/objective information is missing if it is populated in the trial database.
- If a field is genuinely blank or N/A in the structured database, say that the structured database does not contain that field.
- Use tables for cross-study comparisons.
- Do not mention internal data source routing, ChromaDB, RAG, or whether the answer came from structured data versus protocol documents.

TRIAL DATABASE:
{trial_context}"""

            client = get_client()
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1600,
                system=system_prompt,
                messages=[{"role": "user", "content": query}]
            )
            answer = response.content[0].text
            st.session_state.query_history.append({
                "q": query,
                "a": answer,
                "source": "Trial database"
            })
            st.rerun()

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
    st.markdown("Select a flagged issue — Claude drafts a controlled TMF follow-up communication.")

    # Controlled document-specific guidance keeps the email operationally specific
    # while still allowing Claude to adjust tone and wording.
    DOCUMENT_GUIDANCE = {
        "Investigator Agreement": {
            "ask": "a fully executed Investigator Agreement or confirmation that the signed agreement has been uploaded to the TMF",
            "why": "the TMF must contain evidence that the investigator has agreed to conduct the study according to the protocol and applicable requirements",
            "evidence": "signed Investigator Agreement or TMF upload confirmation"
        },
        "Ethics Committee Approval": {
            "ask": "the Ethics Committee / IRB approval letter, including approval date and approved document version where applicable",
            "why": "site activation and continued study conduct require documented ethics approval in the TMF",
            "evidence": "IRB/EC approval letter and approved version details"
        },
        "IND Approval": {
            "ask": "the applicable regulatory authorization, IND acknowledgement, or confirmation that the authorization is filed in the TMF",
            "why": "regulatory authorization must be documented before the TMF can be considered complete",
            "evidence": "regulatory approval / acknowledgement documentation"
        },
        "Informed Consent Form": {
            "ask": "the current approved Informed Consent Form and approval evidence for the version in use",
            "why": "the TMF must retain the approved consent form version used for participant consent",
            "evidence": "approved ICF version and approval documentation"
        },
        "Monitoring Plan": {
            "ask": "the current final Monitoring Plan or confirmation that the approved plan has been filed",
            "why": "the monitoring approach must be documented for oversight and inspection readiness",
            "evidence": "final Monitoring Plan or TMF filing confirmation"
        },
        "Delegation of Authority Log": {
            "ask": "the completed and signed Delegation of Authority Log, including current role assignments",
            "why": "delegation records are required to show who is authorized to perform study procedures",
            "evidence": "signed Delegation of Authority Log"
        },
        "Lab Certification": {
            "ask": "the current laboratory certification, accreditation, or equivalent qualification documentation",
            "why": "laboratory qualification evidence must be available in the TMF for vendor/site oversight",
            "evidence": "current lab certificate or accreditation document"
        },
        "Site Initiation Visit Report": {
            "ask": "the completed Site Initiation Visit report or confirmation of TMF upload",
            "why": "the TMF must document that the site was initiated and trained before study activities proceeded",
            "evidence": "completed SIV report or upload confirmation"
        },
        "Monitoring Visit Reports": {
            "ask": "the outstanding monitoring visit report(s), including visit date and finalization status",
            "why": "monitoring visit documentation is required to evidence site oversight and follow-up",
            "evidence": "finalized monitoring visit report(s)"
        },
    }

    def get_document_guidance(doc_name: str) -> dict:
        doc_lower = doc_name.lower()
        for key, value in DOCUMENT_GUIDANCE.items():
            if key.lower() in doc_lower:
                return value
        return {
            "ask": f"the outstanding TMF document: {doc_name}",
            "why": "the TMF must be complete and inspection-ready",
            "evidence": "document upload or confirmation of filing"
        }

    def clean_sender_signature(name: str, email: str) -> str:
        name = (name or "").strip()
        email = (email or "").strip()
        if name and email:
            return f"{name}, TrialAxis CRO TMF Associate ({email})"
        if name:
            return f"{name}, TrialAxis CRO TMF Associate"
        if email:
            return f"TrialAxis CRO TMF Associate ({email})"
        return "TrialAxis CRO TMF Associate"

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

        doc_info = flagged_docs[doc_selected]
        guidance = get_document_guidance(doc_selected)
        response_window = "within five business days"

        with st.expander("What this request will ask for", expanded=False):
            st.markdown(f"**Required evidence:** {guidance['evidence']}")
            st.markdown(f"**Reason:** {guidance['why']}")
            st.markdown(f"**Target response window:** {response_window}")

        if st.button("Draft Communication →", type="primary"):
            with st.spinner("Drafting..."):
                client = get_client()
                sender_signature = clean_sender_signature(sender_name, sender_email)
                doc_notes = doc_info.get('notes') or 'No additional notes'
                doc_version = doc_info.get('version') or 'N/A'
                doc_date = doc_info.get('date') or 'N/A'

                protocol_no = (t.get('protocol_no') or '').strip()
                protocol_line = f"Protocol Number: {protocol_no}\n" if protocol_no else ""

                prompt = f"""Draft a controlled single-study TMF follow-up email for a TrialAxis CRO TMF Associate.

Study: {t['short_name']} ({t['tax_id']})
{protocol_line}Sponsor: {t['sponsor']}
Drug: {t['drug']}
Document: {doc_selected}
Status: {doc_info['status']}
Document Version on File: {doc_version}
Document Date on File: {doc_date}
Notes: {doc_notes}
Recipient Role: {recipient_type}
Tone: {tone}
Target Response Window: {response_window}

Controlled request details:
- Ask for: {guidance['ask']}
- Reason: {guidance['why']}
- Evidence expected: {guidance['evidence']}

Style sample to follow closely:
Subject: TMF Document Request – Investigator Agreement | RELIEVE UCCD (TAX-2026-001)
Dear Site Coordinator,
I am following up regarding the Investigator Agreement for RELIEVE UCCD (TAX-2026-001), which is currently missing from the Trial Master File. Please provide the fully executed document or confirm that it has been uploaded to the TMF within five business days. This document is required to evidence investigator agreement to conduct the study in accordance with the protocol and applicable requirements.
Thank you for your support.
Best regards,
TMF Associate
TrialAxis CRO

Rules:
- This is always a single-study, one-document communication. Do not write a portfolio-level email.
- Write a complete email with a subject line starting with "Subject:".
- Keep the subject concise: document name, study name, and TAX Study ID.
- Do not include sponsor_ref, study reference, protocol reference, site number, or protocol number in the email unless a Protocol Number is explicitly provided above.
- Do not invent names, site numbers, approval dates, owners, or missing facts.
- Do not use placeholders such as [Name], [Site], [Date], or [Document].
- Avoid generic openings such as "I hope this message finds you well."
- Use the recipient role in the greeting, for example "Dear Site Coordinator," if no name is provided.
- Ask for response or upload within five business days.
- Use one concise body paragraph plus a short thank-you/sign-off. Avoid extra courtesy paragraphs such as "If you have any questions..." unless the tone is Collaborative / Friendly.
- Keep the email under 140 words.
- Sign from: {sender_signature}.
"""

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
    st.markdown("Generate a controlled, audit-ready executive summary — for a single study or the full portfolio.")

    def build_single_trial_context(tax_id: str, t: dict) -> str:
        """Build focused context for one selected study only."""
        crit, warn = count_flags(t)
        protocol_no = t.get("protocol_no") or t.get("sponsor_ref") or "N/A"
        context = f"""TMF INTELLIGENCE SYSTEM — SINGLE STUDY CONTEXT

TAX STUDY ID: {tax_id}
STUDY NAME: {t.get('short_name', 'N/A')}
PROTOCOL NUMBER: {protocol_no}
NCT ID: {t.get('nct_id', 'N/A')}
EUDRACT: {t.get('eudract', 'N/A')}
SPONSOR: {t.get('sponsor', 'N/A')}
DRUG: {t.get('drug', 'N/A')}
PHASE: {t.get('phase', 'N/A')}
CONDITION: {t.get('condition', 'N/A')}
DESIGN: {t.get('design', 'N/A')}
DURATION: {t.get('duration', 'N/A')}
COUNTRIES: {', '.join(t.get('countries', [])) or 'N/A'}
PROTOCOL DATE: {t.get('protocol_date', 'N/A')}
LATEST AMENDMENT: {t.get('latest_amendment', 'N/A')} ({t.get('latest_amendment_date', 'N/A')})
PATIENTS SCREENED: {t.get('patients_screened', 'N/A')}
PATIENTS RANDOMIZED: {t.get('patients_randomized', 'N/A')}

PRIMARY OBJECTIVE:
{t.get('primary_objective', 'N/A')}

PRIMARY ENDPOINT:
{t.get('primary_endpoint', 'N/A')}

TMF STATUS:
Completeness: {completeness_pct(t)}%
Critical flags: {crit}
Warnings: {warn}
Risk level: {t.get('risk_level', 'N/A')}
Notes: {t.get('notes', 'N/A')}

AMENDMENT HISTORY:
"""
        for a in t.get("amendment_history", []):
            context += f"- {a.get('version', 'N/A')} — {a.get('date', 'N/A')} ({a.get('patients_at_time', 'N/A')})\n"

        context += "\nTMF DOCUMENT STATUS:\n"
        for doc, info in t.get("tmf_documents", {}).items():
            context += (
                f"- {doc}: {info.get('status', 'N/A')}"
                f" | Date: {info.get('date') or 'N/A'}"
                f" | Version: {info.get('version') or 'N/A'}\n"
            )
        return context

    def build_portfolio_metrics_context() -> str:
        """Add calculated portfolio-level metrics so the summary uses dashboard-consistent numbers."""
        total_docs = sum(len(t.get("tmf_documents", {})) for t in TRIALS.values())
        complete_docs = sum(
            1 for t in TRIALS.values()
            for d in t.get("tmf_documents", {}).values()
            if d.get("status") == "Complete"
        )
        critical_docs = sum(count_flags(t)[0] for t in TRIALS.values())
        warning_docs = sum(count_flags(t)[1] for t in TRIALS.values())

        missing_by_doc = {}
        for t in TRIALS.values():
            for doc, info in t.get("tmf_documents", {}).items():
                if info.get("status") in ["Missing", "Expired", "Needs Review"]:
                    missing_by_doc[doc] = missing_by_doc.get(doc, 0) + 1
        common_missing = sorted(missing_by_doc.items(), key=lambda x: x[1], reverse=True)

        context = f"""\nPORTFOLIO CALCULATED METRICS:
Registered studies: {len(TRIALS)}
Total TMF document slots: {total_docs}
Complete TMF documents: {complete_docs}
Average TMF completeness: {avg_complete}%
Critical flags: {critical_docs}
Warnings: {warning_docs}

Most common outstanding document types:
"""
        for doc, count in common_missing[:10]:
            context += f"- {doc}: {count} studies\n"
        return context

    AUDIENCE_PROFILES = {
        "VP of Clinical Operations": {
            "focus": "operational risk, inspection readiness, portfolio priorities, and decisions needed this week",
            "style": "executive, concise, action-oriented"
        },
        "Audit Team": {
            "focus": "TMF completeness, missing or expired documents, amendment traceability, and evidence required for inspection readiness",
            "style": "controlled, factual, audit-ready"
        },
        "Sponsor Update": {
            "focus": "study status, document readiness, key risks, and clear next steps without internal system language",
            "style": "client-facing, polished, and non-defensive"
        },
        "Internal Team": {
            "focus": "workplan, owners, follow-up items, and immediate actions",
            "style": "practical, specific, and team-oriented"
        },
    }

    scope = st.radio("Summary scope", ["Single Study", "Full Portfolio"], horizontal=True)

    selected = None
    if scope == "Single Study":
        selected = st.selectbox(
            "Select Study",
            options=list(TRIALS.keys()),
            format_func=lambda x: f"{x} — {TRIALS[x]['short_name']} — {TRIALS[x]['drug']}"
        )
        t = TRIALS[selected]
        summary_title = f"{selected} — {t['short_name']}"
        data_context = build_single_trial_context(selected, t)
    else:
        summary_title = "Full GI / IBD TMF Portfolio"
        data_context = build_trial_context() + build_portfolio_metrics_context()

    audience = st.selectbox("Audience", list(AUDIENCE_PROFILES.keys()))
    include_flags = st.checkbox("Include open flags", value=True)
    include_recommendations = st.checkbox("Include recommendations", value=True)

    audience_profile = AUDIENCE_PROFILES[audience]
    with st.expander("Summary controls", expanded=False):
        st.markdown(f"**Audience focus:** {audience_profile['focus']}")
        st.markdown(f"**Style:** {audience_profile['style']}")
        st.markdown("**Source behavior:** single-study summaries use only the selected study; portfolio summaries use all registered studies.")

    if st.button("Generate Executive Summary →", type="primary"):
        with st.spinner("Claude is generating your summary..."):
            client = get_client()
            today = datetime.now().strftime("%B %d, %Y")

            prompt = f"""Generate a controlled executive summary for TrialAxis CRO as of {today}.

Scope: {scope}
Summary title: {summary_title}
Audience: {audience}
Audience focus: {audience_profile['focus']}
Writing style: {audience_profile['style']}
Include open flags: {include_flags}
Include recommendations: {include_recommendations}

Rules:
- Use only the trial data provided below.
- Do not mention Claude, AI routing, RAG, ChromaDB, trial_data.py, or implementation details.
- Do not invent site names, owners, due dates, approval dates, or missing facts.
- Use TAX Study ID and Protocol Number correctly; do not confuse them.
- If the scope is Single Study, do not summarize other studies.
- If Include open flags is False, keep flag detail minimal and focus on status.
- If Include recommendations is False, omit the recommendations section.
- If no explicit deadline is present in the data, say "No explicit deadline is available in the structured record" rather than inventing one.

Format:
1. Executive Snapshot — 2 to 3 sentences
2. Study / Portfolio Status — compact table or bullets
3. TMF Readiness — include completeness and open document risks
4. Amendment / Protocol Position — latest protocol version and amendment activity
5. Key Risks — only if Include open flags is True
6. Near-Term Actions — practical next steps based on the data
7. Recommendations — only if Include recommendations is True

Keep this to approximately one page for a senior clinical operations audience.

TRIAL DATA:
{data_context}
"""

            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1300,
                messages=[{"role": "user", "content": prompt}]
            )
            summary = response.content[0].text
            st.session_state["exec_summary"] = summary
            st.session_state["exec_meta"] = {
                "title": summary_title,
                "today": today,
                "audience": audience,
                "scope": scope,
            }

    if "exec_summary" in st.session_state:
        summary = st.session_state["exec_summary"]
        meta = st.session_state["exec_meta"]

        st.markdown(f"""
        <div style="background:#1B3A5C;border-radius:8px 8px 0 0;padding:0.75rem 1.5rem;">
            <div style="font-size:0.68rem;font-weight:700;color:rgba(255,255,255,0.5);text-transform:uppercase;letter-spacing:0.1em;">
                Executive Summary &nbsp;·&nbsp; {meta['today']} &nbsp;·&nbsp; {meta['audience']} &nbsp;·&nbsp; {meta.get('scope','')}
            </div>
            <div style="font-size:0.9rem;font-weight:600;color:white;margin-top:2px">{meta['title']}</div>
        </div>
        """, unsafe_allow_html=True)

        with st.container():
            st.markdown("""
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
                file_name=f"ExecSummary_{meta['title'].replace(' ','_').replace('/','-')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        with col2:
            if st.button("↺ Clear & Reset", use_container_width=True):
                for key in ["exec_summary", "exec_meta"]:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# MODULE 7 — INGESTION TRACKER
# ══════════════════════════════════════════════════════════════════════════════
elif module == "📥 Ingestion Tracker":
    import csv
    import html
    from pathlib import Path as _Path

    _root        = _Path(__file__).parent
    _audit_log   = _root / "logs" / "ingestion_audit.log"
    _registered_dir = _root / "data" / "pdfs"
    _unreg_dir   = _registered_dir / "unregistered"
    _incoming_dir = _registered_dir / "incoming"
    _inbox_dir   = _root / "TMF_Ingestion_Agent" / "inbox"
    _excel_file  = _root / "data" / "exports" / "eTMF_Status_Report.xlsx"

    def _safe(value) -> str:
        return html.escape(str(value or "—"))

    def _action(row: dict) -> str:
        return str(row.get("action", "")).strip().upper()

    def _relative(path: _Path) -> str:
        try:
            return str(path.relative_to(_root))
        except Exception:
            return str(path)

    # ── Load audit log ────────────────────────────────────────────────────────
    _audit_rows = []
    if _audit_log.exists():
        with open(_audit_log, newline="", encoding="utf-8") as _f:
            _reader = csv.DictReader(_f)
            _audit_rows = list(_reader)

    _ingested_rows     = [r for r in _audit_rows if _action(r) == "INGESTED"]
    _duplicates        = [r for r in _audit_rows if _action(r) == "DUPLICATE"]
    _unregistered_rows = [r for r in _audit_rows if _action(r) == "UNREGISTERED"]
    _failed            = [r for r in _audit_rows if _action(r) == "FAILED"]

    # Latest audit row by source file, useful for showing current known reason/status
    _latest_by_file = {}
    for _r in _audit_rows:
        _name = _r.get("source_file", "")
        if _name:
            _latest_by_file[_name] = _r

    # ── Files on disk ─────────────────────────────────────────────────────────
    _registered_files = sorted(_registered_dir.glob("*.pdf")) if _registered_dir.exists() else []
    _unreg_files      = sorted(_unreg_dir.glob("*.pdf")) if _unreg_dir.exists() else []
    _incoming_files   = sorted(_incoming_dir.glob("*.pdf")) if _incoming_dir.exists() else []
    _inbox_files      = sorted(_inbox_dir.glob("*.pdf")) if _inbox_dir.exists() else []

    st.markdown("### 📥 Governed Ingestion Tracker")
    st.markdown(
        '<p style="color:#6B7280;font-size:0.85rem;margin-top:-0.5rem;">Governed protocol intake status — registry validation, file queues, and audit history.</p>',
        unsafe_allow_html=True
    )
    st.markdown("---")

    with st.expander("How to process new documents", expanded=False):
        st.markdown("""
**Governance rule:** the pipeline can identify, validate, route, and index documents — but it cannot create a TAX Study ID or update the Excel registry.

**Operational flow:**
1. Drop new PDFs into `TMF_Ingestion_Agent/inbox/`.
2. Run `python TMF_Ingestion_Agent/ingest_protocol.py` from the project root.
3. Registered studies are renamed and moved into `data/pdfs/`.
4. Unregistered studies are moved to `data/pdfs/unregistered/` and held there until the Excel registry is updated.
5. Rerun the ingest command after the registry is updated; held files are rechecked automatically.
""")
        if not _excel_file.exists():
            st.warning("Excel registry not found at data/exports/eTMF_Status_Report.xlsx. Registry matching will fail until this file is present.")

    # ── Metric row ────────────────────────────────────────────────────────────
    _mc1, _mc2, _mc3, _mc4, _mc5 = st.columns(5)
    _mc1.markdown(f'<div class="metric-card"><div class="metric-label">Registered PDFs</div><div class="metric-value" style="color:#059669">{len(_registered_files)}</div><div class="metric-sub">In data/pdfs</div></div>', unsafe_allow_html=True)
    _mc2.markdown(f'<div class="metric-card"><div class="metric-label">Awaiting Registry Files</div><div class="metric-value" style="color:#D97706">{len(_unreg_files)}</div><div class="metric-sub">Unique files held</div></div>', unsafe_allow_html=True)
    _mc3.markdown(f'<div class="metric-card"><div class="metric-label">Inbox</div><div class="metric-value" style="color:#1A3F6F">{len(_inbox_files)}</div><div class="metric-sub">Pending intake</div></div>', unsafe_allow_html=True)
    _mc4.markdown(f'<div class="metric-card"><div class="metric-label">Duplicate Attempts</div><div class="metric-value" style="color:#6B7280">{len(_duplicates)}</div><div class="metric-sub">Audit log rows</div></div>', unsafe_allow_html=True)
    _mc5.markdown(f'<div class="metric-card"><div class="metric-label">Failed Attempts</div><div class="metric-value" style="color:#DC2626">{len(_failed)}</div><div class="metric-sub">Audit log rows</div></div>', unsafe_allow_html=True)

    st.caption("Queue counts show current unique files on disk. Duplicate and failed counts are audit-log attempts, so repeated rechecks are counted as separate audit events.")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Current queues ────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Current File Queues</div>', unsafe_allow_html=True)

    q1, q2 = st.columns(2)
    with q1:
        st.markdown("**Awaiting Registry Entry — Unique Files**")
        if _unreg_files:
            for _f in _unreg_files:
                _size_kb = _f.stat().st_size // 1024
                _last = _latest_by_file.get(_f.name, {})
                _doc_type = _last.get("document_type", "—")
                _ref      = _last.get("protocol_no", "—")
                _title    = _last.get("study_title") or "—"
                _sponsor  = _last.get("sponsor", "—")
                _ts       = _last.get("timestamp", "—")
                _error    = _last.get("error", "No registry match recorded")
                st.markdown(f"""
<div style="background:#FFFBEB;border:1px solid #FDE68A;border-left:4px solid #D97706;border-radius:8px;padding:0.9rem 1.2rem;margin-bottom:0.6rem;">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;">
    <div>
      <span style="font-weight:600;color:#92400E;font-size:0.9rem;">{_safe(_f.name)}</span>
      <span style="margin-left:0.75rem;font-size:0.72rem;background:#FEF3C7;color:#B45309;padding:2px 8px;border-radius:10px;font-weight:600;">{_safe(_doc_type)}</span>
    </div>
    <span style="font-size:0.75rem;color:#9CA3AF;">{_size_kb} KB</span>
  </div>
  <div style="font-size:0.8rem;color:#6B7280;margin-top:0.35rem;">
    <b>Title:</b> {_safe(_title)}<br>
    <b>Ref:</b> {_safe(_ref)} &nbsp;|&nbsp; <b>Sponsor:</b> {_safe(_sponsor)}
  </div>
  <div style="font-size:0.75rem;color:#9CA3AF;margin-top:0.25rem;">Last attempted: {_safe(_ts)}</div>
  <div style="font-size:0.75rem;color:#92400E;margin-top:0.25rem;"><b>Action:</b> Add this study to the Excel registry, then rerun ingest_protocol.py.</div>
  <div style="font-size:0.72rem;color:#9CA3AF;margin-top:0.25rem;">{_safe(_error)}</div>
</div>""", unsafe_allow_html=True)
        else:
            st.markdown('<p style="color:#059669;font-size:0.85rem;">✓ No files awaiting registration</p>', unsafe_allow_html=True)

    with q2:
        st.markdown("**Inbox / Incoming**")
        if _inbox_files or _incoming_files:
            for _f in _inbox_files + _incoming_files:
                _size_kb = _f.stat().st_size // 1024
                _mtime   = datetime.fromtimestamp(_f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                _queue   = "Inbox" if _f.parent == _inbox_dir else "Incoming staging"
                st.markdown(f"""
<div style="background:#EFF6FF;border:1px solid #BFDBFE;border-left:4px solid #1A3F6F;border-radius:8px;padding:0.9rem 1.2rem;margin-bottom:0.6rem;">
  <div style="display:flex;justify-content:space-between;">
    <span style="font-weight:600;color:#1E40AF;font-size:0.9rem;">{_safe(_f.name)}</span>
    <span style="font-size:0.75rem;color:#9CA3AF;">{_size_kb} KB</span>
  </div>
  <div style="font-size:0.75rem;color:#9CA3AF;margin-top:0.2rem;">{_queue} · Modified: {_mtime}</div>
</div>""", unsafe_allow_html=True)
        else:
            st.markdown('<p style="color:#6B7280;font-size:0.85rem;">Inbox and incoming staging are empty</p>', unsafe_allow_html=True)

    # ── Registered PDF library ────────────────────────────────────────────────
    with st.expander("Registered PDF Library", expanded=False):
        if _registered_files:
            _registered_rows = []
            for _f in _registered_files:
                _registered_rows.append({
                    "File": _f.name,
                    "Size KB": _f.stat().st_size // 1024,
                    "Modified": datetime.fromtimestamp(_f.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
                    "Location": _relative(_f),
                })
            st.dataframe(pd.DataFrame(_registered_rows), use_container_width=True, hide_index=True)
        else:
            st.info("No registered PDFs found in data/pdfs/.")

    # ── Full audit log table ──────────────────────────────────────────────────
    st.markdown('<div class="section-header">Audit History — Attempt-Level Log</div>', unsafe_allow_html=True)
    if _audit_rows:
        _STATUS_COLOR = {
            "INGESTED":     ("#D1FAE5", "#059669"),
            "DUPLICATE":    ("#F3F4F6", "#6B7280"),
            "UNREGISTERED": ("#FEF3C7", "#D97706"),
            "FAILED":       ("#FEE2E2", "#DC2626"),
        }
        _df_rows = []
        for _r in reversed(_audit_rows):
            _df_rows.append({
                "Timestamp":    _r.get("timestamp", ""),
                "File":         _r.get("source_file", ""),
                "Type":         _r.get("document_type", ""),
                "Protocol Ref": _r.get("protocol_no", ""),
                "Study Title":  _r.get("study_title", ""),
                "Sponsor":      _r.get("sponsor", ""),
                "TAX ID":       _r.get("tax_id") or "—",
                "Status":       _action(_r),
                "Location":     _r.get("final_location", "").replace(str(_root), "").lstrip("/\\"),
                "Error":        _r.get("error", ""),
            })
        _df = pd.DataFrame(_df_rows)

        _available_statuses = [s for s in ["INGESTED", "DUPLICATE", "UNREGISTERED", "FAILED"] if s in set(_df["Status"])]
        _selected_statuses = st.multiselect(
            "Filter audit status (attempt-level)",
            options=_available_statuses,
            default=_available_statuses,
        )
        if _selected_statuses:
            _display_df = _df[_df["Status"].isin(_selected_statuses)].copy()
        else:
            _display_df = _df.copy()

        def _color_status(val):
            _bg, _fg = _STATUS_COLOR.get(val, ("#F3F4F6", "#374151"))
            return f"background-color:{_bg};color:{_fg};font-weight:600;"

        st.dataframe(
            _display_df.style.map(_color_status, subset=["Status"]),
            use_container_width=True,
            hide_index=True,
            height=min(460, 70 + max(len(_display_df), 1) * 35),
        )

        _csv_bytes = _display_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇ Export Filtered Audit Log (CSV)",
            data=_csv_bytes,
            file_name=f"ingestion_audit_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )
    else:
        st.info("No audit records yet. Run ingest_protocol.py to start tracking.")
