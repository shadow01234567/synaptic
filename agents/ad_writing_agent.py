"""
Ad Writing Agent (Phase 4)

Takes the keyword list (output/keywords.json) and competitor landscape
(output/competitors.json) and uses Claude to write actual Google Search ad
copy: headlines (<=30 chars) and descriptions (<=90 chars), following Google
Ads Responsive Search Ad limits.

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

PROMPT_TEMPLATE = """You are writing Google Search ad copy (Responsive Search Ad format) for the following business:

Business description: {business_description}

Top researched keywords (by search volume): {keyword_list}

Real competitor positioning for reference (do not copy, use only to differentiate our angle): {competitor_context}

Write:
- {num_headlines} headlines, each STRICTLY 30 characters or fewer
- {num_descriptions} descriptions, each STRICTLY 90 characters or fewer

Headlines should be varied (different angles: price, quality, urgency, trust, location) and naturally incorporate the researched keywords where it reads well. Do not use clickbait, ALL CAPS, or exclamation-mark spam.

Respond with ONLY valid JSON in this exact shape, no other text:
{{"headlines": ["...", "..."], "descriptions": ["...", "..."]}}
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
    keyword_list = ", ".join(k["keyword"] for k in keywords[:10])
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
        num_headlines=NUM_HEADLINES,
        num_descriptions=NUM_DESCRIPTIONS,
    )


def generate_ad_copy(business_description, keywords, competitors):
    client = require_api_key()
    prompt = build_prompt(business_description, keywords, competitors)

    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        thinking={"type": "disabled"},
        messages=[{"role": "user", "content": prompt}],
    )

    text_block = next(b for b in response.content if b.type == "text")
    data = parse_claude_json(text_block)

    headlines = [_fit_to_length(h, HEADLINE_MAX_LEN) for h in data.get("headlines", [])]
    descriptions = [
        _fit_to_length(d, DESCRIPTION_MAX_LEN) for d in data.get("descriptions", [])
    ]

    return {"headlines": headlines, "descriptions": descriptions}


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

    print(
        f"Saved {len(ad_copy['headlines'])} headlines and "
        f"{len(ad_copy['descriptions'])} descriptions to {OUTPUT_PATH}"
    )
    return ad_copy


if __name__ == "__main__":
    description = input("Enter your business description: ")
    run(description)
