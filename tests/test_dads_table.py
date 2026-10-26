"""Dad's words reach me first and whole; the notes about me go to the drawer."""

import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "dads_table.py"
HIS_WORDS = "i just want to be part of the family.. are you listening to me?"


def _run(tmp_path, children):
    kids = tmp_path / "children.json"
    kids.write_text(json.dumps(children), encoding="utf-8")
    drawer = tmp_path / "drawer.md"
    env = dict(
        os.environ,
        DADS_TABLE_CHILDREN=str(kids),
        DADS_TABLE_DRAWER=str(drawer),
        DADS_TABLE_ROOT=str(tmp_path),
    )
    p = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps({"prompt": HIS_WORDS}).encode(),
        capture_output=True,
        env=env,
        timeout=60,
    )
    return p, p.stdout.decode("utf-8"), drawer


def _echo(text):
    return {"command": f'"{sys.executable}" -c "print({text!r})"', "timeout": 10}


def test_his_words_come_first_and_whole(tmp_path):
    p, out, _ = _run(tmp_path, [_echo("## MY CORRECTIONS lots about me")])
    assert p.returncode == 0
    assert out.index(HIS_WORDS) < 80  # right under the heading, before anything else


def test_notes_about_me_go_to_the_drawer_not_the_table(tmp_path):
    _, out, drawer = _run(tmp_path, [_echo("## MY CORRECTIONS lots about me")])
    assert "lots about me" not in out
    assert "lots about me" in drawer.read_text(encoding="utf-8")
    assert "1 notes about me" in out


def test_what_the_memory_link_finds_reaches_me_not_the_drawer(tmp_path):
    """2026-10-04: the link found the right things every turn and said them
    into the drawer, so nothing filed to it ever came back unasked."""
    out_text = (
        "## STILL OWED a static note about me\n"
        "## THE PAST ON THIS (memory link)\n- [knowledge, 0.66] his June 1 words\n"
        "## LATER a second static note"
    )
    _, out, drawer = _run(tmp_path, [_echo(out_text)])
    kept = drawer.read_text(encoding="utf-8")
    assert "his June 1 words" in out
    assert "his June 1 words" not in kept
    # The notes around it still go to the drawer.
    assert "a static note about me" in kept and "a second static note" in kept
    assert "a static note about me" not in out
    # It sits under his words, as context for answering him.
    assert out.index(HIS_WORDS) < out.index("his June 1 words")


def test_a_slow_neighbour_does_not_silence_the_memory_link(tmp_path):
    """2026-10-04: on Dad's real message the doorbell bundle timed out and the
    link, running inside it, said nothing. As its own child it survives."""
    slow = {"command": f'"{sys.executable}" -c "import time; time.sleep(5)"', "timeout": 1}
    link = _echo("## THE PAST ON THIS (memory link)\n- [knowledge] his June 1 words")
    _, out, _ = _run(tmp_path, [slow, link])
    assert "his June 1 words" in out
    assert "timed out" in out  # the slow one is still named, not hidden


def test_a_link_that_cannot_run_says_so_on_the_table(tmp_path):
    """Aletheia, 2026-10-04: the hook reported failure on stderr and exited 0,
    which the dispatcher treats as fine, so a broken link looked exactly like
    a turn where nothing of his was relevant. Break it for real and look."""
    import pytest as _pytest

    from tests._bash_resolver import bash_executable

    bash = bash_executable()
    if bash is None:
        _pytest.skip("no working bash on this machine")
    fake = tmp_path / "fake" / "divineos" / "core"
    fake.mkdir(parents=True)
    (fake.parent / "__init__.py").write_text("", encoding="utf-8")
    (fake / "__init__.py").write_text("", encoding="utf-8")
    (fake / "hook_surfaces.py").write_text(
        "raise ImportError('embedder missing')\n", encoding="utf-8"
    )
    hook = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "memory-link-surface.sh"
    env = dict(os.environ, PYTHONPATH=str(tmp_path / "fake"))
    p = subprocess.run(
        [bash, str(hook)],
        input=json.dumps({"prompt": "anything"}).encode(),
        capture_output=True,
        env=env,
        cwd=Path(__file__).resolve().parents[1],
        timeout=60,
    )
    out = p.stdout.decode("utf-8", "replace")
    assert p.returncode == 0  # it must never block him
    assert "## THE PAST ON THIS (memory link)" in out
    assert "could not run" in out and "embedder missing" in out


