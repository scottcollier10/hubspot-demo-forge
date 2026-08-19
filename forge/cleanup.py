"""Cleanup — search for and remove forge-created demo data.

Safety: only touches records with forge_source property set.
Never modifies pipeline config, reports, dashboards, or lead scoring.
"""

from forge.client import BATCH_LIMIT

# Object types that carry the forge_source property
TRACKED_TYPES = ["contacts", "companies", "deals", "tickets", "products"]

# Deletion order: dependents first, then parents
DELETION_ORDER = [
    "line_items",
    "calls",
    "emails",
    "meetings",
    "notes",
    "deals",
    "tickets",
    "contacts",
    "companies",
    "products",
]

# Which tracked type owns which dependent types (via association)
_DEPENDENT_MAP = {
    "deals": ["line_items"],
    "contacts": ["calls", "emails", "meetings", "notes"],
}


def discover_forge_records(client, session_id: str | None = None) -> dict[str, list[str]]:
    """Find all forge-created records and their dependents.

    Returns {object_type: [record_ids]} for every type in DELETION_ORDER.
    """
    results: dict[str, list[str]] = {}

    # Step 1: Search tracked types for forge_source
    if session_id:
        forge_filter = {
            "propertyName": "forge_source",
            "operator": "EQ",
            "value": session_id,
        }
    else:
        forge_filter = {
            "propertyName": "forge_source",
            "operator": "HAS_PROPERTY",
        }

    for obj_type in TRACKED_TYPES:
        records = _search_forge_records(client, obj_type, forge_filter)
        results[obj_type] = [r["id"] for r in records]

    # Step 2: Find dependents via batch association lookup
    for parent_type, dep_types in _DEPENDENT_MAP.items():
        parent_ids = results.get(parent_type, [])
        for dep_type in dep_types:
            dep_ids = _batch_association_lookup(client, parent_type, parent_ids, dep_type)
            results[dep_type] = dep_ids

    return results


def _search_forge_records(client, obj_type: str, forge_filter: dict) -> list[dict]:
    """Search for forge-tagged records. Handles missing properties and permissions."""
    results = []
    after = None

    while True:
        body = {
            "filterGroups": [{"filters": [forge_filter]}],
            "properties": ["forge_source"],
            "limit": 100,
        }
        if after:
            body["after"] = after

        data, status = client.post(f"/crm/v3/objects/{obj_type}/search", body)

        if status == 400:
            print(f"  {obj_type}: forge_source property not created yet (skipping)")
            return []
        if status == 403:
            print(f"  {obj_type}: no API access (skipping)")
            return []
        if status != 200:
            print(f"  {obj_type}: search error {status} (skipping)")
            return []

        results.extend(data.get("results", []))

        paging = data.get("paging", {})
        after = paging.get("next", {}).get("after")
        if not after:
            break

    if results:
        print(f"  {obj_type}: {len(results)} records")
    else:
        print(f"  {obj_type}: 0")

    return results


def _batch_association_lookup(
    client, from_type: str, from_ids: list[str], to_type: str,
) -> list[str]:
    """Batch lookup associated object IDs."""
    if not from_ids:
        return []

    all_ids: set[str] = set()
    for i in range(0, len(from_ids), BATCH_LIMIT):
        chunk = from_ids[i : i + BATCH_LIMIT]
        data, status = client.post(
            f"/crm/v4/associations/{from_type}/{to_type}/batch/read",
            {"inputs": [{"id": fid} for fid in chunk]},
        )
        if status == 200:
            for result in data.get("results", []):
                for assoc in result.get("to", []):
                    all_ids.add(str(assoc["toObjectId"]))
        client.throttle()

    return list(all_ids)


def cleanup_forge_records(
    client,
    records_by_type: dict[str, list[str]],
    dry_run: bool = False,
) -> dict[str, int]:
    """Archive forge records in dependency order.

    Returns {object_type: count_deleted}.
    """
    deleted: dict[str, int] = {}

    for obj_type in DELETION_ORDER:
        ids = records_by_type.get(obj_type, [])
        if not ids:
            continue

        if dry_run:
            print(f"  would archive: {len(ids)} {obj_type}")
            deleted[obj_type] = len(ids)
            continue

        print(f"  archiving: {len(ids)} {obj_type}...")
        ok = client.batch_archive(obj_type, ids)
        if ok:
            deleted[obj_type] = len(ids)
            print(f"    OK — {len(ids)} {obj_type} archived")
        else:
            print(f"    FAILED — {obj_type} archive error")
            deleted[obj_type] = 0

    return deleted
