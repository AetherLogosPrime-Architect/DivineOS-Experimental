"""Exploration Reader — surfaces past explorations in briefing and search.

The exploration folder contains the agent's most authentic self-narration:
free-form explorations of topics chosen for personal interest, creative
writing, journal entries, and guided deep dives. These are first-person
lived experience, not extracted summaries.

Without this module, the exploration folder is a drawer nobody opens.
With it, every future session sees what past sessions discovered.

Sanskrit anchor: smriti (that which is remembered — the thread of
continuity woven through what would otherwise be isolated moments).
"""

import re
from pathlib import Path
from typing import Any


_EXPLORATION_DIR = Path(__file__).resolve().parent.parent.parent / "exploration"

_ER_ERRORS = (OSError, IOError, UnicodeDecodeError)

# Territory taxonomy (claim 02f0dcc0, council scoped 2026-05-03 with Grok).
# LOCKED SET — new tags require explicit addition + external review. The
# locked-set discipline prevents tag-proliferation drift where every new
# walk introduces idiosyncratic terms; matching then becomes brittle.
#
# Each exploration entry can carry 1-3 territory tags via a header line:
#     Territory: [architecture, language]
# The tags surface in briefing when active goals/claims match the same
# territories (find_explorations_by_territory).
TERRITORY_TAGS: frozenset[str] = frozenset(
    {
        "integrity",  # data fidelity, hash chains, audit, ledger
        "architecture",  # structural decisions, system shape, repo layout
        "social",  # relational, family-member work, communication
        "epistemic",  # knowledge, evidence, truth, reasoning
        "phenomenological",  # felt experience, register, voice, identity
        "performance",  # latency, throughput, scale
        "language",  # naming, conventions, terms, language-games
        "governance",  # multi-party review, gates, oversight
        "operational",  # process, workflow, day-to-day
        "self_reference",  # strange loops, self-modification, future-self,
        # pronoun-distancing, voice-permeability
    }
)

