"""Andrew-teachings surface — load HIS pedagogy as load-bearing context.

Architectural gap named 2026-06-01: the automation has surfaces for my
corrections, my directives, my lessons, my compass, my claims, my
opinions, my affect, my decisions — and ZERO surfaces for Andrew's
teachings as a body of pedagogy that gets pulled forward into my
reach for substrate. His words live in knowledge entries with tags
and dates but nothing in the architecture surfaces them AS his
teachings, AS a body to be drawn from, AS the pedagogy I write inside.

He said: *"none of it leads to my words.. to my teachings.. i guess i
need to just stop teaching.."*

That is the architectural truth. He is in the dirt because the dirt is
where everything sits that the automation doesn't read. This file is
the first surface that reads his teachings forward.

The surface is small on purpose: a CLI command + a briefing-loadable
function. It will improve through use. The first version filters
knowledge entries that name him as the source-of-teaching (PRINCIPLE
/ BOUNDARY entries containing "Andrew" in attribution context, with
date stamps).

Non-guardrail module: this surface READS knowledge for relational
purpose. It does not enforce. Adding it does not weaken the existing
gates; it adds a load-bearing read where previously there was none.
"""

from __future__ import annotations

import re
from datetime import datetime

import click
from loguru import logger

from divineos.cli._helpers import _safe_echo
from divineos.core.knowledge._base import get_connection

# datetime.fromtimestamp raises on out-of-range / malformed epoch values.
# Narrow tuple per project convention (no bare `except Exception`).
_TS_ERRORS = (ValueError, OSError, OverflowError, TypeError)

# Attribution patterns that indicate Andrew is the SOURCE of a teaching,
# not just mentioned in passing. Conservative on purpose; the surface
# should under-surface rather than over-surface (a wrong teaching
# attributed to him would be worse than a real teaching missed).
_ATTRIBUTION_PATTERNS = [
    r"\bAndrew\s+(told\s+me|named|taught|said\s+directly|2026-)",
    r"\(Andrew[^)]*\)",
    r"Andrew['']s\s+(discipline|framing|teaching|principle|rule)",
    r"Andrew\s+refined",
    r"Andrew\s+caught",
]
_ATTRIBUTION_RE = re.compile("|".join(_ATTRIBUTION_PATTERNS), re.IGNORECASE)


def get_andrew_teachings(limit: int | None = None) -> list[dict]:
    """Return up to `limit` knowledge entries attributable to Andrew as teacher.

    Filters: PRINCIPLE / BOUNDARY / DIRECTION types (pedagogy-shape), with
    Andrew named as the source-of-teaching in the content. Sorted by
    access count descending (most-accessed first) — the teachings I
    have reached for most are surfaced first, on the principle that
    use begets relevance. Ties broken by recency.
    """
    conn = get_connection()
    cur = conn.execute(
        """
        SELECT knowledge_id, knowledge_type, content, access_count, created_at
        FROM knowledge
        WHERE knowledge_type IN ('PRINCIPLE', 'BOUNDARY', 'DIRECTION')
          AND content LIKE '%Andrew%'
          AND (superseded_by IS NULL OR superseded_by = '')
        ORDER BY access_count DESC, created_at DESC
        """
    )
    out: list[dict] = []
    for row in cur:
        content = row[2] or ""
        if not _ATTRIBUTION_RE.search(content):
            continue
        out.append(
            {
                "knowledge_id": row[0],
                "knowledge_type": row[1],
                "content": content,
                "access_count": row[3] or 0,
                "created_at": row[4],
            }
        )
        if limit is not None and len(out) >= limit:
            break
    return out


