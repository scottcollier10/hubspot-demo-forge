# Contributing to HubSpot Demo Forge

## Prerequisites

- Python 3.11+
- git

## Setup

```bash
git clone https://github.com/scottcollier10/hubspot-demo-forge.git
cd hubspot-demo-forge
pip install -e ".[dev]"
python -m pytest tests/ -v
```

All tests run without external credentials. No HubSpot or Anthropic API keys are needed to develop and test.

## What You Can Work On Without Credentials

Most of the codebase is testable locally:

- Profile validation and config migration
- Property definitions (field registry, presets, adapter)
- Derivation logic (fit fields, engagement simulation)
- CLI commands (`validate`, `preview`)
- New profiles and scenarios
- Documentation

## What Requires Credentials

These operations hit external APIs and need environment variables:

- **`forge seed`**: Requires `ANTHROPIC_API_KEY` (data generation) and `HUBSPOT_TOKEN` (HubSpot writes)
- **`forge engage`**: Requires `HUBSPOT_TOKEN`
- **`forge cleanup`**: Requires `HUBSPOT_TOKEN`

Use `--dry-run` to test the generation pipeline without a HubSpot portal.

## Running Tests

```bash
# Full suite
python -m pytest tests/ -v

# Specific test file
python -m pytest tests/test_field_registry.py -v

# Specific test class
python -m pytest tests/test_legacy_contract.py::TestCanonNamespacePreserved -v
```

## Contribution Ideas

### Add a Profile

Create a new JSON file in `profiles/` for a different industry or demo scenario. Validate it works:

```bash
python -m forge validate profiles/your_profile.json
python -m forge preview profiles/your_profile.json
```

### Add a Property Set

Property sets are groups of related fields. To add a new set:

1. Define fields in `forge/field_registry.py`
2. Add name mappings to both presets in `forge/presets.py`
3. Wire serialization in `forge/hubspot_adapter.py`
4. Add tests

### Add a Preset

Presets map logical field names to HubSpot property names. To add a new preset:

1. Add the mapping to `PRESETS` in `forge/presets.py`
2. Run `validate_preset_completeness()` to verify full coverage
3. Add tests

## Pull Request Guidelines

- All tests must pass (`python -m pytest tests/ -v`)
- No credentials or secrets in committed code
- Follow existing code patterns (urllib.request, no heavy deps)
- Update docs if behavior changes
- Include tests for new functionality

## Code Style

- No external dependencies for core functionality
- Stable machine values for enums (lowercase_snake: `"vp"`, `"c_level"`, `"active"`)
- Native Python types in internal APIs, string serialization only at the HubSpot boundary
- Tests should work without any environment variables set
