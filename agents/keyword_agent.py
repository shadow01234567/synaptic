"""
Keyword Agent (Phase 2)

Takes a plain-text business description, derives candidate seed keywords
from it, and pulls real keyword data from one of two genuine sources:

- Google Trends (via pytrends) -- the default. Needs no Google Ads access
  at all. Returns real *relative search interest* (0-100, scaled to the
  peak within the chosen timeframe/region) and real related queries Google
  actually associates with the seeds. This is NOT the same thing as Keyword
  Planner's average-monthly-search-volume count -- it's a different, but
  genuinely real, signal.
- Google Ads Keyword Planner (GenerateKeywordIdeas) -- real absolute
  average monthly search volume + competition level, but requires Basic
  Access on the developer token (still pending as of this writing).

No fabricated/hashed data is generated anywhere in this file.

pytrends is an unofficial, reverse-engineered Google Trends client (Google
publishes no official public API for Trends). It needs no API key, but
Google does rate-limit/block aggressive use, so failures are handled
gracefully rather than crashing the pipeline.
"""

import json
import os
import re
import sys

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from pytrends.request import TrendReq

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents._shared import STOPWORDS

GOOGLE_ADS_YAML_PATH = "google-ads.yaml"
LANGUAGE_CONSTANT = "languageConstants/1000"       # English
GEO_TARGET_CONSTANT = "geoTargetConstants/2586"    # Pakistan (Google Ads)
TRENDS_GEO = "PK"                                  # Pakistan (Google Trends)
TRENDS_TIMEFRAME = "today 12-m"
OUTPUT_PATH = os.path.join("output", "keywords.json")
MAX_RESULTS = 30
MAX_TRENDS_SEEDS = 5   # Google Trends allows at most 5 terms per comparison

SOURCE_LABELS = {
    "google_ads": "Keyword Planner",
    "google_trends_seed": "Trends (seed)",
    "google_trends_related_top": "Trends (related)",
    "google_trends_related_rising": "Trends (rising)",
}


def describe_source(source):
    return SOURCE_LABELS.get(source, source or "Unknown")


def keyword_score(idea):
    """Rank/sort value for a keyword idea, regardless of which real source produced it."""
    if idea.get("avg_monthly_searches") is not None:
        return idea["avg_monthly_searches"]
    if idea.get("relative_interest") is not None:
        return idea["relative_interest"]
    return idea.get("rising_percent") or 0


def extract_seed_keywords(business_description, max_seeds=15):
    # Bigrams are built per sentence, not across the whole text -- otherwise the
    # last word of one sentence gets glued to the first word of the next
    # (e.g. "...heating service. Business name: Sucoy..." -> bogus "service name").
    text = re.sub(r"https?://\S+", " ", business_description)
    sentences = re.split(r"[.\n]", text)

    unigrams = []
    bigrams = []
    for sentence in sentences:
        words = re.findall(r"[a-zA-Z']+", sentence.lower())
        significant = [w for w in words if w not in STOPWORDS and len(w) > 2]
        for w in significant:
            if w not in unigrams:
                unigrams.append(w)
        for i in range(len(significant) - 1):
            bigram = f"{significant[i]} {significant[i + 1]}"
            if bigram not in bigrams:
                bigrams.append(bigram)

    seeds = []
    for seed in bigrams + unigrams:
        if seed not in seeds:
            seeds.append(seed)
        if len(seeds) >= max_seeds:
            break
    return seeds


# ---------------------------------------------------------------------------
# Real mode: Google Ads Keyword Planner (requires Basic Access)
# ---------------------------------------------------------------------------

