import json
from unittest.mock import patch, MagicMock
from forge.client import HubSpotClient


def _mock_response(data, status=200):
    """Build a mock urllib response."""
    resp = MagicMock()
    resp.read.return_value = json.dumps(data).encode()
    resp.status = status
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


class TestHubSpotClient:
    def test_init_requires_token(self):
        client = HubSpotClient("pat-test-123")
        assert client.token == "pat-test-123"

    def test_init_from_env(self):
        with patch.dict("os.environ", {"HUBSPOT_TOKEN": "pat-env-456"}):
            client = HubSpotClient.from_env()
            assert client.token == "pat-env-456"

    def test_init_from_env_missing(self):
        with patch.dict("os.environ", {}, clear=True):
            try:
                HubSpotClient.from_env()
                assert False, "Should have raised"
            except SystemExit:
                pass

    @patch("urllib.request.urlopen")
    def test_post_success(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response({"id": "123"}, 200)
        client = HubSpotClient("pat-test")
        data, status = client.post("/crm/v3/objects/contacts", {"properties": {}})
        assert status == 200
        assert data["id"] == "123"

    @patch("urllib.request.urlopen")
    def test_post_sends_auth_header(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response({}, 200)
        client = HubSpotClient("pat-test-token")
        client.post("/crm/v3/objects/contacts", {})
        req = mock_urlopen.call_args[0][0]
        assert req.get_header("Authorization") == "Bearer pat-test-token"
        assert req.get_header("Content-type") == "application/json"

    @patch("urllib.request.urlopen")
    def test_get_success(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response({"results": []}, 200)
        client = HubSpotClient("pat-test")
        data = client.get("/crm/v3/properties/contacts")
        assert data == {"results": []}

    @patch("urllib.request.urlopen")
    def test_patch_success(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response({"id": "1"}, 200)
        client = HubSpotClient("pat-test")
        result = client.patch("/crm/v3/objects/contacts/1", {"properties": {}})
        assert result["id"] == "1"

    @patch("urllib.request.urlopen")
    def test_put_success(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response({}, 200)
        client = HubSpotClient("pat-test")
        data, status = client.put("/crm/v4/objects/contacts/1/associations/default/companies/2")
        assert status == 200

    @patch("urllib.request.urlopen")
    def test_post_http_error(self, mock_urlopen):
        import urllib.error
        error_body = json.dumps({"message": "conflict"}).encode()
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "url", 409, "Conflict", {}, MagicMock(read=lambda: error_body)
        )
        client = HubSpotClient("pat-test")
        data, status = client.post("/crm/v3/objects/contacts", {})
        assert status == 409

    @patch("urllib.request.urlopen")
    def test_fetch_all_paginates(self, mock_urlopen):
        page1 = _mock_response({
            "results": [{"id": "1"}],
            "paging": {"next": {"after": "cursor1"}}
        })
        page2 = _mock_response({
            "results": [{"id": "2"}],
        })
        mock_urlopen.side_effect = [page1, page2]
        client = HubSpotClient("pat-test")
        results = client.fetch_all("/crm/v3/objects/contacts/search", {
            "properties": ["email"],
        })
        assert len(results) == 2
        assert results[0]["id"] == "1"
        assert results[1]["id"] == "2"

    @patch("urllib.request.urlopen")
    def test_batch_archive_success(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response({}, 204)
        client = HubSpotClient("pat-test")
        ok = client.batch_archive("contacts", ["1", "2", "3"])
        assert ok is True

    @patch("urllib.request.urlopen")
    def test_batch_archive_chunks(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response({}, 204)
        client = HubSpotClient("pat-test")
        ids = [str(i) for i in range(150)]
        ok = client.batch_archive("contacts", ids)
        assert ok is True
        # Should have made 2 calls (100 + 50)
        assert mock_urlopen.call_count == 2

    @patch("urllib.request.urlopen")
    def test_batch_archive_empty(self, mock_urlopen):
        client = HubSpotClient("pat-test")
        ok = client.batch_archive("contacts", [])
        assert ok is True
        mock_urlopen.assert_not_called()

    @patch("urllib.request.urlopen")
    def test_batch_archive_failure(self, mock_urlopen):
        import urllib.error
        error_body = json.dumps({"message": "forbidden"}).encode()
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "url", 403, "Forbidden", {}, MagicMock(read=lambda: error_body)
        )
        client = HubSpotClient("pat-test")
        ok = client.batch_archive("contacts", ["1"])
        assert ok is False
