"""CLI entrypoint for HubSpot Demo Forge."""

import argparse
import json
import os
import random
import sys
import uuid
from datetime import datetime

from forge.client import HubSpotClient
from forge.config import load_profile
from forge.defaults import apply_defaults
from forge.properties import get_properties_for_profile, create_all_properties
from forge.generate import (
    generate_companies, generate_contacts, generate_deals,
    generate_products, generate_tickets, generate_activities,
)
from forge.companies import seed_companies
from forge.contacts import seed_contacts, get_contact_id_by_email
from forge.deals import seed_deals, flip_stages
from forge.products import seed_products, seed_line_items
from forge.tickets import seed_tickets
from forge.activities import seed_activities
from forge.associations import (
    associate_contacts_to_companies, associate_deals, associate_tickets,
)
from forge.campaigns import seed_campaigns, generate_email_csv
from forge.engage import cmd_engage_contacts
from forge.cleanup import discover_forge_records, cleanup_forge_records


def generate_session_id() -> str:
    """Generate a unique forge session ID."""
    date = datetime.now().strftime("%Y%m%d")
    short_hex = uuid.uuid4().hex[:6]
    return f"forge-{date}-{short_hex}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="forge",
        description="HubSpot Demo Forge — generate and seed realistic demo environments",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # seed command
    seed_cmd = sub.add_parser("seed", help="Generate data and seed a HubSpot portal")
    seed_cmd.add_argument("profile", help="Path to profile config (JSON or YAML)")
    seed_cmd.add_argument("--dry-run", action="store_true",
                          help="Generate data but don't push to HubSpot")
    seed_cmd.add_argument("--skip-properties", action="store_true",
                          help="Skip custom property creation")
    seed_cmd.add_argument("--skip-generation", action="store_true",
                          help="Skip AI generation (use cached data)")
    seed_cmd.add_argument("--cache-dir", default=".forge-cache",
                          help="Directory for cached generated data")

    # refresh-deals command
    refresh_cmd = sub.add_parser("refresh-deals", help="Flip deal stages to reset time-in-stage")
    refresh_cmd.add_argument("--all", action="store_true",
                             help="Include ALL deals in the pipeline (not just forge-owned)")

    # campaigns command
    camp = sub.add_parser("campaigns", help="Campaign management")
    camp_sub = camp.add_subparsers(dest="campaigns_command", required=True)
    camp_seed = camp_sub.add_parser("seed", help="Seed demo campaigns with goals and email data")
    camp_seed.add_argument("--dry-run", action="store_true",
                           help="Preview campaigns without creating")
    camp_seed.add_argument("--original-dates", action="store_true",
                           help="Use original CSV dates (don't shift to present)")

    # engage command
    engage_cmd = sub.add_parser("engage", help="Simulate engagement levels and populate fit properties")
    engage_cmd.add_argument("profile", help="Path to profile config (JSON or YAML)")
    engage_cmd.add_argument("--dry-run", action="store_true",
                            help="Preview engagement distribution without updating HubSpot")
    engage_cmd.add_argument("--limit", type=int, default=None,
                            help="Only process first N contacts")
    engage_cmd.add_argument("--all", action="store_true",
                            help="Include ALL contacts (not just forge-owned)")

    # cleanup command
    cleanup_cmd = sub.add_parser("cleanup", help="Remove forge-created demo data from HubSpot")
    cleanup_cmd.add_argument("--session", default=None,
                             help="Only clean up records from a specific session ID")
    cleanup_cmd.add_argument("--dry-run", action="store_true",
                             help="Preview what would be deleted without deleting")
    cleanup_cmd.add_argument("--confirm", action="store_true",
                             help="Skip confirmation prompt")

    # sessions command
    sub.add_parser("sessions", help="List saved seed sessions")

    # validate command
    validate_cmd = sub.add_parser("validate", help="Validate a profile")
    validate_cmd.add_argument("profile", help="Path to profile JSON")

    # preview command
    preview_cmd = sub.add_parser("preview", help="Preview what a profile would create")
    preview_cmd.add_argument("profile", help="Path to profile JSON")

    return parser


