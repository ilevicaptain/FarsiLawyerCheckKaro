import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from datetime import date

from backend import analyze_lawyer

# ── Page config ───────────────────────────────────────────────────────
st.set_page_config(
    page_title="Nyaypath — Lawyer Analytics",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_URL = "https://webapi.ecourtsindia.com/api/partner/search"
API_KEY = st.secrets["ECI_API_KEY"]

# ── CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,400;1,9..144,300&family=DM+Sans:wght@300;400;500&display=swap');

/* ── Base font ── */
html, body, [class*="css"], .stMarkdown, .stText,
.stRadio label, .stSlider label, .stDateInput label,
.stTextInput label, .stButton button, .stCaption {
    font-family: 'DM Sans', sans-serif !important;
    color-scheme: light !important;
}

/* ── Force light mode always — prevent system dark mode from inverting ── */
html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"],
.main, .block-container, [data-testid="stVerticalBlock"] {
    background-color: #ffffff !important;
    color: #1A1814 !important;
    color-scheme: light !important;
}

/* ── Inputs and widgets stay light ── */
.stTextInput > div > div,
.stTextInput > div > div > input,
.stDateInput > div > div > input,
[data-baseweb="input"], [data-baseweb="base-input"] {
    background-color: #ffffff !important;
    color: #1A1814 !important;
}

/* ── Tabs stay light ── */
[data-baseweb="tab-panel"],
[data-baseweb="tab-list"],
[data-baseweb="tab"] {
    background-color: #ffffff !important;
    color: #3D3A34 !important;
}

/* ── Dataframe stays light ── */
[data-testid="stDataFrame"] {
    background-color: #ffffff !important;
}

/* ── Hide only footer ── */
footer { visibility: hidden !important; }

/* ── Fix white header bar — match page background ── */
header[data-testid="stHeader"] {
    background-color: #ffffff !important;
    border-bottom: 1px solid rgba(26,24,20,0.06) !important;
}

/* ── Sidebar background — every child element matches ── */
section[data-testid="stSidebar"],
section[data-testid="stSidebar"] > div,
section[data-testid="stSidebar"] > div > div,
section[data-testid="stSidebar"] [data-testid="stVerticalBlock"],
section[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"],
section[data-testid="stSidebar"] .stMarkdown,
section[data-testid="stSidebar"] .element-container,
section[data-testid="stSidebar"] .stRadio,
section[data-testid="stSidebar"] .stDateInput,
section[data-testid="stSidebar"] .stSlider,
section[data-testid="stSidebar"] hr {
    background-color: #F5F0E8 !important;
    border-color: rgba(26,24,20,0.1) !important;
}

/* ── Sidebar text ── */
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] .stRadio label,
section[data-testid="stSidebar"] .stCaption,
section[data-testid="stSidebar"] p {
    color: #3D3A34 !important;
    font-size: 13px !important;
}

/* ── Sidebar date inputs — sand background not white ── */
section[data-testid="stSidebar"] .stDateInput > div > div,
section[data-testid="stSidebar"] .stDateInput input,
section[data-testid="stSidebar"] [data-baseweb="input"],
section[data-testid="stSidebar"] [data-baseweb="base-input"],
section[data-testid="stSidebar"] [data-baseweb="input"] > div {
    background-color: #EDE6D6 !important;
    border-color: rgba(26,24,20,0.12) !important;
    color: #1A1814 !important;
}

/* ── Main area padding — enough to clear the sticky header ── */
.block-container {
    padding-top: 5rem !important;
    padding-bottom: 3rem !important;
}

/* ── Page title ── */
.page-title {
    font-family: 'Fraunces', serif !important;
    font-size: 36px;
    font-weight: 300;
    color: #1A1814;
    line-height: 1.2;
    margin-bottom: 4px;
}
.page-title em { font-style: italic; color: #2A6B5E; }
.page-sub {
    font-size: 14px;
    color: #7A7368;
    margin-bottom: 24px;
}

/* ── Logo in sidebar ── */
.ny-logo {
    font-family: 'Fraunces', serif !important;
    font-size: 24px;
    font-weight: 300;
    color: #1A1814;
    letter-spacing: -0.3px;
}
.ny-logo span { color: #2A6B5E; }
.ny-tagline {
    font-size: 11px;
    color: #7A7368;
    margin-top: 2px;
    margin-bottom: 16px;
}

/* ── Lawyer hero card ── */
.lawyer-card {
    background: linear-gradient(135deg, #2A6B5E 0%, #1A4A40 100%);
    border-radius: 18px;
    padding: 28px 32px;
    color: white;
    margin-bottom: 20px;
}
.lc-name {
    font-family: 'Fraunces', serif;
    font-size: 26px;
    font-weight: 300;
    margin-bottom: 4px;
    line-height: 1.2;
}
.lc-meta { font-size: 12px; opacity: 0.7; margin-bottom: 16px; }
.lc-pills { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 18px; }
.lc-pill {
    background: rgba(255,255,255,0.15);
    border: 1px solid rgba(255,255,255,0.2);
    border-radius: 50px;
    padding: 3px 11px;
    font-size: 11px;
}
.lc-quick-stats { display: flex; gap: 28px; flex-wrap: wrap; margin-bottom: 20px; }
.lc-stat-val {
    font-family: 'Fraunces', serif;
    font-size: 26px;
    font-weight: 300;
    line-height: 1;
}
.lc-stat-label { font-size: 10px; opacity: 0.6; margin-top: 2px; }
.score-strip { display: flex; gap: 10px; flex-wrap: wrap; }
.score-badge {
    background: rgba(255,255,255,0.12);
    border: 1px solid rgba(255,255,255,0.18);
    border-radius: 10px;
    padding: 10px 16px;
    text-align: center;
    min-width: 85px;
}
.score-badge-val {
    font-family: 'Fraunces', serif;
    font-size: 20px;
    font-weight: 300;
}
.score-badge-label { font-size: 10px; opacity: 0.65; margin-top: 2px; }
.overall-circle {
    text-align: center;
    background: rgba(255,255,255,0.1);
    border-radius: 14px;
    padding: 16px 20px;
    min-width: 110px;
}
.overall-num {
    font-family: 'Fraunces', serif;
    font-size: 48px;
    font-weight: 300;
    line-height: 1;
}

/* ── Data quality tags ── */
.dq-good        { color: #6EE7B7; font-size: 11px; font-weight: 500; }
.dq-limited     { color: #FCD34D; font-size: 11px; font-weight: 500; }
.dq-insufficient{ color: #FCA5A5; font-size: 11px; font-weight: 500; }

/* ── KPI cards ── */
.kpi-card {
    background: #ffffff;
    border: 1px solid rgba(26,24,20,0.09);
    border-radius: 12px;
    padding: 14px 16px;
    margin-bottom: 10px;
    min-height: 90px;
    overflow: hidden;
}
.kpi-val {
    font-family: 'Fraunces', serif;
    font-size: 22px;
    font-weight: 300;
    color: #1A1814;
    line-height: 1;
    margin-bottom: 4px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.kpi-label {
    font-size: 11px;
    color: #7A7368;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.kpi-note {
    font-size: 11px;
    color: #2A6B5E;
    margin-top: 3px;
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

/* ── Section title ── */
.sec-title {
    font-family: 'Fraunces', serif;
    font-size: 20px;
    font-weight: 300;
    color: #1A1814;
    margin: 24px 0 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid rgba(26,24,20,0.08);
}

/* ── Verdict card ── */
.verdict-card {
    background: #1A1814;
    border-radius: 18px;
    padding: 32px;
    color: white;
    text-align: center;
    margin-bottom: 20px;
}
.verdict-eyebrow {
    font-size: 11px;
    letter-spacing: 0.1em;
    color: rgba(255,255,255,0.4);
    margin-bottom: 10px;
}
.verdict-winner {
    font-family: 'Fraunces', serif;
    font-size: 30px;
    font-weight: 300;
    margin-bottom: 10px;
}
.verdict-winner em { font-style: italic; color: #4A9B8A; }
.verdict-reason {
    font-size: 13px;
    color: rgba(255,255,255,0.65);
    line-height: 1.6;
    max-width: 560px;
    margin: 0 auto 20px;
}
.verdict-scores {
    display: flex;
    gap: 40px;
    justify-content: center;
    align-items: center;
}
.vs-num {
    font-family: 'Fraunces', serif;
    font-size: 42px;
    font-weight: 300;
    line-height: 1;
}
.vs-name { font-size: 11px; color: rgba(255,255,255,0.5); margin-top: 4px; }
.vs-divider {
    font-family: 'Fraunces', serif;
    font-size: 20px;
    color: rgba(255,255,255,0.2);
}
.verdict-footnote {
    font-size: 10px;
    color: rgba(255,255,255,0.25);
    margin-top: 16px;
}

/* ── Note bar ── */
.ny-note {
    background: #E8F2EF;
    border-left: 3px solid #2A6B5E;
    border-radius: 0 8px 8px 0;
    padding: 10px 14px;
    font-size: 12px;
    color: #1F5246;
    margin-bottom: 16px;
    margin-top: 8px;
}

/* ── Search input ── */
.stTextInput > div > div > input {
    border-radius: 10px !important;
    border: 1.5px solid rgba(26,24,20,0.15) !important;
    padding: 10px 14px !important;
    font-size: 14px !important;
    font-family: 'DM Sans', sans-serif !important;
}
.stTextInput > div > div > input:focus {
    border-color: #2A6B5E !important;
    box-shadow: 0 0 0 2px rgba(42,107,94,0.12) !important;
}

/* ── Primary button ── */
.stButton > button[kind="primary"] {
    background: #2A6B5E !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 500 !important;
    font-size: 14px !important;
    padding: 10px 24px !important;
    width: 100% !important;
}
.stButton > button[kind="primary"]:hover {
    background: #1F5246 !important;
}

/* ── Divider ── */
hr { border-color: rgba(26,24,20,0.08) !important; }
</style>
""", unsafe_allow_html=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONSTANTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TEAL    = "#2A6B5E"
AMBER   = "#C17B2A"
NEUTRAL = "#B8B0A2"

PLOTLY_BASE = dict(
    font_family="DM Sans",
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=16, r=16, t=40, b=16),
    title_font_size=13,
    title_font_color="#1A1814",
    font_color="#3D3A34",
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def dq_info(dq: str):
    if "Good" in dq:    return "dq-good",        "✓ Good data"
    if "Limited" in dq: return "dq-limited",     "⚠ Limited data"
    return "dq-insufficient", "⚠ Insufficient"

def compute_overall(scores: dict) -> int:
    keys = ["competence", "availability", "case_speed", "activity"]
    return round(sum(scores.get(k, 0) for k in keys) / len(keys))

def top_domain(profile: dict) -> str:
    db = profile["case_types"]["domain_breakdown"]
    if not db:
        return "—"
    return max(db, key=lambda k: db[k]["count"])


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RENDER: LAWYER HERO CARD
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def render_lawyer_card(profile: dict, scores: dict):
    ident   = profile["identity"]
    vol     = profile["volume"]
    out     = profile["outcomes"]
    act     = profile["activity"]
    overall = compute_overall(scores)
    dq_cls, dq_txt = dq_info(scores["data_quality"])
    domain  = top_domain(profile)

    courts_txt = ", ".join(ident["all_courts"][:3])
    if len(ident["all_courts"]) > 3:
        courts_txt += f"  +{len(ident['all_courts'])-3} more"

    active_pill = "<span class='lc-pill'>Active</span>" \
        if (act["days_since_last_appearance"] or 999) <= 90 else ""
    days_shown = act["days_since_last_appearance"] \
        if act["days_since_last_appearance"] is not None else "—"

    st.markdown(f"""
    <div class="lawyer-card">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap;">
        <div style="flex:1;min-width:220px;">
          <div class="lc-name">{ident['normalised_name']}</div>
          <div class="lc-meta">
            {ident['highest_court_tier']}
            &nbsp;·&nbsp; First case: {ident['first_case_on_record'] or '—'}
            &nbsp;·&nbsp; <span class="{dq_cls}">{dq_txt}</span>
          </div>
          <div class="lc-pills">
            <span class="lc-pill">{domain}</span>
            <span class="lc-pill">{ident['total_courts']} courts</span>
            <span class="lc-pill">{vol['total_petitioner_cases']} cases</span>
            {active_pill}
          </div>
          <div class="lc-quick-stats">
            <div>
              <div class="lc-stat-val">{out['disposed_pct']}%</div>
              <div class="lc-stat-label">Disposal rate</div>
            </div>
            <div>
              <div class="lc-stat-val">{vol['current_year_count']}</div>
              <div class="lc-stat-label">Cases {pd.Timestamp.today().year}</div>
            </div>
            <div>
              <div class="lc-stat-val">{out['pending_count']}</div>
              <div class="lc-stat-label">Open cases</div>
            </div>
            <div>
              <div class="lc-stat-val">{days_shown}</div>
              <div class="lc-stat-label">Days since hearing</div>
            </div>
          </div>
          <div class="score-strip">
            <div class="score-badge">
              <div class="score-badge-val">{scores['competence']}</div>
              <div class="score-badge-label">Competence</div>
            </div>
            <div class="score-badge">
              <div class="score-badge-val">{scores['availability']}</div>
              <div class="score-badge-label">Availability</div>
            </div>
            <div class="score-badge">
              <div class="score-badge-val">{scores['case_speed']}</div>
              <div class="score-badge-label">Case Speed</div>
            </div>
            <div class="score-badge">
              <div class="score-badge-val">{scores['activity']}</div>
              <div class="score-badge-label">Activity</div>
            </div>
          </div>
        </div>
        <div class="overall-circle">
          <div style="font-size:10px;opacity:0.55;letter-spacing:0.07em;margin-bottom:6px;">OVERALL</div>
          <div class="overall-num">{overall}</div>
          <div style="font-size:10px;opacity:0.4;">/100</div>
        </div>
      </div>
      <div style="margin-top:14px;font-size:11px;opacity:0.5;">
        Courts: {courts_txt}
      </div>
    </div>
    """, unsafe_allow_html=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RENDER: KPI GRID
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def render_kpi_grid(profile: dict, compact: bool = False):
    v  = profile["volume"]
    o  = profile["outcomes"]
    a  = profile["activity"]
    yr = pd.Timestamp.today().year

    items = [
        (v["total_petitioner_cases"],
         "Total cases",
         f"Last 12m: {v['last_12_months_count']}"),
        (f"{o['disposed_pct']}%",
         "Disposal rate",
         f"{o['disposed_count']} of {v['total_petitioner_cases']}"),
        (f"{int(o['median_case_duration_days']) if o['median_case_duration_days'] else '—'} days",
         "Median duration",
         "Disposed cases only"),
        (a["next_scheduled_hearing"] or "—",
         "Next hearing",
         f"Open: {o['pending_count']} cases"),
        (v["current_year_count"],
         f"Cases in {yr}",
         f"Last year ({yr-1}): {v['last_year_count']}"),
        (f"{o['with_judgments_pct']}%",
         "With judgment",
         f"{o['with_judgments_count']} cases"),
        (f"{o['avg_hearings_per_case'] or '—'}",
         "Avg hearings",
         "Lower = fewer adj."),
        (a["last_court_appearance"] or "—",
         "Last appearance",
         f"Days since: {a['days_since_last_appearance'] or '—'}"),
    ]

    ncols = 2 if compact else 4
    cols = st.columns(ncols)
    for i, (val, label, note) in enumerate(items):
        with cols[i % ncols]:
            st.markdown(f"""
            <div class="kpi-card">
              <div class="kpi-val">{val}</div>
              <div class="kpi-label">{label}</div>
              <div class="kpi-note">{note}</div>
            </div>
            """, unsafe_allow_html=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RENDER: IDENTITY EXPANDER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def render_identity(profile: dict):
    ident = profile["identity"]
    with st.expander("Identity & all courts"):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**Highest court tier:** {ident['highest_court_tier']}")
            st.markdown(f"**First case on record:** {ident['first_case_on_record'] or '—'}")
            st.markdown(f"**States:** {', '.join(ident['states_covered']) if ident['states_covered'] else '—'}")
            st.markdown(f"**Districts:** {', '.join(ident['districts_covered']) if ident['districts_covered'] else '—'}")
        with c2:
            st.markdown(f"**All courts ({ident['total_courts']}):**")
            for court in ident["all_courts"]:
                st.markdown(f"&nbsp;&nbsp;• {court}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RENDER: CHARTS (tabbed)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def render_charts(profile: dict, scores: dict, label: str):
    v  = profile["volume"]
    o  = profile["outcomes"]
    ct = profile["case_types"]

    t1, t2, t3, t4 = st.tabs(["Yearly trend", "Case types", "Outcomes", "Score radar"])

    with t1:
        if v["year_by_year"]:
            ydf = pd.DataFrame({
                "Year":  list(v["year_by_year"].keys()),
                "Cases": list(v["year_by_year"].values()),
            }).sort_values("Year")
            fig = px.bar(ydf, x="Year", y="Cases",
                         title="Petitioner cases by year",
                         color_discrete_sequence=[TEAL])
            fig.update_layout(**PLOTLY_BASE)
            fig.update_traces(marker_line_width=0)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No yearly data available.")

    with t2:
        ctb = ct.get("case_type_breakdown", [])
        if ctb:
            ctdf = pd.DataFrame(ctb).head(12)
            fig = px.bar(ctdf, x="count", y="full_name", orientation="h",
                         title="Case types (decoded)", color="domain",
                         color_discrete_map={
                             "Family": TEAL, "Criminal": "#D94F3A",
                             "Civil": "#185FA5", "Constitutional": "#534AB7",
                             "Property": AMBER, "Other": NEUTRAL,
                         })
            fig.update_layout(**PLOTLY_BASE, yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig, use_container_width=True)

        db = ct.get("domain_breakdown", {})
        if db:
            domdf = pd.DataFrame([
                {"Domain": k, "Cases": v2["count"]} for k, v2 in db.items()
            ])
            fig2 = px.pie(domdf, names="Domain", values="Cases",
                          hole=0.55, title="Domain split",
                          color_discrete_sequence=[TEAL, AMBER, "#185FA5", "#534AB7", NEUTRAL])
            fig2.update_layout(**PLOTLY_BASE)
            st.plotly_chart(fig2, use_container_width=True)

    with t3:
        outdf = pd.DataFrame({
            "Status": ["Disposed", "Pending"],
            "Count":  [o["disposed_count"], o["pending_count"]],
        })
        fig = px.pie(outdf, names="Status", values="Count",
                     hole=0.58, title="Case status",
                     color_discrete_sequence=[TEAL, NEUTRAL])
        fig.update_layout(**PLOTLY_BASE)
        st.plotly_chart(fig, use_container_width=True)

    with t4:
        fig = go.Figure(go.Scatterpolar(
            r=[scores["competence"], scores["availability"],
               scores["case_speed"], scores["activity"]],
            theta=["Competence", "Availability", "Case Speed", "Activity"],
            fill="toself", name=label,
            line_color=TEAL, fillcolor="rgba(42,107,94,0.18)",
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            title=f"Score radar — {label}",
            **PLOTLY_BASE,
        )
        st.plotly_chart(fig, use_container_width=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RENDER: VERDICT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def render_verdict(name_a, sa, pa, name_b, sb, pb):
    oa = compute_overall(sa)
    ob = compute_overall(sb)
    na = pa["identity"]["normalised_name"]
    nb = pb["identity"]["normalised_name"]

    winner = na if oa > ob else (nb if ob > oa else None)

    reasons = []
    for key, label in [("competence","competence"),("availability","availability"),
                       ("case_speed","case resolution speed"),("activity","recent activity")]:
        if sa[key] != sb[key]:
            better_name = name_a if sa[key] > sb[key] else name_b
            better_val  = max(sa[key], sb[key])
            reasons.append(f"stronger {label} ({better_val}/100 for {better_name})")

    reason_txt = "Leads on " + " and ".join(reasons[:2]) + "." if reasons \
        else "Both lawyers are comparable — check domain breakdown to decide."

    winner_line = f"Go with <em>{winner}</em>" if winner else "It's a <em>tie</em>"
    ca = "#4A9B8A" if oa >= ob else "rgba(255,255,255,0.35)"
    cb = "#4A9B8A" if ob >= oa else "rgba(255,255,255,0.35)"

    st.markdown(f"""
    <div class="verdict-card">
      <div class="verdict-eyebrow">RECOMMENDATION</div>
      <div class="verdict-winner">{winner_line}</div>
      <div class="verdict-reason">{reason_txt}</div>
      <div class="verdict-scores">
        <div>
          <div class="vs-num" style="color:{ca};">{oa}</div>
          <div class="vs-name">{na}</div>
        </div>
        <div class="vs-divider">vs</div>
        <div>
          <div class="vs-num" style="color:{cb};">{ob}</div>
          <div class="vs-name">{nb}</div>
        </div>
      </div>
      <div class="verdict-footnote">
        Equal weight: competence · availability · case speed · activity.
        Based on petitioner-side cases from public eCourts data.
      </div>
    </div>
    """, unsafe_allow_html=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RENDER: COMPARISON RADAR + TABLE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def render_comparison_radar(name_a, sa, name_b, sb):
    theta = ["Competence", "Availability", "Case Speed", "Activity"]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=[sa["competence"], sa["availability"], sa["case_speed"], sa["activity"]],
        theta=theta, fill="toself", name=name_a,
        line_color=TEAL, fillcolor="rgba(42,107,94,0.18)",
    ))
    fig.add_trace(go.Scatterpolar(
        r=[sb["competence"], sb["availability"], sb["case_speed"], sb["activity"]],
        theta=theta, fill="toself", name=name_b,
        line_color=AMBER, fillcolor="rgba(193,123,42,0.15)",
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        title="Score comparison radar", **PLOTLY_BASE,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_comparison_table(name_a, sa, pa, name_b, sb, pb):
    na = pa["identity"]["normalised_name"]
    nb = pb["identity"]["normalised_name"]
    va, oa = pa["volume"], pa["outcomes"]
    vb, ob = pb["volume"], pb["outcomes"]
    yr = pd.Timestamp.today().year

    rows = [
        ("Overall score",    compute_overall(sa), compute_overall(sb)),
        ("Competence",       sa["competence"],    sb["competence"]),
        ("Availability",     sa["availability"],  sb["availability"]),
        ("Case speed",       sa["case_speed"],    sb["case_speed"]),
        ("Activity",         sa["activity"],      sb["activity"]),
        ("Total cases",      va["total_petitioner_cases"], vb["total_petitioner_cases"]),
        ("Disposal %",       oa["disposed_pct"],  ob["disposed_pct"]),
        (f"Cases {yr}",      va["current_year_count"], vb["current_year_count"]),
        (f"Cases {yr-1}",    va["last_year_count"],    vb["last_year_count"]),
        ("Pending cases",    oa["pending_count"], ob["pending_count"]),
        ("With judgments %", oa["with_judgments_pct"], ob["with_judgments_pct"]),
    ]

    df_cmp = pd.DataFrame(rows, columns=["Metric", na, nb]).set_index("Metric")
    st.dataframe(df_cmp, use_container_width=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SIDEBAR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

with st.sidebar:
    st.markdown(
        '<div class="ny-logo">Nyay<span>path</span></div>'
        '<div class="ny-tagline">Advocate analytics · eCourts data</div>',
        unsafe_allow_html=True,
    )
    st.divider()

    mode = st.radio("Mode", ["Single Lawyer", "Compare Two Lawyers"], index=0)

    st.divider()
    st.markdown("**Date range**")
    date_from = st.date_input("From", value=date(2021, 1, 1))
    date_to   = st.date_input("To",   value=date.today())

    st.divider()
    st.markdown("**Fetch settings**")
    page_size = st.slider("Page size",  20, 100, 100, 10)
    max_pages = st.slider("Max pages",  10, 100, 100, 10)

    st.divider()
    st.caption("Petitioner cases only · No composite score · Public data")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN CONTENT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

st.markdown('<p class="page-title">Advocate <em>intelligence</em></p>', unsafe_allow_html=True)
st.markdown('<p class="page-sub">Built from public eCourts data — petitioner cases only, no self-reported data</p>', unsafe_allow_html=True)

# ── SINGLE LAWYER ─────────────────────────────────────────────────────
if mode == "Single Lawyer":

    c1, c2 = st.columns([5, 1])
    with c1:
        lawyer_name = st.text_input(
            "Search", placeholder="e.g. Rohan Venkatesh Yemul",
            label_visibility="collapsed",
        )
    with c2:
        search = st.button("Analyse →", type="primary", use_container_width=True)

    st.markdown('<div class="ny-note">4 independent scores — no composite. You decide what matters most for your case.</div>', unsafe_allow_html=True)

    if search:
        if not lawyer_name.strip():
            st.warning("Please enter a lawyer name.")
        else:
            with st.spinner(f"Fetching cases for {lawyer_name.strip()}…"):
                profile, scores, df = analyze_lawyer(
                    advocate_name=lawyer_name.strip(),
                    api_key=API_KEY, api_url=API_URL,
                    date_from=str(date_from), date_to=str(date_to),
                    page_size=page_size, max_pages=max_pages,
                    court_codes=None,
                )

            if not profile:
                st.error("No petitioner-side cases found. Check spelling or widen the date range.")
            else:
                render_lawyer_card(profile, scores)
                st.markdown('<p class="sec-title">Key metrics</p>', unsafe_allow_html=True)
                render_kpi_grid(profile)
                render_identity(profile)
                st.markdown('<p class="sec-title">Detailed analysis</p>', unsafe_allow_html=True)
                render_charts(profile, scores, lawyer_name.strip())
                st.markdown('<p class="sec-title">Case type breakdown</p>', unsafe_allow_html=True)
                ctb = profile["case_types"]["case_type_breakdown"]
                if ctb:
                    ct_df = pd.DataFrame(ctb).rename(columns={
                        "abbreviation": "Code", "full_name": "Case Type",
                        "domain": "Domain", "act": "Act",
                        "count": "Count", "pct": "%",
                    })
                    st.dataframe(ct_df.set_index("Code"), use_container_width=True)

# ── COMPARE ────────────────────────────────────────────────────────────
else:
    ca, cv, cb = st.columns([5, 1, 5])
    with ca:
        lawyer_a = st.text_input("Lawyer A", placeholder="First advocate name", label_visibility="collapsed")
        st.caption("Lawyer A")
    with cv:
        st.markdown("<div style='text-align:center;font-family:Fraunces,serif;font-size:20px;color:#B8B0A2;padding-top:10px;'>vs</div>", unsafe_allow_html=True)
    with cb:
        lawyer_b = st.text_input("Lawyer B", placeholder="Second advocate name", label_visibility="collapsed")
        st.caption("Lawyer B")

    compare = st.button("Compare lawyers →", type="primary")
    st.markdown('<div class="ny-note">We analyse both lawyers and tell you which one to go with, and why.</div>', unsafe_allow_html=True)

    if compare:
        if not lawyer_a.strip() or not lawyer_b.strip():
            st.warning("Please enter both lawyer names.")
        else:
            with st.spinner(f"Fetching {lawyer_a.strip()}…"):
                pa, sa, dfa = analyze_lawyer(
                    advocate_name=lawyer_a.strip(),
                    api_key=API_KEY, api_url=API_URL,
                    date_from=str(date_from), date_to=str(date_to),
                    page_size=page_size, max_pages=max_pages, court_codes=None,
                )
            with st.spinner(f"Fetching {lawyer_b.strip()}…"):
                pb, sb, dfb = analyze_lawyer(
                    advocate_name=lawyer_b.strip(),
                    api_key=API_KEY, api_url=API_URL,
                    date_from=str(date_from), date_to=str(date_to),
                    page_size=page_size, max_pages=max_pages, court_codes=None,
                )

            if not pa or not pb:
                st.error("Could not build one or both profiles. Check names or date range.")
            else:
                st.markdown('<p class="sec-title">Verdict</p>', unsafe_allow_html=True)
                render_verdict(lawyer_a.strip(), sa, pa, lawyer_b.strip(), sb, pb)

                st.markdown('<p class="sec-title">Score comparison</p>', unsafe_allow_html=True)
                render_comparison_radar(lawyer_a.strip(), sa, lawyer_b.strip(), sb)
                render_comparison_table(lawyer_a.strip(), sa, pa, lawyer_b.strip(), sb, pb)

                st.markdown('<p class="sec-title">Individual profiles</p>', unsafe_allow_html=True)
                left, right = st.columns(2)
                with left:
                    render_lawyer_card(pa, sa)
                    render_kpi_grid(pa, compact=True)
                    render_identity(pa)
                    render_charts(pa, sa, lawyer_a.strip())
                with right:
                    render_lawyer_card(pb, sb)
                    render_kpi_grid(pb, compact=True)
                    render_identity(pb)
                    render_charts(pb, sb, lawyer_b.strip())