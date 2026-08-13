"""
main.py -- Synaptic pipeline orchestrator

Runs all 6 agents for a single business description. keyword_agent and
competitor_agent don't depend on each other, and negative_keyword_agent /
ad_writing_agent don't depend on each other once stage 1 finishes, so each
pair runs concurrently:

  Stage 1 (parallel): keyword_agent, competitor_agent
  Stage 2 (parallel): negative_keyword_agent, ad_writing_agent
  Stage 3:            campaign_agent
  Stage 4:            reporting_agent

Usage:
    python main.py               # keyword_agent uses real Google Trends data (no Google Ads needed)
    python main.py --google-ads  # keyword_agent uses real Google Ads Keyword Planner (needs Basic Access)
"""

import sys
from concurrent.futures import ThreadPoolExecutor

from agents import ad_writing_agent
from agents import campaign_agent
from agents import competitor_agent
from agents import description_validator
from agents import intake_agent
from agents import keyword_agent
from agents import negative_keyword_agent
from agents import reporting_agent
from agents._shared import AGENT_FAILURE_EXCEPTIONS, describe_agent_error


def run_pipeline(business_description, use_google_ads=False):
    check = description_validator.validate_description(business_description)
    if not check["is_valid"]:
        print("=" * 60)
        print("This doesn't look like a valid business description.")
        print(f"Reason: {check['reason']}")
        print("Please provide a clearer business description and try again.")
        print("=" * 60)
        return

    print("=" * 60)
    print("STAGE 1/4: Keyword Agent + Competitor Agent (parallel)")
    print("=" * 60)
    with ThreadPoolExecutor(max_workers=2) as executor:
        keywords_future = executor.submit(
            keyword_agent.run, business_description, use_google_ads=use_google_ads
        )
        competitors_future = executor.submit(competitor_agent.run, business_description)

        keywords_future.result()
        try:
            competitors_future.result()
        except AGENT_FAILURE_EXCEPTIONS as e:
            print(f"Competitor Agent skipped: {describe_agent_error(e)}")

    print()
    print("=" * 60)
    print("STAGE 2/4: Negative Keyword Agent + Ad Writing Agent (parallel)")
    print("=" * 60)
    with ThreadPoolExecutor(max_workers=2) as executor:
        negative_future = executor.submit(negative_keyword_agent.run, business_description)
        ad_copy_future = executor.submit(ad_writing_agent.run, business_description)

        try:
            negative_future.result()
        except AGENT_FAILURE_EXCEPTIONS as e:
            print(f"Negative Keyword Agent skipped: {describe_agent_error(e)}")

        try:
            ad_copy_future.result()
        except AGENT_FAILURE_EXCEPTIONS as e:
            print(f"Ad Writing Agent stopped: {describe_agent_error(e)}")
            print("Cannot continue to Campaign Agent without ad copy. Stopping pipeline.")
            return

    print()
    print("=" * 60)
    print("STAGE 3/4: Campaign Agent")
    print("=" * 60)
    campaign_agent.run(business_description)

    print()
    print("=" * 60)
    print("STAGE 4/4: Reporting Agent")
    print("=" * 60)
    reporting_agent.run()

    print()
    print("=" * 60)
    print("Pipeline complete. Results saved in the output/ folder:")
    print("  output/keywords.json")
    print("  output/negative_keywords.json")
    print("  output/competitors.json")
    print("  output/ad_copy.json")
    print("  output/campaign_plan.json")
    print("  output/performance_report.json")
    print("=" * 60)


if __name__ == "__main__":
    use_ads = "--google-ads" in sys.argv
    description = intake_agent.collect_business_context()
    run_pipeline(description, use_google_ads=use_ads)
