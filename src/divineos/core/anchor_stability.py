"""Is the content an auditor is about to sign already a fixed point?

WHY THIS EXISTS, and it is the second instance rather than the first.

An external confirm binds to the content that was read -- a tree and a
change-fingerprint -- which is what stops anyone obtaining a sign-off and then
altering the work underneath it. That binding cannot tell a rewrite that changes
behaviour from one that changes nothing, and it should not try: guessing would
be the hole.

The consequence is that ANY automated rewriter still pending on a branch is a
signature-killer. On 2026-09-11 the pre-commit formatter rejoined two wrapped
lines in a test -- same call, same arguments, nothing about behaviour touched --
and Aletheia's confirm, filed minutes earlier on the strongest rung, went dead.

IT HAD HAPPENED BEFORE. Round filed 2026-05-10: "Andrew re-confirmed after
auto-format whitespace changes drifted the hash. Substantive content unchanged;
intent identical to original CONFIRMS." Same cause, four months earlier, and the
answer was a human re-signing by hand. That is a resolution, not a fix, so the
recurrence was guaranteed and only its date was open.

THE INVARIANT, stated rather than the procedure (Dijkstra's lens on the walk):
an anchor is meaningful only if the content it names is a FIXED POINT of every
automated rewriter in the pipeline. Formatter-stability is not a nicety beside
the anchor; it is a precondition of the anchor meaning anything.

WHAT THIS DELIBERATELY DOES NOT COVER (Schneier's lens, written down rather
than discovered later): it sees the formatter's opinion and nothing else. A
hand-rewrapped comment, a rename, or a different tool in the chain all move the
fingerprint and are invisible here. This closes MECHANISED drift. A signature
can still die for a human reason, and that is the binding doing its job.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

__all__ = ["StabilityResult", "formatter_stability"]


@dataclass(frozen=True)
class StabilityResult:
    """Three states, and the third is the point.

    ``stable``       -- nothing the formatter would rewrite.
    ``unstable``     -- these files move on the next commit; an anchor is void.
    ``cannot-tell``  -- the formatter did not run. NOT a clean bill.
    """

    state: str
    unstable: tuple[str, ...]
    reason: str

    @property
    def blocks_an_anchor(self) -> bool:
        """True when an anchor taken now should NOT be handed out.

        Could-not-tell blocks as well as unstable. An instrument that did not
        run has not said the branch is clean, and the whole incident this
        module exists for is a green that meant less than it looked like --
        answering optimistically here would build a second one.
        """
        return self.state != "stable"


def formatter_stability(
    repo_root: Path,
    rel_paths: Sequence[str],
    formatter: Sequence[str] = ("ruff", "format", "--check"),
) -> StabilityResult:
    """Would the formatter rewrite any of ``rel_paths`` as they stand?

    SCOPED TO THE BRANCH'S OWN FILES, never the tree. This repository carries a
    scratch directory the formatter would rewrite on sight; a whole-tree check
    would refuse every branch forever, and a check that always refuses is one
    that gets switched off inside a week. The control test for that lives in
    ``test_instability_outside_the_changed_set_does_not_refuse``.

    Paths that no longer exist are skipped rather than reported: a deletion is
    in the changed set and has nothing to format, and naming it would send
    someone to run a formatter over a file that is gone.
    """
    candidates = [p for p in rel_paths if p.endswith(".py") and (repo_root / p).is_file()]
    if not candidates:
        return StabilityResult(
            state="stable",
            unstable=(),
            reason="no python files in this set for the formatter to move",
        )

    try:
        proc = subprocess.run(
            [*formatter, "--", *candidates],
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return StabilityResult(
            state="cannot-tell",
            unstable=(),
            reason=f"could not run the formatter, so stability is unknown: {exc}",
        )

    if proc.returncode == 0:
        return StabilityResult(
            state="stable",
            unstable=(),
            reason=f"{len(candidates)} file(s) already at the formatter's fixed point",
        )

    # Exit 1 is the formatter's "these would change". Anything else is the tool
    # failing rather than answering, and failing is not a verdict.
    if proc.returncode != 1:
        return StabilityResult(
            state="cannot-tell",
            unstable=(),
            reason=(
                f"the formatter exited {proc.returncode}, which is neither clean "
                f"nor a would-reformat verdict: {(proc.stderr or '').strip()[:200]}"
            ),
        )

    moved: list[str] = []
    for line in (proc.stdout or "").splitlines():
        line = line.strip()
        if not line.lower().startswith("would reformat:"):
            continue
        named = line.split(":", 1)[1].strip().replace("\\", "/")
        for candidate in candidates:
            if named.endswith(candidate) or candidate.endswith(named):
                moved.append(candidate)
                break

    if not moved:
        # It said something would change and named nothing this call can map
        # back. Could-not-tell rather than a guess in either direction.
        return StabilityResult(
            state="cannot-tell",
            unstable=(),
            reason="the formatter reported changes but named no file this check could match",
        )

    return StabilityResult(
        state="unstable",
        unstable=tuple(dict.fromkeys(moved)),
        reason=(
            f"{len(moved)} file(s) would be rewritten by the formatter, so an "
            "anchor taken now is void after the next commit"
        ),
    )
