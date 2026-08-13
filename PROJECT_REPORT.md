# Synaptic — Project Report

**What it is:** an AI-powered Google Ads automation tool. A business owner types one plain-English description of their business; Synaptic runs it through a pipeline of 7 agents and produces real keyword research, competitor research, negative keywords, segmented ad copy, a full campaign plan, and a simulated performance report — with no manual ad-management work required.

**Two ways to run it:**
- `python main.py` — terminal version, walks through an intake Q&A first.
- `streamlit run app.py` — the dashboard (sidebar + tabs UI), the primary way this is used/demoed.

---

## 1. Pipeline architecture

```
description_validator (sanity-checks the input first)
        |
        v
Stage 1 (parallel): keyword_agent  +  competitor_agent
        |
        v
Stage 2 (parallel): negative_keyword_agent  +  ad_writing_agent
        |
        v
Stage 3: campaign_agent   (assembles the plan; can optionally push it live)
        |
        v
Stage 4: reporting_agent
```

Each agent reads its inputs from `output/*.json` (written by earlier agents) and writes its own output there. Every agent that calls an external API always writes its output file even on failure (empty result), specifically so a failed run can never leave a stale file from a *previous, unrelated* business description silently lying around for the next agent to read.

---

## 2. The agents

### `description_validator.py`
Runs first. Asks Claude (Haiku) a yes/no: does this text actually read like a real business description? Blocks garbage input from silently producing a fabricated campaign. Fails open (lets the pipeline continue) if the API key is missing or Claude errors — a broken validator should never be the reason the whole pipeline stops.

