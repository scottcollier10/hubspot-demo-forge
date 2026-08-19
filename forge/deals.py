"""Deal seeding with stage distribution and stage-flip trick."""

import time
from datetime import datetime, timedelta


def assign_stages(deals: list[dict], pipeline_cfg: dict) -> dict[str, list[dict]]:
    """Split deals into stage buckets by weight.

    Returns {"warm": [...], "at_risk": [...], "dormant": [...]}.
    """
    total = len(deals)
    stages = pipeline_cfg["stages"]

    buckets = {}
    start = 0
    stage_names = list(stages.keys())

    for i, name in enumerate(stage_names):
        if i == len(stage_names) - 1:
            # Last bucket gets remainder to avoid rounding gaps
            buckets[name] = deals[start:]
        else:
            count = round(total * stages[name]["weight"])
            buckets[name] = deals[start : start + count]
            start += count

    return buckets


def seed_deals(client, deals: list[dict], pipeline_cfg: dict, forge_source: str = "") -> list[dict]:
    """Create deals with assigned stages and close dates.

    Returns list of {"id": hubspot_id, "dealstage": stage_id, "company_name": name}.
    """
    print("\n-- Deals " + "-" * 46)
    today = datetime.now()
    offsets = pipeline_cfg.get("close_date_offsets", {})
    pipeline_id = pipeline_cfg.get("id", "default")

    buckets = assign_stages(deals, pipeline_cfg)
    created_deals = []

    for bucket_name, bucket_deals in buckets.items():
        stage_id = pipeline_cfg["stages"][bucket_name]["id"]
        offset_days = offsets.get(bucket_name, 0)
        close_date = (today + timedelta(days=offset_days)).strftime("%Y-%m-%d")

        for deal in bucket_deals:
            props = {
                **deal,
                "dealstage": stage_id,
                "closedate": close_date,
                "pipeline": pipeline_id,
            }
            if forge_source:
                props["forge_source"] = forge_source
            # Remove non-HubSpot fields
            company_name = props.pop("company_name", None)

            result, status = client.post(
                "/crm/v3/objects/deals",
                {"properties": props},
            )

            if status in (200, 201):
                created_deals.append({
                    "id": result["id"],
                    "dealstage": stage_id,
                    "company_name": company_name,
                })
                print(f"  created: {deal.get('dealname', '?')} [{bucket_name}]")
            else:
                print(f"  ERROR {status}: {deal.get('dealname', '?')}")

            client.throttle()

    print(f"  --- {len(created_deals)} deals created")
    return created_deals


def flip_stages(client, deal_stage_map: dict[str, str], pipeline_cfg: dict):
    """Flip deals through temp stage to reset time-in-stage timestamps.

    deal_stage_map: {deal_id: target_stage_id}
    """
    temp_stage = pipeline_cfg.get("temp_stage", "appointmentscheduled")
    deal_ids = list(deal_stage_map.keys())

    if not deal_ids:
        return

    print("\n-- Stage Flip " + "-" * 41)
    print(f"  Flipping {len(deal_ids)} deals through '{temp_stage}'...")

    # Batch 1: move all to temp stage
    batch1 = [{"id": did, "properties": {"dealstage": temp_stage}} for did in deal_ids]
    ok = client.batch_update("deals", batch1)
    if not ok:
        print("  FAILED batch 1 — aborting stage flip")
        return

    print(f"    -> {len(deal_ids)} deals moved to temp stage")
    print("  Waiting 2s for HubSpot to stamp stage entry...")
    time.sleep(2)

    # Batch 2: move to target stages
    batch2 = [
        {"id": did, "properties": {"dealstage": stage}}
        for did, stage in deal_stage_map.items()
    ]
    ok = client.batch_update("deals", batch2)
    if not ok:
        print("  FAILED batch 2 — deals stuck in temp stage!")
        return

    print(f"    -> {len(deal_ids)} deals moved to target stages")
    print("  Time-in-stage reset complete")
