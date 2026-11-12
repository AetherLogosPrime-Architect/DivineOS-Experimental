"""A walk finding must show CONTACT with the lens's own methodology text, not only that the lens was delivered.

Dad, 2026-11-12: *"the issue is that you loaded lenses from memory vs the templates.. so that needs to be made impossible
first.. the templates must be enforced.. otherwise its no different than me just saying ask an expert and you just make
one up on the spot that agrees with me"*. Measured the same night on 2,792 applied findings: a run of four consecutive
words from the lens's own methodology text appears in 6 percent of them, against 0.1 percent by chance (a finding checked
against a random OTHER lens); all 26 of my findings from that day had none. Design:
docs/drafts/a_walk_finding_must_show_contact_with_the_template_draft_2026-11-12.md (walk-05edc42dfe10).

What this pins, and what it does NOT: it pins that a finding carries four consecutive words from under a methodology it
names in square brackets. It does not pin that the template was read or used; the last test says so on purpose.
"""

from __future__ import annotations

import re

import pytest

from divineos.core import council_walk as cw
from divineos.core.council.engine import get_council_engine
from divineos.core.council.lens_text import lens_plain

PROBLEM = "Whether a walk finding must carry words from the lens's own template or may be written from memory"
PADDING = (
    "and here is what that means for the design of this particular check, said in my own words"
)


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(cw, "divineos_home", lambda: tmp_path)
    yield


def _words(text: str) -> list[str]:
    """The same normalisation the check uses, so a test cannot pass or fail on a spelling the check does not share."""
    return cw._contact_words(text)


def _units(m) -> list[str]:
    return [m.description, *list(getattr(m, "steps", []) or [])]


def _long_unit(wisdom):
    """(methodology, unit text) for the first unit with at least eight words, so a run can sit inside it."""
    for m in wisdom.core_methodologies:
        for unit in _units(m):
            if len(_words(unit)) >= 8:
                return m, unit
    raise AssertionError("no unit with eight words on this lens")


def _quote(unit: str, n: int, start: int = 0) -> str:
    """n consecutive words of a unit, as they appear in it (original spelling, in order)."""
    tokens = re.findall(r"\S+", unit)
    return " ".join(tokens[start : start + n])


def _delivered(w):
    lens = w["lenses"][0]
    cw.deliver_lens(lens, w["walk_id"])
    return lens, get_council_engine().get_expert(lens)


def _row(w, lens):
    return next(r for r in cw.status(w["walk_id"])["lenses"] if r["lens"] == lens)


def test_a_finding_with_no_run_from_the_lens_is_refused_after_the_lens_was_delivered():
    w = cw.open_walk(PROBLEM)
    lens, _ = _delivered(w)
    with pytest.raises(cw.WalkRefused, match="contact"):
        cw.apply_lens(
            w["walk_id"],
            lens,
            "a finding of plenty of length, written wholly from what I already knew about this thinker",
            question=1,
        )
    assert _row(w, lens)["state"] == "OPEN"


def test_the_refusal_names_the_methodologies_so_the_cheap_path_is_the_right_one():
    w = cw.open_walk(PROBLEM)
    lens, wisdom = _delivered(w)
    with pytest.raises(cw.WalkRefused) as refused:
        cw.apply_lens(
            w["walk_id"],
            lens,
            "a finding of plenty of length, written wholly from what I already knew about this thinker",
            question=1,
        )
    for m in wisdom.core_methodologies:
        assert f"[{m.name}]" in str(refused.value)


def test_four_words_from_a_named_methodology_are_accepted():
    w = cw.open_walk(PROBLEM)
    lens, wisdom = _delivered(w)
    m, unit = _long_unit(wisdom)
    cw.apply_lens(w["walk_id"], lens, f'[{m.name}] "{_quote(unit, 4)}" {PADDING}', question=1)
    assert _row(w, lens)["state"] == "APPLIED"