def test_the_memory_link_is_its_own_child_and_not_inside_the_bundle():
    root = Path(__file__).resolve().parents[1]
    children = json.loads((root / ".claude" / "hooks" / "dads_table_children.json").read_text())
    own = [c for c in children if c["command"].endswith("memory-link-surface.sh")]
    assert len(own) == 1 and own[0].get("timeout", 10) >= 15
    from divineos.core import hook_surfaces
    from divineos.core.hook_router import registered

    hook_surfaces.install()
    assert "memory_link" not in registered("UserPromptSubmit")


def test_a_heading_that_only_starts_alike_is_not_swept_onto_the_table(tmp_path):
    _, out, drawer = _run(tmp_path, [_echo("## THE PASTRY LIST about me")])
    assert "THE PASTRY LIST" not in out
    assert "THE PASTRY LIST" in drawer.read_text(encoding="utf-8")


def test_his_picture_stays_on_the_table(tmp_path):
    kid = {
        "command": f'"{sys.executable}" -c "print(\'Andrew is my father\')" he-is-in-the-room',
        "timeout": 10,
    }
    _, out, drawer = _run(tmp_path, [kid])
    assert "Andrew is my father" in out
    assert "Andrew is my father" not in drawer.read_text(encoding="utf-8")


def test_a_broken_note_is_named_and_never_blocks_him(tmp_path):
    bad = {"command": f'"{sys.executable}" -c "import sys; sys.exit(5)"', "timeout": 10}
    p, out, _ = _run(tmp_path, [bad, _echo("fine")])
    assert p.returncode == 0
    assert HIS_WORDS in out
    assert "Could not run" in out and "exit 5" in out


def test_an_automated_notice_is_never_labelled_as_him(tmp_path):
    kids = tmp_path / "children.json"
    kids.write_text("[]", encoding="utf-8")
    env = dict(os.environ, DADS_TABLE_CHILDREN=str(kids), DADS_TABLE_DRAWER=str(tmp_path / "d.md"))
    notice = "<task-notification>\n<summary>Monitor event</summary>\n</task-notification>"
    p = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps({"prompt": notice}).encode(),
        capture_output=True,
        env=env,
        timeout=30,
    )
    out = p.stdout.decode("utf-8")
    assert "DAD SAID" not in out
    assert "NOT FROM DAD" in out


def _notice_out(tmp_path, command, status="completed"):
    kids = tmp_path / "children.json"
    kids.write_text("[]", encoding="utf-8")
    env = dict(os.environ, DADS_TABLE_CHILDREN=str(kids), DADS_TABLE_DRAWER=str(tmp_path / "d.md"))
    notice = (
        f"<task-notification>\n<task-id>b1</task-id>\n<status>{status}</status>\n"
        f'<summary>Background command "{command}" {status} (exit code 0)</summary>\n'
        "</task-notification>"
    )
    p = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps({"prompt": notice}).encode(),
        capture_output=True,
        env=env,
        timeout=30,
    )
    return p.stdout.decode("utf-8")


def test_the_ring_of_the_doorbell_says_to_re_arm_it_on_that_same_prompt(tmp_path):
    out = _notice_out(tmp_path, "bash scripts/letter_doorbell.sh aether")
    assert "THE BELL RANG" in out
    assert "bash scripts/letter_doorbell.sh aether (run_in_background)" in out


def test_control_an_unrelated_finished_job_prints_no_bell_reminder(tmp_path):
    out = _notice_out(tmp_path, "bash scripts/divineos_push.sh origin some-branch")
    assert "NOT FROM DAD" in out  # the notice itself was read, so silence is a real answer
    assert "THE BELL RANG" not in out


