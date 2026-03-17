"""
Event Validation Module

Validates event payloads before they are stored in the ledger.
Prevents corrupted or malformed data from being persisted.
"""

import logging
import re
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)


class EventValidationError(Exception):
    """Raised when event validation fails."""
    pass


class EventValidator:
    """Validates event payloads for data integrity."""
    
    # Valid tool names (alphanumeric, underscores, hyphens)
    VALID_TOOL_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')
    
    # Valid session ID format (UUID)
    VALID_SESSION_ID_PATTERN = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        re.IGNORECASE
    )
    
    # Valid timestamp format (ISO8601)
    VALID_TIMESTAMP_PATTERN = re.compile(
        r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z?$'
    )
    
    @staticmethod
    def is_valid_tool_name(tool_name: str) -> bool:
        """Check if tool name is valid."""
        if not isinstance(tool_name, str):
            return False
        if len(tool_name) == 0 or len(tool_name) > 100:
            return False
        return EventValidator.VALID_TOOL_NAME_PATTERN.match(tool_name) is not None
    
    @staticmethod
    def is_valid_session_id(session_id: str) -> bool:
        """Check if session ID is valid UUID format."""
        if not isinstance(session_id, str):
            return False
        return EventValidator.VALID_SESSION_ID_PATTERN.match(session_id) is not None
    
    @staticmethod
    def is_valid_timestamp(timestamp: str) -> bool:
        """Check if timestamp is valid ISO8601 format."""
        if not isinstance(timestamp, str):
            return False
        return EventValidator.VALID_TIMESTAMP_PATTERN.match(timestamp) is not None
    
    @staticmethod
    def is_valid_content(content: str, max_length: int = 1000000) -> bool:
        """Check if content is valid (readable text, not corrupted)."""
        if not isinstance(content, str):
            return False
        
        if len(content) == 0:
            return False
        
        if len(content) > max_length:
            return False
        
        # Check for excessive control characters (sign of corruption)
        control_char_count = sum(1 for c in content if ord(c) < 32 and c not in '\t\n\r')
        if control_char_count > len(content) * 0.1:  # More than 10% control chars
            return False
        
        # Check for invalid Unicode sequences
        try:
            content.encode('utf-8')
        except UnicodeEncodeError:
            return False
        
        return True
    
    @staticmethod
    def validate_user_input_payload(payload: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate USER_INPUT event payload."""
        required_fields = ['content', 'timestamp', 'session_id']
        
        for field in required_fields:
            if field not in payload:
                return False, f"Missing required field: {field}"
        
        # Validate content
        content = payload.get('content', '')
        if not EventValidator.is_valid_content(content):
            return False, f"Invalid content: {repr(content[:50])}"
        
        # Validate timestamp
        timestamp = payload.get('timestamp', '')
        if not EventValidator.is_valid_timestamp(timestamp):
            return False, f"Invalid timestamp: {timestamp}"
        
        # Validate session ID
        session_id = payload.get('session_id', '')
        if not EventValidator.is_valid_session_id(session_id):
            return False, f"Invalid session ID: {session_id}"
        
        return True, "Valid"
    
    @staticmethod
    def validate_tool_call_payload(payload: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate TOOL_CALL event payload."""
        required_fields = ['tool_name', 'tool_input', 'tool_use_id', 'timestamp', 'session_id']
        
        for field in required_fields:
            if field not in payload:
                return False, f"Missing required field: {field}"
        
        # Validate tool name
        tool_name = payload.get('tool_name', '')
        if not EventValidator.is_valid_tool_name(tool_name):
            return False, f"Invalid tool name: {repr(tool_name)}"
        
        # Validate tool_input is a dict
        tool_input = payload.get('tool_input')
        if not isinstance(tool_input, dict):
            return False, f"tool_input must be a dict, got {type(tool_input)}"
        
        # Validate tool_use_id
        tool_use_id = payload.get('tool_use_id', '')
        if not isinstance(tool_use_id, str) or len(tool_use_id) == 0:
            return False, f"Invalid tool_use_id: {repr(tool_use_id)}"
        
        # Validate timestamp
        timestamp = payload.get('timestamp', '')
        if not EventValidator.is_valid_timestamp(timestamp):
            return False, f"Invalid timestamp: {timestamp}"
        
        # Validate session ID
        session_id = payload.get('session_id', '')
        if not EventValidator.is_valid_session_id(session_id):
            return False, f"Invalid session ID: {session_id}"
        
        return True, "Valid"
    
    @staticmethod
    def validate_tool_result_payload(payload: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate TOOL_RESULT event payload."""
        required_fields = ['tool_name', 'tool_use_id', 'result', 'duration_ms', 'timestamp', 'session_id']
        
        for field in required_fields:
            if field not in payload:
                return False, f"Missing required field: {field}"
        
        # Validate tool name
        tool_name = payload.get('tool_name', '')
        if not EventValidator.is_valid_tool_name(tool_name):
            return False, f"Invalid tool name: {repr(tool_name)}"
        
        # Validate result
        result = payload.get('result', '')
        if not EventValidator.is_valid_content(result):
            return False, f"Invalid result: {repr(result[:50])}"
        
        # Validate duration_ms
        duration_ms = payload.get('duration_ms')
        if not isinstance(duration_ms, (int, float)) or duration_ms < 0:
            return False, f"Invalid duration_ms: {duration_ms}"
        
        # Validate timestamp
        timestamp = payload.get('timestamp', '')
        if not EventValidator.is_valid_timestamp(timestamp):
            return False, f"Invalid timestamp: {timestamp}"
        
        # Validate session ID
        session_id = payload.get('session_id', '')
        if not EventValidator.is_valid_session_id(session_id):
            return False, f"Invalid session ID: {session_id}"
        
        return True, "Valid"
    
    @staticmethod
    def validate_session_end_payload(payload: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate SESSION_END event payload."""
        required_fields = ['session_id', 'message_count', 'tool_call_count', 'tool_result_count', 'duration_seconds', 'timestamp']
        
        for field in required_fields:
            if field not in payload:
                return False, f"Missing required field: {field}"
        
        # Validate session ID
        session_id = payload.get('session_id', '')
        if not EventValidator.is_valid_session_id(session_id):
            return False, f"Invalid session ID: {session_id}"
        
        # Validate counts
        for count_field in ['message_count', 'tool_call_count', 'tool_result_count']:
            count = payload.get(count_field)
            if not isinstance(count, int) or count < 0:
                return False, f"Invalid {count_field}: {count}"
        
        # Validate duration
        duration = payload.get('duration_seconds')
        if not isinstance(duration, (int, float)) or duration < 0:
            return False, f"Invalid duration_seconds: {duration}"
        
        # Validate timestamp
        timestamp = payload.get('timestamp', '')
        if not EventValidator.is_valid_timestamp(timestamp):
            return False, f"Invalid timestamp: {timestamp}"
        
        return True, "Valid"
    
    @staticmethod
    def validate_payload(event_type: str, payload: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate a payload based on event type."""
        if event_type == "USER_INPUT":
            return EventValidator.validate_user_input_payload(payload)
        elif event_type == "TOOL_CALL":
            return EventValidator.validate_tool_call_payload(payload)
        elif event_type == "TOOL_RESULT":
            return EventValidator.validate_tool_result_payload(payload)
        elif event_type == "SESSION_END":
            return EventValidator.validate_session_end_payload(payload)
        else:
            return False, f"Unknown event type: {event_type}"
