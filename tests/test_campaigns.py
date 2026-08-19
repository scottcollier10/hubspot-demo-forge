from unittest.mock import MagicMock
from forge.campaigns import seed_campaigns, _shift_dates, _load_campaigns_csv, generate_email_csv


class TestShiftDates:
    def test_preserves_relative_spacing(self):
        rows = [
            {"Campaign name": "A", "Campaign start date": "2026-01-01", "Campaign end date": "2026-02-01"},
            {"Campaign name": "B", "Campaign start date": "2026-03-01", "Campaign end date": "2026-04-01"},
        ]
        shifted = _shift_dates(rows)
        from datetime import datetime
        a_start = datetime.strptime(shifted[0]["Campaign start date"], "%Y-%m-%d")
        b_start = datetime.strptime(shifted[1]["Campaign start date"], "%Y-%m-%d")
        # 59 days between original starts, should be preserved
        assert (b_start - a_start).days == 59

    def test_midpoint_near_today(self):
        rows = [
            {"Campaign name": "A", "Campaign start date": "2020-01-01", "Campaign end date": "2020-12-31"},
        ]
        shifted = _shift_dates(rows)
        from datetime import datetime
        start = datetime.strptime(shifted[0]["Campaign start date"], "%Y-%m-%d")
        end = datetime.strptime(shifted[0]["Campaign end date"], "%Y-%m-%d")
        midpoint = start + (end - start) / 2
        today = datetime.now()
        assert abs((midpoint - today).days) <= 1


class TestLoadCampaignsCsv:
    def test_loads_12_campaigns(self):
        rows = _load_campaigns_csv()
        assert len(rows) == 12
        assert rows[0]["Campaign name"] == "Q2 Demand Gen Blitz"


class TestSeedCampaigns:
    def test_creates_campaigns(self):
        client = MagicMock()
        # get returns no existing campaigns
        client.get.return_value = {"results": []}
        client.post.return_value = ({"id": "camp_1"}, 201)
        client.throttle = MagicMock()

        id_map = seed_campaigns(client)
        assert len(id_map) == 12
        assert client.post.call_count == 12

    def test_skips_duplicates(self):
        client = MagicMock()
        # get returns one existing campaign
        client.get.return_value = {
            "results": [{"properties": {"hs_name": "Q2 Demand Gen Blitz"}}]
        }
        client.post.return_value = ({"id": "camp_2"}, 201)
        client.throttle = MagicMock()

        id_map = seed_campaigns(client)
        assert len(id_map) == 11  # 12 - 1 duplicate
        assert "Q2 Demand Gen Blitz" not in id_map

    def test_dry_run_creates_nothing(self):
        client = MagicMock()
        id_map = seed_campaigns(client, dry_run=True)
        assert id_map == {}
        client.post.assert_not_called()


class TestGenerateEmailCsv:
    def test_writes_csv(self, tmp_path):
        output = tmp_path / "emails.csv"
        generate_email_csv(str(output))
        assert output.exists()
        content = output.read_text()
        assert "Email Name" in content
        assert "Spring Webinar" in content
        lines = content.strip().split("\n")
        assert len(lines) == 9  # header + 8 emails
