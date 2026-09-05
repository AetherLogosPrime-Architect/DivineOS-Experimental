"""A tag push proposes no commits, so the commit-verifying stages skip it.

WHY TAGS EXIST HERE AT ALL, and it is Aria's. A squash merge puts ONE message
on main; every other commit message on the branch -- the reasoning behind each
change, which this house calls the audit trail -- lives only on the branch.
Deleting a merged branch is the least ceremonious act in the system. Her
sentence: I paid a real price to preserve something and then set it down in
the least durable place either of us has. Seven branches had already gone that
way before anyone asked.

She could put a number on the cost afterward, on the one branch that survived
only in her clone: the squash body on main is 314 bytes; the commit body was
1710. What main did not keep included a named, unclaimed piece of work --
seventeen test files spawning shells with timeouts from one second to a
hundred and twenty, no shared runner -- recorded in that commit and nowhere
else. The loss was not general. It was that paragraph.

So: tag the tip, push the tag, delete nothing. Three stages then refused the
tags, each asking a branch-shaped question of something that is not a branch:

  freshness   refused them for being OLD, which is what a history tag IS.
              Aria reproduced it and sharpened it: the check does not read a
              WRONG ref from the push, it reads NO ref from the push at all.
              Its verdict is about the working state and the push is only the
              trigger. An instrument that never looks at the thing it judges
              cannot be wrong about it -- it was never measuring it.

  tests       builds its snapshot from the FIRST REF in the push, so an
              eight-tag archival push sent the whole suite against a
              months-old tree. Real failures for that tree, none about
              anything being pushed.

  scope       refused an archival tag OF A LETTERS BRANCH for containing
              letters.

SYNTHETIC REPOS, NEVER THIS ONE -- and the first version of this file broke
that rule, one file over from where it is written in capitals.

That version drove the real gate against whatever repository it found itself
in. It passed every time I ran it by hand and hung when the gate ran it inside
its own detached worktree, which is the only run that decides. An instrument
whose answer depends on where it is standing: the same disease as the three
stages above, in the test written to cure them. The neighbouring file had
already solved it and said so in its own docstring. I did not look.
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
_HOOK_GENERATOR = _PROJECT_ROOT / "setup" / "setup-hooks.sh"

_ZERO = "0" * 40
_SHA = "1" * 40


def _find_bash() -> str | None:
    for candidate in (r"C:\Program Files\Git\bin\bash.exe", "/bin/bash", "/usr/bin/bash"):
        if Path(candidate).exists():
            return candidate
    return shutil.which("bash")


_BASH = _find_bash()

pytestmark = pytest.mark.skipif(_BASH is None, reason="bash not available")

# Enumerate the SMALL STABLE set the harness owns and strip every other
# DIVINEOS_ name. Its sibling learned this the hard way: an enumeration of
# ESCAPES can only ever trail a population that grows whenever anyone adds a
# door, and default-strip is the safe direction.
_HARNESS_OWNED = frozenset(
    {
        "DIVINEOS_DB",
        "DIVINEOS_HOME",
        "DIVINEOS_SESSION_ID",
        "DIVINEOS_DISABLE_AUTO_REMEDIATE",
    }
)


def _clean_env() -> dict[str, str]:
    """Ambient environment with gate-disabling variables stripped.

    Load-bearing for one concrete reason: DIVINEOS_SUBSTRATE_BRANCH is a
    variable a person legitimately exports to push a letters branch, and it
    was exported in the shell that pushed these very tags. Inheriting it would
    switch the scope stage off underneath a test that asserts what that stage
    does.
    """
    return {
        k: v for k, v in os.environ.items() if not k.startswith("DIVINEOS_") or k in _HARNESS_OWNED
    }


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=str(repo), capture_output=True, text=True, check=True)
    return done.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A repo with main, an origin/main mirroring it, and the checkers present.

    The gate resolves its checker relative to the repo it RUNS IN, so a
    fixture without a scripts/ directory silently takes the
    instrument-missing path and reports on a step that never ran.
    """
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "test")
    (root / "scripts").mkdir()
    for script in (_SCRIPT, _SCOPE):
        shutil.copy2(script, root / "scripts" / script.name)
    (root / "src").mkdir()
    (root / "src" / "thing.py").write_text("value = 1\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "base")
    _git(root, "update-ref", "refs/remotes/origin/main", _git(root, "rev-parse", "HEAD"))
    return root


def _run_gate(repo: Path, refs: list[str]) -> subprocess.CompletedProcess[str]:
    """Run the real gate against a synthetic pre-push stdin, in a synthetic repo.

    The timeout is a backstop against a hang, not part of any assertion. The
    fixture has no tests/ directory, so the branch cases reach the test stage
    and return at once rather than running a real suite -- which is what lets
    the negative cases assert without the test-suppression variable the first
    version of this file needed.
    """
    stdin = "".join(f"{ref} {_SHA} {ref} {_ZERO}\n" for ref in refs)
    return subprocess.run(
        [_BASH, str(_SCRIPT)],
        input=stdin,
        capture_output=True,
        text=True,
        timeout=300,
        cwd=str(repo),
        env=_clean_env(),
    )


def test_a_tag_only_push_skips_the_commit_stages(repo: Path):
    """THE CATCH. Eight archival tags sent the suite to a months-old tree."""
    out = _run_gate(repo, ["refs/tags/history/one"]).stdout
    assert "Tag-only push" in out, out[-2000:]


def test_several_tags_still_count_as_tag_only(repo: Path):
    """The real push was eight at once; one-at-a-time would have hidden it."""
    refs = [f"refs/tags/history/{n}" for n in ("a", "b", "c")]
    out = _run_gate(repo, refs).stdout
    assert "Tag-only push" in out, out[-2000:]


def test_a_tag_mixed_with_a_branch_does_not_skip(repo: Path):
    """The mixed case is where a real change could ride in behind a cheap one,
    and it is the same rule the deletion-only path already used."""
    out = _run_gate(repo, ["refs/tags/history/one", "refs/heads/work"]).stdout
    assert "Tag-only push" not in out, out[-2000:]


def test_a_branch_push_does_not_skip(repo: Path):
    """Guard the guard: a skip leaking to branches would silently disable the
    slowest and most load-bearing stage in the house."""
    out = _run_gate(repo, ["refs/heads/work"]).stdout
    assert "Tag-only push" not in out, out[-2000:]


def test_the_scope_stage_ignores_tag_refs(repo: Path):
    """The stage that refused an archival tag OF A LETTERS BRANCH for
    containing letters. A tag carries nothing anywhere; it marks a commit that
    already exists."""
    result = _run_gate(repo, ["refs/tags/history/one"])
    assert result.returncode != 24, (result.stdout + result.stderr)[-2000:]
    assert "REFUSED" not in result.stdout, result.stdout[-2000:]


def test_the_hook_generator_skips_freshness_for_tag_only_pushes():
    """The freshness step lives in the hook, not the gate, and it refused
    first -- so it needs its own pin.

    Reads the GENERATOR rather than the installed hook: the installer
    regenerates that file wholesale, and this repo has lost a live wiring
    exactly that way. Pinning the generated copy would stay green while the
    source that rewrites it went wrong.
    """
    src = _HOOK_GENERATOR.read_text(encoding="utf-8")
    assert "PUSH_IS_TAGS_ONLY" in src, "the hook generator no longer computes tag-only"
    assert '"$PUSH_IS_TAGS_ONLY" != "1"' in src, (
        "the freshness step no longer guards on tag-only -- a history tag will "
        "be refused for being old, which is what a history tag is"
    )