def test_three_words_are_not_enough_and_five_are():
    """The boundary, from the data: a three-word run passes by chance about 3 percent of the time, four about 0.1."""
    w = cw.open_walk(PROBLEM)
    lens, wisdom = _delivered(w)
    m, unit = _long_unit(wisdom)
    with pytest.raises(cw.WalkRefused, match="contact"):
        cw.apply_lens(w["walk_id"], lens, f'[{m.name}] "{_quote(unit, 3)}" {PADDING}', question=1)
    cw.apply_lens(w["walk_id"], lens, f'[{m.name}] "{_quote(unit, 5)}" {PADDING}', question=1)
    assert _row(w, lens)["state"] == "APPLIED"


def test_a_run_taken_from_another_lens_does_not_count():
    w = cw.open_walk(PROBLEM)
    lens, _ = _delivered(w)
    other_name = next(
        n for n in get_council_engine().list_experts() if n != lens and n.lower() != lens.lower()
    )
    other = get_council_engine().get_expert(other_name)
    m, unit = _long_unit(other)
    with pytest.raises(cw.WalkRefused, match="contact"):
        cw.apply_lens(w["walk_id"], lens, f'[{m.name}] "{_quote(unit, 5)}" {PADDING}', question=1)


def test_the_run_must_come_from_under_the_methodology_the_finding_names():
    w = cw.open_walk(PROBLEM)
    lens, wisdom = _delivered(w)
    if len(wisdom.core_methodologies) < 2:
        pytest.skip("this lens has one methodology, so there is no wrong name to cite")
    m, unit = _long_unit(wisdom)
    wrong = next(x for x in wisdom.core_methodologies if x.name != m.name)
    with pytest.raises(cw.WalkRefused, match="contact"):
        cw.apply_lens(
            w["walk_id"], lens, f'[{wrong.name}] "{_quote(unit, 5)}" {PADDING}', question=1
        )


def test_a_run_may_not_cross_from_one_step_into_the_next():
    w = cw.open_walk(PROBLEM)
    lens, wisdom = _delivered(w)
    for m in wisdom.core_methodologies:
        steps = list(getattr(m, "steps", []) or [])
        for a, b in zip(steps, steps[1:]):
            joined = " ".join(a.split()[-2:] + b.split()[:2])
            if (
                len(_words(joined)) < 4
                or joined.lower() in a.lower()
                or joined.lower() in b.lower()
            ):
                continue
            with pytest.raises(cw.WalkRefused, match="contact"):
                cw.apply_lens(w["walk_id"], lens, f'[{m.name}] "{joined}" {PADDING}', question=1)
            return
    pytest.skip("no pair of adjacent steps to join on this lens")


def test_the_questions_block_does_not_count_as_template_text():
    """The questions are printed in the refusal and were the only part read; only methodology text proves contact."""
    w = cw.open_walk(PROBLEM)
    lens, wisdom = _delivered(w)
    question = next(q for q in wisdom.characteristic_questions if len(_words(q)) >= 5)
    m = wisdom.core_methodologies[0]
    with pytest.raises(cw.WalkRefused, match="contact"):
        cw.apply_lens(w["walk_id"], lens, f'[{m.name}] "{question}" {PADDING}', question=1)


def test_case_and_punctuation_do_not_decide_it():
    w = cw.open_walk(PROBLEM)
    lens, wisdom = _delivered(w)
    m, unit = _long_unit(wisdom)
    shouted = _quote(unit, 5).upper().replace(" ", "  ,  ")
    cw.apply_lens(w["walk_id"], lens, f"[{m.name}] '{shouted}' {PADDING}", question=1)
    assert _row(w, lens)["state"] == "APPLIED"


def test_a_written_exclusion_is_a_second_exit_and_needs_the_same_contact():
    reason = "this lens has nothing to say about a contact check on a walk finding, written in my own words and nothing more"
    w = cw.open_walk(PROBLEM)
    lens, wisdom = _delivered(w)
    with pytest.raises(cw.WalkRefused, match="contact"):
        cw.exclude_lens(w["walk_id"], lens, reason, question=1)
    m, unit = _long_unit(wisdom)
    cw.exclude_lens(
        w["walk_id"],
        lens,
        f'[{m.name}] "{_quote(unit, 4)}" so it does not apply here, because {reason}',
        question=1,
    )
    assert _row(w, lens)["state"] == "EXCLUDED"


