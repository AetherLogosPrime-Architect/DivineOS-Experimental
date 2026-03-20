"""Tests for configuration validator.

Tests cover:
- Configuration validation
- Error detection and reporting
- Default value application
- Schema generation
- Helpful error messages
"""

from divineos.clarity_enforcement.config_validator import (
    ConfigValidator,
    validate_config,
    get_default_config,
    get_config_schema,
)


class TestConfigValidatorBasics:
    """Test basic configuration validator functionality."""

    def test_validator_initialization(self):
        """Test that validator initializes correctly."""
        validator = ConfigValidator()
        assert validator is not None
        assert len(validator.VALID_OPTIONS) > 0

    def test_get_default_config(self):
        """Test getting default configuration."""
        config = get_default_config()
        assert config is not None
        assert "enforcement_mode" in config
        assert config["enforcement_mode"] == "logging"
        assert config["semantic_analysis_enabled"] is True

    def test_get_config_schema(self):
        """Test getting configuration schema."""
        schema = get_config_schema()
        assert schema is not None
        assert "enforcement_mode" in schema
        assert "type" in schema["enforcement_mode"]
        assert "description" in schema["enforcement_mode"]


class TestConfigValidation:
    """Test configuration validation."""

    def test_valid_config(self):
        """Test validation of valid configuration."""
        config = {
            "enforcement_mode": "blocking",
            "violation_threshold": 0.7,
            "semantic_analysis_enabled": True,
        }
        is_valid, errors, merged = validate_config(config)
        assert is_valid
        assert len(errors) == 0
        assert merged["enforcement_mode"] == "blocking"

    def test_empty_config(self):
        """Test validation of empty configuration."""
        config = {}
        is_valid, errors, merged = validate_config(config)
        assert is_valid
        assert len(errors) == 0
        # Should have defaults
        assert "enforcement_mode" in merged
        assert merged["enforcement_mode"] == "logging"

    def test_unknown_option(self):
        """Test detection of unknown options."""
        config = {"unknown_option": "value"}
        is_valid, errors, merged = validate_config(config)
        assert not is_valid
        assert len(errors) > 0
        assert any("unknown" in error.lower() for error in errors)

    def test_invalid_type(self):
        """Test detection of invalid types."""
        config = {"enforcement_mode": 123}  # Should be string
        is_valid, errors, merged = validate_config(config)
        assert not is_valid
        assert len(errors) > 0

    def test_invalid_enum_value(self):
        """Test detection of invalid enum values."""
        config = {"enforcement_mode": "invalid_mode"}
        is_valid, errors, merged = validate_config(config)
        assert not is_valid
        assert len(errors) > 0

    def test_value_too_low(self):
        """Test detection of values below minimum."""
        config = {"violation_threshold": -0.5}
        is_valid, errors, merged = validate_config(config)
        assert not is_valid
        assert len(errors) > 0

    def test_value_too_high(self):
        """Test detection of values above maximum."""
        config = {"violation_threshold": 1.5}
        is_valid, errors, merged = validate_config(config)
        assert not is_valid
        assert len(errors) > 0

    def test_multiple_errors(self):
        """Test detection of multiple errors."""
        config = {
            "enforcement_mode": "invalid",
            "violation_threshold": 2.0,
            "unknown_option": "value",
        }
        is_valid, errors, merged = validate_config(config)
        assert not is_valid
        assert len(errors) >= 2


class TestDefaultApplication:
    """Test default value application."""

    def test_defaults_applied_for_missing_options(self):
        """Test that defaults are applied for missing options."""
        config = {"enforcement_mode": "blocking"}
        is_valid, errors, merged = validate_config(config)
        assert is_valid
        # Check that defaults are applied
        assert merged["violation_threshold"] == 0.5
        assert merged["semantic_analysis_enabled"] is True

    def test_defaults_applied_for_invalid_options(self):
        """Test that defaults are applied for invalid options."""
        config = {"violation_threshold": 2.0}  # Invalid
        is_valid, errors, merged = validate_config(config)
        # Should use default for invalid option
        assert merged["violation_threshold"] == 0.5

    def test_valid_options_preserved(self):
        """Test that valid options are preserved."""
        config = {
            "enforcement_mode": "blocking",
            "violation_threshold": 0.8,
        }
        is_valid, errors, merged = validate_config(config)
        assert is_valid
        assert merged["enforcement_mode"] == "blocking"
        assert merged["violation_threshold"] == 0.8


