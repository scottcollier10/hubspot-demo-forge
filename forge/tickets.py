"""Ticket seeding with status distribution."""


def assign_ticket_statuses(tickets: list[dict], statuses_cfg: dict) -> dict[str, list[dict]]:
    """Split tickets into status buckets by weight."""
    total = len(tickets)
    buckets = {}
    start = 0
    status_names = list(statuses_cfg.keys())

    for i, name in enumerate(status_names):
        if i == len(status_names) - 1:
            buckets[name] = tickets[start:]
        else:
            count = round(total * statuses_cfg[name])
            buckets[name] = tickets[start : start + count]
            start += count

    return buckets


STATUS_STAGE_MAP = {
    "open": "1",
    "waiting": "2",
    "closed": "4",
}


def seed_tickets(client, tickets: list[dict], ticket_cfg: dict, forge_source: str = "") -> list[dict]:
    """Create tickets with assigned statuses.

    Returns list of {"id": hubspot_id, "contact_email": email}.
    """
    print("\n-- Tickets " + "-" * 44)
    pipeline = ticket_cfg.get("pipeline", "0")  # "0" is HubSpot's default ticket pipeline
    statuses = ticket_cfg.get("statuses", {"open": 0.4, "waiting": 0.3, "closed": 0.3})
    buckets = assign_ticket_statuses(tickets, statuses)
    created_tickets = []

    for status_name, bucket in buckets.items():
        stage_id = STATUS_STAGE_MAP.get(status_name, "1")
        for ticket in bucket:
            contact_email = ticket.pop("contact_email", None)
            props = {
                **ticket,
                "hs_pipeline": pipeline,
                "hs_pipeline_stage": stage_id,
            }
            if forge_source:
                props["forge_source"] = forge_source
            result, status = client.post(
                "/crm/v3/objects/tickets", {"properties": props}
            )
            if status in (200, 201):
                created_tickets.append({
                    "id": result["id"],
                    "contact_email": contact_email,
                })
                print(f"  created: {ticket.get('subject', '?')} [{status_name}]")
            else:
                print(f"  ERROR {status}: {ticket.get('subject', '?')}")

            client.throttle()

    print(f"  --- {len(created_tickets)} tickets created")
    return created_tickets
