"""Test that `divineos hold check` is a pure review surface — no auto-mutation.

Bullet-wound-clause + code-does-not-think directives (2026-05-12). Pattern
matches `goal check`: surface puts items in front of me with age + content,
shows decide-each affordances, leaves the decision with me. The machine
records what I decide via separate `hold promote` and `hold let-go`
commands; it never decides for me.

A regression that wires auto-promotion or auto-let-go into the check
command fails the mutation-purity test.
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from divineos.cli import cli
from divineos.core.holding import hold as receive, let_go, promote


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setenv("DIVINEOS_DB", str(db))
    yield db


def test_hold_check_lists_active_items(isolated_db):
    """All active items appear, regardless of age."""
    receive("old idea worth remembering", mode="receive")
    receive("fresh idea", mode="receive")

    runner = CliRunner()
    result = runner.invoke(cli, ["hold", "check"])
    assert result.exit_code == 0
    assert "old idea worth remembering" in result.output
    assert "fresh idea" in result.output


def test_hold_check_does_not_mutate(isolated_db):
    """Pure-read surface — running check leaves the store unchanged."""
    receive("test item", mode="receive")

    from divineos.core.holding import get_holding

    before = get_holding(include_stale=True)
    assert len(before) == 1
    assert before[0]["promoted_to"] is None
    assert before[0]["stale"] == 0

    runner = CliRunner()
    runner.invoke(cli, ["hold", "check"])

    after = get_holding(include_stale=True)
    assert len(after) == 1
    assert after[0]["promoted_to"] is None
    assert after[0]["stale"] == 0


def test_hold_check_shows_decide_affordances(isolated_db):
    """The surface names how to promote, let-go, or leave-alive — making the
    cognitive next-step explicit instead of leaving the agent to guess."""
    receive("something", mode="receive")

    runner = CliRunner()
    result = runner.invoke(cli, ["hold", "check"])
    assert result.exit_code == 0
    assert "Decide each" in result.output
    assert "hold promote" in result.output
    assert "hold let-go" in result.output


def test_hold_check_empty_state(isolated_db):
    """No active items → friendly empty message, no crash."""
    runner = CliRunner()
    result = runner.invoke(cli, ["hold", "check"])
    assert result.exit_code == 0
    assert "No items in holding" in result.output


def test_hold_check_includes_stale_items(isolated_db):
    """Stale items still appear (unlike `hold list` which filters them by default).
    Reviewing means looking at all of them, marked-stale or not."""
    item_id = receive("aged item", mode="receive")
    # Manually mark stale to simulate auto-aging
    from divineos.core.holding import _get_connection

    conn = _get_connection()
    conn.execute("UPDATE holding_room SET stale = 1 WHERE item_id = ?", (item_id,))
    conn.commit()
    conn.close()

    runner = CliRunner()
    result = runner.invoke(cli, ["hold", "check"])
    assert "aged item" in result.output
    assert "stale" in result.output


def test_let_go_marks_item_closed(isolated_db):
    """`let_go` records the operator's decision in promoted_to with let-go marker."""
    item_id = receive("idea to let go of", mode="receive")
    assert let_go(item_id, note="superseded by exploration/48") is True

    from divineos.core.holding import _get_connection

    conn = _get_connection()
    row = conn.execute(
        "SELECT promoted_to FROM holding_room WHERE item_id = ?", (item_id,)
    ).fetchone()
    conn.close()
    assert row[0].startswith("let-go")
    assert "superseded" in row[0]


def test_let_go_without_note_records_let_go_marker(isolated_db):
    item_id = receive("plain let-go", mode="receive")
    assert let_go(item_id) is True

    from divineos.core.holding import _get_connection

    conn = _get_connection()
    row = conn.execute(
        "SELECT promoted_to FROM holding_room WHERE item_id = ?", (item_id,)
    ).fetchone()
    conn.close()
    assert row[0] == "let-go"


def test_let_go_after_promote_returns_false(isolated_db):
    """Can't let-go an already-promoted item — append-only spirit holds."""
    item_id = receive("test", mode="receive")
    promote(item_id, "knowledge")
    assert let_go(item_id) is False


def test_let_go_cli_command(isolated_db):
    """The CLI invocation routes to the store correctly."""
    item_id = receive("CLI test item", mode="receive")
    runner = CliRunner()
    result = runner.invoke(cli, ["hold", "let-go", item_id, "--note", "trying it"])
    assert result.exit_code == 0
    assert "Let go" in result.output
    assert item_id in result.output


def test_let_go_cli_command_unknown_item(isolated_db):
    runner = CliRunner()
    result = runner.invoke(cli, ["hold", "let-go", "hold-doesnotexist"])
    assert result.exit_code == 0
    assert "not found" in result.output.lower() or "already" in result.output.lower()