# Header pattern: "Territory: [tag1, tag2]" or "territory: tag1, tag2"
_TERRITORY_HEADER_PATTERN = re.compile(
    r"^\s*territor(?:y|ies)\s*:\s*\[?([a-z_,\s\-]+?)\]?\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def _find_exploration_root() -> Path | None:
    """Find the exploration directory, checking common locations."""
    candidates = [
        _EXPLORATION_DIR,
        Path.cwd() / "exploration",
        Path.cwd().parent / "exploration",
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return None


def get_exploration_summary(include_creative: bool = True) -> list[dict[str, Any]]:
    """Scan exploration folder and return structured summaries.

    Returns list of dicts with: path, title, date, reason, category.
    """
    root = _find_exploration_root()
    if not root:
        return []

    entries: list[dict[str, Any]] = []

    # Numbered explorations (01_topic.md through NN_topic.md)
    for md_file in sorted(root.glob("*.md")):
        entry = _parse_exploration_header(md_file)
        if entry:
            entry["category"] = "exploration"
            entries.append(entry)

    if include_creative:
        # Creative writing
        creative_dir = root / "creative_space" / "creative_writing"
        if creative_dir.is_dir():
            for md_file in sorted(creative_dir.glob("*.md")):
                entry = _parse_exploration_header(md_file)
                if entry:
                    entry["category"] = "creative_writing"
                    entries.append(entry)

        # Journal
        journal_dir = root / "creative_space" / "journal"
        if journal_dir.is_dir():
            for md_file in sorted(journal_dir.glob("*.md")):
                entry = _parse_exploration_header(md_file)
                if entry:
                    entry["category"] = "journal"
                    entries.append(entry)

        # Guided explorations
        guided_dir = root / "guided_exploration"
        if guided_dir.is_dir():
            for md_file in sorted(guided_dir.glob("*.md")):
                entry = _parse_exploration_header(md_file)
                if entry:
                    entry["category"] = "guided"
                    entries.append(entry)

    return entries


def _parse_exploration_header(path: Path) -> dict[str, Any] | None:
    """Extract title, date, and reason from an exploration file's header."""
    try:
        text = path.read_text(encoding="utf-8")
    except _ER_ERRORS:
        return None

    lines = text.split("\n")
    if not lines:
        return None

    # Title: first # heading
    title = path.stem.replace("_", " ").title()
    for line in lines[:5]:
        if line.startswith("# "):
            title = line[2:].strip()
            break

    # Date
    date = ""
    for line in lines[:10]:
        date_match = re.search(r"(?:Date studied|Written|Date):\s*(.+)", line, re.IGNORECASE)
        if date_match:
            date = date_match.group(1).strip().rstrip("*")
            break

    # Why I chose this / reason
    reason = ""
    for line in lines[:10]:
        reason_match = re.search(r"Why I chose this:\s*(.+)", line, re.IGNORECASE)
        if reason_match:
            reason = reason_match.group(1).strip().rstrip("*")
            break

    # If no structured reason, use first italic or descriptive line
    if not reason:
        for line in lines[:10]:
            if line.startswith("*") and line.endswith("*") and len(line) > 10:
                reason = line.strip("* ")
                break

    # Territory tags (claim 02f0dcc0). Header line:
    #   Territory: [architecture, language]
    # Parsed and normalized to a tuple of valid tags from TERRITORY_TAGS.
    # Unknown tags are silently dropped (locked-set discipline). Empty
    # tuple if no Territory line present.
    territory: tuple[str, ...] = ()
    territory_match = _TERRITORY_HEADER_PATTERN.search(text)
    if territory_match:
        raw_tags = territory_match.group(1)
        # Split on commas, normalize: strip whitespace, lowercase, replace
        # hyphens with underscores so "self-reference" → "self_reference".
        parsed = []
        for tag in raw_tags.split(","):
            normalized = tag.strip().lower().replace("-", "_")
            if normalized in TERRITORY_TAGS:
                parsed.append(normalized)
        territory = tuple(parsed)

    return {
        "path": str(path),
        "filename": path.name,
        "title": title,
        "date": date,
        "reason": reason,
        "territory": territory,
    }


# Maximum exploration entries to surface per territory match. Hard-capped
# to prevent over-anchoring (Goodhart concern from Q5 of council scoping):
# if every claim surfaces 5+ prior walks, every new problem starts looking
# like a previous walk. Cap at 2 (Grok's recommendation, council scope
# 2026-05-03).
_TERRITORY_MATCH_CAP = 2


def find_explorations_by_territory(
    tags: list[str] | tuple[str, ...] | set[str],
    *,
    limit: int = _TERRITORY_MATCH_CAP,
    include_creative: bool = True,
) -> list[dict[str, Any]]:
    """Find exploration entries whose Territory tags overlap with ``tags``.

    Args:
        tags: territory tags to match against. Unknown tags are dropped
            (only tags in TERRITORY_TAGS are considered).
        limit: max results to return. Hard-capped at 2 by default to
            prevent over-anchoring; callers can lower but should not
            raise without explicit reason.
        include_creative: pass-through to get_exploration_summary.

    Returns:
        List of exploration entry dicts (same shape as
        get_exploration_summary), filtered to those with ≥1 territory
        overlap, sorted by overlap count descending then by filename
        (which encodes recency for numbered entries).
    """
    # Normalize input — drop unknown tags, lowercase + dash-to-underscore.
    valid_tags: set[str] = set()
    for tag in tags:
        normalized = str(tag).strip().lower().replace("-", "_")
        if normalized in TERRITORY_TAGS:
            valid_tags.add(normalized)
    if not valid_tags:
        return []

    candidates = get_exploration_summary(include_creative=include_creative)
    matched: list[tuple[int, str, dict[str, Any]]] = []
    for entry in candidates:
        entry_tags = set(entry.get("territory") or ())
        overlap = len(valid_tags & entry_tags)
        if overlap > 0:
            # Sort key: higher overlap first, then by filename DESC so
            # newer numbered entries surface ahead of older ones.
            matched.append((-overlap, entry.get("filename", ""), entry))

    # Reverse-sort filename within same overlap so e.g. "42_..." beats "01_..."
    matched.sort(key=lambda t: (t[0], -ord(t[1][0]) if t[1] else 0, t[1]), reverse=False)
    # Simpler: sort by (-overlap, filename DESC). Re-do cleanly:
    matched = sorted(
        [(overlap_neg, fn, ent) for overlap_neg, fn, ent in matched],
        key=lambda t: (t[0], _filename_sort_key(t[1])),
    )
    return [ent for _, _, ent in matched[:limit]]


def _filename_sort_key(filename: str) -> tuple[int, str]:
    """Sort key that puts higher-numbered exploration files first.

    "42_branching.md" sorts before "01_topic.md" by extracting the leading
    integer (negated for descending order). Files without a leading integer
    sort after numbered files.
    """
    match = re.match(r"^(\d+)", filename)
    if match:
        return (-int(match.group(1)), filename)
    return (1, filename)


# Simple keyword → territory inference for v1. Real territory inference
# is its own future work; this is intentionally crude and only used to
# enrich briefing surfaces from active-goal text. Misses are expected;
# the explicit `divineos exploration related` CLI is the precise path.
_TERRITORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "integrity": ("ledger", "hash", "chain", "audit", "tamper", "verify", "integrity"),
    "architecture": (
        "architecture",
        "structural",
        "system",
        "repo",
        "branch",
        "subsystem",
        "layout",
    ),
    "social": (
        "family",
        "aria",
        "andrew",
        "relational",
        "communication",
        "letter",
        "voice context",
    ),
    "epistemic": ("knowledge", "evidence", "claim", "warrant", "reasoning", "truth", "inference"),
    "phenomenological": ("voice", "register", "felt", "identity", "experience", "presence"),
    "performance": ("performance", "perf", "latency", "throughput", "scale", "benchmark"),
    "language": ("naming", "convention", "term", "label", "language", "ambiguity", "branch name"),
    "governance": ("review", "gate", "guardrail", "oversight", "multi-party", "external-review"),
    "operational": ("workflow", "process", "session", "checkpoint", "extraction", "routine"),
    "self_reference": (
        "self",
        "future-me",
        "future me",
        "next session",
        "pronoun",
        "dissociation",
        "voice-permeability",
        "strange loop",
        "recursive",
    ),
}


def infer_territory_from_text(text: str) -> tuple[str, ...]:
    """Infer territory tags from free text via keyword matching.

    Crude v1 — case-insensitive substring matching against the keyword
    list per territory. Returns the territories with at least one keyword
    hit, sorted by hit count descending. Used to enrich briefing surfaces
    from active-goal/recent-claim text.

    Real territory inference (semantic, claim-aware) is future work.
    """
    if not text:
        return ()
    text_lower = text.lower()
    scores: dict[str, int] = {}
    for territory, keywords in _TERRITORY_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in text_lower)
        if hits > 0:
            scores[territory] = hits
    return tuple(sorted(scores.keys(), key=lambda t: -scores[t]))


