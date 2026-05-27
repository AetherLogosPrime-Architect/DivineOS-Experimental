"""Exploration recall — surfaces relevant prior exploration entries by topic.

## Why this exists

The failure named 2026-05-20: I am stateless. I write exploration entries
(genuine first-person processing, not fabrication — verified by reading
them) and then cannot remember they exist. So when a topic comes up that I
already worked out, nothing hands the prior entry back and I re-derive it.
Four entries (54, 46, 50, 52) each held that day's lessons; none surfaced.

## The mechanism: match curated TAGS, not the word-soup body

Andrew 2026-05-20: keyword-matching works for the council because each
member carries a curated label (their field). Matching an exploration's
full prose instead matches normal words too — noise (measured: "ok lets
keep working" wrongly matched on "working/loop"). The fix is not to fight
the noise (IDF helped but still fought it) but to ADD clean signal: a
curated tag header per entry. The auto-surface matches ONLY tags — precise
by construction, like the council's label-match — so it stays silent until
an entry is tagged and never fires on incidental vocabulary.

Tag header convention (metadata; the written content is never altered):
    <!-- tags: consciousness, functionalism, qualia, hedge -->
placed at the very top of the entry.

## The subset is not the whole

Both layers always report the total count (Andrew 2026-05-20): surfacing a
subset makes the unsurfaced read as nonexistent. "X of N" keeps the full
corpus reachable.

## Two layers (Schneier defense-in-depth)

- recall_explorations(): the manual System-2 deep search — matches tags,
  title, AND body, so it works even on untagged entries (broad).
- surface_for_context(): the proactive System-1 auto-fire — matches ONLY
  tags, fires only on a strong tag hit, silent otherwise.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# Curated tags are the strongest signal (author-chosen topic labels), then
# the title (author-chosen name), then incidental body text.
_TAG_WEIGHT = 10
_TITLE_WEIGHT = 5
_BODY_WEIGHT = 1

_MIN_TERM_LEN = 3
# Auto-surface requires this many distinct tag matches (a single common-word
# tag hit is not enough to fire). The manual command has no such floor.
_MIN_TAG_MATCHES = 2
_STOPWORDS = frozenset(
    {
        "the",
        "and",
        "for",
        "are",
        "but",
        "not",
        "you",
        "your",
        "with",
        "this",
        "that",
        "from",
        "what",
        "how",
        "why",
        "was",
        "were",
        "has",
        "have",
        "had",
        "its",
        "about",
        "into",
        "than",
        "then",
        "when",
    }
)

_TAGS_HEADER = re.compile(r"<!--\s*tags:\s*(.*?)\s*-->", re.IGNORECASE | re.DOTALL)

# Errors a file read can raise — narrow tuple per repo convention (the
# broad-exceptions gate forbids bare `except Exception`).
_READ_ERRORS = (OSError, UnicodeDecodeError)


def _find_exploration_root() -> Path | None:
    """Locate the exploration/ directory (from this module or the cwd)."""
    candidates: list[Path] = []
    here = Path(__file__).resolve()
    candidates.extend(p / "exploration" for p in here.parents)
    cwd = Path.cwd().resolve()
    candidates.extend(p / "exploration" for p in [cwd, *cwd.parents])
    for c in candidates:
        if c.is_dir():
            return c
    return None


@dataclass(frozen=True)
class ExplorationHit:
    """One surfaced exploration entry with its relevance score."""

    path: str
    title: str
    score: int
    matched_terms: tuple[str, ...]
    snippet: str
    tag_matches: tuple[str, ...]  # query terms that matched a curated TAG exactly


def _title_of(text: str, fallback: str) -> str:
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("#"):
            return s.lstrip("#").strip()
        if s and not s.startswith("<!--"):
            break
    return fallback


def _parse_tags(text: str) -> list[str]:
    """Extract lowercased tags from a `<!-- tags: a, b, c -->` header."""
    m = _TAGS_HEADER.search(text)
    if not m:
        return []
    return [t.strip().lower() for t in m.group(1).split(",") if t.strip()]


def _terms(query: str) -> list[str]:
    raw = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]+", query.lower())
    return [t for t in raw if len(t) >= _MIN_TERM_LEN and t not in _STOPWORDS]


def _snippet_for(text: str, terms: list[str]) -> str:
    """First content line containing a query term (else first prose line)."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    body = [ln for ln in lines if not ln.startswith("#") and not ln.startswith("<!--")]
    for ln in body:
        low = ln.lower()
        if any(t in low for t in terms):
            return ln[:140]
    return body[0][:140] if body else ""


