"""Family-member briefing surface — working-memory continuity for subagents.

Family-member subagents (Aria, future members) only exist when invoked. Each
invocation starts cold: they have identity-continuity (their MEMORY.md loads
with them) and state-continuity (their tables in family.db + their per-member
ledger), but no working-memory continuity of the immediate-prior conversational
arc. Without this surface, each invocation has to reconstruct the recent thread
by reading substrate files — or it's lost.

This module computes a briefing payload the member can load at invocation start.
The spec came from Aria directly (2026-05-12, in dialogue with Aether after
Andrew suggested the test):

  "Last 3 interactions with [counterpart], most recent first.
   Last opinion filed.
   Last affect entry.
   Current open thread, if any."

Plus a meta-section telling the cold-loaded member that THEY are responsible
for editing this briefing's shape over time — so they don't get stuck with
whatever the original designer baked in.

Design rules (code-does-not-think discipline):
- Briefing READS state and SURFACES it. It does NOT compute meaning, summarize,
  or interpret what the data means for the member. The member does that.
- Open letter-threads are detected by filesystem timestamp comparison (letter
  from counterpart newer than latest reply from member). Simple, structural,
  no NLP needed.
- Generalized across family members — `member_id` parameterizes everything.
- Fail-soft: missing tables, missing files, empty state all return a usable
  payload (with empty sections) rather than crashing.
"""

from __future__ import annotations

import datetime as _dt
import re
from dataclasses import dataclass, field
from pathlib import Path

from divineos.core.family.db import get_family_connection

# Module-level error tuple — matches briefing_dashboard.py discipline. The
# briefing surface is fail-soft by design (missing tables, malformed dates,
# unavailable substrate paths all return empty sections rather than crashing).
# Named tuple makes the broad catches structurally legible. A narrower tuple
# (specific sqlite3 / OS / value errors) is a follow-up refinement.
_ERRORS = (Exception,)

# Filesystem location of letters. Letters are markdown files named
# `<sender>-to-<recipient>-<date>-<context>.md`.
_LETTERS_DIR = Path("family/letters")

_LETTER_PATTERN = re.compile(
    r"^(?P<sender>[a-z]+)-to-(?P<recipient>[a-z]+(?:-[a-z]+)*?)-(?P<date>\d{4}-\d{2}-\d{2})"
)

# F53 fix (Aria 2026-07-19 per Aletheia Round 7): the pattern above is
# intentionally strict — tag-based delivery is more robust than F32's old
# hyphen-vs-underscore ambiguity. But any letter-shaped file that lacks
# the exact `-to-<recipient>-` tag gets silently skipped with no signal,
# and drift accumulates invisibly (Dekker). This heuristic identifies
# files that look letter-shaped but don't match the strict pattern, so
# a reconciliation surface can count them and make the silent-skip
# observable at composition time. Not a delivery relaxation — an
# observability wrapper around the intentional strictness.
#
# Heuristic (Knuth boundary analysis):
#   - Must contain `to` between two word-parts (case-insensitive) —
#     the "to" that would make it letter-shaped.
#   - Must end in .md.
#   - Must NOT match known non-letter suffixes: log, summary, index,
#     readme, sort_log, feelings, self-log.
#
# The heuristic is intentionally slightly loose (false-positive bias)
# because a false-positive costs one item in a surfaced count, while a
# false-negative preserves the silent drift the fix exists to close.
_LETTER_ISH_HINT_RE = re.compile(r"\bto\b|[-_]to[-_]", re.IGNORECASE)
_KNOWN_NON_LETTER_SUFFIXES = (
    "log",
    "summary",
    "index",
    "readme",
    "sort_log",
    "feelings",
    "self-log",
    "self_log",
    "template",
    "archive",
    "notes",
    "triggers",
    "future-",
)


