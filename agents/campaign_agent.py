"""
Campaign Agent (Phase 5)

Takes the AI-written ad copy (output/ad_copy.json) -- already segmented into
themed ad groups by ad_writing_agent -- and assembles a complete campaign
plan -- budget, targeting, ad groups, keyword match types, and each ad
group's responsive search ad -- in the same shape a real Google Ads
campaign would need. One ad group is emitted per theme instead of lumping
every keyword into a single flat group.

push_campaign_real() pushes that plan to a real Google Ads account via the
real API (CampaignBudgetService, CampaignService, AdGroupService, etc). It
works against a Google Ads Test Account with just the pending/test-tier
developer token -- no Basic Access needed -- since test accounts allow full
create/read/update/delete on campaigns, ad groups, ads, and keywords; they
just never serve to real users and never spend real money. Real Keyword
Planner data and real performance metrics still require Basic Access on a
real account, and are out of scope for this function.
"""

import json
import os
import time
import re
import sys

from google.ads.googleads.client import GoogleAdsClient

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents._shared import STOPWORDS, hash_range, load_json

AD_COPY_INPUT_PATH = os.path.join("output", "ad_copy.json")
NEGATIVE_KEYWORDS_INPUT_PATH = os.path.join("output", "negative_keywords.json")
OUTPUT_PATH = os.path.join("output", "campaign_plan.json")

GOOGLE_ADS_YAML_PATH = "google-ads.yaml"
GEO_TARGET_CONSTANT = "geoTargetConstants/2586"    # Pakistan
LANGUAGE_CONSTANT = "languageConstants/1000"       # English

TARGET_LOCATION = "Pakistan"
TARGET_LANGUAGE = "English"
NETWORK = "SEARCH"
DEFAULT_STATUS = "PAUSED"  # created paused -- safe default, requires manual review before going live
MIN_DAILY_BUDGET = 300   # Rs. -- fallback range used only when the owner doesn't provide a real budget
MAX_DAILY_BUDGET = 1500


def extract_business_name(business_description, max_words=3):
    words = re.findall(r"[a-zA-Z']+", business_description.lower())
    significant = [w for w in words if w not in STOPWORDS and len(w) > 2]
    return " ".join(w.title() for w in significant[:max_words]) or "Business"


def assign_match_type(keyword):
    return ["EXACT", "PHRASE", "BROAD"][hash_range(keyword, 0, 2)]


def build_campaign_plan(business_description, ad_copy, negative_keywords=None, monthly_budget=None, website_url=None):
    business_name = extract_business_name(business_description)

    if monthly_budget:
        daily_budget = round(monthly_budget / 30)
    else:
        daily_budget = hash_range(business_name, MIN_DAILY_BUDGET, MAX_DAILY_BUDGET)

    ad_groups = []
    for i, group in enumerate(ad_copy.get("ad_groups", []), start=1):
        group_name = group.get("name") or f"Ad Group {i}"
        ad_groups.append({
            "ad_group_name": f"{business_name} - {group_name}",
            "keywords": [
                {"keyword": kw, "match_type": assign_match_type(kw)}
                for kw in group.get("keywords", [])
            ],
            "responsive_search_ad": {
                "headlines": group.get("headlines", []),
                "descriptions": group.get("descriptions", []),
            },
        })

    return {
        "campaign_name": f"{business_name} - Search Campaign",
        "status": DEFAULT_STATUS,
        "network": NETWORK,
        "daily_budget_pkr": daily_budget,
        "monthly_budget_pkr": monthly_budget or daily_budget * 30,
        "bidding_strategy": "MAXIMIZE_CLICKS",
        "target_location": TARGET_LOCATION,
        "target_language": TARGET_LANGUAGE,
        "website_url": (website_url or "").strip(),
        "negative_keywords": negative_keywords or [],
        "ad_groups": ad_groups,
    }


