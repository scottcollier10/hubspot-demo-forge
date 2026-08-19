from unittest.mock import MagicMock
from forge.deals import assign_stages, seed_deals, flip_stages


class TestAssignStages:
    def test_distributes_by_weight(self):
        deals = [{"dealname": f"Deal {i}"} for i in range(10)]
        pipeline_cfg = {
            "stages": {
                "warm": {"id": "qualifiedtobuy", "weight": 0.4},
                "at_risk": {"id": "contractsent", "weight": 0.4},
                "dormant": {"id": "presentationscheduled", "weight": 0.2},
            },
            "close_date_offsets": {"warm": 30, "at_risk": -5, "dormant": -45},
        }
        buckets = assign_stages(deals, pipeline_cfg)
        assert len(buckets["warm"]) == 4
        assert len(buckets["at_risk"]) == 4
        assert len(buckets["dormant"]) == 2

    def test_all_deals_assigned(self):
        deals = [{"dealname": f"D{i}"} for i in range(7)]
        pipeline_cfg = {
            "stages": {
                "warm": {"id": "a", "weight": 0.4},
                "at_risk": {"id": "b", "weight": 0.4},
                "dormant": {"id": "c", "weight": 0.2},
            },
            "close_date_offsets": {"warm": 30, "at_risk": -5, "dormant": -45},
        }
        buckets = assign_stages(deals, pipeline_cfg)
        total = sum(len(v) for v in buckets.values())
        assert total == 7


class TestSeedDeals:
    def test_creates_deals_with_stage_and_closedate(self):
        client = MagicMock()
        client.post.return_value = ({"id": "900"}, 201)
        client.throttle = MagicMock()

        deals = [{"dealname": "Acme — License", "amount": "50000"}]
        pipeline_cfg = {
            "id": "default",
            "stages": {
                "warm": {"id": "qualifiedtobuy", "weight": 1.0},
                "at_risk": {"id": "contractsent", "weight": 0.0},
                "dormant": {"id": "presentationscheduled", "weight": 0.0},
            },
            "close_date_offsets": {"warm": 30, "at_risk": -5, "dormant": -45},
        }
        deal_ids = seed_deals(client, deals, pipeline_cfg)
        assert len(deal_ids) == 1

        # Verify the POST body includes dealstage and closedate
        call_body = client.post.call_args[0][1]
        props = call_body["properties"]
        assert "dealstage" in props
        assert "closedate" in props
        assert props["pipeline"] == "default"

    def test_injects_forge_source(self):
        client = MagicMock()
        client.post.return_value = ({"id": "100"}, 201)
        client.throttle = MagicMock()

        deals = [{"dealname": "Deal A", "amount": "10000"}]
        pipeline = {
            "id": "default",
            "stages": {"warm": {"id": "qualifiedtobuy", "weight": 1.0}},
            "close_date_offsets": {"warm": 30},
        }
        records = seed_deals(client, deals, pipeline, forge_source="forge-test-456")

        create_call = client.post.call_args_list[0]
        props = create_call[0][1]["properties"]
        assert props["forge_source"] == "forge-test-456"


class TestFlipStages:
    def test_batch_updates_through_temp_stage(self):
        client = MagicMock()
        client.batch_update.return_value = True
        client.throttle = MagicMock()

        deal_stage_map = {
            "901": "qualifiedtobuy",
            "902": "contractsent",
        }
        pipeline_cfg = {
            "temp_stage": "appointmentscheduled",
            "stages": {
                "warm": {"id": "qualifiedtobuy", "weight": 0.5},
                "at_risk": {"id": "contractsent", "weight": 0.5},
                "dormant": {"id": "presentationscheduled", "weight": 0.0},
            },
        }
        flip_stages(client, deal_stage_map, pipeline_cfg)
        # Should have been called twice: once for temp, once for target
        assert client.batch_update.call_count == 2
