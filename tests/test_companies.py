from unittest.mock import MagicMock, call
from forge.companies import seed_companies


class TestSeedCompanies:
    def test_creates_new_company(self):
        client = MagicMock()
        # Search returns no existing
        client.post.side_effect = [
            ({"results": []}, 200),           # search
            ({"id": "100"}, 201),              # create
        ]
        client.throttle = MagicMock()

        companies = [{"name": "Acme", "domain": "acme.example.com", "industry": "SaaS"}]
        id_map = seed_companies(client, companies)
        assert id_map["acme.example.com"] == "100"

    def test_updates_existing_forge_owned_company(self):
        client = MagicMock()
        # Search finds existing with forge_source
        client.post.return_value = (
            {"results": [{"id": "200", "properties": {"forge_source": "forge-old"}}]},
            200,
        )
        client.patch.return_value = {"id": "200"}
        client.throttle = MagicMock()

        companies = [{"name": "Acme", "domain": "acme.example.com", "industry": "SaaS"}]
        id_map = seed_companies(client, companies)
        assert id_map["acme.example.com"] == "200"
        client.patch.assert_called_once()

    def test_skips_non_forge_owned_company(self):
        """Existing company without forge_source must NOT be modified or claimed."""
        client = MagicMock()
        # Search finds existing without forge_source
        client.post.return_value = (
            {"results": [{"id": "300", "properties": {"forge_source": None}}]},
            200,
        )
        client.throttle = MagicMock()

        companies = [{"name": "Acme", "domain": "acme.example.com", "industry": "SaaS"}]
        id_map = seed_companies(client, companies)
        # Should not be in the map (skipped)
        assert "acme.example.com" not in id_map
        # Should NOT have called patch
        client.patch.assert_not_called()

    def test_skips_company_with_empty_forge_source(self):
        """Empty string forge_source is treated as not forge-owned."""
        client = MagicMock()
        client.post.return_value = (
            {"results": [{"id": "300", "properties": {"forge_source": ""}}]},
            200,
        )
        client.throttle = MagicMock()

        companies = [{"name": "Acme", "domain": "acme.example.com"}]
        id_map = seed_companies(client, companies)
        assert "acme.example.com" not in id_map
        client.patch.assert_not_called()

    def test_returns_id_map_by_domain(self):
        client = MagicMock()
        client.post.side_effect = [
            ({"results": []}, 200), ({"id": "1"}, 201),
            ({"results": []}, 200), ({"id": "2"}, 201),
        ]
        client.throttle = MagicMock()

        companies = [
            {"name": "A", "domain": "a.example.com"},
            {"name": "B", "domain": "b.example.com"},
        ]
        id_map = seed_companies(client, companies)
        assert len(id_map) == 2
        assert "a.example.com" in id_map
        assert "b.example.com" in id_map

    def test_injects_forge_source(self):
        client = MagicMock()
        client.post.side_effect = [
            ({"results": []}, 200),
            ({"id": "100"}, 201),
        ]
        client.throttle = MagicMock()

        companies = [{"name": "Acme", "domain": "acme.example.com"}]
        seed_companies(client, companies, forge_source="forge-20260601-abc123")

        create_call = client.post.call_args_list[1]
        props = create_call[0][1]["properties"]
        assert props["forge_source"] == "forge-20260601-abc123"
