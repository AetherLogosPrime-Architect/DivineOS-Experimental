"""Telemetry: failing detectors are recorded, not silently swallowed.

Closes audit finding find-f128475b5b65 (silent-failure pattern at the
detector-wrapper layer). Before this telemetry: a detector raising
inside _run_detector returned [] — indistinguishable from a clean run.
After: the failure logs a warning AND appends to _LAST_RUN_ERRORS,
which run_audit clears on each invocation.
"""

from __future__ import annotations

import logging

from divineos.core import operating_loop_audit as opla


def test_run_detector_records_exception_into_last_run_errors():
    opla._LAST_RUN_ERRORS.clear()

    def busted_detector(_text: str) -> list:
        raise RuntimeError("boom")

    result = opla._run_detector("busted", busted_detector, "input text")

    assert result == []
    assert len(opla._LAST_RUN_ERRORS) == 1
    err = opla._LAST_RUN_ERRORS[0]
    assert err["name"] == "busted"
    assert err["exc_type"] == "RuntimeError"
    assert "boom" in err["exc_msg"]


def test_run_detector_clean_path_does_not_record_error():
    opla._LAST_RUN_ERRORS.clear()

    def clean_detector(_text: str) -> list:
        return []

    result = opla._run_detector("clean", clean_detector, "input")

    assert result == []
    assert opla._LAST_RUN_ERRORS == []


def test_run_detector_logs_warning_on_exception(caplog):
    opla._LAST_RUN_ERRORS.clear()

    def busted(_text: str) -> list:
        raise ValueError("kaboom")

    with caplog.at_level(logging.WARNING, logger="divineos.core.operating_loop_audit"):
        opla._run_detector("noisy", busted, "x")

    assert any("noisy" in r.message and "kaboom" in r.message for r in caplog.records)


def test_public_accessor_returns_copy():
    """last_run_detector_errors() returns a copy — callers can't mutate state."""
    opla._LAST_RUN_ERRORS.clear()
    opla._LAST_RUN_ERRORS.append({"name": "x", "exc_type": "E", "exc_msg": "m"})

    snapshot = opla.last_run_detector_errors()
    snapshot.append({"name": "injected", "exc_type": "X", "exc_msg": "y"})

    assert len(opla._LAST_RUN_ERRORS) == 1
    assert opla._LAST_RUN_ERRORS[0]["name"] == "x"


def test_exc_msg_truncated():
    """Long exception messages get bounded to 200 chars."""
    opla._LAST_RUN_ERRORS.clear()
    long_msg = "x" * 5000

    def busted(_text: str) -> list:
        raise RuntimeError(long_msg)

    opla._run_detector("big", busted, "x")
    assert len(opla._LAST_RUN_ERRORS[0]["exc_msg"]) <= 200
