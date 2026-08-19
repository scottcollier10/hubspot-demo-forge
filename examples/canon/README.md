# Canon Preset Example

This profile uses the `canon` preset, which creates custom properties with the `canon_*` namespace (e.g., `canon_seniority`, `canon_department`, `canon_persona`).

## Why Canon Exists

The Canon data normalization system standardizes messy CRM data into clean, structured properties. It expects specific `canon_*` property names on contacts and companies, and `engagement_*` properties on deals.

The `canon` preset exists so Demo Forge can seed portals that are pre-configured for Canon normalization workflows. If you're not using Canon, use the `default` preset instead (which creates `forge_*` properties).

## Usage

```bash
# Dry run (no HubSpot changes)
python -m forge seed examples/canon/canon_demo.json --dry-run

# Seed a test portal
python -m forge seed examples/canon/canon_demo.json

# Add engagement simulation
python -m forge engage examples/canon/canon_demo.json
```

## Property Mapping

| Preset | Contact/Company Properties | Deal Properties |
|--------|---------------------------|-----------------|
| `default` | `forge_*` | `forge_*` |
| `canon` | `canon_*` | `engagement_*` |

The `engagement_*` deal naming in the Canon preset is a legacy convention from the original engagement intelligence system.
