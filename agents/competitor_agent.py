"""
Competitor Agent (Phase 3)

Uses Claude's real web search tool to research actual competing businesses
for the given business description -- their real selling points, offers,
and likely keyword targets, based on genuine search results rather than
fabricated data. This does not require Google Ads API access at all (web
search is an Anthropic capability, independent of Basic Access).

Needs ANTHROPIC_API_KEY set to run, same as ad_writing_agent and
negative_keyword_agent.
"""

import json
import os
import sys

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents._shared import parse_claude_json, require_api_key

OUTPUT_PATH = os.path.join("output", "competitors.json")

MODEL = "claude-haiku-4-5"
NUM_COMPETITORS = 3
MAX_SEARCH_USES = 8

PROMPT_TEMPLATE = """You are researching real competitors for the following business, using web search:

Business description: {business_description}

Search the web to find {num_competitors} real businesses that would compete with this one for the same customers (same industry/niche, and the same area if a location is mentioned). For each real competitor you find:
- Their business name
- Their website domain, if you found one
- Their key selling points / positioning -- what makes them stand out, based on what you find on their site or in search results
- Any current offers, promotions, or pricing signals you find
- 4-6 keywords this competitor is likely targeting, based on what their business actually offers

Only include real businesses you found evidence of through search. Do not invent competitors. If you cannot find enough real competitors, return fewer rather than making any up.

Respond with ONLY valid JSON in this exact shape, no other text:
{{"competitors": [{{"competitor_name": "...", "website": "...", "usps": ["...", "..."], "notable_offers": ["...", "..."], "likely_keywords": ["...", "..."]}}]}}
"""


def build_prompt(business_description):
    return PROMPT_TEMPLATE.format(
        business_description=business_description,
        num_competitors=NUM_COMPETITORS,
    )


def research_competitors(business_description):
    client = require_api_key()
    prompt = build_prompt(business_description)

    messages = [{"role": "user", "content": prompt}]
    tools = [{
        "type": "web_search_20260209",
        "name": "web_search",
        "max_uses": MAX_SEARCH_USES,
        "allowed_callers": ["direct"],  # required for models below Sonnet 4.5+/Opus 4.5+, e.g. Haiku
    }]

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            tools=tools,
            messages=messages,
        )
        if response.stop_reason == "pause_turn":
            messages = [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": response.content},
            ]
            continue
        break

    text_blocks = [b for b in response.content if b.type == "text" and b.text.strip()]
    if not text_blocks:
        raise RuntimeError("Competitor Agent got no text response from Claude -- try again.")

    data = parse_claude_json(text_blocks[-1])
    return data.get("competitors", [])


def run(business_description):
    competitors = research_competitors(business_description)

    os.makedirs("output", exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(competitors, f, indent=2)

    print(f"Saved {len(competitors)} real competitors to {OUTPUT_PATH}")
    return competitors


if __name__ == "__main__":
    description = input("Enter your business description: ")
    run(description)
