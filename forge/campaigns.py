"""Campaign seeding — curated demo campaigns from CSV data.

Combines two operations into one command:
1. Create campaigns via Marketing API
2. Generate demo email performance CSV
"""

import csv
import io
import os
from datetime import datetime, timedelta
from pathlib import Path

# Resolve data directory relative to this module
DATA_DIR = Path(__file__).parent.parent / "data"


def _load_campaigns_csv() -> list[dict]:
    """Load campaign seed data from CSV."""
    csv_path = DATA_DIR / "campaigns.csv"
    with open(csv_path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _shift_dates(rows: list[dict]) -> list[dict]:
    """Shift all campaign dates so the midpoint lands near today.

    Preserves relative spacing between campaigns.
    """
    dates = []
    for row in rows:
        start = row.get("Campaign start date", "").strip()
        end = row.get("Campaign end date", "").strip()
        if start:
            dates.append(datetime.strptime(start, "%Y-%m-%d"))
        if end:
            dates.append(datetime.strptime(end, "%Y-%m-%d"))

    if not dates:
        return rows

    earliest = min(dates)
    latest = max(dates)
    original_midpoint = earliest + (latest - earliest) / 2
    today = datetime.now()
    offset = today - original_midpoint

    shifted = []
    for row in rows:
        row = dict(row)
        start = row.get("Campaign start date", "").strip()
        end = row.get("Campaign end date", "").strip()
        if start:
            new_start = datetime.strptime(start, "%Y-%m-%d") + offset
            row["Campaign start date"] = new_start.strftime("%Y-%m-%d")
        if end:
            new_end = datetime.strptime(end, "%Y-%m-%d") + offset
            row["Campaign end date"] = new_end.strftime("%Y-%m-%d")
        shifted.append(row)

    return shifted


def _fetch_existing_campaign_names(client) -> set[str]:
    """Fetch all existing campaign names for duplicate checking."""
    names = set()
    after = None
    while True:
        url = "/marketing/v3/campaigns?limit=100"
        if after:
            url += f"&after={after}"
        data = client.get(url)
        for item in data.get("results", []):
            name = (
                (item.get("properties") or {}).get("hs_name")
                or item.get("hs_name")
                or item.get("name")
            )
            if name:
                names.add(name.strip().lower())
        after = data.get("paging", {}).get("next", {}).get("after")
        if not after:
            break
    return names


def seed_campaigns(client, original_dates: bool = False, dry_run: bool = False) -> dict[str, str]:
    """Create campaigns from CSV data. Returns {campaign_name: campaign_id} map."""
    print("\n-- Campaigns " + "-" * 42)
    rows = _load_campaigns_csv()

    if not original_dates:
        rows = _shift_dates(rows)
        print("  Dates auto-shifted to present")

    if dry_run:
        for row in rows:
            print(f"  [dry-run] {row.get('Campaign name', '?')} ({row.get('Campaign start date', '?')} - {row.get('Campaign end date', '?')})")
        print(f"  --- {len(rows)} campaigns (dry-run)")
        return {}

    # Check for duplicates
    print("  Checking for existing campaigns...")
    existing = _fetch_existing_campaign_names(client)
    print(f"  Found {len(existing)} existing campaigns")

    campaign_id_map = {}
    created = 0
    skipped = 0

    for row in rows:
        name = row.get("Campaign name", "").strip()
        if name.lower() in existing:
            print(f"  SKIP  {name} (already exists)")
            skipped += 1
            continue

        props = {"hs_name": name}
        start = row.get("Campaign start date", "").strip()
        end = row.get("Campaign end date", "").strip()
        notes = row.get("Campaign notes", "").strip()
        audience = row.get("Campaign audience", "").strip()
        currency = row.get("Currency code", "").strip()

        if start:
            props["hs_start_date"] = start
        if end:
            props["hs_end_date"] = end
        if notes:
            props["hs_notes"] = notes
        if audience:
            props["hs_audience"] = audience
        if currency:
            props["hs_currency_code"] = currency

        result, status = client.post("/marketing/v3/campaigns", {"properties": props})

        if status in (200, 201):
            cid = result.get("id") or result.get("campaignGuid") or ""
            campaign_id_map[name] = cid
            created += 1
            print(f"  created: {name} ({start} - {end})")
        else:
            print(f"  ERROR {status}: {name}")

        client.throttle()

    print(f"  --- {created} created, {skipped} skipped")
    return campaign_id_map


# ── Email CSV Generation ──────────────────────────────────────────────────

DEMO_EMAILS = [
    {"name": "Spring Webinar — Save Your Spot", "subject": "Seats are filling fast — Marketing Automation 101 (April 8)", "date": "2026-03-18", "recipients": 94, "delivered": 93, "open_rate_pct": 31.2, "click_rate_pct": 4.8, "bounces": 1, "unsubs": 0},
    {"name": "Customer Re-Engagement — We noticed", "subject": "It's been a while — here's what's changed", "date": "2026-03-10", "recipients": 38, "delivered": 37, "open_rate_pct": 28.9, "click_rate_pct": 7.9, "bounces": 1, "unsubs": 0},
    {"name": "Content Engine — AI Ops Roundup (Feb)", "subject": "5 ways AI is reshaping ops teams in 2026", "date": "2026-02-28", "recipients": 86, "delivered": 85, "open_rate_pct": 22.3, "click_rate_pct": 2.6, "bounces": 1, "unsubs": 1},
    {"name": "Product Launch Countdown — Teaser", "subject": "Something big is coming May 1st", "date": "2026-03-20", "recipients": 94, "delivered": 93, "open_rate_pct": 29.4, "click_rate_pct": 2.1, "bounces": 1, "unsubs": 0},
    {"name": "Thought Leadership Newsletter — March", "subject": "Why most RevOps teams are flying blind in Q2", "date": "2026-03-05", "recipients": 89, "delivered": 88, "open_rate_pct": 24.7, "click_rate_pct": 1.8, "bounces": 1, "unsubs": 1},
    {"name": "Content Engine — AI Ops Roundup (Mar)", "subject": "The automation gap: are you falling behind?", "date": "2026-03-14", "recipients": 85, "delivered": 83, "open_rate_pct": 17.6, "click_rate_pct": 1.4, "bounces": 2, "unsubs": 1},
    {"name": "Free Trial Conversion — Activation Nudge", "subject": "You haven't connected your HubSpot yet", "date": "2026-03-22", "recipients": 22, "delivered": 21, "open_rate_pct": 14.3, "click_rate_pct": 0.0, "bounces": 1, "unsubs": 0},
    {"name": "Q2 Demand Gen — Early Access Invite", "subject": "You're on the early access list for [Product]", "date": "2026-03-25", "recipients": 94, "delivered": 87, "open_rate_pct": 19.1, "click_rate_pct": 1.9, "bounces": 7, "unsubs": 2},
]

EMAIL_FIELDNAMES = [
    "Email Name", "Subject Line", "Send Date", "Status", "Recipients",
    "Delivered", "Delivered %", "Open Rate", "Click Rate", "Click-through Rate",
    "Bounces", "Bounce %", "Unsubscribes", "Unsubscribe %",
]


def generate_email_csv(output_path: str):
    """Generate demo email performance CSV."""
    print(f"\n-- Email CSV " + "-" * 42)
    rows = []
    for e in DEMO_EMAILS:
        recipients = e["recipients"]
        delivered = e["delivered"]
        opens = round(recipients * e["open_rate_pct"] / 100)
        clicks = round(recipients * e["click_rate_pct"] / 100)
        ctr = round(clicks / opens * 100, 1) if opens > 0 else 0.0

        rows.append({
            "Email Name": e["name"],
            "Subject Line": e["subject"],
            "Send Date": e["date"],
            "Status": "Sent",
            "Recipients": recipients,
            "Delivered": delivered,
            "Delivered %": f"{round(delivered / recipients * 100, 1)}%",
            "Open Rate": f"{e['open_rate_pct']}%",
            "Click Rate": f"{e['click_rate_pct']}%",
            "Click-through Rate": f"{ctr}%",
            "Bounces": e["bounces"],
            "Bounce %": f"{round(e['bounces'] / recipients * 100, 1)}%",
            "Unsubscribes": e["unsubs"],
            "Unsubscribe %": f"{round(e['unsubs'] / recipients * 100, 1)}%",
        })

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=EMAIL_FIELDNAMES)
    writer.writeheader()
    writer.writerows(rows)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        f.write(output.getvalue())

    print(f"  Written: {output_path}")
    print(f"  {len(DEMO_EMAILS)} emails | {sum(e['recipients'] for e in DEMO_EMAILS)} total recipients")
