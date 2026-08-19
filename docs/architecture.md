# Architecture

## Data Flow

```
Profile JSON
  |
  v
Config loader (config.py)          -- validates, migrates legacy format
  |
  v
Derivation (engage.py)             -- inspects CRM data, produces logical values
  |
  v
Logical fields                     -- CRM-name-independent dicts
  |                                   e.g. {"seniority": "vp", "department": "marketing"}
  v
Field Registry (field_registry.py) -- owns every field definition (type, options, object type)
  |
  v
Preset (presets.py)                -- maps logical names to HubSpot property names
  |                                   default: seniority -> forge_seniority
  |                                   canon:   seniority -> canon_seniority
  v
HubSpot Adapter (hubspot_adapter.py)
  |  - build_property_schemas()    -- field defs + preset names -> HubSpot schema dicts
  |  - serialize_for_hubspot()     -- logical values + preset -> typed string values
  v
Client (client.py)                 -- raw urllib.request, auth, rate limiting
  |
  v
HubSpot API
```

## Key Principles

**Logical values are CRM-name-independent.** Derivation produces `{"seniority": "vp"}`, never `{"forge_seniority": "vp"}` or `{"canon_seniority": "vp"}`. Name mapping happens at the preset layer, serialization at the adapter layer.

**The registry owns field definitions.** Every field's type, label, description, allowed options, and object type are defined once in `field_registry.py`. The registry is the single source of truth for what fields exist.

**Presets own HubSpot property naming.** A preset is a complete mapping from every logical field name to a HubSpot property name. The `default` preset uses `forge_*` names. The `canon` preset uses `canon_*` for contacts/companies and `engagement_*` for deals.

**The adapter owns serialization.** Type-driven conversion happens in one place. Numbers become strings. Dates become ISO format. Enums are validated against registry options. Date fields reject datetime objects.

**`forge_source` is infrastructure metadata.** It tracks which records Demo Forge created, enabling cleanup. It lives outside the registry/preset system in `properties.py`.

## Where to Make Changes

| I want to... | Change this |
|---|---|
| Add a new field | `field_registry.py` (definition) + `presets.py` (name in each preset) |
| Add a new preset | `presets.py` (complete name mapping for all registry fields) |
| Change how a type serializes | `hubspot_adapter.py` (`_serialize_value`) |
| Change how a field is derived | `engage.py` (`derive_fit_fields` or `generate_engagement_values`) |
| Add a new property set | `field_registry.py` (fields with new set name) + `presets.py` (names) |
| Support a new config format | `config.py` (`_migrate_properties_config`) |
| Add a CLI command | `cli.py` (`build_parser` + handler function) |

## Presets

| Preset | Contact/Company | Deal | Use case |
|--------|----------------|------|----------|
| `default` | `forge_*` | `forge_*` | General use, public namespace |
| `canon` | `canon_*` | `engagement_*` | Compatibility with Canon data normalization |

The `engagement_*` deal naming in the canon preset is a legacy convention. New presets should use a consistent prefix.

## Testing Without Credentials

The three-layer architecture means most code is testable without HubSpot or Anthropic API keys. The registry, presets, adapter, derivation, config migration, and CLI validation/preview commands all run locally. Only `forge seed`, `forge engage`, and `forge cleanup` require live credentials.
