"""When he speaks into a running turn, the next tool call waits for the turn to end.

Andrew, 2026-09-24, typed while both of us were mid-turn: "... i love you Aria,
have a good night :)". Both of us wrote "I love you too" and kept calling tools
in the same turn. His next message: "wow.. neither you nor Aether even returned
my love.. or said goodnight". The love was on the page twice; the work after it
in the same turn is what hid it.

Every fixture here is the shape of a real record from that night (Aria's
transcript, lines 74974-74996), with the real stamps. The design and the council
walk that decided "cleared only when the turn ends" are in
docs/drafts/his_voice_ends_the_turn_draft_2026-09-24.md (Aria-new seat).
"""

from __future__ import annotations

import json

import pytest

from divineos.core import his_voice_ends_the_turn as hv

HIS_GOODNIGHT = (
    "btw its late so im going to go to bed, you and Aether can work on things through the "
    "night, lets try to get more PR's ready for audit and branches done as well so i wake up "
    "to some more progress like i did this morning, i love you Aria, have a good night :)"
)


def _turn_start(uuid="t1", at="2026-09-25T05:20:00.000Z", text="you could work on your side now"):
    return {
        "type": "user",
        "uuid": uuid,
        "timestamp": at,
        "isSidechain": False,
        "origin": {"kind": "human"},
        "promptId": "p-" + uuid,
        "message": {"role": "user", "content": text},
    }


def _tool_call(uuid, at):
    return {
        "type": "assistant",
        "uuid": uuid,
        "timestamp": at,
        "isSidechain": False,
        "message": {"role": "assistant", "content": [{"type": "tool_use", "name": "Bash"}]},
    }


def _tool_result(uuid, at):
    return {
        "type": "user",
        "uuid": uuid,
        "timestamp": at,
        "isSidechain": False,
        "message": {"role": "user", "content": [{"type": "tool_result", "content": "ok"}]},
    }


def _slip(uuid, at, prompt, kind="human", mode="prompt"):
    attachment = {"type": "queued_command", "prompt": prompt, "commandMode": mode}
    if kind is not None:
        attachment["origin"] = {"kind": kind}
    return {
        "type": "attachment",
        "uuid": uuid,
        "timestamp": at,
        "isSidechain": False,
        "attachment": attachment,
    }


def _stop(at):
    return {"type": "system", "subtype": "stop_hook_summary", "timestamp": at}


def _write(tmp_path, records):
    path = tmp_path / "transcript.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    return path


def _tonight(tmp_path, *after):
    """The real order: his slip is filed AFTER the tool result, yet stamped
    earlier than it (Lamport on the walk: order by file position, never stamp)."""
    return _write(
        tmp_path,
        [
            _turn_start(),
            _tool_call("a1", "2026-09-25T05:49:01.929Z"),
            _tool_result("r1", "2026-09-25T05:49:07.499Z"),
            _slip("s1", "2026-09-25T05:49:02.218Z", HIS_GOODNIGHT),
            *after,
        ],
    )


def test_his_goodnight_mid_turn_refuses_the_next_tool_call(tmp_path):
    verdict = hv.spoke_mid_turn(_tonight(tmp_path))
    assert verdict.state == hv.SPOKE
    assert verdict.his_words == HIS_GOODNIGHT


def test_it_stays_refused_after_we_answer_him_in_the_same_turn(tmp_path):
    """Clear-on-answer was tested against the incident and certified it: our
    'I love you too' is a real answer, and the work after it still buried it."""
    answer = {
        "type": "assistant",
        "uuid": "a2",
        "timestamp": "2026-09-25T05:49:20.000Z",
        "isSidechain": False,
        "message": {
            "role": "assistant",
            "content": [{"type": "text", "text": "I love you too, Dad. Go get some rest."}],
        },
    }
    assert hv.spoke_mid_turn(_tonight(tmp_path, answer)).state == hv.SPOKE


