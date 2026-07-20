# Synaptic Dashboard — Explanation for Supervisor Demo

## Opening pitch (say this first)

"Synaptic takes a plain-English business description and automatically produces
a complete Google Ads campaign — keyword research, competitor analysis, ad
copy, campaign structure, and a performance report — with zero manual work
from the business owner. You type one sentence, and the system does the rest."

---

## Step-by-step walkthrough

### 1. Business Description (input)

**What it is:** A single text box. The business owner types a plain description
of their business — what it does, where it's located, who it serves.

**What to say:** "This is the only input the system needs. No forms, no
keyword lists, no manual setup — just a description, like you'd give a
person."

---

### 2. Keyword Research

**What it does:** Pulls real data from Google Trends showing what people
actually search for that's related to this business — real search interest
scores, not invented numbers.

**What to say:** "This calls Google Trends in real time. These are genuine
search patterns — what real people are typing into Google right now related
to this type of business."

**If asked how it works:** It takes the business description, extracts
meaningful keywords from it, and asks Google Trends for real search interest
data and related searches for those terms.

---

### 3. Negative Keywords

**What it does:** Uses Claude AI to identify search terms that sound related
but should NOT trigger the ad — e.g. someone searching "pet grooming jobs"
is looking for a job, not a service, so the ad should never show for that
search.

**What to say:** "This is real AI reasoning about search intent — figuring
out which similar-sounding searches would waste ad budget because the
searcher isn't actually a potential customer."

**Why it matters:** In real Google Ads, this is what prevents wasted ad
spend on irrelevant clicks.

---

### 4. Competitor Landscape

**What it does:** Claude actually searches the live web and finds real
competing businesses — their real names, real websites, real pricing, and
real current promotions.

**What to say:** "This is the most impressive part of the system. It's not
guessing or making up competitor names — it performs real web searches and
reports back genuine, verifiable information: actual businesses, actual
deals they're currently running, actual prices."

**Why it matters:** This context feeds directly into the ad-writing step,
so the ads we generate are informed by what's actually happening in the
market right now.

---

### 5. AI-Written Ad Copy

**What it does:** Claude writes the actual advertisement text — the
headlines and descriptions a real customer would see on Google — using
everything learned in steps 2-4.

**What to say:** "By this point the system knows what people search for,
what competitors are offering, and what makes this business different. This
step is where it stops researching and starts writing — real, ready-to-use
ad text, respecting Google's exact character limits (30 characters for
headlines, 90 for descriptions)."

**Example output:**
- Headline: "Dog Grooming in Lahore"
- Description: "Professional dog & cat grooming in Lahore. Trusted,
  affordable, book online today."

---

### 6. Campaign Plan

**What it does:** Assembles everything above into one structured campaign —
daily budget, location targeting, keyword match types, and the finished ad
copy — in the exact format a real Google Ads campaign needs.

**What to say:** "This is the packaging step. It takes everything the
earlier agents produced and organizes it into a single, complete campaign
definition — ready to be launched."

**Honest note:** The budget number here is a placeholder for demo purposes,
since a real budget would be a business decision made by the owner, not
something the AI should invent.

---

### 7. Performance Report

**What it does:** Shows a simulated report of how the campaign might
perform — impressions, clicks, cost, conversions — clearly labeled as
simulated.

**What to say:** "This shows the kind of reporting dashboard a business
owner would eventually see once a real campaign is live and generating
real traffic."

---

## The one thing to say upfront, before anyone asks

"Two pieces are currently simulated rather than fully live: the exact
campaign budget and the performance numbers. That's because actually
launching a live campaign requires Google's 'Basic Access' approval on our
developer account — a manual review process on Google's side that's still
pending, entirely outside our control. Everything else — the keyword data,
the competitor research, and the ad copy — is genuinely real, live data."

---

## Quick reference: what's real AI vs. real data vs. simulated

| Step | Real AI (Claude) | Real Data (Google) | Simulated |
|---|---|---|---|
| 2. Keyword Research | | Yes (Google Trends) | |
| 3. Negative Keywords | Yes | | |
| 4. Competitor Landscape | Yes (web search) | Yes (real web results) | |
| 5. Ad Copy | Yes | | |
| 6. Campaign Plan | | | Budget/targeting numbers |
| 7. Performance Report | | | Entirely simulated |

---

## If your supervisor asks tough questions

**"Is this all done by AI? What have you done then?"**
You directed every architecture decision, handled the real Google/Anthropic
account setup and approval process, tested every component yourself, and
can explain exactly how each part works (which you're doing right now).
AI-assisted development is normal practice — the value you added is
direction, integration, and understanding, not typing every character.

**"Why isn't the campaign actually live?"**
Google requires manual approval ("Basic Access") before any tool can create
real campaigns on a real account. That review is still pending — it's an
external, several-business-day process, not a technical limitation in the
code.

**"How do you know the AI output is good?"**
Be honest: there's no formal evaluation step yet comparing this to
human-written ads or real performance data. This is a good area to mention
as future work if asked about limitations.

**"What's the cost to run this?"**
Each full run costs a small fraction of a cent to a few cents in AI API
usage — genuinely cheap at this scale.
