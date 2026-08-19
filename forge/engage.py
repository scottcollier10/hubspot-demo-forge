"""Engagement simulation — derive fit properties and generate engagement data."""

import re
import random
from datetime import date, timedelta


# -- Title-to-field mapping (keyword-based, forge generates clean titles) --

# Keywords that are short acronyms need whole-word matching to avoid
# false positives (e.g. "cto" inside "director"). Phrases and longer
# words are safe for simple substring matching.
_WORD_BOUNDARY_KEYWORDS = {
    "ceo", "cto", "cfo", "coo", "cmo", "cro", "cio", "cpo",
    "vp", "mgr", "eng",
    "bdr", "sdr",
    "ops", "hr",
    "ux", "ui",
    "csm",
}

SENIORITY_RULES = [
    (["chief", "ceo", "cto", "cfo", "coo", "cmo", "cro", "cio", "cpo"], "c_level"),
    (["vp", "vice president"], "vp"),
    (["director", "dir."], "director"),
    (["manager", "mgr"], "manager"),
]

DEPARTMENT_RULES = [
    (["marketing", "mktg", "demand gen", "brand", "content"], "marketing"),
    (["sales", "account exec", "business development", "bdr", "sdr"], "sales"),
    (["engineering", "software", "developer", "devops", "sre", "eng"], "engineering"),
    (["finance", "cfo", "accounting", "controller"], "finance"),
    (["operations", "ops", "coo"], "operations"),
    (["hr", "human resources", "people", "talent"], "hr"),
    (["product", "cpo", "product manager"], "product"),
    (["design", "ux", "ui", "creative"], "design"),
    (["customer success", "cs manager", "csm"], "customer_success"),
    (["ceo", "cto", "cmo", "cro", "cio", "president", "founder"], "executive"),
]


def _kw_match(keyword, text):
    """Match keyword in text. Uses word boundaries for short acronyms."""
    if keyword in _WORD_BOUNDARY_KEYWORDS:
        return bool(re.search(r'\b' + re.escape(keyword) + r'\b', text))
    return keyword in text


def derive_seniority(title: str) -> str:
    """Map a job title to a seniority level (stable machine value)."""
    if not title:
        return "unknown"
    lower = title.lower()
    for keywords, seniority in SENIORITY_RULES:
        for kw in keywords:
            if _kw_match(kw, lower):
                return seniority
    return "individual_contributor"


def derive_department(title: str) -> str:
    """Map a job title to a department (stable machine value)."""
    if not title:
        return "unknown"
    lower = title.lower()
    for keywords, dept in DEPARTMENT_RULES:
        for kw in keywords:
            if _kw_match(kw, lower):
                return dept
    return "other"


# -- Engagement level assignment --

PYRAMID = {1: 0.20, 2: 0.30, 3: 0.50}  # hot / warm / cold

ENGAGEMENT_RANGES = {
    1: {  # hot
        "email_opens": (8, 15),
        "email_clicks": (3, 8),
        "sends_since_engagement": (0, 1),
        "open_recency_days": (1, 7),
        "click_recency_days": (1, 7),
        "engagement_status": "active",
        "engagement_score": (80, 100),
    },
    2: {  # warm
        "email_opens": (2, 6),
        "email_clicks": (0, 2),
        "sends_since_engagement": (2, 4),
        "open_recency_days": (8, 30),
        "click_recency_days": (15, 45),
        "engagement_status": "at_risk",
        "engagement_score": (40, 70),
    },
    3: {  # cold
        "email_opens": (0, 1),
        "email_clicks": (0, 0),
        "sends_since_engagement": (5, 10),
        "open_recency_days": (60, 90),
        "click_recency_days": None,  # no clicks
        "engagement_status": ("cold", "dormant"),
        "engagement_score": (0, 30),
    },
}


def assign_engagement_levels(contacts: list[dict]) -> dict[int, list[dict]]:
    """Shuffle contacts and split into engagement levels by pyramid ratio."""
    shuffled = list(contacts)
    random.shuffle(shuffled)

    n = len(shuffled)
    cut1 = round(n * PYRAMID[1])
    cut2 = cut1 + round(n * PYRAMID[2])

    return {
        1: shuffled[:cut1],
        2: shuffled[cut1:cut2],
        3: shuffled[cut2:],
    }


def generate_engagement_values(level: int) -> dict:
    """Generate engagement values for a given level.
    Returns logical values with native Python types.
    """
    r = ENGAGEMENT_RANGES[level]
    opens = random.randint(*r["email_opens"])
    clicks = random.randint(*r["email_clicks"])
    sends = random.randint(*r["sends_since_engagement"])
    score = random.randint(*r["engagement_score"])

    status = r["engagement_status"]
    if isinstance(status, tuple):
        status = random.choice(status)

    today = date.today()

    last_open = None
    if opens > 0 and r["open_recency_days"]:
        days_ago = random.randint(*r["open_recency_days"])
        last_open = today - timedelta(days=days_ago)

    last_click = None
    if clicks > 0 and r["click_recency_days"]:
        days_ago = random.randint(*r["click_recency_days"])
        last_click = today - timedelta(days=days_ago)

    return {
        "email_opens": opens,
        "email_clicks": clicks,
        "sends_since_engagement": sends,
        "engagement_status": status,
        "engagement_score": score,
        "last_open_date": last_open,
        "last_click_date": last_click,
    }