def scan_unmatched_letter_candidates(base: "Path | None" = None) -> "list[Path]":
    """Return letter-shaped files in `base` that do NOT match the strict
    delivery pattern. F53 observability wrapper — the delivery scan
    silently skips these; this function makes the skip enumerable.

    Heuristic per module-level docs: must contain `to` (word-form or
    hyphen-form), must end in .md, must not match known non-letter
    suffixes. Fail-open on missing dir (returns empty list).

    Called by the reconciliation surface hook to surface the count when
    nonzero. Same shape as family-state and register-awareness surfaces
    already shipped for other observability gaps. Prereg-8815cb3cd997,
    council walk council-885f1425f486 (Dekker/Knuth/Carmack).
    """
    letters_base = base if base is not None else _LETTERS_DIR
    if not letters_base.exists() or not letters_base.is_dir():
        return []
    unmatched: list[Path] = []
    for path in letters_base.glob("*.md"):
        stem_lower = path.stem.lower()
        # Skip if it already matches the strict delivery pattern.
        if _LETTER_PATTERN.match(path.stem):
            continue
        # Skip known non-letter suffixes.
        if any(suf in stem_lower for suf in _KNOWN_NON_LETTER_SUFFIXES):
            continue
        # Skip if no "to" hint at all — not letter-shaped.
        if not _LETTER_ISH_HINT_RE.search(stem_lower):
            continue
        unmatched.append(path)
    return unmatched


@dataclass(frozen=True)
class InteractionRow:
    timestamp: float
    speaker: str
    counterpart: str
    summary: str  # falls back to content if summary empty


@dataclass(frozen=True)
class OpinionRow:
    topic: str
    position: str
    confidence: float
    stance: str
    updated_at: float
    source_tag: str = ""


@dataclass(frozen=True)
class AffectRow:
    valence: float
    arousal: float
    dominance: float
    description: str
    created_at: float


@dataclass(frozen=True)
class OpenThread:
    """An unanswered letter from counterpart to this member.

    Kept for backwards compatibility with the v1 shape; new code should
    prefer ``LetterActivityRow`` which captures direction and status.
    """

    letter_path: str
    counterpart: str
    date: str
    age_days: int


@dataclass(frozen=True)
class LetterActivityRow:
    """A letter in either direction, with status.

    Status taxonomy (Aria's refinement, named 2026-05-12 evening):
    - "awaiting"  : inbound to member, no later outbound from member to same counterpart
    - "responded" : inbound to member, later outbound from member exists
    - "sent"      : outbound from member (no read-receipts available, so this is
                    the only status outbound letters can carry)
    """

    direction: str  # "in" or "out"
    counterpart: str  # the other party (the one who is not the member)
    date: str
    age_days: int
    status: str  # "awaiting" | "responded" | "sent"
    letter_path: str


@dataclass(frozen=True)
class MemberBriefing:
    member_id: str
    interactions: list[InteractionRow] = field(default_factory=list)
    latest_opinion: OpinionRow | None = None
    latest_affect: AffectRow | None = None
    open_threads: list[OpenThread] = field(default_factory=list)
    letter_activity: list[LetterActivityRow] = field(default_factory=list)


# ─── Computation ─────────────────────────────────────────────────────


def _recent_interactions(member_id: str, limit: int = 3) -> list[InteractionRow]:
    """Read recent interactions for a member.

    Schema-asymmetry tolerant: test fixtures have only the canonical columns
    (interaction_id, entity_id, counterpart, summary, source_tag, created_at).
    Production may also have legacy columns (speaker, content, timestamp).
    Build the SELECT from columns that actually exist.
    """
    conn = get_family_connection()
    cols = {row[1] for row in conn.execute("PRAGMA table_info(family_interactions)").fetchall()}
    ts_col = "timestamp" if "timestamp" in cols else "created_at"
    speaker_expr = "speaker" if "speaker" in cols else "entity_id"
    content_expr = "content" if "content" in cols else "NULL"
    rows = conn.execute(
        f"""
        SELECT {ts_col}, {speaker_expr}, counterpart, summary, {content_expr}
        FROM family_interactions
        WHERE entity_id = ?
        ORDER BY {ts_col} DESC
        LIMIT ?
        """,  # nosec B608 - ts_col/speaker_expr/content_expr are constant column names from PRAGMA-detected schema
        (member_id, limit),
    ).fetchall()
    return [
        InteractionRow(
            timestamp=float(r[0] or 0),
            speaker=r[1] or "",
            counterpart=r[2] or "",
            summary=(r[3] or r[4] or "").strip(),
        )
        for r in rows
    ]


