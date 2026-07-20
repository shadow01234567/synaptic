"""
Description Validator

Quick sanity-check run before the main pipeline: asks Claude whether the
typed business description actually looks like a real business
description, so nonsense/garbage input doesn't silently produce a
fabricated campaign for a fake company. Uses Haiku since this is a simple
classification task, not creative generation -- keeps the check cheap.
"""

import os
import sys

import anthropic

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents._shared import parse_claude_json

MODEL = "claude-haiku-4-5"

PROMPT_TEMPLATE = """Does the following text look like a genuine business description -- something a real business owner would write to describe what their business does (product/service, and ideally who it's for or where it operates)?

Text: "{business_description}"

Respond with ONLY valid JSON in this exact shape, no other text:
{{"is_valid": true or false, "reason": "one short sentence explaining why"}}
"""


def validate_description(business_description):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        # No key available -- don't block the pipeline over a missing validator key.
        return {"is_valid": True, "reason": "Validation skipped (ANTHROPIC_API_KEY not set)."}

    client = anthropic.Anthropic(api_key=api_key)
    prompt = PROMPT_TEMPLATE.format(business_description=business_description)

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIError as e:
        # Don't let a Claude API problem (rate limit, low credit balance, etc.)
        # block the whole pipeline over a pre-flight check.
        message = getattr(e, "message", str(e))
        return {"is_valid": True, "reason": f"Validation skipped (Claude API error: {message})."}

    text_block = next(b for b in response.content if b.type == "text")
    try:
        data = parse_claude_json(text_block)
    except ValueError:
        # Don't let a validator parsing hiccup block the whole pipeline.
        return {"is_valid": True, "reason": "Validation response could not be parsed; proceeding anyway."}

    return {
        "is_valid": bool(data.get("is_valid", True)),
        "reason": data.get("reason", ""),
    }