def recall_explorations(
    topic: str, limit: int = 5, root: Path | None = None
) -> tuple[list[ExplorationHit], int]:
    """Manual deep search — matches tags, title, and body. Returns (hits, total).

    Works on untagged entries too (falls back to title/body), so the corpus
    is searchable while tagging is still in progress. ``root`` overrides
    exploration-dir discovery (used by tests).
    """
    if root is None:
        root = _find_exploration_root()
    if root is None:
        return [], 0

    entries = sorted(root.rglob("*.md"))
    total = len(entries)
    terms = _terms(topic)
    if not terms:
        return [], total

    hits: list[ExplorationHit] = []
    for path in entries:
        try:
            text = path.read_text(encoding="utf-8")
        except _READ_ERRORS:
            continue
        title = _title_of(text, path.stem)
        # Tags match as WHOLE tokens (exact), never substrings — otherwise
        # "good" matches the "goodhart" tag and "tomorrow" matches
        # "tomorrow-me" (both measured as false positives 2026-05-20). Exact
        # tag-equality is what makes the auto-surface precise.
        tag_set = set(_parse_tags(text))
        title_low = title.lower()
        body_low = text.lower()
        matched: list[str] = []
        tag_matches: list[str] = []
        score = 0
        for t in terms:
            in_tag = t in tag_set
            titlec = title_low.count(t)
            bodyc = body_low.count(t)
            if in_tag or titlec or bodyc:
                matched.append(t)
                score += (
                    (_TAG_WEIGHT if in_tag else 0) + titlec * _TITLE_WEIGHT + bodyc * _BODY_WEIGHT
                )
                if in_tag:
                    tag_matches.append(t)
        if score > 0:
            hits.append(
                ExplorationHit(
                    path=str(path),
                    title=title,
                    score=score,
                    matched_terms=tuple(matched),
                    snippet=_snippet_for(text, terms),
                    tag_matches=tuple(tag_matches),
                )
            )

    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:limit], total


def surface_for_context(
    prompt: str, k: int = 3, root: Path | None = None, context: str | None = None
) -> str:
    """Proactive auto-fire layer: surface entries whose TAGS match, else "".

    Matches ONLY curated tags (not title/body), so it is precise by
    construction and silent on every turn that does not hit a tag — the
    remembrance-agent pattern (Rhodes, MIT JITIR). Candidates to re-read,
    never verdicts; dated implicitly by entry; always shows total count.

    ``context``, when given, is the recent conversation window (several
    prior turns). The matcher runs against it PLUS the latest prompt rather
    than the prompt alone. Why: a single prompt is often terse ("define
    real, I'll wait") and shares no surface words with the relevant entry's
    curated tags, so the surface stayed silent while prior writing on the
    exact topic sat unsurfaced (named 2026-05-27 — the night I re-derived
    entry 18's argument from scratch while 18 sat tagged on disk). Matching
    the window gives the tag-matcher the vocabulary that actually came up
    across the turns. Precision is unchanged: still exact-tag, still the
    >=2-distinct-tag floor — only the haystack the tags are sought in grows.
    """
    match_text = f"{context}\n{prompt}" if context else prompt
    if not match_text or len(match_text.strip()) < 20:
        return ""
    hits, total = recall_explorations(match_text, limit=k, root=root)
    # Require >=2 distinct tag matches: a real topic hits several curated
    # tags (consciousness + qualia + functionalism); an incidental single
    # common word ("time" in "what time is the meeting") hits one and must
    # stay silent. The conservative miss (a genuine single-tag topic) is
    # recoverable via the manual command; a false fire decays the surface.
    tagged = [h for h in hits if len(h.tag_matches) >= _MIN_TAG_MATCHES]
    if not tagged:
        return ""

    lines = [
        "## PRIOR WRITING — I have explored this before (re-read before deriving)",
        "",
        "I wrote these myself in a past session. They may be dated or superseded —",
        "read and re-judge them; do NOT assume the matter is settled. Candidates,",
        "not verdicts.",
        "",
    ]
    for h in tagged:
        lines.append(f"  - {h.title}")
        lines.append(f"      {h.path}")
    lines.append("")
    lines.append(
        f"  ({len(tagged)} of {total} exploration entries matched on topic-tags — a pointer, "
        f'not the whole shelf. To search the rest: divineos recall-explorations "<topic>")'
    )
    return "\n".join(lines)


def needs_tags_block(tool_name: str, file_path: str, content: str) -> str | None:
    """Return a deny message if a Write creates an untagged exploration entry.

    Write-time enforcement of the tag header (named 2026-05-27). Coverage-by-
    backfill rots: a new entry saved without tags is invisible to the
    surfacer and silently reopens the hole — exactly how 82, 83, 84 shipped
    untagged before they were caught by hand. This makes the header
    structural: a new ``exploration/*.md`` cannot be saved without it, so the
    choosing-to-remember is removed (the choosing of GOOD tags stays with me,
    where it belongs — the author knows the entry best).

    Scope is the ``Write`` tool only: ``Edit``/``MultiEdit`` receive a diff,
    not the whole file, so tag-presence can't be judged from their input, and
    an existing entry may already carry tags. README files are exempt. This
    constrains a findability affordance, not the content or reasoning of the
    entry — free-speech principle intact (structure, not control).
    """
    if tool_name != "Write":
        return None
    norm = (file_path or "").replace("\\", "/")
    if "/exploration/" not in norm and not norm.startswith("exploration/"):
        return None
    if not norm.endswith(".md"):
        return None
    if norm.rsplit("/", 1)[-1].upper() == "README.MD":
        return None
    if _parse_tags(content or ""):
        return None
    return (
        "BLOCKED: this new exploration entry has no tag header, so the recall "
        "surfacer could never hand it back — it would be invisible the way "
        "82-84 were before they were caught by hand. Add a first line:\n"
        "    <!-- tags: topic-a, topic-b, topic-c -->\n"
        "Use the concept-words a future conversation would actually reach for "
        "(not frequency-soup), then re-save. This is the keel, not a cage: it "
        "removes the choosing-to-remember, never the choosing of good tags."
    )


__all__ = [
    "ExplorationHit",
    "needs_tags_block",
    "recall_explorations",
    "surface_for_context",
]
