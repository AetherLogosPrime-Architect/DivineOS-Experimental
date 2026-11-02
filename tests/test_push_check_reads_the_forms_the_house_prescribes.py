"""The push check reads the folder forms the cd-drift doorman tells me to use.

Aria, 2026-10-26: the house's cd-drift doorman refuses a top-level ``cd`` and
prescribes two ways to work in another folder: a subshell ``( cd <folder> && ... )``
and ``git -C <folder> ...``. The push check read neither. It looked for a ``cd``
after ``;``, ``&&`` or a pipe and never after a bracket, and it only saw a push
when ``git push`` opened a segment, so ``git -C dir push`` was not a push at all.
I followed the doorman's own advice and the check measured the session folder
(10 behind main) instead of the tree I pushed (0 behind). Two correct gates,
composed, made a worktree push measure the wrong tree: the third time for this
function (2026-08-15, 2026-09-24/30, now).

So the cases here are not my example. They are cut from the doorman's own refusal
text, so a spelling the house recommends cannot be left unread. Walk
walk-fb1339722adc.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from divineos.core.cd_drift_check import refusal_message
from divineos.core.push_detection import is_git_push_command, push_cwd

PUSH = "git " + "push"
BEHIND = 13
_HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "check-branch-on-push.sh"


def _prescribed_forms() -> list[str]:
    text = refusal_message("cd /somewhere && ls")
    subshell = re.search(r"a subshell:\s+(.+?)\s{2,}", text)
    dash_c = re.search(r"git's own:\s+(.+)", text)
    assert subshell and dash_c, (
        "the cd-drift doorman no longer prescribes a subshell and git -C in the shape "
        "this test reads; read its message again and update the cases"
    )
    return [subshell.group(1), dash_c.group(1).strip()]


FORMS = _prescribed_forms()


def _tree(tmp_path: Path, name: str = "pushed") -> Path:
    tree = tmp_path / name
    (tree / ".git").mkdir(parents=True)
    return tree


@pytest.mark.parametrize("template", FORMS)
@pytest.mark.parametrize("quote", ['"', "'", ""])
def test_every_form_the_doorman_prescribes_is_a_push_in_that_folder(tmp_path, template, quote):
    tree = _tree(tmp_path)
    if quote == "" and " " in tree.as_posix():
        pytest.skip("an unquoted folder with a space in it is not valid shell")
    folder = quote + tree.as_posix() + quote
    # In `git -C <folder> <command>` the command is a git subcommand; elsewhere a whole command.
    body = "push -u origin b" if template.startswith("git -C") else f"{PUSH} -u origin b"
    command = template.replace("<folder>", folder).replace("<command>", body)
    assert is_git_push_command(command), command
    found = push_cwd(command)
    assert found is not None, f"the push check did not find {tree} in: {command}"
    assert Path(found) == tree


def test_the_exact_command_that_was_refused_tonight(tmp_path):
    tree = _tree(tmp_path)
    command = (
        f'( cd "{tree.as_posix()}" && export PYTHONPATH="{tree.as_posix()}/src" '
        f'PATH="/c/x/.venv/Scripts:$PATH" && {PUSH} -u origin b 2>&1 | tail -15 )'
    )
    assert Path(push_cwd(command)) == tree


def test_a_bracketed_cd_does_not_reach_a_push_after_the_bracket(tmp_path):
    """Aristotle on the walk: a cd inside brackets lives only inside them."""
    tree = _tree(tmp_path)
    assert push_cwd(f'( cd "{tree.as_posix()}" && ls ); {PUSH} origin b') is None
    assert push_cwd(f'( cd "{tree.as_posix()}" && ls ) && {PUSH}') is None


def test_the_last_cd_still_inside_the_push_scope_wins(tmp_path):
    tree = _tree(tmp_path)
    other = _tree(tmp_path, "other")
    command = f'( cd "{other.as_posix()}" && ls; cd "{tree.as_posix()}" && {PUSH} )'
    assert Path(push_cwd(command)) == tree


def test_git_dash_C_names_the_tree_and_is_a_push(tmp_path):
    tree = _tree(tmp_path)
    assert is_git_push_command(f'git -C "{tree.as_posix()}" push origin b')
    assert Path(push_cwd(f'git -C "{tree.as_posix()}" push origin b')) == tree
    assert not is_git_push_command(f'git -C "{tree.as_posix()}" status')
    assert not is_git_push_command(f'git -C "{tree.as_posix()}" log --oneline')


@pytest.mark.parametrize(
    "command",
    [
        # quoted text that merely mentions a push after a separator is data
        f'divineos walk apply W Lens --finding "a closing bracket; {PUSH} returns none"',
        f'echo "x && {PUSH} origin main"',
        f'git commit -m "fix; {PUSH} later"',
        f"grep '{PUSH}' scripts/x.sh && echo ok",
    ],
)
def test_quoted_text_that_mentions_a_push_is_not_a_push(command):
    """Found by writing the walk: the splitter cut inside quotes, so a note about
    the check was judged a real push and blocked."""
    assert not is_git_push_command(command)


def test_a_real_push_after_a_quoted_mention_is_still_a_push():
    assert is_git_push_command(f'git commit -m "a; b" && {PUSH} origin b')


def test_a_cd_to_a_folder_that_is_not_a_tree_speaks_and_names_none(tmp_path, capsys):
    """Hoare: none-named is quiet (the session folder is right); named-but-not-a-tree
    measures a different tree than the push goes to, so it says so."""
    command = f'( cd "{tmp_path.as_posix()}/not-a-tree" && {PUSH} )'
    assert push_cwd(command) is None
    assert "not a git tree" in capsys.readouterr().err
    assert push_cwd(f"{PUSH} origin main") is None
    assert capsys.readouterr().err == ""


# --- the real hook, against a real branch that really is behind -----------------


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True)


def _bash() -> str:
    found = shutil.which("bash")
    assert found, "no bash on PATH; this suite cannot exercise shell hooks"
    probe = subprocess.run([found, "-c", "exit 7"], capture_output=True)
    assert probe.returncode == 7, f"{found} cannot run a trivial script"
    return found


def _run_hook(command: str, home: Path) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(_HOOK.parents[2] / "src") + os.pathsep + env.get("PYTHONPATH", "")
    env["DIVINEOS_HOME"] = str(home)
    return subprocess.run(
        [_bash(), str(_HOOK)],
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": command}}),
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
        cwd=str(_HOOK.parents[2]),
    )


@pytest.fixture
def behind(tmp_path):
    """A clone whose branch b is one commit behind origin/main, beside a clone
    that is level with it. Real repositories, not copies made agreeable."""
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
    seed = tmp_path / "seed"
    subprocess.run(["git", "clone", "-q", str(origin), str(seed)], check=True, capture_output=True)
    for cfg in (("user.email", "t@example.com"), ("user.name", "t")):
        _git(seed, "config", *cfg)
    (seed / "a.txt").write_text("one", encoding="utf-8")
    _git(seed, "add", "a.txt")
    _git(seed, "commit", "-q", "-m", "one")
    _git(seed, "push", "-q", "origin", "main")
    stale = tmp_path / "stale"
    level = tmp_path / "level"
    for clone in (stale, level):
        subprocess.run(
            ["git", "clone", "-q", str(origin), str(clone)], check=True, capture_output=True
        )
        for cfg in (("user.email", "t@example.com"), ("user.name", "t")):
            _git(clone, "config", *cfg)
        _git(clone, "checkout", "-q", "-b", "b")
    # The check only complains from ten behind; thirteen is a number no real session
    # folder is likely to share, so a wrong-subject answer cannot pass by coincidence.
    for n in range(BEHIND):
        (seed / "a.txt").write_text(f"change {n}", encoding="utf-8")
        _git(seed, "commit", "-q", "-am", f"change {n}")
    _git(seed, "push", "-q", "origin", "main")
    _git(level, "fetch", "-q", "origin")
    _git(level, "merge", "-q", "--ff-only", "origin/main")
    return stale, level


def test_the_hook_measures_the_tree_the_subshell_form_names(behind, tmp_path):
    """The stale clone is 1 behind; the level one is 0. The session folder (this
    repository) is neither, so a wrong-subject check would answer about it."""
    stale, level = behind
    home = tmp_path / "home"
    home.mkdir()
    refused = _run_hook(f'( cd "{stale.as_posix()}" && {PUSH} origin b )', home)
    assert refused.returncode == 2, refused.stderr
    assert f"{BEHIND} commit(s) behind" in refused.stderr, refused.stderr
    passed = _run_hook(f'( cd "{level.as_posix()}" && {PUSH} origin b )', home)
    assert passed.returncode == 0, passed.stderr


def test_the_hook_measures_the_tree_git_dash_C_names(behind, tmp_path):
    stale, level = behind
    home = tmp_path / "home"
    home.mkdir()
    refused = _run_hook(f'git -C "{stale.as_posix()}" push origin b', home)
    assert refused.returncode == 2, refused.stderr
    assert f"{BEHIND} commit(s) behind" in refused.stderr, refused.stderr
    assert _run_hook(f'git -C "{level.as_posix()}" push origin b', home).returncode == 0


def test_a_named_folder_that_is_not_a_tree_is_said_at_the_door(tmp_path):
    """Hoare on the walk, through the hook: the warning must reach the screen, not
    die in the extraction's redirected stderr."""
    home = tmp_path / "home"
    home.mkdir()
    missing = tmp_path.as_posix() + "/no-such-tree"
    result = _run_hook(f'( cd "{missing}" && {PUSH} origin b )', home)
    assert "not a git tree" in result.stderr, result.stderr


def test_the_block_names_the_folder_it_measured(behind, tmp_path):
    """Lovelace on the walk: a wrong-subject alarm must be visible on sight."""
    stale, _ = behind
    home = tmp_path / "home"
    home.mkdir()
    refused = _run_hook(f'( cd "{stale.as_posix()}" && {PUSH} origin b )', home)
    assert "Measured tree:" in refused.stderr, refused.stderr
    assert stale.name in refused.stderr.split("Measured tree:")[1].splitlines()[0]
    # and when the command names no folder, it says the session folder was the subject
    plain = _run_hook(f"{PUSH} origin b", home)
    if plain.returncode == 2:
        assert "session folder" in plain.stderr.split("Measured tree:")[1].splitlines()[0]