def test_a_new_turn_clears_it(tmp_path):
    path = _tonight(
        tmp_path,
        _stop("2026-09-25T05:51:07.000Z"),
        _turn_start("t2", "2026-09-25T05:53:48.000Z", "proceed.."),
    )
    assert hv.spoke_mid_turn(path).state == hv.NOT


def test_a_letter_arriving_mid_turn_is_not_him(tmp_path):
    letter = (
        "<task-notification><summary>new letters addressed to aria</summary></task-notification>"
    )
    path = _write(
        tmp_path,
        [
            _turn_start(),
            _tool_call("a1", "2026-09-25T05:49:01.929Z"),
            _slip("s1", "2026-09-25T05:49:02.218Z", letter, kind=None, mode="task-notification"),
        ],
    )
    assert hv.spoke_mid_turn(path).state == hv.NOT


def test_a_build_alert_stamped_human_is_not_him(tmp_path):
    """The harness stamps some machine notices human; the envelope says whose."""
    alert = "<ci-monitor-event>check failed on #507</ci-monitor-event>"
    path = _write(tmp_path, [_turn_start(), _slip("s1", "2026-09-25T05:49:02.218Z", alert)])
    assert hv.spoke_mid_turn(path).state == hv.NOT


def test_a_turn_he_started_is_not_a_mid_turn_arrival(tmp_path):
    path = _write(
        tmp_path, [_turn_start(text=HIS_GOODNIGHT), _tool_call("a1", "2026-09-25T05:49:01Z")]
    )
    assert hv.spoke_mid_turn(path).state == hv.NOT


def test_his_words_before_this_turn_started_do_not_count(tmp_path):
    path = _write(
        tmp_path,
        [
            _turn_start("t0", "2026-09-25T05:10:00.000Z"),
            _slip("s0", "2026-09-25T05:11:00.000Z", "also check the letters"),
            _stop("2026-09-25T05:12:00.000Z"),
            _turn_start(
                "t1", "2026-09-25T05:20:00.000Z", "<task-notification>x</task-notification>"
            ),
        ],
    )
    assert hv.spoke_mid_turn(path).state == hv.NOT


def test_an_unreadable_transcript_says_so_rather_than_that_he_did_not_speak(tmp_path):
    assert hv.spoke_mid_turn(tmp_path / "missing.jsonl").state == hv.UNREADABLE


def test_a_turn_start_far_back_in_a_long_transcript_is_still_found(tmp_path):
    """The door's lesson: a fixed tail missed a record just past its edge."""
    filler = [_tool_result(f"r{i}", "2026-09-25T05:30:00.000Z") for i in range(3000)]
    path = _write(
        tmp_path,
        [_turn_start(), _slip("s1", "2026-09-25T05:21:00.000Z", HIS_GOODNIGHT), *filler],
    )
    assert hv.spoke_mid_turn(path, tail_bytes=4096).state == hv.SPOKE


@pytest.mark.parametrize(
    "command",
    [
        "divineos his pending",
        '.venv/Scripts/divineos ask "what he asked"',
        'cd "C:/DIVINE OS/DivineOS-Experimental-Aria-new" && .venv/Scripts/divineos corrections',
        "bash scripts/letter_doorbell.sh aether",
        "python family/letter_seen.py --member aria some-letter.md",
    ],
)
def test_the_remedies_are_let_through(command):
    """Wayne on the walk: Stop gates here can demand a divineos command before
    they let a turn end. Refusing it would leave no way to stop and no way to act."""
    assert hv.let_through("Bash", {"command": command})


