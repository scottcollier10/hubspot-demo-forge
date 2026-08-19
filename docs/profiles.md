# Profile Reference

Profiles are JSON files that define what Demo Forge creates in your HubSpot portal. Every command that touches HubSpot data takes a profile as its first argument.

## Required Keys

### `company`

Describes the demo company. Used by the AI generator to produce contextually appropriate data.

```json
{
  "company": {
    "name": "Northstar SaaS",
    "industry": "B2B SaaS",
    "size": "mid-market",
    "icp": "Revenue leaders scaling from SMB to enterprise"
  }
}
```

| Field | Description |
|-------|-------------|
| `name` | Company name used as context for AI generation |
| `industry` | Industry vertical |
| `size` | Company size category (e.g., "startup", "mid-market", "enterprise") |
| `icp` | Ideal customer profile description |

### `counts`

Controls how many objects are created.

```json
{
  "counts": {
    "companies": 20,
    "contacts_per_company": [3, 10],
    "deals": 40,
    "tickets": 25,
    "products": 8,
    "activities_per_contact": [3, 8]
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `companies` | int | Number of companies to create |
| `contacts_per_company` | [min, max] | Range of contacts per company |
| `deals` | int | Number of deals to create |
| `tickets` | int | Number of support tickets (optional) |
| `products` | int | Number of products (optional) |
| `activities_per_contact` | [min, max] | Range of activities per contact (optional) |

### `pipeline`

Defines deal pipeline configuration and stage distribution.

```json
{
  "pipeline": {
    "id": "default",
    "stages": {
      "warm": { "id": "qualifiedtobuy", "weight": 0.4 },
      "at_risk": { "id": "contractsent", "weight": 0.4 },
      "dormant": { "id": "presentationscheduled", "weight": 0.2 }
    },
    "close_date_offsets": { "warm": 30, "at_risk": -5, "dormant": -45 },
    "temp_stage": "appointmentscheduled"
  }
}
```

| Field | Description |
|-------|-------------|
| `id` | HubSpot pipeline ID |
| `stages` | Map of category to stage ID and distribution weight |
| `close_date_offsets` | Days from today for close dates (positive = future, negative = past) |
| `temp_stage` | Temporary stage used during stage-flip trick for time-in-stage reset |

Stage weights should sum to 1.0. Deals are distributed across stages according to these weights.

## Optional Keys

### `properties`

Controls which custom properties are created and their naming convention.

```json
{
  "properties": {
    "preset": "default",
    "sets": ["fit", "engagement"]
  }
}
```

| Field | Default | Description |
|-------|---------|-------------|
| `preset` | `"default"` | Naming convention for properties |
| `sets` | `[]` | Which property sets to enable |

**Available presets:**

| Preset | Contact/Company Names | Deal Names |
|--------|----------------------|------------|
| `default` | `forge_*` | `forge_*` |
| `canon` | `canon_*` | `engagement_*` |

**Available sets:**

| Set | Creates | Description |
|-----|---------|-------------|
| `fit` | Contact + company properties | Seniority, department, persona, email type, lead source, data confidence, industry |
| `engagement` | Contact + deal properties | Email opens, clicks, engagement score/status, last open/click dates, deal health |

If `properties` is omitted, no custom properties are created.

**Legacy format:** The older `{"canon": true, "engagement": true}` syntax is still accepted but deprecated. It maps to `{"preset": "canon", "sets": [...]}` automatically with a warning.

### `tickets`

```json
{
  "tickets": {
    "pipeline": "0",
    "statuses": { "open": 0.4, "waiting": 0.3, "closed": 0.3 }
  }
}
```

### `products`

```json
{
  "products": {
    "price_range": [5000, 75000],
    "line_items_per_deal": [1, 3]
  }
}
```

### `activities`

```json
{
  "activities": {
    "types": ["call", "email", "meeting", "note"],
    "recency_days": 90
  }
}
```

## Example Profiles

### Minimal (companies, contacts, deals only)

```json
{
  "company": {
    "name": "Acme Corp",
    "industry": "Manufacturing",
    "size": "mid-market",
    "icp": "Operations managers at mid-market manufacturers"
  },
  "counts": {
    "companies": 10,
    "contacts_per_company": [2, 5],
    "deals": 15
  },
  "pipeline": {
    "id": "default",
    "stages": {
      "warm": { "id": "qualifiedtobuy", "weight": 0.4 },
      "at_risk": { "id": "contractsent", "weight": 0.4 },
      "dormant": { "id": "presentationscheduled", "weight": 0.2 }
    },
    "close_date_offsets": { "warm": 30, "at_risk": -5, "dormant": -45 },
    "temp_stage": "appointmentscheduled"
  }
}
```

### Full portal with properties

See `profiles/full_portal.json` for a complete example including tickets, products, activities, and property configuration.

## Creating Custom Profiles

1. Copy an existing profile from `profiles/`
2. Update `company` fields for your demo scenario
3. Adjust `counts` to your desired data volume
4. Set `pipeline.stages` to match your HubSpot pipeline stage IDs
5. Choose a `properties.preset` and enable the `sets` you need
6. Validate with `python -m forge validate your_profile.json`
7. Preview with `python -m forge preview your_profile.json`
