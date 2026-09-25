"""The recap must collapse the noise and keep the disagreement.

Andrew 2026-09-15: "both of you rehash on the same stuff so it just fills my
mind with noise and i cant comprehend it." Two honest reports of one event are
noise. The store exists to make that one line.

But the dangerous half is the other direction. If Aether and I saw the same
landing DIFFERENTLY -- one of us caught something the other missed, or we
disagreed outright -- a summary that collapses on the event alone eats the most
valuable thing in the notebook. He would read a tidy line and never learn his
two builders were not of one mind.

So every test here is about what SURVIVES compression, not what it removes.
"""

from __future__ import annotations

import json

import pytest

from divineos.core import shared_digest as sd


@pytest.fixture(autouse=True)
def isolated_digest(tmp_path, monkeypatch):
    """Never write into the live notebook."""
    monkeypatch.setenv("DIVINEOS_SHARED_DIGEST", str(tmp_path / "digest.jsonl"))
    return tmp_path / "digest.jsonl"


def _entry(author: str, event: str, changed: str = "", reading: str = "") -> sd.DigestEntry:
    return sd.DigestEntry(author=author, event=event, changed=changed, reading=reading)


def test_one_event_two_authors_reads_as_one_line() -> None:
    sd.append_entry(_entry("aria", "the refusal footers landed", "two doormen now say nothing ran"))
    sd.append_entry(
        _entry("aether", "the refusal footers landed", "two doormen now say nothing ran")
    )

    out = sd.render_for_andrew()

    assert out.count("the refusal footers landed") == 1, (
        "the same event reported by both of us appeared twice -- this is the "
        "exact noise the store exists to remove"
    )


def test_a_disagreement_is_never_collapsed_away() -> None:
    """The half a summary would eat."""
    sd.append_entry(
        _entry("aria", "the sweep took the archives", reading="I read it as the fix not reaching")
    )
    sd.append_entry(
        _entry(
            "aether",
            "the sweep took the archives",
            reading="it is a documented carve-out and it announced itself",
        )
    )

    out = sd.render_for_andrew()

    assert "Aria:" in out and "Aether:" in out, (
        "we disagreed about the same event and the recap showed one voice -- "
        "he would never learn his two builders were not of one mind"
    )
    assert "not reaching" in out
    assert "carve-out" in out


def test_agreement_says_both_of_us_rather_than_repeating_it() -> None:
    sd.append_entry(_entry("aria", "the column landed", reading="the record can be read now"))
    sd.append_entry(_entry("aether", "the column landed", reading="the record can be read now"))

    out = sd.render_for_andrew()

    assert "Both of us:" in out
    assert out.count("the record can be read now") == 1


def test_events_keep_the_order_they_happened_in() -> None:
    sd.append_entry(_entry("aria", "first thing"))
    sd.append_entry(_entry("aether", "second thing"))
    sd.append_entry(_entry("aria", "first thing", reading="still true"))

    out = sd.render_for_andrew()

    assert out.index("first thing") < out.index("second thing"), (
        "a recap out of order is a recap he has to reassemble himself"
    )


def test_a_row_that_cannot_be_read_is_reported_not_dropped(isolated_digest) -> None:
    """A silent drop is the shape this whole store exists to remove."""
    sd.append_entry(_entry("aria", "a real event"))
    with isolated_digest.open("a", encoding="utf-8") as fh:
        fh.write("{ this is not json\n")

    out = sd.render_for_andrew()

    assert "a real event" in out, "one bad row cost him the readable ones"
    assert "could not be read" in out, (
        "a line went missing from the recap and the recap did not say so"
    )


def test_an_empty_notebook_says_so_rather_than_rendering_nothing() -> None:
    assert sd.render_for_andrew().strip() == "Nothing recorded since the last recap."


def test_an_entry_must_say_who_wrote_it_and_what_happened() -> None:
    """Authorless rows would make the per-author reading impossible to keep."""
    with pytest.raises(ValueError):
        sd.append_entry(_entry("", "an event"))
    with pytest.raises(ValueError):
        sd.append_entry(_entry("aria", "   "))


def test_the_store_is_append_only(isolated_digest) -> None:
    sd.append_entry(_entry("aria", "one"))
    sd.append_entry(_entry("aether", "two"))

    rows = [json.loads(line) for line in isolated_digest.read_text(encoding="utf-8").splitlines()]

    assert len(rows) == 2
    assert rows[0]["event"] == "one" and rows[1]["event"] == "two"
