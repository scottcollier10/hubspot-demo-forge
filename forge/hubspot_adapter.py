"""HubSpot adapter — schema building and value serialization.

This is the only layer that knows HubSpot API specifics for custom
properties. It converts logical field definitions + preset mappings
into HubSpot property schemas and serializes logical values for
batch update payloads.

See docs/architecture.md (HubSpot Adapter).
"""

from datetime import date, datetime, timezone

from forge.field_registry import FIELDS
from forge.presets import resolve, PRESETS, PresetError


# Maps registry object_type to HubSpot's default property group name.
# V1 uses HubSpot's built-in groups. Custom groups (e.g., forge_fit)
# can be added later without changing the registry or presets.
OBJECT_TYPE_GROUPS: dict[str, str] = {
    "contact": "contactinformation",
    "company": "companyinformation",
    "deal": "dealinformation",
}

# Maps registry object_type to HubSpot API plural path segment
_API_OBJECT_TYPES: dict[str, str] = {
    "contact": "contacts",
    "company": "companies",
    "deal": "deals",
}


def build_property_schemas(
    enabled_sets: list[str],
    preset_name: str,
) -> dict[str, list[dict]]:
    """Build HubSpot property schemas for enabled sets.

    Returns {api_object_type: [schema_dict, ...]}, e.g.:
    {"contacts": [...], "companies": [...], "deals": [...]}
    """
    if preset_name not in PRESETS:
        raise PresetError(f"Unknown preset: '{preset_name}'")

    preset = PRESETS[preset_name]
    result: dict[str, list[dict]] = {}

    for logical_name, field in FIELDS.items():
        if field["set"] not in enabled_sets:
            continue

        # Explicit missing-mapping guard
        if logical_name not in preset:
            raise PresetError(
                f"Field '{logical_name}' has no mapping in preset '{preset_name}'"
            )
        hubspot_name = preset[logical_name]
        api_type = _API_OBJECT_TYPES[field["object_type"]]
        group_name = OBJECT_TYPE_GROUPS[field["object_type"]]

        schema: dict = {
            "name": hubspot_name,
            "label": field["label"],
            "type": field["type"],
            "fieldType": field["field_type"],
            "groupName": group_name,
            "description": field["description"],
        }

        if field["type"] == "enumeration" and "options" in field:
            schema["options"] = [
                {
                    "label": opt["label"],
                    "value": opt["value"],
                    "displayOrder": i,
                    "hidden": False,
                }
                for i, opt in enumerate(field["options"])
            ]

        result.setdefault(api_type, []).append(schema)

    return result


def serialize_for_hubspot(
    logical_values: dict,
    enabled_sets: list[str],
    preset_name: str,
) -> dict[str, str]:
    """Serialize logical values for HubSpot batch update payload.

    Applies preset name mapping, filters by enabled sets, omits None,
    validates enum values, and converts all values to strings.
    """
    # Use resolve() for name mapping + set filtering + None omission
    resolved = resolve(preset_name, enabled_sets, logical_values)

    # Build a reverse lookup: hubspot_name -> logical_name
    preset = PRESETS[preset_name]
    reverse: dict[str, str] = {}
    for logical_name, value in logical_values.items():
        if value is None:
            continue
        if logical_name in FIELDS and FIELDS[logical_name]["set"] in enabled_sets:
            reverse[preset[logical_name]] = logical_name

    # Serialize each value based on its registry type
    serialized: dict[str, str] = {}
    for hubspot_name, value in resolved.items():
        logical_name = reverse[hubspot_name]
        field = FIELDS[logical_name]
        serialized[hubspot_name] = _serialize_value(value, field, logical_name)

    return serialized


def _serialize_value(value, field: dict, logical_name: str) -> str:
    """Convert a single logical value to its HubSpot wire representation.

    Enforces type correctness — rejects invalid Python types rather than
    silently calling str(). This catches bugs at the serialization boundary
    instead of sending garbage to HubSpot.
    """
    field_type = field["type"]

    if field_type == "enumeration":
        if not isinstance(value, str):
            raise TypeError(
                f"Field '{logical_name}' (enumeration) expected str, got {type(value).__name__}"
            )
        allowed = {opt["value"] for opt in field.get("options", [])}
        if value not in allowed:
            raise ValueError(
                f"'{value}' is not a valid option for field '{logical_name}'. "
                f"Allowed: {sorted(allowed)}"
            )
        return value

    if field_type == "number":
        if not isinstance(value, (int, float)):
            raise TypeError(
                f"Field '{logical_name}' (number) expected int or float, got {type(value).__name__}"
            )
        return str(value)

    if field_type == "date":
        if not isinstance(value, date) or isinstance(value, datetime):
            raise TypeError(
                f"Field '{logical_name}' (date) expected date, got {type(value).__name__}"
            )
        return value.isoformat()

    if field_type == "datetime":
        if not isinstance(value, datetime):
            raise TypeError(
                f"Field '{logical_name}' (datetime) expected datetime, got {type(value).__name__}"
            )
        if value.tzinfo is None:
            raise TypeError(
                f"Field '{logical_name}' (datetime) requires timezone-aware "
                f"datetime, got naive"
            )
        return value.astimezone(timezone.utc).isoformat()

    if field_type == "bool":
        if not isinstance(value, bool):
            raise TypeError(
                f"Field '{logical_name}' (bool) expected bool, got {type(value).__name__}"
            )
        return str(value).lower()

    if field_type == "string":
        if not isinstance(value, str):
            raise TypeError(
                f"Field '{logical_name}' (string) expected str, got {type(value).__name__}"
            )
        return value

    raise ValueError(f"Unknown field type '{field_type}' for field '{logical_name}'")
