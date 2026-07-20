"""
app.py -- Synaptic Streamlit dashboard

Run with: streamlit run app.py

Browser UI for the Synaptic pipeline: enter a business description, run all
6 agents, and see the results laid out per the Claude Design handoff spec
(design_handoff_synaptic_dashboard/README.md).
"""

import html
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

st.set_page_config(page_title="Synaptic", layout="wide")

# ---------------------------------------------------------------------------
# Design tokens (from design_handoff_synaptic_dashboard/README.md)
# ---------------------------------------------------------------------------
PAGE_BG = "#F1ECE0"
CARD_BG = "#FBF8F1"
INK = "#2B2620"
MUTED_1 = "#7A6F5F"
MUTED_2 = "#8A7A63"
MUTED_3 = "#A79A85"
HAIRLINE_1 = "#E4DAC5"
HAIRLINE_2 = "#DCD1BE"
HAIRLINE_3 = "#D2C4AC"
ACCENT_DARK = "#7A3B32"    # buttons / logo
ACCENT_MID = "#B9764F"     # stats / bars
ACCENT_LIGHT = "#E9A87C"   # on dark tiles
SUCCESS = "#4F7A5C"

COMPETITION_COLORS = {"LOW": SUCCESS, "MEDIUM": ACCENT_MID, "HIGH": ACCENT_DARK}

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,wght@0,400;0,600;1,400;1,600&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

    .stApp {{
        background-color: {PAGE_BG};
        color: {INK};
        font-family: 'IBM Plex Sans', sans-serif;
    }}
    .block-container {{
        max-width: 1040px;
        padding: 60px 44px 100px 44px;
        margin: 0 auto;
    }}

    /* Header */
    .synaptic-header {{
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        border-bottom: 3px solid {INK};
        padding-bottom: 20px;
        margin-bottom: 36px;
    }}
    .synaptic-logo-row {{ display: flex; align-items: center; gap: 14px; }}
    .synaptic-logo-circle {{
        width: 38px; height: 38px; min-width: 38px;
        border-radius: 50%;
        background-color: {ACCENT_DARK};
        color: {CARD_BG};
        font-family: 'Source Serif 4', serif;
        font-style: italic;
        font-size: 20px;
        display: flex; align-items: center; justify-content: center;
    }}
    .synaptic-wordmark {{
        font-family: 'Source Serif 4', serif;
        font-weight: 600;
        font-size: 38px;
        color: {INK};
        line-height: 1.1;
    }}
    .synaptic-tagline {{
        font-family: 'Source Serif 4', serif;
        font-style: italic;
        font-size: 14px;
        color: {MUTED_1};
        margin-top: 2px;
    }}
    .synaptic-report-caption {{
        font-size: 12px;
        color: {MUTED_3};
        margin-top: 6px;
    }}

    /* Section headers */
    .section-h2 {{
        font-family: 'Source Serif 4', serif;
        font-weight: 600;
        font-size: 24px;
        color: {INK};
        border-bottom: 1px solid {INK};
        padding-bottom: 10px;
        margin-top: 48px;
        margin-bottom: 4px;
    }}
    .section-sub {{
        font-size: 14px;
        color: {MUTED_1};
        margin-bottom: 18px;
    }}

    /* Input section */
    .input-label {{
        font-size: 12px; font-weight: 600; text-transform: uppercase;
        letter-spacing: 0.08em; color: {MUTED_2}; margin-bottom: 6px;
    }}
    div[data-testid="stTextArea"] div[data-baseweb="textarea"],
    div[data-testid="stTextArea"] div[data-baseweb="base-input"] {{
        background-color: transparent !important;
        border: none !important;
        border-bottom: 1px solid {HAIRLINE_3} !important;
        border-radius: 0 !important;
        box-shadow: none !important;
    }}
    div[data-testid="stTextArea"] textarea {{
        font-family: 'Source Serif 4', serif !important;
        font-size: 18px !important;
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        color: {INK} !important;
        padding-left: 0 !important;
        caret-color: {INK} !important;
    }}
    div[data-testid="stTextArea"] textarea::placeholder {{
        color: {MUTED_3} !important;
        opacity: 1 !important;
    }}
    div[data-testid="stCheckbox"] label p {{ color: {INK}; }}

    div.stButton > button[kind="primary"] {{
        background-color: {ACCENT_DARK};
        color: {CARD_BG};
        font-weight: 600;
        padding: 13px 30px;
        border-radius: 3px;
        border: none;
        box-shadow: 0 2px 8px rgba(122,59,50,0.28);
    }}
    div.stButton > button[kind="primary"]:hover {{
        background-color: #5E2C25;
        color: {CARD_BG};
    }}

    /* Stat tiles */
    .stat-row {{ display: flex; gap: 14px; flex-wrap: wrap; margin-bottom: 20px; }}
    .stat-tile {{
        background-color: {CARD_BG};
        border: 1px solid {HAIRLINE_1};
        border-radius: 10px;
        padding: 16px 18px;
        flex: 1 1 160px;
    }}
    .stat-tile-label {{ font-size: 12px; color: {MUTED_1}; margin-bottom: 6px; }}
    .stat-tile-value {{
        font-family: 'Source Serif 4', serif;
        font-weight: 600;
        font-size: 24px;
        color: {INK};
    }}
    .stat-tile-value.accent {{ color: {ACCENT_MID}; }}
    .stat-tile-dark {{
        background-color: {INK};
        border-radius: 10px;
        padding: 16px 18px;
        flex: 1 1 140px;
    }}
    .stat-tile-dark .stat-tile-label {{ color: #C7BBA6; }}
    .stat-tile-dark .stat-tile-value {{ font-size: 24px; color: {ACCENT_LIGHT}; }}
    .status-dot {{
        display: inline-block; width: 8px; height: 8px; border-radius: 50%;
        margin-right: 6px;
    }}

    /* Tables */
    table.synaptic-table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    table.synaptic-table th {{
        text-align: left; font-size: 12px; text-transform: uppercase;
        letter-spacing: 0.05em; color: {MUTED_2};
        border-bottom: 1px solid {HAIRLINE_2}; padding: 8px 10px;
    }}
    table.synaptic-table td {{
        border-bottom: 1px solid {HAIRLINE_1}; padding: 9px 10px; color: {INK};
    }}
    table.synaptic-table td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    .comp-dot {{ display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }}

    /* Competitor cards */
    .competitor-card {{
        background-color: {CARD_BG}; border: 1px solid {HAIRLINE_1}; border-radius: 10px;
        padding: 18px; flex: 1 1 220px;
    }}
    .competitor-name {{ font-family: 'Source Serif 4', serif; font-size: 17px; color: {INK}; margin-bottom: 8px; }}
    .competitor-caption {{ font-size: 12px; color: {MUTED_1}; margin-bottom: 10px; }}
    .competitor-headlines {{ font-size: 13px; color: {INK}; margin: 0; padding-left: 18px; }}

    /* Bar chart */
    .bar-row {{ display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }}
    .bar-label {{ width: 160px; font-size: 13px; color: {INK}; flex-shrink: 0; }}
    .bar-track {{ flex: 1; background-color: {HAIRLINE_1}; border-radius: 5px; height: 9px; overflow: hidden; }}
    .bar-fill {{ background-color: {ACCENT_MID}; height: 9px; border-radius: 5px; }}
    .bar-value {{ width: 60px; text-align: right; font-size: 13px; color: {MUTED_1}; flex-shrink: 0; }}

    /* Ad copy columns */
    .adcopy-col-title {{ font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: {MUTED_2}; margin-bottom: 8px; }}
    .adcopy-row {{ border-bottom: 1px solid {HAIRLINE_1}; padding: 10px 0; font-size: 14px; color: {INK}; }}
    </style>
    """,
    unsafe_allow_html=True,
)


def esc(x):
    return html.escape(str(x))


def render_header():
    st.markdown(
        f"""
        <div class="synaptic-header">
            <div class="synaptic-logo-row">
                <div class="synaptic-logo-circle"><i>S</i></div>
                <div>
                    <div class="synaptic-wordmark">Synaptic</div>
                    <div class="synaptic-tagline">AI-powered Google Ads automation</div>
                </div>
            </div>
            <div class="synaptic-report-caption">Pipeline Report</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section_header(title, subtitle):
    st.markdown(
        f'<div class="section-h2">{esc(title)}</div>'
        f'<div class="section-sub">{esc(subtitle)}</div>',
        unsafe_allow_html=True,
    )


def _md(parts):
    st.markdown("".join(parts), unsafe_allow_html=True)


def render_table(headers, rows, right_align_cols=None):
    right_align_cols = right_align_cols or set()
    thead = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body_rows = []
    for row in rows:
        cells = []
        for i, cell in enumerate(row):
            cls = ' class="num"' if i in right_align_cols else ""
            cells.append(f"<td{cls}>{cell}</td>")  # cell may already be pre-escaped HTML
        body_rows.append(f"<tr>{''.join(cells)}</tr>")
    _md([
        f'<table class="synaptic-table"><thead><tr>{thead}</tr></thead>',
        f'<tbody>{"".join(body_rows)}</tbody></table>',
    ])


def competition_cell(level):
    color = COMPETITION_COLORS.get(level, MUTED_1)
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


def render_bar_chart(items):
    max_val = max((v for _, v in items), default=1) or 1
    rows = []
    for label, value in items:
        pct = max(4, round((value / max_val) * 100))
        rows.append(
            f'<div class="bar-row">'
            f'<div class="bar-label">{esc(label)}</div>'
            f'<div class="bar-track"><div class="bar-fill" style="width:{pct}%;"></div></div>'
            f'<div class="bar-value">{value:,}</div>'
            f"</div>"
        )
    _md(rows)


def render_stat_tiles(tiles, dark=False):
    tile_class = "stat-tile-dark" if dark else "stat-tile"
    parts = ['<div class="stat-row">']
    for label, value_html in tiles:
        parts.append(
            f'<div class="{tile_class}">'
            f'<div class="stat-tile-label">{esc(label)}</div>'
            f'<div class="stat-tile-value">{value_html}</div>'
            f"</div>"
        )
    parts.append("</div>")
    _md(parts)


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
render_header()

st.markdown('<div class="input-label">Business description</div>', unsafe_allow_html=True)
business_description = st.text_area(
    "Business description",
    placeholder="e.g. We're a local coffee roastery selling small-batch beans online and in our cafe.",
    label_visibility="collapsed",
    height=90,
)

col_check, col_spacer, col_btn = st.columns([3, 3, 1.4])
with col_check:
    use_google_ads = st.checkbox(
        "Use Google Ads Keyword Planner instead of Google Trends (requires Basic Access)",
        value=False,
    )
with col_btn:
    run_clicked = st.button("Run Pipeline", type="primary", use_container_width=True)

st.markdown(f'<hr style="border:none;border-bottom:1px solid {HAIRLINE_2};margin:20px 0 0 0;">', unsafe_allow_html=True)

if run_clicked and business_description.strip():
    with st.spinner("Checking business description..."):
        check = description_validator.validate_description(business_description)

    if not check["is_valid"]:
        st.error(f"This doesn't look like a valid business description. {check['reason']}")
        st.stop()

    with st.spinner("Running Pipeline..."):
        # Stage 1: keyword_agent and competitor_agent don't depend on each other
        # (or on anything else) -- run them concurrently.
        with ThreadPoolExecutor(max_workers=2) as executor:
            keywords_future = executor.submit(
                keyword_agent.run, business_description, use_google_ads=use_google_ads
            )
            competitors_future = executor.submit(competitor_agent.run, business_description)

            st.session_state["keywords"] = keywords_future.result()
            st.session_state["competitors"] = []
            try:
                st.session_state["competitors"] = competitors_future.result()
            except AGENT_FAILURE_EXCEPTIONS as e:
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

        # Stage 2: negative_keyword_agent (needs only keywords) and ad_writing_agent
        # (needs keywords + competitors, both ready now) don't depend on each other.
        with ThreadPoolExecutor(max_workers=2) as executor:
            negative_future = executor.submit(negative_keyword_agent.run, business_description)
            ad_copy_future = executor.submit(ad_writing_agent.run, business_description)

            st.session_state["negative_keywords"] = None
            try:
                st.session_state["negative_keywords"] = negative_future.result()
            except AGENT_FAILURE_EXCEPTIONS as e:
                st.warning(f"Negative Keyword Agent skipped: {describe_agent_error(e)}")

            st.session_state["ad_copy"] = None
            try:
                st.session_state["ad_copy"] = ad_copy_future.result()
            except AGENT_FAILURE_EXCEPTIONS as e:
                st.error(f"Ad Writing Agent failed: {describe_agent_error(e)}")

        # Stage 3/4: campaign_agent needs ad_copy + negative_keywords; reporting_agent
        # needs the campaign plan -- both are genuinely sequential.
        st.session_state["campaign_plan"] = None
        st.session_state["report"] = None
        if st.session_state["ad_copy"]:
            st.session_state["campaign_plan"] = campaign_agent.run(business_description)
            st.session_state["report"] = reporting_agent.run()

# --- 1. Keyword Research ---
if "keywords" in st.session_state:
    render_section_header("Keyword Research", "Real search data for this business (Google Trends or Google Ads)")
    kw = st.session_state["keywords"]
    rows = [
        [esc(k["keyword"]), keyword_score_cell(k), keyword_detail_cell(k)]
        for k in kw
    ]
    render_table(["Keyword", "Score", "Detail"], rows, right_align_cols={1})
    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)
    top6 = sorted(kw, key=keyword_score, reverse=True)[:6]
    render_bar_chart([(k["keyword"], keyword_score(k)) for k in top6])

# --- 2. Negative Keywords ---
if st.session_state.get("negative_keywords"):
    render_section_header("Negative Keywords", "Excluded search terms and why")
    rows = [
        [esc(n["keyword"]), esc(n["match_type"]), esc(n["reason"])]
        for n in st.session_state["negative_keywords"]
    ]
    render_table(["Excluded Term", "Match Type", "Reason for Exclusion"], rows)

def _competitor_card(comp):
    website = comp.get("website", "")
    usps = "".join(f"<li>{esc(u)}</li>" for u in comp.get("usps", [])) or "<li>None found</li>"
    offers = "".join(f"<li>{esc(o)}</li>" for o in comp.get("notable_offers", [])) or "<li>None found</li>"
    keywords = esc(", ".join(comp.get("likely_keywords", []))) or "None found"
    website_html = f'<div class="competitor-caption">{esc(website)}</div>' if website else ""
    return (
        f'<div class="competitor-card">'
        f'<div class="competitor-name">{esc(comp.get("competitor_name", "Unknown"))}</div>'
        f"{website_html}"
        f'<div class="competitor-caption" style="margin-top:10px;">USPs</div>'
        f'<ul class="competitor-headlines">{usps}</ul>'
        f'<div class="competitor-caption" style="margin-top:10px;">Notable offers</div>'
        f'<ul class="competitor-headlines">{offers}</ul>'
        f'<div class="competitor-caption" style="margin-top:10px;">Likely keywords</div>'
        f'<div style="font-size:13px;color:{INK};">{keywords}</div>'
        f"</div>"
    )


# --- 3. Competitor Landscape ---
if st.session_state.get("competitors"):
    render_section_header("Competitor Landscape", "Real competitors found via live web search")
    cards = [_competitor_card(comp) for comp in st.session_state["competitors"]]
    _md(['<div style="display:flex;gap:14px;flex-wrap:wrap;">', *cards, "</div>"])

# --- 4. AI-Written Ad Copy ---
if st.session_state.get("ad_copy"):
    render_section_header("AI-Written Ad Copy", "Generated headlines and descriptions")
    ad_copy = st.session_state["ad_copy"]
    left, right = st.columns(2)
    with left:
        st.markdown('<div class="adcopy-col-title">Headlines</div>', unsafe_allow_html=True)
        _md([f'<div class="adcopy-row">{esc(h)}</div>' for h in ad_copy["headlines"]])
    with right:
        st.markdown('<div class="adcopy-col-title">Descriptions</div>', unsafe_allow_html=True)
        _md([f'<div class="adcopy-row">{esc(d)}</div>' for d in ad_copy["descriptions"]])

# --- 5. Campaign Plan ---
if st.session_state.get("campaign_plan"):
    render_section_header("Campaign Plan", "Assembled from the results above")
    plan = st.session_state["campaign_plan"]
    is_active = plan["status"].upper() == "ACTIVE"
    dot_color = SUCCESS if is_active else ACCENT_MID
    status_value = f'<span class="status-dot" style="background-color:{dot_color};"></span>{esc(plan["status"].title())}'
    render_stat_tiles([
        ("Campaign Name", esc(plan["campaign_name"])),
        ("Daily Budget", f'<span class="accent">${plan["daily_budget_usd"]}</span>'),
        ("Status", status_value),
        ("Keywords Targeted", str(len(plan["ad_groups"][0]["keywords"]))),
    ])
    rows = [[esc(k["keyword"]), esc(k["match_type"])] for k in plan["ad_groups"][0]["keywords"]]
    render_table(["Keyword", "Match Type"], rows)
    if plan.get("negative_keywords"):
        st.markdown(
            f'<div style="font-size:12px;color:{MUTED_1};margin-top:10px;">'
            f'{len(plan["negative_keywords"])} negative keywords applied to this campaign</div>',
            unsafe_allow_html=True,
        )

# --- 6. Simulated Performance Report ---
if st.session_state.get("report"):
    render_section_header("Simulated Performance Report", st.session_state["report"]["report_period"])
    report = st.session_state["report"]
    s = report["summary"]
    render_stat_tiles(
        [
            ("Impressions", f"{s['impressions']:,}"),
            ("Clicks", f"{s['clicks']:,}"),
            ("CTR", f"{s['ctr_percent']}%"),
            ("Cost", f"${s['cost_usd']:,}"),
            ("Conversions", str(s["conversions"])),
        ],
        dark=True,
    )
    rows = []
    for k in report["by_keyword"]:
        rows.append([
            esc(k["keyword"]),
            f'{k["impressions"]:,}',
            f'{k["clicks"]:,}',
            f'{k["ctr_percent"]}%',
            f'${k["avg_cpc_usd"]}',
            f'${k["cost_usd"]}',
            str(k["conversions"]),
        ])
    render_table(
        ["Keyword", "Impr.", "Clicks", "CTR", "Avg. CPC", "Cost", "Conv."],
        rows,
        right_align_cols={1, 2, 3, 4, 5, 6},
    )