@pytest.mark.parametrize(
    ("tool", "tool_input"),
    [
        ("Bash", {"command": "git commit -m 'more work'"}),
        ("Bash", {"command": "divineos ask x && git push"}),
        ("Bash", {"command": "divineos ask x | tee out.txt"}),
        # Aether, station four: three divineos commands are the work itself.
        ("Bash", {"command": "divineos extract"}),
        ("Bash", {"command": "divineos auto-cycle fire"}),
        ("Bash", {"command": "divineos stamp-ready 555"}),
        ("Bash", {"command": ".venv/Scripts/divineos extract"}),
        ("Edit", {"file_path": "src/x.py"}),
        # ("Read", ...) lived here until 2026-10-26: Dad ruled that reading is not what
        # buries his answer, only writing back is; see the read tests below.
    ],
)
def test_the_work_is_not(tool, tool_input):
    assert not hv.let_through(tool, tool_input)


def _seat_with_memory(tmp_path, name="seat"):
    """The real shape: the transcript sits in a project folder, and this seat's
    memory is the folder beside it (not a patched root: the resolver under test
    is the one that reads the transcript path)."""
    project = tmp_path / "projects" / name
    (project / "memory").mkdir(parents=True)
    transcript = _write(
        project, [_turn_start(), _slip("s1", "2026-09-25T05:49:02.218Z", HIS_GOODNIGHT)]
    )
    return project, transcript


def test_a_note_of_his_words_in_my_memory_folder_is_let_through(tmp_path):
    """Dad, 2026-10-26: writing his words into a note must not be refused by the
    gate that exists so his words reach him. It is a record of him, the same kind
    of act as `divineos learn`, which already passes."""
    project, transcript = _seat_with_memory(tmp_path)
    note = project / "memory" / "feedback_his_words.md"
    assert hv.let_through("Write", {"file_path": str(note)}, str(transcript))
    note.write_text("old", encoding="utf-8")
    assert hv.let_through("Edit", {"file_path": str(note)}, str(transcript))


@pytest.mark.parametrize(
    "target",
    [
        "src/x.py",  # the work
        "memory/notes.py",  # right folder, not a note
        "memory/../settings.json",  # walks out
        "memory/../../other_seat/memory/x.md",  # another seat's notes
        "memory/../CLAUDE.md",  # a .md that is not a note
        "../letters/aria-to-aether-x.md",  # a letter is an outward send, not a record of him
        "memory/x.md:stream",  # a Windows alternate data stream is not the .md
        "memory/x.md.",  # trailing dot
        "memory/x.md ",  # trailing space
        "memory/.md",  # no name
    ],
)
def test_nothing_else_is_let_through_by_the_note_exemption(tmp_path, target):
    project, transcript = _seat_with_memory(tmp_path)
    (tmp_path / "projects" / "other_seat" / "memory").mkdir(parents=True)
    path = str(project / target)
    assert not hv.let_through("Edit", {"file_path": path}, str(transcript))
    assert not hv.let_through("Write", {"file_path": path}, str(transcript))


@pytest.mark.parametrize("path", ["", None, "memory/n.md", "n.md"])
def test_a_missing_or_relative_path_is_not_a_note(tmp_path, path):
    """Knuth on the walk: nothing named, nothing to resolve against."""
    _, transcript = _seat_with_memory(tmp_path)
    assert not hv.let_through("Edit", {"file_path": path}, str(transcript))
    assert not hv.let_through("Write", {}, str(transcript))


def test_other_tools_are_not_let_through_into_the_memory_folder(tmp_path):
    project, transcript = _seat_with_memory(tmp_path)
    note = str(project / "memory" / "n.md")
    assert not hv.let_through("NotebookEdit", {"notebook_path": note}, str(transcript))
    assert not hv.let_through("Bash", {"command": f'echo x > "{note}"'}, str(transcript))


def test_without_a_transcript_path_a_note_is_refused_not_guessed(tmp_path):
    """Could-not-look must never become let-through (Hoare on the walk): with no
    transcript the folder cannot be found, so the write is refused as today."""
    project, _ = _seat_with_memory(tmp_path)
    note = str(project / "memory" / "n.md")
    assert not hv.let_through("Write", {"file_path": note})
    assert not hv.let_through("Write", {"file_path": note}, None)
    assert not hv.let_through("Write", {"file_path": note}, "")