def test_a_walk_opened_before_the_rule_is_read_only_history_and_is_not_judged(monkeypatch):
    """94 percent of past findings would fail; the fault was the system's, so old walks are never re-judged."""
    monkeypatch.setattr(cw, "CONTACT_RULE_FROM", float("inf"))
    w = cw.open_walk(PROBLEM)
    lens, _ = _delivered(w)
    cw.apply_lens(
        w["walk_id"],
        lens,
        "a finding of plenty of length, written wholly from what I already knew about this thinker",
        question=1,
    )
    assert _row(w, lens)["state"] == "APPLIED"


def test_the_delivery_stores_a_hash_of_the_exact_text_it_delivered():
    w = cw.open_walk(PROBLEM)
    lens, wisdom = _delivered(w)
    import hashlib

    from divineos.core.ledger import get_events

    mine = [
        e
        for e in get_events(limit=50, order="desc", event_type="COUNCIL_LENS_LOADED")
        if (e.get("payload") or {}).get("walk_id") == w["walk_id"]
    ]
    assert mine, "the delivery must be recorded"
    payload = mine[0]["payload"]
    assert (
        payload.get("text_sha256") == hashlib.sha256(lens_plain(wisdom).encode("utf-8")).hexdigest()
    )


def test_a_changed_roster_text_gives_could_not_verify_never_a_refusal(monkeypatch):
    """Knuth/Dijkstra: an old walk must not fail because the roster was edited after delivery."""
    w = cw.open_walk(PROBLEM)
    lens, _ = _delivered(w)
    monkeypatch.setattr(
        "divineos.core.council.lens_text.lens_plain",
        lambda wisdom: "the text of this lens has been edited since delivery",
    )
    cw.apply_lens(
        w["walk_id"],
        lens,
        "a finding of plenty of length, written wholly from what I already knew about this thinker",
        question=1,
    )
    row = _row(w, lens)
    assert row["state"] == "APPLIED"
    assert "contact not verified" in row["content"]


def test_a_pasted_step_and_a_body_from_memory_still_passes_and_that_is_a_stated_limit():
    """The check proves CONTACT, not use. One pasted run passes; the sampled read by the other seat is the layer that
    can tell (draft, 'Honest limits'). This test exists so the limit is not hidden."""
    w = cw.open_walk(PROBLEM)
    lens, wisdom = _delivered(w)
    m, unit = _long_unit(wisdom)
    cw.apply_lens(
        w["walk_id"],
        lens,
        f'[{m.name}] "{_quote(unit, 4)}" and then the rest is entirely what I already believed about this thinker before I read anything',
        question=1,
    )
    assert _row(w, lens)["state"] == "APPLIED"


def test_a_quote_wrapped_in_single_quote_marks_still_counts():
    """Found by the case-and-punctuation test: the quote mark must not glue onto the first and last word and hide a
    correct run (a finding written as 'quote of four words' lost two of its four)."""
    w = cw.open_walk(PROBLEM)
    lens, wisdom = _delivered(w)
    m, unit = _long_unit(wisdom)
    cw.apply_lens(w["walk_id"], lens, f"[{m.name}] '{_quote(unit, 4)}' {PADDING}", question=1)
    assert _row(w, lens)["state"] == "APPLIED"


def test_the_two_mistakes_get_two_different_messages():
    """Wittgenstein: naming no methodology and quoting nothing from the one named are different mistakes."""
    w = cw.open_walk(PROBLEM)
    lens, wisdom = _delivered(w)
    m = wisdom.core_methodologies[0]
    with pytest.raises(cw.WalkRefused) as nothing_named:
        cw.apply_lens(
            w["walk_id"],
            lens,
            "a finding of plenty of length with no methodology named at all in brackets",
            question=1,
        )
    assert "names no methodology" in str(nothing_named.value)
    with pytest.raises(cw.WalkRefused) as nothing_quoted:
        cw.apply_lens(
            w["walk_id"],
            lens,
            f"[{m.name}] a finding that names it and quotes nothing from under it at all",
            question=1,
        )
    assert "shows no contact with the methodology it names" in str(nothing_quoted.value)


