"""
Intake Agent

Runs before the main pipeline. Collects the business description from the
owner, a short set of intake questions, and (optionally) their website --
fetched with Claude's real web_fetch tool -- then folds everything into a
single enriched business_description string, which is the shape every other
agent in the pipeline already expects.

Website fetching is best-effort: if it's skipped or fails, the pipeline
still runs on the description + question answers alone.
"""

import os
import sys

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents._shared import AGENT_FAILURE_EXCEPTIONS, describe_agent_error, require_api_key

MODEL = "claude-haiku-4-5"
MAX_FETCH_USES = 3

QUESTIONS = [
    ("product", "What do you sell, and what's your single most profitable product/service?"),
    ("ideal_customer", "Who is your ideal customer (age, location, income, interests)?"),
    ("geography", "What locations do you want to target (city, radius, nationwide, online-only)?"),
    ("budget", "What's your monthly ad budget?"),
    ("goal", "What's the goal -- sales, leads/calls, website traffic, app installs, foot traffic?"),
    ("differentiation", "What makes you different / why should someone pick you over competitors?"),
]

FETCH_PROMPT_TEMPLATE = """Fetch this business website and summarize it for someone about to run a Google Ads campaign for this business: {url}

Cover: what they sell, who they seem to target, any pricing or offers mentioned, service area/locations, and anything distinctive about their positioning. Be factual -- only report what's actually on the site. Keep it to a few sentences.
"""


def fetch_website_summary(url):
    """Use Claude's real web_fetch tool to pull the business website and
    summarize anything relevant to an ad campaign. Returns None on any
    failure -- this is a nice-to-have, not a blocker for the pipeline."""
    try:
        client = require_api_key()
    except RuntimeError as e:
        print(f"Website fetch skipped: {e}")
        return None

    prompt = FETCH_PROMPT_TEMPLATE.format(url=url)
    messages = [{"role": "user", "content": prompt}]
    tools = [{
        "type": "web_fetch_20260209",
        "name": "web_fetch",
        "max_uses": MAX_FETCH_USES,
        "allowed_callers": ["direct"],  # required for models below Sonnet 4.5+/Opus 4.5+, e.g. Haiku
    }]

    try:
        while True:
            response = client.messages.create(
                model=MODEL,
                max_tokens=1024,
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
    except AGENT_FAILURE_EXCEPTIONS as e:
        print(f"Website fetch skipped: {describe_agent_error(e)}")
        return None

    text_blocks = [b for b in response.content if b.type == "text" and b.text.strip()]
    if not text_blocks:
        return None
    return text_blocks[-1].text.strip()


def ask_questions():
    print()
    print("A few quick questions before we start (press Enter to skip any):")
    answers = {}
    for key, question in QUESTIONS:
        answers[key] = input(f"  {question} ").strip()
    return answers


def build_business_description(description, answers, website_summary):
    parts = [description.strip()]

    labeled = [
        ("Most profitable product/service", answers.get("product")),
        ("Ideal customer", answers.get("ideal_customer")),
        ("Target locations", answers.get("geography")),
        ("Monthly ad budget", answers.get("budget")),
        ("Campaign goal", answers.get("goal")),
        ("Differentiation from competitors", answers.get("differentiation")),
    ]
    detail_lines = [f"- {label}: {value}" for label, value in labeled if value]
    if detail_lines:
        parts.append("Additional details:\n" + "\n".join(detail_lines))

    if website_summary:
        parts.append(f"Website summary:\n{website_summary}")

    return "\n\n".join(parts)


def collect_business_context():
    description = input("Enter your business description: ").strip()
    website_url = input("Business website (optional, press Enter to skip): ").strip()

    website_summary = None
    if website_url:
        print("Fetching website...")
        website_summary = fetch_website_summary(website_url)
        if website_summary:
            print("Got it.")

    answers = ask_questions()

    return build_business_description(description, answers, website_summary)


if __name__ == "__main__":
    print()
    print("=" * 60)
    print(collect_business_context())
    print("=" * 60)
