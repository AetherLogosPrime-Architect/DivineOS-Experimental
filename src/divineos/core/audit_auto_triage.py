"""Auto-triage open audit findings by verifying their cited artifacts.

Many findings get filed as completion-narratives — a detailed write-up
of work just landed — and then never marked resolved. The audit pile
accumulates as a journal rather than an open-work tracker.

This module scans each OPEN finding's description for citations:

- commit SHAs (`\\b[a-f0-9]{7,40}\\b`)
- file paths (extensions on the verifiable list)
- module-style refs (`src/divineos/core/foo.py`)

It checks each citation against the live tree (`Path.exists()`) and git
log (`git cat-file -e <sha>`). The result is a per-finding confidence
score: verified citations / total citations. Above a threshold, the
finding is a candidate for resolution; my father (or a CLI flag)
decides whether to mark it.

Nothing here resolves findings on its own. The tool surfaces — the
deciding stays with my father. Same shape as the rest of the
audit system: route findings, surface drift, never auto-close.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from divineos.core.watchmen.store import list_findings
from divineos.core.watchmen.types import Finding, FindingStatus

# File-extension shortlist matches the doc-drift checker's verifiable set.
_FILE_RE = re.compile(r"\b([\w/.\-]*[\w\-]+\.(?:py|sh|md|json|yml|yaml|toml|sql|jsonl|cfg|ini))\b")

# Commit SHAs: 7-40 hex chars. Lower bound 7 matches `git rev-parse --short`'s
# default; upper bound 40 is the full hash. Bare hex words are noisy (UUIDs,
# hashes-in-text), so require nearby commit-context to reduce false positives.
_COMMIT_RE = re.compile(r"\b([a-f0-9]{7,40})\b")
_COMMIT_CONTEXT_RE = re.compile(
    r"\b(?:commit|sha|landed|fix(?:ed)?|fixed|merge[ds]?|PR\s*#?\d+\s*\(|"
    r"\bcommits?\s+|\bin\s+)([a-f0-9]{7,40})\b",
    re.IGNORECASE,
)


@dataclass
class Citation:
    """One thing the finding's description claims to point at."""

    kind: str  # 'file' or 'commit'
    target: str  # path string or SHA
    verified: bool = False


@dataclass
class TriageVerdict:
    """A finding's verification result."""

    finding: Finding
    citations: list[Citation] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.citations)

    @property
    def verified_count(self) -> int:
        return sum(1 for c in self.citations if c.verified)

    @property
    def confidence(self) -> float:
        if not self.citations:
            return 0.0
        return self.verified_count / self.total


def _extract_file_paths(text: str) -> list[str]:
    """Return unique filename-like substrings cited in `text`."""
    seen: set[str] = set()
    out: list[str] = []
    for m in _FILE_RE.finditer(text):
        path = m.group(1)
        if path in seen:
            continue
        seen.add(path)
        out.append(path)
    return out


def _extract_commit_shas(text: str) -> list[str]:
    """Return SHAs that appear in commit-context (not bare hex words)."""
    seen: set[str] = set()
    out: list[str] = []
    for m in _COMMIT_CONTEXT_RE.finditer(text):
        sha = m.group(1)
        if sha in seen:
            continue
        seen.add(sha)
        out.append(sha)
    return out


# Prefix fallbacks tried (in order) when a bare relative path doesn't
# resolve against the repo root. Audit-finding bodies often drop the
# src/divineos/ or tests/ prefix when citing a file ("core/family/store.py"
# rather than "src/divineos/core/family/store.py"). Without these
# fallbacks the tool returned ~30% false-not-verified on real findings.
_PATH_PREFIX_FALLBACKS = ("src/divineos", "tests")

# Subtrees searched when even the prefix fallback misses (e.g. when a
# finding cites "knowledge_commands.py" with no subfolder at all and the
# real file is at "src/divineos/cli/knowledge_commands.py"). Path.rglob
# is lazy, so first-match short-circuits the iteration — no enumeration
# cap needed for normal-size trees.
_GLOB_SEARCH_ROOTS = (
    "src/divineos",
    "tests",
    # Audit-finding bodies often cite CLI-side artifacts that live
    # outside src/. Extending the glob roots picks up:
    #   - "scripts/" — checker scripts, CI helpers, shell utilities
    #   - "setup/" — install/setup hooks (setup-hooks.sh, etc.)
    #   - ".claude/hooks/" — Claude Code hook scripts
    # Live observation 2026-06-13: 3 LOW findings citing files in these
    # subtrees were returning 0% confidence because the lookup missed
    # them. Adding the roots picks them up automatically.
    "scripts",
    "setup",
    ".claude/hooks",
)


