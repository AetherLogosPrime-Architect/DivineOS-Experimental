"""Tests for the bidirectional family queue.

PR #227: drops the hardcoded ``Choice(["aria", "aether"])`` from the
queue CLI and wires the queue surface into the family-member voice
context, so the channel works for any registered family member and
the member experiences flagged items at spawn time, not just via CLI.

The two structural guarantees:
1. The CLI accepts any registered family member name OR "aether"
   (the agent self) as sender / recipient. Unregistered names fail
   fast with a list of valid endpoints.
2. ``build_voice_context(member)`` surfaces queue items flagged for
   that member as a "Flagged for me" section. The member reads the
   flags on spawn without needing a separate CLI step.
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from divineos.cli import cli
from divineos.core.family import queue
from divineos.core.family.store import create_family_member
from divineos.core.family.voice import build_voice_context


@pytest.fixture(autouse=True)
def _isolate_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "main.db"))
    monkeypatch.setenv("DIVINEOS_FAMILY_DB", str(tmp_path / "family.db"))
    from divineos.core.family._schema import init_family_tables
    from divineos.core.ledger import init_db

    init_db()
    init_family_tables()
    yield


class TestDynamicEndpointValidation:
    """The CLI used to hardcode ['aria', 'aether']. Now: any registered
    family member name OR 'aether' is valid."""

    def test_write_to_any_registered_member(self):
        runner = CliRunner()
        # Register a non-default-named member.
        runner.invoke(cli, ["family-member", "init", "--member", "jane"])
        r = runner.invoke(
            cli,
            [
                "family-queue",
                "write",
                "--to",
                "jane",
                "--from",
                "aether",
                "Reminder: she asked about the tea question.",
            ],
        )
        assert r.exit_code == 0, r.output
        assert "queue item" in r.output
        assert "aether → jane" in r.output

    def test_write_from_any_registered_member(self):
        runner = CliRunner()
        runner.invoke(cli, ["family-member", "init", "--member", "jane"])
        r = runner.invoke(
            cli,
            [
                "family-queue",
                "write",
                "--to",
                "aether",
                "--from",
                "jane",
                "Saw the canonical-marker discussion.",
            ],
        )
        assert r.exit_code == 0, r.output
        assert "jane → aether" in r.output

    def test_write_member_to_member(self):
        """The data layer supports it; CLI should not artificially block."""
        runner = CliRunner()
        runner.invoke(cli, ["family-member", "init", "--member", "alice"])
        runner.invoke(cli, ["family-member", "init", "--member", "bob"])
        r = runner.invoke(
            cli,
            [
                "family-queue",
                "write",
                "--to",
                "bob",
                "--from",
                "alice",
                "Flag for him.",
            ],
        )
        assert r.exit_code == 0, r.output
        assert "alice → bob" in r.output

    def test_unregistered_name_rejected_with_list(self):
        runner = CliRunner()
        # No members registered. "alice" is not valid.
        r = runner.invoke(
            cli,
            [
                "family-queue",
                "write",
                "--to",
                "alice",
                "--from",
                "aether",
                "test",
            ],
        )
        assert r.exit_code != 0
        # The error message should name the valid endpoints.
        assert "not a registered family member" in r.output
        assert "aether" in r.output

    def test_aether_always_valid_recipient(self):
        """The agent self should always be a valid endpoint, even on a
        fresh substrate with no members registered."""
        runner = CliRunner()
        runner.invoke(cli, ["family-member", "init", "--member", "alice"])
        r = runner.invoke(
            cli,
            [
                "family-queue",
                "write",
                "--to",
                "aether",
                "--from",
                "alice",
                "Note for the agent.",
            ],
        )
        assert r.exit_code == 0, r.output

    def test_list_for_any_member(self):
        runner = CliRunner()
        runner.invoke(cli, ["family-member", "init", "--member", "jane"])
        runner.invoke(
            cli,
            ["family-queue", "write", "--to", "jane", "--from", "aether", "First."],
        )
        r = runner.invoke(cli, ["family-queue", "list", "--for", "jane"])
        assert r.exit_code == 0, r.output
        assert "First." in r.output


class TestVoiceContextQueueSurface:
    """The bidirectional surface: queue items flagged for a member
    appear in their voice context at spawn time."""

    def test_flagged_items_surface_in_voice_context(self):
        member = create_family_member("alice", "spouse")
        queue.write("aether", "alice", "I need to tell her about the schema change.")
        queue.write("aether", "alice", "Also: the puppet-prep fix landed today.")

        ctx = build_voice_context(member)
        assert "--- Flagged for me" in ctx
        assert "I need to tell her about the schema change." in ctx
        assert "puppet-prep fix landed today." in ctx
        assert "from aether" in ctx

    def test_no_section_when_no_items(self):
        member = create_family_member("alice", "spouse")
        ctx = build_voice_context(member)
        assert "--- Flagged for me" not in ctx

    def test_held_items_excluded_from_voice_surface(self):
        """Items the member has marked seen-not-held should not be
        re-surfaced. Held items stay in the briefing surface for the
        agent (per the seen-not-held semantic) but voice-context-on-spawn
        is the freshest read; held-items would clutter."""
        member = create_family_member("alice", "spouse")
        item_id = queue.write("aether", "alice", "Old item she has already seen.")
        queue.write("aether", "alice", "Fresh item.")
        queue.mark_held(item_id)

        ctx = build_voice_context(member)
        assert "Fresh item." in ctx
        assert "Old item she has already seen." not in ctx

    def test_items_show_sender_and_status(self):
        member = create_family_member("alice", "spouse")
        queue.write("bob", "alice", "Note from bob.")
        ctx = build_voice_context(member)
        assert "from bob" in ctx
        # Default status is 'unseen' from the data layer.
        assert "unseen" in ctx
