"""HubSpot custom property creation — delegates to field registry + adapter.

The forge_source tracking property is handled separately as
infrastructure metadata outside the registry/preset system.
"""

import json
from forge.hubspot_adapter import build_property_schemas


# -- Forge tracking property (infrastructure, not in registry) --

FORGE_TRACKED_TYPES = ["contacts", "companies", "deals", "tickets", "products"]

_FORGE_GROUP_NAMES = {
    "contacts": "contactinformation",
    "companies": "companyinformation",
    "deals": "dealinformation",
    "tickets": "ticketinformation",
    "products": "productinformation",
}


def get_forge_tracking_property(object_type: str) -> dict:
    """Return the forge_source property definition for a given object type."""
    return {
        "name": "forge_source",
        "label": "Forge Source",
        "type": "string",
        "fieldType": "text",
        "groupName": _FORGE_GROUP_NAMES[object_type],
        "description": "Session ID from hubspot-demo-forge (do not edit manually)",
    }


def get_properties_for_profile(profile: dict) -> dict[str, list[dict]]:
    """Return {api_object_type: [property_schemas]} based on profile config.

    Delegates to field registry + adapter. The profile's preset and sets
    determine which properties are created and what names they use.
    """
    props_config = profile.get("properties", {})
    preset = props_config.get("preset", "default")
    sets = props_config.get("sets", [])

    if not sets:
        return {}

    return build_property_schemas(sets, preset)


def create_all_properties(client, object_type: str, properties: list[dict]) -> tuple[int, int, int]:
    """Create properties for an object type, skipping existing ones.

    Returns (created, skipped, failed).
    """
    existing_data = client.get(f"/crm/v3/properties/{object_type}")
    existing = {p["name"] for p in existing_data.get("results", [])}

    created = 0
    skipped = 0
    failed = 0

    for prop in properties:
        name = prop["name"]

        if name in existing:
            print(f"  SKIP  {name} (already exists)")
            skipped += 1
            continue

        _, status = client.post(f"/crm/v3/properties/{object_type}", prop)

        if status in (200, 201):
            print(f"  OK    {name}")
            created += 1
        elif status == 409:
            print(f"  SKIP  {name} (conflict)")
            skipped += 1
        else:
            print(f"  FAIL  {name} ({status}: {json.dumps(_)[:200]})")
            failed += 1

        client.throttle()

    return created, skipped, failed
