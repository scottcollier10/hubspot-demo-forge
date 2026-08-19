"""Tests for HubSpot adapter — schema building + value serialization."""

import pytest
from datetime import date, datetime, timezone
from forge.hubspot_adapter import (
    build_property_schemas,
    serialize_for_hubspot,
    OBJECT_TYPE_GROUPS,
)


class TestBuildPropertySchemas:
    def test_returns_dict_keyed_by_object_type(self):
        result = build_property_schemas(["fit"], "default")
        assert isinstance(result, dict)
        assert "contacts" in result  # contact -> contacts for API

    def test_fit_set_includes_contact_and_company(self):
        result = build_property_schemas(["fit"], "default")
        assert "contacts" in result
        assert "companies" in result
        assert "deals" not in result

    def test_engagement_set_includes_contact_and_deal(self):
        result = build_property_schemas(["engagement"], "default")
        assert "contacts" in result
        assert "deals" in result
        # companies have no engagement fields
        assert "companies" not in result

    def test_both_sets_include_all_types(self):
        result = build_property_schemas(["fit", "engagement"], "default")
        assert "contacts" in result
        assert "companies" in result
        assert "deals" in result

    def test_schema_has_required_hubspot_fields(self):
        result = build_property_schemas(["fit"], "default")
        schema = result["contacts"][0]
        required = {"name", "label", "type", "fieldType", "groupName", "description"}
        assert required.issubset(set(schema.keys()))

    def test_schema_uses_preset_names(self):
        default_result = build_property_schemas(["fit"], "default")
        canon_result = build_property_schemas(["fit"], "canon")
        default_names = {s["name"] for s in default_result["contacts"]}
        canon_names = {s["name"] for s in canon_result["contacts"]}
        assert all(n.startswith("forge_") for n in default_names)
        # Canon contact fit should use canon_ prefix
        assert any(n.startswith("canon_") for n in canon_names)

    def test_enumeration_schema_has_options(self):
        result = build_property_schemas(["fit"], "default")
        seniority = next(
            s for s in result["contacts"] if s["name"] == "forge_seniority"
        )
        assert "options" in seniority
        assert len(seniority["options"]) == 6
        opt = seniority["options"][0]
        assert "label" in opt
        assert "value" in opt
        assert "displayOrder" in opt
        assert "hidden" in opt

    def test_empty_sets_returns_empty(self):
        result = build_property_schemas([], "default")
        assert result == {}

    def test_schema_count_matches_registry(self):
        result = build_property_schemas(["fit", "engagement"], "default")
        total = sum(len(schemas) for schemas in result.values())
        assert total == 22


class TestSerializeForHubspot:
    def test_number_to_string(self):
        result = serialize_for_hubspot(
            {"engagement_score": 87}, ["engagement"], "default"
        )
        assert result["forge_engagement_score"] == "87"

    def test_string_passthrough(self):
        result = serialize_for_hubspot(
            {"title": "VP of Marketing"}, ["fit"], "default"
        )
        assert result["forge_title"] == "VP of Marketing"

    def test_enum_passthrough(self):
        result = serialize_for_hubspot(
            {"seniority": "vp"}, ["fit"], "default"
        )
        assert result["forge_seniority"] == "vp"

    def test_date_to_iso(self):
        result = serialize_for_hubspot(
            {"last_open_date": date(2026, 8, 19)}, ["engagement"], "default"
        )
        assert result["forge_last_open_date"] == "2026-08-19"

    def test_datetime_rejected_for_date_field(self):
        """Date fields must receive date, not datetime."""
        with pytest.raises(TypeError, match="expected date"):
            serialize_for_hubspot(
                {"deal_last_activity": datetime(2026, 8, 19, 14, 30, tzinfo=timezone.utc)},
                ["engagement"], "default"
            )

    def test_wrong_type_for_number_raises(self):
        """Passing a string where a number is expected should fail."""
        with pytest.raises(TypeError, match="[Ee]xpected.*int|float"):
            serialize_for_hubspot(
                {"engagement_score": "not_a_number"}, ["engagement"], "default"
            )

    def test_wrong_type_for_date_raises(self):
        with pytest.raises(TypeError, match="[Ee]xpected.*date"):
            serialize_for_hubspot(
                {"last_open_date": "2026-08-19"}, ["engagement"], "default"
            )

    def test_none_omitted(self):
        result = serialize_for_hubspot(
            {"seniority": "vp", "department": None}, ["fit"], "default"
        )
        assert "forge_seniority" in result
        assert "forge_department" not in result

    def test_filters_by_enabled_sets(self):
        result = serialize_for_hubspot(
            {"seniority": "vp", "engagement_score": 87},
            ["fit"],
            "default",
        )
        assert "forge_seniority" in result
        assert "forge_engagement_score" not in result

    def test_canon_preset_maps_names(self):
        result = serialize_for_hubspot(
            {"seniority": "vp"}, ["fit"], "canon"
        )
        assert result == {"canon_seniority": "vp"}

    def test_validates_enum_values(self):
        with pytest.raises(ValueError, match="not a valid option"):
            serialize_for_hubspot(
                {"seniority": "invalid_value"}, ["fit"], "default"
            )


class TestObjectTypeGroups:
    def test_contact_group(self):
        assert OBJECT_TYPE_GROUPS["contact"] == "contactinformation"

    def test_company_group(self):
        assert OBJECT_TYPE_GROUPS["company"] == "companyinformation"

    def test_deal_group(self):
        assert OBJECT_TYPE_GROUPS["deal"] == "dealinformation"
