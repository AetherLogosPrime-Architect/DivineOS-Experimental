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

import re
import shlex
import subprocess
from pathlib import Path

from divineos.core.command_parsing import split_shell_segments, strip_prefixes_raw

# Nothing runs under these.
_COLLECT_ONLY = {"--collect-only", "--co"}
# These narrow only by their expression (Aletheia added -m, 2026-10-03). Aria,
# 2026-10-04: an empty one, or one that opens with "not", leaves the whole
# folder selected, so the flag alone proves nothing.
_EXPRESSION = {"-k", "-m"}
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
    """The arguments after pytest, wherever pytest sits in the segment.

    Aletheia, 2026-10-04, the fifth round: `timeout 600 pytest`, `nohup`,
    `nice`, `sudo`, `xargs` and every other word that runs the command after
    it walked past a check that expected pytest first. Listing runners is the
    list that keeps leaking, so pytest is found anywhere and everything in
    front of it is treated as a runner. The one exception is a program that
    only READS text (grep, git, cat...), where pytest is data: that list can
    only be wrong loudly, by refusing an honest search, never silently.
    """
    try:
        tokens = shlex.split(strip_prefixes_raw(segment).strip(), posix=True)
    except ValueError:
        return None
    if not tokens or _program(tokens[0]) in _READERS:
        return None
    for i, tok in enumerate(tokens):
        if _program(tok) in ("pytest", "py.test"):
            return tokens[i + 1 :]
        if tok == "-m" and i + 1 < len(tokens) and tokens[i + 1] == "pytest":
            return tokens[i + 2 :]
    return None


def _program(token: str) -> str:
    return token.replace("\\", "/").rsplit("/", 1)[-1].lower().removesuffix(".exe")


# Programs that read or show text. A pytest after one of these is a word being
# searched for or printed, not a run.
_READERS = {
    "grep",
    "egrep",
    "fgrep",
    "rg",
    "git",
    "cat",
    "ls",
    "echo",
    "printf",
    "head",
    "tail",
    "less",
    "more",
    "wc",
    "find",
    "sed",
    "awk",
    "which",
    "type",
    "man",
    "diff",
    "file",
}


def _points_at_everything(target: str, roots: tuple[Path, ...], cwd: Path | None) -> bool:
    """Where this target resolves, not how it is spelled (Aletheia, 2026-10-03).

    A target the check cannot place counts as everything, because a path that
    cannot be resolved is the one a route around this would use: a shell
    substitution, a glob the shell expands only after this has read it (Aria,
    2026-10-04), or any target after a cd to somewhere that could not be
    followed.
    """
    path = target.split("::", 1)[0]
    if cwd is None or any(c in path for c in "$`*?["):
        return True
    resolved = (cwd / path).resolve()
    return any(resolved in (r, r / "tests") for r in roots)


def _narrows(expression: str) -> bool:
    expression = expression.strip()
    return bool(expression) and expression.split()[0] != "not"


def whole_suite(args: list[str], base: Path | None = None) -> bool:
    """True when these pytest arguments collect the whole tests folder."""
    resolved = (base or Path.cwd()).resolve()
    return _whole_suite_from(args, resolved, resolved)


def _whole_suite_from(args: list[str], base: Path, here: Path | None) -> bool:
    """``base`` is the repository; ``here`` is where the shell stands after any
    cd, None when a cd could not be followed. The whole suite is either place,
    or its tests folder."""
    roots: tuple[Path, ...] = (base,) if here is None else (base, here)
    targets: list[str] = []
    i = 0
    while i < len(args):
        a = args[i]
        head, eq, value = a.partition("=")
        if head in _COLLECT_ONLY:
            return False
        if head in _EXPRESSION:
            if not eq:
                value = args[i + 1] if i + 1 < len(args) else ""
                i += 1
            if _narrows(value):
                return False
            i += 1
            continue
        if a.startswith("-"):
            if a in _TAKES_VALUE:
                i += 1
            i += 1
            continue
        targets.append(a)
        i += 1
    if not targets:
        return True
    return any(_points_at_everything(t, roots, here) for t in targets)


