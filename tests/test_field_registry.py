"""Tests for the field registry — logical field definitions."""

from forge.field_registry import FIELDS, get_fields_by_set, get_fields_by_object_type


class TestFieldRegistryStructure:
    def test_every_field_has_required_keys(self):
        required = {"set", "label", "description", "type", "field_type", "object_type"}
        for name, field in FIELDS.items():
            missing = required - set(field.keys())
            assert not missing, f"Field '{name}' missing: {missing}"

    def test_sets_are_known(self):
        known_sets = {"fit", "engagement"}
        for name, field in FIELDS.items():
            assert field["set"] in known_sets, f"Field '{name}' has unknown set: {field['set']}"

    def test_object_types_are_known(self):
        known = {"contact", "company", "deal"}
        for name, field in FIELDS.items():
            assert field["object_type"] in known, f"Field '{name}' has unknown object_type"

    def test_types_are_known(self):
        known = {"string", "number", "enumeration", "date", "datetime", "bool"}
        for name, field in FIELDS.items():
            assert field["type"] in known, f"Field '{name}' has unknown type: {field['type']}"

    def test_enumeration_fields_have_options(self):
        for name, field in FIELDS.items():
            if field["type"] == "enumeration":
                assert "options" in field, f"Enum field '{name}' missing options"
                assert len(field["options"]) > 0, f"Enum field '{name}' has empty options"

    def test_non_enumeration_fields_have_no_options(self):
        for name, field in FIELDS.items():
            if field["type"] != "enumeration":
                assert "options" not in field, f"Non-enum field '{name}' has options"

    def test_options_have_label_and_value(self):
        for name, field in FIELDS.items():
            if field["type"] == "enumeration":
                for opt in field["options"]:
                    assert "label" in opt, f"Field '{name}' option missing label"
                    assert "value" in opt, f"Field '{name}' option missing value"

    def test_option_values_are_lowercase_snake(self):
        """Stable machine values should be lowercase with underscores."""
        import re
        pattern = re.compile(r"^[a-z0-9_]+$")
        for name, field in FIELDS.items():
            if field["type"] == "enumeration":
                for opt in field["options"]:
                    assert pattern.match(opt["value"]), \
                        f"Field '{name}' option value '{opt['value']}' is not lowercase_snake"

    def test_no_duplicate_option_values(self):
        for name, field in FIELDS.items():
            if field["type"] == "enumeration":
                values = [opt["value"] for opt in field["options"]]
                assert len(values) == len(set(values)), \
                    f"Field '{name}' has duplicate option values"


class TestFieldRegistryCompleteness:
    """Ensure the registry covers all fields from the pre-refactor code."""

    def test_fit_contact_fields_exist(self):
        fit_contact = {n for n, f in FIELDS.items()
                       if f["set"] == "fit" and f["object_type"] == "contact"}
        expected = {
            "title", "seniority", "department", "function",
            "data_confidence", "normalization_notes",
            "email_type", "persona", "lead_source",
        }
        assert fit_contact == expected

    def test_fit_company_fields_exist(self):
        fit_company = {n for n, f in FIELDS.items()
                       if f["set"] == "fit" and f["object_type"] == "company"}
        expected = {"company_domain", "company_industry", "company_employee_band"}
        assert fit_company == expected

    def test_engagement_contact_fields_exist(self):
        eng_contact = {n for n, f in FIELDS.items()
                       if f["set"] == "engagement" and f["object_type"] == "contact"}
        expected = {
            "engagement_score", "engagement_status",
            "email_opens", "email_clicks", "sends_since_engagement",
            "last_open_date", "last_click_date",
        }
        assert eng_contact == expected

    def test_engagement_deal_fields_exist(self):
        eng_deal = {n for n, f in FIELDS.items()
                    if f["set"] == "engagement" and f["object_type"] == "deal"}
        expected = {
            "deal_health_score", "deal_engagement_status", "deal_last_activity",
        }
        assert eng_deal == expected

    def test_total_field_count(self):
        assert len(FIELDS) == 22


class TestFieldRegistryHelpers:
    def test_get_fields_by_set_fit(self):
        fit = get_fields_by_set("fit")
        assert all(f["set"] == "fit" for f in fit.values())
        assert len(fit) == 12  # 9 contact + 3 company

    def test_get_fields_by_set_engagement(self):
        eng = get_fields_by_set("engagement")
        assert all(f["set"] == "engagement" for f in eng.values())
        assert len(eng) == 10  # 7 contact + 3 deal

    def test_get_fields_by_object_type_contact(self):
        contacts = get_fields_by_object_type("contact")
        assert all(f["object_type"] == "contact" for f in contacts.values())

    def test_get_fields_by_set_unknown_returns_empty(self):
        assert get_fields_by_set("nonexistent") == {}