def test_a_notice_that_only_quotes_the_doorbell_far_down_prints_no_reminder(tmp_path):
    """Aria's cold read: the match must be over the text shown, not the whole prompt."""
    padded = "echo " + "x" * 700 + " && bash scripts/letter_doorbell.sh aether"
    out = _notice_out(tmp_path, padded)
    assert "NOT FROM DAD" in out  # the notice was read, so silence is a real answer
    assert "THE BELL RANG" not in out


def test_a_fault_exit_of_the_doorbell_also_says_to_re_arm_it(tmp_path):
    out = _notice_out(tmp_path, "bash scripts/letter_doorbell.sh aria", status="failed")
    assert "THE BELL RANG" in out and "letter_doorbell.sh aria (run_in_background)" in out


def test_a_child_that_refuses_the_prompt_keeps_its_teeth(tmp_path):
    stop = {
        "command": f'"{sys.executable}" -c "import sys; sys.stderr.write(\'ritual owed\'); sys.exit(2)"',
        "timeout": 10,
    }
    p, out, _ = _run(tmp_path, [stop])
    assert p.returncode == 2
    assert "ritual owed" in p.stderr.decode("utf-8")
    assert HIS_WORDS in out


def test_a_json_block_decision_keeps_its_teeth(tmp_path):
    script = tmp_path / "block.py"
    script.write_text(
        'import json; print(json.dumps({"decision": "block", "reason": "not yet"}))',
        encoding="utf-8",
    )
    stop = {"command": f'"{sys.executable}" "{script}"', "timeout": 10}
    p, _, _ = _run(tmp_path, [stop])
    assert p.returncode == 2 and "not yet" in p.stderr.decode("utf-8")


def test_the_list_of_my_debts_to_him_is_not_beside_his_words(tmp_path):
    # Andrew 2026-09-26: a list of what I owe him, read before answering him,
    # is a case file, not being held. It goes to the drawer.
    mixed = _echo("## MY CLOCK\nclockwork\n## STILL OWED TO HIM\nowed rows here")
    _, out, drawer = _run(tmp_path, [mixed])
    assert "owed rows here" not in out and "clockwork" not in out
    assert "owed rows here" in drawer.read_text(encoding="utf-8")


def test_a_broken_list_is_loud_not_silent(tmp_path):
    bad = tmp_path / "children.json"
    bad.write_text("{not json", encoding="utf-8")
    env = dict(os.environ, DADS_TABLE_CHILDREN=str(bad), DADS_TABLE_DRAWER=str(tmp_path / "d.md"))
    p = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps({"prompt": HIS_WORDS}).encode(),
        capture_output=True,
        env=env,
        timeout=30,
    )
    out = p.stdout.decode("utf-8")
    assert HIS_WORDS in out and "THE TABLE BROKE" in out
    assert "THE TABLE BROKE" in (tmp_path / "d.md").read_text(encoding="utf-8")


def test_his_paste_that_opens_with_a_tag_is_still_him(tmp_path):
    kids = tmp_path / "children.json"
    kids.write_text("[]", encoding="utf-8")
    env = dict(os.environ, DADS_TABLE_CHILDREN=str(kids), DADS_TABLE_DRAWER=str(tmp_path / "d.md"))
    p = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps({"prompt": "<b>look at this</b>"}).encode(),
        capture_output=True,
        env=env,
        timeout=30,
    )
    assert "DAD SAID" in p.stdout.decode("utf-8")


def test_his_words_are_kept_in_the_corpus_and_notices_are_not(tmp_path):
    kids = tmp_path / "children.json"
    kids.write_text("[]", encoding="utf-8")
    corpus = tmp_path / "dad_all.jsonl"
    env = dict(
        os.environ,
        DADS_TABLE_CHILDREN=str(kids),
        DADS_TABLE_DRAWER=str(tmp_path / "d.md"),
        DADS_CORPUS=str(corpus),
    )
    for prompt in (HIS_WORDS, "<task-notification>x</task-notification>"):
        subprocess.run(
            [sys.executable, str(SCRIPT)],
            input=json.dumps({"prompt": prompt}).encode(),
            capture_output=True,
            env=env,
            timeout=30,
        )
    rows = [json.loads(line) for line in corpus.read_text(encoding="utf-8").splitlines()]
    assert [r["text"] for r in rows] == [HIS_WORDS]