# Programs that run a string they are handed as another command line.
_SHELLS = {"bash", "sh", "zsh", "dash", "ksh", "fish", "pwsh", "powershell", "cmd"}


def _runs_a_string(segment: str) -> bool:
    """True for `bash -c "..."`, `sh -lc ...`, `cmd /c ...`, `python -c ...`.

    Aletheia, 2026-10-04: the command inside is a string this check never
    parses, so a pytest in it cannot be placed.
    """
    try:
        tokens = shlex.split(strip_prefixes_raw(segment).strip(), posix=True)
    except ValueError:
        return True
    if not tokens:
        return False
    prog = tokens[0].replace("\\", "/").rsplit("/", 1)[-1].lower().removesuffix(".exe")
    flags = tokens[1:3]
    if prog in _SHELLS:
        return any(
            re.fullmatch(r"-[a-z]*c[a-z]*", f) or f.lower() in ("/c", "-command") for f in flags
        )
    if prog.startswith("python") or prog in ("py",):
        return "-c" in flags
    return False


def _cd_target(segment: str) -> str | None:
    """The directory a ``cd``/``pushd`` segment moves to, or None if it is not one."""
    try:
        tokens = shlex.split(strip_prefixes_raw(segment).strip(), posix=True)
    except ValueError:
        return None
    if not tokens or tokens[0] not in ("cd", "pushd"):
        return None
    return tokens[1] if len(tokens) > 1 else "~"


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
    # The raw split, not acting_segments: that one drops cd as inert, which is
    # right for the gates it serves and is exactly the segment this one needs.
    segments = split_shell_segments(command)
    if segments is None:
        segments = [command]
    base = (repo or Path.cwd()).resolve()
    # Aria, 2026-10-04: "cd src && pytest ../tests" ran everything, because the
    # check read the target from the repository, not from where the cd left
    # the shell. Walk the segments in order and carry the cd forward. A cd
    # this cannot follow (a variable, ~, -) leaves the place unknown, and an
    # unknown place counts as everything.
    here: Path | None = base
    hit = False
    # Aletheia, 2026-10-04: "(cd src; pytest ../tests)" and "{ ...; }" run in a
    # group the splitter cuts into pieces, so a brace group's pytest arrives
    # with no brace on it. Carry the depth across segments: a run inside any
    # group, or inside a string handed to another shell, cannot be placed and
    # counts as everything. Failing closed refuses a named file inside a
    # wrapper too; the way out is to run it unwrapped.
    depth = 0
    for s in segments:
        stripped = s.strip()
        if stripped.startswith(("(", "{")):
            depth += 1
        hidden = depth > 0 or _runs_a_string(s)
        if stripped.endswith((")", "}")):
            depth = max(0, depth - 1)
        if "pytest" in s.lower() and hidden:
            hit = True
            break
        moved = _cd_target(s)
        if moved is not None:
            if here is None or moved == "-" or any(c in moved for c in "$`~*?["):
                here = None
            else:
                here = (here / moved).resolve()
            continue
        args = _pytest_args(s)
        if args is not None and _whole_suite_from(args, base, here):
            hit = True
            break
    if not hit:
        return None
    tests = changed_tests(repo) if repo is not None else []
    # Tannen, 2026-10-04: after a cd these paths would read from the wrong
    # place, so name where they are written from.
    instead = (
        "Run the tests for what you changed, from the repository root:\n    pytest "
        + " ".join(tests)
        + " -q"
        if tests
        else "No changed file maps to a test file here. Name the test files you mean."
    )
    return (
        "THE FULL SUITE IS THE PUSH'S JOB. This runs every test in the house by hand.\n\n"
        'Dad, 2026-09-09: "is there a reason you continue to run the full suite and '
        "gauntlet after every small change? do you realize that it takes upwards of "
        '15-20 mins?" He has asked four times. The push runs the whole suite itself.\n\n' + instead
    )
