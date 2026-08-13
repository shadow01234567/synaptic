"""
Reporting Agent (Phase 6)

Takes the campaign plan (output/campaign_plan.json) and generates a
performance report -- impressions, clicks, cost, conversions -- as if the
campaign had been running for the last 30 days. This is the final step of
the Synaptic pipeline, giving the business owner a dashboard-style summary.

Real performance data requires the campaign to actually be live in Google
Ads, which requires Basic Access (same requirement as the other agents'
real modes). fetch_report_real() is a placeholder for that future
integration.
"""

import hashlib
import json
import os
import sys

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents._shared import hash_range, load_json

CAMPAIGN_INPUT_PATH = os.path.join("output", "campaign_plan.json")
OUTPUT_PATH = os.path.join("output", "performance_report.json")

REPORT_PERIOD = "Last 30 days (simulated)"


def _hash_percent(text, low_pct, high_pct):
    """Returns a float percent (e.g. 3.5) deterministically derived from text."""
    digest = hashlib.md5(text.encode()).hexdigest()
    hundredths = low_pct * 100 + (int(digest[6:8], 16) % ((high_pct - low_pct) * 100 + 1))
    return round(hundredths / 100, 2)


def generate_mock_keyword_performance(keyword):
    impressions = hash_range(keyword, 100, 5000)
    ctr = _hash_percent(f"{keyword}-ctr", 2.0, 8.0)
    clicks = round(impressions * (ctr / 100))
    avg_cpc = hash_range(f"{keyword}-cpc", 8, 40)
    cost = round(clicks * avg_cpc, 2)
    conv_rate = _hash_percent(f"{keyword}-conv", 2.0, 10.0)
    conversions = round(clicks * (conv_rate / 100))

    return {
        "keyword": keyword,
        "impressions": impressions,
        "clicks": clicks,
        "ctr_percent": ctr,
        "avg_cpc_pkr": avg_cpc,
        "cost_pkr": cost,
        "conversions": conversions,
    }


def build_report(campaign_plan):
    keyword_rows = [
        generate_mock_keyword_performance(k["keyword"])
        for ad_group in campaign_plan["ad_groups"]
        for k in ad_group["keywords"]
    ]

    total_impressions = sum(r["impressions"] for r in keyword_rows)
    total_clicks = sum(r["clicks"] for r in keyword_rows)
    total_cost = round(sum(r["cost_pkr"] for r in keyword_rows), 2)
    total_conversions = sum(r["conversions"] for r in keyword_rows)

    overall_ctr = round((total_clicks / total_impressions) * 100, 2) if total_impressions else 0
    overall_conv_rate = round((total_conversions / total_clicks) * 100, 2) if total_clicks else 0
    cost_per_conversion = round(total_cost / total_conversions, 2) if total_conversions else None

    return {
        "campaign_name": campaign_plan["campaign_name"],
        "report_period": REPORT_PERIOD,
        "summary": {
            "impressions": total_impressions,
            "clicks": total_clicks,
            "ctr_percent": overall_ctr,
            "cost_pkr": total_cost,
            "conversions": total_conversions,
            "conversion_rate_percent": overall_conv_rate,
            "cost_per_conversion_pkr": cost_per_conversion,
        },
        "by_keyword": keyword_rows,
    }


def fetch_report_real(*args, **kwargs):
    """Placeholder for pulling real performance data from a live campaign. Requires Basic Access."""
    raise NotImplementedError(
        "Real performance data requires the campaign to be live in Google Ads, "
        "which requires Basic Access. Use the simulated report until then."
    )


def run():
    campaign_plan = load_json(CAMPAIGN_INPUT_PATH)
    report = build_report(campaign_plan)

    os.makedirs("output", exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    s = report["summary"]
    print(f"Saved performance report to {OUTPUT_PATH}")
    print(f"  Campaign: {report['campaign_name']} ({report['report_period']})")
    print(f"  Impressions: {s['impressions']}  |  Clicks: {s['clicks']}  |  CTR: {s['ctr_percent']}%")
    print(f"  Cost: Rs.{s['cost_pkr']}  |  Conversions: {s['conversions']}  |  Cost/Conv: Rs.{s['cost_per_conversion_pkr']}")

    return report


if __name__ == "__main__":
    run()