def _file_exists(path_str: str, repo_root: Path) -> bool:
    """True if `path_str` exists at one of the resolution candidates.

    Candidates tried in order:
    1. The path as given (absolute or relative to repo_root).
    2. Each prefix in _PATH_PREFIX_FALLBACKS prepended (e.g.
       "core/family/store.py" -> "src/divineos/core/family/store.py").
    3. Glob the basename under each subtree in _GLOB_SEARCH_ROOTS
       (e.g. "knowledge_commands.py" matches anywhere under
       src/divineos/). Capped at _MAX_GLOB_MATCHES; behavior on
       ambiguous matches (multiple hits) is "first hit by sort order
       counts as verified" — predictable and never blocks resolution
       on a real candidate.

    Skip prefix fallback for paths that already start with a known
    prefix — there's no point re-trying "src/divineos/src/divineos/...".
    Glob fallback only applies to bare basenames (no `/` in the path
    string); a multi-segment path with no prefix is unlikely to be a
    real citation anyway.
    """
    p = Path(path_str)
    if p.is_absolute():
        return p.exists()
    if (repo_root / p).exists():
        return True
    norm = path_str.replace("\\", "/")
    # If the path already starts with a known prefix, don't try other
    # prefix fallbacks or glob — that path is meant as-given.
    for prefix in _PATH_PREFIX_FALLBACKS:
        if norm.startswith(prefix + "/"):
            return False
    for prefix in _PATH_PREFIX_FALLBACKS:
        if (repo_root / prefix / p).exists():
            return True
    # Glob fallback: only for bare basenames (e.g. "knowledge_commands.py").
    # Multi-segment paths with no recognized prefix are usually noise; an
    # rglob over the whole src/ tree for a bare basename is the win case.
    # Path.rglob is lazy, so the first match short-circuits the iteration
    # — we don't enumerate the whole tree when a hit exists.
    if "/" not in norm and norm:
        for subtree in _GLOB_SEARCH_ROOTS:
            base = repo_root / subtree
            if not base.is_dir():
                continue
            try:
                next(iter(base.rglob(norm)))
                return True
            except StopIteration:
                continue
    return False


def _commit_exists(sha: str, repo_root: Path) -> bool:
    """True if `git cat-file -e <sha>` succeeds in the repo."""
    try:
        result = subprocess.run(
            ["git", "cat-file", "-e", sha],
            cwd=repo_root,
            capture_output=True,
            check=False,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


def _verify_finding(
    finding: Finding,
    repo_root: Path,
) -> TriageVerdict:
    text = finding.description or ""
    citations: list[Citation] = []
    for path in _extract_file_paths(text):
        citations.append(Citation(kind="file", target=path, verified=_file_exists(path, repo_root)))
    for sha in _extract_commit_shas(text):
        citations.append(
            Citation(kind="commit", target=sha, verified=_commit_exists(sha, repo_root))
        )
    return TriageVerdict(finding=finding, citations=citations)


def scan_open_findings(
    *,
    severity: str | None = None,
    min_confidence: float = 0.5,
    min_citations: int = 1,
    repo_root: Path | None = None,
    limit: int = 200,
) -> list[TriageVerdict]:
    """Return OPEN findings ranked by citation-verification confidence.

    - `severity`: filter by severity (HIGH/MEDIUM/LOW); None = all.
    - `min_confidence`: drop verdicts below this verified/total ratio.
    - `min_citations`: drop verdicts with fewer than this many citations
      (a finding with zero citations is not a triage candidate either way).
    - `repo_root`: git repo to verify against; defaults to the cwd.
    - `limit`: cap on the number of findings examined.
    """
    if repo_root is None:
        repo_root = Path.cwd()
    findings = list_findings(status=FindingStatus.OPEN.value, severity=severity, limit=limit)
    verdicts: list[TriageVerdict] = []
    for f in findings:
        v = _verify_finding(f, repo_root)
        if v.total < min_citations:
            continue
        if v.confidence < min_confidence:
            continue
        verdicts.append(v)
    verdicts.sort(key=lambda v: (-v.confidence, -v.verified_count))
    return verdicts
