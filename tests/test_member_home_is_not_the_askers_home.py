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
