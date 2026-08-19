"""Object associations — v4 API pattern."""


def associate_contacts_to_companies(
    client,
    contacts: list[dict],
    company_id_map: dict[str, str],
) -> int:
    """Associate contacts to companies by email domain.

    Returns count of successful links.
    """
    print("\n-- Associations: Contact -> Company " + "-" * 19)
    linked = 0

    for contact in contacts:
        email = contact.get("email", "")
        domain = email.split("@")[-1] if "@" in email else ""

        if domain not in company_id_map:
            print(f"  skipped: {email} (no company for {domain})")
            continue

        company_id = company_id_map[domain]

        # Find contact ID by email
        search_body = {
            "filterGroups": [{
                "filters": [{
                    "propertyName": "email",
                    "operator": "EQ",
                    "value": email,
                }]
            }],
            "properties": ["email"],
            "limit": 1,
        }
        result, _ = client.post("/crm/v3/objects/contacts/search", search_body)
        results = result.get("results", [])
        if not results:
            print(f"  skipped: {email} (not found in HubSpot)")
            client.throttle()
            continue

        contact_id = results[0]["id"]

        _, status = client.put(
            f"/crm/v4/objects/contacts/{contact_id}/associations/default/companies/{company_id}"
        )
        if status in (200, 201):
            linked += 1
            name = f"{contact.get('firstname', '')} {contact.get('lastname', '')}".strip()
            print(f"  linked: {name} -> company {company_id}")
        else:
            print(f"  ERROR {status}: {email}")

        client.throttle()

    print(f"  --- {linked} contacts linked")
    return linked


def associate_deals(
    client,
    deal_records: list[dict],
    company_id_map: dict[str, str],
    company_name_to_domain: dict[str, str],
    contact_ids_by_company: dict[str, list[str]],
) -> int:
    """Associate deals to companies and contacts.

    deal_records: [{"id": deal_id, "company_name": name, ...}]
    contact_ids_by_company: {domain: [contact_hubspot_ids]}
    """
    print("\n-- Associations: Deal -> Company/Contact " + "-" * 14)
    linked = 0

    for deal in deal_records:
        deal_id = deal["id"]
        company_name = deal.get("company_name", "")
        domain = company_name_to_domain.get(company_name, "")

        # Deal -> Company
        if domain and domain in company_id_map:
            company_id = company_id_map[domain]
            _, status = client.put(
                f"/crm/v4/objects/deals/{deal_id}/associations/default/companies/{company_id}"
            )
            if status in (200, 201):
                linked += 1
                print(f"  linked: deal {deal_id} -> company {company_name}")
            client.throttle()

        # Deal -> first Contact at that company
        contact_ids = contact_ids_by_company.get(domain, [])
        if contact_ids:
            _, status = client.put(
                f"/crm/v4/objects/deals/{deal_id}/associations/default/contacts/{contact_ids[0]}"
            )
            if status in (200, 201):
                linked += 1
                print(f"  linked: deal {deal_id} -> contact {contact_ids[0]}")
            client.throttle()

    print(f"  --- {linked} associations created")
    return linked


def associate_tickets(
    client,
    ticket_records: list[dict],
    company_id_map: dict[str, str],
) -> int:
    """Associate tickets to contacts and companies.

    ticket_records: [{"id": ticket_id, "contact_email": email}]
    """
    print("\n-- Associations: Ticket -> Contact/Company " + "-" * 11)
    linked = 0

    for ticket in ticket_records:
        ticket_id = ticket["id"]
        email = ticket.get("contact_email", "")
        domain = email.split("@")[-1] if "@" in email else ""

        if email:
            search_body = {
                "filterGroups": [{
                    "filters": [{
                        "propertyName": "email",
                        "operator": "EQ",
                        "value": email,
                    }]
                }],
                "properties": ["email"],
                "limit": 1,
            }
            result, _ = client.post("/crm/v3/objects/contacts/search", search_body)
            results = result.get("results", [])
            if results:
                contact_id = results[0]["id"]
                _, status = client.put(
                    f"/crm/v4/objects/tickets/{ticket_id}/associations/default/contacts/{contact_id}"
                )
                if status in (200, 201):
                    linked += 1
                client.throttle()

        if domain and domain in company_id_map:
            company_id = company_id_map[domain]
            _, status = client.put(
                f"/crm/v4/objects/tickets/{ticket_id}/associations/default/companies/{company_id}"
            )
            if status in (200, 201):
                linked += 1
            client.throttle()

    print(f"  --- {linked} ticket associations created")
    return linked
