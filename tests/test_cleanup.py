from unittest.mock import MagicMock, patch, call
from forge.cleanup import discover_forge_records, cleanup_forge_records, TRACKED_TYPES, DELETION_ORDER


class TestDiscoverForgeRecords:
    def _make_client(self, search_results=None, assoc_results=None, error_types=None):
        """Build a mock client.

        search_results: {obj_type: [{"id": "..."}]} for successful searches
        assoc_results: response body for association batch reads
        error_types: {obj_type: status_code} to simulate API errors
        """
        client = MagicMock()
        error_types = error_types or {}

        def fake_post(path, body):
            # Association batch reads
            if "/associations/" in path:
                return (assoc_results or {"results": []}, 200)
            # Search calls
            for obj_type in TRACKED_TYPES:
                if f"/{obj_type}/search" in path:
                    if obj_type in error_types:
                        return ({"message": "error"}, error_types[obj_type])
                    hits = (search_results or {}).get(obj_type, [])
                    return ({"results": hits}, 200)
            return ({"results": []}, 200)

        client.post = MagicMock(side_effect=fake_post)
        client.throttle = MagicMock()
        return client

    def test_finds_tagged_contacts(self):
        client = self._make_client(
            search_results={"contacts": [{"id": "1"}, {"id": "2"}]},
        )
        result = discover_forge_records(client)
        assert result["contacts"] == ["1", "2"]

    def test_finds_all_tracked_types(self):
        search_results = {t: [{"id": f"{t}-1"}] for t in TRACKED_TYPES}
        client = self._make_client(search_results=search_results)
        result = discover_forge_records(client)
        for t in TRACKED_TYPES:
            assert result[t] == [f"{t}-1"]

    def test_session_filter(self):
        client = self._make_client(
            search_results={"contacts": [{"id": "1"}]},
        )
        discover_forge_records(client, session_id="forge-20260601-abc123")

        # Find the contacts search call
        for c in client.post.call_args_list:
            if "/contacts/search" in c[0][0]:
                body = c[0][1]
                filt = body["filterGroups"][0]["filters"][0]
                assert filt["operator"] == "EQ"
                assert filt["value"] == "forge-20260601-abc123"
                break

    def test_finds_associated_line_items(self):
        client = self._make_client(
            search_results={"deals": [{"id": "d1"}]},
            assoc_results={
                "results": [
                    {"from": {"id": "d1"}, "to": [{"toObjectId": "li1"}, {"toObjectId": "li2"}]}
                ]
            },
        )
        result = discover_forge_records(client)
        assert set(result["line_items"]) == {"li1", "li2"}

    def test_finds_associated_activities(self):
        client = self._make_client(
            search_results={"contacts": [{"id": "c1"}]},
            assoc_results={
                "results": [
                    {"from": {"id": "c1"}, "to": [{"toObjectId": "a1"}]}
                ]
            },
        )
        result = discover_forge_records(client)
        for act_type in ["calls", "emails", "meetings", "notes"]:
            assert "a1" in result[act_type]

    def test_empty_portal(self):
        client = self._make_client(search_results={})
        result = discover_forge_records(client)
        for obj_type in DELETION_ORDER:
            assert result.get(obj_type, []) == []

    def test_deletion_order_dependents_first(self):
        li_idx = DELETION_ORDER.index("line_items")
        deals_idx = DELETION_ORDER.index("deals")
        assert li_idx < deals_idx

        for act_type in ["calls", "emails", "meetings", "notes"]:
            act_idx = DELETION_ORDER.index(act_type)
            contacts_idx = DELETION_ORDER.index("contacts")
            assert act_idx < contacts_idx

    def test_handles_400_property_not_found(self):
        """forge_source property doesn't exist yet — skip gracefully."""
        client = self._make_client(
            error_types={"contacts": 400, "companies": 400, "deals": 400},
        )
        result = discover_forge_records(client)
        assert result["contacts"] == []
        assert result["companies"] == []
        assert result["deals"] == []

    def test_handles_403_no_access(self):
        """Private app missing scopes for some types — skip gracefully."""
        client = self._make_client(
            search_results={"contacts": [{"id": "1"}]},
            error_types={"tickets": 403, "products": 403},
        )
        result = discover_forge_records(client)
        assert result["contacts"] == ["1"]
        assert result["tickets"] == []
        assert result["products"] == []

    def test_mixed_errors_and_results(self):
        """Some types work, some 400, some 403 — only return working ones."""
        client = self._make_client(
            search_results={"deals": [{"id": "d1"}]},
            error_types={"contacts": 400, "companies": 400, "tickets": 403, "products": 403},
        )
        result = discover_forge_records(client)
        assert result["deals"] == ["d1"]
        assert result["contacts"] == []
        assert result["tickets"] == []


class TestCleanupForgeRecords:
    def test_deletes_in_order(self):
        client = MagicMock()
        client.batch_archive = MagicMock(return_value=True)
        client.throttle = MagicMock()

        records = {
            "contacts": ["c1", "c2"],
            "deals": ["d1"],
            "line_items": ["li1"],
            "calls": ["a1"],
        }
        deleted = cleanup_forge_records(client, records)

        assert deleted["contacts"] == 2
        assert deleted["deals"] == 1
        assert deleted["line_items"] == 1
        assert deleted["calls"] == 1

        # Verify line_items deleted before deals, calls before contacts
        archive_calls = client.batch_archive.call_args_list
        types_in_order = [c[0][0] for c in archive_calls]
        assert types_in_order.index("line_items") < types_in_order.index("deals")
        assert types_in_order.index("calls") < types_in_order.index("contacts")

    def test_dry_run_skips_api(self):
        client = MagicMock()
        records = {"contacts": ["c1", "c2"]}
        deleted = cleanup_forge_records(client, records, dry_run=True)

        assert deleted["contacts"] == 2
        client.batch_archive.assert_not_called()

    def test_skips_empty_types(self):
        client = MagicMock()
        client.batch_archive = MagicMock(return_value=True)

        records = {"contacts": ["c1"], "deals": [], "companies": []}
        deleted = cleanup_forge_records(client, records)

        assert deleted.get("contacts") == 1
        assert "deals" not in deleted
        assert "companies" not in deleted

    def test_reports_failure(self):
        client = MagicMock()
        client.batch_archive = MagicMock(return_value=False)

        records = {"contacts": ["c1"]}
        deleted = cleanup_forge_records(client, records)
        assert deleted["contacts"] == 0
