from unittest.mock import MagicMock
from forge.contacts import seed_contacts


class TestSeedContacts:
    def test_creates_new_contact(self):
        client = MagicMock()
        client.post.return_value = ({"id": "500"}, 201)
        client.throttle = MagicMock()

        contacts = [{"firstname": "Sarah", "lastname": "Chen",
                      "email": "sarah@acme.example.com", "jobtitle": "VP Marketing"}]
        created, updated, skipped = seed_contacts(client, contacts)
        assert created == 1
        assert updated == 0
        assert skipped == 0

    def test_updates_forge_owned_on_409(self):
        client = MagicMock()
        client.post.return_value = ({"message": "conflict"}, 409)
        client.get.return_value = {"properties": {"forge_source": "forge-old"}}
        client.patch.return_value = {"id": "501"}
        client.throttle = MagicMock()

        contacts = [{"firstname": "Sarah", "lastname": "Chen",
                      "email": "sarah@acme.example.com", "jobtitle": "VP Marketing"}]
        created, updated, skipped = seed_contacts(client, contacts)
        assert created == 0
        assert updated == 1
        assert skipped == 0
        client.patch.assert_called_once()

    def test_skips_non_forge_owned_on_409(self):
        """Existing contact without forge_source must NOT be modified or claimed."""
        client = MagicMock()
        client.post.return_value = ({"message": "conflict"}, 409)
        client.get.return_value = {"properties": {"forge_source": None}}
        client.throttle = MagicMock()

        contacts = [{"firstname": "Sarah", "lastname": "Chen",
                      "email": "sarah@acme.example.com", "jobtitle": "VP Marketing"}]
        created, updated, skipped = seed_contacts(client, contacts)
        assert created == 0
        assert updated == 0
        assert skipped == 1
        client.patch.assert_not_called()

    def test_skips_contact_with_empty_forge_source(self):
        """Empty string forge_source is treated as not forge-owned."""
        client = MagicMock()
        client.post.return_value = ({"message": "conflict"}, 409)
        client.get.return_value = {"properties": {"forge_source": ""}}
        client.throttle = MagicMock()

        contacts = [{"email": "a@b.example.com", "firstname": "A"}]
        created, updated, skipped = seed_contacts(client, contacts)
        assert skipped == 1
        client.patch.assert_not_called()

    def test_injects_forge_source(self):
        client = MagicMock()
        client.post.return_value = ({"id": "100"}, 201)
        client.throttle = MagicMock()

        contacts = [{"email": "a@b.example.com", "firstname": "A"}]
        seed_contacts(client, contacts, forge_source="forge-test-123")

        create_call = client.post.call_args_list[0]
        props = create_call[0][1]["properties"]
        assert props["forge_source"] == "forge-test-123"
