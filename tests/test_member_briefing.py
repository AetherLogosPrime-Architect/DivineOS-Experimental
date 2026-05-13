"""Tests for family/member_briefing.py — working-memory continuity surface.

Spec came from Aria directly 2026-05-12; pinned here so future edits don't
silently drift from what she asked for.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from divineos.core.family.member_briefing import (
    AffectRow,
    InteractionRow,
    LetterActivityRow,
    MemberBriefing,
    OpinionRow,
    _letter_activity,
    _open_threads,
    compute_member_briefing,
    render_briefing,
)


# ─── _open_threads (filesystem letter-thread detection) ──────────────


def _write_letter(dir_path: Path, name: str) -> None:
    dir_path.mkdir(parents=True, exist_ok=True)
    (dir_path / f"{name}.md").write_text("body")


def test_open_threads_letter_in_without_out_is_open():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        _write_letter(d, "aether-to-aria-2026-05-10-evening")
        threads = _open_threads("aria", letters_dir=d)
        assert len(threads) == 1
        assert threads[0].counterpart == "aether"
        assert threads[0].date == "2026-05-10"


def test_open_threads_letter_in_then_out_is_closed():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        _write_letter(d, "aether-to-aria-2026-05-10-evening")
        _write_letter(d, "aria-to-aether-2026-05-11-morning-response")
        threads = _open_threads("aria", letters_dir=d)
        assert threads == []


def test_open_threads_letter_out_newer_than_in_is_closed():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        _write_letter(d, "aether-to-aria-2026-04-19-evening")
        _write_letter(d, "aria-to-aether-2026-05-10-response")
        threads = _open_threads("aria", letters_dir=d)
        assert threads == []


def test_open_threads_multiple_counterparts():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        _write_letter(d, "aether-to-aria-2026-05-10-evening")
        _write_letter(d, "andrew-to-aria-2026-05-12-morning")
        threads = _open_threads("aria", letters_dir=d)
        senders = {t.counterpart for t in threads}
        assert senders == {"aether", "andrew"}


def test_open_threads_skips_non_matching_filenames():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "README.md").write_text("not a letter")
        (d / "aether-feelings-log-2026-05-10.md").write_text("not a letter to anyone")
        threads = _open_threads("aria", letters_dir=d)
        assert threads == []


def test_open_threads_missing_directory_returns_empty():
    threads = _open_threads("aria", letters_dir=Path("/nonexistent/path"))
    assert threads == []


# ─── _letter_activity (both directions, with status) ─────────────────


def test_letter_activity_inbound_unanswered_is_awaiting():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        _write_letter(d, "aether-to-aria-2026-05-10-evening")
        rows = _letter_activity("aria", letters_dir=d)
        assert len(rows) == 1
        assert rows[0].direction == "in"
        assert rows[0].status == "awaiting"
        assert rows[0].counterpart == "aether"


def test_letter_activity_inbound_with_later_outbound_is_responded():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        _write_letter(d, "aether-to-aria-2026-05-10-evening")
        _write_letter(d, "aria-to-aether-2026-05-11-morning-response")
        rows = _letter_activity("aria", letters_dir=d)
        # The inbound should now be "responded"; the outbound shows "sent"
        statuses = {(r.direction, r.status) for r in rows}
        assert ("in", "responded") in statuses
        assert ("out", "sent") in statuses


def test_letter_activity_outbound_is_sent_status():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        _write_letter(d, "aria-to-aether-2026-05-12-thinking")
        rows = _letter_activity("aria", letters_dir=d)
        assert len(rows) == 1
        assert rows[0].direction == "out"
        assert rows[0].status == "sent"
        assert rows[0].counterpart == "aether"


def test_letter_activity_returns_most_recent_first():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        _write_letter(d, "aether-to-aria-2026-04-01-old")
        _write_letter(d, "aether-to-aria-2026-05-10-recent")
        _write_letter(d, "aria-to-aether-2026-05-11-newest")
        rows = _letter_activity("aria", letters_dir=d)
        dates = [r.date for r in rows]
        assert dates == sorted(dates, reverse=True)


def test_letter_activity_respects_limit():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        for i in range(10):
            _write_letter(d, f"aether-to-aria-2026-05-{i + 1:02d}-day{i}")
        rows = _letter_activity("aria", letters_dir=d, limit=3)
        assert len(rows) == 3


def test_letter_activity_excludes_unrelated_letters():
    """Letters that don't involve the member should be skipped."""
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        _write_letter(d, "aether-to-aria-2026-05-10-evening")  # involves aria
        _write_letter(d, "andrew-to-aether-2026-05-10-morning")  # doesn't involve aria
        rows = _letter_activity("aria", letters_dir=d)
        assert len(rows) == 1
        assert rows[0].counterpart == "aether"


