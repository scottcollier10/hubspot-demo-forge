"""Legacy compatibility contract — the behaviors Forge intentionally supports.

This file is a single, identifiable location for the backward-compatibility
promises made to existing users with legacy profile configs. If a refactor
causes any of these tests to fail, it is breaking a public contract.

What is backward compatible:
  - Legacy config syntax (canon/engagement booleans) still loads
  - Canon namespace (canon_* contact/company, engagement_* deal) preserved
  - Deprecation warning emitted for legacy format
  - Mixed old + new syntax rejected cleanly

What was intentionally changed (NOT covered here):
  - Enum wire values changed to stable machine values (e.g., "vp" not "VP")
  - Derivation functions return logical dicts, not prefixed HubSpot dicts

Unit-level migration tests live in test_config_migration.py.
Unit-level derivation tests live in test_engage_derivation.py.
This file tests the cross-layer contract: legacy config → migration →
preset resolution → correct HubSpot names on output.
"""

import json
import sys
import warnings

import pytest

from forge.config import load_profile, ProfileValidationError
from forge.engage import derive_fit_fields, generate_engagement_values
from forge.hubspot_adapter import build_property_schemas, serialize_for_hubspot


# -- Helpers --

def _make_profile(tmp_path, properties_config):
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


class TestLegacyConfigSyntaxAccepted:
    """Legacy {canon: bool, engagement: bool} loads and maps to canon preset."""

    def test_canon_true_maps_to_canon_preset_with_fit(self, tmp_path):
        result = load_profile(_make_profile(tmp_path, {"canon": True}))
        assert result["properties"]["preset"] == "canon"
        assert "fit" in result["properties"]["sets"]

    def test_engagement_true_maps_to_engagement_set(self, tmp_path):
        result = load_profile(_make_profile(tmp_path, {"canon": False, "engagement": True}))
        assert result["properties"]["preset"] == "canon"
        assert result["properties"]["sets"] == ["engagement"]


class TestCanonNamespacePreserved:
    """The canon preset produces canon_* contact/company names and
    engagement_* deal names — matching existing Canon pipeline expectations."""

    def test_contact_fit_uses_canon_prefix(self):
        schemas = build_property_schemas(["fit"], "canon")
        contact_names = {s["name"] for s in schemas["contacts"]}
        assert "canon_seniority" in contact_names
        assert "canon_department" in contact_names
        assert "canon_persona" in contact_names

    def test_company_fit_uses_canon_prefix(self):
        schemas = build_property_schemas(["fit"], "canon")
        company_names = {s["name"] for s in schemas["companies"]}
        assert "canon_industry" in company_names

    def test_deal_engagement_uses_engagement_prefix(self):
        """Deal engagement properties use engagement_*, not canon_*."""
        schemas = build_property_schemas(["engagement"], "canon")
        deal_names = {s["name"] for s in schemas["deals"]}
        assert "engagement_health_score" in deal_names
        assert "engagement_status" in deal_names
        # NOT canon_health_score or canon_status
        assert not any(n.startswith("canon_") for n in deal_names)

    def test_serialized_values_use_canon_names(self):
        contact = {"id": "1", "properties": {"jobtitle": "CEO", "email": "a@b.com"}}
        logical = derive_fit_fields(contact)
        serialized = serialize_for_hubspot(logical, ["fit"], "canon")
        assert "canon_seniority" in serialized
        assert "canon_department" in serialized
        assert "forge_seniority" not in serialized


class TestLegacyDeprecationWarning:
    """Legacy format emits a deprecation warning to stderr."""

    def test_deprecation_warning_on_legacy_format(self, tmp_path, capsys):
        load_profile(_make_profile(tmp_path, {"canon": True, "engagement": True}))
        captured = capsys.readouterr()
        assert "deprecated" in captured.err.lower() or "legacy" in captured.err.lower()


class TestMixedSyntaxRejected:
    """Combining old and new syntax is an error, not a silent merge."""

    def test_canon_plus_preset_raises(self, tmp_path):
        with pytest.raises(ProfileValidationError, match="[Mm]ix"):
            load_profile(_make_profile(tmp_path, {
                "canon": True, "preset": "default", "sets": ["fit"],
            }))

    def test_engagement_plus_sets_raises(self, tmp_path):
        with pytest.raises(ProfileValidationError, match="[Mm]ix"):
            load_profile(_make_profile(tmp_path, {
                "engagement": True, "sets": ["engagement"],
            }))


class TestLegacyFullPipeline:
    """End-to-end: legacy config → migration → derivation → serialization
    with correct canon_* names and string wire format."""

    def test_legacy_config_through_full_pipeline(self, tmp_path):
        # Load legacy config
        result = load_profile(_make_profile(tmp_path, {"canon": True, "engagement": True}))
        preset = result["properties"]["preset"]
        sets = result["properties"]["sets"]

        # Derive + serialize
        contact = {"id": "1", "properties": {"jobtitle": "VP of Marketing", "email": "a@b.com"}}
        fit = derive_fit_fields(contact)
        engagement = generate_engagement_values(1)
        serialized = serialize_for_hubspot({**fit, **engagement}, sets, preset)

        # Fit uses canon_* names
        assert "canon_seniority" in serialized
        assert "canon_department" in serialized

        # Engagement contact props use canon_* names
        assert "canon_engagement_score" in serialized

        # All values are strings (HubSpot wire format)
        for key, value in serialized.items():
            assert isinstance(value, str), f"{key} should be str, got {type(value).__name__}"
