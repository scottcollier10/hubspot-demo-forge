"""Tests for profile config migration — legacy to new format."""

import json
import pytest
from forge.config import load_profile, ProfileValidationError


def _write_profile(tmp_path, properties_config, filename="test.json"):
    """Write a minimal valid profile with the given properties config."""
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
    path = tmp_path / filename
    path.write_text(json.dumps(profile))
    return str(path)


class TestLegacyMigration:
    def test_canon_true_engagement_true(self, tmp_path):
        path = _write_profile(tmp_path, {"canon": True, "engagement": True})
        result = load_profile(path)
        assert result["properties"]["preset"] == "canon"
        assert set(result["properties"]["sets"]) == {"fit", "engagement"}

    def test_canon_true_engagement_false(self, tmp_path):
        path = _write_profile(tmp_path, {"canon": True, "engagement": False})
        result = load_profile(path)
        assert result["properties"]["preset"] == "canon"
        assert result["properties"]["sets"] == ["fit"]

    def test_canon_false_engagement_true(self, tmp_path):
        path = _write_profile(tmp_path, {"canon": False, "engagement": True})
        result = load_profile(path)
        assert result["properties"]["preset"] == "canon"
        assert result["properties"]["sets"] == ["engagement"]

    def test_canon_false_engagement_false(self, tmp_path):
        path = _write_profile(tmp_path, {"canon": False, "engagement": False})
        result = load_profile(path)
        assert result["properties"]["preset"] == "canon"
        assert result["properties"]["sets"] == []


class TestNewFormat:
    def test_new_format_passthrough(self, tmp_path):
        path = _write_profile(tmp_path, {"preset": "default", "sets": ["fit"]})
        result = load_profile(path)
        assert result["properties"]["preset"] == "default"
        assert result["properties"]["sets"] == ["fit"]

    def test_preset_defaults_to_default(self, tmp_path):
        path = _write_profile(tmp_path, {"sets": ["fit"]})
        result = load_profile(path)
        assert result["properties"]["preset"] == "default"

    def test_sets_defaults_to_empty(self, tmp_path):
        path = _write_profile(tmp_path, {"preset": "default"})
        result = load_profile(path)
        assert result["properties"]["sets"] == []

    def test_no_properties_key(self, tmp_path):
        path = _write_profile(tmp_path, None)
        result = load_profile(path)
        assert result["properties"]["preset"] == "default"
        assert result["properties"]["sets"] == []


class TestMixedFormatRejection:
    def test_canon_plus_preset_raises(self, tmp_path):
        path = _write_profile(tmp_path, {
            "canon": True, "preset": "default", "sets": ["fit"]
        })
        with pytest.raises(ProfileValidationError, match="[Mm]ix"):
            load_profile(path)

    def test_engagement_plus_sets_raises(self, tmp_path):
        path = _write_profile(tmp_path, {
            "engagement": True, "sets": ["engagement"]
        })
        with pytest.raises(ProfileValidationError, match="[Mm]ix"):
            load_profile(path)


class TestPresetValidation:
    def test_unknown_preset_raises(self, tmp_path):
        path = _write_profile(tmp_path, {"preset": "nonexistent", "sets": ["fit"]})
        with pytest.raises(ProfileValidationError, match="[Uu]nknown preset"):
            load_profile(path)

    def test_unknown_set_raises(self, tmp_path):
        path = _write_profile(tmp_path, {"preset": "default", "sets": ["nonexistent"]})
        with pytest.raises(ProfileValidationError, match="[Uu]nknown.*set"):
            load_profile(path)


class TestTypeValidation:
    def test_legacy_canon_string_raises(self, tmp_path):
        """'canon: "true"' (string) must not be silently truthy."""
        path = _write_profile(tmp_path, {"canon": "true"})
        with pytest.raises(ProfileValidationError, match="boolean"):
            load_profile(path)

    def test_legacy_engagement_string_raises(self, tmp_path):
        path = _write_profile(tmp_path, {"engagement": "false"})
        with pytest.raises(ProfileValidationError, match="boolean"):
            load_profile(path)

    def test_sets_must_be_list(self, tmp_path):
        path = _write_profile(tmp_path, {"preset": "default", "sets": "fit"})
        with pytest.raises(ProfileValidationError, match="list"):
            load_profile(path)

    def test_sets_entries_must_be_strings(self, tmp_path):
        path = _write_profile(tmp_path, {"preset": "default", "sets": [123]})
        with pytest.raises(ProfileValidationError, match="string"):
            load_profile(path)

    def test_preset_must_be_string(self, tmp_path):
        path = _write_profile(tmp_path, {"preset": 42, "sets": ["fit"]})
        with pytest.raises(ProfileValidationError, match="string"):
            load_profile(path)