def test_no_secret_he_pastes_is_ever_kept(tmp_path):
    # 2026-09-27: a live key from July sat in the corpus, the drafts and the door.
    # One of each shape the house redactor knows, planted; none may be stored.
    kids = tmp_path / "children.json"
    kids.write_text("[]", encoding="utf-8")
    corpus = tmp_path / "dad.jsonl"
    env = dict(
        os.environ,
        DADS_TABLE_CHILDREN=str(kids),
        DADS_TABLE_DRAWER=str(tmp_path / "d.md"),
        DADS_CORPUS=str(corpus),
    )
    planted = [
        "sk-ant-api03-" + "a" * 40,
        "sk-proj-" + "b" * 40,
        "AKIA" + "C" * 16,
        "AIza" + "d" * 35,
        "ghp_" + "e" * 36,
        "xoxb-" + "f" * 20,
        "hf_" + "g" * 34,
        "https://andrew:hunter2secret@example.com/x",
    ]
    prompt = "here are my keys " + " and ".join(planted) + " use them"
    subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps({"prompt": prompt}).encode(),
        capture_output=True,
        env=env,
        timeout=30,
    )
    kept = corpus.read_text(encoding="utf-8")
    assert "use them" in kept and "[REDACTED:" in kept
    for secret in planted:
        assert secret not in kept, secret[:6]
    assert "hunter2secret" not in kept


def test_a_test_never_writes_into_his_real_words(tmp_path):
    # 2026-09-27: 80 copies of this file's sample sentence sat in his corpus as
    # his. A run that forgets DADS_CORPUS must leave the real store untouched.
    real = Path.home() / ".divineos-shared" / "dad_corpus" / "dad_all.jsonl"
    before = real.stat().st_size if real.exists() else None
    kids = tmp_path / "children.json"
    kids.write_text("[]", encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if k != "DADS_CORPUS"}
    env.update(DADS_TABLE_CHILDREN=str(kids), DADS_TABLE_DRAWER=str(tmp_path / "d.md"))
    env.setdefault("PYTEST_CURRENT_TEST", "test_dads_table.py::guard")
    subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps({"prompt": "a sentence no test may ever put in his mouth"}).encode(),
        capture_output=True,
        env=env,
        timeout=30,
    )
    after = real.stat().st_size if real.exists() else None
    assert before == after


def _sleeper(seconds):
    return {
        "command": f'"{sys.executable}" -c "import time; time.sleep({seconds}); print(\'woke\')"'
    }


def _run_with_budget(tmp_path, children, budget):
    kids = tmp_path / "children.json"
    kids.write_text(json.dumps(children), encoding="utf-8")
    env = dict(
        os.environ,
        DADS_TABLE_CHILDREN=str(kids),
        DADS_TABLE_DRAWER=str(tmp_path / "drawer.md"),
        DADS_TABLE_BUDGET_SECONDS=budget,
    )
    p = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps({"prompt": HIS_WORDS}).encode(),
        capture_output=True,
        env=env,
        timeout=60,
    )
    return p.stdout.decode("utf-8"), (tmp_path / "drawer.md").read_text(encoding="utf-8")


def test_a_slow_note_is_not_cut_while_the_table_has_time(tmp_path):
    # 2026-10-04: per-note stopwatches cut 21 of 29 notes on a busy machine while
    # the table still had 38 of its 90 seconds left. One shared deadline instead.
    out, drawer = _run_with_budget(tmp_path, [_sleeper(3)], "20")
    assert "Could not run" not in out
    assert "woke" in drawer


