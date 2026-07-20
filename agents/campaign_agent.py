"""
Campaign Agent (Phase 5)

Takes the keyword list (output/keywords.json) and the AI-written ad copy
(output/ad_copy.json) and assembles a complete campaign plan -- budget,
targeting, ad group, keyword match types, and the responsive search ad --
in the same shape a real Google Ads campaign would need.

Actually pushing this to a live account requires Google Ads Basic Access
(the same requirement as keyword_agent's real mode), so this agent currently
only assembles the plan and saves it locally. push_campaign_real() is a
placeholder for that future integration.
"""

import json
import os
import re
import sys

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents._shared import STOPWORDS, hash_range, load_json
from agents.keyword_agent import keyword_score

KEYWORDS_INPUT_PATH = os.path.join("output", "keywords.json")
AD_COPY_INPUT_PATH = os.path.join("output", "ad_copy.json")
NEGATIVE_KEYWORDS_INPUT_PATH = os.path.join("output", "negative_keywords.json")
OUTPUT_PATH = os.path.join("output", "campaign_plan.json")

TARGET_LOCATION = "Pakistan"
TARGET_LANGUAGE = "English"
NETWORK = "SEARCH"
DEFAULT_STATUS = "PAUSED"  # created paused -- safe default, requires manual review before going live
MAX_AD_GROUP_KEYWORDS = 15
MIN_DAILY_BUDGET = 10
MAX_DAILY_BUDGET = 50


def extract_business_name(business_description, max_words=3):
    words = re.findall(r"[a-zA-Z']+", business_description.lower())
    significant = [w for w in words if w not in STOPWORDS and len(w) > 2]
    return " ".join(w.title() for w in significant[:max_words]) or "Business"


def assign_match_type(keyword):
    return ["EXACT", "PHRASE", "BROAD"][hash_range(keyword, 0, 2)]


def build_campaign_plan(business_description, keywords, ad_copy, negative_keywords=None):
    business_name = extract_business_name(business_description)
    top_keywords = sorted(keywords, key=keyword_score, reverse=True)[:MAX_AD_GROUP_KEYWORDS]

    return {
        "campaign_name": f"{business_name} - Search Campaign",
        "status": DEFAULT_STATUS,
        "network": NETWORK,
        "daily_budget_usd": hash_range(business_name, MIN_DAILY_BUDGET, MAX_DAILY_BUDGET),
        "bidding_strategy": "MAXIMIZE_CLICKS",
        "target_location": TARGET_LOCATION,
        "target_language": TARGET_LANGUAGE,
        "negative_keywords": negative_keywords or [],
        "ad_groups": [
            {
                "ad_group_name": f"{business_name} - Ad Group 1",
                "keywords": [
                    {"keyword": k["keyword"], "match_type": assign_match_type(k["keyword"])}
                    for k in top_keywords
                ],
                "responsive_search_ad": {
                    "headlines": ad_copy.get("headlines", []),
                    "descriptions": ad_copy.get("descriptions", []),
                },
            }
        ],
    }


def push_campaign_real(*args, **kwargs):
    """Placeholder for pushing this plan to a live Google Ads account. Requires Basic Access."""
    raise NotImplementedError(
        "Creating a real campaign requires Google Ads Basic Access. "
        "The campaign plan is available locally in output/campaign_plan.json until then."
    )


def run(business_description, push_live=False):
    keywords = load_json(KEYWORDS_INPUT_PATH)
    ad_copy = load_json(AD_COPY_INPUT_PATH)

    try:
        negative_keywords = load_json(NEGATIVE_KEYWORDS_INPUT_PATH)
    except FileNotFoundError:
        negative_keywords = []
        print("No negative_keywords.json found -- run negative_keyword_agent.py first for a fuller plan. Continuing without it.")

    plan = build_campaign_plan(business_description, keywords, ad_copy, negative_keywords)

    os.makedirs("output", exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2)

    print(f"Saved campaign plan to {OUTPUT_PATH}")
    print(f"  Campaign: {plan['campaign_name']}")
    print(f"  Daily budget: ${plan['daily_budget_usd']}")
    print(f"  Keywords in ad group: {len(plan['ad_groups'][0]['keywords'])}")
    print(f"  Negative keywords: {len(plan['negative_keywords'])}")

    if push_live:
        push_campaign_real(plan)

    return plan


if __name__ == "__main__":
    description = input("Enter your business description: ")
    run(description)
