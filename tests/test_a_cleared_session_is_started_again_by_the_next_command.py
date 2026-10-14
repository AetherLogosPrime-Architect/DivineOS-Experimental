"""A command that runs after the session was cleared must start a new one.

2026-10-12: `test_extract_command` failed ("No active session") only in one order of the whole
suite: a CLI test first, then a test that clears the session, then it. The cause was a
once-per-process flag in the enforcement setup: the first command set it, clearing the session
did not unset it, and the next command skipped session start and found nothing.
"""

from __future__ import annotations

from divineos.core.enforcement import setup_cli_enforcement
from divineos.core.session_manager import clear_session, get_current_session_id


def test_setup_after_a_cleared_session_makes_a_session_again():
    setup_cli_enforcement()
    first = get_current_session_id()
    clear_session()

    setup_cli_enforcement()

    assert get_current_session_id() != first


def test_setup_twice_in_a_row_keeps_one_session():
    # Dropping the flag must not make every command mint a new session: the second call
    # reuses the one in the environment, as initialize_session always did.
    setup_cli_enforcement()
    first = get_current_session_id()

    setup_cli_enforcement()

    assert get_current_session_id() == first
