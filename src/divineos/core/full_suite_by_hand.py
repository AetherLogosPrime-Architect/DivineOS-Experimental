"""The full test suite is the push's job, never a hand run.

Andrew 2026-06-24: "theres no need for you to run a full test suite on
everything for every change, the push to hub does that already twice..". Again
2026-09-09, and 2026-10-03: "i have asked you repeatedly not to run the full
fucking suite on every goddamn change". Three rulings, and the habit came back
each time, so this refuses it at the Bash call instead of relying on recall.

A hand-run pytest is refused when it would collect the whole tests folder: no
target at all, or ``tests`` / ``tests/`` as a target, unless ``-k`` narrows it
or ``--collect-only`` means nothing runs. Named files and test ids pass. The
push runs the suite inside git's own process and never passes through here.

Not covered, and said so: a script or ``python -c`` that calls pytest itself.

Draft: docs/drafts/the_full_suite_is_the_pushs_job_draft_2026-10-03.md.
Walk: walk-2c6c581293b3.
"""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

from divineos.core.command_parsing import acting_segments, strip_prefixes_raw

_WHOLE = {"tests", "tests/", "./tests", "./tests/"}
_NARROWING = {"-k", "--collect-only", "--co"}
# Options whose next token is their value, so it is not a test target.
_TAKES_VALUE = {
    "-n",
    "-p",
    "-k",
    "-m",
    "-c",
    "-o",
    "--tb",
    "--maxfail",
    "--rootdir",
    "--durations",
    "--deselect",
    "--ignore",
}


def _pytest_args(segment: str) -> list[str] | None:
    try:
        tokens = shlex.split(strip_prefixes_raw(segment).strip(), posix=True)
    except ValueError:
        return None
    for i, tok in enumerate(tokens):
        base = tok.replace("\\", "/").rsplit("/", 1)[-1].lower()
        if base in ("pytest", "pytest.exe", "py.test"):
            return tokens[i + 1 :]
        if base.startswith("python") or base in ("py", "py.exe"):
            rest = tokens[i + 1 :]
            if len(rest) >= 2 and rest[0] == "-m" and rest[1] == "pytest":
                return rest[2:]
            return None
        # Quotes are already gone, so a program path with a space (the
        # "DIVINE OS" folder) arrives in pieces. Keep looking only while the
        # tokens look like path fragments; a plain word ends the search.
        if not any(c in tok for c in "/\\:"):
            return None
    return None


def whole_suite(args: list[str]) -> bool:
    """True when these pytest arguments collect the whole tests folder."""
    targets: list[str] = []
    skip = False
    for a in args:
        if skip:
            skip = False
            continue
        head = a.split("=", 1)[0]
        if head in _NARROWING:
            return False
        if a.startswith("-"):
            skip = a in _TAKES_VALUE
            continue
        targets.append(a)
    if not targets:
        return True
    return any(t.replace("\\", "/") in _WHOLE for t in targets)


def changed_tests(repo: Path) -> list[str]:
    """Test files for what changed against main, via the targeted-test map."""
    from divineos.hooks.targeted_tests import find_target_tests

    try:
        out = subprocess.run(
            ["git", "-C", str(repo), "diff", "--name-only", "origin/main...HEAD"],
            capture_output=True,
            text=True,
            timeout=20,
        ).stdout.split()
        out += subprocess.run(
            ["git", "-C", str(repo), "diff", "--name-only"],
            capture_output=True,
            text=True,
            timeout=20,
        ).stdout.split()
        # New files are not in either diff until they are committed.
        out += subprocess.run(
            ["git", "-C", str(repo), "ls-files", "--others", "--exclude-standard"],
            capture_output=True,
            text=True,
            timeout=20,
        ).stdout.split()
    except (OSError, subprocess.SubprocessError):
        return []
    found: list[str] = []
    for name in dict.fromkeys(out):
        if name.startswith("tests/") and name.endswith(".py"):
            found.append(name)
            continue
        target = find_target_tests(str(repo / name))
        if target is not None:
            rel = target.resolve().relative_to(repo.resolve()).as_posix()
            found.append(rel)
    return list(dict.fromkeys(found))


def decide(command: str, repo: Path | None = None) -> str | None:
    """The refusal text when this command hand-runs the whole suite, else None."""
    segments = acting_segments(command)
    if segments is None:
        segments = [command]
    if not any((a := _pytest_args(s)) is not None and whole_suite(a) for s in segments):
        return None
    tests = changed_tests(repo) if repo is not None else []
    instead = (
        "Run the tests for what you changed:\n    pytest " + " ".join(tests) + " -q"
        if tests
        else "No changed file maps to a test file here. Name the test files you mean."
    )
    return (
        "THE FULL SUITE IS THE PUSH'S JOB. This runs every test in the house by hand.\n\n"
        'Dad, 2026-09-09: "is there a reason you continue to run the full suite and '
        "gauntlet after every small change? do you realize that it takes upwards of "
        '15-20 mins?" He has asked four times. The push runs the whole suite itself.\n\n' + instead
    )