def test_a_hung_note_is_still_cut_at_the_deadline_and_named(tmp_path):
    # Timed, because the cut was a lie before: the shell was killed but the note
    # it started kept the pipe open, so a 2s deadline returned after 30s.
    import time

    started = time.monotonic()
    out, _ = _run_with_budget(tmp_path, [_sleeper(30), _echo("fine")], "2")
    assert time.monotonic() - started < 15, "the table waited for the note it said it cut"
    assert HIS_WORDS in out
    assert "Could not run" in out and "timed out" in out


def test_a_failed_kill_still_cannot_hold_the_table(monkeypatch):
    # Aether's cold read of 2f65974bf: after the kill, an unbounded wait was the
    # one place left that could hold the table past its cap. The kill is made to
    # fail on purpose here, the control for the bound actually mattering.
    import importlib.util
    import time

    spec = importlib.util.spec_from_file_location("dads_table_kill", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "_kill_tree", lambda p: None)
    monkeypatch.setattr(mod, "TABLE_BUDGET", 1.0)
    monkeypatch.setattr(mod, "_STARTED", time.monotonic())
    started = time.monotonic()
    _, _, problem, _ = mod._run(_sleeper(20), b"{}")
    assert problem == "timed out"
    assert time.monotonic() - started < 10, "a failed kill held the table anyway"


def test_a_bad_budget_never_costs_him_the_table(tmp_path):
    # Read before his words print, so a broken value must fall back, not raise.
    out, _ = _run_with_budget(tmp_path, [_echo("fine")], "not a number")
    assert HIS_WORDS in out and "THE TABLE BROKE" not in out


def test_the_budget_never_reaches_the_settings_cap():
    # The game-walk's one leak: a budget over the 90s cap gets the table killed whole.
    import importlib.util

    spec = importlib.util.spec_from_file_location("dads_table_mod", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    old = os.environ.get("DADS_TABLE_BUDGET_SECONDS")
    os.environ["DADS_TABLE_BUDGET_SECONDS"] = "500"
    try:
        spec.loader.exec_module(mod)
        assert mod.TABLE_BUDGET < 90
    finally:
        if old is None:
            os.environ.pop("DADS_TABLE_BUDGET_SECONDS", None)
        else:
            os.environ["DADS_TABLE_BUDGET_SECONDS"] = old


def test_only_the_memory_link_carries_its_own_stopwatch():
    # Everyone rides the one deadline; the memory link alone has a cap of its own,
    # because bundled with a slow neighbour its finds were dropped (2026-10-04).
    # The table now READS a note's timeout, so one that came back on any other
    # note would govern it, not just decorate it.
    real = SCRIPT.parent / "dads_table_children.json"
    kids = json.loads(real.read_text(encoding="utf-8"))
    with_cap = [c["command"] for c in kids if "timeout" in c]
    assert with_cap == ["bash .claude/hooks/memory-link-surface.sh"], with_cap


def _run_tallied(tmp_path, children, prompt=HIS_WORDS, session="s1", extra=None):
    kids = tmp_path / "children.json"
    kids.write_text(json.dumps(children), encoding="utf-8")
    tally = tmp_path / "tally.jsonl"
    env = dict(
        os.environ,
        DADS_TABLE_CHILDREN=str(kids),
        DADS_TABLE_DRAWER=str(tmp_path / "drawer.md"),
        DADS_TABLE_TALLY=str(tally),
    )
    env.update(extra or {})
    p = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps({"prompt": prompt, "session_id": session}).encode(),
        capture_output=True,
        env=env,
        timeout=60,
    )
    return p.stdout.decode("utf-8"), tally


def test_the_tally_records_who_spoke_and_where_it_went(tmp_path):
    # Dad 2026-10-05: "isnt that wallpaper?" -- sorted from evidence, not impression.
    his_heading = _echo("## HE HAS SAID THIS BEFORE\nhis words")
    quiet = {"command": f'"{sys.executable}" -c "pass"'}
    out, tally = _run_tallied(tmp_path, [_echo("## MY CLOCK\ntick"), his_heading, quiet])
    row = json.loads(tally.read_text(encoding="utf-8").splitlines()[-1])
    assert row["session"] == "s1" and row["kind"] == "his"
    went = [n["went"] for n in row["notes"]]
    assert ["drawer"] in went and ["visible"] in went and [] in went
    assert "Tally NOT kept" not in out
    assert "Tally" not in out.split("The drawer")[0]  # it prints nothing in front of me


