"""Tests for preset resolution — logical names to HubSpot property names."""

import pytest
from forge.presets import (
    PRESETS,
    resolve,
    validate_preset_completeness,
    PresetError,
)
from forge.field_registry import FIELDS


class TestPresetCompleteness:
    """Built-in presets must cover all registry fields."""

    def test_default_preset_covers_all_fields(self):
        missing = set(FIELDS.keys()) - set(PRESETS["default"].keys())
        assert not missing, f"default preset missing fields: {missing}"

    def test_canon_preset_covers_all_fields(self):
        missing = set(FIELDS.keys()) - set(PRESETS["canon"].keys())
        assert not missing, f"canon preset missing fields: {missing}"

    def test_default_preset_has_no_extra_fields(self):
        extra = set(PRESETS["default"].keys()) - set(FIELDS.keys())
        assert not extra, f"default preset has fields not in registry: {extra}"

    def test_canon_preset_has_no_extra_fields(self):
        extra = set(PRESETS["canon"].keys()) - set(FIELDS.keys())
        assert not extra, f"canon preset has fields not in registry: {extra}"

    def test_validate_preset_completeness_passes_for_builtins(self):
        """Should not raise for built-in presets."""
        for name in PRESETS:
            validate_preset_completeness(name)

    def test_default_uses_forge_prefix(self):
        for logical_name, hubspot_name in PRESETS["default"].items():
            assert hubspot_name.startswith("forge_"), \
                f"default['{logical_name}'] = '{hubspot_name}' doesn't start with forge_"

    def test_canon_contact_fit_uses_canon_prefix(self):
        """Canon contact fit fields use canon_* prefix."""
        contact_fit = {n for n, f in FIELDS.items()
                       if f["object_type"] == "contact" and f["set"] == "fit"}
        for name in contact_fit:
            assert PRESETS["canon"][name].startswith("canon_"), \
                f"canon['{name}'] should use canon_ prefix"


class TestPresetNoDuplicateNames:
    def test_default_no_duplicate_hubspot_names(self):
        names = list(PRESETS["default"].values())
        assert len(names) == len(set(names)), "default preset has duplicate HubSpot names"

    def test_canon_no_duplicate_hubspot_names(self):
        names = list(PRESETS["canon"].values())
        assert len(names) == len(set(names)), "canon preset has duplicate HubSpot names"


class TestResolve:
    def test_resolve_maps_names(self):
        logical = {"seniority": "vp", "department": "marketing"}
        result = resolve("default", ["fit"], logical)
        assert result == {"forge_seniority": "vp", "forge_department": "marketing"}

    def test_resolve_filters_by_enabled_sets(self):
        logical = {"seniority": "vp", "engagement_score": 87}
        result = resolve("default", ["fit"], logical)
        assert "forge_seniority" in result
        assert "forge_engagement_score" not in result

    def test_resolve_with_multiple_sets(self):
        logical = {"seniority": "vp", "engagement_score": 87}
        result = resolve("default", ["fit", "engagement"], logical)
        assert "forge_seniority" in result
        assert "forge_engagement_score" in result

    def test_resolve_with_canon_preset(self):
        logical = {"seniority": "vp"}
        result = resolve("canon", ["fit"], logical)
        assert result == {"canon_seniority": "vp"}

    def test_resolve_omits_none_values(self):
        logical = {"seniority": "vp", "department": None}
        result = resolve("default", ["fit"], logical)
        assert "forge_seniority" in result
        assert "forge_department" not in result

    def test_resolve_unknown_preset_raises(self):
        with pytest.raises(PresetError, match="Unknown preset"):
            resolve("nonexistent", ["fit"], {"seniority": "vp"})

    def test_resolve_unknown_field_raises(self):
        with pytest.raises(PresetError, match="not in field registry"):
            resolve("default", ["fit"], {"nonexistent_field": "value"})

    def test_resolve_empty_sets_returns_empty(self):
        result = resolve("default", [], {"seniority": "vp"})
        assert result == {}

    def test_resolve_preserves_value_types(self):
        """Values pass through without type conversion."""
        logical = {"engagement_score": 87, "email_opens": 12}
        result = resolve("default", ["engagement"], logical)
        assert result["forge_engagement_score"] == 87
        assert result["forge_email_opens"] == 12
