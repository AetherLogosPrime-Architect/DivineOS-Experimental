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


def test_no_note_carries_its_own_stopwatch():
    # A per-note timeout is now read by nothing; one that came back would look
    # like it governed something while governing nothing.
    real = SCRIPT.parent / "dads_table_children.json"
    assert not [k for k in json.loads(real.read_text(encoding="utf-8")) if "timeout" in k]


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