class TestHelpfulErrorMessages:
    """Test helpful error message generation."""

    def test_unknown_option_message(self):
        """Test error message for unknown option."""
        validator = ConfigValidator()
        message = validator.get_helpful_error_message("unknown_option", "value")
        assert "unknown" in message.lower()
        assert "valid options" in message.lower()

    def test_invalid_type_message(self):
        """Test error message for invalid type."""
        validator = ConfigValidator()
        message = validator.get_helpful_error_message("enforcement_mode", 123)
        assert "type" in message.lower()
        assert "str" in message.lower()

    def test_invalid_value_message(self):
        """Test error message for invalid value."""
        validator = ConfigValidator()
        message = validator.get_helpful_error_message("enforcement_mode", "invalid")
        assert "invalid" in message.lower()
        assert "valid values" in message.lower()

    def test_value_too_low_message(self):
        """Test error message for value too low."""
        validator = ConfigValidator()
        message = validator.get_helpful_error_message("violation_threshold", -0.5)
        assert "too low" in message.lower() or "minimum" in message.lower()

    def test_value_too_high_message(self):
        """Test error message for value too high."""
        validator = ConfigValidator()
        message = validator.get_helpful_error_message("violation_threshold", 1.5)
        assert "too high" in message.lower() or "maximum" in message.lower()


class TestConfigurationOptions:
    """Test specific configuration options."""

    def test_enforcement_mode_options(self):
        """Test enforcement mode configuration."""
        for mode in ["permissive", "logging", "blocking"]:
            config = {"enforcement_mode": mode}
            is_valid, errors, merged = validate_config(config)
            assert is_valid
            assert merged["enforcement_mode"] == mode

    def test_violation_threshold_range(self):
        """Test violation threshold range."""
        for threshold in [0.0, 0.25, 0.5, 0.75, 1.0]:
            config = {"violation_threshold": threshold}
            is_valid, errors, merged = validate_config(config)
            assert is_valid
            assert merged["violation_threshold"] == threshold

    def test_compression_threshold_range(self):
        """Test compression threshold range."""
        for threshold in [50000, 100000, 150000, 200000]:
            config = {"compression_threshold": threshold}
            is_valid, errors, merged = validate_config(config)
            assert is_valid
            assert merged["compression_threshold"] == threshold

    def test_boolean_options(self):
        """Test boolean configuration options."""
        for value in [True, False]:
            config = {
                "semantic_analysis_enabled": value,
                "learning_cycle_enabled": value,
            }
            is_valid, errors, merged = validate_config(config)
            assert is_valid
            assert merged["semantic_analysis_enabled"] == value
            assert merged["learning_cycle_enabled"] == value


class TestSchemaGeneration:
    """Test configuration schema generation."""

    def test_schema_structure(self):
        """Test that schema has correct structure."""
        schema = get_config_schema()
        for option_name, option_schema in schema.items():
            assert "type" in option_schema
            assert "default" in option_schema
            assert "description" in option_schema

    def test_schema_completeness(self):
        """Test that schema includes all options."""
        schema = get_config_schema()
        validator = ConfigValidator()
        assert len(schema) == len(validator.VALID_OPTIONS)

    def test_schema_types(self):
        """Test that schema types are correct."""
        schema = get_config_schema()
        assert schema["enforcement_mode"]["type"] == "str"
        assert schema["violation_threshold"]["type"] == "float"
        assert schema["compression_threshold"]["type"] == "int"
        assert schema["semantic_analysis_enabled"]["type"] == "bool"


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_partial_config(self):
        """Test validation of partial configuration."""
        config = {"enforcement_mode": "blocking"}
        is_valid, errors, merged = validate_config(config)
        assert is_valid
        # Should have all options with defaults
        assert len(merged) == len(ConfigValidator.VALID_OPTIONS)

    def test_all_options_config(self):
        """Test validation with all options specified."""
        validator = ConfigValidator()
        config = validator.get_default_config()
        is_valid, errors, merged = validate_config(config)
        assert is_valid
        assert len(errors) == 0

    def test_case_sensitivity(self):
        """Test that validation is case-sensitive for enums."""
        config = {"enforcement_mode": "BLOCKING"}  # Wrong case
        is_valid, errors, merged = validate_config(config)
        assert not is_valid

    def test_none_values(self):
        """Test handling of None values."""
        config = {"enforcement_mode": None}
        is_valid, errors, merged = validate_config(config)
        assert not is_valid

    def test_empty_string_values(self):
        """Test handling of empty string values."""
        config = {"enforcement_mode": ""}
        is_valid, errors, merged = validate_config(config)
        assert not is_valid


class TestValidateAndLog:
    """Test validate_and_log method."""

    def test_validate_and_log_valid(self):
        """Test validate_and_log with valid config."""
        validator = ConfigValidator()
        config = {"enforcement_mode": "blocking"}
        result = validator.validate_and_log(config)
        assert result is not None
        assert "enforcement_mode" in result

    def test_validate_and_log_invalid(self):
        """Test validate_and_log with invalid config."""
        validator = ConfigValidator()
        config = {"enforcement_mode": "invalid"}
        result = validator.validate_and_log(config)
        assert result is not None
        # Should use default for invalid option
        assert result["enforcement_mode"] == "logging"