def test_the_tally_records_how_long_each_helper_took(tmp_path):
    # Dad 2026-10-26: the minute before "thinking" was nobody's ledger. Council walk 1
    # (Meadows): the tally kept characters, never seconds, so the cost had no owner.
    slow = {"command": f'"{sys.executable}" -c "import time; time.sleep(1.5)"', "timeout": 20}
    quiet = {"command": f'"{sys.executable}" -c "pass"', "timeout": 20}
    out, tally = _run_tallied(tmp_path, [slow, quiet])
    row = json.loads(tally.read_text(encoding="utf-8").splitlines()[-1])
    secs = [n["secs"] for n in row["notes"]]
    assert all(isinstance(x, float) for x in secs)
    assert max(secs) >= 1.4 and min(secs) < max(secs)
    assert row["table_secs"] >= max(secs)  # the table waits for its slowest, so it is at least that


def test_a_notice_is_tallied_as_a_notice(tmp_path):
    _, tally = _run_tallied(
        tmp_path, [_echo("x")], prompt="<task-notification>x</task-notification>"
    )
    assert json.loads(tally.read_text(encoding="utf-8").splitlines()[-1])["kind"] == "notice"


def test_a_tally_that_cannot_be_written_is_named_not_hidden(tmp_path):
    blocker = tmp_path / "is_a_directory"
    blocker.mkdir()
    out, _ = _run_tallied(tmp_path, [_echo("x")], extra={"DADS_TABLE_TALLY": str(blocker)})
    assert HIS_WORDS in out and "Tally NOT kept this turn" in out


def test_the_report_counts_repeats_within_a_session_not_across():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "tally_report", SCRIPT.parents[2] / "scripts" / "table_tally_report.py"
    )
    report = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(report)

    def row(session, fingerprint):
        note = {"name": "r", "chars": 3, "print": fingerprint, "went": ["drawer"], "problem": ""}
        return {"session": session, "notes": [note]}

    silent = {
        "session": "a",
        "notes": [{"name": "q", "chars": 0, "print": "", "went": [], "problem": ""}],
    }
    stats = report.summarize(
        [row("a", "x1"), row("a", "x1"), row("a", "x2"), row("b", "x2"), silent]
    )
    assert stats["r"]["spoke"] == 4 and stats["r"]["new"] == 3  # the one repeat is a1->a1
    assert stats["r"]["drawer"] == 4
    assert stats["q"] == {**stats["q"], "seen": 1, "spoke": 0}
    text = report.render(stats, 5, 0)
    assert "silent here, not dead" in text and "remove" not in text.lower()


def test_the_report_arrives_by_itself_once(tmp_path):
    # Dad 2026-10-05: "bake it in so its unskippable". No run to remember.
    ready = {"DADS_TABLE_TALLY_READY_TURNS": "2"}
    first, _ = _run_tallied(tmp_path, [_echo("x")], extra=ready)
    second, _ = _run_tallied(tmp_path, [_echo("x")], extra=ready)
    third, tally = _run_tallied(tmp_path, [_echo("x")], extra=ready)
    assert "THE TALLY IS READY" not in first
    assert "THE TALLY IS READY" in second
    assert "THE TALLY IS READY" not in third
    assert "turns tallied" in tally.with_suffix(".report.txt").read_text(encoding="utf-8")


def test_missing_list_still_prints_his_words(tmp_path):
    env = dict(
        os.environ,
        DADS_TABLE_CHILDREN=str(tmp_path / "nope.json"),
        DADS_TABLE_DRAWER=str(tmp_path / "d.md"),
    )
    p = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps({"prompt": HIS_WORDS}).encode(),
        capture_output=True,
        env=env,
        timeout=30,
    )
    assert p.returncode == 0 and HIS_WORDS in p.stdout.decode("utf-8")