def _banner(title: str):
    print("=" * 55)
    print(f"  {title}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)


def cmd_seed(args):
    """Full seed pipeline: generate -> properties -> seed -> associate -> flip."""
    _banner("HubSpot Demo Forge — Seed")

    profile = load_profile(args.profile)
    profile = apply_defaults(profile)

    counts = profile["counts"]
    print(f"\n  Profile: {profile['company']['name']}")
    print(f"  Industry: {profile['company']['industry']}")
    print(f"  Companies: {counts['companies']}")
    print(f"  Deals: {counts['deals']}")
    if counts.get("tickets"):
        print(f"  Tickets: {counts['tickets']}")
    if counts.get("products"):
        print(f"  Products: {counts['products']}")
    if counts.get("activities_per_contact"):
        print(f"  Activities: {counts['activities_per_contact']} per contact")

    # -- Step 1: Generate data --
    cache_dir = args.cache_dir
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, "generated_data.json")

    if args.skip_generation and os.path.exists(cache_file):
        print("\n  Loading cached data...")
        with open(cache_file) as f:
            gen_data = json.load(f)
        all_companies = gen_data["companies"]
        all_contacts = gen_data["contacts"]
        all_deals = gen_data["deals"]
        all_products = gen_data.get("products", [])
        all_tickets = gen_data.get("tickets", [])
        all_activities = gen_data.get("activities", [])
    else:
        print("\n  Generating data via Claude API...")
        all_companies = generate_companies(profile)
        print(f"  Generated {len(all_companies)} companies")

        all_contacts = []
        lo, hi = counts["contacts_per_company"]
        for company in all_companies:
            count = random.randint(lo, hi)
            contacts = generate_contacts(company, count, profile["company"]["icp"])
            all_contacts.extend(contacts)
            print(f"  Generated {len(contacts)} contacts for {company['name']}")

        all_deals = generate_deals(
            all_companies, counts["deals"], profile["company"]["industry"],
        )
        print(f"  Generated {len(all_deals)} deals")

        # v1: conditional generation
        all_products = []
        if counts.get("products", 0) > 0:
            prod_cfg = profile.get("products", {})
            all_products = generate_products(
                profile["company"]["industry"],
                counts["products"],
                prod_cfg.get("price_range", [5000, 50000]),
            )
            print(f"  Generated {len(all_products)} products")

        all_tickets = []
        if counts.get("tickets", 0) > 0:
            all_tickets = generate_tickets(
                all_companies, all_contacts, counts["tickets"],
            )
            print(f"  Generated {len(all_tickets)} tickets")

        all_activities = []
        apc = counts.get("activities_per_contact", 0)
        if apc and apc != [0, 0]:
            act_cfg = profile.get("activities", {})
            act_range = apc if isinstance(apc, list) else [apc, apc]
            all_activities = generate_activities(
                all_contacts,
                act_range,
                act_cfg.get("types", ["call", "email", "meeting", "note"]),
                act_cfg.get("recency_days", 90),
            )
            print(f"  Generated {len(all_activities)} activities")

        # Cache generated data
        with open(cache_file, "w") as f:
            json.dump({
                "companies": all_companies,
                "contacts": all_contacts,
                "deals": all_deals,
                "products": all_products,
                "tickets": all_tickets,
                "activities": all_activities,
            }, f, indent=2)
        print(f"  Cached to {cache_file}")

    if args.dry_run:
        print("\n  --dry-run: skipping HubSpot operations")
        print(f"\n  Generated data summary:")
        print(f"    Companies:  {len(all_companies)}")
        print(f"    Contacts:   {len(all_contacts)}")
        print(f"    Deals:      {len(all_deals)}")
        if all_products:
            print(f"    Products:   {len(all_products)}")
        if all_tickets:
            print(f"    Tickets:    {len(all_tickets)}")
        if all_activities:
            print(f"    Activities: {len(all_activities)}")
        print("\n" + "=" * 55)
        return

    # -- Step 2: Connect to HubSpot --
    client = HubSpotClient.from_env()

    session_id = generate_session_id()
    print(f"\n  Session: {session_id}")

    # -- Step 3: Properties --
    if not args.skip_properties:
        props_cfg = profile.get("properties", {})
        if props_cfg:
            print("\n-- Properties " + "-" * 41)
            props_by_type = get_properties_for_profile(profile)
            for obj_type, props in props_by_type.items():
                print(f"\n  {obj_type}:")
                create_all_properties(client, obj_type, props)

    # forge_source tracking property is required safety infrastructure —
    # always created, even with --skip-properties
    from forge.properties import get_forge_tracking_property, FORGE_TRACKED_TYPES
    print("\n  forge_source tracking:")
    for obj_type in FORGE_TRACKED_TYPES:
        forge_prop = get_forge_tracking_property(obj_type)
        create_all_properties(client, obj_type, [forge_prop])

    # -- Step 4: Seed companies --
    company_id_map = seed_companies(client, all_companies, forge_source=session_id)
    company_name_to_domain = {c["name"]: c["domain"] for c in all_companies}

    # -- Step 5: Seed contacts --
    seed_contacts(client, all_contacts, forge_source=session_id)

    # -- Step 6: Seed deals --
    deal_records = seed_deals(client, all_deals, profile["pipeline"], forge_source=session_id)

    # -- Step 7: Seed products + line items (conditional) --
    product_id_map = {}
    if all_products:
        product_id_map = seed_products(client, all_products, forge_source=session_id)
        prod_cfg = profile.get("products", {})
        seed_line_items(
            client, deal_records, product_id_map, all_products,
            prod_cfg.get("line_items_per_deal", [1, 3]),
        )

    # -- Step 8: Seed tickets (conditional) --
    ticket_records = []
    if all_tickets:
        ticket_cfg = profile.get("tickets", {})
        ticket_records = seed_tickets(client, all_tickets, ticket_cfg, forge_source=session_id)

    # -- Step 9: Seed activities (conditional) --
    contact_email_to_id = {}
    if all_activities:
        for contact in all_contacts:
            email = contact.get("email", "")
            cid = get_contact_id_by_email(client, email)
            if cid:
                contact_email_to_id[email] = cid
            client.throttle()
        seed_activities(client, all_activities, contact_email_to_id)

    # -- Step 10: Associations --
    associate_contacts_to_companies(client, all_contacts, company_id_map)

    contact_ids_by_company = {}
    if not contact_email_to_id:
        for contact in all_contacts:
            email = contact.get("email", "")
            domain = email.split("@")[-1] if "@" in email else ""
            cid = get_contact_id_by_email(client, email)
            if cid and domain:
                contact_ids_by_company.setdefault(domain, []).append(cid)
            client.throttle()
    else:
        for email, cid in contact_email_to_id.items():
            domain = email.split("@")[-1] if "@" in email else ""
            if domain:
                contact_ids_by_company.setdefault(domain, []).append(cid)

    associate_deals(
        client, deal_records, company_id_map,
        company_name_to_domain, contact_ids_by_company,
    )

    if ticket_records:
        associate_tickets(client, ticket_records, company_id_map)

    # -- Step 11: Stage flip --
    deal_stage_map = {d["id"]: d["dealstage"] for d in deal_records}
    flip_stages(client, deal_stage_map, profile["pipeline"])

    # Save session manifest
    sessions_dir = os.path.join(cache_dir, "sessions")
    os.makedirs(sessions_dir, exist_ok=True)
    manifest = {
        "session_id": session_id,
        "profile": args.profile,
        "timestamp": datetime.now().isoformat(),
        "counts": {
            "companies": len(company_id_map),
            "contacts": len(all_contacts),
            "deals": len(deal_records),
            "products": len(product_id_map),
            "tickets": len(ticket_records),
            "activities": len(all_activities),
        },
    }
    manifest_path = os.path.join(sessions_dir, f"{session_id}.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\n  Session manifest: {manifest_path}")

    # -- Summary --
    print("\n" + "=" * 55)
    print("  Seed complete")
    print(f"  Session:      {session_id}")
    print(f"  Companies:    {len(company_id_map)}")
    print(f"  Contacts:     {len(all_contacts)}")
    print(f"  Deals:        {len(deal_records)}")
    if product_id_map:
        print(f"  Products:     {len(product_id_map)}")
    if ticket_records:
        print(f"  Tickets:      {len(ticket_records)}")
    if all_activities:
        print(f"  Activities:   {len(all_activities)}")
    print("  Associations: linked")
    print("  Time-in-stage: reset")
    print("  Ready for demo.")
    print("=" * 55)