def push_campaign_real(plan, customer_id=None):
    """Push an assembled campaign plan to a real Google Ads account via the
    real API. Intended for a Google Ads Test Account: creates real Campaign,
    Ad Group, Keyword, and Ad objects, but nothing serves to real users and
    no money is spent. The campaign itself is created PAUSED regardless.

    customer_id must be the Test Account's own customer ID (digits only, no
    dashes) -- create the test account first under your Google Ads manager
    account, then pass its ID here or set GOOGLE_ADS_TEST_CUSTOMER_ID.

    Returns a dict of the resource names Google assigned to everything
    created, so the caller can confirm what landed.
    """
    customer_id = (customer_id or os.environ.get("GOOGLE_ADS_TEST_CUSTOMER_ID") or "").replace("-", "")
    if not customer_id:
        raise RuntimeError(
            "No customer_id given. Create a Google Ads Test Account first, then "
            "pass its customer ID to push_campaign_real() or set GOOGLE_ADS_TEST_CUSTOMER_ID."
        )
    if not plan.get("website_url"):
        raise ValueError(
            "plan['website_url'] is required -- a responsive search ad needs a landing "
            "page URL. Re-run campaign_agent.run() with website_url set."
        )

    final_url = plan["website_url"]
    if not final_url.startswith("http"):
        final_url = f"https://{final_url}"

    client = GoogleAdsClient.load_from_storage(GOOGLE_ADS_YAML_PATH)
    created = {"budget": None, "campaign": None, "ad_groups": []}

    # 1. Campaign budget -- one shared daily budget for the whole campaign.
    budget_service = client.get_service("CampaignBudgetService")
    budget_op = client.get_type("CampaignBudgetOperation")
    # Budget names must be unique per account -- a timestamp suffix keeps retries
    # and repeat pushes of the same business from colliding with earlier attempts.
    budget_op.create.name = f"{plan['campaign_name']} Budget {int(time.time())}"
    budget_op.create.amount_micros = plan["daily_budget_pkr"] * 1_000_000
    budget_op.create.delivery_method = client.enums.BudgetDeliveryMethodEnum.STANDARD
    budget_response = budget_service.mutate_campaign_budgets(customer_id=customer_id, operations=[budget_op])
    budget_resource_name = budget_response.results[0].resource_name
    created["budget"] = budget_resource_name

    # 2. Campaign -- Search network only, Maximize Clicks bidding, created PAUSED.
    campaign_service = client.get_service("CampaignService")
    campaign_op = client.get_type("CampaignOperation")
    campaign = campaign_op.create
    campaign.name = plan["campaign_name"]
    campaign.campaign_budget = budget_resource_name
    campaign.status = client.enums.CampaignStatusEnum.PAUSED
    campaign.advertising_channel_type = client.enums.AdvertisingChannelTypeEnum.SEARCH
    campaign.network_settings.target_google_search = True
    campaign.network_settings.target_search_network = False
    campaign.network_settings.target_content_network = False
    campaign.network_settings.target_partner_search_network = False
    campaign.target_spend = client.get_type("TargetSpend")  # "Maximize Clicks" bidding strategy
    campaign.contains_eu_political_advertising = (
        client.enums.EuPoliticalAdvertisingStatusEnum.DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING
    )
    campaign_response = campaign_service.mutate_campaigns(customer_id=customer_id, operations=[campaign_op])
    campaign_resource_name = campaign_response.results[0].resource_name
    created["campaign"] = campaign_resource_name

    # 3. Campaign-level targeting (location + language) and negative keywords.
    criterion_service = client.get_service("CampaignCriterionService")
    location_op = client.get_type("CampaignCriterionOperation")
    location_op.create.campaign = campaign_resource_name
    location_op.create.location.geo_target_constant = GEO_TARGET_CONSTANT
    language_op = client.get_type("CampaignCriterionOperation")
    language_op.create.campaign = campaign_resource_name
    language_op.create.language.language_constant = LANGUAGE_CONSTANT
    criterion_ops = [location_op, language_op]

    for neg in plan.get("negative_keywords", []):
        neg_op = client.get_type("CampaignCriterionOperation")
        neg_op.create.campaign = campaign_resource_name
        neg_op.create.negative = True
        neg_op.create.keyword.text = neg["keyword"]
        neg_op.create.keyword.match_type = getattr(
            client.enums.KeywordMatchTypeEnum, neg.get("match_type", "BROAD"),
            client.enums.KeywordMatchTypeEnum.BROAD,
        )
        criterion_ops.append(neg_op)
    criterion_service.mutate_campaign_criteria(customer_id=customer_id, operations=criterion_ops)

    # 4. One ad group per theme, with its keywords and its responsive search ad.
    ad_group_service = client.get_service("AdGroupService")
    ad_group_criterion_service = client.get_service("AdGroupCriterionService")
    ad_group_ad_service = client.get_service("AdGroupAdService")

    for group in plan["ad_groups"]:
        ag_op = client.get_type("AdGroupOperation")
        ag_op.create.name = group["ad_group_name"]
        ag_op.create.campaign = campaign_resource_name
        ag_op.create.status = client.enums.AdGroupStatusEnum.ENABLED
        ag_op.create.type_ = client.enums.AdGroupTypeEnum.SEARCH_STANDARD
        ag_response = ad_group_service.mutate_ad_groups(customer_id=customer_id, operations=[ag_op])
        ag_resource_name = ag_response.results[0].resource_name

        keyword_ops = []
        for kw in group["keywords"]:
            kw_op = client.get_type("AdGroupCriterionOperation")
            kw_op.create.ad_group = ag_resource_name
            kw_op.create.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
            kw_op.create.keyword.text = kw["keyword"]
            kw_op.create.keyword.match_type = getattr(
                client.enums.KeywordMatchTypeEnum, kw["match_type"], client.enums.KeywordMatchTypeEnum.BROAD
            )
            keyword_ops.append(kw_op)
        if keyword_ops:
            ad_group_criterion_service.mutate_ad_group_criteria(customer_id=customer_id, operations=keyword_ops)

        ad_op = client.get_type("AdGroupAdOperation")
        ad_op.create.ad_group = ag_resource_name
        ad_op.create.status = client.enums.AdGroupAdStatusEnum.ENABLED
        rsa = ad_op.create.ad.responsive_search_ad
        for headline in group["responsive_search_ad"]["headlines"]:
            asset = client.get_type("AdTextAsset")
            asset.text = headline
            rsa.headlines.append(asset)
        for description in group["responsive_search_ad"]["descriptions"]:
            asset = client.get_type("AdTextAsset")
            asset.text = description
            rsa.descriptions.append(asset)
        ad_op.create.ad.final_urls.append(final_url)
        ad_response = ad_group_ad_service.mutate_ad_group_ads(customer_id=customer_id, operations=[ad_op])

        created["ad_groups"].append({
            "ad_group_name": group["ad_group_name"],
            "ad_group_resource_name": ag_resource_name,
            "ad_resource_name": ad_response.results[0].resource_name,
            "keywords_created": len(keyword_ops),
        })

    return created