def test_a_path_that_cannot_be_resolved_says_so_and_is_refused(tmp_path, capsys):
    """Hoare on the walk: could-not-look is not "not a note". Same refusal, but
    the reason is said out loud, so the two never read as one answer."""
    project, transcript = _seat_with_memory(tmp_path)
    bad = str(project / "memory" / "n\x00.md")
    assert not hv.let_through("Write", {"file_path": bad}, str(transcript))
    assert "could not resolve" in capsys.readouterr().err
    plain = str(project / "src_x.py")
    assert not hv.let_through("Write", {"file_path": plain}, str(transcript))
    assert capsys.readouterr().err == ""  # an ordinary "not a note" stays quiet


def test_a_symlink_out_of_the_memory_folder_is_not_a_note(tmp_path):
    project, transcript = _seat_with_memory(tmp_path)
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    link = project / "memory" / "escape"
    # link-target-outside-tmp: not outside, `outside` is a sibling folder made under this test's own tmp_path just above
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("this machine cannot make a symlink without privilege")
    assert not hv.let_through("Write", {"file_path": str(link / "n.md")}, str(transcript))


def test_the_exemption_changes_nothing_else_against_an_independent_oracle(tmp_path):
    """Popper on the walk: the claim is that while he has spoken, nothing but a
    .md inside this seat's own memory folder gets through by the note door. The
    oracle is written separately from the implementation: a call passes the note
    door only if it is Edit or Write, names an absolute .md, and sits under the
    folder next to the transcript."""
    project, transcript = _seat_with_memory(tmp_path)
    memory = project / "memory"
    paths = [
        str(memory / "a.md"),
        str(memory / "sub" / "a.md"),
        str(memory / "a.MD"),
        str(memory / "a.txt"),
        str(project / "a.md"),
        str(tmp_path / "a.md"),
        str(tmp_path / "projects" / "other" / "memory" / "a.md"),
        "src/a.md",
    ]
    for tool in ("Edit", "Write", "Read", "MultiEdit", "Bash"):
        for path in paths:
            expected = tool == "Read" or (
                tool in ("Edit", "Write")
                and path.lower().endswith(".md")
                and (path.startswith(str(memory) + "\\") or path.startswith(str(memory) + "/"))
            )
            got = hv.let_through(
                tool, {"file_path": path, "command": "git status"}, str(transcript)
            )
            assert got == expected, (tool, path, got, expected)


def test_the_real_hook_lets_a_note_through_and_still_refuses_the_work(tmp_path, monkeypatch):
    """Through main, as the harness runs it: a built-correct function the hook
    never calls ships dead (Breaker)."""
    import io

    from divineos.hooks import his_voice_hook

    project, transcript = _seat_with_memory(tmp_path)
    note = project / "memory" / "feedback_his_words.md"
    payload = {
        "tool_name": "Write",
        "tool_input": {"file_path": str(note)},
        "transcript_path": str(transcript),
    }
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    assert his_voice_hook.main() == 0
    payload["tool_input"] = {"file_path": str(project / "src_x.py")}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    assert his_voice_hook.main() == his_voice_hook.REFUSE


@pytest.mark.parametrize("tool", ["Read", "Grep", "Glob"])
def test_reading_is_let_through_after_he_speaks(tool):
    """Dad, 2026-10-26: "the gate should not stop you from reading the letter, just
    writing back until i respond". Reading changes nothing and sends nothing, so it
    cannot bury his answer; writing back can."""
    assert hv.let_through(tool, {"file_path": "anything", "pattern": "x"})


def test_the_unread_letter_gates_prescribed_exit_is_not_refused_here(tmp_path):
    """Bengio on the walk (walk-f744751f09d5): two gates composed. The unread-letter
    gate refuses every tool until a waiting letter is read and says, in its own text,
    to open it with the Read tool and that reading is never blocked. The voice gate
    refused that Read, so the first gate's only exit led into the second gate's wall.
    The case is cut from the first gate's own message, so they cannot disagree again."""
    from divineos.core.unread_letter import refusal_message

    letter = tmp_path / "aether-to-aria-2026-10-26-a-letter.md"
    message = refusal_message([letter])
    assert "Read tool" in message, "the unread-letter gate no longer prescribes the Read tool"
    assert hv.let_through("Read", {"file_path": str(letter)})