def cmd_refresh_deals(args):
    """Re-flip deal stages to refresh time-in-stage (no generation needed)."""
    _banner("Deal Demo Refresh")
    client = HubSpotClient.from_env()

    filters = [{
        "propertyName": "pipeline",
        "operator": "EQ",
        "value": "default",
    }]

    if not args.all:
        filters.append({
            "propertyName": "forge_source",
            "operator": "HAS_PROPERTY",
        })
        print("\nFetching forge-owned deals in default pipeline...")
    else:
        print("\n  WARNING: --all mode — refreshing ALL deals in the pipeline")
        print("\nFetching all deals in default pipeline...")

    deals = client.fetch_all("/crm/v3/objects/deals/search", {
        "filterGroups": [{
            "filters": filters,
        }],
        "properties": ["dealname", "dealstage", "closedate", "pipeline"],
        "sorts": [{"propertyName": "createdate", "direction": "ASCENDING"}],
    })
    print(f"  Found {len(deals)} deals")

    if not deals:
        print("  Nothing to do.")
        return

    deal_stage_map = {
        d["id"]: d.get("properties", {}).get("dealstage", "")
        for d in deals
    }
    pipeline_cfg = {
        "temp_stage": "appointmentscheduled",
        "stages": {
            "warm": {"id": "qualifiedtobuy"},
            "at_risk": {"id": "contractsent"},
            "dormant": {"id": "presentationscheduled"},
        },
    }
    flip_stages(client, deal_stage_map, pipeline_cfg)


