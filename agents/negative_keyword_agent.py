"""
Negative Keyword Agent

Takes the keyword list (output/keywords.json) and uses Claude to identify
negative keywords: search terms that overlap with the target keywords but
signal the wrong intent (DIY/recipe searches, free/cheap intent, job
seekers, wrong product category, competitor brand names, etc). Negative
keywords tell Google Ads NOT to show the ad for those searches, avoiding
wasted spend on irrelevant clicks.

Like ad_writing_agent, this agent only calls the Anthropic API -- it does
not touch Google Ads, so it works regardless of the developer token's
access level. It needs ANTHROPIC_API_KEY set to run for real.
"""

import json
import os
import sys

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents._shared import load_json, parse_claude_json, require_api_key

KEYWORDS_INPUT_PATH = os.path.join("output", "keywords.json")
OUTPUT_PATH = os.path.join("output", "negative_keywords.json")

MODEL = "claude-haiku-4-5"
NUM_NEGATIVE_KEYWORDS = 15

PROMPT_TEMPLATE = """You are building a Google Ads negative keyword list for the following business:

Business description: {business_description}

Current target keywords (what we DO want to show ads for): {keyword_list}

Negative keywords tell Google NOT to show our ad for certain searches, to avoid wasting ad spend on irrelevant clicks. Identify {num} negative keywords or phrases that are related enough to overlap with our target keywords, but signal the wrong search intent for this business -- for example: DIY/recipe/how-to intent, free/cheap intent unrelated to our offering, job-seeking intent ("jobs", "careers", "hiring"), a mismatched product category, or generic informational searches that won't convert into a customer.

For each negative keyword, include a suggested match type (EXACT, PHRASE, or BROAD) and a short one-sentence reason it should be excluded.

Respond with ONLY valid JSON in this exact shape, no other text:
{{"negative_keywords": [{{"keyword": "...", "match_type": "...", "reason": "..."}}]}}
"""


def build_prompt(business_description, keywords):
    keyword_list = ", ".join(k["keyword"] for k in keywords[:15])
    return PROMPT_TEMPLATE.format(
        business_description=business_description,
        keyword_list=keyword_list or "none available -- base this on the business description alone",
        num=NUM_NEGATIVE_KEYWORDS,
    )


def generate_negative_keywords(business_description, keywords):
    client = require_api_key()
    prompt = build_prompt(business_description, keywords)

    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        thinking={"type": "disabled"},
        messages=[{"role": "user", "content": prompt}],
    )

    text_block = next(b for b in response.content if b.type == "text")
    data = parse_claude_json(text_block)

    return data.get("negative_keywords", [])


def run(business_description):
    keywords = load_json(KEYWORDS_INPUT_PATH)
    negative_keywords = generate_negative_keywords(business_description, keywords)

    os.makedirs("output", exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(negative_keywords, f, indent=2)

    print(f"Saved {len(negative_keywords)} negative keywords to {OUTPUT_PATH}")
    return negative_keywords


if __name__ == "__main__":
    description = input("Enter your business description: ")
    run(description)