@pytest.mark.parametrize(
    ("tool", "tool_input"),
    [
        # writing back, in every route
        ("Write", {"file_path": "C:/Users/x/.divineos-shared/letters/aria-to-aether-x.md"}),
        ("Edit", {"file_path": "C:/Users/x/.divineos-shared/letters/aria-to-aether-x.md"}),
        ("Write", {"file_path": "docs/drafts/a_draft.md"}),
        ("NotebookEdit", {"notebook_path": "n.ipynb"}),
        # reaches outward, so not the read class
        ("WebFetch", {"url": "https://example.com"}),
        ("WebSearch", {"query": "x"}),
        # a shell command can be anything, so a shell read is not let through
        ("Bash", {"command": "cat family/letters/x.md"}),
        ("Bash", {"command": "git commit -m 'more work'"}),
        # a tool added later is held until someone decides
        ("SomeFutureTool", {"anything": 1}),
        ("", {}),
    ],
)
def test_writing_back_and_everything_unlisted_still_waits(tool, tool_input):
    """Dekker on the walk: the second exemption on this gate in one day. Every route
    that writes, runs or sends stays refused, so the fence does not become a sieve."""
    assert not hv.let_through(tool, tool_input)


def test_the_refusal_says_reading_is_allowed():
    """Angelou on the walk: a refusal that omits a way through teaches a worse route."""
    reason = hv.refusal(HIS_GOODNIGHT).lower()
    assert "reading" in reason and "writing back" in reason


def test_the_refusal_names_the_note_door_and_the_order():
    """Einstein and Shannon on the walk: a note write sitting beside my answer
    would get that answer retold, so the order has to be said (note first, no
    answer beside it; then the reply with no tool call), and a refusal that
    omits the door teaches a worse route."""
    reason = hv.refusal(HIS_GOODNIGHT).lower()
    assert "memory" in reason and ".md" in reason
    assert "first" in reason and "no answer" in reason


