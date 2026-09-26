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
