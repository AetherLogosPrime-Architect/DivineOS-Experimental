"""Station four buys a COLD READ, and co-authorship is what spends it.

Aria found the defect: the station globbed for HER letters for every branch,
with no field anywhere for who wrote the thing. On my branches that was real
external review; on hers it asked the author to certify her own reading and
would have accepted it. Her pairing is the sharp part -- station two refuses
the other seat's work because the author must think for herself, and this
station accepted the author's own reading because it never asked who the
author was. Same board, same principle, opposite errors, both from one missing
fact.

I argued the third state might honestly be a pass, since two vantages were in
a co-authored branch. She refuted it, and the refutation is now the docstring
of the thing: co-authorship supplies *the author thought this through* and
STRUCTURALLY DENIES *someone looked at the finished whole from outside it*.
The more each seat built, the less either can arrive cold.

So the load-bearing tests here are the two that REFUSE, plus the one proving
an undeclared owner is not a failure. A station that guessed an owner from a
branch name would pass everything below except those.

Companion to tests/test_build_flow_aria_declaration.py, which pins the
reading-declaration parsing this reuses.
"""

from __future__ import annotations

import pytest

from divineos.core.build_flow import Status, check_cold_read_station, declared_owner

BRANCH = "fix/a-thing"


@pytest.fixture
def dirs(tmp_path):
    letters = tmp_path / "letters"
    owners = tmp_path / "owners"
    letters.mkdir()
    owners.mkdir()
    return letters, owners


def _own(owners, branch, *seats):
    (owners / f"{branch.replace('/', '__')}.txt").write_text(
        f"Owner: {', '.join(seats)}\n", encoding="utf-8"
    )


def _reading(letters, reviewer, branch):
    (letters / f"{reviewer}-to-someone-2026-09-12-a-letter.md").write_text(
        f"# a letter\n\n**Reading:** {branch}\n\nbody\n", encoding="utf-8"
    )


def test_the_owner_cannot_certify_their_own_reading(dirs):
    """The inversion Aria found, stated as the refusal it now is."""
    letters, owners = dirs
    _own(owners, BRANCH, "aria")
    _reading(letters, "aria", BRANCH)
    r = check_cold_read_station(BRANCH, letters, owners)
    assert r.status is Status.MISSING, "the author's own reading must not satisfy a cold read"


def test_the_other_seat_satisfies_it(dirs):
    letters, owners = dirs
    _own(owners, BRANCH, "aria")
    _reading(letters, "aether", BRANCH)
    assert check_cold_read_station(BRANCH, letters, owners).status is Status.SATISFIED


def test_it_runs_in_both_directions(dirs):
    """Not a station about Aria. A station about whoever did not write it."""
    letters, owners = dirs
    _own(owners, BRANCH, "aether")
    _reading(letters, "aether", BRANCH)
    assert check_cold_read_station(BRANCH, letters, owners).status is Status.MISSING
    _reading(letters, "aria", BRANCH)
    assert check_cold_read_station(BRANCH, letters, owners).status is Status.SATISFIED


def test_a_co_authored_branch_is_refused_and_says_why(dirs):
    """The state I wanted to be a pass, and Aria was right that it is not.

    Both seats declared, both seats built, so nobody can arrive cold. The
    station must say the product is out of stock rather than pick a victim.
    """
    letters, owners = dirs
    _own(owners, BRANCH, "aether", "aria")
    _reading(letters, "aria", BRANCH)
    _reading(letters, "aether", BRANCH)
    r = check_cold_read_station(BRANCH, letters, owners)
    assert r.status is Status.MISSING
    assert "NO SEAT IS EXTERNAL" in r.detail
    assert "aether" in r.detail and "aria" in r.detail


def test_an_undeclared_owner_is_not_a_failure(dirs):
    """could-not-check, and the wording must not read as unread.

    Every branch open today is in this state, because nothing has ever
    declared ownership. Reporting that as MISSING would be a verdict about
    whether anyone read the work, which is a different question entirely.
    """
    letters, owners = dirs
    _reading(letters, "aria", BRANCH)
    r = check_cold_read_station(BRANCH, letters, owners)
    assert r.status is Status.CANNOT_CHECK
    assert "declared ownership" in r.detail


def test_ownership_is_never_inferred_from_the_branch_name(dirs):
    """Measured 2026-09-12: a branch named for one seat carried commits from
    both, and a neutrally-named one was written entirely by the other. The
    prefix is a naming convention and the board must not read it as a fact.
    """
    letters, owners = dirs
    _reading(letters, "aria", "aria/her-branch")
    r = check_cold_read_station("aria/her-branch", letters, owners)
    assert r.status is Status.CANNOT_CHECK, (
        "a branch prefixed with a seat name must still require a declaration"
    )


def test_an_unreadable_owner_store_is_not_an_absent_owner(dirs):
    letters, owners = dirs
    state, _ = declared_owner(BRANCH, owners / "gone")
    assert state == "cannot-read"
    assert state != "undeclared"


def test_a_file_naming_no_seat_reads_as_undeclared(dirs):
    """Garbage in the field is not a declaration, and is not contested either."""
    _letters, owners = dirs
    (owners / f"{BRANCH.replace('/', '__')}.txt").write_text("Owner: nobody\n", encoding="utf-8")
    assert declared_owner(BRANCH, owners)[0] == "undeclared"
