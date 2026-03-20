"""Tests for clarity enforcement configuration system."""

import os
import json
import tempfile
from pathlib import Path

from divineos.clarity_enforcement.config import (
    ClarityConfig,
    ClarityEnforcementMode,
    get_clarity_config,
    reload_clarity_config,
)


class TestClarityEnforcementMode:
    """Tests for ClarityEnforcementMode enum."""

    def test_enforcement_modes_exist(self):
        """Test that all enforcement modes are defined."""
        assert ClarityEnforcementMode.BLOCKING.value == "BLOCKING"
        assert ClarityEnforcementMode.LOGGING.value == "LOGGING"
        assert ClarityEnforcementMode.PERMISSIVE.value == "PERMISSIVE"

    def test_enforcement_mode_comparison(self):
        """Test enforcement mode comparison."""
        assert ClarityEnforcementMode.BLOCKING == ClarityEnforcementMode.BLOCKING
        assert ClarityEnforcementMode.BLOCKING != ClarityEnforcementMode.LOGGING


class TestClarityConfigDataModel:
    """Tests for ClarityConfig dataclass."""

    def test_config_creation(self):
        """Test creating a ClarityConfig instance."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.LOGGING,
            violation_severity_threshold="medium",
            log_violations=True,
            emit_events=True,
        )

        assert config.enforcement_mode == ClarityEnforcementMode.LOGGING
        assert config.violation_severity_threshold == "medium"
        assert config.log_violations is True
        assert config.emit_events is True

    def test_config_defaults(self):
        """Test ClarityConfig with default values."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.PERMISSIVE,
            violation_severity_threshold="low",
            log_violations=False,
            emit_events=False,
        )

        assert config.enforcement_mode == ClarityEnforcementMode.PERMISSIVE
        assert config.violation_severity_threshold == "low"
        assert config.log_violations is False
        assert config.emit_events is False


class TestClarityConfigLoading:
    """Tests for ClarityConfig loading from various sources."""

    def test_load_default_permissive(self):
        """Test loading default PERMISSIVE mode when no config exists."""
        # Clear environment variable
        os.environ.pop("DIVINEOS_CLARITY_MODE", None)

        config = ClarityConfig.load()

        assert config.enforcement_mode == ClarityEnforcementMode.PERMISSIVE
        assert config.violation_severity_threshold == "medium"
        assert config.log_violations is True
        assert config.emit_events is True

    def test_load_from_env_var_blocking(self):
        """Test loading BLOCKING mode from environment variable."""
        os.environ["DIVINEOS_CLARITY_MODE"] = "BLOCKING"

        config = ClarityConfig.load()

        assert config.enforcement_mode == ClarityEnforcementMode.BLOCKING

        # Cleanup
        os.environ.pop("DIVINEOS_CLARITY_MODE", None)

    def test_load_from_env_var_logging(self):
        """Test loading LOGGING mode from environment variable."""
        os.environ["DIVINEOS_CLARITY_MODE"] = "LOGGING"

        config = ClarityConfig.load()

        assert config.enforcement_mode == ClarityEnforcementMode.LOGGING

        # Cleanup
        os.environ.pop("DIVINEOS_CLARITY_MODE", None)

    def test_load_from_env_var_permissive(self):
        """Test loading PERMISSIVE mode from environment variable."""
        os.environ["DIVINEOS_CLARITY_MODE"] = "PERMISSIVE"

        config = ClarityConfig.load()

        assert config.enforcement_mode == ClarityEnforcementMode.PERMISSIVE

        # Cleanup
        os.environ.pop("DIVINEOS_CLARITY_MODE", None)

    def test_load_from_env_var_case_insensitive(self):
        """Test that environment variable loading is case-insensitive."""
        os.environ["DIVINEOS_CLARITY_MODE"] = "blocking"

        config = ClarityConfig.load()

        assert config.enforcement_mode == ClarityEnforcementMode.BLOCKING

        # Cleanup
        os.environ.pop("DIVINEOS_CLARITY_MODE", None)

    def test_load_from_env_var_invalid(self):
        """Test loading invalid mode from environment variable falls back to PERMISSIVE."""
        os.environ["DIVINEOS_CLARITY_MODE"] = "INVALID_MODE"

        config = ClarityConfig.load()

        assert config.enforcement_mode == ClarityEnforcementMode.PERMISSIVE

        # Cleanup
        os.environ.pop("DIVINEOS_CLARITY_MODE", None)

    def test_load_from_config_file(self):
        """Test loading configuration from config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".divineos"
            config_dir.mkdir()
            config_file = config_dir / "clarity_config.json"

            config_data = {
                "enforcement_mode": "BLOCKING",
                "violation_severity_threshold": "high",
                "log_violations": False,
                "emit_events": True,
            }

            with open(config_file, "w") as f:
                json.dump(config_data, f)

            # Mock home directory
            original_home = Path.home

            def mock_home():
                return Path(tmpdir)

            Path.home = mock_home

            try:
                config = ClarityConfig.load()

                assert config.enforcement_mode == ClarityEnforcementMode.BLOCKING
                assert config.violation_severity_threshold == "high"
                assert config.log_violations is False
                assert config.emit_events is True
            finally:
                Path.home = original_home

    def test_load_from_config_file_invalid_json(self):
        """Test loading invalid JSON from config file falls back to PERMISSIVE."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".divineos"
            config_dir.mkdir()
            config_file = config_dir / "clarity_config.json"

            # Write invalid JSON
            with open(config_file, "w") as f:
                f.write("{ invalid json }")

            # Mock home directory
            original_home = Path.home

            def mock_home():
                return Path(tmpdir)

            Path.home = mock_home

            try:
                config = ClarityConfig.load()

                assert config.enforcement_mode == ClarityEnforcementMode.PERMISSIVE
            finally:
                Path.home = original_home

    def test_env_var_precedence_over_config_file(self):
        """Test that environment variable takes precedence over config file."""
        os.environ["DIVINEOS_CLARITY_MODE"] = "BLOCKING"

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".divineos"
            config_dir.mkdir()
            config_file = config_dir / "clarity_config.json"

            config_data = {
                "enforcement_mode": "LOGGING",
            }

            with open(config_file, "w") as f:
                json.dump(config_data, f)

            # Mock home directory
            original_home = Path.home

            def mock_home():
                return Path(tmpdir)

            Path.home = mock_home

            try:
                config = ClarityConfig.load()

                # Environment variable should take precedence
                assert config.enforcement_mode == ClarityEnforcementMode.BLOCKING
            finally:
                Path.home = original_home
                os.environ.pop("DIVINEOS_CLARITY_MODE", None)


