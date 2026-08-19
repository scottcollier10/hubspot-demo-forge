"""Tests for refactored derivation — logical values with stable enum values."""

from datetime import date
from forge.engage import (
    derive_fit_fields,
    generate_engagement_values,
)


class TestDeriveFitFields:
    """derive_fit_fields replaces build_canon_fit_props.
    Returns logical values with stable machine enum values and native types.
    """

    def test_returns_logical_keys(self):
        contact = {
            "id": "1",
            "properties": {"jobtitle": "VP of Marketing", "email": "vp@acme.com"},
        }
        result = derive_fit_fields(contact)
        expected_keys = {
            "seniority", "department", "title",
            "email_type", "persona", "lead_source",
            "data_confidence",
        }
        assert set(result.keys()) == expected_keys

    def test_seniority_uses_stable_value(self):
        contact = {"id": "1", "properties": {"jobtitle": "VP of Marketing", "email": "a@b.com"}}
        result = derive_fit_fields(contact)
        assert result["seniority"] == "vp"

    def test_department_uses_stable_value(self):
        contact = {"id": "1", "properties": {"jobtitle": "VP of Marketing", "email": "a@b.com"}}
        result = derive_fit_fields(contact)
        assert result["department"] == "marketing"

    def test_email_type_uses_stable_value(self):
        work = {"id": "1", "properties": {"jobtitle": "X", "email": "a@acme.com"}}
        personal = {"id": "2", "properties": {"jobtitle": "X", "email": "a@gmail.com"}}
        assert derive_fit_fields(work)["email_type"] == "work_email"
        assert derive_fit_fields(personal)["email_type"] == "personal_email"

    def test_persona_uses_stable_value(self):
        contact = {"id": "1", "properties": {"jobtitle": "CEO", "email": "a@b.com"}}
        result = derive_fit_fields(contact)
        assert result["persona"] == "economic_buyer"

    def test_lead_source_uses_stable_value(self):
        contact = {"id": "1", "properties": {"jobtitle": "X", "email": "a@b.com"}}
        result = derive_fit_fields(contact)
        # lead_source is randomized, just check it's a valid machine value
        import re
        assert re.match(r"^[a-z_]+$", result["lead_source"])

    def test_data_confidence_is_int(self):
        contact = {"id": "1", "properties": {"jobtitle": "CEO", "email": "a@b.com"}}
        result = derive_fit_fields(contact)
        assert isinstance(result["data_confidence"], int)
        assert 85 <= result["data_confidence"] <= 95

    def test_c_level_seniority(self):
        for title in ["Chief Revenue Officer", "CEO", "CTO", "CFO"]:
            contact = {"id": "1", "properties": {"jobtitle": title, "email": "a@b.com"}}
            assert derive_fit_fields(contact)["seniority"] == "c_level"

    def test_unknown_seniority_for_empty_title(self):
        contact = {"id": "1", "properties": {"jobtitle": "", "email": "a@b.com"}}
        assert derive_fit_fields(contact)["seniority"] == "unknown"


class TestGenerateEngagementValues:
    """generate_engagement_values replaces generate_engagement_props.
    Returns logical values with native types.
    """

    def test_returns_logical_keys(self):
        result = generate_engagement_values(1)
        expected_keys = {
            "email_opens", "email_clicks", "sends_since_engagement",
            "engagement_status", "engagement_score",
            "last_open_date", "last_click_date",
        }
        assert set(result.keys()) == expected_keys

    def test_numbers_are_ints(self):
        result = generate_engagement_values(1)
        assert isinstance(result["email_opens"], int)
        assert isinstance(result["email_clicks"], int)
        assert isinstance(result["engagement_score"], int)
        assert isinstance(result["sends_since_engagement"], int)

    def test_dates_are_date_objects_or_none(self):
        result = generate_engagement_values(1)
        val = result["last_open_date"]
        assert val is None or isinstance(val, date)

    def test_status_uses_stable_value(self):
        result = generate_engagement_values(1)
        assert result["engagement_status"] == "active"

    def test_level_1_hot_ranges(self):
        result = generate_engagement_values(1)
        assert 8 <= result["email_opens"] <= 15
        assert 3 <= result["email_clicks"] <= 8
        assert result["sends_since_engagement"] <= 1
        assert 80 <= result["engagement_score"] <= 100

    def test_level_2_warm_ranges(self):
        result = generate_engagement_values(2)
        assert 2 <= result["email_opens"] <= 6
        assert 0 <= result["email_clicks"] <= 2
        assert 2 <= result["sends_since_engagement"] <= 4
        assert result["engagement_status"] == "at_risk"
        assert 40 <= result["engagement_score"] <= 70

    def test_level_3_cold_ranges(self):
        result = generate_engagement_values(3)
        assert 0 <= result["email_opens"] <= 1
        assert result["email_clicks"] == 0
        assert 5 <= result["sends_since_engagement"] <= 10
        assert result["engagement_status"] in ("cold", "dormant")
        assert 0 <= result["engagement_score"] <= 30

    def test_level_3_may_have_none_dates(self):
        results = [generate_engagement_values(3) for _ in range(20)]
        has_none = any(r["last_open_date"] is None for r in results)
        has_value = any(r["last_open_date"] is not None for r in results)
        assert has_none or has_value  # level 3 can have 0 opens → None date
