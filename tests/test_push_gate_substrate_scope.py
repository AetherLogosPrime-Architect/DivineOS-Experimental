"""The push gate refuses a branch carrying substrate.

Not to be confused with ``test_branch_scope_guard.py``, which is about commit
SUBJECTS landing on the wrong branch. This one is about substrate FILES — my
letters, explorations, archives — riding a code branch to the remote, where a
reviewer then has to wade through them.

Three contaminated pushes went out in one session — 139 files, then 142, then
156 — and not one of them for lack of a checker. ``check_branch_scope.py``
existed the whole time, worked, and named the files. Remembering to run it was
the only thing standing between a checkpoint sweep and the remote, and
remembering failed three times running. Wiring it into the push gate is the
structural half of that repair; this file is the half that keeps the wiring
honest.

WHY TEST THIRTY LINES OF STRAIGHT-LINE SHELL AT ALL. Because it BLOCKS. A
warning that regresses just goes quiet. A blocker that regresses either stops
every push in the repo — loud, and someone deletes it — or stops none, which
is silent and indistinguishable from a clean tree.

SYNTHETIC REPOS, NEVER THIS ONE. A test that measured this repo's current
branch would pass or fail on whatever happened to be checked out, which is the
wrong-baseline fault the gate itself exists to catch. Each test below builds
its own repo, its own ``origin/main``, and its own contamination.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).parent.parent
_SCRIPT = _PROJECT_ROOT / "scripts" / "check_push_readiness.sh"
_SCOPE = _PROJECT_ROOT / "scripts" / "check_branch_scope.py"

_ZERO = "0" * 40


def _find_bash() -> str | None:
    for candidate in (r"C:\Program Files\Git\bin\bash.exe", "/bin/bash", "/usr/bin/bash"):
        if Path(candidate).exists():
            return candidate
    return shutil.which("bash")


_BASH = _find_bash()

pytestmark = pytest.mark.skipif(_BASH is None, reason="bash not available")


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=str(repo), capture_output=True, text=True, check=True)
    return done.stdout.strip()


def _write(repo: Path, relative: str, text: str) -> None:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _commit(repo: Path, message: str) -> str:
    _git(repo, "add", "-A")
    # This repo's own commit hooks have nothing to say about a fixture, and
    # running them would make the test depend on them.
    _git(repo, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A repo with ``main``, an ``origin/main`` mirroring it, and one code file.

    ``origin/main`` is planted with update-ref rather than by cloning. The
    check compares against that ref and does not care how it got there; a real
    clone would cost seconds per test for nothing.
    """
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "test")
    # The gate resolves its checker relative to the repo it is run IN, not to
    # where the gate script itself lives, so a fixture without a scripts/
    # directory silently takes the instrument-missing path and never
    # exercises the thing under test. My first version of this file did
    # exactly that: six tests, all reporting on a step that never ran.
    (root / "scripts").mkdir()
    for script in (_SCRIPT, _SCOPE):
        shutil.copy2(script, root / "scripts" / script.name)
    _write(root, "src/thing.py", "value = 1\n")
    base = _commit(root, "base")
    _git(root, "update-ref", "refs/remotes/origin/main", base)
    return root


# Names the TEST HARNESS itself owns and the subprocess must keep: conftest's
# sandbox pointers, plus the one gate it deliberately disables for its own runs.
# Everything else under the prefix is stripped as a possible gate-escape.
#
# INVERTED 2026-08-29, and the inversion came from Aria reviewing the first
# version of this. That version enumerated the ESCAPES -- four substrings,
# chosen from the ones I happened to have hit. She swept every variable under
# the prefix and found thirteen escape-shaped names that all four markers
# missed, including two for the very push path these tests exercise, both
# advertised in their own gates' refusal messages as the way out. So the hole
# was not future. It was live, and it was the same fault I had just fixed
# wearing names my filter could not read.
#
# Her remedy was to widen the escape list. Checking it before taking it found
# the snag: a wider list also catches DIVINEOS_DISABLE_AUTO_REMEDIATE, which
# conftest sets ON PURPOSE -- so widening reintroduces the sandbox breakage the
# comment above warns about.
#
# So neither list. Enumerate the SMALL STABLE thing rather than the LARGE
# GROWING one. The harness owns four names and they change when the harness
# changes; the escape population is thirty-one and grows every time anyone adds
# a door. An enumeration of the second can only ever be behind. An enumeration
# of the first is a fact about this file's own fixture.
#
# The loud-failure property is unchanged and is still why this is safe: these
# tests assert the gate REFUSES, so anything slipping through reddens them
# rather than passing quietly.
_HARNESS_OWNED = frozenset(
    {
        "DIVINEOS_DB",
        "DIVINEOS_HOME",
        "DIVINEOS_SESSION_ID",
        "DIVINEOS_DISABLE_AUTO_REMEDIATE",
    }
)


