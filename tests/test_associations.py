from unittest.mock import MagicMock
from forge.associations import associate_contacts_to_companies, associate_deals, associate_tickets


class TestAssociateContactsToCompanies:
    def test_links_contact_to_company(self):
        client = MagicMock()
        # search returns contact
        client.post.return_value = ({"results": [{"id": "500"}]}, 200)
        client.put.return_value = ({}, 200)
        client.throttle = MagicMock()

        contacts = [{"email": "sarah@acme.com", "firstname": "Sarah", "lastname": "Chen"}]
        company_id_map = {"acme.com": "100"}

        linked = associate_contacts_to_companies(client, contacts, company_id_map)
        assert linked == 1
        # Verify v4 association endpoint
        put_path = client.put.call_args[0][0]
        assert "/associations/default/" in put_path
        assert "500" in put_path
        assert "100" in put_path


class TestAssociateDeals:
    def test_links_deal_to_company(self):
        client = MagicMock()
        client.put.return_value = ({}, 200)
        client.throttle = MagicMock()

        deal_records = [{"id": "900", "company_name": "Acme Corp"}]
        company_id_map = {"acme.com": "100"}
        company_name_to_domain = {"Acme Corp": "acme.com"}

        linked = associate_deals(client, deal_records, company_id_map,
                                 company_name_to_domain, contact_ids_by_company={})
        assert linked >= 1


class TestAssociateTickets:
    def test_links_ticket_to_contact_and_company(self):
        client = MagicMock()
        client.post.return_value = ({"results": [{"id": "c_500"}]}, 200)
        client.put.return_value = ({}, 200)
        client.throttle = MagicMock()

        ticket_records = [{"id": "t_1", "contact_email": "sarah@acme.com"}]
        company_id_map = {"acme.com": "co_100"}

        linked = associate_tickets(client, ticket_records, company_id_map)
        assert linked >= 1