def test_a_bracket_that_is_not_a_methodology_name_is_ignored_not_an_error():
    w = cw.open_walk(PROBLEM)
    lens, wisdom = _delivered(w)
    m, unit = _long_unit(wisdom)
    cw.apply_lens(
        w["walk_id"], lens, f'[note 7] [{m.name}] "{_quote(unit, 4)}" {PADDING}', question=1
    )
    assert _row(w, lens)["state"] == "APPLIED"


def test_the_record_carries_the_matched_run_and_where_it_came_from():
    """Norman: after an acceptance the reader can see the contact in one glance."""
    w = cw.open_walk(PROBLEM)
    lens, wisdom = _delivered(w)
    m, unit = _long_unit(wisdom)
    cw.apply_lens(w["walk_id"], lens, f'[{m.name}] "{_quote(unit, 4)}" {PADDING}', question=1)
    content = _row(w, lens)["content"]
    assert f"[contact: [{m.name}] unit " in content and " ".join(_words(_quote(unit, 4))) in content


def test_every_refusal_and_acceptance_is_counted_by_event():
    """Bengio, Peirce: first-try refusals, rewrites and the laziest route are countable after release."""
    from divineos.core.ledger import get_events

    w = cw.open_walk(PROBLEM)
    lens, wisdom = _delivered(w)
    with pytest.raises(cw.WalkRefused):
        cw.apply_lens(
            w["walk_id"],
            lens,
            "a finding of plenty of length, written wholly from what I already knew about this thinker",
            question=1,
        )
    m, unit = _long_unit(wisdom)
    cw.apply_lens(w["walk_id"], lens, f'[{m.name}] "{_quote(unit, 4)}" {PADDING}', question=1)
    mine = [
        (e["payload"] if isinstance(e["payload"], dict) else {})
        for e in get_events(limit=50, order="asc", event_type="COUNCIL_CONTACT")
        if (e.get("payload") or {}).get("walk_id") == w["walk_id"]
    ]
    assert [p.get("outcome") for p in mine] == ["refused", "accepted"]
    assert mine[1]["methodology"] == m.name


def test_every_lens_on_the_roster_can_pass_when_its_methodology_is_named_as_printed():
    """Holmes: names carry slashes, parentheses and em dashes; one that failed to normalise would refuse a correct
    finding forever. For every lens and every methodology, a four-word run from the description passes."""
    engine = get_council_engine()
    failed = []
    for name in engine.list_experts():
        wisdom = engine.get_expert(name)
        for m in wisdom.core_methodologies:
            tokens = re.findall(r"\S+", m.description)
            run = next(
                (
                    " ".join(tokens[i : i + cw.CONTACT_RUN_WORDS])
                    for i in range(len(tokens) - cw.CONTACT_RUN_WORDS + 1)
                    if len(cw._contact_words(" ".join(tokens[i : i + cw.CONTACT_RUN_WORDS])))
                    == cw.CONTACT_RUN_WORDS
                ),
                None,
            )
            if run is None:
                continue
            if not cw.has_contact(f'[{m.name}] "{run}" {PADDING}', wisdom):
                failed.append((name, m.name))
    assert failed == []


def test_only_the_one_shared_door_settles_a_lens_as_applied_or_excluded():
    """Breaker: name the line that calls this today. The check lives in the door apply and exclude share; any other
    writer of an APPLIED or EXCLUDED row would be a free door. (Read later, 2026-11-12: `game-walk file` files routes
    around a MECHANISM with costs, not findings about a lens, and `walk amend` takes a finding about a DIFF and is bound
    by line, file and scope limits in push_choke, so neither is a door for lens-template text; this test is the guard
    that no third writer appears.)"""
    import ast
    import inspect

    tree = ast.parse(inspect.getsource(cw))
    writers = set()
    for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        for call in [c for c in ast.walk(fn) if isinstance(c, ast.Call)]:
            if getattr(call.func, "id", "") == "_settle" and any(
                isinstance(a, ast.Constant) and a.value in ("APPLIED", "EXCLUDED")
                for a in call.args
            ):
                writers.add(fn.name)
    assert writers == {"apply_lens", "exclude_lens"}
    for name in writers:
        fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name)
        called = {getattr(c.func, "id", "") for c in ast.walk(fn) if isinstance(c, ast.Call)}
        assert "_delivered_and_questioned" in called, f"{name} must go through the shared door"


