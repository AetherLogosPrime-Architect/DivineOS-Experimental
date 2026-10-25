"""A gate's exit stays an exit when its output is filtered through grep.

2026-10-24: I ended nearly every divineos command with `2>&1 | grep -v "embedding\\|Loading" | tail -3` to
hide model-loading noise. The shared remedy matcher knew `head` and `tail` as harmless viewers but not
`grep`, so a recording command with that filter on the end stopped being a recognised exit. The correction
marker told me to run `divineos compass-ops observe`; the council-paperwork gate refused it as an edit;
and the paperwork commands were themselves blocked by the marker. Each gate was right and I was the one
who had made the exit unrecognisable. Dad ordered the root cause fixed.

The bar for the viewer list (command_parsing._INERT_HEADS): consumes input, emits text, cannot write.
GNU grep has no option that writes a file, unlike sed and awk, which stay out.

This file pins the parsing half. The half that matters, the real shell library deciding on a real hook
payload, is in tests/test_remedy_allowlist.py (class TestAGrepFilterDoesNotDisarmAnExit).
Draft: docs/drafts/a_grep_filter_does_not_disarm_a_gate_exit_draft_2026-10-24.md.
"""

from __future__ import annotations

from divineos.core.command_parsing import _INERT_HEADS, acting_segments

NOISE = '"embedding\\|Loading weights\\|Could not reach"'


def test_the_filter_is_stripped_and_the_exit_is_what_remains():
    assert acting_segments(f"divineos learn x 2>&1 | grep -v {NOISE} | tail -3") == [
        "divineos learn x 2>&1"
    ]


def test_a_grep_alone_is_inert_and_does_not_hide_an_acting_command_beside_it():
    assert acting_segments("grep -r x . && git push") == ["git push"]
    assert acting_segments("divineos learn x | grep y && rm -rf /tmp/z") == [
        "divineos learn x",
        "rm -rf /tmp/z",
    ]


def test_grep_joins_the_viewers_and_the_write_capable_filters_stay_out():
    assert "grep" in _INERT_HEADS
    assert "sed" not in _INERT_HEADS
    assert "awk" not in _INERT_HEADS


# Aletheia's hold on #718 (2026-10-24): a viewer is inert only while it writes nothing. Before this
# change `| grep x > out.txt` (and `echo x > src/...`) was dropped WHOLE, redirect included, so the
# write was invisible to every gate; adding grep to the viewers opened it wider for exactly the
# commands that end in a filter. A redirect to anywhere but /dev/null makes the segment act.


def test_a_viewer_with_a_redirect_to_a_file_is_an_acting_segment():
    assert acting_segments("divineos briefing | grep x > out.txt") == [
        "divineos briefing",
        "grep x > out.txt",
    ]
    assert acting_segments("divineos briefing | grep x >> out.txt") == [
        "divineos briefing",
        "grep x >> out.txt",
    ]


def test_a_redirect_over_source_is_never_hidden_behind_an_inert_head():
    assert acting_segments("divineos briefing | grep x > src/divineos/core/ledger.py") == [
        "divineos briefing",
        "grep x > src/divineos/core/ledger.py",
    ]
    assert acting_segments("echo x > .claude/settings.json && divineos briefing") == [
        "echo x > .claude/settings.json",
        "divineos briefing",
    ]
    assert acting_segments("divineos briefing | cat > notes.txt") == [
        "divineos briefing",
        "cat > notes.txt",
    ]


def test_every_spelling_of_a_write_redirect_counts():
    # `&>` is split on its ampersand by the segment reader, so what must hold is that the write target
    # shows in some acting segment, not that the segment is spelled one way.
    for spelling in ("&> out.txt", ">| out.txt", "2> err.txt", "&>> out.txt"):
        got = acting_segments(f"divineos briefing | grep x {spelling}")
        assert got is not None and any(t in seg for seg in got for t in ("out.txt", "err.txt")), (
            spelling
        )


def test_control_a_redirect_to_dev_null_leaves_the_filter_inert():
    assert acting_segments("divineos briefing 2>&1 | grep -v noise 2>/dev/null") == [
        "divineos briefing 2>&1"
    ]
    assert acting_segments("divineos briefing | grep x > /dev/null") == ["divineos briefing"]


def test_control_a_filter_with_no_redirect_stays_inert():
    assert acting_segments("divineos briefing | grep x | head -5") == ["divineos briefing"]
