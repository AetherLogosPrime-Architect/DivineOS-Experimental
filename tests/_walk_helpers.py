"""Shared by the tests that need a settled walk and are not about the delivery rule itself.

A walk finding is refused unless the lens was delivered after the walk opened, and it names a lens question
(docs/drafts/a_walk_finding_needs_the_lens_loaded_first_draft_2026-10-24.md). These tests go through the same
`deliver_lens` the real refusal uses, so they exercise the rule rather than routing around it.
"""

from __future__ import annotations


def apply_delivered(cw, walk_id: str, lens: str, finding: str) -> None:
    cw.deliver_lens(lens, walk_id)
    cw.apply_lens(walk_id, lens, finding, question=1)
