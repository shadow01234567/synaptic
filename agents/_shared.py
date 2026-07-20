"""
Shared helpers used across multiple Synaptic agents: stopword filtering,
JSON I/O, deterministic hash-based sampling (used by the mock/simulated
agents), and the Claude API response-parsing boilerplate (used by the
real-AI agents).
"""

import hashlib
import json
import os
import re

import anthropic

STOPWORDS = {
    "a", "an", "the", "and", "or", "for", "with", "of", "to", "is", "are",
    "that", "this", "in", "on", "at", "by", "we", "our", "your", "you",
    "it", "as", "be", "from", "will", "can", "has", "have", "who", "which",
}


def load_json(path, hint="Run the earlier agents first."):
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} not found. {hint}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def hash_range(text, low, high):
    """Deterministic pseudo-value in [low, high], derived from an MD5 hash of text."""
    digest = hashlib.md5(text.encode()).hexdigest()
    return low + (int(digest[:4], 16) % (high - low + 1))


def parse_claude_json(text_block):
    """Extract and parse a JSON object from Claude's response text. Tolerates a
    fenced ```json block anywhere in the text (not just at the very start) and
    leading/trailing prose -- some models (e.g. Haiku) explain themselves before
    the JSON despite being told to respond with only JSON."""
    raw_text = text_block.text.strip()

    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)```", raw_text, re.DOTALL)
    if fence_match:
        raw_text = fence_match.group(1).strip()

    if not raw_text.startswith("{"):
        start, end = raw_text.find("{"), raw_text.rfind("}")
        if start != -1 and end != -1 and end > start:
            raw_text = raw_text[start:end + 1]

    return json.loads(raw_text)


def require_api_key():
    """Return an Anthropic client, or raise RuntimeError with setup instructions."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Get a key from console.anthropic.com "
            "and set it as an environment variable before running this agent."
        )
    return anthropic.Anthropic(api_key=api_key)


# Exceptions an agent call can raise that mean "this agent failed, but the
# rest of the pipeline can still continue" -- as opposed to a bug.
AGENT_FAILURE_EXCEPTIONS = (RuntimeError, ValueError, anthropic.APIError)


def describe_agent_error(e):
    """Human-readable message for an agent failure, including real Claude API errors
    (rate limits, low credit balance, server errors) alongside our own RuntimeErrors."""
    if isinstance(e, anthropic.APIError):
        return f"Claude API error: {getattr(e, 'message', str(e))}"
    return str(e)
