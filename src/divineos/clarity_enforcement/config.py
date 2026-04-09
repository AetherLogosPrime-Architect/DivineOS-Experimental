"""Configuration system for clarity enforcement.

Loads enforcement mode from environment variables, config files, and session metadata.
Supports dynamic configuration reloading and validation.
"""

import json
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger


class ClarityEnforcementMode(Enum):
    """Enforcement mode for clarity violations."""

    BLOCKING = "BLOCKING"  # Prevent unexplained tool calls
    LOGGING = "LOGGING"  # Log violations but allow execution
    PERMISSIVE = "PERMISSIVE"  # Allow all tool calls (default)


@dataclass
class ClarityConfig:
    """Configuration for clarity enforcement."""

    enforcement_mode: ClarityEnforcementMode
    violation_severity_threshold: str  # "low", "medium", "high"
    log_violations: bool
    emit_events: bool

    @staticmethod
    def load() -> "ClarityConfig":
        """Load configuration from environment, config file, or defaults.

        Precedence order:
        1. Environment variable DIVINEOS_CLARITY_MODE
        2. Config file ~/.divineos/clarity_config.json
        3. Default PERMISSIVE mode

        Returns:
            ClarityConfig: Loaded configuration with validated values
        """
        # Check environment variable first
        env_mode = os.environ.get("DIVINEOS_CLARITY_MODE")
        if env_mode:
            logger.debug(f"Loading clarity enforcement mode from env var: {env_mode}")
            return ClarityConfig._from_mode_string(env_mode)

        # Check config file
        config_path = Path.home() / ".divineos" / "clarity_config.json"
        if config_path.exists():
            logger.debug(f"Loading clarity enforcement config from: {config_path}")
            try:
                with open(config_path) as f:
                    config_data = json.load(f)
                return ClarityConfig._from_dict(config_data)
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error reading config file {config_path}: {e}")
                logger.debug("Falling back to default PERMISSIVE mode")

        # Default to PERMISSIVE
        logger.debug("No configuration found, using default PERMISSIVE mode")
        return ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.PERMISSIVE,
            violation_severity_threshold="medium",
            log_violations=True,
            emit_events=True,
        )

    @staticmethod
    def load_from_session_metadata(metadata: Dict[str, Any]) -> Optional["ClarityConfig"]:
        """Load configuration from session metadata.

        Args:
            metadata: Session metadata dictionary

        Returns:
            ClarityConfig if enforcement_mode is in metadata, None otherwise
        """
        if "enforcement_mode" not in metadata:
            return None

        logger.debug("Loading clarity enforcement from session metadata")
        return ClarityConfig._from_dict(metadata)

    @staticmethod
    def _from_mode_string(mode_str: str) -> "ClarityConfig":
        """Create config from enforcement mode string.

        Args:
            mode_str: Enforcement mode string (BLOCKING, LOGGING, PERMISSIVE)

        Returns:
            ClarityConfig with specified mode

        Raises:
            ValueError: If mode_str is not a valid enforcement mode
        """
        mode_str = mode_str.upper()
        try:
            mode = ClarityEnforcementMode[mode_str]
        except KeyError:
            logger.error(f"Invalid enforcement mode: {mode_str}")
            logger.debug("Falling back to default PERMISSIVE mode")
            mode = ClarityEnforcementMode.PERMISSIVE

        return ClarityConfig(
            enforcement_mode=mode,
            violation_severity_threshold="medium",
            log_violations=True,
            emit_events=True,
        )

    @staticmethod
    def _from_dict(data: Dict[str, Any]) -> "ClarityConfig":
        """Create config from dictionary.

        Args:
            data: Configuration dictionary

        Returns:
            ClarityConfig with values from dictionary

        Raises:
            ValueError: If required fields are missing or invalid
        """
        mode_str = data.get("enforcement_mode", "PERMISSIVE").upper()
        try:
            mode = ClarityEnforcementMode[mode_str]
        except KeyError:
            logger.error(f"Invalid enforcement mode in config: {mode_str}")
            mode = ClarityEnforcementMode.PERMISSIVE

        severity = data.get("violation_severity_threshold", "medium").lower()
        if severity not in ("low", "medium", "high"):
            logger.error(f"Invalid severity threshold: {severity}")
            severity = "medium"

        return ClarityConfig(
            enforcement_mode=mode,
            violation_severity_threshold=severity,
            log_violations=data.get("log_violations", True),
            emit_events=data.get("emit_events", True),
        )


def get_clarity_config() -> ClarityConfig:
    """Get the current clarity enforcement configuration.

    Returns:
        ClarityConfig: Current configuration
    """
    return ClarityConfig.load()


def reload_clarity_config() -> ClarityConfig:
    """Reload configuration from environment and config files.

    Returns:
        ClarityConfig: Reloaded configuration
    """
    logger.debug("Reloading clarity enforcement configuration")
    return ClarityConfig.load()
