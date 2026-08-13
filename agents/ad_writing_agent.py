"""
Ad Writing Agent (Phase 4)

Takes the keyword list (output/keywords.json) and competitor landscape
(output/competitors.json), segments the keywords into tightly themed ad
groups, and uses Claude to write separate Google Search ad copy --
headlines (<=30 chars) and descriptions (<=90 chars) -- for each ad group,
following Google Ads Responsive Search Ad limits. Thematic ad groups (vs.
one flat group with every keyword lumped together) is standard Google Ads
best practice: tighter keyword-to-ad relevance improves Quality Score.

Unlike keyword_agent / competitor_agent, this agent does not touch the
Google Ads API at all -- it only calls the Anthropic API, so it works
regardless of the developer token's access level. It does need an
ANTHROPIC_API_KEY environment variable set to run for real.
"""

import json
import os
import sys

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents._shared import load_json, parse_claude_json, require_api_key

KEYWORDS_INPUT_PATH = os.path.join("output", "keywords.json")
COMPETITORS_INPUT_PATH = os.path.join("output", "competitors.json")
OUTPUT_PATH = os.path.join("output", "ad_copy.json")

MODEL = "claude-haiku-4-5"
HEADLINE_MAX_LEN = 30
DESCRIPTION_MAX_LEN = 90
NUM_HEADLINES = 8
NUM_DESCRIPTIONS = 4
MAX_KEYWORDS_CONSIDERED = 25
MIN_AD_GROUPS = 1
MAX_AD_GROUPS = 5

PROMPT_TEMPLATE = """You are structuring a Google Search Ads campaign for the following business:

Business description: {business_description}

Researched keywords to organize (by search volume/interest): {keyword_list}

Real competitor positioning for reference (do not copy, use only to differentiate our angle): {competitor_context}

Step 1 -- Ad group segmentation: Group the keywords above into {min_groups}-{max_groups} tightly themed ad groups by topic/search intent (for example "AC Repair", "Installation & Quotes", "Emergency Service"). Every keyword must be assigned to exactly one ad group. Do not force a split if the keywords are all one clear theme -- a single focused ad group beats several artificial ones. Give each ad group a short, clear name.

Step 2 -- Ad copy: For each ad group, write:
- {num_headlines} headlines, each STRICTLY 30 characters or fewer, specific to that ad group's theme
- {num_descriptions} descriptions, each STRICTLY 90 characters or fewer, specific to that ad group's theme

Headlines should be varied (different angles: price, quality, urgency, trust, location) and naturally incorporate that ad group's own keywords where it reads well. Do not use clickbait, ALL CAPS, or exclamation-mark spam.

Respond with ONLY valid JSON in this exact shape, no other text:
{{"ad_groups": [{{"name": "...", "keywords": ["...", "..."], "headlines": ["...", "..."], "descriptions": ["...", "..."]}}]}}
"""


def _fit_to_length(text, max_len):
    """Trim text to fit Google's character limit instead of discarding it outright."""
    if len(text) <= max_len:
        return text
    truncated = text[:max_len]
    if " " in truncated:
        truncated = truncated.rsplit(" ", 1)[0]
    return truncated.rstrip(",.;: ")


def build_prompt(business_description, keywords, competitors):
    keyword_list = ", ".join(k["keyword"] for k in keywords[:MAX_KEYWORDS_CONSIDERED])
    context_parts = []
    for c in competitors:
        name = c.get("competitor_name", "")
        usps = ", ".join(c.get("usps", []))
        offers = ", ".join(c.get("notable_offers", []))
        context_parts.append(f"{name} -- USPs: {usps}; Offers: {offers}")
    competitor_context = "; ".join(context_parts)[:500]

    return PROMPT_TEMPLATE.format(
        business_description=business_description,
        keyword_list=keyword_list or "none available -- base this on the business description alone",
        competitor_context=competitor_context or "none available",
        min_groups=MIN_AD_GROUPS,
        max_groups=MAX_AD_GROUPS,
        num_headlines=NUM_HEADLINES,
        num_descriptions=NUM_DESCRIPTIONS,
    )


def generate_ad_copy(business_description, keywords, competitors):
    client = require_api_key()
    prompt = build_prompt(business_description, keywords, competitors)

    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        thinking={"type": "disabled"},
        messages=[{"role": "user", "content": prompt}],
    )

    text_block = next(b for b in response.content if b.type == "text")
    data = parse_claude_json(text_block)

    ad_groups = []
    for i, group in enumerate(data.get("ad_groups", []), start=1):
        ad_groups.append({
            "name": group.get("name") or f"Ad Group {i}",
            "keywords": group.get("keywords", []),
            "headlines": [_fit_to_length(h, HEADLINE_MAX_LEN) for h in group.get("headlines", [])],
            "descriptions": [_fit_to_length(d, DESCRIPTION_MAX_LEN) for d in group.get("descriptions", [])],
        })

    return {"ad_groups": ad_groups}


def run(business_description):
    keywords = load_json(KEYWORDS_INPUT_PATH)
    try:
        competitors = load_json(COMPETITORS_INPUT_PATH)
    except FileNotFoundError:
        competitors = []

    ad_copy = generate_ad_copy(business_description, keywords, competitors)

    os.makedirs("output", exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(ad_copy, f, indent=2)

    total_headlines = sum(len(g["headlines"]) for g in ad_copy["ad_groups"])
    total_descriptions = sum(len(g["descriptions"]) for g in ad_copy["ad_groups"])
    print(
        f"Saved {len(ad_copy['ad_groups'])} ad groups "
        f"({total_headlines} headlines, {total_descriptions} descriptions) to {OUTPUT_PATH}"
    )
    return ad_copy


if __name__ == "__main__":
    description = input("Enter your business description: ")
    run(description)
