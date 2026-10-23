"""The pre-push hook the installer writes starts the watcher, and a broken watcher can never change a push's verdict.

Breaker's first finding (walk-193e1c70464f): BUILT-BUT-UNWIRED. A watcher script does nothing unless the generated hook
starts it, so this renders the hook text out of setup/setup-hooks.sh, installs it in a scratch repository, and pushes.

WHAT THIS DOES NOT COVER: the real gates behind the hook (the stub stands in for the readiness script), and the hook
running under the tool that normally launches a push. It covers the watcher's own wiring and its fail-open rule.

The scratch repositories live OUTSIDE the project folder on purpose: a `git init` that fails partway can make git walk up
into the enclosing repository, and that is a known way the real repository's config has been flipped.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
INSTALLER = REPO / "setup" / "setup-hooks.sh"
WATCHER = REPO / "scripts" / "push_watcher.py"
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _hook_text() -> str:
    text = INSTALLER.read_text(encoding="utf-8")
    match = re.search(r"cat > \"\$HOOKS_DIR/pre-push\" << 'EOF'\n(.*?)\nEOF\n", text, re.S)
    assert match, (
        "could not find the pre-push hook text in the installer: this reader is blind, not the hook clean"
    )
    return match.group(1) + "\n"


def _git(args, cwd, env):
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        creationflags=_NO_WINDOW,
    )


@pytest.fixture
def scratch():
    root = Path(tempfile.mkdtemp(prefix="pw_wired_"))
    home = root / "home"
    home.mkdir()
    work, bare = root / "work", root / "remote.git"
    env = dict(os.environ)
    env["HOME"] = str(home)
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        env.pop(key, None)
    work.mkdir()
    _git(["init", "-q", "-b", "main", str(work)], root, env)
    _git(["init", "-q", "--bare", str(bare)], root, env)
    # THE CONTROL: prove the scratch repo is its own repository, not the enclosing one, before trusting any result.
    top = _git(["rev-parse", "--show-toplevel"], work, env).stdout.strip().replace("\\", "/")
    assert Path(top).resolve() == work.resolve(), f"scratch repo resolved to {top}, not {work}"
    for cfg in (["user.email", "t@t"], ["user.name", "t"]):
        _git(["config", *cfg], work, env)
    _git(["remote", "add", "origin", str(bare)], work, env)
    (work / "scripts").mkdir()
    (work / ".claude" / "hooks").mkdir(parents=True)
    shutil.copy(
        REPO / ".claude" / "hooks" / "_lib.sh", work / ".claude" / "hooks" / "_lib.sh"
    )  # the python resolver the hook asks
    # A real checkout has its own .venv, which the resolver accepts first. Without one it asks whether the divineos an
    # interpreter can see lives under THIS repository and (rightly) refuses a different checkout's. A stand-in launcher
    # keeps the resolver honest and avoids a junction, whose cleanup could follow it into the real environment.
    (work / ".venv" / "bin").mkdir(parents=True)
    launcher = work / ".venv" / "bin" / "python"
    launcher.write_text(
        f'#!/bin/bash\nexec "{Path(sys.executable).as_posix()}" "$@"\n',
        encoding="utf-8",
        newline="\n",
    )
    launcher.chmod(0o755)
    (work / "a.txt").write_text("a")
    _git(["add", "a.txt"], work, env)
    _git(["commit", "-q", "-m", "one"], work, env)
    hook = work / ".git" / "hooks" / "pre-push"
    hook.write_text(_hook_text(), encoding="utf-8", newline="\n")
    hook.chmod(0o755)
    yield work, home, env
    try:
        shutil.rmtree(root)
    except (
        OSError
    ) as exc:  # fail-soft: cleanup after the test; a locked temp file must not fail it, but is said
        print(f"could not remove the scratch folder {root}: {exc}", file=sys.stderr)


def _stub_readiness(work: Path, exit_code: int):
    stub = work / "scripts" / "check_push_readiness.sh"
    stub.write_text(
        f"#!/bin/bash\ncat > /dev/null\nexit {exit_code}\n", encoding="utf-8", newline="\n"
    )
    stub.chmod(0o755)


def _push(work, env):
    return _git(["push", "origin", "HEAD:refs/heads/x"], work, env)


def _reports(home: Path):
    return list((home / ".divineos" / "push_reports").glob("push-*.json"))


def test_the_installer_hook_text_starts_the_watcher():
    text = _hook_text()
    assert "push_watcher.py" in text and 'start --parent "$WATCH_WINPID"' in text
    assert "/proc/$$/winpid" in text, (
        "the watcher must be given the Windows process number, not the MSYS one"
    )


def test_a_refused_push_ends_with_a_plain_sentence_and_leaves_a_report(scratch):
    work, home, env = scratch
    shutil.copy(WATCHER, work / "scripts" / "push_watcher.py")
    _stub_readiness(work, 7)
    done = _push(work, env)
    assert done.returncode != 0
    assert "a check stopped it before the tests ran" in done.stderr, done.stderr
    assert len(_reports(home)) == 1


def test_a_passing_push_prints_nothing_extra_and_leaves_no_report(scratch):
    work, home, env = scratch
    shutil.copy(WATCHER, work / "scripts" / "push_watcher.py")
    _stub_readiness(work, 0)
    done = _push(work, env)
    assert done.returncode == 0, done.stderr
    assert "This push" not in done.stderr and _reports(home) == []


def test_a_missing_watcher_does_not_stop_the_push_and_says_so(scratch):
    work, home, env = scratch
    _stub_readiness(work, 0)
    done = _push(work, env)
    assert done.returncode == 0, done.stderr
    log = (home / ".divineos" / "push_reports" / "without_watcher.log").read_text()
    assert "pushed WITHOUT the watcher" in log


def test_no_python_for_the_watcher_is_said_once_and_the_push_goes_on(scratch):
    """Aether's sixth attack: the hook cannot assume which python runs. With no resolver it says so in one line."""
    work, home, env = scratch
    shutil.copy(WATCHER, work / "scripts" / "push_watcher.py")
    (work / ".claude" / "hooks" / "_lib.sh").unlink()
    _stub_readiness(work, 0)
    done = _push(work, env)
    assert done.returncode == 0, done.stderr
    assert done.stderr.count("watcher python missing") == 1, done.stderr


def test_a_report_that_hangs_cannot_hold_a_failed_push_open(scratch):
    """Aether's fifth attack: the finish call runs under a hard three-second limit."""
    import time

    work, home, env = scratch
    (work / "scripts" / "push_watcher.py").write_text(
        "import sys, time\nif sys.argv[1] == 'finish':\n    time.sleep(60)\n", encoding="utf-8"
    )
    _stub_readiness(work, 7)
    began = time.time()
    done = _push(work, env)
    assert done.returncode != 0
    assert time.time() - began < 30, "a hung report held the failed push open"
    assert "could not build the report" in done.stderr


def test_a_broken_watcher_cannot_change_the_verdict(scratch):
    """The invariant: the watcher's own failure never reaches the hook's exit status, in either direction."""
    work, home, env = scratch
    (work / "scripts" / "push_watcher.py").write_text("this is not python (\n")
    _stub_readiness(work, 0)
    assert _push(work, env).returncode == 0, (
        "a broken watcher must not turn a passing push into a failure"
    )
    _stub_readiness(work, 7)
    assert _push(work, env).returncode != 0, (
        "a broken watcher must not turn a failing push into a pass"
    )
