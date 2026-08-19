import json
from unittest.mock import MagicMock
from forge.properties import (
    get_properties_for_profile,
    get_forge_tracking_property,
    create_all_properties,
    FORGE_TRACKED_TYPES,
)


class TestGetPropertiesForProfile:
    def test_fit_only_returns_contacts_and_companies(self):
        profile = {"properties": {"preset": "default", "sets": ["fit"]}}
        result = get_properties_for_profile(profile)
        assert "contacts" in result
        assert "companies" in result
        assert "deals" not in result

    def test_engagement_only_returns_contacts_and_deals(self):
        profile = {"properties": {"preset": "default", "sets": ["engagement"]}}
        result = get_properties_for_profile(profile)
        assert "contacts" in result
        assert "deals" in result

    def test_default_preset_uses_forge_names(self):
        profile = {"properties": {"preset": "default", "sets": ["fit"]}}
        result = get_properties_for_profile(profile)
        names = {p["name"] for p in result["contacts"]}
        assert all(n.startswith("forge_") for n in names)

    def test_canon_preset_uses_canon_names(self):
        profile = {"properties": {"preset": "canon", "sets": ["fit"]}}
        result = get_properties_for_profile(profile)
        names = {p["name"] for p in result["contacts"]}
        assert all(n.startswith("canon_") for n in names)

    def test_no_sets_returns_empty(self):
        profile = {"properties": {"preset": "default", "sets": []}}
        result = get_properties_for_profile(profile)
        assert result == {}


class TestCreateAllProperties:
    def test_skips_existing(self):
        client = MagicMock()
        client.get.return_value = {
            "results": [{"name": "canon_title"}]
        }
        client.post.return_value = ({}, 201)
        client.throttle = MagicMock()

        props = [
            {"name": "canon_title", "label": "Title", "type": "string", "fieldType": "text"},
            {"name": "canon_seniority", "label": "Seniority", "type": "string", "fieldType": "text"},
        ]
        created, skipped, failed = create_all_properties(client, "contacts", props)
        assert skipped == 1  # canon_title
        assert created == 1  # canon_seniority

    def test_handles_409_conflict(self):
        client = MagicMock()
        client.get.return_value = {"results": []}
        client.post.return_value = ({"message": "exists"}, 409)
        client.throttle = MagicMock()

        props = [{"name": "canon_x", "label": "X", "type": "string", "fieldType": "text"}]
        created, skipped, failed = create_all_properties(client, "contacts", props)
        assert skipped == 1
        assert created == 0


class TestForgeTrackingProperty:
    def test_returns_property_dict(self):
        prop = get_forge_tracking_property("contacts")
        assert prop["name"] == "forge_source"
        assert prop["type"] == "string"
        assert prop["fieldType"] == "text"
        assert prop["groupName"] == "contactinformation"

    def test_company_group(self):
        prop = get_forge_tracking_property("companies")
        assert prop["groupName"] == "companyinformation"

    def test_deal_group(self):
        prop = get_forge_tracking_property("deals")
        assert prop["groupName"] == "dealinformation"

    def test_all_tracked_types_supported(self):
        for obj_type in FORGE_TRACKED_TYPES:
            prop = get_forge_tracking_property(obj_type)
            assert prop["name"] == "forge_source"
            assert "groupName" in prop
