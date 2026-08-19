"""Tests for credential-free CLI commands."""

import json
import subprocess
import sys
import os
import pytest


def _write_profile(tmp_path, properties_config=None):
    profile = {
        "company": {"name": "T", "industry": "S", "size": "s", "icp": "x"},
        "counts": {"companies": 5, "contacts_per_company": [2, 4], "deals": 10},
        "pipeline": {
            "id": "default",
            "stages": {
                "warm": {"id": "a", "weight": 0.4},
                "at_risk": {"id": "b", "weight": 0.4},
                "dormant": {"id": "c", "weight": 0.2},
            },
            "close_date_offsets": {"warm": 30, "at_risk": -5, "dormant": -45},
            "temp_stage": "appointmentscheduled",
        },
    }
    if properties_config is not None:
        profile["properties"] = properties_config
    path = tmp_path / "test.json"
    path.write_text(json.dumps(profile))
    return str(path)


class TestValidateCommand:
    def test_valid_profile_exits_zero(self, tmp_path):
        path = _write_profile(tmp_path, {"preset": "default", "sets": ["fit"]})
        result = subprocess.run(
            [sys.executable, "-m", "forge", "validate", path],
            capture_output=True, text=True,
        )
        assert result.returncode == 0

    def test_invalid_preset_exits_nonzero(self, tmp_path):
        path = _write_profile(tmp_path, {"preset": "bogus", "sets": ["fit"]})
        result = subprocess.run(
            [sys.executable, "-m", "forge", "validate", path],
            capture_output=True, text=True,
        )
        assert result.returncode != 0
        assert "preset" in result.stderr.lower() or "preset" in result.stdout.lower()

    def test_legacy_format_warns_but_validates(self, tmp_path):
        path = _write_profile(tmp_path, {"canon": True, "engagement": True})
        result = subprocess.run(
            [sys.executable, "-m", "forge", "validate", path],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "deprecated" in result.stderr.lower() or "legacy" in result.stderr.lower()


class TestPreviewCommand:
    def test_preview_shows_counts(self, tmp_path):
        path = _write_profile(tmp_path, {"preset": "default", "sets": ["fit", "engagement"]})
        result = subprocess.run(
            [sys.executable, "-m", "forge", "preview", path],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "companies" in result.stdout.lower()
        assert "contacts" in result.stdout.lower()
        assert "deals" in result.stdout.lower()

    def test_preview_shows_property_schemas(self, tmp_path):
        path = _write_profile(tmp_path, {"preset": "default", "sets": ["fit"]})
        result = subprocess.run(
            [sys.executable, "-m", "forge", "preview", path],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "forge_seniority" in result.stdout

    def test_preview_no_sets_shows_no_properties(self, tmp_path):
        path = _write_profile(tmp_path, {"preset": "default", "sets": []})
        result = subprocess.run(
            [sys.executable, "-m", "forge", "preview", path],
            capture_output=True, text=True,
        )
        assert result.returncode == 0

    def test_preview_requires_no_credentials(self, tmp_path):
        """Preview must work without HUBSPOT_TOKEN or ANTHROPIC_API_KEY."""
        path = _write_profile(tmp_path, {"preset": "default", "sets": ["fit"]})
        env = {k: v for k, v in os.environ.items()
               if k not in ("HUBSPOT_TOKEN", "ANTHROPIC_API_KEY")}
        result = subprocess.run(
            [sys.executable, "-m", "forge", "preview", path],
            capture_output=True, text=True, env=env,
        )
        assert result.returncode == 0
