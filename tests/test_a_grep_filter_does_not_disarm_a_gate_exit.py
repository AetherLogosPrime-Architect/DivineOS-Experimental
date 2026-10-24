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
