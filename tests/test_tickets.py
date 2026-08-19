from unittest.mock import MagicMock
from forge.tickets import seed_tickets, assign_ticket_statuses


class TestAssignTicketStatuses:
    def test_distributes_by_weight(self):
        tickets = [{"subject": f"Ticket {i}"} for i in range(10)]
        statuses_cfg = {"open": 0.4, "waiting": 0.3, "closed": 0.3}
        buckets = assign_ticket_statuses(tickets, statuses_cfg)
        assert sum(len(v) for v in buckets.values()) == 10

    def test_all_tickets_assigned(self):
        tickets = [{"subject": f"T{i}"} for i in range(7)]
        statuses_cfg = {"open": 0.5, "closed": 0.5}
        buckets = assign_ticket_statuses(tickets, statuses_cfg)
        total = sum(len(v) for v in buckets.values())
        assert total == 7


class TestSeedTickets:
    def test_creates_tickets(self):
        client = MagicMock()
        client.post.return_value = ({"id": "t_1"}, 201)
        client.throttle = MagicMock()

        tickets = [{"subject": "Login issue", "content": "Can't login"}]
        ticket_cfg = {"pipeline": "support", "statuses": {"open": 1.0}}
        records = seed_tickets(client, tickets, ticket_cfg)
        assert len(records) == 1
        assert records[0]["id"] == "t_1"

        call_body = client.post.call_args[0][1]
        props = call_body["properties"]
        assert props["hs_pipeline"] == "support"

    def test_injects_forge_source(self):
        client = MagicMock()
        client.post.return_value = ({"id": "100"}, 201)
        client.throttle = MagicMock()

        tickets = [{"subject": "Help", "content": "Need help"}]
        ticket_cfg = {"pipeline": "0", "statuses": {"open": 1.0}}
        seed_tickets(client, tickets, ticket_cfg, forge_source="forge-test-789")

        create_call = client.post.call_args_list[0]
        props = create_call[0][1]["properties"]
        assert props["forge_source"] == "forge-test-789"
