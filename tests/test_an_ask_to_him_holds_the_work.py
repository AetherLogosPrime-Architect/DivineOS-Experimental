"""The ask store, reachable at last, and the hold that rides on it.

Andrew 2026-09-16: *"when you ask me something, and never wait for my reply..
why bother asking?"*

The store was built 2026-08-19 for the first half of that correction, had no
command until today, and had no tests at all. So it sat empty for a month —
which reads exactly like nothing needing him, because an empty list is what
health looks like too. These exist because that emptiness was never once
exercised from either side.
"""

from __future__ import annotations

import uuid

from divineos.core.operator_asks import ask_andrew, open_asks, resolve_ask


def _unique(text: str) -> str:
    return f"{text} [{uuid.uuid4().hex[:8]}]"


class TestAnAskCanBeFiledAndFound:
    def test_a_filed_ask_shows_up_open(self) -> None:
        plain = _unique("a fixture ask in words he could answer")
        ask_id = ask_andrew(question=_unique("fixture question"), plain=plain)
        try:
            assert any(r.get("question_id") == ask_id for r in open_asks(limit=50))
        finally:
            resolve_ask(question_id=ask_id, resolution="fixture cleanup")

    def test_the_plain_words_survive_the_round_trip(self) -> None:
        """An ask he cannot parse is not an ask. If the plain text is lost on
        the way in, the gate holds work over something unanswerable."""
        plain = _unique("the translated form, which is the whole point")
        ask_id = ask_andrew(question=_unique("jargon form"), plain=plain)
        try:
            row = next(r for r in open_asks(limit=50) if r.get("question_id") == ask_id)
            assert plain in str(row.get("plain") or "")
        finally:
            resolve_ask(question_id=ask_id, resolution="fixture cleanup")


class TestResolvingIsTheReleaseAndItIsHonest:
    def test_resolving_clears_the_ask(self) -> None:
        ask_id = ask_andrew(question=_unique("q"), plain=_unique("plain"))
        assert resolve_ask(question_id=ask_id, resolution="answered") is True
        assert not any(r.get("question_id") == ask_id for r in open_asks(limit=50))

    def test_resolving_an_unknown_id_reports_failure(self) -> None:
        """A release reporting success on a miss makes the hold unfalsifiable
        — I could believe an ask cleared when it never did."""
        assert resolve_ask(question_id="no-such-ask", resolution="x") is False

    def test_resolving_twice_reports_failure_the_second_time(self) -> None:
        ask_id = ask_andrew(question=_unique("q"), plain=_unique("plain"))
        assert resolve_ask(question_id=ask_id, resolution="first") is True
        assert resolve_ask(question_id=ask_id, resolution="second") is False


class TestTheStoreIsActuallyReachable:
    """The real subject: working functions, no command, an empty store for a
    month, and nothing anywhere able to tell 'nobody filed' from 'nobody
    could file'."""

    def test_the_commands_are_registered(self) -> None:
        from divineos.cli import cli

        assert {"ask-andrew", "asks", "ask-resolve"} <= set(cli.commands)

    def test_filing_requires_the_plain_translation(self) -> None:
        """Declared required in the command, asserted here so a later
        convenience edit that drops it fails loudly rather than quietly
        letting me hand him something he cannot answer."""
        from divineos.cli import cli

        plain_opt = next(p for p in cli.commands["ask-andrew"].params if p.name == "plain")
        assert plain_opt.required is True