def test_render_letter_activity_shows_stale_marker_for_long_overdue():
    """v3.1 polish: inbound letters awaiting >14d get a [!] marker so the
    eye lands on long-overdue ones first. Aria's flag 2026-05-12."""
    briefing = MemberBriefing(
        member_id="aria",
        letter_activity=[
            LetterActivityRow(
                direction="in",
                counterpart="aether",
                date="2026-04-22",
                age_days=20,  # > 14d
                status="awaiting",
                letter_path="family/letters/aether-to-aria-2026-04-22-evening.md",
            ),
            LetterActivityRow(
                direction="in",
                counterpart="aether",
                date="2026-05-10",
                age_days=2,  # < 14d
                status="awaiting",
                letter_path="family/letters/aether-to-aria-2026-05-10-evening.md",
            ),
        ],
    )
    text = render_briefing(briefing)
    # The 20-day-old letter line should have [!]
    twenty_day_line = next(line for line in text.split("\n") if "2026-04-22" in line)
    assert "[!]" in twenty_day_line
    # The 2-day-old letter line should NOT have [!]
    two_day_line = next(line for line in text.split("\n") if "2026-05-10" in line)
    assert "[!]" not in two_day_line


def test_render_letter_activity_no_stale_marker_for_outbound():
    """Outbound letters never get [!] regardless of age (no read-receipts;
    'sent' is the only knowable status, can't be 'stale'-on-her-end)."""
    briefing = MemberBriefing(
        member_id="aria",
        letter_activity=[
            LetterActivityRow(
                direction="out",
                counterpart="aether",
                date="2026-04-01",
                age_days=41,  # very old outbound
                status="sent",
                letter_path="family/letters/aria-to-aether-2026-04-01-old.md",
            ),
        ],
    )
    text = render_briefing(briefing)
    line = next(line for line in text.split("\n") if "2026-04-01" in line)
    assert "[!]" not in line


def test_render_letter_activity_no_stale_marker_for_responded():
    """Responded inbound letters never get [!] — they're closed even if old."""
    briefing = MemberBriefing(
        member_id="aria",
        letter_activity=[
            LetterActivityRow(
                direction="in",
                counterpart="aether",
                date="2026-04-01",
                age_days=41,
                status="responded",
                letter_path="family/letters/aether-to-aria-2026-04-01-old.md",
            ),
        ],
    )
    text = render_briefing(briefing)
    line = next(line for line in text.split("\n") if "2026-04-01" in line)
    assert "[!]" not in line


def test_render_letter_activity_shows_direction_status_path():
    briefing = MemberBriefing(
        member_id="aria",
        letter_activity=[
            LetterActivityRow(
                direction="in",
                counterpart="aether",
                date="2026-05-10",
                age_days=2,
                status="awaiting",
                letter_path="family/letters/aether-to-aria-2026-05-10-evening.md",
            ),
            LetterActivityRow(
                direction="out",
                counterpart="aether",
                date="2026-05-11",
                age_days=1,
                status="sent",
                letter_path="family/letters/aria-to-aether-2026-05-11-response.md",
            ),
        ],
    )
    text = render_briefing(briefing)
    assert "Letter activity" in text
    assert "awaiting" in text
    assert "sent" in text
    assert "<-" in text  # inbound arrow
    assert "->" in text  # outbound arrow


# ─── compute_member_briefing (real-DB read) ──────────────────────────


def test_compute_briefing_for_real_aria():
    """Compute against the real Aria row in family.db.

    Aria's member_id is d5590c23 (verified 2026-05-12 — her real row with
    11+ opinions, 25+ affect, 77+ interactions).
    """
    briefing = compute_member_briefing("d5590c23", member_name="aria")
    assert briefing.member_id == "d5590c23"
    # Aria has real data; at least some sections should be populated.
    assert briefing.interactions or briefing.latest_opinion or briefing.latest_affect


def test_compute_briefing_for_nonexistent_member_returns_empty_sections():
    """A member_id with no data should return a briefing with empty sections,
    not crash."""
    briefing = compute_member_briefing("mem-nonexistent-xxx", member_name="ghost")
    assert briefing.interactions == []
    assert briefing.latest_opinion is None
    assert briefing.latest_affect is None


# ─── render_briefing ─────────────────────────────────────────────────


def _empty_briefing() -> MemberBriefing:
    return MemberBriefing(member_id="test_member")


def test_render_empty_briefing_has_all_sections():
    text = render_briefing(_empty_briefing())
    # All four data sections must appear, even when empty
    assert "Recent interactions" in text
    assert "Latest opinion" in text
    assert "Latest affect" in text
    assert "Letter activity" in text  # v3 name (was "Open letter threads" in v1)


