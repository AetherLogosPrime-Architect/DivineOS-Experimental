"""Tests for .claude/hooks/venv-python-gate.sh.

The gate stands in one specific hole: a bare `python` in a Bash tool call
resolves `import divineos` through the ONE global editable-install slot,
which points at whichever tree ran `pip install -e .` last. From this repo
that is Aether's tree, so the command answers about his substrate while
looking like it answers about mine.

The cases that matter are not "does it parse JSON". They are the two ways a
narrow gate fails: firing on commands that were already correct (noise, which
gets the gate routed around), and staying silent on the shape it exists for.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _bash_resolver import bash_executable  # noqa: E402

REPO_ROOT = Path(__file__).parent.parent
HOOK = REPO_ROOT / ".claude" / "hooks" / "venv-python-gate.sh"


# Uses the shared resolver rather than a local copy. The local one returned the
# first candidate that EXISTED, which is the presence-is-not-evidence flaw --
# the bare name `bash` resolves to a WSL relay stub on this machine that exits 1
# having produced nothing, and a test reading that empty output as a verdict
# would agree with anything. tests/_bash_resolver.py probes each candidate on
# both exit code and output, and is the one home for this question precisely so
# there stops being a sixth copy of the answer.
_BASH = bash_executable()

# The gate resolves the repo's sealed venv and stands aside when there is
# none — on a checkout without .venv every case would "pass" vacuously and
# the suite would report green while testing nothing.
_VENV_PRESENT = (REPO_ROOT / ".venv" / "Scripts" / "python.exe").exists() or (
    REPO_ROOT / ".venv" / "bin" / "python"
).exists()

pytestmark = [
    pytest.mark.skipif(_BASH is None, reason="no usable bash interpreter on this platform"),
    pytest.mark.skipif(
        not _VENV_PRESENT, reason="no sealed venv in this checkout; gate stands aside"
    ),
]


def _run(command: str, cwd: Path | None = None) -> str:
    assert _BASH is not None
    payload = json.dumps({"tool_input": {"command": command}})
    result = subprocess.run(
        [_BASH, str(HOOK)],
        cwd=str(cwd or REPO_ROOT),
        input=payload,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


@pytest.fixture(scope="module")
def foreign_repo(tmp_path_factory) -> Path:
    """A git repo where bare ``python`` provably resolves somewhere else.

    WHY A FIXTURE INSTEAD OF THE REPO ROOT, and it is the same correction the
    gate itself needed. These tests used to run from REPO_ROOT and assert a
    deny, which encoded the conclusion "bare python points at the other tree" as
    a fact about the world. That was true in Aria's checkout, where the gate was
    written, and false in Aether's, where the install slot points at this repo —
    so on 2026-08-25 the gate was corrected to MEASURE the condition, and these
    four tests began failing because they still assumed it.

    A test that assumes the condition it is testing has the disease of the code
    it tests. So the condition is constructed: a throwaway git repo with no
    ``src/divineos`` of its own and a sealed venv of its own (the gate stands
    aside entirely when it finds no venv). Bare python inside it resolves to
    whatever the global slot holds, which is by construction not that repo's
    src — the deny path, deterministically, on either machine.

    NEVER LINK TO THE REAL VENV. The first version of this fixture created a
    directory junction from the temp repo's ``.venv`` to this repo's, so the
    gate would find a working interpreter. It worked, and then pytest's
    temp-directory cleanup walked the junction and deleted the contents of the
    REAL venv -- ``pyvenv.cfg`` and ``Lib/`` gone, ``Scripts/`` left behind, the
    ``divineos`` shim broken with "failed to locate pyvenv.cfg". Written and
    detonated inside one session, on 2026-08-25.

    A junction is not a copy and rmtree does not know the difference. This
    repo's conftest even carries an ``onerror`` handler that chmods read-only
    files and retries the unlink, which makes the traversal MORE thorough, not
    less. So the fixture builds a real throwaway interpreter instead:
    ``--without-pip`` keeps it to about a second and nothing outside tmp is
    reachable from it.
    """
    root = tmp_path_factory.mktemp("foreign_repo")
    subprocess.run(["git", "init", "-q", str(root)], check=True, capture_output=True)

    made = subprocess.run(
        [sys.executable, "-m", "venv", "--without-pip", str(root / ".venv")],
        capture_output=True,
        text=True,
    )
    link = root / ".venv"
    if not (link / "Scripts" / "python.exe").exists() and not (link / "bin" / "python").exists():
        pytest.skip(f"could not build a throwaway venv for the fixture: {made.stderr.strip()}")
    return root


def _is_deny(stdout: str) -> bool:
    if not stdout:
        return False
    decision = json.loads(stdout)["hookSpecificOutput"]
    return decision["permissionDecision"] == "deny"


class TestFiresOnTheShapeItExistsFor:
    def test_bare_python_importing_divineos_is_denied(self, foreign_repo):
        assert _is_deny(
            _run('python -c "import divineos; print(divineos.__file__)"', cwd=foreign_repo)
        )

    def test_python3_is_denied_too(self, foreign_repo):
        assert _is_deny(_run('python3 -c "from divineos.core import ledger"', cwd=foreign_repo))

    def test_bare_python_after_a_shell_separator_is_denied(self, foreign_repo):
        """The reach is usually `cd <repo> && python - <<PY`, not a bare
        first word — matching only at the start would miss every real case."""
        assert _is_deny(
            _run(
                "cd /somewhere && python - <<PY\nfrom divineos.core.family import entity\nPY",
                cwd=foreign_repo,
            )
        )

    def test_the_reason_names_the_venv_to_use(self, foreign_repo):
        out = _run('python -c "import divineos"', cwd=foreign_repo)
        reason = json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"]
        assert ".venv" in reason, "a gate that blocks without naming the fix is a wall"

    def test_the_reason_names_where_it_actually_resolved(self, foreign_repo):
        """The diagnostic must report the measurement, not a stored belief.

        The old message asserted "bare python imports Aether's tree, not mine",
        which read as the exact inverse of the reader's situation in the other
        checkout. Naming the two paths it compared is what makes the refusal
        arguable instead of something to be believed.
        """
        out = _run('python -c "import divineos"', cwd=foreign_repo)
        reason = json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"]

        assert "resolves to" in reason
        assert str(foreign_repo.resolve()) in reason.replace("/", "\\"), (
            "the refusal must name THIS repo's src as the thing that did not match"
        )


class TestStandsAsideWhenBarePythonIsAlreadyCorrect:
    """The half the gate gained on 2026-08-25, which had no coverage at all.

    Blocking a correct interpreter is not a harmless false positive here: the
    gate steers the reader into the sealed venv, whose dependency set is smaller
    than the interpreter it refused. Routing someone away from the right tool
    and toward a worse one, with a diagnostic telling them the opposite of their
    situation, is how a gate teaches people to route around it.
    """

    def test_it_says_nothing_when_bare_python_reaches_this_tree(self):
        resolved = subprocess.run(
            [
                "python",
                "-c",
                "import divineos, pathlib; print(pathlib.Path(divineos.__file__).resolve().parent)",
            ],
            capture_output=True,
            text=True,
        )
        here = (REPO_ROOT / "src" / "divineos").resolve()
        if resolved.returncode != 0 or resolved.stdout.strip() != str(here):
            pytest.skip(
                "the global install slot does not point at this checkout right now, "
                "so the stand-aside condition cannot be constructed without claiming it"
            )

        assert _run('python -c "import divineos"') == "", (
            "bare python resolves to THIS tree, so the gate has nothing to say; "
            "refusing here would send the reader to a venv with fewer deps than "
            "the interpreter it just refused"
        )


class TestStandsAsideWhenAlreadyCorrect:
    """Noise is how a narrow gate gets routed around. Each of these was
    already doing the right thing and must produce no output at all."""

    def test_explicit_venv_python_passes(self):
        assert _run('.venv/Scripts/python.exe -c "import divineos"') == ""

    def test_windows_style_venv_path_passes(self):
        assert _run('.venv\\Scripts\\python.exe -c "import divineos"') == ""

    def test_hook_helper_variable_passes(self):
        assert _run('"$PYTHON_BIN" -m divineos.hooks.pre_tool_use_gate') == ""

    def test_the_wrapper_passes(self):
        assert _run("python scripts/divineos_wrapper.py briefing") == ""

    def test_bare_python_without_divineos_passes(self):
        """Out of scope on purpose. A gate on every `python` call is noise."""
        assert _run('python -c "print(1 + 1)"') == ""

    def test_pytest_passes(self):
        """Measured on the gate's first fire: it blocked `python -m pytest`,
        which is the only way the suite runs here — the sealed venv has no
        pytest. pyproject's `pythonpath` already forces this worktree's src
        ahead of any installed copy, so pytest was never the unrouted path.
        A gate standing in front of the normal way of running tests teaches
        the routing-around it exists to prevent."""
        assert _run("python -m pytest tests/test_divineos_thing.py -q") == ""

    def test_bare_pytest_passes(self):
        assert _run("pytest tests/ -q --tb=short  # divineos suite") == ""

    def test_divineos_cli_alone_passes(self):
        assert _run("divineos briefing") == ""

    def test_empty_command_passes(self):
        assert _run("") == ""


class TestMalformedInputDoesNotBlock:
    """Every gate here runs in front of real work. None may fail closed on
    a payload it did not expect."""

    def test_not_json_passes(self):
        assert (
            subprocess.run(
                [_BASH, str(HOOK)],
                cwd=str(REPO_ROOT),
                input="not json at all",
                capture_output=True,
                text=True,
            ).stdout.strip()
            == ""
        )

    def test_missing_tool_input_passes(self):
        assert (
            subprocess.run(
                [_BASH, str(HOOK)],
                cwd=str(REPO_ROOT),
                input=json.dumps({"something_else": 1}),
                capture_output=True,
                text=True,
            ).stdout.strip()
            == ""
        )
