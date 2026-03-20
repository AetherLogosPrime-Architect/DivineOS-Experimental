"""Configuration validation for clarity enforcement system.

Validates all configuration options and provides helpful error messages.
"""

from typing import Dict, Any, List, Tuple
from enum import Enum
from loguru import logger


class ConfigOption(Enum):
    """Configuration options for clarity enforcement."""

    ENFORCEMENT_MODE = "enforcement_mode"
    VIOLATION_THRESHOLD = "violation_threshold"
    COMPRESSION_THRESHOLD = "compression_threshold"
    WARNING_THRESHOLD = "warning_threshold"
    SEMANTIC_ANALYSIS_ENABLED = "semantic_analysis_enabled"
    CONFIDENCE_THRESHOLD = "confidence_threshold"
    MAX_CONTEXT_LENGTH = "max_context_length"
    LEARNING_CYCLE_ENABLED = "learning_cycle_enabled"


class ConfigValidator:
    """Validates clarity enforcement configuration."""

    # Valid configuration options and their types
    VALID_OPTIONS: Dict[str, Dict[str, Any]] = {
        "enforcement_mode": {
            "type": str,
            "valid_values": ["permissive", "logging", "blocking"],
            "default": "logging",
            "description": (
                "How violations are handled: permissive (allow), "
                "logging (log), or blocking (prevent)"
            ),
        },
        "violation_threshold": {
            "type": float,
            "min": 0.0,
            "max": 1.0,
            "default": 0.5,
            "description": "Confidence threshold for reporting violations (0.0-1.0)",
        },
        "compression_threshold": {
            "type": int,
            "min": 50000,
            "max": 200000,
            "default": 150000,
            "description": "Token count at which compression is triggered",
        },
        "warning_threshold": {
            "type": int,
            "min": 50000,
            "max": 200000,
            "default": 130000,
            "description": "Token count at which warning is issued",
        },
        "semantic_analysis_enabled": {
            "type": bool,
            "default": True,
            "description": "Enable semantic analysis for violation detection",
        },
        "confidence_threshold": {
            "type": float,
            "min": 0.0,
            "max": 1.0,
            "default": 0.6,
            "description": "Confidence threshold for semantic analysis (0.0-1.0)",
        },
        "max_context_length": {
            "type": int,
            "min": 1,
            "max": 100,
            "default": 5,
            "description": "Maximum number of preceding messages to consider",
        },
        "learning_cycle_enabled": {
            "type": bool,
            "default": True,
            "description": "Enable learning cycle at session end",
        },
    }

    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, List[str], Dict[str, Any]]:
        """Validate configuration and return errors and defaults.

        Args:
            config: Configuration dictionary to validate

        Returns:
            Tuple of (is_valid, errors, merged_config)
            - is_valid: True if config is valid
            - errors: List of error messages
            - merged_config: Config with defaults applied
        """
        errors = []
        merged_config = {}

        # Check for unknown options
        for key in config:
            if key not in self.VALID_OPTIONS:
                errors.append(f"Unknown configuration option: {key}")

        # Validate each option
        for option_name, option_spec in self.VALID_OPTIONS.items():
            if option_name in config:
                value = config[option_name]
                option_errors = self._validate_option(option_name, value, option_spec)
                errors.extend(option_errors)

                if not option_errors:
                    merged_config[option_name] = value
                else:
                    # Use default if validation failed
                    merged_config[option_name] = option_spec["default"]
            else:
                # Use default for missing options
                merged_config[option_name] = option_spec["default"]

        is_valid = len(errors) == 0
        return is_valid, errors, merged_config

    @staticmethod
    def _validate_option(
        option_name: str,
        value: Any,
        option_spec: Dict[str, Any],
    ) -> List[str]:
        """Validate a single configuration option.

        Args:
            option_name: Name of the option
            value: Value to validate
            option_spec: Option specification

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        # Check type
        expected_type = option_spec["type"]
        if not isinstance(value, expected_type):
            errors.append(
                f"Invalid type for {option_name}: expected {expected_type.__name__}, "
                f"got {type(value).__name__}"
            )
            return errors

        # Check valid values (for enums)
        if "valid_values" in option_spec:
            if value not in option_spec["valid_values"]:
                errors.append(
                    f"Invalid value for {option_name}: {value}. "
                    f"Valid values: {', '.join(option_spec['valid_values'])}"
                )

        # Check min/max (for numbers)
        if "min" in option_spec:
            if value < option_spec["min"]:
                errors.append(f"Value for {option_name} is too low: {value} < {option_spec['min']}")

        if "max" in option_spec:
            if value > option_spec["max"]:
                errors.append(
                    f"Value for {option_name} is too high: {value} > {option_spec['max']}"
                )

        return errors

    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration.

        Returns:
            Dictionary with default values for all options
        """
        return {
            option_name: option_spec["default"]
            for option_name, option_spec in self.VALID_OPTIONS.items()
        }

    def get_config_schema(self) -> Dict[str, Dict[str, Any]]:
        """Get configuration schema for documentation.

        Returns:
            Dictionary describing all configuration options
        """
        schema = {}
        for option_name, option_spec in self.VALID_OPTIONS.items():
            schema[option_name] = {
                "type": option_spec["type"].__name__,
                "default": option_spec["default"],
                "description": option_spec["description"],
            }

            if "valid_values" in option_spec:
                schema[option_name]["valid_values"] = option_spec["valid_values"]

            if "min" in option_spec:
                schema[option_name]["min"] = option_spec["min"]

            if "max" in option_spec:
                schema[option_name]["max"] = option_spec["max"]

        return schema

    def get_helpful_error_message(self, option_name: str, value: Any) -> str:
        """Get a helpful error message for an invalid option.

        Args:
            option_name: Name of the option
            value: Invalid value

        Returns:
            Helpful error message with suggestions
        """
        if option_name not in self.VALID_OPTIONS:
            return (
                f"Unknown option: {option_name}\n"
                f"Valid options: {', '.join(self.VALID_OPTIONS.keys())}"
            )

        option_spec = self.VALID_OPTIONS[option_name]
        expected_type = option_spec["type"]

        if not isinstance(value, expected_type):
            return (
                f"Invalid type for {option_name}: expected {expected_type.__name__}, "
                f"got {type(value).__name__}\n"
                f"Description: {option_spec['description']}\n"
                f"Default: {option_spec['default']}"
            )

        if "valid_values" in option_spec:
            return (
                f"Invalid value for {option_name}: {value}\n"
                f"Valid values: {', '.join(option_spec['valid_values'])}\n"
                f"Description: {option_spec['description']}"
            )

        if "min" in option_spec and value < option_spec["min"]:
            return (
                f"Value for {option_name} is too low: {value}\n"
                f"Minimum: {option_spec['min']}\n"
                f"Description: {option_spec['description']}"
            )

        if "max" in option_spec and value > option_spec["max"]:
            return (
                f"Value for {option_name} is too high: {value}\n"
                f"Maximum: {option_spec['max']}\n"
                f"Description: {option_spec['description']}"
            )

        return f"Invalid value for {option_name}: {value}"

    def validate_and_log(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration and log results.

        Args:
            config: Configuration to validate

        Returns:
            Validated and merged configuration
        """
        is_valid, errors, merged_config = self.validate_config(config)

        if is_valid:
            logger.info("Configuration validation passed")
        else:
            logger.warning(f"Configuration validation failed with {len(errors)} errors:")
            for error in errors:
                logger.warning(f"  - {error}")

        return merged_config


def validate_config(config: Dict[str, Any]) -> Tuple[bool, List[str], Dict[str, Any]]:
    """Validate configuration.

    Args:
        config: Configuration dictionary

    Returns:
        Tuple of (is_valid, errors, merged_config)
    """
    validator = ConfigValidator()
    return validator.validate_config(config)


def get_default_config() -> Dict[str, Any]:
    """Get default configuration.

    Returns:
        Dictionary with default values
    """
    validator = ConfigValidator()
    return validator.get_default_config()


def get_config_schema() -> Dict[str, Dict[str, Any]]:
    """Get configuration schema.

    Returns:
        Dictionary describing all configuration options
    """
    validator = ConfigValidator()
    return validator.get_config_schema()
