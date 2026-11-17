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
