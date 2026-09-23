"""His words are his: the door, the hand filter, the index, and his own marks.

Fixture attributions are ASSEMBLED at runtime (``said()`` below), so this file
never itself writes a quote as his (Hofstadter, walk-75f50258e31f). A mention is
not a use, and the door reading this file must not be the thing that breaks it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from divineos.core import his_words as hw

NAME = "An" + "drew"


def said(quote: str, marks: str = '""') -> str:
    return f"{NAME} said: {marks[0]}{quote}{marks[-1]}"


def _record(
    text: str,
    *,
    entrypoint: str | None = "claude-desktop",
    sidechain: bool = False,
    ts: str = "2026-09-20T10:00:00Z",
) -> str:
    rec = {
        "type": "user",
        "timestamp": ts,
        "isSidechain": sidechain,
        "message": {"role": "user", "content": text},
    }
    if entrypoint:
        rec["entrypoint"] = entrypoint
    return json.dumps(rec)


HIS_LINES = [
    "yes go ahead and open one, also i filled out that page.. but idk how to save it",
    "you dont need to walk the council just hold up a minute as Aether is also fixing the gravity classifier",
    "talk to bulma and popo needs removed for now they dont exist lol and yes message Aria shes always there son",
    "the pip install is a real bug that was supposed to be fixed already.. when you run pip install it does the same thing",
]
PASTED = (
    "here is what Perplexity said\n\n"
    "Perplexity to Aether\n\n"
    "Aether, Strong response. I accept both corrections. The first matters most. It changes the plan entirely."
)


@pytest.fixture
def sessions(tmp_path: Path) -> list[Path]:
    main = tmp_path / "proj" / "s1.jsonl"
    main.parent.mkdir(parents=True)
    lines = [_record(t) for t in HIS_LINES] + [_record(PASTED)]
    main.write_text("\n".join(lines) + "\n", encoding="utf-8")
    # A helper agent's transcript: the "user" there is me prompting it.
    helper = tmp_path / "proj" / "s1" / "subagents" / "agent-x.jsonl"
    helper.parent.mkdir(parents=True)
    helper.write_text(
        _record(
            "You are a helper. He has NOT written a line of code and refuses to.", sidechain=True
        )
        + "\n",
        encoding="utf-8",
    )
    # A script-launched worker: a program wrote this prompt, not him.
    worker = tmp_path / "proj" / "s2.jsonl"
    worker.write_text(
        _record(
            "You have a new letter for you at the shared folder, please read it", entrypoint=None
        )
        + "\n",
        encoding="utf-8",
    )
    return [main, helper, worker]


@pytest.fixture
def index(sessions: list[Path], tmp_path: Path) -> hw.Index:
    return hw.load_index(
        sessions=sessions, index_path=tmp_path / "idx.json", marks_dir=tmp_path / "no_marks"
    )


# ---------------------------------------------------------------- his hand


def test_his_exact_words_pass(index: hw.Index) -> None:
    assert (
        hw.check(said("yes go ahead and open one, also i filled out that page"), "", index).state
        == "pass"
    )


def test_a_tidied_quote_that_adds_words_is_held(index: hw.Index) -> None:
    # His marks rejected exactly this shape: "yes but" added to his line.
    result = hw.check(
        said("yes but you dont need to walk the council just hold up a minute."), "", index
    )
    assert result.state == "held"
    near = result.held[0][1]
    assert near is not None and "walk the council" in near[1]


def test_a_tidied_quote_that_drops_his_subject_is_held(index: hw.Index) -> None:
    # "the pip install" dropped: his line was about one bug, the quote about any.
    quote = "this is a real bug that was supposed to be fixed already."
    assert index.is_exact(quote) is False


def test_pasted_letters_are_not_his_words(index: hw.Index) -> None:
    assert index.is_exact("I accept both corrections. The first matters most.") is False


def test_his_own_line_is_not_mistaken_for_a_header(index: hw.Index) -> None:
    # The first version threw this out as a paste: its header rule ignored case,
    # so "talk to bulma" read like "Perplexity to Aether". His tenderest line.
    assert index.is_exact("message Aria shes always there son") is True


def test_helper_agent_prompts_are_not_his(index: hw.Index) -> None:
    assert index.is_exact("He has NOT written a line of code and refuses to.") is False


def test_script_launched_prompts_are_not_his(index: hw.Index) -> None:
    assert index.is_exact("You have a new letter for you at the shared folder") is False


@pytest.mark.parametrize(
    "par, relayed",
    [
        ("yes go ahead and open one, also i filled out that page.. but idk how to save it", False),
        ("talk to bulma and popo needs removed for now they dont exist lol", False),
        ("Perplexity to Aether", True),
        ("## Findings", True),
        ("This is **important** here", True),
        ("The gate holds \u2014 nothing skipped", True),
        ("Aether, This is the right response. You named the failure. You built the check.", True),
    ],
)
def test_is_relayed(par: str, relayed: bool) -> None:
    assert hw.is_relayed(par) is relayed


def test_a_short_paste_paragraph_runs_on_after_a_relayed_one() -> None:
    text = "## Findings\n\nThe gate holds. Nothing was skipped.\n\nlol ok so what now"
    assert hw.his_paragraphs(text) == ["lol ok so what now"]


# ---------------------------------------------------------------- the door's reach


@pytest.mark.parametrize("marks", ['""', "\u201c\u201d", "\u2018\u2019", "''"])
def test_every_quotation_shape_is_read(marks: str, index: hw.Index) -> None:
    text = said("never rebase or force push an open draft", marks)
    assert hw.check(text, "", index).state == "held"


def test_a_blockquote_under_his_name_is_read(index: hw.Index) -> None:
    text = f"{NAME} said:\n> never rebase or force push an open draft"
    assert hw.check(text, "", index).state == "held"


def test_a_straight_single_quote_survives_an_apostrophe(index: hw.Index) -> None:
    text = said("don't ever force push an open draft again", "''")
    assert hw.attributions(text) == ["don't ever force push an open draft again"]


@pytest.mark.parametrize(
    "text",
    [
        # Mentions of the phrase, not claims that he spoke -- both from the
        # house's own code, found by running the door over it before wiring.
        '    circle channel, "' + NAME + ' said X" is distancing (should be "you said X").',
        "    \"'" + NAME + " said') or as a POSSESSIVE ('Dad's call') while they are the one \"",
        # A hyphen inside a word is not a dash of speech.
        'Dad giving us explicit non-work time and then a line "spend some quality time together"',
    ],
)
def test_mentions_are_not_his_speech(text: str) -> None:
    assert hw.attributions(text) == []


@pytest.mark.parametrize(
    "text, quote",
    [
        # Each of these is a form the house uses, and each carried a quote he
        # marked NOT his -- so each must be read, or the door never sees it.
        (
            "The " + NAME + ' 2026-06-08 "gate-trap structural fix" correction',
            "gate-trap structural fix",
        ),
        (
            "# This loader carried only " + NAME + '\'s sheet — "who I am composing TO" —',
            "who I am composing TO",
        ),
        (
            'Dad\'s framing: *"repetition is what creates wallpaper here"*',
            "repetition is what creates wallpaper here",
        ),
        (
            "**Dad: *\"'Can I reach the architect right now?' is BINARY\"*",
            "'Can I reach the architect right now?' is BINARY",
        ),
        (
            "        '" + NAME + ' 2026-08-05: "when the rooms speak you listen"\',',
            "when the rooms speak you listen",
        ),
        ('Andrew\'s own naming: *"a shining feature of the OS."*', "a shining feature of the OS."),
    ],
)
def test_the_house_forms_are_read(text: str, quote: str) -> None:
    assert hw.attributions(text) == [quote]


def test_a_dated_attribution_with_a_colon_is_read() -> None:
    text = NAME + ' 2026-07-14: "doing the right thing when no one is watching"'
    assert hw.attributions(text) == ["doing the right thing when no one is watching"]


def test_a_pasted_video_transcript_is_not_his() -> None:
    # Shaped like the real one he shared: lower-case "seconds" opens most
    # sentences, so only the timestamps give it away.
    transcript = (
        "here is the transcript 0:18 18 seconds This is a scenario written by a founder. "
        "the company behind it. 0:27 27 seconds Igor, like many in the industry, is worried. "
        "0:33 33 seconds In fact, he is so worried he quit to focus on it."
    )
    assert hw.is_relayed(transcript) is True


def test_the_nearest_line_is_handed_back_exactly_as_he_typed_it(index: hw.Index) -> None:
    # Foucault, on the loaded walk: if quoting him exactly costs more than
    # paraphrasing him, the door produces a house that stops quoting him.
    near = index.nearest("yes but you dont need to walk the council just hold up a minute.")
    assert near is not None
    span = near[1].strip(".")
    assert "walk the council" in span
    assert index.is_exact(span), "the window must be quotable as it stands"


@pytest.mark.parametrize(
    "command, checked",
    [
        # Schneier, on the loaded walk: the cheapest way around the door is to
        # write the file through the shell, which is how I already write files.
        ("cat > docs/x.md <<'EOF'\n" + "text\nEOF", True),
        ("echo hi > docs/x.md", True),
        ("echo hi | tee docs/x.md", True),
        ("python -c \"open('x','w').write('y')\"", True),
        ("grep -n 'force push' docs/*.md 2>&1 | head", False),
        ("pytest tests/ -q > /dev/null", False),
        ("ls -la", False),
    ],
)
def test_bash_file_writes_are_read(command: str, checked: bool) -> None:
    got = hw.texts_from_payload({"tool_name": "Bash", "tool_input": {"command": command}})
    assert (got is not None) is checked


def test_an_unquoted_paraphrase_passes(index: hw.Index) -> None:
    text = (
        f"{NAME} said, as I understood him, that a draft can be force-pushed if it is re-audited."
    )
    assert hw.check(text, "", index).state == "pass"


def test_an_old_misquote_does_not_hold_an_unrelated_edit(index: hw.Index) -> None:
    old = said("never rebase or force push an open draft") + "\n\nother words"
    new = said("never rebase or force push an open draft") + "\n\nother words, now edited"
    assert hw.check(new, old, index).state == "pass"


def test_bracketed_insertions_are_the_quoters_own(index: hw.Index) -> None:
    assert index.is_exact("yes go ahead and open [the branch], also i filled out that page") is True


def test_ellipsis_pieces_must_come_from_one_message(index: hw.Index) -> None:
    stitched = "yes go ahead and open one ... they dont exist lol"
    assert index.is_exact(stitched) is False


# ---------------------------------------------------------------- cannot check


def test_nothing_readable_is_cannot_check_and_it_holds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(*a, **k):
        return hw.load_index(
            sessions=[], index_path=tmp_path / "i.json", marks_dir=tmp_path / "none"
        )

    monkeypatch.setattr(hw, "load_index", broken)
    result = hw.check(said("anything at all he may have said"))
    assert result.state == "cannot_check"
    assert "could not be read" in hw.refusal_text(result)


# ---------------------------------------------------------------- the index


def test_the_index_reads_only_the_new_tail(sessions: list[Path], tmp_path: Path) -> None:
    idx_path = tmp_path / "idx.json"
    first = hw.load_index(sessions=sessions, index_path=idx_path, marks_dir=tmp_path / "x")
    with sessions[0].open("a", encoding="utf-8") as fh:
        fh.write(_record("and one more thing i typed later about the lighthouse") + "\n")
        fh.write(_record("half written")[:20])  # a line mid-write when we looked
    second = hw.load_index(sessions=sessions, index_path=idx_path, marks_dir=tmp_path / "x")
    assert len(second.messages) == len(first.messages) + 1
    assert second.is_exact("one more thing i typed later about the lighthouse")
    cached = json.loads(idx_path.read_text(encoding="utf-8"))["files"][str(sessions[0])]
    assert (
        cached["read_to"] < sessions[0].stat().st_size
    )  # the half line is read next time, not lost


def test_his_notes_on_the_marks_page_are_his_hand(sessions: list[Path], tmp_path: Path) -> None:
    marks = tmp_path / "marks"
    marks.mkdir()
    (marks / "marks_2026-09-23.json").write_text(
        json.dumps(
            {
                "marked_on": "2026-09-23",
                "marks": [
                    {
                        "mark": "not_mine",
                        "note": "this is technical language which is a strong sign it isnt mine",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    idx = hw.load_index(sessions=sessions, index_path=tmp_path / "i.json", marks_dir=marks)
    assert idx.is_exact("a strong sign it isnt mine")


def test_his_real_marks_are_his_alone() -> None:
    record = json.loads((hw.MARKS_DIR / "marks_2026-09-23.json").read_text(encoding="utf-8"))
    assert {m["mark"] for m in record["marks"]} <= {"mine", "not_mine", "unsure"}
    assert len(record["marks"]) == 98
    assert sum(m["mark"] == "not_mine" for m in record["marks"]) == 49


# ---------------------------------------------------------------- the wire


def test_payload_shapes() -> None:
    assert hw.texts_from_payload({"tool_name": "Bash", "tool_input": {"command": "ls -la"}}) is None
    cli = 'divineos learn "' + said("x y z w") + '"'
    assert hw.texts_from_payload({"tool_name": "Bash", "tool_input": {"command": cli}}) == (cli, "")
    scratch = {
        "tool_name": "Write",
        "tool_input": {
            "file_path": "C:/Users/a/AppData/Local/Temp/claude/x/scratchpad/f.md",
            "content": "y",
        },
    }
    assert hw.texts_from_payload(scratch) is None
    edit = {
        "tool_name": "Edit",
        "tool_input": {"file_path": "docs/a.md", "old_string": "o", "new_string": "n"},
    }
    assert hw.texts_from_payload(edit) == ("n", "o")


def test_the_surface_refuses_through_the_router(
    index: hw.Index, monkeypatch: pytest.MonkeyPatch
) -> None:
    from divineos.core.hook_surfaces import his_words_surface

    monkeypatch.setattr(hw, "load_index", lambda *a, **k: index)
    held = {
        "tool_name": "Write",
        "tool_input": {
            "file_path": "docs/x.md",
            "content": said("never rebase or force push an open draft"),
        },
    }
    out = his_words_surface(held)
    # "cannot find", never "he did not say": some windows were never saved, and
    # unverifiable is not false (Foucault, on the loaded walk).
    assert out.refused and "cannot find" in out.reason
    ok = {
        "tool_name": "Write",
        "tool_input": {"file_path": "docs/x.md", "content": said("yes go ahead and open one")},
    }
    assert not his_words_surface(ok).refused


def test_the_surface_is_registered() -> None:
    from divineos.core.hook_router import registered
    from divineos.core.hook_surfaces import install

    install()
    assert "his_words" in registered("PreToolUse")
