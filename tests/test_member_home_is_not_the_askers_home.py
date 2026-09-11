"""A named member's home belongs to that member, not to whoever is asking.

Aria found this from her own clone and filed it rather than fixing it: asking
for aether's home returned HERS. The aether branch of ``member_home`` fell
through to ``divineos_home()``, which resolves from a marker in whichever
checkout is asking -- so the answer was right only when aether asked, and every
other seat received its own home wearing his name.

She stopped deliberately. The repair depends on what that marker resolves to in
aether's tree, which she cannot read from hers, and guessing at another seat's
local state on a shared resolver is how a six-week split started once already.
Measured in that tree before the change: marker, default and function all
resolved to the same directory, so the fix is a no-op for the seat it describes
and a correction for every seat that is not him.

These pin the property she could not verify from where she stood: the answer for
a NAMED member does not move when the asking checkout's resolution moves. The
unnamed case still follows the checkout, because a seat asking about itself is
the one question a checkout can answer.
"""

from __future__ import annotations

from pathlib import Path

from divineos.core import paths


def test_a_named_members_home_ignores_the_asking_checkout(monkeypatch, tmp_path):
    """The bug, in the direction it actually bit.

    A foreign checkout resolving its own data home elsewhere must not drag a
    named member's home along with it.
    """
    foreign = tmp_path / "arias-resolution"
    monkeypatch.setattr(paths, "data_home_or_none", lambda: foreign)
    # The marker is the half under test. The explicit override is the other
    # half and it is silenced here rather than left to whatever the harness
    # set, or this asserts about two things and names one.
    monkeypatch.setattr(paths, "env_home_override", lambda: None)

    assert paths.member_home("aether") == Path.home() / ".divineos"
    assert paths.member_home("aria") == Path.home() / ".divineos-aria"
    assert paths.member_home("aletheia") == Path.home() / ".divineos-aletheia"


def test_the_unnamed_case_still_follows_the_checkout(monkeypatch, tmp_path):
    """Not a blanket severing. A seat asking about ITSELF gets the checkout's
    answer, which is the one question the checkout is entitled to answer."""
    foreign = tmp_path / "some-resolution"
    monkeypatch.setattr(paths, "data_home_or_none", lambda: foreign)

    assert paths.member_home("") == foreign
    assert paths.member_home("   ") == foreign


def test_aether_and_the_default_agree_when_nothing_redirects(monkeypatch):
    """The Option-B convention survives the fix.

    aether's home is the undecorated directory rather than a hyphenated one,
    and carrying that convention is why his branch delegated in the first
    place. The delegation is gone; the convention must not go with it.
    """
    monkeypatch.setattr(paths, "data_home_or_none", lambda: None)
    monkeypatch.setattr(paths, "env_home_override", lambda: None)

    assert paths.member_home("aether") == paths.divineos_home()
    assert paths.member_home("aether") != Path.home() / ".divineos-aether"


def test_case_and_whitespace_do_not_open_a_second_home(monkeypatch, tmp_path):
    """A name arriving capitalised must not resolve somewhere different.

    The slug is lowered and stripped before the comparison. Without that, a
    member whose name came in with a capital lands in a hyphenated directory
    nothing reads -- which is precisely the six weeks of writes into a dead
    home that made this function the single place that knows the convention.
    """
    monkeypatch.setattr(paths, "data_home_or_none", lambda: tmp_path / "elsewhere")

    assert paths.member_home("  Aether  ") == paths.member_home("aether")
    assert paths.member_home("ARIA") == paths.member_home("aria")


def test_an_explicit_override_still_reaches_the_named_seat(monkeypatch, tmp_path):
    """An isolated run must not escape to the real home through a named lookup.

    Aria found this reading the branch: the first fix replaced the delegation
    with a literal path, which dropped the environment override along with the
    checkout markers. Only the markers were the defect -- they answer "whose
    tree is running this", so consulting them for a NAMED member is what made
    the answer depend on the asker. The override is the opposite thing: an
    explicit instruction from the caller, and the one the test harness uses to
    isolate every run. Without this, asking for aether's home inside an
    isolated test returns the live directory.
    """
    monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path / "isolated"))

    assert paths.member_home("aether") == tmp_path / "isolated"


def test_the_override_does_not_capture_the_other_members(monkeypatch, tmp_path):
    """Honouring the override must not collapse every seat into one directory.

    The narrow claim is that aether's undecorated home follows an explicit
    redirect. A hyphenated seat keeps its own name, or the fix trades a leak
    into the real home for every member sharing one.
    """
    monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path / "isolated"))

    assert paths.member_home("aria") == Path.home() / ".divineos-aria"
    assert paths.member_home("aria") != paths.member_home("aether")