class TestClarityConfigFromDict:
    """Tests for ClarityConfig._from_dict method."""

    def test_from_dict_all_fields(self):
        """Test creating config from dictionary with all fields."""
        data = {
            "enforcement_mode": "BLOCKING",
            "violation_severity_threshold": "high",
            "log_violations": False,
            "emit_events": True,
        }

        config = ClarityConfig._from_dict(data)

        assert config.enforcement_mode == ClarityEnforcementMode.BLOCKING
        assert config.violation_severity_threshold == "high"
        assert config.log_violations is False
        assert config.emit_events is True

    def test_from_dict_partial_fields(self):
        """Test creating config from dictionary with partial fields."""
        data = {
            "enforcement_mode": "LOGGING",
        }

        config = ClarityConfig._from_dict(data)

        assert config.enforcement_mode == ClarityEnforcementMode.LOGGING
        assert config.violation_severity_threshold == "medium"  # Default
        assert config.log_violations is True  # Default
        assert config.emit_events is True  # Default

    def test_from_dict_invalid_mode(self):
        """Test creating config from dictionary with invalid mode."""
        data = {
            "enforcement_mode": "INVALID",
        }

        config = ClarityConfig._from_dict(data)

        assert config.enforcement_mode == ClarityEnforcementMode.PERMISSIVE

    def test_from_dict_invalid_severity(self):
        """Test creating config from dictionary with invalid severity."""
        data = {
            "enforcement_mode": "BLOCKING",
            "violation_severity_threshold": "invalid",
        }

        config = ClarityConfig._from_dict(data)

        assert config.violation_severity_threshold == "medium"  # Default


class TestClarityConfigSessionMetadata:
    """Tests for loading config from session metadata."""

    def test_load_from_session_metadata_blocking(self):
        """Test loading BLOCKING mode from session metadata."""
        metadata = {
            "enforcement_mode": "BLOCKING",
            "violation_severity_threshold": "high",
        }

        config = ClarityConfig.load_from_session_metadata(metadata)

        assert config is not None
        assert config.enforcement_mode == ClarityEnforcementMode.BLOCKING
        assert config.violation_severity_threshold == "high"

    def test_load_from_session_metadata_missing(self):
        """Test loading from session metadata without enforcement_mode."""
        metadata = {
            "some_other_field": "value",
        }

        config = ClarityConfig.load_from_session_metadata(metadata)

        assert config is None

    def test_load_from_session_metadata_empty(self):
        """Test loading from empty session metadata."""
        metadata = {}

        config = ClarityConfig.load_from_session_metadata(metadata)

        assert config is None


class TestClarityConfigHelperFunctions:
    """Tests for helper functions."""

    def test_get_clarity_config(self):
        """Test get_clarity_config helper function."""
        os.environ.pop("DIVINEOS_CLARITY_MODE", None)

        config = get_clarity_config()

        assert isinstance(config, ClarityConfig)
        assert config.enforcement_mode == ClarityEnforcementMode.PERMISSIVE

    def test_reload_clarity_config(self):
        """Test reload_clarity_config helper function."""
        os.environ["DIVINEOS_CLARITY_MODE"] = "BLOCKING"

        config = reload_clarity_config()

        assert config.enforcement_mode == ClarityEnforcementMode.BLOCKING

        # Cleanup
        os.environ.pop("DIVINEOS_CLARITY_MODE", None)


class TestClarityConfigValidation:
    """Tests for configuration validation."""

    def test_severity_threshold_validation_low(self):
        """Test that 'low' is valid severity threshold."""
        data = {
            "enforcement_mode": "LOGGING",
            "violation_severity_threshold": "low",
        }

        config = ClarityConfig._from_dict(data)

        assert config.violation_severity_threshold == "low"

    def test_severity_threshold_validation_medium(self):
        """Test that 'medium' is valid severity threshold."""
        data = {
            "enforcement_mode": "LOGGING",
            "violation_severity_threshold": "medium",
        }

        config = ClarityConfig._from_dict(data)

        assert config.violation_severity_threshold == "medium"

    def test_severity_threshold_validation_high(self):
        """Test that 'high' is valid severity threshold."""
        data = {
            "enforcement_mode": "LOGGING",
            "violation_severity_threshold": "high",
        }

        config = ClarityConfig._from_dict(data)

        assert config.violation_severity_threshold == "high"

    def test_boolean_fields_validation(self):
        """Test that boolean fields are properly validated."""
        data = {
            "enforcement_mode": "LOGGING",
            "log_violations": True,
            "emit_events": False,
        }

        config = ClarityConfig._from_dict(data)

        assert config.log_violations is True
        assert config.emit_events is False