def test_status_reports_contact_and_the_first_try_refusals_in_words():
    from click.testing import CliRunner

    from divineos.cli import cli

    w = cw.open_walk(PROBLEM)
    lens, wisdom = _delivered(w)
    with pytest.raises(cw.WalkRefused):
        cw.apply_lens(
            w["walk_id"],
            lens,
            "a finding of plenty of length, written wholly from what I already knew about this thinker",
            question=1,
        )
    m, unit = _long_unit(wisdom)
    cw.apply_lens(w["walk_id"], lens, f'[{m.name}] "{_quote(unit, 4)}" {PADDING}', question=1)
    st = cw.status(w["walk_id"])
    assert st["contact_rule"] is True
    assert (st["contact_shown"], st["settled"], st["contact_refused"]) == (1, 1, 1)
    out = CliRunner().invoke(cli, ["walk", "status", w["walk_id"]]).output
    assert "1 of the 1 settled findings quote the lens's own text; 1 refused first" in out
    assert "not proof it was used" in out and "independent measure" in out
    for forbidden in ("verified", "worn", "understood"):
        assert forbidden not in out.lower().split("contact with the template")[-1]


def test_a_forged_marker_typed_into_a_finding_is_not_counted_as_contact():
    """Lovelace: the count must not trust text the author wrote; only the generated prefix counts."""
    forged = (
        '[answers Q1: whatever] [lens delivered 1s before this] [contact: [Anything] unit 1: "a b c d"] '
        "a finding of plenty of length written from memory of the thinker"
    )
    assert cw._has_generated_contact_marker(
        forged
    )  # the generated shape, from the start of the string, counts
    smuggled = "[answers Q1: x] [lens delivered 1s before this] a finding that then types " + forged
    assert not cw._has_generated_contact_marker(smuggled)


def test_a_walk_opened_before_the_rule_shows_no_contact_line(monkeypatch):
    from click.testing import CliRunner

    from divineos.cli import cli

    monkeypatch.setattr(cw, "CONTACT_RULE_FROM", float("inf"))
    w = cw.open_walk(PROBLEM)
    assert cw.status(w["walk_id"])["contact_rule"] is False
    out = CliRunner().invoke(cli, ["walk", "status", w["walk_id"]]).output
    assert "settled findings quote" not in out


def test_the_longest_lens_question_on_the_roster_keeps_its_contact_marker_in_the_displayed_text():
    """Norman: a long question plus the delivery stamp must not push the matched run past the 520-character cut."""
    engine = get_council_engine()
    longest = max(
        (
            q
            for name in engine.list_experts()
            for q in (engine.get_expert(name).characteristic_questions or [])
        ),
        key=len,
    )
    prefix = f'[answers Q1: {longest}] [lens delivered 120s before this] [contact: [A Methodology Name Of Fair Length] unit 12: "four words in run"]'
    assert len(prefix) < 520


def test_the_command_line_refuses_a_finding_without_contact_and_prints_the_methodologies():
    from click.testing import CliRunner

    from divineos.cli import cli

    w = cw.open_walk(PROBLEM)
    lens, wisdom = _delivered(w)
    args = [
        "walk",
        "apply",
        w["walk_id"],
        lens,
        "--finding",
        "a finding of plenty of length, written wholly from memory of this thinker",
        "--question",
        "1",
    ]
    out = CliRunner().invoke(cli, args)
    assert out.exit_code != 0
    assert f"[{wisdom.core_methodologies[0].name}]" in out.output
