"""
Keyword Agent (Phase 2)

Takes a plain-text business description, derives candidate seed keywords from it,
and asks the Google Ads Keyword Planner API for real search volume / competition
data on those seeds. Results are saved to output/keywords.json for the next agent
(competitor_agent) to consume.
"""

import json
import os
import re

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

GOOGLE_ADS_YAML_PATH = "google-ads.yaml"
LANGUAGE_CONSTANT = "languageConstants/1000"       # English
GEO_TARGET_CONSTANT = "geoTargetConstants/2586"    # Pakistan
OUTPUT_PATH = os.path.join("output", "keywords.json")
MIN_MONTHLY_SEARCHES = 10
MAX_RESULTS = 30

STOPWORDS = {
    "a", "an", "the", "and", "or", "for", "with", "of", "to", "is", "are",
    "that", "this", "in", "on", "at", "by", "we", "our", "your", "you",
    "it", "as", "be", "from", "will", "can", "has", "have", "who", "which",
}


def extract_seed_keywords(business_description, max_seeds=15):
    words = re.findall(r"[a-zA-Z']+", business_description.lower())
    significant = [w for w in words if w not in STOPWORDS and len(w) > 2]

    unigrams = list(dict.fromkeys(significant))
    bigrams = list(dict.fromkeys(
        f"{significant[i]} {significant[i + 1]}"
        for i in range(len(significant) - 1)
    ))

    seeds = []
    for seed in bigrams + unigrams:
        if seed not in seeds:
            seeds.append(seed)
        if len(seeds) >= max_seeds:
            break
    return seeds


def fetch_keyword_ideas(client, customer_id, seed_keywords):
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
        })
    return ideas


def filter_and_rank(ideas, min_volume=MIN_MONTHLY_SEARCHES, top_n=MAX_RESULTS):
    filtered = [i for i in ideas if (i["avg_monthly_searches"] or 0) >= min_volume]
    filtered.sort(key=lambda i: i["avg_monthly_searches"] or 0, reverse=True)
    return filtered[:top_n]


def run(business_description):
    client = GoogleAdsClient.load_from_storage(GOOGLE_ADS_YAML_PATH)
    customer_id = client.login_customer_id

    seeds = extract_seed_keywords(business_description)
    print(f"Seed keywords: {seeds}")

    try:
        ideas = fetch_keyword_ideas(client, customer_id, seeds)
    except GoogleAdsException as ex:
        print(f"Google Ads API error: {ex}")
        return []

    ranked = filter_and_rank(ideas)

    os.makedirs("output", exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(ranked, f, indent=2)

    print(f"Saved {len(ranked)} keywords to {OUTPUT_PATH}")
    return ranked


if __name__ == "__main__":
    description = input("Enter your business description: ")
    run(description)