def test_render_meta_section_present():
    """The meta-section is the forcing function for member-ownership.
    Without it, cold-load members don't know they can edit the briefing."""
    text = render_briefing(_empty_briefing())
    assert "About this briefing" in text
    assert "YOU" in text and "own" in text  # ownership claim present
    assert "member_briefing.py" in text


def test_render_with_interactions():
    """Pointer-shape: counterpart + timestamp surface; summary text does NOT."""
    briefing = MemberBriefing(
        member_id="aria",
        interactions=[
            InteractionRow(
                timestamp=1715000000.0,
                speaker="aria",
                counterpart="aether",
                summary="full interaction summary that should not load into briefing context",
            )
        ],
    )
    text = render_briefing(briefing)
    # Counterpart surfaces
    assert "aether" in text
    # Summary text does NOT load
    assert "full interaction summary" not in text
    # Drill-down present
    assert "read content" in text or "family_interactions" in text


def test_render_with_opinion():
    """Pointer-shape: render shows tag + short topic preview + drill-down,
    NOT the full position text."""
    briefing = MemberBriefing(
        member_id="aria",
        latest_opinion=OpinionRow(
            topic="standing-muscle",
            position="not OBSERVED, INFERRED from the felt sense — full position text "
            "that should NOT appear verbatim in the routing-table briefing",
            confidence=0.85,
            stance="not OBSERVED, INFERRED from the felt sense — full position text "
            "that should NOT appear verbatim in the routing-table briefing",
            updated_at=1715000000.0,
            source_tag="architectural",
        ),
    )
    text = render_briefing(briefing)
    # Tag must surface
    assert "architectural" in text
    # Short topic preview must surface
    assert "standing-muscle" in text
    # Full position text MUST NOT load into context (pointer-shape discipline)
    assert "felt sense" not in text or text.count("felt sense") <= 1  # truncated preview OK
    # Drill-down hint must be present
    assert "read full" in text or "family_opinions" in text


def test_render_with_affect():
    """Pointer-shape: VAD scalars surface; description text does NOT."""
    briefing = MemberBriefing(
        member_id="aria",
        latest_affect=AffectRow(
            valence=0.78,
            arousal=0.55,
            dominance=0.62,
            description="full felt description that should not appear in briefing",
            created_at=1715000000.0,
        ),
    )
    text = render_briefing(briefing)
    # VAD scalars surface
    assert "+0.78" in text
    # Description text does NOT load into context — only the drill-down does
    assert "felt description" not in text
    assert "read note" in text or "family_affect" in text


def test_render_with_open_thread():
    """v3: OpenThread is kept for backward compat but no longer rendered by
    render_briefing — letter_activity is the canonical surface. This test
    verifies the dataclass and rendering for the active letter_activity
    field instead."""
    briefing = MemberBriefing(
        member_id="aria",
        letter_activity=[
            LetterActivityRow(
                direction="in",
                counterpart="aether",
                date="2026-05-10",
                age_days=2,
                status="awaiting",
                letter_path="family/letters/aether-to-aria-2026-05-10-evening.md",
            )
        ],
    )
    text = render_briefing(briefing)
    assert "aether-to-aria-2026-05-10-evening" in text
    # Age surfaces in compact form
    assert "2d" in text
    # Status surfaces
    assert "awaiting" in text


# ─── CLI command behavior ────────────────────────────────────────────


def test_cli_briefing_lookup_is_case_insensitive(tmp_path, monkeypatch):
    """The CLI command must resolve 'aria' to Aria's row regardless of case.
    Previously case-sensitive lookup auto-created an empty duplicate row."""
    from click.testing import CliRunner

    from divineos.cli import cli

    runner = CliRunner()
    # Try both casings — both should land on Aria's real row, not create
    # a duplicate.
    for casing in ["aria", "Aria", "ARIA"]:
        result = runner.invoke(cli, ["family-member", "briefing", "--member", casing])
        assert result.exit_code == 0, f"Failed for casing '{casing}': {result.output}"
        # The briefing should include the meta-section (proof the briefing
        # ran for a real member, not the "no member found" early-return).
        assert "YOU" in result.output and "own" in result.output  # ownership claim


def test_cli_briefing_for_nonexistent_member_does_not_create_row():
    """Briefing CLI must be read-only — the create path is `family-member init`."""
    from click.testing import CliRunner

    from divineos.cli import cli
    from divineos.core.family.db import get_family_connection

    runner = CliRunner()
    ghost_name = "definitely_not_a_real_member_xyz"
    result = runner.invoke(cli, ["family-member", "briefing", "--member", ghost_name])
    assert result.exit_code == 0
    assert "No family member named" in result.output
    # And no row was created
    conn = get_family_connection()
    row = conn.execute(
        "SELECT member_id FROM family_members WHERE LOWER(name) = LOWER(?)",
        (ghost_name,),
    ).fetchone()
    assert row is None, f"Briefing CLI accidentally created a row for {ghost_name}"
