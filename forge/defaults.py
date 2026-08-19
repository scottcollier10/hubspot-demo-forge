"""Smart defaults for profile config — fills missing keys before validation."""

import copy

TICKET_DEFAULTS = {
    "pipeline": "0",  # HubSpot's default ticket pipeline ID
    "statuses": {"open": 0.4, "waiting": 0.3, "closed": 0.3},
}

PRODUCT_DEFAULTS = {
    "price_range": [5000, 50000],
    "line_items_per_deal": [1, 3],
}

ACTIVITY_DEFAULTS = {
    "types": ["call", "email", "meeting", "note"],
    "recency_days": 90,
}


def apply_defaults(profile: dict) -> dict:
    """Apply smart defaults to a profile, filling missing optional keys.

    Does not overwrite explicitly set values.
    """
    p = copy.deepcopy(profile)

    counts = p.get("counts", {})
    counts.setdefault("tickets", 0)
    counts.setdefault("products", 0)
    counts.setdefault("activities_per_contact", 0)
    p["counts"] = counts

    if counts["tickets"] > 0:
        p.setdefault("tickets", {})
        for k, v in TICKET_DEFAULTS.items():
            p["tickets"].setdefault(k, v)

    if counts["products"] > 0:
        p.setdefault("products", {})
        for k, v in PRODUCT_DEFAULTS.items():
            p["products"].setdefault(k, v)

    if counts["activities_per_contact"] not in (0, [0, 0]):
        p.setdefault("activities", {})
        for k, v in ACTIVITY_DEFAULTS.items():
            p["activities"].setdefault(k, v)

    p.setdefault("properties", {})

    return p