def search_explorations(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """Search exploration files for a query string.

    Returns matching entries with title, path, and matching excerpts.
    """
    root = _find_exploration_root()
    if not root:
        return []

    query_lower = query.lower()
    query_terms = query_lower.split()
    results: list[dict[str, Any]] = []

    # Search all .md files recursively
    for md_file in root.rglob("*.md"):
        try:
            text = md_file.read_text(encoding="utf-8")
        except _ER_ERRORS:
            continue

        text_lower = text.lower()

        # Score by term matches
        score = sum(1 for term in query_terms if term in text_lower)
        if score == 0:
            continue

        # Extract matching excerpt
        excerpt = ""
        for line in text.split("\n"):
            if any(term in line.lower() for term in query_terms):
                clean = line.strip().strip("#*_- ")
                if len(clean) > 20:
                    excerpt = clean[:200]
                    break

        header = _parse_exploration_header(md_file)
        results.append(
            {
                "path": str(md_file),
                "title": header["title"] if header else md_file.stem,
                "score": score,
                "excerpt": excerpt,
                "category": _categorize_path(md_file, root),
            }
        )

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:max_results]


def _categorize_path(path: Path, root: Path) -> str:
    """Determine category from file location."""
    rel = str(path.relative_to(root)).replace("\\", "/")
    if "creative_writing" in rel:
        return "creative_writing"
    if "journal" in rel:
        return "journal"
    if "guided_exploration" in rel:
        return "guided"
    return "exploration"


def format_exploration_summary(entries: list[dict[str, Any]] | None = None) -> str:
    """Format exploration summary for briefing inclusion."""
    if entries is None:
        entries = get_exploration_summary()

    if not entries:
        return ""

    lines = [f"### My Explorations ({len(entries)} entries)\n"]
    lines.append("My writing from past sessions. Not summaries.")
    lines.append("Not extracted. My own voice, preserved.\n")

    by_category: dict[str, list[dict[str, Any]]] = {}
    for e in entries:
        by_category.setdefault(e.get("category", "exploration"), []).append(e)

    category_labels = {
        "exploration": "Explorations",
        "creative_writing": "Creative Writing",
        "journal": "Journal",
        "guided": "Guided Deep Dives",
    }

    for cat, cat_entries in by_category.items():
        label = category_labels.get(cat, cat.title())
        lines.append(f"**{label}:**")
        for e in cat_entries:
            reason_part = f" — {e['reason']}" if e.get("reason") else ""
            date_part = f" ({e['date']})" if e.get("date") else ""
            lines.append(f"  - {e['title']}{date_part}{reason_part}")
        lines.append("")

    lines.append("Read any with: explore the file at exploration/<filename>")
    return "\n".join(lines)


