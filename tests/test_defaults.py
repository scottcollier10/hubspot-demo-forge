from forge.defaults import apply_defaults


class TestApplyDefaults:
    def test_v0_profile_unchanged(self):
        profile = {
            "company": {"name": "T", "industry": "S", "size": "s", "icp": "x"},
            "counts": {"companies": 5, "contacts_per_company": [2, 4], "deals": 10},
            "pipeline": {"id": "default", "stages": {}, "close_date_offsets": {}, "temp_stage": "a"},
            "properties": {"canon": True},
        }
        result = apply_defaults(profile)
        assert result["counts"]["companies"] == 5
        assert result["counts"]["deals"] == 10
        assert result["properties"]["canon"] is True

    def test_missing_optional_counts_default_to_zero(self):
        profile = {
            "company": {"name": "T", "industry": "S", "size": "s", "icp": "x"},
            "counts": {"companies": 5, "contacts_per_company": [2, 4], "deals": 10},
            "pipeline": {"id": "default", "stages": {}, "close_date_offsets": {}, "temp_stage": "a"},
        }
        result = apply_defaults(profile)
        assert result["counts"].get("tickets", 0) == 0
        assert result["counts"].get("products", 0) == 0
        assert result["counts"].get("activities_per_contact", 0) == 0

    def test_ticket_defaults_applied(self):
        profile = {
            "company": {"name": "T", "industry": "S", "size": "s", "icp": "x"},
            "counts": {"companies": 5, "contacts_per_company": [2, 4], "deals": 10, "tickets": 20},
            "pipeline": {"id": "default", "stages": {}, "close_date_offsets": {}, "temp_stage": "a"},
        }
        result = apply_defaults(profile)
        assert "tickets" in result
        assert result["tickets"]["statuses"]["open"] == 0.4

    def test_product_defaults_applied(self):
        profile = {
            "company": {"name": "T", "industry": "S", "size": "s", "icp": "x"},
            "counts": {"companies": 5, "contacts_per_company": [2, 4], "deals": 10, "products": 8},
            "pipeline": {"id": "default", "stages": {}, "close_date_offsets": {}, "temp_stage": "a"},
        }
        result = apply_defaults(profile)
        assert result["products"]["price_range"] == [5000, 50000]
        assert result["products"]["line_items_per_deal"] == [1, 3]

    def test_activity_defaults_applied(self):
        profile = {
            "company": {"name": "T", "industry": "S", "size": "s", "icp": "x"},
            "counts": {"companies": 5, "contacts_per_company": [2, 4], "deals": 10, "activities_per_contact": [2, 6]},
            "pipeline": {"id": "default", "stages": {}, "close_date_offsets": {}, "temp_stage": "a"},
        }
        result = apply_defaults(profile)
        assert result["activities"]["recency_days"] == 90
        assert "call" in result["activities"]["types"]

    def test_explicit_config_not_overwritten(self):
        profile = {
            "company": {"name": "T", "industry": "S", "size": "s", "icp": "x"},
            "counts": {"companies": 5, "contacts_per_company": [2, 4], "deals": 10, "tickets": 15},
            "pipeline": {"id": "default", "stages": {}, "close_date_offsets": {}, "temp_stage": "a"},
            "tickets": {"pipeline": "custom", "statuses": {"open": 0.6, "closed": 0.4}},
        }
        result = apply_defaults(profile)
        assert result["tickets"]["pipeline"] == "custom"
        assert result["tickets"]["statuses"]["open"] == 0.6

    def test_properties_defaults_to_empty(self):
        profile = {
            "company": {"name": "T", "industry": "S", "size": "s", "icp": "x"},
            "counts": {"companies": 5, "contacts_per_company": [2, 4], "deals": 10},
            "pipeline": {"id": "default", "stages": {}, "close_date_offsets": {}, "temp_stage": "a"},
        }
        result = apply_defaults(profile)
        assert result.get("properties", {}) == {}
