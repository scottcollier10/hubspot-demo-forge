"""Activity seeding — calls, emails, meetings, notes."""

ACTIVITY_ENDPOINTS = {
    "call": "/crm/v3/objects/calls",
    "email": "/crm/v3/objects/emails",
    "meeting": "/crm/v3/objects/meetings",
    "note": "/crm/v3/objects/notes",
}

TIMESTAMP_PROPS = {
    "call": "hs_timestamp",
    "email": "hs_timestamp",
    "meeting": "hs_timestamp",
    "note": "hs_timestamp",
}

BODY_PROPS = {
    "call": "hs_call_body",
    "email": "hs_email_text",
    "meeting": "hs_meeting_body",
    "note": "hs_note_body",
}

SUBJECT_PROPS = {
    "call": "hs_call_title",
    "email": "hs_email_subject",
    "meeting": "hs_meeting_title",
    "note": "hs_note_body",
}


def seed_activities(
    client,
    activities: list[dict],
    contact_email_to_id: dict[str, str],
) -> int:
    """Create activities and associate to contacts.

    Returns count of created activities.
    """
    print("\n-- Activities " + "-" * 41)
    created = 0

    for activity in activities:
        act_type = activity.get("type", "note")
        endpoint = ACTIVITY_ENDPOINTS.get(act_type)
        if not endpoint:
            print(f"  skipped: unknown type '{act_type}'")
            continue

        contact_email = activity.get("contact_email", "")

        props = {
            TIMESTAMP_PROPS[act_type]: activity.get("timestamp", ""),
            BODY_PROPS[act_type]: activity.get("body", ""),
        }
        if act_type != "note":
            props[SUBJECT_PROPS[act_type]] = activity.get("subject", "")

        # Email engagements require direction
        if act_type == "email":
            props["hs_email_direction"] = "EMAIL"  # outbound sent email

        result, status = client.post(endpoint, {"properties": props})

        if status in (200, 201):
            act_id = result["id"]
            created += 1
            print(f"  created: {act_type} — {activity.get('subject', '?')}")

            if contact_email in contact_email_to_id:
                contact_id = contact_email_to_id[contact_email]
                client.put(
                    f"/crm/v4/objects/{act_type}s/{act_id}/associations/default/contacts/{contact_id}"
                )
        else:
            print(f"  ERROR {status}: {act_type} — {activity.get('subject', '?')}")

        client.throttle()

    print(f"  --- {created} activities created")
    return created