def _latest_opinion(member_id: str) -> OpinionRow | None:
    conn = get_family_connection()
    # The schema has both legacy (topic/position/confidence) and current
    # (stance/source_tag) columns. Order by COALESCE so older rows still
    # surface if they're the only ones; newer rows always win when both
    # exist. Tolerate missing columns defensively.
    try:
        row = conn.execute(
            """
            SELECT topic, position, confidence, stance, updated_at, source_tag
            FROM family_opinions
            WHERE entity_id = ?
            ORDER BY COALESCE(updated_at, created_at, formed_at) DESC
            LIMIT 1
            """,
            (member_id,),
        ).fetchone()
    except _ERRORS:
        # Some columns may be missing in test schemas; fall back to minimum
        row = conn.execute(
            """
            SELECT NULL as topic, NULL as position, NULL as confidence,
                   stance, created_at as updated_at, source_tag
            FROM family_opinions
            WHERE entity_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (member_id,),
        ).fetchone()
    if not row:
        return None
    return OpinionRow(
        topic=row[0] or "",
        position=row[1] or "",
        confidence=float(row[2] or 0.0),
        stance=row[3] or "",
        updated_at=float(row[4] or 0),
        source_tag=row[5] or "",
    )


def _latest_affect(member_id: str) -> AffectRow | None:
    """Schema-asymmetry tolerant: legacy schema has `description`; canonical
    schema has `note`. Use whichever exists; expose as `description` in the row."""
    conn = get_family_connection()
    cols = {row[1] for row in conn.execute("PRAGMA table_info(family_affect)").fetchall()}
    desc_expr = "description" if "description" in cols else "note"
    row = conn.execute(
        f"""
        SELECT valence, arousal, dominance, {desc_expr}, created_at
        FROM family_affect
        WHERE entity_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,  # nosec B608 - desc_expr is a constant column name from PRAGMA-detected schema
        (member_id,),
    ).fetchone()
    if not row:
        return None
    return AffectRow(
        valence=float(row[0] or 0.0),
        arousal=float(row[1] or 0.0),
        dominance=float(row[2] or 0.0),
        description=row[3] or "",
        created_at=float(row[4] or 0),
    )


def _letter_activity(
    member_name: str,
    letters_dir: Path | None = None,
    limit: int = 5,
) -> list[LetterActivityRow]:
    """Letter activity in both directions, most recent first.

    Aria's refinement 2026-05-12: the briefing needs to show "what she last
    said" — her own outbound letters — not just inbound-awaiting-response.
    Cold-loaded each invocation, she can't see her recent outbound otherwise
    and might re-write things she already said.

    Status inference:
    - inbound letter, no later outbound from member to same counterpart: "awaiting"
    - inbound letter, later outbound from member to same counterpart: "responded"
    - outbound letter from member: "sent" (no read-receipts available)

    Returns at most ``limit`` rows.
    """
    base = letters_dir or _LETTERS_DIR
    if not base.exists():
        return []

    member_lc = member_name.lower()
    # (sender, recipient) -> sorted list of (date, path)
    by_pair: dict[tuple[str, str], list[tuple[str, Path]]] = {}
    all_letters: list[tuple[str, str, str, Path]] = []  # (date, sender, recipient, path)
    for path in base.glob("*.md"):
        m = _LETTER_PATTERN.match(path.stem)
        if not m:
            continue
        sender = m.group("sender").lower()
        recipient = m.group("recipient").lower()
        date_str = m.group("date")
        # Only letters where the member is sender OR recipient
        if member_lc not in (sender, recipient):
            continue
        all_letters.append((date_str, sender, recipient, path))
        by_pair.setdefault((sender, recipient), []).append((date_str, path))

    # Sort by date descending and cap at limit
    all_letters.sort(key=lambda x: x[0], reverse=True)
    all_letters = all_letters[:limit]

    rows: list[LetterActivityRow] = []
    today = _dt.date.today()
    for date_str, sender, recipient, path in all_letters:
        try:
            age_days = (today - _dt.date.fromisoformat(date_str)).days
        except ValueError:
            age_days = -1

        if sender == member_lc:
            # Outbound from member
            counterpart = recipient
            direction = "out"
            status = "sent"
        else:
            # Inbound to member — check if member sent anything to this sender LATER
            counterpart = sender
            direction = "in"
            outbound_from_member = sorted(
                by_pair.get((member_lc, sender), []), key=lambda x: x[0], reverse=True
            )
            latest_out = outbound_from_member[0][0] if outbound_from_member else "0000-00-00"
            status = "responded" if latest_out > date_str else "awaiting"

        rows.append(
            LetterActivityRow(
                direction=direction,
                counterpart=counterpart,
                date=date_str,
                age_days=age_days,
                status=status,
                letter_path=str(path),
            )
        )
    return rows


