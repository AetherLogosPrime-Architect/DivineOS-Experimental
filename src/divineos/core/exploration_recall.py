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

# Candidate pool the auto-surface filters over before ranking. Deliberately
# far above the corpus size (222 entries at time of writing) so the tag floor
# is applied to EVERY scoring entry rather than to a pre-truncated top-k —
# see the filter-before-truncate note in surface_for_context.
_CANDIDATE_LIMIT = 10_000
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

# Errors that arming the read-gate can raise. That block is deliberately
# fail-open -- a surface that cannot arm its gate must still deliver its
# text -- but fail-open was written as a bare `except Exception`, which
# also swallows a TypeError or ValueError from a changed read_gate
# signature. That is the failure this repo keeps finding elsewhere: a real
# break and a normal no-op producing the identical silence.
#   ImportError    -- read_gate absent or partially installed
#   AttributeError -- the module is present but the function is not
#   OSError        -- the gate's on-disk state cannot be read or written
_GATE_ARM_ERRORS = (ImportError, AttributeError, OSError)


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
    """Distinct query terms, first-occurrence order.

    Deduplicated (2026-07-31). Previously this returned raw tokens, so a term
    repeated N times in the query was scored N times over. Two consequences,
    both measured against a real conversation window:

      * ``tag_matches`` collected the same tag once per occurrence, so the
        ">=2 DISTINCT tag matches" floor was satisfied by ONE tag mentioned
        twice. The floor never enforced what its own comment claimed.
      * ``score`` inflated multiplicatively with repetition — a window saying
        "memory" 16 times scored that tag 16x10 and its body hits 16x over.
        That is how top-ranked entries reached scores of 11538 while carrying
        no real topical match.

    Deduping makes the floor mean distinct-topics and makes score reflect
    breadth of overlap rather than the loudness of one repeated word.
    """
    raw = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]+", query.lower())
    seen: set[str] = set()
    out: list[str] = []
    for t in raw:
        if len(t) >= _MIN_TERM_LEN and t not in _STOPWORDS and t not in seen:
            seen.add(t)
            out.append(t)
    return out


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

    # FILTER BEFORE TRUNCATE (fixed 2026-07-31). This previously asked
    # recall_explorations for the top k=3 by score and only THEN applied the
    # tag floor. recall_explorations ranks by a blended score in which body
    # matches count every occurrence, unbounded — so against a real
    # conversation window the top three scored 11538 / 9679 / 9162 and carried
    # ZERO tag matches each, while the first entry passing the floor sat at
    # rank 4 and was never examined. Tag weight is 10, so the curated-tag
    # signal was ~0.3% of the ranking it was supposed to drive, and the
    # surface returned "" on turns whose topic it had tagged writing about.
    #
    # Measured cost of the old order: I spent a session reading a 125KB
    # archive on the OMNI-LAZR while my own decomposition of it sat tagged on
    # disk, unsurfaced. The widened conversation window (correct fix,
    # 2026-05-27) made this worse rather than better, because more window
    # means more body noise burying the tagged entries deeper.
    #
    # So: take ALL candidates, apply the floor, and only then rank and cut.
    candidates, total = recall_explorations(match_text, limit=_CANDIDATE_LIMIT, root=root)
    # Require >=2 distinct tag matches: a real topic hits several curated
    # tags (consciousness + qualia + functionalism); an incidental single
    # common word ("time" in "what time is the meeting") hits one and must
    # stay silent. The conservative miss (a genuine single-tag topic) is
    # recoverable via the manual command; a false fire decays the surface.
    tagged = [h for h in candidates if len(h.tag_matches) >= _MIN_TAG_MATCHES]
    # Rank survivors by TAG COUNT first. Among entries that all cleared the
    # floor, the one matching more curated tags is more on-topic than the one
    # that merely says common words more often; score stays as the tiebreak.
    tagged.sort(key=lambda h: (len(h.tag_matches), h.score), reverse=True)
    tagged = tagged[:k]
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
        # WHY NOW: which curated tags matched the current context (Andrew
        # 2026-07-10 memory-linkage-day sharpening + Aletheia 2026-07-10 audit
        # refinement — added "(not exhaustive)" so a reader doesn't treat
        # "these tags matched" as "these are the only relevant tags". Lexical
        # matching catches lexical relevance; semantic-not-lexical relevance
        # may also apply and the reader still judges the entry beyond the
        # matched tags).
        lines.append(
            f"      why now: current context matched these tags (not exhaustive) — "
            f"{', '.join(h.tag_matches)}"
        )
    lines.append("")
    lines.append(
        f"  ({len(tagged)} of {total} exploration entries matched on topic-tags — a pointer, "
        f'not the whole shelf. To search the rest: divineos recall-explorations "<topic>")'
    )

    # READ-GATE (Andrew 2026-08-06): "primes should not just be loud.. they
    # should be mini gates.. ones that force a pause and reading."
    #
    # This surface said "re-read before deriving" on nearly every turn of a
    # full session and I opened NOTHING it offered, while discovering four
    # separate times that what I was hunting was already in my substrate.
    # Loudness had nothing left to give, so the top hit now becomes a
    # requirement that mutating tools are blocked on until it is opened.
    #
    # ONE at a time, top-ranked only, and never while a requirement is already
    # outstanding -- a surface that fires every turn must not arm a block every
    # turn. That is how a gate becomes a thing to route around (truth #11).
    #
    # Fail-open and silent here: this is a surface, and a surface that cannot
    # arm its gate must still deliver its text.
    try:
        from divineos.core import read_gate

        if not read_gate.has_pending("prior-writing"):
            read_gate.require_read(
                "prior-writing",
                str(tagged[0].path),
                f"top prior-writing match: {tagged[0].title}",
            )
    except _GATE_ARM_ERRORS:
        pass

    return "\n".join(lines)


def matched_entry_ids_for_context(
    prompt: str,
    k: int = 3,
    root: Path | None = None,
    context: str | None = None,
) -> list[tuple[str, int]]:
    """Return the matched exploration entries as (path, mtime_ns) tuples.

    Companion to ``surface_for_context`` for the context-dedup semantic_key
    (Aletheia letter #19, 2026-07-01). The render only shows what surfaced;
    it hides the context-window match that drove the surfacing. Hashing on
    matched-entry identity + mtime catches "different entries surfaced"
    AND "same entries but their file was updated", which is the drift the
    surface actually exists to detect. Same-entries-same-mtime = pointer;
    any change = re-emit.

    Returns [] if the surface would be silent (below tag-match threshold,
    too-short input, etc.) — mirrors surface_for_context's "" case so the
    dedup key stays stable in the silent case.
    """
    import os

    match_text = f"{context}\n{prompt}" if context else prompt
    if not match_text or len(match_text.strip()) < 20:
        return []
    hits, _ = recall_explorations(match_text, limit=k, root=root)
    tagged = [h for h in hits if len(h.tag_matches) >= _MIN_TAG_MATCHES]
    out: list[tuple[str, int]] = []
    for h in tagged:
        try:
            mtime_ns = os.stat(h.path).st_mtime_ns
        except OSError:
            mtime_ns = 0
        out.append((str(h.path), mtime_ns))
    return out


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