def cmd_campaigns_seed(args):
    """Seed curated demo campaigns and generate email CSV."""
    _banner("HubSpot Demo Forge — Campaigns")

    if args.dry_run:
        campaign_id_map = seed_campaigns(None, original_dates=args.original_dates, dry_run=True)
        print("\n  --dry-run: no HubSpot operations performed")
        return

    client = HubSpotClient.from_env()

    # Step 1: Create campaigns
    campaign_id_map = seed_campaigns(client, original_dates=args.original_dates)

    if not campaign_id_map:
        print("\n  No campaigns created — skipping email CSV")
        return

    # Step 2: Generate email CSV
    cache_dir = ".forge-cache"
    os.makedirs(cache_dir, exist_ok=True)
    email_csv_path = os.path.join(cache_dir, "demo_emails.csv")
    generate_email_csv(email_csv_path)

    # Summary
    print("\n" + "=" * 55)
    print("  Campaigns complete")
    print(f"  Campaigns: {len(campaign_id_map)}")
    print(f"  Email CSV: {email_csv_path}")
    print("=" * 55)


def cmd_engage(args):
    """Fetch contacts, assign engagement levels, populate fit + engagement properties."""
    _banner("HubSpot Demo Forge — Engage")

    profile = load_profile(args.profile)
    props_config = profile.get("properties", {})
    preset = props_config.get("preset", "default")
    sets = props_config.get("sets", ["fit", "engagement"])

    print(f"\n  Profile: {profile['company']['name']}")
    print(f"  Preset: {preset}")
    print(f"  Sets: {sets}")

    client = HubSpotClient.from_env()
    result = cmd_engage_contacts(
        client,
        preset=preset,
        enabled_sets=sets,
        dry_run=args.dry_run,
        limit=args.limit,
        all_contacts=args.all,
    )

    print("\n" + "=" * 55)
    print("  Engage complete")
    print(f"  Total:  {result['total']}")
    print(f"  Hot:    {result['hot']}")
    print(f"  Warm:   {result['warm']}")
    print(f"  Cold:   {result['cold']}")
    print("=" * 55)


