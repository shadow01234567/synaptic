"""
app.py -- Synaptic Streamlit dashboard

Run with: streamlit run app.py

Sidebar + tabbed dashboard UI, laid out to match the reference design in
synaptic_prototype.html: a business-details form and live agent-status panel
on the left, and a tabbed results view (Overview / Keywords / Negatives /
Competitors / Ad Copy / Campaign / Performance) on the right. All content is
real pipeline output -- nothing here is placeholder/demo data.
"""

import html
import os
import time
from concurrent.futures import ThreadPoolExecutor

import streamlit as st

from agents import (
    ad_writing_agent,
    campaign_agent,
    competitor_agent,
    description_validator,
    keyword_agent,
    negative_keyword_agent,
    reporting_agent,
)
from agents._shared import AGENT_FAILURE_EXCEPTIONS, describe_agent_error
from agents.keyword_agent import describe_source, keyword_score

st.set_page_config(page_title="Synaptic", layout="wide", initial_sidebar_state="expanded")

# ---------------------------------------------------------------------------
# Design tokens (from synaptic_prototype.html reference)
# ---------------------------------------------------------------------------
BG = "#F5F6FA"
WHITE = "#FFFFFF"
BORDER = "#E8EAF0"
TEXT = "#1A1D23"
TEXT2 = "#6B7280"
TEXT3 = "#9CA3AF"
ORANGE = "#F97316"
ORANGE_LIGHT = "#FFF7ED"
ORANGE_BORDER = "#FED7AA"
GREEN = "#16A34A"
GREEN_BG = "#F0FDF4"
RED = "#DC2626"
RED_BG = "#FEF2F2"
PURPLE = "#7C3AED"
PURPLE_BG = "#FAF5FF"

COMPETITION_COLORS = {"LOW": GREEN, "MEDIUM": ORANGE, "HIGH": RED}

AGENT_ROWS_DEF = [
    ("ti-shield-check", "Validator"),
    ("ti-search", "Keyword Agent"),
    ("ti-eye", "Competitor Agent"),
    ("ti-ban", "Negative Keywords"),
    ("ti-layers-intersect", "Ad Writing"),
    ("ti-speakerphone", "Campaign Agent"),
    ("ti-chart-bar", "Reporting Agent"),
]

