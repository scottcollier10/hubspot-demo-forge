"""End-to-end integration tests — verify full pipeline produces correct output.

These tests exercise: profile loading → config migration → derivation →
preset resolution → adapter serialization. No HubSpot API calls.
"""

import json
import pytest
from forge.config import load_profile
from forge.engage import derive_fit_fields, generate_engagement_values
from forge.hubspot_adapter import build_property_schemas, serialize_for_hubspot


class TestDefaultPresetPipeline:
    def test_fit_properties_use_forge_names(self, tmp_path):
        profile = _make_profile(tmp_path, {"preset": "default", "sets": ["fit", "engagement"]})
        result = load_profile(profile)
        schemas = build_property_schemas(
            result["properties"]["sets"],
            result["properties"]["preset"],
        )
        contact_names = {s["name"] for s in schemas.get("contacts", [])}
        assert "forge_seniority" in contact_names
        assert "forge_engagement_score" in contact_names
        assert "canon_seniority" not in contact_names

    def test_serialized_values_use_forge_names(self):
        contact = {"id": "1", "properties": {"jobtitle": "VP of Marketing", "email": "a@b.com"}}
        logical = derive_fit_fields(contact)
        serialized = serialize_for_hubspot(logical, ["fit"], "default")
        assert "forge_seniority" in serialized
        assert serialized["forge_seniority"] == "vp"

    def test_engagement_values_serialize_correctly(self):
        logical = generate_engagement_values(1)
        serialized = serialize_for_hubspot(logical, ["engagement"], "default")
        assert "forge_engagement_score" in serialized
        assert "forge_email_opens" in serialized
        # Numbers become strings
        assert isinstance(serialized["forge_engagement_score"], str)


class TestCanonPresetPipeline:
    def test_fit_properties_use_canon_names(self, tmp_path):
        profile = _make_profile(tmp_path, {"preset": "canon", "sets": ["fit"]})
        result = load_profile(profile)
        schemas = build_property_schemas(
            result["properties"]["sets"],
            result["properties"]["preset"],
        )
        contact_names = {s["name"] for s in schemas.get("contacts", [])}
        assert "canon_seniority" in contact_names
        assert "forge_seniority" not in contact_names

    def test_serialized_values_use_canon_names(self):
        contact = {"id": "1", "properties": {"jobtitle": "CEO", "email": "a@b.com"}}
        logical = derive_fit_fields(contact)
        serialized = serialize_for_hubspot(logical, ["fit"], "canon")
        assert "canon_seniority" in serialized
        assert serialized["canon_seniority"] == "c_level"

    def test_deal_engagement_uses_legacy_names(self):
        """Canon deal engagement properties use engagement_* not canon_*."""
        schemas = build_property_schemas(["engagement"], "canon")
        deal_names = {s["name"] for s in schemas.get("deals", [])}
        assert "engagement_health_score" in deal_names
        assert "engagement_status" in deal_names


class TestLegacyMigrationPipeline:
    """The highest-risk path: legacy config → migration → canon output."""

    def test_legacy_canon_true_produces_canon_schemas(self, tmp_path):
        profile = _make_profile(tmp_path, {"canon": True, "engagement": True})
        result = load_profile(profile)
        assert result["properties"]["preset"] == "canon"
        assert set(result["properties"]["sets"]) == {"fit", "engagement"}
        schemas = build_property_schemas(
            result["properties"]["sets"],
            result["properties"]["preset"],
        )
        contact_names = {s["name"] for s in schemas.get("contacts", [])}
        assert "canon_seniority" in contact_names
        assert "canon_engagement_score" in contact_names

    def test_legacy_engagement_only_produces_canon_engagement(self, tmp_path):
        profile = _make_profile(tmp_path, {"canon": False, "engagement": True})
        result = load_profile(profile)
        assert result["properties"]["preset"] == "canon"
        assert result["properties"]["sets"] == ["engagement"]
        schemas = build_property_schemas(
            result["properties"]["sets"],
            result["properties"]["preset"],
        )
        # Should have engagement contact props but no fit contact props
        contact_names = {s["name"] for s in schemas.get("contacts", [])}
        assert "canon_engagement_score" in contact_names
        assert "canon_seniority" not in contact_names

    def test_legacy_full_pipeline_derivation_to_serialization(self, tmp_path):
        """Full path: legacy config → migration → derivation → serialization."""
        profile = _make_profile(tmp_path, {"canon": True, "engagement": True})
        result = load_profile(profile)
        preset = result["properties"]["preset"]
        sets = result["properties"]["sets"]

        # Derive fit fields
        contact = {"id": "1", "properties": {"jobtitle": "VP of Marketing", "email": "a@b.com"}}
        fit = derive_fit_fields(contact)
        engagement = generate_engagement_values(1)

        # Merge and serialize
        logical = {**fit, **engagement}
        serialized = serialize_for_hubspot(logical, sets, preset)

        # Fit fields use canon_* names
        assert "canon_seniority" in serialized
        assert serialized["canon_seniority"] == "vp"
        assert "canon_department" in serialized
        assert serialized["canon_department"] == "marketing"

        # Engagement fields use canon_* names
        assert "canon_engagement_score" in serialized
        assert "canon_email_opens" in serialized

        # All values are strings (HubSpot wire format)
        for k, v in serialized.items():
            assert isinstance(v, str), f"{k} should be str, got {type(v).__name__}"

        # Enum values are stable machine values, not display labels
        assert serialized["canon_seniority"] == "vp"  # not "VP"
        assert serialized["canon_engagement_status"] == "active"  # not "Active"


class TestNoPropertySets:
    def test_empty_sets_produces_no_schemas(self, tmp_path):
        profile = _make_profile(tmp_path, {"preset": "default", "sets": []})
        result = load_profile(profile)
        schemas = build_property_schemas(
            result["properties"]["sets"],
            result["properties"]["preset"],
        )
        assert schemas == {}

    def test_no_properties_key_produces_no_schemas(self, tmp_path):
        profile = _make_profile(tmp_path, None)
        result = load_profile(profile)
        schemas = build_property_schemas(
            result["properties"]["sets"],
            result["properties"]["preset"],
        )
        assert schemas == {}


def _make_profile(tmp_path, properties_config):
    """Write a minimal profile and return its path."""
    profile = {
        "company": {"name": "T", "industry": "S", "size": "s", "icp": "x"},
        "counts": {"companies": 5, "contacts_per_company": [2, 4], "deals": 10},
        "pipeline": {
            "id": "default",
            "stages": {
                "warm": {"id": "a", "weight": 0.4},
                "at_risk": {"id": "b", "weight": 0.4},
                "dormant": {"id": "c", "weight": 0.2},
            },
            "close_date_offsets": {"warm": 30, "at_risk": -5, "dormant": -45},
            "temp_stage": "appointmentscheduled",
        },
    }
    if properties_config is not None:
        profile["properties"] = properties_config
    path = tmp_path / "test.json"
    path.write_text(json.dumps(profile))
    return str(path)
