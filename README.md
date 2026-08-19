# HubSpot Demo Forge

![CI](https://github.com/scottcollier10/hubspot-demo-forge/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

Generate and seed realistic HubSpot demo environments from reusable profile definitions.

Replace hours of manual portal setup with a single command. Demo Forge uses AI to generate realistic companies, contacts, and deals, then seeds them into HubSpot with proper associations and custom properties.

## Who It's For

- **HubSpot consultants and agencies** building client demos
- **Solution engineers** preparing live portal walkthroughs
- **RevOps teams** testing workflows, scoring rules, and automations

## Safety First

Always start with `--dry-run` to preview what will be created. Use a test or developer portal until you're comfortable with the output. The `cleanup` command can remove seeded data, but treat production portals with care.

## Quick Start

```bash
# Install
pip install -e .

# Validate a profile (no credentials needed)
python -m forge validate profiles/full_portal.json

# Preview what would be created (no credentials needed)
python -m forge preview profiles/full_portal.json

# Dry run (generates data via Claude API, no HubSpot changes)
export ANTHROPIC_API_KEY=sk-ant-xxxxx
python -m forge seed profiles/full_portal.json --dry-run

# Seed a test portal
export HUBSPOT_TOKEN=pat-na1-xxxxx
python -m forge seed profiles/full_portal.json
```

## What It Creates

- Companies with realistic profiles (industry, size, location)
- Contacts with job titles, emails, phone numbers
- Deals with stage distribution and relative close dates
- Products and line items
- Support tickets
- CRM activities (calls, emails, meetings, notes)
- Object associations (contact-company, deal-contact, deal-company)
- Custom properties (configurable via presets)
- Engagement simulation (email opens, clicks, scores)

## Commands

### `forge validate [profile]`

Validate a profile config without credentials. Reports preset, enabled property sets, and object counts.

### `forge preview [profile]`

Preview what a profile would create, including custom property schemas. No credentials required.

### `forge seed [profile]`

Generate realistic data via Claude API and seed it into HubSpot.

| Flag | Description |
|------|-------------|
| `--dry-run` | Generate data but skip HubSpot API calls |
| `--skip-properties` | Skip custom property creation |
| `--skip-generation` | Use cached data from previous run |
| `--cache-dir` | Directory for cached data (default: `.forge-cache`) |

### `forge engage [profile]`

Fetch forge-owned contacts and set fit properties (seniority, department, persona) and engagement properties (email opens, clicks, scores). Contacts are distributed across engagement tiers:

| Level | % | Engagement | Status |
|-------|---|------------|--------|
| 1 (hot) | 20% | 8-15 opens, 3-8 clicks | Active |
| 2 (warm) | 30% | 2-6 opens, 0-2 clicks | At Risk |
| 3 (cold) | 50% | 0-1 opens, 0 clicks | Cold/Dormant |

| Flag | Description |
|------|-------------|
| `--dry-run` | Preview distribution without updating HubSpot |
| `--limit N` | Only process first N contacts |
| `--all` | Include all contacts, not just forge-owned |

### `forge refresh-deals`

Re-flip deal stages to reset "time in stage" for demos. Only touches forge-owned deals by default.

| Flag | Description |
|------|-------------|
| `--all` | Include all deals in the pipeline, not just forge-owned |

### `forge campaigns seed`

Seed curated demo campaigns and generate email engagement data.

| Flag | Description |
|------|-------------|
| `--dry-run` | Preview campaigns without creating |
| `--original-dates` | Use original CSV dates (don't shift to present) |

### `forge cleanup`

Remove forge-created demo data from HubSpot.

| Flag | Description |
|------|-------------|
| `--session ID` | Only clean up a specific session |
| `--dry-run` | Preview what would be deleted |
| `--confirm` | Skip confirmation prompt |

### `forge sessions`

List saved seed sessions.

## Profiles

Profiles are JSON files that define your demo environment. See [docs/profiles.md](docs/profiles.md) for the full schema reference.

```json
{
  "company": {
    "name": "Northstar SaaS",
    "industry": "B2B SaaS",
    "size": "mid-market",
    "icp": "Revenue leaders scaling from SMB to enterprise"
  },
  "counts": {
    "companies": 20,
    "contacts_per_company": [3, 10],
    "deals": 40
  },
  "properties": {
    "preset": "default",
    "sets": ["fit", "engagement"]
  }
}
```

## Presets

Presets control the naming convention for custom properties.

| Preset | Contact/Company Properties | Deal Properties |
|--------|---------------------------|-----------------|
| `default` | `forge_*` | `forge_*` |
| `canon` | `canon_*` | `engagement_*` |

The `default` preset uses `forge_` prefixed names. The `canon` preset uses the `canon_*` namespace for compatibility with Canon data normalization workflows. See [examples/canon/](examples/canon/) for details.

## Prerequisites

1. Python 3.11+
2. HubSpot developer account with a test portal
3. Private app with required scopes (see below)
4. `HUBSPOT_TOKEN` environment variable
5. `ANTHROPIC_API_KEY` environment variable (for data generation)

`validate` and `preview` commands work without any credentials.

### HubSpot permissions

Core seeding requires CRM read/write access for contacts, companies, deals, and their property schemas.

Optional profile features may require additional access:

- **Tickets**: ticket read/write
- **Products and line items**: product/line-item read/write
- **CRM activities**: calls, emails, meetings, and notes
- **Campaigns**: Marketing Campaigns read/write and an eligible HubSpot account

Enable only the scopes needed for the features you use.

## Development

```bash
pip install -e ".[dev]"
python -m pytest tests/ -v
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

## License

MIT