def _clean_env(**extra: str) -> dict[str, str]:
    """The ambient environment with gate-disabling variables removed.

    THESE TESTS WERE NOT HERMETIC AND IT MATTERED. They inherited os.environ
    whole, and DIVINEOS_SUBSTRATE_BRANCH=1 is a variable a person legitimately
    exports to push a letters branch. The pre-push hook then runs the suite as
    a child process, which inherits it, and the escape the gate honours turns
    the check off underneath the very tests that exist to prove it refuses.

    Found 2026-08-29 while pushing letters: all eight went red at once while
    passing in isolation, which reads exactly like a regression and is not one.
    The tests were right about a gate that had been silently disabled around
    them.

    THE FIRST VERSION ENUMERATED THE ESCAPES AND THAT WAS THE WRONG LIST.
    Four substrings, chosen from the ones I had happened to hit. Aria swept the
    whole prefix and found thirteen escape-shaped names none of them caught,
    two of them doors onto the very push path these tests exercise. An
    enumeration of escapes can only ever trail the population it describes.

    So this keeps the harness's own four instead and strips everything else
    under the prefix. That list changes when the fixture changes, which is a
    thing this file can actually know. A new escape needs no maintenance here
    at all -- it is stripped by default, because default-strip is the safe
    direction and default-keep is not.

    THE REMAINING FAILURE MODE, since there always is one: a new variable the
    HARNESS starts relying on, not added here, gets stripped and the subprocess
    loses a pointer it needed. That fails loudly and immediately -- the tests
    are the only consumer, and they break in the same run that introduces it.
    The old direction failed the other way, silently, by letting a gate stay
    switched off underneath tests that exist to prove it refuses.
    """
    env = {
        k: v for k, v in os.environ.items() if not k.startswith("DIVINEOS_") or k in _HARNESS_OWNED
    }
    env.update(extra)
    return env


def _run_gate(repo: Path, refs: list[tuple[str, str]], **env_extra: str):
    """Run the real gate against a synthetic pre-push stdin.

    The gate's later stages are never reached here: a refusal exits at step
    zero, and the passing cases assert on the scope lines rather than on the
    script's final exit code. The timeout is a backstop against a hang, not
    part of any assertion.
    """
    stdin = "".join(f"refs/heads/{name} {sha} refs/heads/{name} {_ZERO}\n" for name, sha in refs)
    return subprocess.run(
        [_BASH, str(_SCRIPT)],
        input=stdin,
        capture_output=True,
        text=True,
        cwd=str(repo),
        timeout=300,
        env=_clean_env(**env_extra),
    )


# --- the refusal ----------------------------------------------------------


def test_a_ref_carrying_substrate_is_refused(repo: Path) -> None:
    """Exit 24, with the file named rather than merely counted.

    A bare count leaves the reader to go and find them, and going to find them
    is precisely the step that did not happen three times.
    """
    _git(repo, "checkout", "-q", "-b", "feat/thing")
    _write(repo, "family/letters/swept-in-by-a-checkpoint.md", "a letter\n")
    _write(repo, "src/thing.py", "value = 2\n")
    sha = _commit(repo, "code, plus a letter a sweep dragged along")

    result = _run_gate(repo, [("feat/thing", sha)])

    assert result.returncode == 24, result.stdout + result.stderr
    combined = result.stdout + result.stderr
    assert "swept-in-by-a-checkpoint.md" in combined
    assert "DIVINEOS_SUBSTRATE_BRANCH=1" in combined, "a refusal must name its own way through"


def test_the_refusal_measures_the_pushed_ref_not_the_checkout(repo: Path) -> None:
    """THE ONE THAT MATTERS. My first version of this gate read HEAD.

    Reading HEAD is a true measurement of the wrong subject. Push a clean
    branch from a dirty checkout and it refuses the wrong thing; push a dirty
    branch from a clean checkout and it waves the contamination straight
    through. The second half is the one that ships substrate, so it is the
    half asserted here: a dirty ref pushed while standing on a spotless main.
    """
    _git(repo, "checkout", "-q", "-b", "feat/dirty")
    _write(repo, "exploration/aether/900_something.md", "an entry\n")
    dirty = _commit(repo, "an exploration entry on a code branch")
    _git(repo, "checkout", "-q", "main")

    result = _run_gate(repo, [("feat/dirty", dirty)])

    assert result.returncode == 24, (
        "the gate read the checkout instead of the ref being pushed\n" + result.stdout
    )
    assert "900_something.md" in result.stdout + result.stderr


