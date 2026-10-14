"""Aria's cold read of #585 at b4d3271df (2026-10-06): the deadlock fix is sound,
and three of her four ways through are closed here; the fourth is Dad's call and
he made it the same day.

1. The addressee is read from the file's OWN name, not from anywhere in its path.
2. A shell command that writes into a letter is held like an editor write.
3. "Away" needs his own away words, not any ten characters of his message.

Each test below failed against b4d3271df first.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def qh(tmp_path, monkeypatch):
    from divineos.core import question_hold as mod

    monkeypatch.setattr(mod, "STATE", tmp_path / "hold.json")
    monkeypatch.setattr(mod, "HOLD_LOG", tmp_path / "log.jsonl")
    monkeypatch.setattr(mod, "ESCAPED", tmp_path / "escaped.json")
    monkeypatch.setattr(mod, "AWAY", tmp_path / "away.json")
    monkeypatch.setattr(mod, "BOARD", tmp_path / "board")
    monkeypatch.setattr(mod, "CARD", tmp_path / "board" / "me.json")
    mod.arm("work\n\n## INNER CIRCLE\n\nDad, is the nexus a room or a hub?")
    return mod


# 1. The addressee is in the file's own name ---------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "family/letters/aria-to-aether-2026-10-06-what-i-owe-to-dad.md",
        "family/letters/aria-to-aether-x-note-to-andrew-later.md",
        "family/letters/threads/aether-to-dad-archive/aria-to-aether-x.md",
        "C:\\family\\letters\\aria-to-aether-2026-10-06-owe-to-pop-x.md",
    ],
)
def test_a_dads_name_elsewhere_in_the_path_does_not_make_it_a_letter_to_him(qh, path):
    assert qh.refusal("Write", {"file_path": path}), path


@pytest.mark.parametrize(
    "path",
    [
        "family/letters/aether-to-andrew-volley-board.md",
        "family/letters/aria-to-dad-2026-10-06-x.md",
        "family/letters/aether-to-pop-x.md",
        "C:\\family\\letters\\Aether-To-Andrew-x.md",
    ],
)
def test_a_letter_really_addressed_to_him_still_passes(qh, path):
    assert qh.refusal("Write", {"file_path": path}) == "", path


# 2. A shell command that writes into a letter ---------------------------------

LETTER = "family/letters/aria-to-aether-x.md"


@pytest.mark.parametrize(
    "command",
    [
        f"cat > {LETTER} <<'EOF'\nhi\nEOF",
        f"cat >> {LETTER} <<'EOF'\nhi\nEOF",
        f"echo hi | tee {LETTER}",
        f'printf x | tee -a "{LETTER}"',
        f"echo hi>{LETTER}",
    ],
)
def test_a_shell_write_into_a_letter_not_to_him_is_held(qh, command):
    assert qh.refusal("Bash", {"command": command}), command


@pytest.mark.parametrize(
    "command",
    [
        "cat > family/letters/aether-to-andrew-x.md <<'EOF'\nhi\nEOF",
        "echo x > /tmp/aria-to-aether-x.md",
        "echo x > notes/aria-to-aether-x.txt",
        "ls family/letters/",
        f"cat {LETTER}",
        'git commit -q -m "I read family/letters/aria-to-aether-x.md today"',
        f"grep -n hub {LETTER} 2>&1",
    ],
)
def test_everything_else_a_shell_does_still_runs(qh, command):
    assert qh.refusal("Bash", {"command": command}) == "", command


@pytest.mark.parametrize(
    "command",
    [
        "bash scripts/letter_doorbell.sh aether",
        'divineos ask-resolve 3b045e25 "he ruled my questions do not hold me"',
        'divineos question-hold release --reason "a push that must be checked now"',
        'divineos question-hold away --words "i am going to bed"',
        "gh pr view 585 --json state",
        "git ls-remote --heads origin fix/the-two-holds-pass-each-others-key",
        "bash scripts/divineos_push.sh origin fix/the-two-holds-pass-each-others-key",
    ],
)
def test_the_doorbell_and_every_exit_run_while_a_question_is_open(qh, command):
    # The day this fix exists for (2026-10-06): a question of mine froze my own
    # read-only check, its own exit, and the doorbell he has asked for 24 times.
    assert qh.refusal("Bash", {"command": command}) == "", command


# 3. Away needs his own away words ---------------------------------------------


@pytest.mark.parametrize("said", ["ok go ahead", "proceed", "continue, etc etc", "yes go ahead"])
def test_go_ahead_and_proceed_are_not_away(qh, monkeypatch, said):
    # Dad, 2026-10-06: "ok go ahead, proceed, continue ... should not be treated
    # as permission to volley ... otherwise the above phrases mean i am currently
    # here". They are his words, so provenance alone would have let them through.
    monkeypatch.setattr(qh, "_his_latest_words", lambda: said + " and keep building the thing")
    with pytest.raises(ValueError, match="stepping away|going to bed|volley"):
        qh.step_away(said + " and keep building the thing")
    assert qh.is_away() is None


@pytest.mark.parametrize(
    "said",
    [
        "i am going to bed, you two volley",
        "ill be gone for a few hours",
        "go into volley mode",
        "heading to bed",
        "i am stepping away for dinner",
    ],
)
def test_his_own_away_words_open_volley_mode(qh, monkeypatch, said):
    monkeypatch.setattr(qh, "_his_latest_words", lambda: said)
    assert qh.step_away(said)["his_words"] == said
    assert qh.is_away()