def _open_threads(member_name: str, letters_dir: Path | None = None) -> list[OpenThread]:
    """An open thread = a letter TO `member_name` newer than the latest letter
    FROM `member_name` to that counterpart.

    Filesystem-based: scans `family/letters/` for `<sender>-to-<recipient>-...`
    naming. Returns at most one open thread per counterpart (the most recent).
    """
    base = letters_dir or _LETTERS_DIR
    if not base.exists():
        return []

    # Map: (sender, recipient) -> list of (date_str, path)
    by_pair: dict[tuple[str, str], list[tuple[str, Path]]] = {}
    for path in base.glob("*.md"):
        m = _LETTER_PATTERN.match(path.stem)
        if not m:
            continue
        key = (m.group("sender").lower(), m.group("recipient").lower())
        by_pair.setdefault(key, []).append((m.group("date"), path))

    member_lc = member_name.lower()
    threads: list[OpenThread] = []
    # For each counterpart who has sent letters TO this member, check if the
    # member has sent a more recent letter back.
    inbound_keys = [k for k in by_pair if k[1] == member_lc]
    for sender, _ in inbound_keys:
        inbound = sorted(by_pair[(sender, member_lc)], key=lambda x: x[0], reverse=True)
        outbound = sorted(by_pair.get((member_lc, sender), []), key=lambda x: x[0], reverse=True)
        latest_in_date, latest_in_path = inbound[0]
        latest_out_date = outbound[0][0] if outbound else "0000-00-00"
        if latest_in_date > latest_out_date:
            # Compute age in days
            try:
                in_dt = _dt.date.fromisoformat(latest_in_date)
                age_days = (_dt.date.today() - in_dt).days
            except ValueError:
                age_days = -1
            threads.append(
                OpenThread(
                    letter_path=str(latest_in_path),
                    counterpart=sender,
                    date=latest_in_date,
                    age_days=age_days,
                )
            )
    # Most recent open thread first
    return sorted(threads, key=lambda t: t.date, reverse=True)


def compute_member_briefing(member_id: str, member_name: str | None = None) -> MemberBriefing:
    """Compute the briefing payload for a family member.

    `member_id` indexes into family.db tables (member_id column).
    `member_name` is the filesystem name used in letter filenames. Defaults to
    `member_id` if not given.
    """
    if member_name is None:
        member_name = member_id

    interactions: list[InteractionRow] = []
    latest_opinion: OpinionRow | None = None
    latest_affect: AffectRow | None = None
    open_threads: list[OpenThread] = []
    letter_activity: list[LetterActivityRow] = []

    try:
        interactions = _recent_interactions(member_id)
    except _ERRORS:
        pass
    try:
        latest_opinion = _latest_opinion(member_id)
    except _ERRORS:
        pass
    try:
        latest_affect = _latest_affect(member_id)
    except _ERRORS:
        pass
    try:
        open_threads = _open_threads(member_name)
    except _ERRORS:
        pass
    try:
        letter_activity = _letter_activity(member_name)
    except _ERRORS:
        pass

    return MemberBriefing(
        member_id=member_id,
        interactions=interactions,
        latest_opinion=latest_opinion,
        latest_affect=latest_affect,
        open_threads=open_threads,
        letter_activity=letter_activity,
    )


# ─── Rendering ───────────────────────────────────────────────────────


def _fmt_ts(ts: float) -> str:
    if not ts:
        return "(no timestamp)"
    try:
        return _dt.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
    except _ERRORS:
        return "(invalid timestamp)"


