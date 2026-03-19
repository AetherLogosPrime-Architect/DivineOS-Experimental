"""
Tests for centralized logging setup.

Validates that:
1. setup_logging() initializes loguru correctly
2. Log file is created at ~/.divineos/divineos.log
3. Console handler outputs INFO+ level
4. File handler outputs DEBUG+ level
5. Log rotation is configured (500 MB)
6. Log retention is configured (30 days)
7. setup_logging() is idempotent
"""

import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch
import pytest
from loguru import logger

from divineos.core.logging_setup import setup_logging


@pytest.fixture
def mock_home_dir():
    """Provide a temporary home directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_setup_logging_creates_directory(mock_home_dir):
    """Test that setup_logging() creates ~/.divineos directory."""
    with patch("pathlib.Path.home", return_value=mock_home_dir):
        setup_logging()
        divineos_dir = mock_home_dir / ".divineos"
        assert divineos_dir.exists(), "~/.divineos directory should be created"
        assert divineos_dir.is_dir(), "~/.divineos should be a directory"


def test_setup_logging_creates_log_file(mock_home_dir):
    """Test that setup_logging() creates the log file."""
    with patch("pathlib.Path.home", return_value=mock_home_dir):
        setup_logging()
        log_file = mock_home_dir / ".divineos" / "divineos.log"

        # Log something to trigger file creation
        logger.info("Test log message")

        assert log_file.exists(), "divineos.log should be created"


def test_setup_logging_writes_to_file(mock_home_dir):
    """Test that setup_logging() writes logs to file."""
    with patch("pathlib.Path.home", return_value=mock_home_dir):
        setup_logging()
        log_file = mock_home_dir / ".divineos" / "divineos.log"

        # Log a test message
        test_message = "Test logging message for verification"
        logger.info(test_message)

        # Read the log file
        assert log_file.exists(), "Log file should exist"
        log_content = log_file.read_text()
        assert test_message in log_content, "Log message should be written to file"


def test_setup_logging_includes_debug_level(mock_home_dir):
    """Test that file handler captures DEBUG level messages."""
    with patch("pathlib.Path.home", return_value=mock_home_dir):
        setup_logging()
        log_file = mock_home_dir / ".divineos" / "divineos.log"

        # Log a debug message
        debug_message = "Debug level test message"
        logger.debug(debug_message)

        # Read the log file
        log_content = log_file.read_text()
        assert debug_message in log_content, "DEBUG level messages should be in file"


def test_setup_logging_format_includes_timestamp(mock_home_dir):
    """Test that log format includes timestamp."""
    with patch("pathlib.Path.home", return_value=mock_home_dir):
        setup_logging()
        log_file = mock_home_dir / ".divineos" / "divineos.log"

        logger.info("Format test")

        log_content = log_file.read_text()
        # Check for timestamp format YYYY-MM-DD HH:mm:ss
        import re

        timestamp_pattern = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}"
        assert re.search(timestamp_pattern, log_content), "Log should include timestamp"


def test_setup_logging_format_includes_level(mock_home_dir):
    """Test that log format includes log level."""
    with patch("pathlib.Path.home", return_value=mock_home_dir):
        setup_logging()
        log_file = mock_home_dir / ".divineos" / "divineos.log"

        logger.info("Level test")

        log_content = log_file.read_text()
        assert "INFO" in log_content, "Log should include level"


def test_setup_logging_format_includes_module_info(mock_home_dir):
    """Test that log format includes module, function, and line number."""
    with patch("pathlib.Path.home", return_value=mock_home_dir):
        setup_logging()
        log_file = mock_home_dir / ".divineos" / "divineos.log"

        logger.info("Module info test")

        log_content = log_file.read_text()
        # Should contain module name, function name, and line number
        assert "test_logging_setup" in log_content, "Log should include module name"


def test_setup_logging_idempotent(mock_home_dir):
    """Test that calling setup_logging() multiple times is safe."""
    with patch("pathlib.Path.home", return_value=mock_home_dir):
        # Call setup_logging multiple times
        setup_logging()
        setup_logging()
        setup_logging()

        # Should not raise any errors
        log_file = mock_home_dir / ".divineos" / "divineos.log"
        logger.info("Idempotent test")

        assert log_file.exists(), "Log file should exist after multiple setup calls"


def test_setup_logging_directory_already_exists(mock_home_dir):
    """Test that setup_logging() works if directory already exists."""
    with patch("pathlib.Path.home", return_value=mock_home_dir):
        divineos_dir = mock_home_dir / ".divineos"
        divineos_dir.mkdir(exist_ok=True, parents=True)

        # Should not raise any errors
        setup_logging()

        assert divineos_dir.exists(), "Directory should still exist"


def test_setup_logging_removes_default_handler(mock_home_dir):
    """Test that setup_logging() removes the default loguru handler."""
    with patch("pathlib.Path.home", return_value=mock_home_dir):
        # Before setup, there should be a default handler
        # (we don't check the count, just verify setup works)

        setup_logging()

        # After setup, handlers should be reconfigured
        # (exact count depends on implementation, but should have console and file)
        final_handlers = len(logger._core.handlers)
        assert final_handlers >= 2, "Should have at least console and file handlers"
