"""Contact seeding — create-or-update pattern."""


def seed_contacts(client, contacts: list[dict], forge_source: str = "") -> tuple[int, int, int]:
    """Create or update contacts. Returns (created, updated, skipped) counts.

    Only updates existing contacts if they are already forge-owned
    (have a forge_source property). Non-forge records are skipped to
    avoid claiming ownership of pre-existing CRM data.
    """
    print("\n-- Contacts " + "-" * 43)
    created = 0
    updated = 0
    skipped = 0

    for contact in contacts:
        email = contact.get("email", "")
        props = {**contact}
        if forge_source:
            props["forge_source"] = forge_source

        result, status = client.post("/crm/v3/objects/contacts", {"properties": props})

        if status == 409:
            # Contact exists — check if forge-owned before updating
            existing = client.get(
                f"/crm/v3/objects/contacts/{email}?idProperty=email&properties=forge_source"
            )
            existing_forge_source = (existing.get("properties") or {}).get("forge_source")

            if existing_forge_source:
                client.patch(
                    f"/crm/v3/objects/contacts/{email}?idProperty=email",
                    {"properties": props},
                )
                updated += 1
                print(f"  updated: {contact.get('firstname', '')} {contact.get('lastname', '')}")
            else:
                skipped += 1
                print(f"  SKIP  {email} (exists, not forge-owned)")
        elif status in (200, 201):
            created += 1
            print(f"  created: {contact.get('firstname', '')} {contact.get('lastname', '')}")
        else:
            print(f"  ERROR {status}: {email}")

        client.throttle()

    print(f"  --- {created} created, {updated} updated, {skipped} skipped (not forge-owned)")
    return created, updated, skipped


def get_contact_id_by_email(client, email: str) -> str | None:
    """Look up a contact's HubSpot ID by email."""
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
    return results[0]["id"] if results else None