### `intake_agent.py` (terminal path only, `main.py`)
Collects the raw description, an optional website URL (fetched and summarized for real via Claude's `web_fetch` tool), and 6 structured questions (product, ideal customer, geography, budget, goal, differentiation). Folds all of it into one enriched description string — the same shape every other agent expects. The dashboard (`app.py`) has its own equivalent business-details form instead of this terminal Q&A.

### `keyword_agent.py` — Phase 2
Extracts seed keywords from the business description (per-sentence unigrams/bigrams, stopword-filtered, URL-stripped) and fetches real keyword data.
- **Default mode:** Google Trends via `pytrends` — real relative search interest (0–100) and real related queries. No Google Ads access needed at all.
- **Real mode** (`use_google_ads=True`): Google Ads Keyword Planner (`GenerateKeywordIdeas`) — real absolute search volume. **Currently blocked** — requires Basic Access, which Google has not granted (see §4).

No fabricated data anywhere in this file — both modes pull genuinely real numbers from their respective source.

### `competitor_agent.py` — Phase 3
Uses Claude's real `web_search` tool to find actual competing businesses, their positioning, offers, and likely keyword targets. Only invents nothing — if it can't find real competitors, it returns fewer rather than making any up. Doesn't touch Google Ads at all, so it's unaffected by the Basic Access situation.

### `negative_keyword_agent.py`
Uses Claude to generate a negative keyword list — search terms that overlap with the target keywords but signal the wrong intent (DIY, job-seeking, free/cheap, wrong category). Each entry includes a suggested match type and a one-line reason. Claude-only, unaffected by Basic Access.

### `ad_writing_agent.py` — Phase 4
Takes the keyword list and competitor context, and does two things in one Claude call:
1. **Segments** the keywords into 1–5 tightly themed ad groups (e.g. "AC Repair", "Installation & Quotes").
2. Writes **8 headlines (≤30 chars) and 4 descriptions (≤90 chars)** per ad group, following Responsive Search Ad limits — trimmed to fit if Claude runs long, rather than discarded.

Themed ad groups (instead of one flat group) is standard Google Ads practice — tighter keyword-to-ad relevance improves Quality Score. Claude-only, unaffected by Basic Access.

### `campaign_agent.py` — Phase 5
Assembles everything into a complete campaign plan: budget (daily/monthly, in PKR — real if the owner gave one, otherwise a deterministic placeholder range), one ad group per theme with keywords assigned EXACT/PHRASE/BROAD match types, and each ad group's responsive search ad. Saved locally to `output/campaign_plan.json` regardless.

**`push_campaign_real(plan, customer_id)`** — pushes that plan to a **real Google Ads account** via real mutate calls (budget → campaign → location/language targeting → negative keywords → per ad group: ad group → keywords → responsive search ad). Built and **confirmed working** against a Google Ads Test Account (see §4) — created campaign `customers/4916506329/campaigns/24089855253` with 4 ad groups. Requires `plan["website_url"]` (the ad's landing page) and a test-account customer ID, entered via the dashboard's Campaign tab → "Push to Google Ads (Test Account)" — an explicit, user-triggered action, never automatic.

### `reporting_agent.py` — Phase 6
Generates a simulated 30-day performance report (impressions, clicks, CTR, cost, conversions, cost/conversion) per keyword and in aggregate, deterministically derived from each keyword so results are stable across runs. Labeled "simulated" in the report itself. Real performance data requires the campaign to actually be live and accruing real traffic — out of reach until Basic Access is granted (`fetch_report_real()` is a stub for that).

---

## 3. The dashboard (`app.py`)

Streamlit app, rebuilt to match a supplied reference design: sidebar navigation + a two-column layout (business-details form and live agent-status panel on the left, tabbed results on the right).

- **Business details form:** name, website URL, description, target city, monthly budget (PKR), campaign goals, USP, and a toggle for Google Ads Keyword Planner vs. Trends.
- **Live agent status panel:** 7 rows, updated in place as each agent actually runs (not simulated).
- **Results tabs:** Overview, Keywords, Negatives, Competitors, Ad Copy, Campaign, Performance — each shows an empty-state until the pipeline has run, then real output.
- **Campaign tab** additionally has the "Push to Google Ads (Test Account)" control described above.

---

## 4. Google Ads API access status

- **Basic Access application: returned as incomplete**, not denied outright (2026-07-14). Google's stated reason: the tool was still in development. Guidance given: keep building against a **Test Account** (works with the current pending/test-tier developer token, no approval needed), then resubmit the New Token Form later with a design document attached — and don't resubmit with the same answers.
- **What a Test Account unlocks:** full create/read/update/delete on real Campaign, Ad Group, Ad, Keyword, and Negative Keyword objects — proven working end-to-end (see `push_campaign_real` above).
- **What a Test Account does NOT unlock:** real Keyword Planner data (`GenerateKeywordIdeas` is blocked on test accounts regardless of token tier) and real performance metrics (test accounts have no real traffic, so metrics are always zero). Both still require actual Basic Access approval on a real account.
- **Account structure in use:**
  - `993-446-8919` ("Final year project") — real production manager account, client "Synaptic" (`723-999-6956`, also real).
  - `146-673-7474` ("FYP") — a **test manager account**, with one test client account (`491-650-6329`) created under it. `google-ads.yaml`'s `login_customer_id` currently points at this test manager so pushes route correctly.
- **Reapplication checklist** (not yet started): finish the tool end-to-end, write the required design document (what Synaptic does, its architecture, which API endpoints it calls and why, screenshots), rewrite the form answers from scratch, fix the domain/contact-email inconsistency flagged in the first application, then resubmit.

---

## 5. What's fully built vs. not

| Piece | Status |
|---|---|
| Business description validation | Done — real (Claude) |
| Keyword research (Trends mode) | Done — real data |
| Keyword research (Ads Keyword Planner mode) | Built, blocked by Basic Access |
| Competitor research | Done — real (Claude web search) |
| Negative keywords | Done — real (Claude) |
| Ad copy + ad group segmentation | Done — real (Claude) |
| Campaign plan assembly | Done |
| Push campaign to real Google Ads (test account) | Done — verified working |
| Performance reporting | Done, but simulated (real version blocked by Basic Access) |
| Dashboard (Streamlit) | Done — full pipeline + push feature wired in |
| Terminal pipeline (`main.py`) | Done, but doesn't currently thread a website URL into `campaign_agent` (dashboard path does) |
| Basic Access (production Keyword Planner + real reporting) | Pending reapplication |

---

## 6. Tech stack

Python, `google-ads` (Python client, targeting Ads API v24), `anthropic` (Claude — Haiku for classification/generation tasks), `pytrends` (Google Trends), `streamlit` (dashboard), `pandas`. No `requirements.txt` yet.
