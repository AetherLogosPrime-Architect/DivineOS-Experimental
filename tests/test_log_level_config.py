"""Tests for DIVINEOS_LOG_LEVEL env-var configuration of file logging.

Locked invariants:

1. Default level is INFO when env var is unset.
2. Valid levels (DEBUG, INFO, WARNING, etc.) from env var are honored.
3. Invalid env-var values fall back to INFO silently (fail-open).
4. Case is normalized — ``debug`` and ``DEBUG`` both work.
"""

from __future__ import annotations

import importlib
import os


def _reload_ledger_and_get_level() -> str:
    """Re-import the ledger module so its module-level env-var read re-runs,
    then return the _FILE_LOG_LEVEL value it settled on."""
    import divineos.core.ledger as _ledger

    importlib.reload(_ledger)
    return _ledger._FILE_LOG_LEVEL


class TestLogLevelConfig:
    def test_default_is_info(self, monkeypatch):
        monkeypatch.delenv("DIVINEOS_LOG_LEVEL", raising=False)
        level = _reload_ledger_and_get_level()
        assert level == "INFO"

    def test_debug_env_var_honored(self, monkeypatch):
        monkeypatch.setenv("DIVINEOS_LOG_LEVEL", "DEBUG")
        level = _reload_ledger_and_get_level()
        assert level == "DEBUG"

    def test_warning_env_var_honored(self, monkeypatch):
        monkeypatch.setenv("DIVINEOS_LOG_LEVEL", "WARNING")
        level = _reload_ledger_and_get_level()
        assert level == "WARNING"

    def test_lowercase_normalized(self, monkeypatch):
        monkeypatch.setenv("DIVINEOS_LOG_LEVEL", "debug")
        level = _reload_ledger_and_get_level()
        assert level == "DEBUG"

    def test_invalid_falls_back_to_info(self, monkeypatch):
        monkeypatch.setenv("DIVINEOS_LOG_LEVEL", "NOT_A_LEVEL")
        level = _reload_ledger_and_get_level()
        assert level == "INFO"

    def test_empty_string_falls_back_to_info(self, monkeypatch):
        monkeypatch.setenv("DIVINEOS_LOG_LEVEL", "")
        level = _reload_ledger_and_get_level()
        assert level == "INFO"


def teardown_module(_module):
    """Reload ledger cleanly at end of module so other tests see INFO
    regardless of any env vars that leaked."""
    os.environ.pop("DIVINEOS_LOG_LEVEL", None)
    import divineos.core.ledger as _ledger

    importlib.reload(_ledger)
