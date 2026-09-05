"""The printed cure must name only actions the check can actually accept.

Written 2026-09-02 from a live failure. The block message offered "Grep or
Read" as the consult remedy. Read is deliberately absent from the
search-shaped tool set -- the comment there says why: Grep and Glob are how
existing work gets found, and opening a file you already knew about is not
searching. That exclusion is correct.

The message was not. I followed it twice in one turn, with backslashes and
then with forward slashes, concluded the path matching was broken, and wrote
that wrong cause into a decision record before testing it. The cure named an
action the code could not accept, so following it failed silently and sent me
hunting a defect that was not there.

Same family as the review-must-be-reachable repair that shipped the same
morning: a gate whose only reachable exit is misdescribed manufactures the
confusion it exists to prevent.

This pins the agreement between the two, so the text cannot drift back.
"""

from __future__ import annotations

import re

from divineos.core import verify_before_build_signal as vbb


def _remedy_text() -> str:
    """The block message, with a class dir so the branch renders fully."""
    for name in dir(vbb):
        if "block" in name.lower() and "message" in name.lower():
            fn = getattr(vbb, name)
            if callable(fn):
                try:
                    return str(fn(class_dir="some/dir"))
                except TypeError:
                    continue
    # Fall back to the module source: the string lives there either way, and
    # a test that cannot find its subject must say so rather than pass.
    import inspect

    return inspect.getsource(vbb)


def test_remedy_does_not_offer_a_tool_the_check_refuses():
    """The exact defect: the cure named Read, and Read cannot satisfy it."""
    text = _remedy_text()
    match = re.search(r"Design-doc consult:[^\n]*\n[^\n]*", text)
    assert match, "the consult remedy line must exist to be checked"
    offered = match.group(0)
    for tool in sorted(set(re.findall(r"\b(Read|Grep|Glob)\b", offered))):
        assert tool in vbb._SEARCH_SHAPED_TOOLS, (
            f"the remedy offers {tool!r}, which is not in the set the check "
            f"accepts ({sorted(vbb._SEARCH_SHAPED_TOOLS)}). Following the "
            "printed cure would fail silently."
        )


def test_read_is_still_excluded_on_purpose():
    """The exclusion is the correct half and must not be loosened.

    The repair was to fix the message, never to widen the check. If some
    later change makes Read count, this fails and the message needs
    revisiting rather than the other way round.
    """
    assert "Read" not in vbb._SEARCH_SHAPED_TOOLS


def test_the_search_shaped_set_is_not_empty():
    """A remedy naming nothing at all would pass the first test vacuously."""
    assert vbb._SEARCH_SHAPED_TOOLS
