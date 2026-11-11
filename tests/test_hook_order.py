"""One table orders every refusing surface, and a Stop that refuses several things says one first."""

from divineos.core import hook_order, hook_router, hook_surfaces
from divineos.core.hook_router import RouterResult, SurfaceOutcome


def _refused(name: str, reason: str) -> SurfaceOutcome:
    return SurfaceOutcome(name=name, refused=True, reason=reason, state="spoke")


def test_a_tool_call_goes_before_appended_text():
    first, rest = hook_order.first_and_rest(
        "Stop",
        [("summary_room", "add a summary"), ("landed_claim", "read the remote")],
    )
    assert first[0] == "landed_claim"
    assert rest == ["summary_room"]


def test_one_refusal_is_left_exactly_as_it_was():
    result = RouterResult(event="Stop", refusals=[_refused("summary_room", "add a summary")])
    assert "BLOCKED by summary_room: add a summary" in result.stderr()
    assert "after that" not in result.stderr().lower()


def test_several_stop_refusals_say_one_in_full_and_name_the_rest():
    result = RouterResult(
        event="Stop",
        refusals=[
            _refused("summary_room", "SUMMARY-TEXT add a summary"),
            _refused("landed_claim", "LANDED-TEXT read the remote"),
            _refused("voiced_family", "VOICED-TEXT take it back"),
        ],
    )
    text = result.stderr()
    assert "BLOCKED by landed_claim: LANDED-TEXT" in text
    lower = text.lower()
    assert "after that" in lower
    tail = text[lower.index("after that") :]
    assert "summary_room" in tail and "voiced_family" in tail
    # the others are named, not told in full a second time
    assert "SUMMARY-TEXT" not in text and "VOICED-TEXT" not in text


def test_surfaces_with_no_row_are_left_alone_and_never_swallowed():
    result = RouterResult(
        event="Stop",
        refusals=[_refused("brand_new_note", "NEW-TEXT"), _refused("summary_room", "SUM-TEXT")],
    )
    text = result.stderr()
    assert "NEW-TEXT" in text and "SUM-TEXT" in text


def test_unknown_surfaces_sort_last_and_are_reported():
    first, rest = hook_order.first_and_rest(
        "Stop", [("brand_new_note", "x"), ("summary_room", "y")]
    )
    assert first[0] == "summary_room"
    assert hook_order.unlisted("Stop", ["brand_new_note", "summary_room"]) == ["brand_new_note"]


def test_a_row_nobody_has_read_says_unread_and_never_looks_like_a_known_kind():
    # Aria's cold read: heredoc_escape was filed as "other" when its way out is the Write tool.
    # A placeholder kind that looks like a fact gets believed, so unread rows are named UNREAD.
    assert hook_order.row_for("PreToolUse", "heredoc_escape").kind == hook_order.TOOL_CALL
    # Every refusal text was read on 2026-11-04 (Stop by me, PreToolUse by Aria): nothing is
    # unread now. The kind stays for the next surface registered before anyone reads its text.
    unread = [r.name for r in hook_order.ROWS if r.kind == hook_order.UNREAD]
    assert unread == [], unread
    assert hook_order.row_for("PreToolUse", "pr_merge_gate").kind == hook_order.TOOL_CALL
    assert hook_order.row_for("PreToolUse", "trial_in_days").kind == hook_order.TOOL_CALL
    # The four Stop surfaces that never refuse (they record or report) are record-only, not
    # text remedies.
    assert hook_order.row_for("Stop", "waiting_claim").kind == hook_order.TOOL_CALL
    for name in ("self_demotion_stop", "his_standing_verdict", "close_reach", "compaction_reach"):
        assert hook_order.row_for("Stop", name).kind == hook_order.RECORD_ONLY, name
    known = {
        hook_order.READ_LETTER,
        hook_order.WAIT,
        hook_order.TOOL_CALL,
        hook_order.APPEND_TEXT,
        hook_order.UNREAD,
        hook_order.RECORD_ONLY,
    }
    assert {r.kind for r in hook_order.ROWS} <= known


def test_every_registered_surface_has_a_row():
    # The twenty-first person: a surface added to the router with no row in the table
    # is a new sticky note nobody ordered, and this fails until it joins.
    hook_router.clear()
    hook_surfaces.install()
    for event in ("Stop", "PreToolUse"):
        assert hook_order.unlisted(event, hook_router.registered(event)) == [], event
