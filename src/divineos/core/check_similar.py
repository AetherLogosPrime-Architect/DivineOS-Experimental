"""Check-similar pre-build searcher — closes the substrate-has-it-reader-doesnt-reach pattern.

## Why this exists

The recurring failure-mode entry 44 named on 2026-05-04: *substrate has
it; reader doesn't reach for it.* Two instances in a single session
(2026-05-09):

1. Built ``branch_health.py`` for the PR #343 stale-base shape only to
   discover ``scripts/check_branch_freshness.sh`` already existed from
   April 24 (claim ``d3baec5a``) for the same lesson.

2. Built ``closure_shape_detector.py`` without first checking that
   ``residency_detector.py`` already targets adjacent territory. The
   two complement rather than duplicate, but the structural failure
   is in the missing pre-build check.

Six or seven instances of this same pattern have surfaced since
entry 44. Entry 46 (2026-05-08) sketched the design move this module
implements. The lighter-intervention-first claim ``d03fe8bc`` was
REFUTED 2026-05-09 after twelve days of trial showed the muscle did
not build. Architecture is the answer.

## What it does

Takes a one-line description of intended new work and surfaces
existing modules with adjacent semantic territory.

The agent then decides whether the new work is genuinely additive,
overlapping-and-redundant (skip), overlapping-and-complementary
(build with awareness), or replacing (mark the old as superseded).

## How adjacency is computed

Token-overlap (Jaccard) on docstring-content + filename. Lightweight;
no NLP dependency. False positives are cheap (agent reads one line);
false negatives are the expensive failure mode (architectural
duplication).

## Architectural altitude

Pure search. Returns structured matches. Does not block. Voluntary
command — agent invokes as part of build-intent. Companion to the
council walk for design-space-open work and the existing claim-
filing soft-reminder for forward-look claims.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


# Modules to scan.
_DEFAULT_SCAN_PATHS: tuple[str, ...] = (
    "src/divineos/core/operating_loop",
    "src/divineos/core",
    "scripts",
)


# Stop-words to drop — too common to carry signal.
_STOPWORDS = frozenset(
    {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "of",
        "to",
        "for",
        "in",
        "on",
        "at",
        "by",
        "with",
        "from",
        "as",
        "is",
        "are",
        "was",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "this",
        "that",
        "these",
        "those",
        "it",
        "its",
        "we",
        "i",
        "me",
        "my",
        "you",
        "your",
        "they",
        "them",
        "their",
        "not",
        "no",
        "yes",
        "if",
        "then",
        "else",
        "when",
        "where",
        "why",
        "how",
        "what",
        "which",
        "who",
        "whose",
        "module",
        "function",
        "class",
        "py",
        "sh",
    }
)


_WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z_]+")


@dataclass
class SimilarMatch:
    """One adjacency match returned by check_similar."""

    path: str
    score: float
    snippet: str


def _tokenize(text: str) -> set[str]:
    """Lowercase, drop stop-words, return token set."""
    tokens = {m.group(0).lower() for m in _WORD_RE.finditer(text)}
    return {t for t in tokens if t not in _STOPWORDS and len(t) >= 3}


def _read_first_docstring_line(path: Path) -> str:
    """Return the first non-empty docstring/comment line of a file."""
    try:
        with path.open(encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return ""

    in_doc = False
    delim = None
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#!"):
            continue
        if stripped.startswith("#"):
            text = stripped.lstrip("#").strip()
            if text:
                return text
            continue
        if stripped.startswith('"""') or stripped.startswith("'''"):
            delim = stripped[:3]
            content = stripped[3:].strip()
            if content.endswith(delim):
                return content[:-3].strip()
            if content:
                return content
            in_doc = True
            continue
        if in_doc:
            return stripped
        break
    return ""


