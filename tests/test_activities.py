from unittest.mock import MagicMock
from forge.activities import seed_activities


class TestSeedActivities:
    def test_creates_activities(self):
        client = MagicMock()
        client.post.return_value = ({"id": "act_1"}, 201)
        client.put.return_value = ({}, 200)
        client.throttle = MagicMock()

        activities = [
            {"type": "call", "subject": "Discovery call", "body": "Discussed needs",
             "timestamp": "2026-05-10T10:00:00Z", "contact_email": "sarah@acme.com"},
        ]
        contact_email_to_id = {"sarah@acme.com": "c_500"}
        created = seed_activities(client, activities, contact_email_to_id)
        assert created == 1

    def test_skips_unknown_contact(self):
        client = MagicMock()
        client.post.return_value = ({"id": "act_2"}, 201)
        client.put.return_value = ({}, 200)
        client.throttle = MagicMock()

        activities = [
            {"type": "note", "subject": "Note", "body": "...",
             "timestamp": "2026-05-10T10:00:00Z", "contact_email": "unknown@foo.com"},
        ]
        created = seed_activities(client, activities, {})
        assert created == 1

    def test_uses_correct_endpoint_per_type(self):
        client = MagicMock()
        client.post.return_value = ({"id": "act_3"}, 201)
        client.put.return_value = ({}, 200)
        client.throttle = MagicMock()

        activities = [
            {"type": "meeting", "subject": "Kickoff", "body": "...",
             "timestamp": "2026-05-10T10:00:00Z", "contact_email": "s@a.com"},
        ]
        seed_activities(client, activities, {"s@a.com": "c_1"})
        post_path = client.post.call_args[0][0]
        assert post_path == "/crm/v3/objects/meetings"

    def test_does_not_send_forge_source(self):
        """Activities don't support custom properties — no forge_source."""
        client = MagicMock()
        client.post.return_value = ({"id": "100"}, 201)
        client.put.return_value = ({}, 200)
        client.throttle = MagicMock()

        activities = [{"type": "note", "body": "Test", "contact_email": "a@b.com"}]
        seed_activities(client, activities, {"a@b.com": "1"})

        create_call = client.post.call_args_list[0]
        props = create_call[0][1]["properties"]
        assert "forge_source" not in props
