from forge.engage import (
    derive_seniority,
    derive_department,
    assign_engagement_levels,
)


class TestDeriveSeniority:
    def test_c_level(self):
        assert derive_seniority("Chief Revenue Officer") == "c_level"

    def test_vp(self):
        assert derive_seniority("VP of Marketing") == "vp"

    def test_vp_abbreviated(self):
        assert derive_seniority("VP Mktg") == "vp"

    def test_director(self):
        assert derive_seniority("Director of Engineering") == "director"

    def test_sr_director(self):
        assert derive_seniority("Sr. Dir. Eng") == "director"

    def test_manager(self):
        assert derive_seniority("Marketing Manager") == "manager"

    def test_individual_contributor(self):
        assert derive_seniority("Software Engineer") == "individual_contributor"

    def test_empty(self):
        assert derive_seniority("") == "unknown"


class TestDeriveDepartment:
    def test_marketing(self):
        assert derive_department("VP of Marketing") == "marketing"

    def test_sales(self):
        assert derive_department("Sales Manager") == "sales"

    def test_engineering(self):
        assert derive_department("Director of Engineering") == "engineering"

    def test_finance(self):
        assert derive_department("CFO") == "finance"

    def test_hr(self):
        assert derive_department("HR Director") == "hr"

    def test_operations(self):
        assert derive_department("VP Operations") == "operations"

    def test_product(self):
        assert derive_department("Product Manager") == "product"

    def test_customer_success(self):
        assert derive_department("Customer Success Manager") == "customer_success"

    def test_fallback(self):
        assert derive_department("Analyst") == "other"


class TestAssignEngagementLevels:
    def test_distribution_ratios(self):
        contacts = [{"id": str(i)} for i in range(100)]
        levels = assign_engagement_levels(contacts)
        assert len(levels[1]) == 20
        assert len(levels[2]) == 30
        assert len(levels[3]) == 50

    def test_small_list(self):
        contacts = [{"id": str(i)} for i in range(5)]
        levels = assign_engagement_levels(contacts)
        total = len(levels[1]) + len(levels[2]) + len(levels[3])
        assert total == 5

    def test_all_contacts_assigned(self):
        contacts = [{"id": str(i)} for i in range(37)]
        levels = assign_engagement_levels(contacts)
        all_ids = set()
        for lvl_contacts in levels.values():
            for c in lvl_contacts:
                all_ids.add(c["id"])
        assert len(all_ids) == 37


from forge.cli import build_parser


class TestCLIEngage:
    def test_engage_subcommand_parses(self):
        parser = build_parser()
        args = parser.parse_args(["engage", "profiles/full_portal.json"])
        assert args.command == "engage"
        assert args.profile == "profiles/full_portal.json"

    def test_engage_dry_run_flag(self):
        parser = build_parser()
        args = parser.parse_args(["engage", "profiles/full_portal.json", "--dry-run"])
        assert args.dry_run is True

    def test_engage_limit_flag(self):
        parser = build_parser()
        args = parser.parse_args(["engage", "profiles/full_portal.json", "--limit", "25"])
        assert args.limit == 25


from unittest.mock import MagicMock
from forge.engage import cmd_engage_contacts


class TestCmdEngageContacts:
    def _make_client(self, contacts):
        """Build a mock client that returns contacts from fetch_all."""
        client = MagicMock()
        client.fetch_all.return_value = contacts
        client.batch_update.return_value = True
        client.throttle = MagicMock()
        return client

    def test_fetches_and_updates(self):
        contacts = [
            {"id": str(i), "properties": {"jobtitle": "Manager", "email": f"u{i}@co.com"}}
            for i in range(10)
        ]
        client = self._make_client(contacts)
        result = cmd_engage_contacts(client, preset="default", enabled_sets=["fit", "engagement"])

        assert result["total"] == 10
        assert result["hot"] + result["warm"] + result["cold"] == 10
        client.batch_update.assert_called()

    def test_dry_run_skips_update(self):
        contacts = [
            {"id": "1", "properties": {"jobtitle": "CEO", "email": "a@b.com"}},
        ]
        client = self._make_client(contacts)
        result = cmd_engage_contacts(client, preset="default", dry_run=True)

        assert result["total"] == 1
        client.batch_update.assert_not_called()

    def test_limit_caps_contacts(self):
        contacts = [
            {"id": str(i), "properties": {"jobtitle": "Eng", "email": f"u{i}@co.com"}}
            for i in range(50)
        ]
        client = self._make_client(contacts)
        result = cmd_engage_contacts(client, preset="default", limit=10)

        assert result["total"] == 10

    def test_empty_portal(self):
        client = self._make_client([])
        result = cmd_engage_contacts(client, preset="default")
        assert result["total"] == 0
        client.batch_update.assert_not_called()

    def test_defaults_to_forge_owned_filter(self):
        """By default, engage only fetches contacts with forge_source."""
        client = self._make_client([])
        cmd_engage_contacts(client, preset="default")

        search_body = client.fetch_all.call_args[0][1]
        filters = search_body["filterGroups"][0]["filters"]
        assert any(
            f["propertyName"] == "forge_source" and f["operator"] == "HAS_PROPERTY"
            for f in filters
        )

    def test_all_contacts_skips_forge_filter(self):
        """With all_contacts=True, no forge_source filter is applied."""
        client = self._make_client([])
        cmd_engage_contacts(client, preset="default", all_contacts=True)

        search_body = client.fetch_all.call_args[0][1]
        assert search_body["filterGroups"] == []
