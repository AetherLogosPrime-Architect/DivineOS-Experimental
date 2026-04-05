"""Hook Validator — Validates hook configuration files for Real IDE Integration.

Validates JSON structure, required fields, event types, and action types.
Provides clear error messages for invalid hooks.

Requirements:
- Requirement 13.1: Validate JSON structure
- Requirement 13.2: Verify required fields (name, version, when, then)
- Requirement 13.3: Verify event types (promptSubmit, postToolUse, agentStop)
- Requirement 13.4: Verify action types (askAgent, runCommand)
- Requirement 13.5: Log errors and skip invalid hooks
- Requirement 13.6: Provide clear error messages
"""

import json
from pathlib import Path
from typing import Any
import sqlite3

from loguru import logger

_HV_ERRORS = (
    ImportError,
    sqlite3.OperationalError,
    OSError,
    KeyError,
    TypeError,
    ValueError,
    json.JSONDecodeError,
)

# Valid event types that hooks can listen for
VALID_EVENT_TYPES = {
    "promptSubmit",
    "postToolUse",
    "agentStop",
    "fileEdited",
    "fileCreated",
    "fileDeleted",
    "userTriggered",
    "preToolUse",
    "preTaskExecution",
    "postTaskExecution",
}

# Valid action types that hooks can perform
VALID_ACTION_TYPES = {
    "askAgent",
    "runCommand",
}


class HookValidationError(Exception):
    """Raised when hook validation fails."""


def validate_hook_structure(hook_data: dict[str, Any]) -> tuple[bool, str]:
    """Validate the structure of a hook configuration.

    Args:
        hook_data: The parsed hook JSON data

    Returns:
        tuple: (is_valid, error_message) where is_valid is True if valid

    Requirements:
        - Requirement 13.1: Validate JSON structure
        - Requirement 13.2: Verify required fields
        - Requirement 13.3: Verify event types
        - Requirement 13.4: Verify action types

    """
    # Check required top-level fields
    required_fields = {"name", "version", "when", "then"}
    missing_fields = required_fields - set(hook_data.keys())
    if missing_fields:
        return False, f"Missing required fields: {', '.join(sorted(missing_fields))}"

    # Validate name
    if not isinstance(hook_data.get("name"), str):
        return False, "Field 'name' must be a string"
    if not hook_data["name"].strip():
        return False, "Field 'name' cannot be empty"

    # Validate version
    if not isinstance(hook_data.get("version"), str):
        return False, "Field 'version' must be a string"
    if not hook_data["version"].strip():
        return False, "Field 'version' cannot be empty"

    # Validate 'when' section
    when_section = hook_data.get("when")
    if not isinstance(when_section, dict):
        return False, "Field 'when' must be an object"

    if "type" not in when_section:
        return False, "Field 'when.type' is required"

    event_type = when_section.get("type")
    if event_type not in VALID_EVENT_TYPES:
        valid_types = ", ".join(sorted(VALID_EVENT_TYPES))
        return False, f"Invalid event type '{event_type}'. Valid types: {valid_types}"

    # Validate 'then' section
    then_section = hook_data.get("then")
    if not isinstance(then_section, dict):
        return False, "Field 'then' must be an object"

    if "type" not in then_section:
        return False, "Field 'then.type' is required"

    action_type = then_section.get("type")
    if action_type not in VALID_ACTION_TYPES:
        valid_actions = ", ".join(sorted(VALID_ACTION_TYPES))
        return False, f"Invalid action type '{action_type}'. Valid types: {valid_actions}"

    # Validate action-specific requirements
    if action_type == "askAgent":
        if "prompt" not in then_section:
            return False, "Field 'then.prompt' is required for askAgent actions"
        if not isinstance(then_section["prompt"], str):
            return False, "Field 'then.prompt' must be a string"
        if not then_section["prompt"].strip():
            return False, "Field 'then.prompt' cannot be empty"

    elif action_type == "runCommand":
        if "command" not in then_section:
            return False, "Field 'then.command' is required for runCommand actions"
        if not isinstance(then_section["command"], str):
            return False, "Field 'then.command' must be a string"
        if not then_section["command"].strip():
            return False, "Field 'then.command' cannot be empty"

    return True, ""


def validate_hook_file(file_path: Path) -> tuple[bool, str, dict[str, Any] | None]:
    """Validate a hook configuration file.

    Args:
        file_path: Path to the hook file

    Returns:
        tuple: (is_valid, error_message, hook_data)

    Requirements:
        - Requirement 13.1: Validate JSON structure
        - Requirement 13.2: Verify required fields
        - Requirement 13.3: Verify event types
        - Requirement 13.4: Verify action types
        - Requirement 13.6: Provide clear error messages

    """
    try:
        # Check file exists
        if not file_path.exists():
            return False, f"Hook file not found: {file_path}", None

        # Read file
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        # Parse JSON
        try:
            hook_data = json.loads(content)
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON in hook file: {e}", None

        # Validate structure
        is_valid, error_msg = validate_hook_structure(hook_data)
        if not is_valid:
            return False, error_msg, None

        return True, "", hook_data

    except _HV_ERRORS as e:
        return False, f"Error reading hook file: {e}", None


def load_hooks_from_directory(directory: Path) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """Load and validate all hook files from a directory.

    Args:
        directory: Path to directory containing hook files

    Returns:
        tuple: (valid_hooks, invalid_hooks)
        where invalid_hooks is a list of dicts with 'file' and 'error' keys

    Requirements:
        - Requirement 13.5: Log errors and skip invalid hooks
        - Requirement 13.6: Provide clear error messages

    """
    valid_hooks: list[dict[str, Any]] = []
    invalid_hooks: list[dict[str, str]] = []

    if not directory.exists():
        logger.warning(f"Hook directory does not exist: {directory}")
        return valid_hooks, invalid_hooks

    # Find all .divineos.hook files
    hook_files = list(directory.glob("*.divineos.hook"))

    if not hook_files:
        logger.debug(f"No hook files found in {directory}")
        return valid_hooks, invalid_hooks

    for hook_file in hook_files:
        is_valid, error_msg, hook_data = validate_hook_file(hook_file)

        if is_valid:
            logger.debug(f"Loaded valid hook: {hook_file.name}")
            valid_hooks.append(hook_data)  # type: ignore[arg-type]
        else:
            logger.error(f"Invalid hook file {hook_file.name}: {error_msg}")
            invalid_hooks.append(
                {
                    "file": hook_file.name,
                    "error": error_msg,
                },
            )

    return valid_hooks, invalid_hooks
