"""A confirm titled in the singular is still a signature.

FOUND IN ANGER 2026-09-19. Two rounds were filed with findings titled
"CONFIRM -- ...", both carrying the reviewed tree hash in full in their
description. The stamp tool reported, twice:

    Round <id> names no tree in any CONFIRMS finding, so nothing here
    proves it covers tree <hash>.

Both sentences were false about the round and true about the selector: three
rungs tested for the literal substring "confirms", none matched, and every one
of them examined zero findings before reporting an absence. The tool whose
entire job is proving a review happened answered a narrower question than the
one asked, and printed the answer as though it were the wide one.

Aria ruled this the first of three broken doors to repair, on the grounds that
the other two merely obstructed while this one answered wrong, and that every
remaining branch in the queue passes through it.

WHY THE EXISTING SUITE DID NOT CATCH IT, which is the part worth carrying.
tests/test_stamp_ready_tree_binding.py covers the extraction thoroughly --
abbreviated forms, full forms, round ids mistaken for trees, branch names. Every
fixture in it spells the word in the plural, because it was written from the
same understanding that produced the code. Thorough coverage of the shape the
author already had in mind is not coverage of the shape they did not.

The tests below hold both edges. A signature must be recognised in any ordinary
form; a refusal must not be recognised as one however often it says the word.
"""

from __future__ import annotations

from divineos.cli.stamp_ready_command import _claims_a_confirm


class TestASignatureIsRecognisedInAnyOrdinaryForm:
    """The live case, plus the forms a reviewer actually writes."""

    def test_the_singular_form_that_shipped_and_was_missed(self) -> None:
        # Verbatim shape of the title that went unread twice.
        assert _claims_a_confirm("CONFIRM -- anchors exact and the tree matches")

    def test_the_plural_form_that_always_worked(self) -> None:
        assert _claims_a_confirm("CONFIRMS on both, anchors verified")

    def test_the_past_tense_a_reviewer_writes_in_prose(self) -> None:
        assert _claims_a_confirm("I have confirmed the seat comparison myself")

    def test_case_does_not_decide_whether_a_signature_counts(self) -> None:
        assert _claims_a_confirm("confirm")
        assert _claims_a_confirm("Confirm")
        assert _claims_a_confirm("CONFIRM")


class TestARefusalIsNotASignatureHoweverOftenItSaysTheWord:
    """The edge the narrow form was protecting, which must survive widening.

    Refusing takes more words than agreeing, so a withheld clearance says the
    word more often than a real one does. That is why the bound sits at word
    edges rather than being left as an open substring.
    """

    def test_a_negated_form_is_not_a_signature(self) -> None:
        assert not _claims_a_confirm("this branch is unconfirmed at this time")

    def test_a_withheld_clearance_is_not_a_signature(self) -> None:
        assert not _claims_a_confirm("confirmation withheld pending a full read")

    def test_text_that_never_speaks_of_confirming_is_not_a_signature(self) -> None:
        assert not _claims_a_confirm("I read three files and have notes")

    def test_the_word_inside_a_longer_word_does_not_count(self) -> None:
        assert not _claims_a_confirm("reconfirmable")


class TestTheSpecificationHasOneHomeRatherThanThree:
    """Three rungs failed identically because each carried its own copy.

    This regression matters more than any single wording: a reader repairing
    the rung that bit them would have fixed a third of the defect, and nothing
    at any of the three sites named the other two.
    """

    def test_no_rung_carries_its_own_literal_substring_test(self) -> None:
        from pathlib import Path

        import divineos.cli.stamp_ready_command as mod

        source = Path(mod.__file__).read_text(encoding="utf-8")
        assert '"confirms" not in' not in source, (
            "a rung has grown its own private copy of the signature test again; "
            "call _claims_a_confirm instead so every rung changes together"
        )
