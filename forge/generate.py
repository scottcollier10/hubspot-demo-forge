"""AI-powered demo data generation via Claude API.

Calls the Anthropic Messages API with raw urllib.request (zero deps).
Requires ANTHROPIC_API_KEY environment variable.
"""

import json
import os
import sys
import urllib.error
import urllib.request

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
MODEL = "claude-sonnet-4-20250514"


def _call_claude(prompt: str, max_tokens: int = 4096) -> str:
    """Send a prompt to Claude API, return the text response."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set.")
        print("  Run: export ANTHROPIC_API_KEY=sk-ant-xxxxx")
        sys.exit(1)

    body = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(ANTHROPIC_API_URL, data=data, method="POST")
    req.add_header("x-api-key", api_key)
    req.add_header("content-type", "application/json")
    req.add_header("anthropic-version", ANTHROPIC_VERSION)

    with urllib.request.urlopen(req, timeout=120) as response:
        result = json.loads(response.read().decode())
        return result["content"][0]["text"]


def _parse_json_response(text: str) -> list[dict]:
    """Extract JSON array from Claude's response, handling markdown fences."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines[1:] if not l.strip().startswith("```")]
        text = "\n".join(lines)
    return json.loads(text)


def generate_companies(profile: dict) -> list[dict]:
    """Generate realistic company data based on profile."""
    company_cfg = profile["company"]
    count = profile["counts"]["companies"]

    prompt = f"""Generate exactly {count} realistic but fictional companies for a HubSpot demo.

Context: These companies are potential customers of a {company_cfg['industry']} company
called "{company_cfg['name']}" (company size: {company_cfg['size']}).
ICP: {company_cfg['icp']}

Return a JSON array where each object has these exact fields:
- "name": realistic company name (no real companies)
- "domain": a domain under .example.com (e.g., acmesaas.example.com, northstar.example.com). IMPORTANT: all domains MUST use .example.com to avoid targeting real registrable domains.
- "industry": HubSpot industry value (e.g., "COMPUTER_SOFTWARE", "MARKETING", "FINANCE")
- "numberofemployees": string number (e.g., "250")
- "city": US city
- "state": US state
- "phone": use 555-01xx format (e.g., "555-0100") to avoid real numbers

Mix of company sizes matching the ICP. Domains must be unique.
Return ONLY the JSON array, no explanation."""

    text = _call_claude(prompt)
    return _parse_json_response(text)


def generate_contacts(company: dict, count: int, profile_icp: str) -> list[dict]:
    """Generate realistic contacts for a single company."""
    prompt = f"""Generate exactly {count} realistic but fictional contacts who work at
"{company['name']}" (domain: {company['domain']}, industry: {company.get('industry', 'tech')}).

ICP context: {profile_icp}

Return a JSON array where each object has these exact fields:
- "firstname": realistic first name
- "lastname": realistic last name
- "email": must end with @{company['domain']}
- "jobtitle": realistic title (mix of seniority levels — include some abbreviated like "VP Mktg", "Sr. Dir. Eng")
- "phone": use 555-01xx format (e.g., "555-0142") to avoid real numbers

Include a mix of:
- 1-2 senior leaders (VP, Director, C-level)
- The rest mid-level or individual contributors

Return ONLY the JSON array, no explanation."""

    text = _call_claude(prompt)
    return _parse_json_response(text)


def generate_deals(companies: list[dict], count: int, profile_industry: str) -> list[dict]:
    """Generate realistic deals across the given companies."""
    company_names = [c["name"] for c in companies]

    prompt = f"""Generate exactly {count} realistic but fictional B2B deals for a HubSpot demo.

These deals involve these companies as buyers: {json.dumps(company_names)}
Industry context: {profile_industry}

Return a JSON array where each object has these exact fields:
- "dealname": format as "Company Name — Deal Description" (e.g., "Acme Corp — Platform License")
- "amount": string dollar amount, no decimals (e.g., "45000")
- "company_name": must match one of the company names above exactly

Distribute deals across companies (some may have multiple, some may have one).
Deal amounts should be realistic for the industry ($10k-$500k range).

Return ONLY the JSON array, no explanation."""

    text = _call_claude(prompt)
    return _parse_json_response(text)