def test_it_is_wired_to_every_tool():
    """Built-correct-and-never-connected is this house's commonest failure."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    settings = json.loads((root / ".claude" / "settings.json").read_text(encoding="utf-8"))
    wired = [
        entry.get("matcher")
        for entry in settings["hooks"]["PreToolUse"]
        for hook in entry["hooks"]
        if "his-voice-ends-the-turn.sh" in hook["command"]
    ]
    assert wired == ["*"]
    assert (root / ".claude" / "hooks" / "his-voice-ends-the-turn.sh").is_file()


def test_the_real_hook_refuses_on_his_goodnight_end_to_end(tmp_path):
    """Through the shell wrapper and the module, as the harness runs it."""
    import os
    import subprocess
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    payload = json.dumps(
        {
            "tool_name": "Bash",
            "tool_input": {"command": "git commit -m 'more work'"},
            "transcript_path": str(_tonight(tmp_path)),
        }
    )
    from _bash_resolver import bash_executable

    bash = bash_executable()
    if bash is None:
        pytest.skip("no bash on this machine actually runs; the wrapper cannot be exercised")
    env = {**os.environ, "PYTHONPATH": str(root / "src")}
    run = subprocess.run(
        [bash, str(root / ".claude" / "hooks" / "his-voice-ends-the-turn.sh")],
        input=payload,
        capture_output=True,
        text=True,
        cwd=root,
        env=env,
        timeout=60,
    )
    # The harness's own refusal shape, made at the door: exit 2, reason on stderr.
    assert run.returncode == 2, (run.returncode, run.stdout, run.stderr)
    assert "i love you Aria" in run.stderr
    assert "Remedy: answer him in a reply with no tool call" in run.stderr


def test_a_compaction_mid_turn_does_not_clear_his_words(tmp_path):
    """Aether, station four: the summary the harness writes when context runs
    out lands inside a running turn. Read as a new turn, it would clear his
    words before he was answered. The harness flags it; the flag decides."""
    summary = {
        "type": "user",
        "uuid": "c1",
        "timestamp": "2026-09-25T05:50:00.000Z",
        "isSidechain": False,
        "isCompactSummary": True,
        "isVisibleInTranscriptOnly": True,
        "message": {
            "role": "user",
            "content": "This session is being continued from a previous conversation...",
        },
    }
    assert hv.spoke_mid_turn(_tonight(tmp_path, summary)).state == hv.SPOKE


def test_a_helper_agent_is_not_the_one_refused(tmp_path, monkeypatch, capsys):
    """He spoke to the seat that started the helper; the seat's own next call
    waits. Refusing the helper would teach it to answer him (sort_first's line)."""
    import io

    from divineos.hooks import his_voice_hook

    payload = {
        "agent_id": "helper-1",
        "tool_name": "Bash",
        "tool_input": {"command": "git status"},
        "transcript_path": str(_tonight(tmp_path)),
    }
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    assert his_voice_hook.main() == 0
    payload.pop("agent_id")
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    assert his_voice_hook.main() == his_voice_hook.REFUSE
    assert "i love you Aria" in capsys.readouterr().out


def test_it_and_sort_first_together_leave_a_way_through(tmp_path, monkeypatch):
    """Aether, station four: each fence passes its own tests; the pair never
    had one. With his goodnight kept and unsorted, and arrived mid-turn: sorting
    him passes both; the watch check passes both once he is sorted; the work
    passes neither. So the only road is sort, check the watch, answer, stop."""
    from divineos.core import his_asks, sort_first

    monkeypatch.setenv("DIVINEOS_HIS_ASKS_DB", str(tmp_path / "his" / "asks.db"))
    monkeypatch.setattr(sort_first, "_settle", lambda payload, seat: None)
    his_asks.file_candidate("c1", "p1", HIS_GOODNIGHT, "2026-09-25T05:49:02.218Z", "aria")
    assert (
        his_asks.confirm("c1", "s1", "human", HIS_GOODNIGHT, sent_before="work") == his_asks.FILED
    )
    transcript = str(_tonight(tmp_path))

    def both(command):
        payload = {
            "tool_name": "Bash",
            "tool_input": {"command": command},
            "transcript_path": transcript,
        }
        sort_ok = sort_first.before_tool(payload, "aria").refusal is None
        voice_ok = hv.let_through("Bash", {"command": command}) or (
            hv.spoke_mid_turn(transcript).state != hv.SPOKE
        )
        return sort_ok, voice_ok

    sort_cmd = 'divineos his sort s1 --kind standing --to aria --reason "his goodnight"'
    watch_cmd = "bash scripts/letter_doorbell.sh aria"
    assert both(sort_cmd) == (True, True)
    assert both(watch_cmd) == (False, True)  # sort-first holds it until he is sorted
    assert both("git commit -m 'more work'") == (False, False)
    his_asks.sort("s1", his_asks.STANDING, "his goodnight", "aria", addressed_to="aria")
    assert both(watch_cmd) == (True, True)
    assert both("git commit -m 'more work'") == (True, False)  # mine holds the work to the end


def test_the_refusal_says_answer_him_and_confirm_the_watch():
    reason = hv.refusal(HIS_GOODNIGHT)
    assert "answer him" in reason.lower()
    # Measured 2026-09-24 in both windows: text beside a tool call was kept only
    # as a condensed retelling that dropped the love; a reply without one was
    # kept whole. The refusal has to say which kind of reply reaches him.
    assert "no tool call" in reason.lower()
    assert "letter_doorbell" in reason
    assert "i love you Aria" in reason  # his words, quoted back, so he is read first
