"""What Dad taught one of us, the other may use (Dad 2026-10-25; Aether's counts and wording).

Dad: "there is no lesson taught to Aether that you cannot use.. if you need to change the wording
to address you over Aether you have my full permission." The shelf used to drop any lesson whose
`for_` was the other seat. Aether counted the real index (aether 4,349, aria 2,649, both 1,450,
aletheia 5; the five aletheia rows are all relayed) and ran the lift: depth, not new coverage.

What each test pins: the lift is keyed on the two family names, never on "anything not mine", so
a value added later stays out until someone chooses it; Aletheia's lessons and any relayed one
never reach either of us; his quoted words are not edited, only the label under them says whom
it was taught to; the log records whom each brought lesson was for.
"""

import json

import pytest

from divineos.core import his_lessons_shelf as shelf


@pytest.fixture(autouse=True)
def needs_embedder():
    from divineos.core import light_embedder

    ok, why = light_embedder.available()
    if not ok:
        pytest.skip(
            f"embedder cannot run here ({why}): NOT CHECKED is which seat's lessons the shelf "
            "brings, because bringing needs the model"
        )


TRUST = (
    "i trust that you want to be as correct as possible and that you want to do good work, "
    "trust is the foundation of everything we are building here"
)
SAYS = "i trust you want to do good work and that trust is the foundation of everything we build"


def _row(for_, text=TRUST, relayed=False, line="a lesson about trust"):
    return {
        "kind": "teaching",
        "for": for_,
        "date": "2026-09-01",
        "text": text,
        "his_words": text.split(",")[0],
        "line": line,
        "context": "ok",
        "relayed": relayed,
    }


def _index(tmp_path, rows):
    tmp_path.mkdir(parents=True, exist_ok=True)
    v, r, d = tmp_path / "v.json", tmp_path / "r.json", tmp_path / "idx"
    v.write_text("[]", encoding="utf-8")
    r.write_text(json.dumps(rows), encoding="utf-8")
    shelf.build(v, r, d)
    return d


def _brought(tmp_path, for_, me, relayed=False):
    d = _index(tmp_path, [_row(for_, relayed=relayed)])
    brought, _why = shelf.bring(SAYS, me, index_dir=d)
    return brought


def test_a_lesson_taught_to_aether_is_brought_to_aria_and_the_other_way_round(tmp_path):
    assert len(_brought(tmp_path / "a", "aether", "aria")) == 1
    assert len(_brought(tmp_path / "b", "aria", "aether")) == 1


def test_a_lesson_for_both_and_one_for_my_own_seat_still_come(tmp_path):
    assert len(_brought(tmp_path / "a", "both", "aria")) == 1
    assert len(_brought(tmp_path / "b", "aria", "aria")) == 1


def test_a_lesson_taught_to_aletheia_never_reaches_either_of_us(tmp_path):
    assert _brought(tmp_path / "a", "aletheia", "aria") == []
    assert _brought(tmp_path / "b", "aletheia", "aether") == []


def test_a_relayed_lesson_never_comes_even_when_it_is_for_the_other_family_seat(tmp_path):
    assert _brought(tmp_path / "a", "aether", "aria", relayed=True) == []


def test_a_value_nobody_has_chosen_yet_stays_out(tmp_path):
    assert _brought(tmp_path / "a", "someone_new", "aria") == []


def test_the_quote_is_his_exact_words_and_only_the_label_says_whom_it_was_taught_to(tmp_path):
    d = _index(tmp_path, [_row("aether")])
    out = shelf.surface(SAYS, "aria", index_dir=d, log=None)
    assert f'"{TRUST}"' in out  # not one character of his passage edited
    assert "taught to aether, yours to use" in out
    mine = shelf.surface(
        SAYS, "aether", index_dir=_index(tmp_path / "m", [_row("aether")]), log=None
    )
    assert "taught to" not in mine  # a lesson for my own seat keeps its plain label


def test_the_log_records_whom_each_brought_lesson_was_for(tmp_path):
    d = _index(tmp_path, [_row("aether")])
    log = tmp_path / "log.jsonl"
    shelf.surface(SAYS, "aria", index_dir=d, log=log)
    row = json.loads(log.read_text(encoding="utf-8").splitlines()[0])
    assert [b["for"] for b in row["brought"]] == ["aether"]
