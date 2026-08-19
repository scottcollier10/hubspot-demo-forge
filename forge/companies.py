"""Company seeding — search-then-upsert pattern."""


def seed_companies(client, companies: list[dict], forge_source: str = "") -> dict[str, str]:
    """Create or update companies. Returns {domain: hubspot_id} map.

    Only updates existing companies if they are already forge-owned
    (have a forge_source property). Non-forge records are skipped to
    avoid claiming ownership of pre-existing CRM data.
    """
    print("\n-- Companies " + "-" * 42)
    created = 0
    updated = 0
    skipped = 0
    company_id_map = {}

    for company in companies:
        domain = company.get("domain", "")
        props = {**company}
        if forge_source:
            props["forge_source"] = forge_source

        # Search by domain, include forge_source to check ownership
        search_body = {
            "filterGroups": [{
                "filters": [{
                    "propertyName": "domain",
                    "operator": "EQ",
                    "value": domain,
                }]
            }],
            "properties": ["name", "domain", "forge_source"],
            "limit": 1,
        }
        result, _ = client.post("/crm/v3/objects/companies/search", search_body)
        existing = result.get("results", [])

        if existing:
            record = existing[0]
            cid = record["id"]
            existing_forge_source = (record.get("properties") or {}).get("forge_source")

            if existing_forge_source:
                # Forge-owned — safe to update
                client.patch(f"/crm/v3/objects/companies/{cid}", {"properties": props})
                company_id_map[domain] = cid
                updated += 1
                print(f"  updated: {company['name']}")
            else:
                # Not forge-owned — skip to avoid claiming external records
                skipped += 1
                print(f"  SKIP  {company['name']} (domain {domain} exists, not forge-owned)")
        else:
            result, status = client.post("/crm/v3/objects/companies", {"properties": props})
            if status in (200, 201):
                company_id_map[domain] = result["id"]
                created += 1
                print(f"  created: {company['name']}")
            else:
                print(f"  ERROR {status}: {company['name']}")

        client.throttle()

    print(f"  --- {created} created, {updated} updated, {skipped} skipped (not forge-owned)")
    return company_id_map
