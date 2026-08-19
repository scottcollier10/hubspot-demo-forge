import json
import os
from unittest.mock import patch, MagicMock
from forge.generate import generate_companies, generate_contacts, generate_deals


def _mock_claude_response(content_text):
    """Mock a Claude API response."""
    resp = MagicMock()
    resp.read.return_value = json.dumps({
        "content": [{"type": "text", "text": content_text}]
    }).encode()
    resp.status = 200
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


# All tests set ANTHROPIC_API_KEY so _call_claude doesn't sys.exit(1)
# before reaching the mocked urlopen.
_ENV_PATCH = {"ANTHROPIC_API_KEY": "sk-ant-test-key"}


class TestGenerateCompanies:
    @patch.dict(os.environ, _ENV_PATCH)
    @patch("urllib.request.urlopen")
    def test_returns_list_of_companies(self, mock_urlopen):
        companies = [
            {"name": "Acme Corp", "domain": "acmecorp.com", "industry": "COMPUTER_SOFTWARE",
             "numberofemployees": "250", "city": "Austin", "state": "Texas"}
        ]
        mock_urlopen.return_value = _mock_claude_response(json.dumps(companies))

        profile = {
            "company": {"name": "Test", "industry": "B2B SaaS", "size": "mid-market", "icp": "devs"},
            "counts": {"companies": 1, "contacts_per_company": [2, 4], "deals": 5},
        }
        result = generate_companies(profile)
        assert len(result) == 1
        assert result[0]["name"] == "Acme Corp"
        assert "domain" in result[0]

    @patch.dict(os.environ, _ENV_PATCH)
    @patch("urllib.request.urlopen")
    def test_requests_correct_count(self, mock_urlopen):
        companies = [{"name": f"Co{i}", "domain": f"co{i}.com",
                       "industry": "SaaS", "numberofemployees": "50"}
                      for i in range(5)]
        mock_urlopen.return_value = _mock_claude_response(json.dumps(companies))

        profile = {
            "company": {"name": "T", "industry": "SaaS", "size": "startup", "icp": "x"},
            "counts": {"companies": 5, "contacts_per_company": [1, 2], "deals": 3},
        }
        result = generate_companies(profile)
        assert len(result) == 5


class TestGenerateContacts:
    @patch.dict(os.environ, _ENV_PATCH)
    @patch("urllib.request.urlopen")
    def test_returns_contacts_for_company(self, mock_urlopen):
        contacts = [
            {"firstname": "Sarah", "lastname": "Chen", "email": "sarah@acme.com",
             "jobtitle": "VP of Marketing", "phone": "555-0100"}
        ]
        mock_urlopen.return_value = _mock_claude_response(json.dumps(contacts))

        company = {"name": "Acme Corp", "domain": "acme.com", "industry": "SaaS"}
        result = generate_contacts(company, count=1, profile_icp="marketing leaders")
        assert len(result) == 1
        assert result[0]["email"].endswith("@acme.com")


class TestGenerateDeals:
    @patch.dict(os.environ, _ENV_PATCH)
    @patch("urllib.request.urlopen")
    def test_returns_deals(self, mock_urlopen):
        deals = [
            {"dealname": "Acme Corp — Platform License", "amount": "45000"}
        ]
        mock_urlopen.return_value = _mock_claude_response(json.dumps(deals))

        companies = [{"name": "Acme Corp", "domain": "acme.com"}]
        result = generate_deals(companies, count=1, profile_industry="B2B SaaS")
        assert len(result) == 1
        assert "dealname" in result[0]
        assert "amount" in result[0]
