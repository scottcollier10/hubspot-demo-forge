import json
import os
import tempfile
from forge.config import load_profile, ProfileValidationError


class TestLoadProfile:
    def test_load_json(self, tmp_path):
        profile = {
            "company": {"name": "Test", "industry": "SaaS", "size": "startup", "icp": "devs"},
            "counts": {"companies": 5, "contacts_per_company": [2, 4], "deals": 10},
            "pipeline": {
                "id": "default",
                "stages": {
                    "warm": {"id": "qualifiedtobuy", "weight": 0.4},
                    "at_risk": {"id": "contractsent", "weight": 0.4},
                    "dormant": {"id": "presentationscheduled", "weight": 0.2},
                },
                "close_date_offsets": {"warm": 30, "at_risk": -5, "dormant": -45},
                "temp_stage": "appointmentscheduled",
            },
            "properties": {"canon": True, "engagement": True},
        }
        path = tmp_path / "test.json"
        path.write_text(json.dumps(profile))
        result = load_profile(str(path))
        assert result["company"]["name"] == "Test"
        assert result["counts"]["companies"] == 5

    def test_load_missing_file(self):
        try:
            load_profile("/nonexistent/path.json")
            assert False, "Should have raised"
        except FileNotFoundError:
            pass

    def test_validation_missing_company(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text(json.dumps({"counts": {}}))
        try:
            load_profile(str(path))
            assert False, "Should have raised"
        except ProfileValidationError:
            pass

    def test_validation_stage_weights_sum_to_one(self, tmp_path):
        profile = {
            "company": {"name": "T", "industry": "S", "size": "s", "icp": "x"},
            "counts": {"companies": 1, "contacts_per_company": [1, 1], "deals": 1},
            "pipeline": {
                "id": "default",
                "stages": {
                    "warm": {"id": "a", "weight": 0.5},
                    "at_risk": {"id": "b", "weight": 0.5},
                    "dormant": {"id": "c", "weight": 0.5},
                },
                "close_date_offsets": {"warm": 30, "at_risk": -5, "dormant": -45},
                "temp_stage": "appointmentscheduled",
            },
            "properties": {"canon": True, "engagement": True},
        }
        path = tmp_path / "bad_weights.json"
        path.write_text(json.dumps(profile))
        try:
            load_profile(str(path))
            assert False, "Should have raised"
        except ProfileValidationError as e:
            assert "weight" in str(e).lower()

    def test_properties_optional(self, tmp_path):
        """Full-portal profiles don't need properties key."""
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
        path = tmp_path / "no_props.json"
        path.write_text(json.dumps(profile))
        result = load_profile(str(path))
        assert result["properties"]["preset"] == "default"
        assert result["properties"]["sets"] == []

    def test_contacts_per_company_range(self, tmp_path):
        profile = {
            "company": {"name": "T", "industry": "S", "size": "s", "icp": "x"},
            "counts": {"companies": 5, "contacts_per_company": [2, 6], "deals": 10},
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
            "properties": {"canon": True, "engagement": True},
        }
        path = tmp_path / "range.json"
        path.write_text(json.dumps(profile))
        result = load_profile(str(path))
        lo, hi = result["counts"]["contacts_per_company"]
        assert lo == 2
        assert hi == 6
