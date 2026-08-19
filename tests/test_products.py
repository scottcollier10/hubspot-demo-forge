import json
from unittest.mock import MagicMock, patch
from forge.products import seed_products, seed_line_items


class TestSeedProducts:
    def test_creates_products(self):
        client = MagicMock()
        client.post.return_value = ({"id": "prod_1"}, 201)
        client.throttle = MagicMock()

        products = [
            {"name": "Platform License", "price": "25000", "description": "Annual platform license"},
        ]
        product_id_map = seed_products(client, products)
        assert product_id_map["Platform License"] == "prod_1"

    def test_returns_name_to_id_map(self):
        client = MagicMock()
        client.post.side_effect = [
            ({"id": "p1"}, 201),
            ({"id": "p2"}, 201),
        ]
        client.throttle = MagicMock()

        products = [
            {"name": "License", "price": "10000"},
            {"name": "Support", "price": "5000"},
        ]
        id_map = seed_products(client, products)
        assert len(id_map) == 2

    def test_injects_forge_source(self):
        client = MagicMock()
        client.post.return_value = ({"id": "100"}, 201)
        client.throttle = MagicMock()

        products = [{"name": "Widget", "price": "5000"}]
        seed_products(client, products, forge_source="forge-test-prod")

        create_call = client.post.call_args_list[0]
        props = create_call[0][1]["properties"]
        assert props["forge_source"] == "forge-test-prod"


class TestSeedLineItems:
    def test_creates_line_items_on_deals(self):
        client = MagicMock()
        client.post.return_value = ({"id": "li_1"}, 201)
        client.put.return_value = ({}, 200)
        client.throttle = MagicMock()

        deal_records = [{"id": "deal_1", "dealstage": "s", "company_name": "Acme"}]
        product_id_map = {"Platform License": "prod_1"}
        products = [{"name": "Platform License", "price": "25000"}]

        created = seed_line_items(client, deal_records, product_id_map, products, line_items_per_deal=[1, 1])
        assert created >= 1
        call_body = client.post.call_args[0][1]
        assert "hs_product_id" in call_body["properties"]

    def test_does_not_send_forge_source(self):
        """Line items don't support custom properties — no forge_source."""
        client = MagicMock()
        client.post.return_value = ({"id": "li_1"}, 201)
        client.put.return_value = ({}, 200)
        client.throttle = MagicMock()

        deal_records = [{"id": "deal_1", "dealstage": "s", "company_name": "Acme"}]
        product_id_map = {"Widget": "prod_1"}
        products = [{"name": "Widget", "price": "5000"}]

        seed_line_items(client, deal_records, product_id_map, products, line_items_per_deal=[1, 1])
        call_body = client.post.call_args[0][1]
        assert "forge_source" not in call_body["properties"]
