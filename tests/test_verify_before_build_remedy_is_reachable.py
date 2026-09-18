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


# ─── The remedy's PATH SHAPE, not just its tool names ──────────────────────
#
# Added 2026-09-18 (council-6d8022ff8464). The tests above pin that the printed
# remedy names only tools the check accepts, and they have held since 2026-09-02.
# The same class recurred one level over anyway: the tool names were right and
# the PATH SHAPE was unaccepted. The message says "Grep or Glob of a docs/*.md
# file", and the natural execution of that — path set to the docs directory,
# glob set to the markdown pattern — matched nothing, because a directory does
# not end in .md and the glob field was never read at all. The block that
# followed was byte-identical to the block for never having looked.
#
# So a test that checks only the VOCABULARY of a remedy is not checking the
# remedy. These run the prescribed shapes through the real detector.


def _consult_seen(tool_input: dict, *, search_only: bool = True) -> bool:
    """Run one synthetic tool-call through the real consult detector."""
    import sys
    import time as _time
    import types

    now = _time.time()
    fake = types.ModuleType("divineos.core.tool_logbook")

    def get_recent_events(**_kwargs):
        return [
            {
                "timestamp": now - 5,
                "payload": {"tool_name": "Grep", "tool_input": tool_input},
            }
        ]

    fake.get_recent_events = get_recent_events  # type: ignore[attr-defined]
    original = sys.modules.get("divineos.core.tool_logbook")
    sys.modules["divineos.core.tool_logbook"] = fake
    try:
        return vbb._has_doc_consult_within(
            "src/divineos/core", now - 1800, now, search_only=search_only
        )
    finally:
        if original is not None:
            sys.modules["divineos.core.tool_logbook"] = original
        else:
            del sys.modules["divineos.core.tool_logbook"]


def test_the_prescribed_docs_search_is_accepted():
    """Directory in one field, file-type in another — the shape the text asks for."""
    assert _consult_seen({"path": "docs", "glob": "*.md", "pattern": "threshold"}) is True


def test_the_prescribed_docs_search_with_an_absolute_windows_path():
    """The same search as the tools actually emit it on this machine."""
    assert (
        _consult_seen(
            {
                "path": "C:\\DIVINE OS\\DivineOS-Experimental\\docs",
                "glob": "*.md",
                "pattern": "headroom",
            }
        )
        is True
    )


def test_a_single_docs_file_still_counts():
    """The shape that already worked must keep working."""
    assert _consult_seen({"path": "docs/build_flow.md", "pattern": "council"}) is True


def test_a_search_with_no_docs_anywhere_is_not_a_consult():
    """The control. If this reads as a consult, the widening went too far."""
    assert _consult_seen({"path": "src/divineos", "glob": "*.py", "pattern": "foo"}) is False


def test_a_markdown_glob_outside_docs_is_not_a_consult():
    """Both halves are required — a file-type alone is not a design-doc read."""
    assert _consult_seen({"path": "family/letters", "glob": "*.md"}) is False