# -- Fit field derivation --

PERSONAL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
    "aol.com", "icloud.com", "mail.com", "protonmail.com",
}

PERSONA_MAP = {
    ("c_level", "executive"): "economic_buyer",
    ("c_level", "finance"): "economic_buyer",
    ("c_level", "operations"): "economic_buyer",
    ("vp", "sales"): "economic_buyer",
    ("vp", "marketing"): "champion",
    ("vp", "engineering"): "technical_evaluator",
    ("vp", "product"): "champion",
    ("director", "engineering"): "technical_evaluator",
    ("director", "sales"): "champion",
    ("director", "marketing"): "champion",
    ("manager", "engineering"): "technical_evaluator",
    ("manager", "sales"): "end_user",
    ("manager", "marketing"): "end_user",
    ("manager", "customer_success"): "end_user",
}

LEAD_SOURCES = [
    "organic_search", "paid_search", "paid_social",
    "content_download", "webinar", "partner_referral",
    "customer_referral", "direct", "event", "outbound",
]


def derive_fit_fields(contact: dict) -> dict:
    """Derive fit fields from a contact's HubSpot data.
    Returns logical values with stable enum values and native types.
    """
    props = contact.get("properties", {})
    title = props.get("jobtitle", "") or ""
    email = props.get("email", "") or ""

    seniority = derive_seniority(title)
    department = derive_department(title)

    domain = email.split("@")[-1].lower() if "@" in email else ""
    email_type = "personal_email" if domain in PERSONAL_DOMAINS else "work_email"

    persona = PERSONA_MAP.get((seniority, department), "influencer")
    lead_source = random.choice(LEAD_SOURCES)
    confidence = random.randint(85, 95)

    return {
        "seniority": seniority,
        "department": department,
        "title": title,
        "email_type": email_type,
        "persona": persona,
        "lead_source": lead_source,
        "data_confidence": confidence,
    }


# -- Main engage command logic --

CONTACT_FETCH_PROPERTIES = [
    "email", "firstname", "lastname", "jobtitle", "company",
]


def cmd_engage_contacts(
    client,
    preset: str = "default",
    enabled_sets: list[str] | None = None,
    dry_run: bool = False,
    limit: int | None = None,
    all_contacts: bool = False,
) -> dict:
    """Fetch forge-owned contacts, assign engagement levels, update properties.

    By default, only operates on contacts with forge_source set. Pass
    all_contacts=True to include all contacts (portal-wide mode).

    Returns summary dict: {total, hot, warm, cold}.
    """
    if enabled_sets is None:
        enabled_sets = ["fit", "engagement"]

    print("\n-- Fetching contacts " + "-" * 34)

    if all_contacts:
        print("  WARNING: --all mode — updating ALL contacts in the portal")
        filter_groups = []
    else:
        filter_groups = [{
            "filters": [{
                "propertyName": "forge_source",
                "operator": "HAS_PROPERTY",
            }]
        }]

    contacts = client.fetch_all("/crm/v3/objects/contacts/search", {
        "filterGroups": filter_groups,
        "properties": CONTACT_FETCH_PROPERTIES,
        "sorts": [{"propertyName": "createdate", "direction": "ASCENDING"}],
    })
    print(f"  Found {len(contacts)} contacts")

    if limit and len(contacts) > limit:
        contacts = contacts[:limit]
        print(f"  Limited to {limit} contacts")

    if not contacts:
        print("  Nothing to do.")
        return {"total": 0, "hot": 0, "warm": 0, "cold": 0}

    # Assign engagement levels
    levels = assign_engagement_levels(contacts)
    summary = {
        "total": len(contacts),
        "hot": len(levels[1]),
        "warm": len(levels[2]),
        "cold": len(levels[3]),
    }

    print(f"\n-- Engagement distribution " + "-" * 28)
    print(f"  Level 1 (hot):  {summary['hot']}")
    print(f"  Level 2 (warm): {summary['warm']}")
    print(f"  Level 3 (cold): {summary['cold']}")

    # Build update payloads using new architecture
    from forge.hubspot_adapter import serialize_for_hubspot

    updates = []
    for level, level_contacts in levels.items():
        for contact in level_contacts:
            logical = {}
            if "fit" in enabled_sets:
                logical.update(derive_fit_fields(contact))
            if "engagement" in enabled_sets:
                logical.update(generate_engagement_values(level))

            serialized = serialize_for_hubspot(logical, enabled_sets, preset)
            updates.append({"id": contact["id"], "properties": serialized})

    if dry_run:
        print("\n  --dry-run: skipping HubSpot updates")
        for u in updates[:3]:
            print(f"\n  Sample: contact {u['id']}")
            for k, v in u["properties"].items():
                if v:
                    print(f"    {k}: {v}")
        return summary

    # Batch update
    print("\n-- Updating contacts " + "-" * 34)
    success = client.batch_update("contacts", updates)
    if success:
        print(f"  Updated {len(updates)} contacts")
    else:
        print("  ERROR: batch update failed")

    return summary