def run(business_description, push_live=False, monthly_budget=None, website_url=None, customer_id=None):
    ad_copy = load_json(AD_COPY_INPUT_PATH)

    try:
        negative_keywords = load_json(NEGATIVE_KEYWORDS_INPUT_PATH)
    except FileNotFoundError:
        negative_keywords = []
        print("No negative_keywords.json found -- run negative_keyword_agent.py first for a fuller plan. Continuing without it.")

    plan = build_campaign_plan(business_description, ad_copy, negative_keywords, monthly_budget, website_url)

    os.makedirs("output", exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2)

    total_keywords = sum(len(g["keywords"]) for g in plan["ad_groups"])
    print(f"Saved campaign plan to {OUTPUT_PATH}")
    print(f"  Campaign: {plan['campaign_name']}")
    print(f"  Daily budget: Rs.{plan['daily_budget_pkr']}")
    print(f"  Ad groups: {len(plan['ad_groups'])}")
    print(f"  Keywords across ad groups: {total_keywords}")
    print(f"  Negative keywords: {len(plan['negative_keywords'])}")

    if push_live:
        result = push_campaign_real(plan, customer_id=customer_id)
        print(f"Pushed to Google Ads test account: {result['campaign']}")

    return plan


if __name__ == "__main__":
    description = input("Enter your business description: ")
    run(description)
