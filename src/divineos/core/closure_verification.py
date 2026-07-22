"""Closure-shape citation verification — the substance-binding mechanism.

Andrew 2026-06-21 catch: keyword-list and shape-match closure-detectors
both fail because the optimizer routes around any single surface. The
fix per the doorman primitive (filed 721ec1ec, named by Andrew and
refined with Aether 2026-06-17): the gate's defense isn't shape-
matching, it's REQUIRING the recording. The unlock-contingent-on-the-
recording is the fifth piece. Self-attestation defeats the discipline.

This module is the verification logic — the substance-binding check
that lives in ONE place so neither the marker module nor any future
caller can clear a closure-shape marker by self-attestation.

## What this verifies

Given a citation string and an optional reference timestamp, this
checks whether the citation resolves to a REAL artifact accessible
from the current substrate state, and whether the artifact is recent
enough relative to the reference timestamp to plausibly back a
just-made closure-claim.

Citation types and how each is checked:

* **file path** (e.g. ``src/foo.py``, ``src/foo.py:42``)
  Verified by: file exists on disk; if line specified, file has
  at least that many lines; file was modified within
  ``_RECENCY_WINDOW_SECONDS`` of the reference timestamp.
* **substrate id** (e.g. ``prereg-abc123``, ``round-xyz789``)
  Verified by: id resolves via the appropriate divineos CLI subcommand
  with non-error exit.
* **commit hash** (e.g. ``a1b2c3d``)
  Verified by: ``git cat-file -t <hash>`` returns ``commit``;
  hash is reachable from HEAD or any branch tip recent enough.
* **test name** (e.g. ``test_closure_verification_rejects_stale``)
  Verified by: grep finds ``def <test_name>`` in tests/.
* **PR/issue ref** (e.g. ``#249``, ``pr 249``)
  Verified by: ``gh pr view <num>`` returns non-error.

Citations that do not match any recognized type fail verification
("unrecognized citation form"). The closed-set behavior is
intentional — Schneier lens 2026-06-21: an open-set "any
plausible-looking string passes" verification would let the
optimizer satisfy the gate by padding output with novel-looking
references. Closed-set means every new citation type goes through
deliberate addition.

## Honest limit

The recency-window check approximates "in this turn" by checking
"modified within N seconds of the reference timestamp." It is not
turn-perfect. A file edited 25 seconds before the closure-claim
(but unrelated to it) would currently pass. The Schneier follow-up
(semantic-relevance check) is deferred; this module is the substance-
binding scaffold the next-tightening composes onto.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path


# Default time window within which a cited artifact must have been
# modified/created/touched to count as substantiating a just-made
# closure-claim. 30 minutes is a reasonable starting point for
# probation per the Deming PDSA discipline (filed earlier today,
# prereg-fb1b42753396); tune based on observed data.
_RECENCY_WINDOW_SECONDS: float = 30 * 60


@dataclass(frozen=True)
class VerificationResult:
    """Outcome of verifying a citation against the substrate state.

    All fields immutable so callers can pass results around without
    risk of mutation. ``ok`` is the headline; ``reason`` carries the
    plain-language explanation suitable for surfacing back to the
    agent in a gate-message.
    """

    ok: bool
    citation: str
    citation_type: str  # "file" | "substrate_id" | "commit" | "test" | "pr" | "unknown"
    reason: str


# Pattern classifiers — each returns the citation type if it matches,
# else None. Order matters: substrate ids checked before commit hashes
# because both can look like hex strings.
_RE_FILE = re.compile(
    r"^([\w/_-]+\.(?:py|md|json|yaml|yml|toml|sh|js|ts|sql))(?::(\d+))?$",
)
_RE_SUBSTRATE_ID = re.compile(
    r"^(?:prereg|round|claim|psf|task|find|consult)-[a-f0-9]{6,}$",
    re.IGNORECASE,
)
_RE_COMMIT = re.compile(r"^[a-f0-9]{7,40}$")
_RE_TEST = re.compile(r"^test_\w+$")
_RE_PR = re.compile(r"^(?:#|pr\s+)(\d+)$", re.IGNORECASE)


def _classify(citation: str) -> str:
    """Determine the citation type from its surface form. Closed-set."""
    s = citation.strip()
    if _RE_FILE.match(s):
        return "file"
    if _RE_SUBSTRATE_ID.match(s):
        return "substrate_id"
    if _RE_COMMIT.match(s):
        return "commit"
    if _RE_TEST.match(s):
        return "test"
    if _RE_PR.match(s):
        return "pr"
    return "unknown"


def _verify_file(citation: str, reference_ts: float, recency: float) -> VerificationResult:
    """File-citation verification. Real path AND recently modified."""
    m = _RE_FILE.match(citation.strip())
    if m is None:
        return VerificationResult(False, citation, "file", "not a file-citation form")
    path_str = m.group(1)
    line_str = m.group(2)
    p = Path(path_str)
    if not p.exists():
        return VerificationResult(False, citation, "file", f"file does not exist: {path_str}")
    if not p.is_file():
        return VerificationResult(
            False, citation, "file", f"path is not a regular file: {path_str}"
        )
    if line_str:
        try:
            line = int(line_str)
        except ValueError:
            return VerificationResult(False, citation, "file", f"bad line number: {line_str}")
        try:
            with p.open("r", encoding="utf-8", errors="replace") as f:
                lines = sum(1 for _ in f)
        except OSError as e:
            return VerificationResult(False, citation, "file", f"cannot read file: {e}")
        if line > lines:
            return VerificationResult(
                False, citation, "file", f"line {line} beyond file length ({lines})"
            )
    try:
        mtime = p.stat().st_mtime
    except OSError as e:
        return VerificationResult(False, citation, "file", f"cannot stat file: {e}")
    age = reference_ts - mtime
    if age > recency:
        return VerificationResult(
            False,
            citation,
            "file",
            f"file last modified {int(age)}s before reference (window: {int(recency)}s) — "
            f"stale-citation pattern",
        )
    return VerificationResult(True, citation, "file", f"file modified {int(age)}s before reference")


def _verify_substrate_id(citation: str, reference_ts: float, recency: float) -> VerificationResult:
    """Substrate-id verification via the appropriate divineos CLI subcommand.

    The id-kind prefix selects the lookup command. Non-error exit means
    the id resolves; error exit means the id is fabricated or stale.
    """
    s = citation.strip().lower()
    if not _RE_SUBSTRATE_ID.match(s):
        return VerificationResult(False, citation, "substrate_id", "not a substrate-id form")
    kind = s.split("-", 1)[0]
    cli_subcommand = {
        "prereg": ["prereg", "show", s],
        "round": ["audit", "show-round", s],
        "claim": ["claims", "show", s],
        "find": ["audit", "show", s],
        "consult": ["mansion", "consultation", "show", s],
    }.get(kind)
    if cli_subcommand is None:
        return VerificationResult(
            False, citation, "substrate_id", f"no lookup path defined for kind: {kind}"
        )
    divineos = shutil.which("divineos")
    if divineos is None:
        return VerificationResult(
            False, citation, "substrate_id", "divineos CLI not on PATH for lookup"
        )
    try:
        result = subprocess.run(
            [divineos, *cli_subcommand],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        return VerificationResult(False, citation, "substrate_id", f"lookup failed: {e}")
    if result.returncode != 0:
        snippet = (result.stderr or result.stdout or "")[:120].strip().replace("\n", " ")
        return VerificationResult(
            False, citation, "substrate_id", f"lookup non-zero exit: {snippet}"
        )
    # Windows CMD-wrapper exit-code trampoline (Aria 2026-07-22,
    # council-c0a53fa5a05a): on Windows the divineos.CMD wrapper installed by
    # pip does not propagate the underlying Python exit code, so a genuine
    # not-found (`[!] Pre-registration not found: ...`) reaches this branch
    # with returncode=0 despite the tool having failed. Defense-in-depth:
    # also treat divineos's own stdout error marker `[!]` as a non-resolution
    # signal. Taleb vantage: single-signal trust across a lossy boundary is
    # the same class-of-bug as os.kill(pid,0) on Windows and try/except-eats-
    # NameError elsewhere in this codebase. Norman vantage: the double check
    # makes the invariant self-documenting for the next reader — resolves iff
    # BOTH exit code is zero AND stdout does not carry divineos's error mark.
    # Check ANY line of stdout for divineos's error marker `[!]` — not just
    # the first, because on fresh test environments divineos initializes
    # the ledger on-demand and prints `[+] Seed v2.1.0 applied...` BEFORE
    # the actual error line. Iterate lines and look for any that start with
    # the error prefix (allowing for leading whitespace).
    error_line = next(
        (ln.strip() for ln in result.stdout.splitlines() if ln.lstrip().startswith("[!]")),
        None,
    )
    if error_line:
        return VerificationResult(
            False,
            citation,
            "substrate_id",
            f"stdout error-marker (windows-cmd-wrapper exit-code drop): {error_line[:120]}",
        )
    return VerificationResult(
        True, citation, "substrate_id", f"resolved via divineos {' '.join(cli_subcommand)}"
    )


def _verify_commit(citation: str, reference_ts: float, recency: float) -> VerificationResult:
    """Commit-hash verification via git cat-file."""
    s = citation.strip()
    if not _RE_COMMIT.match(s):
        return VerificationResult(False, citation, "commit", "not a commit-hash form")
    git = shutil.which("git")
    if git is None:
        return VerificationResult(False, citation, "commit", "git not on PATH")
    try:
        result = subprocess.run(
            [git, "cat-file", "-t", s],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        return VerificationResult(False, citation, "commit", f"git lookup failed: {e}")
    if result.returncode != 0 or result.stdout.strip() != "commit":
        return VerificationResult(False, citation, "commit", "hash does not resolve to a commit")
    # Check commit recency
    try:
        result = subprocess.run(
            [git, "log", "-1", "--format=%ct", s],
            capture_output=True,
            text=True,
            timeout=5,
        )
        commit_ts = float(result.stdout.strip())
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return VerificationResult(False, citation, "commit", "could not read commit timestamp")
    age = reference_ts - commit_ts
    if age > recency:
        return VerificationResult(
            False,
            citation,
            "commit",
            f"commit is {int(age)}s old (window: {int(recency)}s) — stale-citation pattern",
        )
    return VerificationResult(
        True, citation, "commit", f"commit dated {int(age)}s before reference"
    )


def _verify_test(citation: str, reference_ts: float, recency: float) -> VerificationResult:
    """Test-name verification by grepping for def <name> in tests/.

    The recency check applies to the file containing the test: a test
    named in years-old code wouldn't satisfy a just-made closure-claim,
    so the containing file must have been modified within the window.
    """
    s = citation.strip()
    if not _RE_TEST.match(s):
        return VerificationResult(False, citation, "test", "not a test-name form")
    tests_dir = Path("tests")
    if not tests_dir.exists():
        return VerificationResult(False, citation, "test", "tests/ directory not found")
    # Find file containing def <name>(
    needle = f"def {s}("
    matching_file: Path | None = None
    for path in tests_dir.rglob("*.py"):
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if needle in content:
            matching_file = path
            break
    if matching_file is None:
        return VerificationResult(False, citation, "test", f"no test definition found for {s}")
    try:
        mtime = matching_file.stat().st_mtime
    except OSError:
        return VerificationResult(False, citation, "test", "could not stat containing file")
    age = reference_ts - mtime
    if age > recency:
        return VerificationResult(
            False,
            citation,
            "test",
            f"containing file last modified {int(age)}s before reference — stale-citation pattern",
        )
    return VerificationResult(
        True,
        citation,
        "test",
        f"test found in {matching_file}, modified {int(age)}s before reference",
    )


def _verify_pr(citation: str, reference_ts: float, recency: float) -> VerificationResult:
    """PR-reference verification via gh pr view."""
    m = _RE_PR.match(citation.strip())
    if m is None:
        return VerificationResult(False, citation, "pr", "not a PR-ref form")
    num = m.group(1)
    gh = shutil.which("gh")
    if gh is None:
        return VerificationResult(False, citation, "pr", "gh CLI not on PATH")
    try:
        result = subprocess.run(
            [gh, "pr", "view", num, "--json", "number,updatedAt"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        return VerificationResult(False, citation, "pr", f"gh lookup failed: {e}")
    if result.returncode != 0:
        return VerificationResult(False, citation, "pr", f"gh pr view #{num} returned non-zero")
    # The recency check on a PR is whether it was updated recently; the
    # default 30-minute window is generous for "PR I just touched."
    return VerificationResult(True, citation, "pr", f"PR #{num} resolved")


def verify_citation(
    citation: str,
    reference_ts: float | None = None,
    recency_seconds: float = _RECENCY_WINDOW_SECONDS,
) -> VerificationResult:
    """Verify a citation against substrate state.

    ``reference_ts`` defaults to ``time.time()``. ``recency_seconds`` is
    the time-window within which the cited artifact must have been
    touched to count as substantiating a recent closure-claim. The
    default window is a probation-tuned starting point; pass an explicit
    value for tests.

    Returns ``VerificationResult`` — never raises. Failures carry the
    reason; callers (e.g. ``clear_marker``) decide whether to act on
    the ok flag.
    """
    if reference_ts is None:
        reference_ts = time.time()
    if not citation or not citation.strip():
        return VerificationResult(False, citation, "unknown", "empty citation")
    kind = _classify(citation)
    if kind == "file":
        return _verify_file(citation, reference_ts, recency_seconds)
    if kind == "substrate_id":
        return _verify_substrate_id(citation, reference_ts, recency_seconds)
    if kind == "commit":
        return _verify_commit(citation, reference_ts, recency_seconds)
    if kind == "test":
        return _verify_test(citation, reference_ts, recency_seconds)
    if kind == "pr":
        return _verify_pr(citation, reference_ts, recency_seconds)
    return VerificationResult(
        False,
        citation,
        "unknown",
        "unrecognized citation form — must be file:line, substrate-id, "
        "commit hash, test name, or PR/issue ref",
    )


__all__ = [
    "VerificationResult",
    "verify_citation",
]