def cmd_cleanup(args):
    """Search for and remove forge-created demo data."""
    _banner("HubSpot Demo Forge — Cleanup")

    client = HubSpotClient.from_env()

    if args.session:
        print(f"\n  Session filter: {args.session}")
    else:
        print("\n  Scope: ALL forge-created records")

    # Discovery
    print("\n-- Discovering forge records " + "-" * 27)
    records = discover_forge_records(client, session_id=args.session)

    total = sum(len(ids) for ids in records.values())
    if total == 0:
        print("\n  No forge-created records found.")
        return

    print(f"\n  Found {total} records to clean up:")
    for obj_type, ids in records.items():
        if ids:
            print(f"    {obj_type}: {len(ids)}")

    # Confirmation
    if args.dry_run:
        print("\n-- Dry run " + "-" * 44)
        cleanup_forge_records(client, records, dry_run=True)
        print("\n  No records were deleted (--dry-run)")
        return

    if not args.confirm:
        print("\n  Run with --confirm to proceed, or --dry-run to preview.")
        return

    # Deletion
    print("\n-- Archiving records " + "-" * 34)
    deleted = cleanup_forge_records(client, records)

    # Summary
    total_deleted = sum(deleted.values())
    print("\n" + "=" * 55)
    print("  Cleanup complete")
    print(f"  Archived: {total_deleted} records")
    for obj_type, count in deleted.items():
        if count:
            print(f"    {obj_type}: {count}")
    print("=" * 55)


def cmd_sessions(args):
    """List saved session manifests."""
    _banner("HubSpot Demo Forge — Sessions")

    sessions_dir = os.path.join(".forge-cache", "sessions")
    if not os.path.exists(sessions_dir):
        print("\n  No sessions found.")
        return

    manifests = sorted(
        [f for f in os.listdir(sessions_dir) if f.endswith(".json")],
        reverse=True,
    )

    if not manifests:
        print("\n  No sessions found.")
        return

    print(f"\n  Found {len(manifests)} session(s):\n")
    for fname in manifests:
        with open(os.path.join(sessions_dir, fname)) as f:
            m = json.load(f)
        counts = m.get("counts", {})
        total = sum(counts.values())
        print(f"  {m['session_id']}")
        print(f"    Profile:  {m.get('profile', '?')}")
        print(f"    Date:     {m.get('timestamp', '?')[:19]}")
        print(f"    Records:  {total}")
        print()


def cmd_validate(args):
    """Validate a profile without requiring any credentials."""
    try:
        profile = load_profile(args.profile)
        props = profile.get("properties", {})
        preset = props.get("preset", "default")
        sets = props.get("sets", [])

        print(f"Profile valid: {args.profile}")
        print(f"  Preset: {preset}")
        print(f"  Sets: {sets}")
        print(f"  Companies: {profile['counts']['companies']}")
        print(f"  Contacts per company: {profile['counts']['contacts_per_company']}")
        print(f"  Deals: {profile['counts']['deals']}")
    except Exception as e:
        print(f"Validation failed: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_preview(args):
    """Preview what a profile would create — no credentials required."""
    try:
        profile = load_profile(args.profile)
    except Exception as e:
        print(f"Profile error: {e}", file=sys.stderr)
        sys.exit(1)

    props = profile.get("properties", {})
    preset = props.get("preset", "default")
    sets = props.get("sets", [])
    counts = profile["counts"]

    print(f"\n== Profile Preview: {args.profile} ==\n")

    # Object counts
    print("Objects to create:")
    print(f"  Companies: {counts['companies']}")
    cpc = counts["contacts_per_company"]
    if isinstance(cpc, list):
        print(f"  Contacts per company: {cpc[0]}-{cpc[1]}")
    else:
        print(f"  Contacts per company: {cpc}")
    print(f"  Deals: {counts['deals']}")

    # Property schemas
    if sets:
        from forge.hubspot_adapter import build_property_schemas
        schemas = build_property_schemas(sets, preset)
        print(f"\nCustom properties (preset: {preset}):")
        for obj_type, props_list in sorted(schemas.items()):
            print(f"\n  {obj_type} ({len(props_list)} properties):")
            for prop in props_list:
                print(f"    - {prop['name']} ({prop['type']})")
    else:
        print("\nNo custom property sets enabled.")

    print()


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "seed":
        cmd_seed(args)
    elif args.command == "refresh-deals":
        cmd_refresh_deals(args)
    elif args.command == "campaigns":
        cmd_campaigns_seed(args)
    elif args.command == "engage":
        cmd_engage(args)
    elif args.command == "cleanup":
        cmd_cleanup(args)
    elif args.command == "sessions":
        cmd_sessions(args)
    elif args.command == "validate":
        cmd_validate(args)
    elif args.command == "preview":
        cmd_preview(args)


if __name__ == "__main__":
    main()