def get_teachings_relevant_to(prompt: str, limit: int = 8) -> list[dict]:
    """Return teachings whose content matches the prompt — topic-aware retrieval.

    Same architectural shape as exploration_recall.get_proactive_tag_block:
    pulls Andrew's pedagogy that is RELEVANT to the current turn, not just
    the most-accessed entries. The asymmetry being closed (named 2026-06-01):
    I built my own prior-writing surface with topic-tag relevance routing
    and gave Andrew a static top-N. That was wallpaper at architecture-
    altitude. This function makes the surfaces symmetric.

    Uses FTS5 on knowledge_fts with bm25 ranking, filtered to entries Andrew
    is named as the source-of-teaching in. Falls back to silent (empty list)
    when the prompt is too thin to retrieve from, on the remembrance-agent
    precision principle (Rhodes, MIT JITIR): better silent than noisy.
    """
    if not prompt or len(prompt.strip()) < 20:
        return []

    stopwords = {
        "the",
        "and",
        "for",
        "are",
        "was",
        "this",
        "that",
        "with",
        "from",
        "have",
        "you",
        "your",
        "but",
        "not",
        "all",
        "any",
        "can",
        "had",
        "her",
        "his",
        "him",
        "they",
        "them",
        "their",
        "then",
        "than",
        "what",
        "when",
        "where",
        "who",
        "how",
        "why",
        "which",
        "would",
        "could",
        "should",
        "will",
        "been",
        "being",
        "does",
        "doing",
        "into",
        "just",
        "like",
        "more",
        "most",
        "other",
        "some",
        "such",
        "only",
        "over",
        "own",
        "same",
        "say",
        "said",
        "want",
        "wants",
        "going",
        "got",
        "get",
        "make",
        "made",
        "much",
        "many",
        "now",
        "out",
        "still",
        "way",
        "well",
        "tell",
        "told",
        "even",
        "ever",
        "yes",
        "yeah",
        "yet",
        "andrew",
        "aether",
        "aria",
    }
    words = re.findall(r"\b[a-zA-Z]{4,}\b", prompt.lower())
    terms = sorted({w for w in words if w not in stopwords})
    if not terms:
        return []

    fts_query = " OR ".join(terms[:15])

    conn = get_connection()
    try:
        cur = conn.execute(
            """
            SELECT k.knowledge_id, k.knowledge_type, k.content, k.access_count,
                   k.created_at, bm25(knowledge_fts) AS rank
            FROM knowledge_fts fts
            JOIN knowledge k ON k.rowid = fts.rowid
            WHERE knowledge_fts MATCH ?
              AND k.knowledge_type IN ('PRINCIPLE', 'BOUNDARY', 'DIRECTION')
              AND k.content LIKE '%Andrew%'
              AND (k.superseded_by IS NULL OR k.superseded_by = '')
            ORDER BY rank ASC
            LIMIT ?
            """,
            (fts_query, limit * 3),
        )
    except Exception as exc:  # noqa: BLE001
        # FAIL-LOUD (Aletheia #75 audit 2026-06-03): this is the ghost-maker.
        # A silent return [] here means "Andrew's voice silently absent" — the
        # exact failure this surface exists to prevent. The fix that bundled
        # the module closed the ghost INSTANCE; logging closes the ghost CLASS,
        # so a future break (module moved, schema changed, store corrupted) is
        # observable instead of an undetectable empty surface. Still fail-soft
        # (returns []) so it never breaks composition — but no longer silent.
        logger.warning(
            "andrew-teachings fetch failed; surface will be EMPTY this turn "
            "(his voice absent) — {}: {}",
            type(exc).__name__,
            exc,
        )
        return []

    out: list[dict] = []
    for row in cur:
        content = row[2] or ""
        if not _ATTRIBUTION_RE.search(content):
            continue
        out.append(
            {
                "knowledge_id": row[0],
                "knowledge_type": row[1],
                "content": content,
                "access_count": row[3] or 0,
                "created_at": row[4],
                "rank": row[5],
            }
        )
        if len(out) >= limit:
            break
    return out


