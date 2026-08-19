"""Profile loading and validation for demo configs."""

import json
import os
import sys

from forge.presets import PRESETS

REQUIRED_KEYS = ["company", "counts", "pipeline"]
REQUIRED_COMPANY_KEYS = ["name", "industry", "size", "icp"]
REQUIRED_COUNTS_KEYS = ["companies", "contacts_per_company", "deals"]

KNOWN_SETS = {"fit", "engagement"}
_LEGACY_KEYS = {"canon", "engagement"}
_NEW_KEYS = {"preset", "sets"}


class ProfileValidationError(Exception):
    pass


def load_profile(path: str) -> dict:
    """Load a JSON (or YAML) profile and validate it."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Profile not found: {path}")

    with open(path) as f:
        if path.endswith((".yaml", ".yml")):
            try:
                import yaml
                profile = yaml.safe_load(f)
            except ImportError:
                raise ImportError(
                    "pyyaml required for YAML profiles. "
                    "Install: pip install 'hubspot-demo-forge[yaml]'"
                )
        else:
            profile = json.load(f)

    profile = _migrate_properties_config(profile)
    _validate(profile)
    return profile


def _migrate_properties_config(profile: dict) -> dict:
    """Normalize properties config to {preset, sets} format.

    Handles legacy boolean format, new format, and absent properties.
    Raises on mixed old/new syntax.
    """
    props = profile.get("properties")

    if props is None:
        profile["properties"] = {"preset": "default", "sets": []}
        return profile

    keys = set(props.keys())
    has_legacy = bool(keys & _LEGACY_KEYS)
    has_new = bool(keys & _NEW_KEYS)

    if has_legacy and has_new:
        raise ProfileValidationError(
            "Profile mixes legacy and current property configuration.\n\n"
            "Use either:\n"
            '  {"canon": true, "engagement": true}\n\n'
            "or:\n"
            '  {"preset": "default", "sets": ["fit", "engagement"]}\n\n'
            "Do not combine both formats."
        )

    if has_legacy:
        # Validate legacy values are actual booleans
        for key in ("canon", "engagement"):
            if key in props and not isinstance(props[key], bool):
                raise ProfileValidationError(
                    f"Legacy property '{key}' must be a boolean, "
                    f"got {type(props[key]).__name__}: {props[key]!r}"
                )

        # Any legacy key implies canon namespace
        sets = []
        if props.get("canon"):
            sets.append("fit")
        if props.get("engagement"):
            sets.append("engagement")

        profile["properties"] = {"preset": "canon", "sets": sets}

        # Deprecation warning
        legacy_repr = {k: v for k, v in props.items() if k in _LEGACY_KEYS}
        new_repr = profile["properties"]
        print(
            f"Deprecated property configuration detected.\n"
            f"  Legacy:  {legacy_repr}\n"
            f"  Using:   {new_repr}\n"
            f"  Update this profile to the new format.\n"
            f"  See docs/profiles.md",
            file=sys.stderr,
        )
    else:
        # Validate new-format types
        if "sets" in props and not isinstance(props["sets"], list):
            raise ProfileValidationError(
                f"'properties.sets' must be a list, got {type(props['sets']).__name__}"
            )
        if "sets" in props:
            for i, s in enumerate(props["sets"]):
                if not isinstance(s, str):
                    raise ProfileValidationError(
                        f"'properties.sets[{i}]' must be a string, got {type(s).__name__}"
                    )
        if "preset" in props and not isinstance(props["preset"], str):
            raise ProfileValidationError(
                f"'properties.preset' must be a string, got {type(props['preset']).__name__}"
            )

        # Apply defaults
        props.setdefault("preset", "default")
        props.setdefault("sets", [])
        profile["properties"] = props

    return profile


def _validate(profile: dict):
    for key in REQUIRED_KEYS:
        if key not in profile:
            raise ProfileValidationError(f"Missing required key: {key}")

    company = profile["company"]
    for key in REQUIRED_COMPANY_KEYS:
        if key not in company:
            raise ProfileValidationError(f"Missing company.{key}")

    counts = profile["counts"]
    for key in REQUIRED_COUNTS_KEYS:
        if key not in counts:
            raise ProfileValidationError(f"Missing counts.{key}")

    # Validate stage weights sum to ~1.0
    stages = profile["pipeline"]["stages"]
    total_weight = sum(s["weight"] for s in stages.values())
    if abs(total_weight - 1.0) > 0.05:
        raise ProfileValidationError(
            f"Stage weights must sum to 1.0 (got {total_weight:.2f})"
        )

    # Validate properties config
    props = profile.get("properties", {})
    preset = props.get("preset", "default")
    if preset not in PRESETS:
        raise ProfileValidationError(f"Unknown preset: '{preset}'")

    for s in props.get("sets", []):
        if s not in KNOWN_SETS:
            raise ProfileValidationError(f"Unknown property set: '{s}'")