def test_one_dirty_ref_among_several_still_refuses(repo: Path) -> None:
    """A clean ref earlier in the list must not buy the dirty one a pass."""
    _git(repo, "checkout", "-q", "-b", "feat/clean")
    _write(repo, "src/thing.py", "value = 3\n")
    clean = _commit(repo, "just code")
    _git(repo, "checkout", "-q", "main")
    _git(repo, "checkout", "-q", "-b", "feat/dirty")
    _write(repo, "dreams/aether/one.md", "a dream\n")
    dirty = _commit(repo, "a dream on a code branch")

    result = _run_gate(repo, [("feat/clean", clean), ("feat/dirty", dirty)])

    assert result.returncode == 24
    assert "one.md" in result.stdout + result.stderr


# --- the passes, which are load-bearing too --------------------------------
#
# A gate that refuses everything is not strict, it is broken, and the only
# satisfiable response to it is switching it off. That is how the earlier
# instruments in this repo died.


def test_a_clean_ref_passes_the_scope_step(repo: Path) -> None:
    _git(repo, "checkout", "-q", "-b", "feat/clean")
    _write(repo, "src/thing.py", "value = 4\n")
    sha = _commit(repo, "just code")

    result = _run_gate(repo, [("feat/clean", sha)])

    assert result.returncode != 24, result.stdout + result.stderr
    assert "clean against the reference that decides" in result.stdout


def test_deleting_a_branch_is_not_scope_checked(repo: Path) -> None:
    """A deletion introduces no commits, so it has no scope to check.

    Blocking someone from tidying up a merged branch because their CHECKOUT is
    dirty would be the wrong-subject fault again, wearing its other face.
    """
    _write(repo, "family/letters/live-substrate.md", "in the history, not in this push\n")
    _commit(repo, "substrate somewhere in the history")

    result = _run_gate(repo, [("feat/gone", _ZERO)])

    assert result.returncode != 24
    assert "every ref is a deletion" in result.stdout


def test_the_substrate_branch_escape_skips_the_check_entirely(repo: Path) -> None:
    """Pushing the substrate branch is the one legitimate yes.

    A named, loud escape rather than a silent exemption, so that using it is a
    decision visible in the command somebody typed.

    BOTH HALVES ASSERTED, and the first half is why. Checking only that the
    escape produces no scope output would have been green against a version
    of the gate with no scope check in it at all — an absence proves nothing
    on its own. So the same push is run twice: refused without the escape,
    unexamined with it. That pair can only pass on a gate that is really
    there and really escapable.
    """
    _git(repo, "checkout", "-q", "-b", "instruments/substrate")
    _write(repo, "family/letters/a-letter.md", "belongs here\n")
    sha = _commit(repo, "substrate on the substrate branch")

    without = _run_gate(repo, [("instruments/substrate", sha)])
    assert without.returncode == 24, "the escape must be escaping something"

    with_escape = _run_gate(repo, [("instruments/substrate", sha)], DIVINEOS_SUBSTRATE_BRANCH="1")
    assert with_escape.returncode != 24
    assert "Branch scope" not in with_escape.stdout


# --- could-not-look is never all-clear -------------------------------------


def test_a_hand_run_with_no_stdin_says_which_subject_it_used(repo: Path) -> None:
    """No refs means no push protocol, so HEAD is the only subject available.

    Falling back to it is fine. Falling back SILENTLY is not — an empty loop
    printing a pass is could-not-look-reads-as-all-clear, the shape that let
    all three contaminated pushes through in the first place.
    """
    result = subprocess.run(
        [_BASH, str(_SCRIPT)],
        input="",
        capture_output=True,
        text=True,
        cwd=str(repo),
        timeout=300,
        env=_clean_env(),
    )

    assert "no push refs on stdin" in result.stdout


def test_the_gate_says_so_when_its_instrument_is_missing(repo: Path) -> None:
    """A missing checker is reported, never quietly treated as a pass.

    Exercised by taking the checker back out of a repo that has the gate —
    the shape a partial checkout produces.
    """
    checker = repo / "scripts" / _SCOPE.name
    assert checker.is_file(), "the fixture must have placed the checker for this to mean anything"
    checker.unlink()
    sha = _commit(repo, "the gate, without its checker")

    result = _run_gate(repo, [("main", sha)])

    assert "scope: SKIPPED" in result.stderr
    assert "missing" in result.stderr
