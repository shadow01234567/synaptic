# Synaptic — Google Ads API Design Document

**Prepared for:** Google Ads API Basic Access reapplication (New Token Form)
**Developer token:** [see google-ads.yaml -- not included here, test-tier, pending Basic Access]
**Date:** 2026-10-16
**Live demo:** https://synaptic-ads.streamlit.app
**Company / tool name:** Synaptic
**Contact:** sashaheer.ali10@gmail.com

---

## 1. What Synaptic Does

Synaptic is an AI-powered Google Ads campaign automation tool. A business owner
provides a plain-text description of their business (optionally plus a short
questionnaire and their website URL), and Synaptic automatically:

1. Researches real keywords relevant to the business
2. Researches real competitors in the same market
3. Filters out irrelevant search intent with negative keywords
4. Writes Google Search Ads-compliant ad copy (headlines/descriptions)
5. Assembles a complete campaign structure (budget, targeting, ad groups, keywords, ads)
6. Creates that campaign directly in the owner's Google Ads account via the API,
   paused by default for manual review
7. Reports simulated performance metrics for the resulting plan

The goal is to remove the need for a business owner (particularly small/local
businesses with no in-house marketing expertise) to manually build a Google Ads
campaign from scratch.

---

## 2. Architecture

Synaptic is a pipeline of independent agents orchestrated by `main.py`, run in
stages (some in parallel where there is no data dependency):

```
Intake Agent
     |
     v
Stage 1 (parallel):  Keyword Agent  +  Competitor Agent
     |
     v
Stage 2 (parallel):  Negative Keyword Agent  +  Ad Writing Agent
     |
     v
Stage 3:  Campaign Agent  ->  pushes to Google Ads API
     |
     v
Stage 4:  Reporting Agent
     |
     v
Streamlit Dashboard (app.py)
```

| Agent | Role | External APIs used |
|---|---|---|
| Intake Agent | Collects business description, structured Q&A, and an optional website summary | Anthropic API (Claude, web fetch tool) |
| Keyword Agent | Derives seed keywords from the business description and pulls real keyword data | Google Trends (default) or Google Ads API `KeywordPlanIdeaService` (with `--google-ads` flag) |
| Competitor Agent | Finds real competing businesses and their positioning | Anthropic API (Claude, web search tool) |
| Negative Keyword Agent | Identifies search terms to exclude (wrong intent, DIY, job-seekers, etc.) | Anthropic API (Claude) |
| Ad Writing Agent | Groups keywords into themed ad groups and writes Responsive Search Ad copy | Anthropic API (Claude) |
| Campaign Agent | Assembles the full campaign plan and pushes it to a real Google Ads account | **Google Ads API** (see §3) |
| Reporting Agent | Produces a performance summary for the generated plan | None (currently simulated — see §4) |

All agent outputs are saved as JSON in `output/` and rendered in a Streamlit
dashboard (`app.py`), which also exposes the "push to Google Ads" action as an
explicit, opt-in button (never automatic).

---

## 3. Google Ads API Usage

Synaptic calls the following Google Ads API services, all via the official
`google-ads` Python client library (`GoogleAdsClient.load_from_storage`):

| Service | Method | Purpose | Where |
|---|---|---|---|
| `KeywordPlanIdeaService` | `generate_keyword_ideas` | Real average monthly search volume + competition level for candidate keywords | `agents/keyword_agent.py` — optional mode, requires Basic Access |
| `CampaignBudgetService` | `mutate_campaign_budgets` | Creates the shared daily budget for a new campaign | `agents/campaign_agent.py` |
| `CampaignService` | `mutate_campaigns` | Creates the Search campaign itself (Maximize Clicks bidding, created **paused**) | `agents/campaign_agent.py` |
| `CampaignCriterionService` | `mutate_campaign_criteria` | Sets campaign-level location/language targeting and negative keywords | `agents/campaign_agent.py` |
| `AdGroupService` | `mutate_ad_groups` | Creates one ad group per keyword theme | `agents/campaign_agent.py` |
| `AdGroupCriterionService` | `mutate_ad_group_criteria` | Adds keywords (with match type) to each ad group | `agents/campaign_agent.py` |
| `AdGroupAdService` | `mutate_ad_group_ads` | Creates the Responsive Search Ad (headlines, descriptions, final URL) in each ad group | `agents/campaign_agent.py` |

