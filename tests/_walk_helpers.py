"""Shared by the tests that need a settled walk and are not about the delivery rule itself.

A walk finding is refused unless the lens was delivered after the walk opened, it names a lens question
(docs/drafts/a_walk_finding_needs_the_lens_loaded_first_draft_2026-10-24.md), and it shows CONTACT with the lens's own
methodology text (docs/drafts/a_walk_finding_must_show_contact_with_the_template_draft_2026-11-12.md). These tests go
through the same `deliver_lens` the real refusal uses and write a finding that really quotes the lens, so they exercise
the rules rather than routing around them.
"""

from __future__ import annotations

import re


def contact_finding(cw, lens: str, finding: str) -> str:
    """The finding with a real four-word quote from one of the lens's own methodologies, named in square brackets."""
    from divineos.core.council.engine import get_council_engine

    wisdom = get_council_engine().get_expert(lens)
    for m in wisdom.core_methodologies:
        for unit in (m.description, *(getattr(m, "steps", None) or [])):
            tokens = re.findall(r"\S+", unit)
            for i in range(len(tokens) - cw.CONTACT_RUN_WORDS + 1):
                quote = " ".join(tokens[i : i + cw.CONTACT_RUN_WORDS])
                if (
                    len(cw._contact_words(quote)) == cw.CONTACT_RUN_WORDS
                ):  # no bare dash or bullet in the window
                    return f'[{m.name}] "{quote}" {finding}'
    raise AssertionError(f"no unit long enough on {lens} to quote from")


def apply_delivered(cw, walk_id: str, lens: str, finding: str) -> None:
    cw.deliver_lens(lens, walk_id)
    cw.apply_lens(walk_id, lens, contact_finding(cw, lens, finding), question=1)


def close_with_breaking_round(cw, walk_id: str, repo=None):
    """Close a walk that is FOR files after giving it the breaking round the close now requires.

    Dad, 2026-11-13: a walk is not closed until it has been broken on purpose (the Breaker plus at least two other
    scrutiny lenses). These tests are about other rules, so they supply the round the same honest way a person would:
    add the lenses with a reason, walk them, then close. The rule itself is pinned in
    tests/test_a_scoped_walk_does_not_close_without_a_breaking_round.py.
    """
    present = {row["lens"] for row in cw.status(walk_id)["lenses"]}
    for name in (cw.REQUIRED_BREAKER, "Popper", "Schneier"):
        if name not in present:
            cw.add_lens(
                walk_id,
                name,
                "added so the breaking round exists; a free addition would be a picked council",
            )
    for lens in cw.status(walk_id)["open_lenses"]:
        apply_delivered(
            cw,
            walk_id,
            lens,
            "a finding written so the walk can close in a test about something else",
        )
    return cw.close_walk(walk_id, repo=repo) if repo is not None else cw.close_walk(walk_id)
