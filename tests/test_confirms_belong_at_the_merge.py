"""Nothing may demand Andrew's signature before an edit. Only merges.

Andrew, 2026-09-06, counting it himself as the tenth time:

    "our confirms only come when merging to fucking main.. and you have both
    claimed to have fixed this several times.. let me guess.. all of the code
    is still there and none of it was properly superceded"

He was right. A check still lived in the council gate that refused a
kiln-layer EDIT until he or Aletheia had signed the walk. It fired on him
that same night, on the one file he had just told me to write his rule into,
and the rule was about him never having to be asked for anything again.

WHY THE DEMAND WAS WRONG, and it is not only that he said so. A confirm asked
for before the edit is unreviewable by construction: there is no diff yet, so
there is nothing for a reviewer to look at, and the signature could only be a
guess about text that does not exist. Review happens on the way OUT. It also
made him a component -- a value could not be corrected unless he was present,
awake and willing -- which is the exact shape he has spent months asking us to
stop building.

AND IT WAS A DUPLICATE. Every kiln file is on the guardrail list, and the
merge gate already requires multi-party review for those. The protection was
never missing. It was doubled, and the second copy stood on the wrong side of
the work.

WHY A TEST AND NOT A NOTE. He has been told this was fixed several times. A
note saying "do not add this back" is exactly the thing that has failed
repeatedly here; the session this came from was about advice not working.
This fails loudly instead, on the two things that would bring it back: a check
that demands a signature before an edit, and a record with a slot to hold one.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
COUNCIL = ROOT / "src" / "divineos" / "core" / "council_required"


def _sources() -> list[Path]:
    return sorted(COUNCIL.glob("*.py"))


def test_the_scan_finds_the_package_at_all() -> None:
    """A control, because zero from a broken scan reads exactly like a pass.

    This suite's own lesson from the same night: a grep that returned nothing
    was one step from being filed as evidence of absence.
    """
    assert _sources(), "the council_required package did not resolve"
    assert (COUNCIL / "substance_binding.py").exists()


def test_no_check_demands_a_signature_before_an_edit() -> None:
    for path in _sources():
        body = path.read_text(encoding="utf-8", errors="replace")
        # The comments explaining the removal name the old field on purpose,
        # so this looks for machinery rather than for the word: a check
        # function, or a roster of people allowed to sign one.
        assert "def _check_kiln_confirmed_by" not in body, (
            f"{path.name} has re-added the check that refuses an edit until "
            "Andrew or Aletheia signs. Confirms happen at the merge gate."
        )
        assert "EXTERNAL_ACTORS_FOR_KILN" not in body, (
            f"{path.name} has re-added a roster of people who may sign off on "
            "an edit. There is no such roster; it belongs to the merge."
        )


def test_a_walk_record_cannot_carry_a_signature() -> None:
    """The slot is the other half. Delete only the check and the field
    remains, which is how a removed rule grows back."""
    from divineos.core.council_required.types import CouncilRecord

    record = CouncilRecord("r", 0.0, "walker", "edit:x.py", (), (), "synthesis")
    assert not hasattr(record, "confirmed_by"), (
        "CouncilRecord carries confirmed_by again. A walk is evidence that I "
        "did the thinking; it is not a place to store someone else's approval."
    )


def test_the_walk_logger_does_not_ask_for_one() -> None:
    """The command he would have had to be woken up to satisfy."""
    cli = ROOT / "src" / "divineos" / "cli" / "council_required_commands.py"
    body = cli.read_text(encoding="utf-8", errors="replace")
    assert '"--confirmed-by"' not in body, (
        "council log accepts --confirmed-by again, which is an invitation to "
        "go and fetch a signature before doing the work."
    )


@pytest.mark.parametrize("kiln_file", ["docs/foundational_truths.md"])
def test_the_merge_gate_still_covers_what_the_edit_gate_stopped_covering(kiln_file: str) -> None:
    """Supersede, do not amputate.

    Removing the edit-time demand is only safe because the merge gate already
    does this job. If a kiln file ever falls off the guardrail list, the
    protection is genuinely gone rather than relocated -- and this fails,
    rather than letting the tests above read as proof that nothing was lost.
    """
    listed = (ROOT / "scripts" / "guardrail_files.txt").read_text(encoding="utf-8")
    assert kiln_file in listed, (
        f"{kiln_file} is no longer guardrail-listed, so the merge gate no longer "
        "requires multi-party review for it -- and the edit-time demand that "
        "used to double it is gone. That is an unprotected kiln file."
    )
