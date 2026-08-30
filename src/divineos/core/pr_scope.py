"""True file scope for a pull request, derived locally. No API cap.

Andrew 2026-08-06:

    *"for stuff that you have to keep rederiving over and over? automation is
    key... if you think to your self 'this wouldnt have failed IF ONLY I HAD
    DONE X' — those are places where a forced pause would help."*

## The IF-ONLY this came from

I told Aether that PR #412 touched no guardrail files and was safe to merge as
cheap progress. It touches five, including ``check_multi_party_review.py`` —
the script that enforces the audit requirement. He could have merged on my
word.

**If only I had used the local file list instead of the capped one.**

``gh pr view --json files`` returns at most 100 paths. #412 is 446 files. I
reported a 100-file sample as a census, and the guardrail classification built
on it was wrong in the dangerous direction.

I had documented that cap the day before — ``GH_FILE_LIST_CAP`` in
``cli/prs_commands.py``, with a test named
``test_truncated_file_list_is_flagged_loudly`` and a note recording that #405
returned exactly 100 and *the only reason the truncation was caught is that
the number looked suspiciously round.* Then I got exactly 100 back for #412
and did not blink.

## Why this is a module and not a discipline

Knowing the cap did not stop me using the capped call. The knowledge was
present, correct, written down, tested — and the fast command was still the
one my hand reached for, because a fresh survey feels like a new question
rather than the one I already solved.

Truth #11(a): take the option away. This derives scope from
``git merge-base`` + ``git diff`` only. **There is no code path here that can
consult the GitHub file list**, so the capped answer is not available to be
reached for, however tired or fast-moving the reacher.

Andrew's sharpened rule, which generalises past this API: *a result count that
exactly equals a known limit is not data, it is the limit reporting itself.*

## The third word

``PrScope.error`` is set and the file list is ``None`` when the branch cannot
be resolved — never an empty list. "I could not look" and "it touches nothing"
are opposite findings, and this whole module exists because one was reported
as the other.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

_GUARDRAIL_LIST = "scripts/guardrail_files.txt"


@dataclass
class PrScope:
    """Measured scope of one branch against main.

    ``files is None`` means the measurement did not happen. It never means
    the branch is empty.
    """

    branch: str
    merge_base: str | None = None
    files: list[str] | None = None
    guardrail_hits: list[str] | None = None
    error: str | None = None

    @property
    def measured(self) -> bool:
        return self.files is not None

    @property
    def needs_external_review(self) -> bool | None:
        """``None`` when unmeasured — an unknown is not a 'no'."""
        if self.guardrail_hits is None:
            return None
        return bool(self.guardrail_hits)

    def describe(self) -> str:
        if self.error is not None:
            return (
                f"{self.branch}: COULD NOT MEASURE — {self.error}\n"
                "    This is not 'touches nothing'. Nothing was checked."
            )
        assert self.files is not None and self.guardrail_hits is not None
        verdict = (
            f"NEEDS EXTERNAL REVIEW ({len(self.guardrail_hits)} guardrail)"
            if self.guardrail_hits
            else "no guardrail files"
        )
        out = [f"{self.branch}: {len(self.files)} files — {verdict}"]
        out += [f"    {h}" for h in self.guardrail_hits]
        return "\n".join(out)


def _git(args: list[str], repo: Path) -> tuple[str | None, str | None]:
    try:
        proc = subprocess.run(
            ["git", *args], cwd=repo, capture_output=True, text=True, timeout=60, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, f"git {' '.join(args[:2])} failed: {exc}"
    if proc.returncode != 0:
        return (
            None,
            f"git {' '.join(args[:2])} exited {proc.returncode}: {proc.stderr.strip()[:200]}",
        )
    return proc.stdout, None


def load_guardrail_set(repo: Path) -> tuple[set[str] | None, str | None]:
    """The guardrail list, or an honest failure.

    ``None`` rather than an empty set on failure: an unreadable guardrail list
    would otherwise make every branch look clean, which is the exact
    silent-pass this substrate keeps building by accident.
    """
    path = repo / _GUARDRAIL_LIST
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return None, f"cannot read {path}: {exc}"
    return {ln.strip() for ln in lines if ln.strip() and not ln.lstrip().startswith("#")}, None


def measure(branch: str, repo: Path, base: str = "origin/main") -> PrScope:
    """True file scope of ``branch`` against ``base``. Local only."""
    scope = PrScope(branch=branch)

    guard, err = load_guardrail_set(repo)
    if guard is None:
        scope.error = err
        return scope

    out, err = _git(["merge-base", base, branch], repo)
    if out is None:
        scope.error = err
        return scope
    scope.merge_base = out.strip()

    out, err = _git(["diff", "--name-only", scope.merge_base, branch], repo)
    if out is None:
        scope.error = err
        return scope

    files = [ln.strip() for ln in out.splitlines() if ln.strip()]
    scope.files = files
    scope.guardrail_hits = sorted(set(files) & guard)
    return scope
