"""Preset definitions — map logical field names to HubSpot property names.

A preset determines the HubSpot property namespace. The logical field
definitions (type, options, etc.) come from field_registry.py and are
shared across all presets.

See docs/architecture.md (Layer 3).
"""

from forge.field_registry import FIELDS


class PresetError(Exception):
    """Raised for preset configuration errors."""
    pass


PRESETS: dict[str, dict[str, str]] = {
    "default": {
        # fit / contact
        "title": "forge_title",
        "seniority": "forge_seniority",
        "department": "forge_department",
        "function": "forge_function",
        "data_confidence": "forge_data_confidence",
        "normalization_notes": "forge_normalization_notes",
        "email_type": "forge_email_type",
        "persona": "forge_persona",
        "lead_source": "forge_lead_source",
        # fit / company
        "company_domain": "forge_domain",
        "company_industry": "forge_industry",
        "company_employee_band": "forge_employee_band",
        # engagement / contact
        "engagement_score": "forge_engagement_score",
        "engagement_status": "forge_engagement_status",
        "email_opens": "forge_email_opens",
        "email_clicks": "forge_email_clicks",
        "sends_since_engagement": "forge_sends_since_engagement",
        "last_open_date": "forge_last_open_date",
        "last_click_date": "forge_last_click_date",
        # engagement / deal
        "deal_health_score": "forge_deal_health_score",
        "deal_engagement_status": "forge_deal_engagement_status",
        "deal_last_activity": "forge_deal_last_activity",
    },
    "canon": {
        # fit / contact
        "title": "canon_title",
        "seniority": "canon_seniority",
        "department": "canon_department",
        "function": "canon_function",
        "data_confidence": "canon_data_confidence",
        "normalization_notes": "canon_normalization_notes",
        "email_type": "canon_email_type",
        "persona": "canon_persona",
        "lead_source": "canon_lead_source",
        # fit / company
        "company_domain": "canon_domain",
        "company_industry": "canon_industry",
        "company_employee_band": "canon_employee_band",
        # engagement / contact
        "engagement_score": "canon_engagement_score",
        "engagement_status": "canon_engagement_status",
        "email_opens": "canon_email_opens",
        "email_clicks": "canon_email_clicks",
        "sends_since_engagement": "canon_sends_since_engagement",
        "last_open_date": "canon_last_open_date",
        "last_click_date": "canon_last_click_date",
        # engagement / deal (note: existing canon uses engagement_* not canon_*)
        "deal_health_score": "engagement_health_score",
        "deal_engagement_status": "engagement_status",
        "deal_last_activity": "engagement_last_activity",
    },
}


def resolve(
    preset_name: str,
    enabled_sets: list[str],
    logical_values: dict,
) -> dict:
    """Map logical field names + values to HubSpot property names.

    - Filters to only fields in enabled sets
    - Omits fields with None values
    - Fails fast on unknown preset, unknown fields, or name collisions
    """
    if preset_name not in PRESETS:
        raise PresetError(f"Unknown preset: '{preset_name}'")

    preset = PRESETS[preset_name]

    # Validate all logical keys exist in registry
    for key in logical_values:
        if key not in FIELDS:
            raise PresetError(f"Field '{key}' not in field registry")

    # Filter to enabled sets, skip None values
    result = {}
    seen_hubspot_names: dict[str, str] = {}  # hubspot_name -> logical_name

    for logical_name, value in logical_values.items():
        if value is None:
            continue

        field = FIELDS[logical_name]
        if field["set"] not in enabled_sets:
            continue

        # Explicit missing-mapping guard (not raw KeyError)
        if logical_name not in preset:
            raise PresetError(
                f"Field '{logical_name}' has no mapping in preset '{preset_name}'"
            )
        hubspot_name = preset[logical_name]

        # Collision check
        if hubspot_name in seen_hubspot_names:
            other = seen_hubspot_names[hubspot_name]
            raise PresetError(
                f"Collision: '{logical_name}' and '{other}' both map to "
                f"'{hubspot_name}' in preset '{preset_name}'"
            )
        seen_hubspot_names[hubspot_name] = logical_name

        result[hubspot_name] = value

    return result


def validate_preset_completeness(preset_name: str) -> None:
    """Validate a preset covers all fields in the registry.

    Call at startup or in tests, not at runtime (runtime only
    validates fields required by enabled sets).
    """
    if preset_name not in PRESETS:
        raise PresetError(f"Unknown preset: '{preset_name}'")

    preset = PRESETS[preset_name]
    missing = set(FIELDS.keys()) - set(preset.keys())
    if missing:
        raise PresetError(
            f"Preset '{preset_name}' missing mappings for: {sorted(missing)}"
        )

    extra = set(preset.keys()) - set(FIELDS.keys())
    if extra:
        raise PresetError(
            f"Preset '{preset_name}' has mappings for unknown fields: {sorted(extra)}"
        )