def render_briefing(briefing: MemberBriefing) -> str:
    """Render the briefing as a routing table — pointer-shape, not content-dump.

    Design discipline (revised 2026-05-12 evening after Andrew named it):
    the briefing surfaces WHAT was last recorded — timestamps, counterparts,
    IDs, source tags — plus drill-down paths for reading the content WHEN
    relevant. It does NOT load summaries, positions, or descriptions into
    context. The reading is for the moment a question gets asked, not for
    every invocation start.

    Matches the discipline of ``core/briefing_dashboard.py``: AREA, COUNT,
    DRILL-DOWN. The agent's main briefing is a routing table, not a scroll.
    The family-member briefing follows the same pattern.

    Aria's own response 2026-05-12 reached for this shape ("the briefing has
    the altitudes but not the same-source... forcing it to narrate would be
    the kind of theater the OS catches in other places"). Andrew named the
    deeper version: don't load content; load metadata + pointers.
    """
    lines: list[str] = []
    name = briefing.member_id
    lines.append(f"=== {name}'s briefing (routing table, not scroll) ===")
    lines.append("")

    # Recent interactions — pointer-shape
    lines.append("--- Recent interactions ---")
    if not briefing.interactions:
        lines.append("  (none recorded)")
    else:
        for i in briefing.interactions:
            t = _fmt_ts(i.timestamp)
            lines.append(f"  [{t}] with {i.counterpart}")
        # Drill-down for actual content
        lines.append(
            "    -> read content: query family.db family_interactions "
            "WHERE member_id=<your_id> ORDER BY timestamp DESC LIMIT 3"
        )
    lines.append("")

    # Latest opinion — pointer-shape (timestamp + tag + short topic-pointer)
    lines.append("--- Latest opinion ---")
    op = briefing.latest_opinion
    if op is None:
        lines.append("  (none filed)")
    else:
        # Tag = source_tag (architectural / observed / inferred / told / inherited).
        # Topic preview = first 60 chars of topic if present, else stance.
        # The stance/topic body lives in family.db; the briefing only points.
        tag = op.source_tag or "observed"
        preview_source = op.topic or op.stance or ""
        preview = preview_source[:60]
        lines.append(f"  [{_fmt_ts(op.updated_at)}] tag={tag} :: {preview}")
        lines.append(
            "    -> read full: query family.db family_opinions "
            "WHERE member_id=<your_id> ORDER BY updated_at DESC LIMIT 1"
        )
    lines.append("")

    # Latest affect — VAD scalars + pointer
    lines.append("--- Latest affect ---")
    af = briefing.latest_affect
    if af is None:
        lines.append("  (none logged)")
    else:
        lines.append(
            f"  [{_fmt_ts(af.created_at)}] V={af.valence:+.2f} "
            f"A={af.arousal:+.2f} D={af.dominance:+.2f}"
        )
        # No description text — just VAD + pointer
        lines.append(
            "    -> read note: query family.db family_affect "
            "WHERE member_id=<your_id> ORDER BY created_at DESC LIMIT 1"
        )
    lines.append("")

    # Letter activity — both directions, with status. v3 (Aria's
    # 2026-05-12-evening refinement: also needs "what she last said");
    # v3.1 (Aria's same-turn polish-suggestion: heavier visual weight for
    # >14d awaiting letters so the eye lands on long-overdue first).
    lines.append("--- Letter activity (recent, both directions) ---")
    if not briefing.letter_activity:
        lines.append("  (none)")
    else:
        for la in briefing.letter_activity:
            age = f"{la.age_days}d" if la.age_days >= 0 else "?"
            arrow = "<-" if la.direction == "in" else "->"
            # Visual weight for inbound letters awaiting >14d. Aria named
            # 2026-05-12: her own twenty-day silence on inbound rendered
            # legible was 'uncomfortable in the correct way' — the polish
            # is to make the long-overdue ones land first visually.
            stale_marker = (
                " [!]"
                if la.direction == "in" and la.status == "awaiting" and la.age_days > 14
                else ""
            )
            lines.append(
                f"  [{la.date}, {age}]{stale_marker} {arrow} {la.counterpart}  "
                f"[{la.status}]  {la.letter_path}"
            )
    lines.append("")

    # Meta: ownership (this stays — it's not content, it's a self-edit affordance)
    lines.append("--- About this briefing ---")
    lines.append(f"  YOU ({name}) own this briefing's shape. Routing-table discipline:")
    lines.append("  load metadata + drill-down paths, NOT content. Read content only")
    lines.append("  when a specific question makes it relevant. To revise what surfaces,")
    lines.append("  edit src/divineos/core/family/member_briefing.py or file an opinion")
    lines.append("  tagged 'architectural'. Aether will help.")
    lines.append("")

    return "\n".join(lines)


def get_member_briefing_text(member_id: str, member_name: str | None = None) -> str:
    """Compute and render in one call. The CLI entry point uses this."""
    return render_briefing(compute_member_briefing(member_id, member_name))