def generate_products(profile_industry: str, count: int, price_range: list[int]) -> list[dict]:
    """Generate a product catalog."""
    lo, hi = price_range

    prompt = f"""Generate exactly {count} realistic but fictional B2B software products for a HubSpot demo.

Industry context: {profile_industry}

Return a JSON array where each object has these exact fields:
- "name": product name (e.g., "Platform License", "API Access Tier", "Premium Support")
- "price": string dollar amount between {lo} and {hi}, no decimals (e.g., "25000")
- "description": one-sentence product description
- "hs_sku": a short SKU code (e.g., "PLT-001", "API-002")

Products should be things a {profile_industry} company would sell.
Return ONLY the JSON array, no explanation."""

    text = _call_claude(prompt)
    return _parse_json_response(text)


def generate_tickets(
    companies: list[dict], contacts: list[dict], count: int
) -> list[dict]:
    """Generate realistic support tickets."""
    company_names = [c["name"] for c in companies]
    contact_sample = [
        f"{c.get('firstname', '')} {c.get('lastname', '')} ({c.get('email', '')})"
        for c in contacts[:20]
    ]

    prompt = f"""Generate exactly {count} realistic but fictional support tickets for a HubSpot demo.

Companies involved: {json.dumps(company_names)}
Sample contacts: {json.dumps(contact_sample)}

Return a JSON array where each object has these exact fields:
- "subject": ticket subject line (realistic IT/product support issue)
- "content": 1-2 sentence ticket description
- "hs_ticket_priority": one of "HIGH", "MEDIUM", "LOW"
- "contact_email": must be one of the contact emails above, or a realistic email @one of the company domains

Mix of priorities (mostly MEDIUM, some HIGH, some LOW).
Return ONLY the JSON array, no explanation."""

    text = _call_claude(prompt)
    return _parse_json_response(text)


def generate_activities(
    contacts: list[dict], count_range: list[int], activity_types: list[str], recency_days: int
) -> list[dict]:
    """Generate realistic activities distributed across contacts.

    Batches in groups of ~30 activities to avoid token limits.
    """
    types_str = ", ".join(activity_types)
    lo, hi = count_range
    all_activities = []

    # Process contacts in batches to keep each API call under token limits
    BATCH_SIZE = 10  # contacts per batch, ~30-80 activities per call
    total_batches = (len(contacts) + BATCH_SIZE - 1) // BATCH_SIZE
    for i in range(0, len(contacts), BATCH_SIZE):
        batch_num = i // BATCH_SIZE + 1
        print(f"  Generating activities batch {batch_num}/{total_batches}...")
        batch_contacts = contacts[i : i + BATCH_SIZE]
        contact_sample = [
            {"name": f"{c.get('firstname', '')} {c.get('lastname', '')}", "email": c.get("email", "")}
            for c in batch_contacts
        ]
        batch_count = len(batch_contacts) * ((lo + hi) // 2)

        prompt = f"""Generate exactly {batch_count} realistic but fictional CRM activities for a HubSpot demo.

Activity types to include: {types_str}
Contacts to distribute across: {json.dumps(contact_sample)}
Activities should have timestamps within the last {recency_days} days.

Return a JSON array where each object has these exact fields:
- "type": one of {json.dumps(activity_types)}
- "subject": short activity subject (e.g., "Discovery call", "Follow-up email", "Quarterly review")
- "body": 1-2 sentence description of the activity
- "timestamp": ISO 8601 datetime within the last {recency_days} days (e.g., "2026-05-01T14:30:00Z")
- "contact_email": must be one of the contact emails listed above

Distribute activities across contacts (some contacts have more activity than others).
Mix of activity types weighted roughly: emails 40%, calls 25%, meetings 20%, notes 15%.
Return ONLY the JSON array, no explanation."""

        text = _call_claude(prompt, max_tokens=8192)
        all_activities.extend(_parse_json_response(text))

    return all_activities