**Safety defaults:** every campaign is created with `status = PAUSED`
(`agents/campaign_agent.py`, `DEFAULT_STATUS`), so nothing goes live or spends
money without the business owner's explicit review and manual enable in the
Google Ads UI.

**Why real keyword volume (Keyword Planner) still needs Basic Access:**
`GenerateKeywordIdeasRequest` is blocked for test accounts regardless of token
tier, so Synaptic's default keyword source is real Google Trends data
(via `pytrends`) instead — genuinely real relative search interest and related
queries, but not the same metric as Keyword Planner's absolute monthly search
volume. Basic Access is what unlocks the more precise, advertiser-grade
keyword volume data.

---

## 4. Current Status — Verified Against a Real Test Account

The full pipeline has been run end-to-end and verified by actually pushing
generated campaigns to a Google Ads **Test Account** (no Basic Access required
for this — test accounts allow full create/read/update/delete on campaigns,
ad groups, ads, and keywords, they simply never serve to real users or spend
money).

Confirmed working, live in the test account, for multiple independent
businesses (coffee shop, pet grooming, skincare boutique, HVAC company, fitness
studio):

- Campaign created with correct budget, Search network, Maximize Clicks bidding
- Location (Pakistan) and language (English) targeting applied
- One ad group per keyword theme, each with its own keywords (exact/phrase/broad match)
- Responsive Search Ads created per ad group with AI-written headlines/descriptions and the correct landing page URL
- Negative keywords applied at the campaign level
- All campaigns created paused, correctly entering Google's "under review" policy check

*(See §5 for screenshots.)*

**What Basic Access unlocks that a test account cannot provide:**
- Real Keyword Planner search volume (`KeywordPlanIdeaService`) — test accounts return no data
- Real performance metrics (impressions, clicks, cost, conversions) on live accounts — test accounts always report zero, since no real traffic is served

---

## 5. Screenshots

*(Insert the following, captured from the test account run:)*

1. Google Ads **Campaigns** list view — showing multiple real campaigns created by Synaptic, all paused, with correct budgets
2. Google Ads **Ads** view for one campaign — showing the Responsive Search Ad content, status, and ad type
3. Ad group / keyword detail for one campaign
4. Synaptic dashboard (Streamlit `app.py`) — Campaign tab showing the generated plan before push
5. Synaptic dashboard — Performance tab (simulated report)

---

## 6. Intended Use / Business Model

Synaptic is built by a team of four final-year university students as a Final
Year Project. It is not yet a commercial product.

**Who uses it:** small and local business owners in Pakistan (for example
plumbers, clinics, gyms, studios) who have no marketing team and cannot afford
an agency. The owner only describes their business; Synaptic builds the campaign.

**What we use the API for:**
- Creating and managing Search campaigns in Google Ads accounts that the
  business owner (or our team, for demos) owns and has authorized.
- Reading real keyword volume with Keyword Planner, so keyword choices are based
  on real advertiser data instead of only Google Trends.
- Reading campaign performance for the Reporting tab, instead of simulated numbers.

**What we do not do:**
- We do not resell or share Google Ads data with third parties.
- We do not create campaigns without the owner's action: every campaign is
  created PAUSED and the push is an explicit button click.
- We do not manage accounts we do not have authorization for.

**Business model:** none at this stage. After the Final Year Project, the team
may offer Synaptic to small businesses; any such use would follow the Google Ads
API Terms and Required Minimum Functionality policies.

**Live demo:** https://synaptic-ads.streamlit.app (the dashboard runs the full
agent pipeline; the Google Ads push is shown against a test account).

---

## 7. Applicant / Contact Consistency

- **Company / tool name:** Synaptic
- **Website:** https://synaptic-ads.streamlit.app
- **Contact email:** sashaheer.ali10@gmail.com

These three values must be identical in the New Token Form and in the Google Ads
API Center "Developer details" section. The old `shahroz.com` domain is no longer used.