def fetch_keyword_ideas_google_ads(seed_keywords):
    client = GoogleAdsClient.load_from_storage(GOOGLE_ADS_YAML_PATH)
    customer_id = client.login_customer_id

    keyword_plan_idea_service = client.get_service("KeywordPlanIdeaService")
    competition_enum = client.enums.KeywordPlanCompetitionLevelEnum

    request = client.get_type("GenerateKeywordIdeasRequest")
    request.customer_id = customer_id
    request.language = LANGUAGE_CONSTANT
    request.geo_target_constants = [GEO_TARGET_CONSTANT]
    request.include_adult_keywords = False
    request.keyword_plan_network = (
        client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH
    )
    request.keyword_seed.keywords.extend(seed_keywords)

    response = keyword_plan_idea_service.generate_keyword_ideas(request=request)

    ideas = []
    for result in response:
        metrics = result.keyword_idea_metrics
        ideas.append({
            "keyword": result.text,
            "avg_monthly_searches": metrics.avg_monthly_searches if metrics else None,
            "competition": (
                competition_enum(metrics.competition).name if metrics else None
            ),
            "relative_interest": None,
            "source": "google_ads",
        })
    return ideas


# ---------------------------------------------------------------------------
# Default mode: Google Trends (no Google Ads access needed)
# ---------------------------------------------------------------------------

def fetch_keyword_ideas_google_trends(seed_keywords):
    seeds = seed_keywords[:MAX_TRENDS_SEEDS]
    pytrends = TrendReq(hl="en-US", tz=300)
    pytrends.build_payload(seeds, cat=0, timeframe=TRENDS_TIMEFRAME, geo=TRENDS_GEO)

    ideas = []
    seen = set()

    interest_df = pytrends.interest_over_time()
    if not interest_df.empty:
        for seed in seeds:
            if seed in interest_df.columns:
                avg_interest = round(float(interest_df[seed].mean()), 1)
                seen.add(seed)
                ideas.append({
                    "keyword": seed,
                    "avg_monthly_searches": None,
                    "competition": None,
                    "relative_interest": avg_interest,
                    "source": "google_trends_seed",
                })

    related = pytrends.related_queries()
    for seed, data in related.items():
        for kind in ("top", "rising"):
            df = data.get(kind)
            if df is None or df.empty:
                continue
            for _, row in df.iterrows():
                query = str(row["query"])
                if query in seen:
                    continue
                seen.add(query)
                value = row["value"]
                ideas.append({
                    "keyword": query,
                    "avg_monthly_searches": None,
                    "competition": None,
                    "relative_interest": float(value) if kind == "top" else None,
                    "rising_percent": float(value) if kind == "rising" else None,
                    "source": f"google_trends_related_{kind}",
                })

    return ideas


def filter_and_rank(ideas, top_n=MAX_RESULTS):
    filtered = [i for i in ideas if keyword_score(i) > 0]
    filtered.sort(key=keyword_score, reverse=True)
    return filtered[:top_n]


def run(business_description, use_google_ads=False):
    seeds = extract_seed_keywords(business_description)
    print(f"Seed keywords: {seeds}")

    if use_google_ads:
        try:
            ideas = fetch_keyword_ideas_google_ads(seeds)
        except GoogleAdsException as ex:
            print(f"Google Ads API error: {ex}")
            ideas = []
    else:
        try:
            ideas = fetch_keyword_ideas_google_trends(seeds)
        except Exception as e:
            print(f"Google Trends request failed: {e}")
            print("Google sometimes rate-limits pytrends -- try again shortly.")
            ideas = []

    ranked = filter_and_rank(ideas)

    # Always write the file, even when empty -- otherwise a failed run leaves
    # downstream agents (and the dashboard) silently reading a stale
    # keywords.json left over from a previous, unrelated business description.
    os.makedirs("output", exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(ranked, f, indent=2)

    source = "Google Ads" if use_google_ads else "Google Trends"
    print(f"Saved {len(ranked)} keywords (real {source} data) to {OUTPUT_PATH}")
    return ranked


if __name__ == "__main__":
    use_ads = "--google-ads" in sys.argv
    description = input("Enter your business description: ")
    run(description, use_google_ads=use_ads)