STATUS_BADGE = {
    "idle": ("badge-idle", "Idle", TEXT3),
    "running": ("badge-running", "Running", ORANGE),
    "done": ("badge-done", "Done", GREEN),
    "error": ("badge-error", "Error", RED),
}

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    @import url('https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@latest/tabler-icons.min.css');

    .stApp {{ background-color: {BG}; font-family: 'Inter', sans-serif; }}
    .block-container {{ padding: 18px 32px 60px 32px; max-width: 1400px; }}
    body, p, div {{ color: {TEXT}; }}

    /* Sidebar */
    [data-testid="stSidebar"] {{ background-color: {WHITE}; border-right: 1px solid {BORDER}; }}
    [data-testid="stSidebar"] > div {{ padding-top: 0; }}
    .sb-logo {{ padding: 14px 4px 16px; border-bottom: 1px solid {BORDER}; display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }}
    .sb-logo-icon {{ width: 32px; height: 32px; background: {ORANGE}; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: #fff; font-weight: 700; font-size: 14px; flex-shrink: 0; }}
    .sb-logo-name {{ font-size: 15px; font-weight: 700; color: {TEXT}; }}
    .sb-logo-sub {{ font-size: 10px; color: {TEXT3}; }}
    .sb-section {{ padding: 14px 4px 6px; font-size: 10px; font-weight: 600; color: {TEXT3}; text-transform: uppercase; letter-spacing: .08em; }}
    .sb-item {{ display: flex; align-items: center; gap: 10px; padding: 8px 10px; border-radius: 8px; margin: 1px 0; font-size: 13px; color: {TEXT2}; }}
    .sb-item.active {{ background: {ORANGE_LIGHT}; color: {ORANGE}; font-weight: 500; }}
    .sb-item i {{ font-size: 16px; width: 18px; }}
    .user-row {{ display: flex; align-items: center; gap: 10px; padding: 14px 4px; border-top: 1px solid {BORDER}; margin-top: 10px; }}
    .user-av {{ width: 34px; height: 34px; border-radius: 50%; background: {ORANGE}; color: #fff; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600; flex-shrink: 0; }}
    .user-name {{ font-size: 13px; font-weight: 500; color: {TEXT}; }}
    .user-email {{ font-size: 11px; color: {TEXT3}; }}

    /* Sidebar nav buttons (functional replacement for the static sb-item rows) */
    [data-testid="stSidebar"] div.stButton {{ margin: 1px 0; }}
    [data-testid="stSidebar"] div.stButton > button {{
        width: 100%; text-align: left; justify-content: flex-start;
        background: transparent; border: none; box-shadow: none; color: {TEXT2};
        font-size: 13px; font-weight: 500; padding: 8px 10px; border-radius: 8px;
    }}
    [data-testid="stSidebar"] div.stButton > button:hover {{ background: {BG}; color: {TEXT}; border: none; }}
    [data-testid="stSidebar"] div.stButton > button[kind="primary"] {{
        background: {ORANGE_LIGHT}; color: {ORANGE}; font-weight: 600;
    }}
    [data-testid="stSidebar"] div.stButton > button[kind="primary"]:hover {{ background: {ORANGE_LIGHT}; color: {ORANGE}; }}

    /* Topbar */
    .topbar {{ background: {WHITE}; border: 1px solid {BORDER}; border-radius: 10px; padding: 12px 18px; display: flex; align-items: center; justify-content: space-between; margin-bottom: 18px; }}
    .tb-path {{ font-size: 13px; color: {TEXT2}; }}
    .tb-path span {{ color: {TEXT}; font-weight: 500; }}
    .page-title {{ font-size: 20px; font-weight: 700; color: {TEXT}; margin-bottom: 16px; }}

    /* Cards */
    .card-title {{ font-size: 13px; font-weight: 600; color: {TEXT}; margin-bottom: 14px; display: flex; align-items: center; gap: 8px; }}
    .card-title i {{ font-size: 16px; color: {ORANGE}; }}
    .f-label {{ font-size: 12px; font-weight: 500; color: {TEXT2}; margin-bottom: 2px; margin-top: 8px; }}
    div[data-testid="stTextInput"] input,
    div[data-testid="stTextArea"] textarea,
    div[data-testid="stNumberInput"] input {{
        background-color: {BG} !important; border: 1px solid {BORDER} !important;
        border-radius: 8px !important; font-size: 13px !important; color: {TEXT} !important;
        font-family: 'Inter', sans-serif !important;
    }}
    div[data-testid="stTextArea"] textarea {{ min-height: 72px !important; }}
    div[data-testid="stCheckbox"] label p {{ color: {TEXT2}; font-size: 13px; }}
    div.stButton > button[kind="primary"] {{
        background-color: {ORANGE}; color: #fff; font-weight: 600; border-radius: 8px;
        border: none; padding: 10px 16px;
    }}
    div.stButton > button[kind="primary"]:hover {{ background-color: #EA6C0A; color: #fff; }}
    div.stButton > button:not([kind="primary"]) {{ border-radius: 8px; font-size: 13px; }}
    hr {{ border: none; border-top: 1px solid {BORDER}; margin: 14px 0; }}

    /* Tab bar (built from st.radio so the sidebar can also drive it) */
    div[data-testid="stRadio"] > div[role="radiogroup"] {{
        display: flex; flex-wrap: wrap; gap: 4px; border-bottom: 2px solid {BORDER};
        padding-bottom: 10px; margin-bottom: 6px;
    }}
    div[data-testid="stRadio"] label {{
        background: transparent; padding: 6px 12px; border-radius: 20px; font-size: 13px;
    }}
    div[data-testid="stRadio"] label:has(input:checked) {{
        background: {ORANGE_LIGHT}; color: {ORANGE}; font-weight: 600;
    }}

    /* Agent status */
    .agent-row {{ display: flex; align-items: center; gap: 10px; padding: 8px 10px; border-radius: 8px; border: 1px solid {BORDER}; margin-bottom: 6px; background: {WHITE}; }}
    .a-icon {{ width: 28px; height: 28px; border-radius: 8px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; background: {BG}; }}
    .a-name {{ font-size: 12px; font-weight: 500; color: {TEXT}; }}
    .a-sub {{ font-size: 11px; color: {TEXT3}; margin-top: 1px; }}
    .badge {{ font-size: 11px; padding: 3px 9px; border-radius: 20px; font-weight: 500; flex-shrink: 0; }}
    .badge-done {{ background: {GREEN_BG}; color: {GREEN}; border: 1px solid #bbf7d0; }}
    .badge-running {{ background: {ORANGE_LIGHT}; color: {ORANGE}; border: 1px solid {ORANGE_BORDER}; }}
    .badge-idle {{ background: {BG}; color: {TEXT3}; border: 1px solid {BORDER}; }}
    .badge-error {{ background: {RED_BG}; color: {RED}; border: 1px solid #fecaca; }}

    /* Metrics grid */
    .metrics-grid {{ display: grid; grid-template-columns: repeat(4,1fr); gap: 10px; margin-bottom: 6px; }}
    .metric {{ background: {BG}; border: 1px solid {BORDER}; border-radius: 10px; padding: 14px; }}
    .metric-label {{ font-size: 12px; color: {TEXT2}; margin-bottom: 5px; font-weight: 500; }}
    .metric-val {{ font-size: 22px; font-weight: 700; color: {TEXT}; }}

    /* Data table */
    table.data-table {{ width: 100%; border-collapse: collapse; }}
    table.data-table th {{ font-size: 11px; font-weight: 600; color: {TEXT2}; text-align: left; padding: 0 10px 10px; border-bottom: 1px solid {BORDER}; text-transform: uppercase; letter-spacing: .04em; }}
    table.data-table td {{ font-size: 12px; color: {TEXT}; padding: 10px; border-bottom: 1px solid {BG}; }}
    table.data-table tr:last-child td {{ border-bottom: none; }}
    .vol-bar {{ display: inline-block; height: 4px; border-radius: 2px; background: {ORANGE}; vertical-align: middle; margin-right: 6px; opacity: .7; }}
    .comp-dot {{ display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }}
    .match-badge {{ font-size: 10px; padding: 2px 7px; border-radius: 4px; background: {PURPLE_BG}; color: {PURPLE}; border: 1px solid #e9d5ff; font-weight: 500; }}

    /* Competitor cards */
    .comp-grid {{ display: grid; grid-template-columns: repeat(2,1fr); gap: 10px; }}
    .comp-card {{ background: {BG}; border: 1px solid {BORDER}; border-radius: 8px; padding: 14px; }}
    .comp-name {{ font-size: 13px; font-weight: 600; color: {TEXT}; margin-bottom: 3px; }}
    .comp-city {{ font-size: 11px; color: {TEXT3}; margin-bottom: 8px; }}
    .comp-item {{ font-size: 11px; color: {TEXT2}; padding: 4px 0; border-bottom: 1px solid {BORDER}; }}
    .comp-item:last-child {{ border: none; }}
    .keyword-chip {{ display: inline-block; background: {WHITE}; border: 1px solid {BORDER}; border-radius: 20px; padding: 3px 10px; font-size: 11px; color: {TEXT}; margin: 2px 5px 2px 0; }}

    /* Ad group cards */
    .ad-group-card {{ background: {BG}; border: 1px solid {BORDER}; border-radius: 8px; padding: 14px; margin-bottom: 12px; }}
    .ad-group-title {{ font-size: 13px; font-weight: 600; color: {ORANGE}; margin-bottom: 10px; }}
    .headline {{ font-size: 12px; color: {TEXT}; padding: 5px 0; border-bottom: 1px solid {BORDER}; }}
    .desc {{ font-size: 12px; color: {TEXT2}; padding: 5px 0; border-bottom: 1px solid {BORDER}; font-style: italic; }}

    /* Empty state */
    .empty-state {{ display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 60px 20px; gap: 14px; text-align: center; }}
    .empty-icon {{ width: 56px; height: 56px; background: {ORANGE_LIGHT}; border-radius: 50%; display: flex; align-items: center; justify-content: center; }}
    .empty-icon i {{ color: {ORANGE}; font-size: 24px; }}
    .empty-title {{ font-size: 15px; font-weight: 600; color: {TEXT}; }}
    .empty-sub {{ font-size: 13px; color: {TEXT2}; max-width: 320px; line-height: 1.6; }}
    </style>
    """,
    unsafe_allow_html=True,
)


def esc(x):
    return html.escape(str(x))


# ---------------------------------------------------------------------------
# Small render helpers
# ---------------------------------------------------------------------------
def _empty_state(icon, title, sub):
    return (
        f'<div class="empty-state">'
        f'<div class="empty-icon"><i class="ti {icon}"></i></div>'
        f'<div class="empty-title">{esc(title)}</div>'
        f'<div class="empty-sub">{esc(sub)}</div>'
        f"</div>"
    )


def _section_label(icon, text):
    return (
        f'<div style="font-size:13px;font-weight:600;margin-bottom:14px;display:flex;align-items:center;gap:6px;">'
        f'<i class="ti {icon}" style="color:{ORANGE};"></i> {esc(text)}</div>'
    )


def _metric_tile(label, value_html):
    return (
        f'<div class="metric"><div class="metric-label">{esc(label)}</div>'
        f'<div class="metric-val">{value_html}</div></div>'
    )


def _metrics_grid(tiles):
    return '<div class="metrics-grid">' + "".join(tiles) + "</div>"


def render_table(headers, rows):
    thead = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body_rows = "".join(
        "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows
    )
    st.markdown(
        f'<table class="data-table"><thead><tr>{thead}</tr></thead><tbody>{body_rows}</tbody></table>',
        unsafe_allow_html=True,
    )


def competition_cell(level):
    color = COMPETITION_COLORS.get(level, TEXT3)
    label = level.title() if isinstance(level, str) else "Unknown"
    return f'<span class="comp-dot" style="background-color:{color};"></span>{esc(label)}'


def keyword_score_cell(k):
    if k.get("avg_monthly_searches") is not None:
        return f'{k["avg_monthly_searches"]:,} / mo'
    if k.get("relative_interest") is not None:
        return f'{k["relative_interest"]}/100 interest'
    if k.get("rising_percent") is not None:
        return f'+{k["rising_percent"]:.0f}% rising'
    return "&mdash;"


def keyword_detail_cell(k):
    if k.get("competition"):
        return competition_cell(k["competition"])
    return esc(describe_source(k.get("source", "")))


def _competitor_card(comp):
    website = comp.get("website", "")
    items = [(u, False) for u in comp.get("usps", [])] + [(o, True) for o in comp.get("notable_offers", [])]
    items_html = "".join(
        f'<div class="comp-item">{"Offer: " if is_offer else ""}{esc(text)}</div>' for text, is_offer in items
    ) or '<div class="comp-item">No details found</div>'
    caption = esc(website) if website else "Found via live web search"
    keywords_html = (
        "".join(f'<span class="keyword-chip">{esc(k)}</span>' for k in comp.get("likely_keywords", []))
    )
    keywords_block = f'<div style="margin-top:8px;">{keywords_html}</div>' if keywords_html else ""
    return (
        f'<div class="comp-card">'
        f'<div class="comp-name">{esc(comp.get("competitor_name", "Unknown"))}</div>'
        f'<div class="comp-city">{caption}</div>'
        f"{items_html}{keywords_block}"
        f"</div>"
    )


def _ad_group_card(group, index):
    keywords_html = (
        "".join(f'<span class="keyword-chip">{esc(k)}</span>' for k in group.get("keywords", []))
        or '<span class="keyword-chip">None</span>'
    )
    headlines_html = "".join(f'<div class="headline">{esc(h)}</div>' for h in group.get("headlines", []))
    descriptions_html = "".join(f'<div class="desc">{esc(d)}</div>' for d in group.get("descriptions", []))
    return (
        f'<div class="ad-group-card">'
        f'<div class="ad-group-title">Ad Group {index}: {esc(group.get("name", f"Ad Group {index}"))}</div>'
        f'<div style="margin-bottom:10px;">{keywords_html}</div>'
        f'<div style="display:flex;gap:20px;flex-wrap:wrap;">'
        f'<div style="flex:1 1 240px;"><div style="font-size:11px;font-weight:600;color:{TEXT2};'
        f'margin-bottom:5px;text-transform:uppercase;letter-spacing:.05em;">Headlines</div>{headlines_html}</div>'
        f'<div style="flex:1 1 240px;"><div style="font-size:11px;font-weight:600;color:{TEXT2};'
        f'margin-bottom:5px;text-transform:uppercase;letter-spacing:.05em;">Descriptions</div>{descriptions_html}</div>'
        f"</div></div>"
    )


def _agent_row_html(icon, name, sub, status):
    badge_class, badge_text, icon_color = STATUS_BADGE.get(status, STATUS_BADGE["idle"])
    return (
        f'<div class="agent-row">'
        f'<div class="a-icon"><i class="ti {icon}" style="color:{icon_color};font-size:15px;"></i></div>'
        f'<div style="flex:1;min-width:0;"><div class="a-name">{esc(name)}</div><div class="a-sub">{esc(sub)}</div></div>'
        f'<span class="badge {badge_class}">{badge_text}</span>'
        f"</div>"
    )


def _compose_description(name, website, description, city, goals, usp):
    # The real description leads -- keyword_agent extracts its seed keywords
    # from the front of this string, so generic connector text here would
    # crowd out the business's own words.
    segments = []
    if description.strip():
        segments.append(description.strip())
    if name.strip():
        segments.append(f"Business name: {name.strip()}.")
    if city.strip():
        segments.append(f"Target location: {city.strip()}.")
    if goals.strip():
        segments.append(f"Campaign goals: {goals.strip()}.")
    if usp.strip():
        segments.append(f"What makes it better than competitors: {usp.strip()}.")
    if website.strip():
        segments.append(f"Website: {website.strip()}.")
    return " ".join(segments)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        '<div class="sb-logo"><div class="sb-logo-icon">S</div><div>'
        '<div class="sb-logo-name">Synaptic</div><div class="sb-logo-sub">Google Ads AI</div>'
        "</div></div>",
        unsafe_allow_html=True,
    )
    st.session_state.setdefault("active_tab", "overview")

    def _nav_button(label, tab_key):
        is_active = st.session_state["active_tab"] == tab_key
        if st.button(
            label, key=f"nav_{label}", use_container_width=True,
            type="primary" if is_active else "secondary",
        ):
            st.session_state["active_tab"] = tab_key
            st.rerun()

    st.markdown('<div class="sb-section">Main menu</div>', unsafe_allow_html=True)
    _nav_button("Dashboard", "overview")
    _nav_button("Campaigns", "campaign")
    _nav_button("Analytics", "performance")
    _nav_button("Reports", "performance")
    st.markdown('<div class="sb-section">Agents</div>', unsafe_allow_html=True)
    _nav_button("Keywords", "keywords")
    _nav_button("Competitors", "competitors")
    _nav_button("Negatives", "negatives")
    _nav_button("Ad groups", "adcopy")
    st.markdown('<div class="sb-section">Developer</div>', unsafe_allow_html=True)
    st.markdown('<div class="sb-item"><i class="ti ti-settings"></i> Settings</div>', unsafe_allow_html=True)
    st.markdown('<div class="sb-item"><i class="ti ti-help-circle"></i> Support</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="user-row"><div class="user-av">SA</div><div>'
        '<div class="user-name">Shaheer Ali</div><div class="user-email">sashaheer.ali10@gmail.com</div>'
        "</div></div>",
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Topbar
# ---------------------------------------------------------------------------
last_ts = st.session_state.get("last_run_ts")
if last_ts is None:
    updated_text = "Not run yet"
else:
    mins = int((time.time() - last_ts) // 60)
    updated_text = "Updated just now" if mins < 1 else f"Updated {mins} min ago"

top_l, top_r = st.columns([5, 1])
with top_l:
    st.markdown(
        f'<div class="topbar"><div class="tb-path">Dashboard &rsaquo; <span>New campaign</span></div>'
        f'<div style="font-size:12px;color:{TEXT3};display:flex;align-items:center;gap:5px;">'
        f'<i class="ti ti-clock"></i> {esc(updated_text)}</div></div>',
        unsafe_allow_html=True,
    )
with top_r:
    if st.button("Reload", use_container_width=True):
        st.rerun()

st.markdown('<div class="page-title">New Campaign</div>', unsafe_allow_html=True)

left_col, right_col = st.columns([1, 2.2], gap="medium")

# ---------------------------------------------------------------------------
# Left column: business details form
# ---------------------------------------------------------------------------
with left_col:
    with st.container(border=True):
        st.markdown('<div class="card-title"><i class="ti ti-building-store"></i> Business details</div>', unsafe_allow_html=True)

        st.markdown('<div class="f-label">Business name</div>', unsafe_allow_html=True)
        business_name = st.text_input("Business name", placeholder="e.g. Sucoy HVAC", label_visibility="collapsed")

        st.markdown('<div class="f-label">Website URL (optional)</div>', unsafe_allow_html=True)
        website_url = st.text_input("Website URL", placeholder="e.g. sucoy-hvac.com", label_visibility="collapsed")

        st.markdown('<div class="f-label">Business description</div>', unsafe_allow_html=True)
        business_description = st.text_area(
            "Business description",
            placeholder="What does the business do, and who is it for?",
            label_visibility="collapsed",
            height=80,
        )

        st.markdown('<div class="f-label">Target city</div>', unsafe_allow_html=True)
        target_city = st.text_input("Target city", placeholder="e.g. Lahore", label_visibility="collapsed")

        st.markdown('<div class="f-label">Monthly budget (Rs.)</div>', unsafe_allow_html=True)
        monthly_budget = st.number_input(
            "Monthly budget", min_value=0, step=500, value=30000, label_visibility="collapsed"
        )

        st.markdown('<div class="f-label">Campaign goals</div>', unsafe_allow_html=True)
        campaign_goals = st.text_input("Campaign goals", placeholder="e.g. Phone calls and lead forms", label_visibility="collapsed")

        st.markdown('<div class="f-label">Why better than competitors?</div>', unsafe_allow_html=True)
        usp = st.text_input("USP", placeholder="e.g. Same-day service, certified technicians", label_visibility="collapsed")

        use_google_ads = st.checkbox(
            "Use Google Ads Keyword Planner instead of Google Trends (requires Basic Access)",
            value=False,
        )

        st.markdown("<hr>", unsafe_allow_html=True)
        run_clicked = st.button("Run Pipeline", type="primary", use_container_width=True)

    st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown('<div class="card-title"><i class="ti ti-cpu"></i> Agent status</div>', unsafe_allow_html=True)

        if "agent_rows" not in st.session_state:
            st.session_state["agent_rows"] = [
                {"status": "idle", "sub": "Waiting for input" if i == 0 else "Waiting..."}
                for i in range(len(AGENT_ROWS_DEF))
            ]

        row_placeholders = []
        for i, (icon, name) in enumerate(AGENT_ROWS_DEF):
            ph = st.empty()
            state = st.session_state["agent_rows"][i]
            ph.markdown(_agent_row_html(icon, name, state["sub"], state["status"]), unsafe_allow_html=True)
            row_placeholders.append(ph)

        def set_row(i, status, sub):
            st.session_state["agent_rows"][i] = {"status": status, "sub": sub}
            icon, name = AGENT_ROWS_DEF[i]
            row_placeholders[i].markdown(_agent_row_html(icon, name, sub, status), unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Pipeline execution (runs before the right-column tabs are rendered so the
# tabs reflect this run's fresh results)
# ---------------------------------------------------------------------------
if run_clicked:
    composed_description = _compose_description(
        business_name, website_url, business_description, target_city, campaign_goals, usp
    )
    if not composed_description.strip():
        st.error("Please enter at least a business description.")
    else:
        set_row(0, "running", "Checking description...")
        # Validate only the raw description text -- the labeled segments
        # _compose_description() adds (Business name:, Target location:, etc.)
        # read as bolted-on metadata to the validator and cause false rejections.
        check = description_validator.validate_description(business_description)

        if not check["is_valid"]:
            set_row(0, "error", "Invalid description")
            st.error(f"This doesn't look like a valid business description. {check['reason']}")
        else:
            set_row(0, "done", "Business validated")

            set_row(1, "running", "Fetching real keyword data...")
            set_row(2, "running", "Searching the web...")
            with ThreadPoolExecutor(max_workers=2) as executor:
                keywords_future = executor.submit(
                    keyword_agent.run, composed_description, use_google_ads=use_google_ads
                )
                competitors_future = executor.submit(competitor_agent.run, composed_description)

                st.session_state["keywords"] = keywords_future.result()
                if st.session_state["keywords"]:
                    set_row(1, "done", f"{len(st.session_state['keywords'])} keywords found")
                else:
                    set_row(1, "error", "No keyword data returned")

                st.session_state["competitors"] = []
                try:
                    st.session_state["competitors"] = competitors_future.result()
                    set_row(2, "done", f"{len(st.session_state['competitors'])} competitors tracked")
                except AGENT_FAILURE_EXCEPTIONS as e:
                    set_row(2, "error", "Skipped")
                    st.warning(f"Competitor Agent skipped: {describe_agent_error(e)}")

            if not st.session_state["keywords"]:
                if use_google_ads:
                    st.warning(
                        "No keyword data came back from Google Ads Keyword Planner. This "
                        "requires Google Ads Basic Access, which is still pending approval "
                        "-- uncheck the box above to use Google Trends instead. The rest of "
                        "the pipeline will still run using the business description alone."
                    )
                else:
                    st.warning(
                        "No keyword data came back from Google Trends. This can happen if "
                        "Google is temporarily rate-limiting requests -- try running again "
                        "in a moment. The rest of the pipeline will still run using the "
                        "business description alone."
                    )

            set_row(3, "running", "Identifying negative keywords...")
            set_row(4, "running", "Writing themed ad copy...")
            with ThreadPoolExecutor(max_workers=2) as executor:
                negative_future = executor.submit(negative_keyword_agent.run, composed_description)
                ad_copy_future = executor.submit(ad_writing_agent.run, composed_description)

                st.session_state["negative_keywords"] = None
                try:
                    st.session_state["negative_keywords"] = negative_future.result()
                    set_row(3, "done", f"{len(st.session_state['negative_keywords'])} negatives identified")
                except AGENT_FAILURE_EXCEPTIONS as e:
                    set_row(3, "error", "Skipped")
                    st.warning(f"Negative Keyword Agent skipped: {describe_agent_error(e)}")

                st.session_state["ad_copy"] = None
                try:
                    st.session_state["ad_copy"] = ad_copy_future.result()
                    n_groups = len(st.session_state["ad_copy"].get("ad_groups", []))
                    set_row(4, "done", f"{n_groups} ad groups created")
                except AGENT_FAILURE_EXCEPTIONS as e:
                    set_row(4, "error", "Failed")
                    st.error(f"Ad Writing Agent failed: {describe_agent_error(e)}")

            st.session_state["campaign_plan"] = None
            st.session_state["report"] = None
            if st.session_state["ad_copy"]:
                set_row(5, "running", "Assembling campaign...")
                st.session_state["campaign_plan"] = campaign_agent.run(
                    composed_description, monthly_budget=monthly_budget or None, website_url=website_url
                )
                set_row(5, "done", "Campaign assembled -- paused")

                set_row(6, "running", "Generating report...")
                st.session_state["report"] = reporting_agent.run()
                set_row(6, "done", "Report ready")
            else:
                set_row(5, "idle", "Skipped -- no ad copy")
                set_row(6, "idle", "Skipped -- no campaign")

            st.session_state["last_run_ts"] = time.time()

# ---------------------------------------------------------------------------
# Right column: tabbed results
# ---------------------------------------------------------------------------
def _render_overview_tab():
    if "keywords" not in st.session_state:
        st.markdown(
            _empty_state(
                "ti-player-play", "Ready to launch",
                "Fill in your business details and click Run Pipeline -- all 7 agents will run automatically.",
            ),
            unsafe_allow_html=True,
        )
        return
    kw_count = len(st.session_state.get("keywords") or [])
    neg_count = len(st.session_state.get("negative_keywords") or [])
    comp_count = len(st.session_state.get("competitors") or [])
    ad_groups = (st.session_state.get("ad_copy") or {}).get("ad_groups", [])
    tiles = [
        _metric_tile("Keywords", str(kw_count)),
        _metric_tile("Negatives", str(neg_count)),
        _metric_tile("Competitors", str(comp_count)),
        _metric_tile("Ad Groups", str(len(ad_groups))),
    ]
    st.markdown(_section_label("ti-activity", "Pipeline results") + _metrics_grid(tiles), unsafe_allow_html=True)


def _render_keywords_tab():
    if "keywords" not in st.session_state:
        st.markdown(_empty_state("ti-lock", "Pipeline not run yet", "Click Run Pipeline to generate results."), unsafe_allow_html=True)
        return
    kw = st.session_state.get("keywords")
    if not kw:
        st.info("No keyword data available for this run.")
        return
    max_score = max((keyword_score(k) for k in kw), default=1) or 1
    rows = []
    for k in kw:
        score = keyword_score(k)
        pct = max(4, round((score / max_score) * 60))
        score_cell = f'<span class="vol-bar" style="width:{pct}px;"></span>{keyword_score_cell(k)}'
        rows.append([esc(k["keyword"]), score_cell, keyword_detail_cell(k)])
    st.markdown(_section_label("ti-search", f"{len(kw)} keywords found"), unsafe_allow_html=True)
    render_table(["Keyword", "Score", "Detail"], rows)


def _render_negatives_tab():
    if "keywords" not in st.session_state:
        st.markdown(_empty_state("ti-lock", "Pipeline not run yet", "Click Run Pipeline to generate results."), unsafe_allow_html=True)
        return
    negs = st.session_state.get("negative_keywords")
    if not negs:
        st.info("No negative keywords were generated for this run.")
        return
    rows = [
        [esc(n["keyword"]), f'<span class="match-badge">{esc(n["match_type"])}</span>', esc(n["reason"])]
        for n in negs
    ]
    st.markdown(_section_label("ti-ban", f"{len(negs)} negative keywords removed"), unsafe_allow_html=True)
    render_table(["Keyword", "Match Type", "Reason"], rows)


def _render_competitors_tab():
    if "keywords" not in st.session_state:
        st.markdown(_empty_state("ti-lock", "Pipeline not run yet", "Click Run Pipeline to generate results."), unsafe_allow_html=True)
        return
    comps = st.session_state.get("competitors")
    if not comps:
        st.info("No competitors were found for this run.")
        return
    st.markdown(_section_label("ti-eye", f"{len(comps)} competitors tracked (live web search)"), unsafe_allow_html=True)
    cards = "".join(_competitor_card(c) for c in comps)
    st.markdown(f'<div class="comp-grid">{cards}</div>', unsafe_allow_html=True)


def _render_adcopy_tab():
    if "keywords" not in st.session_state:
        st.markdown(_empty_state("ti-lock", "Pipeline not run yet", "Click Run Pipeline to generate results."), unsafe_allow_html=True)
        return
    ad_copy = st.session_state.get("ad_copy")
    if not ad_copy:
        st.info("Ad copy wasn't generated for this run.")
        return
    ad_groups = ad_copy.get("ad_groups", [])
    st.markdown(_section_label("ti-writing", f"AI-written ad copy -- {len(ad_groups)} ad groups"), unsafe_allow_html=True)
    for i, g in enumerate(ad_groups, start=1):
        st.markdown(_ad_group_card(g, i), unsafe_allow_html=True)


def _render_campaign_tab():
    if "keywords" not in st.session_state:
        st.markdown(_empty_state("ti-lock", "Pipeline not run yet", "Click Run Pipeline to generate results."), unsafe_allow_html=True)
        return
    plan = st.session_state.get("campaign_plan")
    if not plan:
        st.info("Campaign plan wasn't assembled for this run.")
        return
    total_keywords = sum(len(g["keywords"]) for g in plan["ad_groups"])
    tiles = [
        _metric_tile("Campaign Name", f'<span style="font-size:14px;">{esc(plan["campaign_name"])}</span>'),
        _metric_tile("Daily Budget", f'Rs.{plan["daily_budget_pkr"]:,}'),
        _metric_tile("Monthly Budget", f'Rs.{plan["monthly_budget_pkr"]:,}'),
        _metric_tile("Ad Groups", str(len(plan["ad_groups"]))),
        _metric_tile("Total Keywords", str(total_keywords)),
        _metric_tile("Status", f'<span style="font-size:14px;color:{ORANGE};">{esc(plan["status"].title())}</span>'),
    ]
    st.markdown(_section_label("ti-speakerphone", "Campaign plan") + _metrics_grid(tiles), unsafe_allow_html=True)

    st.markdown(
        f'<div style="font-size:13px;font-weight:600;margin:16px 0 12px;display:flex;align-items:center;gap:6px;">'
        f'<i class="ti ti-list" style="color:{ORANGE};"></i> Ad group breakdown</div>',
        unsafe_allow_html=True,
    )
    summary_rows = []
    for g in plan["ad_groups"]:
        match_types = sorted({k["match_type"].title() for k in g["keywords"]})
        summary_rows.append([
            esc(g["ad_group_name"]),
            str(len(g["keywords"])),
            esc(" + ".join(match_types)) if match_types else "&mdash;",
            str(len(g["responsive_search_ad"]["headlines"])),
        ])
    render_table(["Ad Group", "Keywords", "Match Types", "Headlines"], summary_rows)

    if plan.get("negative_keywords"):
        st.markdown(
            f'<div style="font-size:12px;color:{TEXT2};margin-top:10px;">'
            f'{len(plan["negative_keywords"])} negative keywords applied to this campaign.</div>',
            unsafe_allow_html=True,
        )

    with st.expander("View all keywords by ad group"):
        detail_rows = [
            [esc(g["ad_group_name"]), esc(k["keyword"]), esc(k["match_type"])]
            for g in plan["ad_groups"]
            for k in g["keywords"]
        ]
        render_table(["Ad Group", "Keyword", "Match Type"], detail_rows)

    st.markdown("<hr>", unsafe_allow_html=True)
    with st.expander("Push to Google Ads (Test Account)"):
        st.caption(
            "Creates this campaign for real in a Google Ads Test Account -- nothing serves to "
            "real users and no money is spent. Requires a Test Account created under your "
            "Google Ads manager account (Tools & Settings → Setup → API Center)."
        )
        if not plan.get("website_url"):
            st.warning("Add a Website URL in the business details form and re-run the pipeline first -- ads need a landing page.")
        else:
            test_customer_id = st.text_input(
                "Test account customer ID",
                value=os.environ.get("GOOGLE_ADS_TEST_CUSTOMER_ID", ""),
                placeholder="e.g. 1234567890",
            )
            if st.button("Push campaign to test account", type="secondary"):
                if not test_customer_id.strip():
                    st.error("Enter the test account's customer ID first.")
                else:
                    try:
                        with st.spinner("Pushing to Google Ads..."):
                            result = campaign_agent.push_campaign_real(plan, customer_id=test_customer_id.strip())
                        st.success(f"Created campaign {result['campaign']} with {len(result['ad_groups'])} ad group(s).")
                    except Exception as e:
                        st.error(f"Push failed: {e}")


def _render_performance_tab():
    if "keywords" not in st.session_state:
        st.markdown(_empty_state("ti-lock", "Pipeline not run yet", "Click Run Pipeline to generate results."), unsafe_allow_html=True)
        return
    report = st.session_state.get("report")
    if not report:
        st.info("No performance report for this run.")
        return
    s = report["summary"]
    avg_cpc = round(s["cost_pkr"] / s["clicks"]) if s["clicks"] else 0
    cost_per_conv = f'Rs.{s["cost_per_conversion_pkr"]}' if s["cost_per_conversion_pkr"] is not None else "&mdash;"
    tiles = [
        _metric_tile("Impressions", f'{s["impressions"]:,}'),
        _metric_tile("Clicks", f'{s["clicks"]:,}'),
        _metric_tile("CTR", f'{s["ctr_percent"]}%'),
        _metric_tile("Total Spend", f'Rs.{s["cost_pkr"]:,}'),
        _metric_tile("Avg. CPC", f'Rs.{avg_cpc}'),
        _metric_tile("Conversions", str(s["conversions"])),
        _metric_tile("Conv. Rate", f'{s["conversion_rate_percent"]}%'),
        _metric_tile("Cost / Conv.", cost_per_conv),
    ]
    st.markdown(
        _section_label("ti-chart-bar", f'Simulated performance report -- {report["report_period"]}') + _metrics_grid(tiles),
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div style="font-size:13px;font-weight:600;margin:16px 0 12px;display:flex;align-items:center;gap:6px;">'
        f'<i class="ti ti-trending-up" style="color:{ORANGE};"></i> Performance by keyword</div>',
        unsafe_allow_html=True,
    )
    rows = []
    for k in sorted(report["by_keyword"], key=lambda r: r["impressions"], reverse=True):
        rows.append([
            esc(k["keyword"]), f'{k["impressions"]:,}', f'{k["clicks"]:,}', f'{k["ctr_percent"]}%',
            f'Rs.{k["cost_pkr"]:,}', str(k["conversions"]),
        ])
    render_table(["Keyword", "Impressions", "Clicks", "CTR", "Spend", "Conv."], rows)


TAB_LABELS = {
    "overview": "Overview",
    "keywords": "Keywords",
    "negatives": "Negatives",
    "competitors": "Competitors",
    "adcopy": "Ad Copy",
    "campaign": "Campaign",
    "performance": "Performance",
}
TAB_RENDERERS = {
    "overview": _render_overview_tab,
    "keywords": _render_keywords_tab,
    "negatives": _render_negatives_tab,
    "competitors": _render_competitors_tab,
    "adcopy": _render_adcopy_tab,
    "campaign": _render_campaign_tab,
    "performance": _render_performance_tab,
}

with right_col:
    with st.container(border=True):
        st.radio(
            "View", list(TAB_LABELS.keys()), format_func=lambda k: TAB_LABELS[k],
            horizontal=True, key="active_tab", label_visibility="collapsed",
        )
        TAB_RENDERERS[st.session_state["active_tab"]]()
