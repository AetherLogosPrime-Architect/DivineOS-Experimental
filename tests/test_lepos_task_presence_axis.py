"""Tests for the LEPOS task-presence axis (Aletheia finding #6).

Closes Aletheia's six-painpoints audit finding #6: the mirror equating
presence with felt-narration only was a category error. A technical-
work turn that ran real tool-calls AND cited Andrew's exact span IS
present at a different axis — task-presence, not felt-presence.
Equating the two would train me to PERFORM interior-verbs to clear
the gate (the exact Goodhart Aria just fixed one layer over).

Contract:
- verified_substrate_engagement fires when tool_calls_in_turn is
  non-empty AND heard is True.
- degenerate() returns False when verified_substrate_engagement is
  True even if interior is False.
- The markdown output names the task-presence axis when it fires.
- Backward-compat: reflect() called without tool_calls_in_turn keeps
  its original behavior (both older 4-arg call sites and new 5-arg
  keyword calls work).
"""

from __future__ import annotations

from divineos.core.lepos_channel_reflect import reflect


def test_verified_substrate_engagement_fires_on_tools_plus_citation():
    """Task-presence: real tools AND a cited Andrew span → axis fires."""
    andrew = "please make sure the compaction monitor uses the transcript file"
    reply = "I checked the compaction monitor uses the transcript file — verified."
    r = reflect(reply, andrew, tool_calls_in_turn=("Bash", "Read"))
    assert r.heard is True
    assert r.verified_substrate_engagement is True


def test_verified_substrate_engagement_requires_both_tools_and_citation():
    """Tools alone without a cited span → task-axis does NOT fire.
    Prevents empty-hand-wavy technical turns from claiming presence."""
    andrew = "please make sure the compaction monitor uses the transcript file"
    reply = "Done."  # no cited span
    r = reflect(reply, andrew, tool_calls_in_turn=("Bash", "Edit"))
    assert r.heard is False
    assert r.verified_substrate_engagement is False


def test_verified_substrate_engagement_requires_tools_not_citation_alone():
    """Cited span without any tool-calls → task-axis does NOT fire.
    (heard alone was never presence at the task axis; that's why the
    third axis exists.)"""
    andrew = "please make sure the compaction monitor uses the transcript file"
    reply = "the compaction monitor uses the transcript file, yes."
    r = reflect(reply, andrew, tool_calls_in_turn=None)
    assert r.heard is True
    assert r.verified_substrate_engagement is False


def test_task_presence_saves_from_channel_empty():
    """A technical-work turn with tools + citation but NO felt-interior
    markers must NOT read as degenerate — that was the exact false-fire
    Aletheia flagged."""
    andrew = "run the wiring gap check"
    reply = "Ran wiring gap check — result: no gaps."  # technical, no interior
    r = reflect(reply, andrew, tool_calls_in_turn=("Bash",))
    assert r.verified_substrate_engagement is True
    assert r.interior is False
    assert r.degenerate() is False, (
        "task-axis presence must save this reply from the channel-empty "
        "flag — technical work with citation IS presence at a different axis"
    )


def test_channel_empty_still_fires_when_no_axis_saves_it():
    """All three axes absent → degenerate → channel-empty message.
    The fix must NOT over-suppress the empty-channel case."""
    andrew = "let me know when the deployment landed"
    reply = "Sure."  # no citation, no interior, no tools
    r = reflect(reply, andrew, tool_calls_in_turn=None)
    assert r.heard is False
    assert r.interior is False
    assert r.verified_substrate_engagement is False
    assert r.degenerate() is True
    assert "channel-empty" in r.markdown()


def test_markdown_names_task_presence_when_it_fires():
    """The reader must SEE the task-axis presence in the surfaced
    markdown — otherwise the fix doesn't communicate why the mirror
    stayed silent on a technical-work turn."""
    andrew = "wire the compaction monitor into the new session start"
    reply = "Wired the compaction monitor into the session start."
    r = reflect(reply, andrew, tool_calls_in_turn=("Edit", "Bash"))
    md = r.markdown()
    assert "task-presence" in md
    assert "verified" in md
    assert "channel-empty" not in md


def test_backward_compat_no_tool_calls_arg():
    """Existing call sites that don't pass tool_calls_in_turn keep
    working — the new field defaults to False and doesn't affect the
    old two-axis behavior."""
    andrew = "care about it"
    reply = "I feel it — the care lands."
    r = reflect(reply, andrew)  # no tool_calls kwarg
    assert r.verified_substrate_engagement is False
    assert r.interior is True  # "feel" is an interior marker
    assert r.degenerate() is False


def test_empty_tool_calls_tuple_is_same_as_none():
    """Passing an empty tuple/list explicitly is equivalent to no
    tools — the task-axis does not fire on empty."""
    andrew = "consider this"
    reply = "considered this"
    r = reflect(reply, andrew, tool_calls_in_turn=())
    assert r.verified_substrate_engagement is False