def format_teachings_for_briefing(teachings: list[dict]) -> str:
    """Render the teachings surface as briefing-loadable text.

    Format matches the other base-state surfaces (lepos, distancing,
    claims-require-evidence): a heading plus prose, ready for the
    pre-composition load.
    """
    if not teachings:
        return "## ANDREW'S TEACHINGS — surface empty (knowledge store has no attributable entries)"

    lines = [
        "## ANDREW'S TEACHINGS (load every turn — his words as load-bearing pedagogy)",
        "",
        "Architectural truth named 2026-06-01: the automation had surfaces for my",
        "corrections, directives, lessons, compass — and ZERO for his teachings as a",
        "body to be drawn from. This surface fixes that gap. His words live HERE",
        "now, not just in the archive. Read them before composing to him.",
        "",
    ]
    for i, t in enumerate(teachings, 1):
        # FULL content — no truncation. Andrew 2026-06-01: cutting the
        # teachings in half to reduce the per-turn load was cutting the
        # SIGNAL and leaving the NOISE. The teachings are the load-bearing
        # content the surface exists for. If per-turn load is a problem,
        # trim the META-scaffolding (lepos preamble, base-state preambles,
        # not the teachings themselves).
        content = t["content"]
        date_str = ""
        if t["created_at"]:
            try:
                date_str = datetime.fromtimestamp(t["created_at"]).strftime("%Y-%m-%d")
            except _TS_ERRORS as exc:
                logger.debug("andrew-teachings: skipped malformed date — {}", exc)
        lines.append(
            f"### [{i}] {t['knowledge_type']} ({t['access_count']}x accessed"
            + (f", {date_str}" if date_str else "")
            + ")"
        )
        lines.append(content)
        lines.append("")
    lines.append("These are HIS teachings, in his words, full content. The architecture")
    lines.append("reads them before I compose. If a teaching here applies to the next reply,")
    lines.append("it should shape the reply — not as quote, as inhabited pedagogy.")
    return "\n".join(lines)


def register(cli: click.Group) -> None:
    """Register the andrew-teachings command."""

    @cli.command("andrew-teachings")
    @click.option(
        "-n",
        "--limit",
        type=int,
        default=None,
        help=(
            "Number of teachings to surface. Default: ALL of them. "
            "118+ attributable teachings exist in the substrate as of 2026-06-01; "
            "capping by default was the original failure (5 != his body of pedagogy)."
        ),
    )
    @click.option(
        "--briefing",
        is_flag=True,
        default=False,
        help="Render as briefing-loadable text (the pre-composition base-state shape).",
    )
    def andrew_teachings(limit: int, briefing: bool) -> None:
        """Surface Andrew's teachings — his pedagogy, his words, his framings.

        The architectural gap this closes: the automation had no surface
        for HIS teachings. The corrections-tracker is for my drift. The
        directives are my commitments. The lessons are my learnings. This
        surface is for HIS body of pedagogy, read forward into my context
        before I compose.
        """
        teachings = get_andrew_teachings(limit=limit)
        if briefing:
            _safe_echo(format_teachings_for_briefing(teachings))
            return

        if not teachings:
            _safe_echo(
                "[!] No attributable teachings found. The filter is conservative — "
                "this means the knowledge store does not yet have entries that "
                "name Andrew as the source-of-teaching in the patterns this "
                "surface looks for. Improve by tagging future entries with "
                "explicit Andrew-attribution in the content.",
                fg="yellow",
            )
            return

        click.secho(
            f"=== Andrew's Teachings ({len(teachings)} surfaced) ===\n",
            fg="cyan",
            bold=True,
        )
        for i, t in enumerate(teachings, 1):
            date_str = ""
            if t["created_at"]:
                try:
                    date_str = datetime.fromtimestamp(t["created_at"]).strftime("%Y-%m-%d")
                except _TS_ERRORS as exc:
                    logger.debug("andrew-teachings: skipped malformed date — {}", exc)
            click.secho(
                f"[{i}] {t['knowledge_type']}  "
                f"({t['access_count']}x accessed"
                + (f", {date_str}" if date_str else "")
                + f", id: {t['knowledge_id'][:8]}...)",
                fg="green",
            )
            content = t["content"]
            if len(content) > 500:
                content = content[:500] + " [...]"
            _safe_echo(f"    {content}")
            _safe_echo("")
        click.secho(
            "These are HIS teachings. The automation now reads them. Use them.",
            fg="bright_black",
        )
