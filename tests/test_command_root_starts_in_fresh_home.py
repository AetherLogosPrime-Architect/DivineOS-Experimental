"""The real command root must start in a blank home without raising.

The test conftest hides startup behaviour (pytest is in sys.modules, so the
input-capture step is skipped), so this starts the real root in a subprocess.
Started from inside another program, sys.argv carries no arguments, which
used to hand an empty string to the input-capture step and raise.
"""

import os
import subprocess
import sys

from divineos.core.enforcement import capture_user_input


def _run_root_in_blank_home(tmp_path) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if not k.startswith("PYTEST")}
    env["DIVINEOS_HOME"] = str(tmp_path)
    env["DIVINEOS_DB"] = str(tmp_path / "ledger.db")
    code = "from divineos.cli import cli\ncli(['verify'], standalone_mode=False)\n"
    return subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_command_root_starts_in_fresh_home_without_argv(tmp_path):
    result = _run_root_in_blank_home(tmp_path)
    assert result.returncode == 0, result.stderr[-1500:]
    assert "EventValidationError" not in result.stderr


def test_empty_first_input_is_skipped_not_an_error(monkeypatch):
    emitted: list[str] = []
    monkeypatch.setattr(
        "divineos.core.enforcement.emit_user_input", lambda content: emitted.append(content)
    )
    assert capture_user_input([]) == ""
    assert emitted == []


def test_docstring_does_not_claim_to_catch_event_validation_errors():
    """The docstring must match the handlers: EventValidationError is not a ValueError."""
    from divineos.event.event_validation import EventValidationError

    assert not issubclass(EventValidationError, ValueError)
    doc = capture_user_input.__doc__ or ""
    assert "Catches validation errors" not in doc
    assert "EventValidationError is NOT caught" in doc