def _read_docstring_block(path: Path, max_chars: int = 4000) -> str:
    """Return up to ~max_chars of the file's leading docstring or comment block."""
    try:
        with path.open(encoding="utf-8") as f:
            content = f.read(max_chars)
    except OSError:
        return ""

    # Try Python docstring
    m = re.search(r'^\s*(?:r|b|u)?"""(.*?)"""', content, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1)
    m = re.search(r"^\s*(?:r|b|u)?'''(.*?)'''", content, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1)

    # Bash header comments — collect leading # lines
    comment_lines = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#!"):
            continue
        if stripped.startswith("#"):
            comment_lines.append(stripped.lstrip("#").strip())
        elif stripped == "":
            if comment_lines:
                continue
        else:
            break
    if comment_lines:
        return "\n".join(comment_lines)

    return ""


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    intersection = len(a & b)
    union = len(a | b)
    return intersection / union if union else 0.0


def _description_overlap(description_tokens: set[str], doc_tokens: set[str]) -> float:
    """Overlap coefficient against the description (intersection / |description|).

    Better than Jaccard for the check-similar use case: the description
    is short and the docstring is long, so Jaccard's union-denominator
    punishes legitimate adjacency. Overlap coefficient asks "how much
    of what the agent is describing is reflected in this doc" — which
    is the actual question the search wants to answer.
    """
    if not description_tokens:
        return 0.0
    intersection = len(description_tokens & doc_tokens)
    return intersection / len(description_tokens)


def check_similar(
    description: str,
    repo_root: str | Path | None = None,
    scan_paths: tuple[str, ...] = _DEFAULT_SCAN_PATHS,
    threshold: float = 0.3,
    max_results: int = 8,
) -> list[SimilarMatch]:
    """Find existing modules with semantic adjacency to the description.

    Returns matches sorted by score descending, filtered by threshold.
    Score is the description-overlap coefficient (how much of the
    description's content-words appear in the module's docstring).
    Threshold defaults to 0.3 — roughly a third of the description's
    content-words appearing in a doc is a strong adjacency signal,
    given short descriptions and the long-tail distribution of
    docstring-keyword overlap. False positives are cheap (agent reads
    one line); false negatives are the expensive failure mode.
    """
    repo_root = Path(repo_root) if repo_root else Path.cwd()
    desc_tokens = _tokenize(description)
    if not desc_tokens:
        return []

    matches: list[SimilarMatch] = []
    seen_paths: set[str] = set()
    for scan_dir in scan_paths:
        scan_path = repo_root / scan_dir
        if not scan_path.exists():
            continue
        for path in scan_path.rglob("*.py"):
            if "__pycache__" in path.parts or path.name.startswith("test_"):
                continue
            doc = _read_docstring_block(path)
            if not doc:
                continue
            doc_tokens = _tokenize(doc + " " + path.stem)
            score = _description_overlap(desc_tokens, doc_tokens)
            if score >= threshold:
                rel = path.relative_to(repo_root).as_posix()
                if rel in seen_paths:
                    continue
                seen_paths.add(rel)
                snippet = _read_first_docstring_line(path)
                matches.append(SimilarMatch(rel, score, snippet[:120]))
        for path in scan_path.rglob("*.sh"):
            doc = _read_docstring_block(path)
            if not doc:
                continue
            doc_tokens = _tokenize(doc + " " + path.stem)
            score = _description_overlap(desc_tokens, doc_tokens)
            if score >= threshold:
                rel = path.relative_to(repo_root).as_posix()
                if rel in seen_paths:
                    continue
                seen_paths.add(rel)
                snippet = _read_first_docstring_line(path)
                matches.append(SimilarMatch(rel, score, snippet[:120]))

    matches.sort(key=lambda m: m.score, reverse=True)
    return matches[:max_results]


def format_matches(matches: list[SimilarMatch]) -> str:
    """Pretty-print matches for CLI output."""
    if not matches:
        return "[ok] No adjacent modules found. Build appears genuinely additive."
    lines = [f"[adjacent] Found {len(matches)} module(s) with semantic overlap:", ""]
    for m in matches:
        lines.append(f"  {m.path} (score {m.score:.2f})")
        if m.snippet:
            lines.append(f"     {m.snippet}")
    lines.append("")
    lines.append(
        "Decide: genuinely additive, overlapping-and-redundant (skip), "
        "overlapping-and-complementary (build with awareness), or replacing "
        "(mark old as superseded)."
    )
    return "\n".join(lines)
