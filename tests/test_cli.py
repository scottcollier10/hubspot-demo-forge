import re
import sys
from unittest.mock import patch, MagicMock
from forge.cli import build_parser, generate_session_id


class TestCLI:
    def test_seed_requires_profile(self):
        parser = build_parser()
        try:
            parser.parse_args(["seed"])
            assert False, "Should require profile arg"
        except SystemExit:
            pass

    def test_seed_accepts_profile(self):
        parser = build_parser()
        args = parser.parse_args(["seed", "profiles/test.json"])
        assert args.command == "seed"
        assert args.profile == "profiles/test.json"

    def test_seed_dry_run_flag(self):
        parser = build_parser()
        args = parser.parse_args(["seed", "--dry-run", "profiles/test.json"])
        assert args.dry_run is True

    def test_seed_skip_flags(self):
        parser = build_parser()
        args = parser.parse_args([
            "seed", "--skip-properties", "--skip-generation",
            "profiles/test.json",
        ])
        assert args.skip_properties is True
        assert args.skip_generation is True

    def test_seed_summary_shows_all_object_types(self):
        parser = build_parser()
        args = parser.parse_args(["seed", "--dry-run", "profiles/full_portal.json"])
        assert args.dry_run is True
        assert args.profile == "profiles/full_portal.json"

    def test_refresh_deals_command(self):
        parser = build_parser()
        args = parser.parse_args(["refresh-deals"])
        assert args.command == "refresh-deals"

    def test_refresh_deals_all_flag(self):
        parser = build_parser()
        args = parser.parse_args(["refresh-deals", "--all"])
        assert args.all is True

    def test_refresh_deals_defaults_no_all(self):
        parser = build_parser()
        args = parser.parse_args(["refresh-deals"])
        assert args.all is False

    def test_engage_all_flag(self):
        parser = build_parser()
        args = parser.parse_args(["engage", "profiles/test.json", "--all"])
        assert args.all is True

    def test_engage_defaults_no_all(self):
        parser = build_parser()
        args = parser.parse_args(["engage", "profiles/test.json"])
        assert args.all is False


class TestCLICleanup:
    def test_cleanup_subcommand_parses(self):
        parser = build_parser()
        args = parser.parse_args(["cleanup"])
        assert args.command == "cleanup"

    def test_cleanup_dry_run(self):
        parser = build_parser()
        args = parser.parse_args(["cleanup", "--dry-run"])
        assert args.dry_run is True

    def test_cleanup_session_filter(self):
        parser = build_parser()
        args = parser.parse_args(["cleanup", "--session", "forge-20260601-abc123"])
        assert args.session == "forge-20260601-abc123"

    def test_cleanup_confirm_flag(self):
        parser = build_parser()
        args = parser.parse_args(["cleanup", "--confirm"])
        assert args.confirm is True


class TestCLISessions:
    def test_sessions_subcommand_parses(self):
        parser = build_parser()
        args = parser.parse_args(["sessions"])
        assert args.command == "sessions"


class TestSessionId:
    def test_format(self):
        sid = generate_session_id()
        assert re.match(r"^forge-\d{8}-[a-f0-9]{6}$", sid)

    def test_unique(self):
        ids = {generate_session_id() for _ in range(10)}
        assert len(ids) == 10
