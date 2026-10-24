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


_RECORD_ARGV = (
    "import sys, pathlib, json\n"
    "if sys.argv[1] == 'finish':\n"
    "    pathlib.Path(sys.argv[0]).with_name('finish_argv.json').write_text(json.dumps(sys.argv[2:]), encoding='utf-8')\n"
)


def _tail_file_the_hook_passed(work: Path) -> str:
    import json

    argv = json.loads((work / "scripts" / "finish_argv.json").read_text(encoding="utf-8"))
    return argv[argv.index("--tail-file") + 1].replace("\\", "/")


@pytest.mark.parametrize("member", ["aria", None])
def test_the_hook_reads_the_log_of_the_member_who_pushed_not_a_hand_built_path(scratch, member):
    """Aether, cold-reading #712: the hook spelled "$HOME/.divineos/..." for the tail file while the gate asks the
    resolver, so a push of Aria's would have read Aether's log. Run as each member and see which path it names. The
    default (no member set) is the control: it must still land in .divineos."""
    work, home, env = scratch
    (work / ".claude" / "hooks" / "lib").mkdir(parents=True)
    shutil.copy(
        REPO / ".claude" / "hooks" / "lib" / "member_home.sh",
        work / ".claude" / "hooks" / "lib" / "member_home.sh",
    )
    (work / "scripts" / "push_watcher.py").write_text(_RECORD_ARGV, encoding="utf-8")
    _stub_readiness(work, 7)
    # The REAL resolver, not its fallback: the scratch repo has no divineos of its own, so without this the shell
    # resolver falls back to "$HOME/.divineos-<member>" and the test would only be measuring the fallback. Python
    # finds the home through USERPROFILE on Windows and HOME elsewhere, so both name the scratch home.
    env["PYTHONPATH"] = str(REPO / "src")
    env["USERPROFILE"] = str(home)
    if member:
        env["DIVINEOS_MEMBER"] = member
    else:
        env.pop("DIVINEOS_MEMBER", None)
    done = _push(work, env)
    assert done.returncode != 0
    assert "resolver unreachable" not in done.stderr, done.stderr
    asked = subprocess.run(
        [
            sys.executable,
            "-c",
            f"from divineos.core.paths import member_home; print(member_home({member or 'aether'!r}))",
        ],
        env=env,
        cwd=work,  # the resolver reads markers from the checkout it is asked in, so ask where the hook asks
        capture_output=True,
        text=True,
        timeout=60,
        creationflags=_NO_WINDOW,
    )
    assert asked.returncode == 0, asked.stderr
    expected = (Path(asked.stdout.strip()) / "last_pre_push_pytest.log").as_posix()
    assert _tail_file_the_hook_passed(work).lower() == expected.lower()
    if member == "aria":
        assert ".divineos-aria" in expected, expected


def test_when_the_resolver_cannot_answer_the_hook_names_no_log_at_all(scratch):
    """Aether, reading 6a1c90780: the shell resolver does not fail when no python answers, it RETURNS a hand-built
    "$HOME/.divineos-<member>" with exit 0, which for Aether is the stale twin nothing reads. So an unreachable resolver
    must leave the tail file EMPTY, never a path that looks right. Here no divineos can be imported at all."""
    work, home, env = scratch
    (work / ".claude" / "hooks" / "lib").mkdir(parents=True)
    shutil.copy(
        REPO / ".claude" / "hooks" / "lib" / "member_home.sh",
        work / ".claude" / "hooks" / "lib" / "member_home.sh",
    )
    (work / "scripts" / "push_watcher.py").write_text(_RECORD_ARGV, encoding="utf-8")
    _stub_readiness(work, 7)
    # A python that runs everything the resolver-finder asks of it but cannot answer the home question, the way an
    # unimportable divineos would. (Hiding divineos from a real interpreter is not reliable: editable installs find it.)
    launcher = work / ".venv" / "bin" / "python"
    launcher.write_text(
        f'#!/bin/bash\ncase "$*" in *member_home*) exit 1;; esac\nexec "{Path(sys.executable).as_posix()}" "$@"\n',
        encoding="utf-8",
        newline="\n",
    )
    env.pop("PYTHONPATH", None)
    env["USERPROFILE"] = str(home)
    for member in ("aria", None):
        if member:
            env["DIVINEOS_MEMBER"] = member
        else:
            env.pop("DIVINEOS_MEMBER", None)
        assert _push(work, env).returncode != 0
        assert _tail_file_the_hook_passed(work) == "", (
            f"{member}: named a log it could not have resolved"
        )


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