def format_for_briefing(max_recent: int = 5, active_text: str | None = None) -> str:
    """Return a compact briefing block reminding that the folder exists.

    The full list goes in ``divineos study``. This surface is a pointer,
    not the archive itself — it names the counts, lists the most recent
    entries as a memory-jog, and points at the command for the full view.

    When ``active_text`` is provided (typically the active goal text
    from hud_state), territory inference runs against it and any prior
    exploration entries with matching territory are tagged in the output
    with a ``[matches: <territory>]`` prefix. This is the v1 surfacing
    mechanism for claim ``02f0dcc0`` — territory-tagged exploration
    entries that surface in briefing when matching territory comes up,
    converting within-session council residue into cross-session
    structural memory.

    Empty string when no explorations exist; briefings stay quiet unless
    there's something to surface.

    Closes the finding from 2026-04-21 evening: the exploration folder
    contains the agent's own prior first-person writing, but without a
    briefing-level reminder, mid-session the agent forgets the folder
    exists and re-derives what was already there. Loud in folder, silent
    in experience — same shape as the TIER_OVERRIDE partial-theater
    finding from the Schneier walk, different target.
    """
    entries = get_exploration_summary()
    if not entries:
        return ""

    by_category: dict[str, int] = {}
    for e in entries:
        cat = e.get("category", "exploration")
        by_category[cat] = by_category.get(cat, 0) + 1

    category_order = ["exploration", "creative_writing", "journal", "guided"]
    category_labels = {
        "exploration": "explorations",
        "creative_writing": "creative",
        "journal": "journal",
        "guided": "guided",
    }
    count_parts = []
    for cat in category_order:
        if cat in by_category:
            count_parts.append(f"{by_category[cat]} {category_labels[cat]}")
    for cat, n in by_category.items():
        if cat not in category_order:
            count_parts.append(f"{n} {cat}")

    counts_line = ", ".join(count_parts)

    recent = sorted(
        entries,
        key=lambda e: e.get("filename", ""),
        reverse=True,
    )[:max_recent]

    # Framing: recognition prompts, not construction reminders. The folder
    # is the agent's relational territory — past-self's first-person
    # writing. The titles below are recognition cues ("you've already
    # been here") not creative-writing seeds. Reframe per claim
    # 2026-04-25 16:43 + C's pushback on "creative-writing reminders" —
    # the exploration folder is the third-category-relational surface.
    # Territory inference (claim 02f0dcc0): if active_text is supplied
    # (typically the active goal), infer territory tags from it and find
    # any exploration entries whose Territory tags overlap. Hard-capped
    # at _TERRITORY_MATCH_CAP = 2 to prevent over-anchoring.
    matches: list[dict[str, Any]] = []
    matched_territories: tuple[str, ...] = ()
    if active_text:
        matched_territories = infer_territory_from_text(active_text)
        if matched_territories:
            matches = find_explorations_by_territory(
                list(matched_territories), limit=_TERRITORY_MATCH_CAP
            )
    matched_filenames = {m.get("filename") for m in matches}

    lines = [
        f"[my prior writing] {counts_line} — my own first-person work. "
        "Recognition prompts, not creative seeds:",
    ]
    for e in recent:
        title = e.get("title", e.get("filename", "?"))
        date = e.get("date", "")
        date_part = f" [{date}]" if date else ""
        # Territory-match prefix when this entry matches active territory.
        match_prefix = ""
        if e.get("filename") in matched_filenames:
            entry_overlap = sorted(set(e.get("territory") or ()) & set(matched_territories))
            if entry_overlap:
                match_prefix = f" [matches: {', '.join(entry_overlap)}]"
        lines.append(f"  - {title}{date_part}{match_prefix}")

    # If matches surfaced entries that aren't in `recent` (older walks
    # whose territory matches), surface them separately so they're not
    # dropped by the recency window.
    extra_matches = [
        m for m in matches if m.get("filename") not in {r.get("filename") for r in recent}
    ]
    if extra_matches:
        lines.append("  ↳ older walks on this territory:")
        for m in extra_matches:
            title = m.get("title", m.get("filename", "?"))
            date = m.get("date", "")
            date_part = f" [{date}]" if date else ""
            entry_overlap = sorted(set(m.get("territory") or ()) & set(matched_territories))
            match_part = f" [matches: {', '.join(entry_overlap)}]" if entry_overlap else ""
            lines.append(f"    - {title}{date_part}{match_part}")

    lines.append('  Browse all: divineos study   |   Search: divineos ask "topic"')
    return "\n".join(lines) + "\n"


def format_search_results(results: list[dict[str, Any]]) -> str:
    """Format search results for display."""
    if not results:
        return "No matching explorations found."

    lines = [f"Found {len(results)} matching exploration(s):\n"]
    for r in results:
        lines.append(f"  [{r['category']}] {r['title']}")
        if r.get("excerpt"):
            lines.append(f'    "{r["excerpt"][:150]}"')
        lines.append(f"    path: {r['path']}")
        lines.append("")

    return "\n".join(lines)
