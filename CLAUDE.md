# hubspot-demo-forge — Claude Code Context

## What This Is
HubSpot Demo Forge -- a CLI tool that generates and seeds
realistic HubSpot demo environments from a single config file.
Replaces hours of manual portal setup with a configurable,
AI-generated data seeder.

## Stack
- CLI: Python (zero external deps for core, Claude API for data generation)
- HubSpot API: Raw urllib.request (zero deps)
- Config: JSON profile files

## Architecture

### Three-Layer Property System
- **Field Registry** (`field_registry.py`): Single source of truth for all logical field definitions (22 fields across fit and engagement sets)
- **Presets** (`presets.py`): Name mapping from logical fields to HubSpot property names. `default` preset uses `forge_*`, `canon` preset uses `canon_*`/`engagement_*`
- **HubSpot Adapter** (`hubspot_adapter.py`): Builds property schemas and handles type-driven serialization for HubSpot wire format

### Core Modules
- Config-driven: company profile defines industry, size, ICP, counts
- AI generation: Claude API generates realistic contacts/companies/deals
- Batch seeding: HubSpot batch APIs for efficient writes
- Modular: separate modules for properties, companies, contacts, deals, associations
- Stage flip: deal refresh logic for "Time in Stage" reporting

## What It Automates
- Custom property creation (preset-driven naming)
- Company creation with realistic profiles
- Contact creation with appropriate titles/seniority per company
- Deal creation with stage distribution and relative close dates
- Object associations (contact-company, deal-contact, deal-company)
- Pipeline stage distribution (warm/at-risk/dormant)
- Time-in-stage reset via stage flip trick

## What It Does NOT Automate (manual prerequisites)
- HubSpot developer account creation
- Private app creation + PAT generation
- HubSpot lead scoring rule configuration

## Key Conventions
- Python: urllib.request, no heavy deps
- Batch API calls wherever possible (100 per call limit)
- HUBSPOT_TOKEN from environment variable
- Rate limit delays between API calls
- Console output with clear progress reporting
- Tests run without credentials (HUBSPOT_TOKEN, ANTHROPIC_API_KEY)

## Known Decisions
- Raw urllib.request over hubspot-api-client -- zero deps
- CLI-first -- ship the engine before the interface
- AI generation via Claude API -- not hardcoded demo data
- Deal-only isolation -- never modify contacts from deal logic
- Stable lowercase_snake enum values (e.g., "vp", "c_level", "active")
- Strict type serialization: date fields reject datetime, numbers become strings

## Hard Boundaries
- Each object type (contacts, companies, deals) stays in its own lane
- Never swap associations across demo systems
- Legacy config format supported via migration with deprecation warnings
- validate and preview commands must never require credentials

## HubSpot Private App Scopes (Required)

| Scope | Read/Write | Used For |
|-------|-----------|----------|
| `crm.objects.contacts.read` | Read | Search contacts by email for associations |
| `crm.objects.contacts.write` | Write | Create/update contacts, create associations |
| `crm.objects.companies.read` | Read | Search companies by domain (upsert check) |
| `crm.objects.companies.write` | Write | Create/update companies, create associations |
| `crm.objects.deals.read` | Read | Search deals by pipeline (refresh-deals) |
| `crm.objects.deals.write` | Write | Create deals, batch update stages, create associations |
| `crm.schemas.contacts.read` | Read | List existing contact properties |
| `crm.schemas.companies.read` | Read | List existing company properties |
| `crm.schemas.deals.read` | Read | List existing deal properties |
| `crm.schemas.contacts.write` | Write | Create custom contact properties |
| `crm.schemas.companies.write` | Write | Create custom company properties |
| `crm.schemas.deals.write` | Write | Create custom deal properties |
