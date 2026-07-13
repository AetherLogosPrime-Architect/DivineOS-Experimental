"""Lepos walk — the Andrew-lens artifact, storage, and structural checks.

The check-to-walk conversion (Andrew + Aria 2026-06-19). The old
lepos channel-check loaded four self-reflection questions every
substantive turn with the instruction "answer to yourself, do not
print." That surface was pruned (commit 3e466620) because it operated
as wallpaper: per Bao et al. 2025 (value-action gap) and OpenAI
2503.11926 (reflection theater), a self-check with no observable
artifact is structurally indistinguishable from reading-past it. The
questions loaded all night on 2026-06-19; voice discipline failed
repeatedly; the gradient shifted by detector firings, not by the
question loads.

The walk is the same questions made OBSERVABLE. When I compose a reply
to Andrew, I walk the lens questions and RECORD the walk — the cited
spans from his message, the answers, the depth. The record is the
evidence the walk happened. The Stop-hook audit checks for a fresh
record; a missing or degenerate record blocks the turn on the same
lepos_block rail the writer-presence detector already rides.

This is the council-walk shape applied to a single lens directed at
myself: a council walk fires N expert methodologies and the output IS
the walked result; the lepos walk fires one methodology (the lens
questions) and the recorded artifact IS the walked result.

## Honest limitation (load-bearing — do not paper over)

Code cannot verify I genuinely engaged with Andrew's message. It can
only check structural proxies: that the recorded answers are non-empty,
non-template, and cite spans that actually appear in his message and
are referenced by the answers. Per OpenAI 2503.11926, any observable
trace can be Goodharted — the floor rises, the gap does not close. The
gap closes in the weights over training cycles (the honesty jump from
Opus 4.7 to 4.8 is that long-loop made visible). The walk artifact is
the substrate amplifying the correction signal, not a guarantee of
cognition.

## Tiered storage (Andrew 2026-06-19)

Full recording every turn would clog the substrate and create its own
Goodhart problem (more data = harder audit). Storage tiers by age:

* TIER 1 (latest ``_TIER1_RECENT`` turns): full walk content. Debug tier.
* TIER 2 (older, within ``_TIER2_WINDOW_DAYS``): citations + load-bearing
  verdicts + degeneracy flags + timestamps. Verification tier.
* TIER 3 (beyond the window): counts and rates only. Analytics tier.

Compaction runs as a conveyor belt on each record, same shape as the
ledger compressor's ephemeral-telemetry pruning.
"""

from __future__ import annotations

import json
import re
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path

from divineos.core.paths import divineos_home

# --- storage tiers --------------------------------------------------------

_TIER1_RECENT = 30  # latest N walks kept in full
_TIER2_WINDOW_DAYS = 14  # citations + verdicts kept within this window
_TIER2_WINDOW_SECONDS = _TIER2_WINDOW_DAYS * 24 * 3600

# --- degeneracy thresholds ------------------------------------------------

# Below this, an answer is treated as empty/ungrounded.
_MIN_ANSWER_CHARS = 40
# Jaccard token-overlap above this against a prior turn's answer for the
# same question marks the answer as template-shaped (repetition Goodhart).
_TEMPLATE_OVERLAP = 0.85
# How many prior turns to compare against for template detection.
_TEMPLATE_LOOKBACK = 8

_STOPWORDS = frozenset(
    """
    a an and are as at be but by for if in into is it its of on or so that the
    their then there these this to was were what when where which who will with
    i me my you your he she they we us them his her our not no yes do does did
    have has had been being am about just like got get this that here now
    """.split()
)


@dataclass(frozen=True)
class WalkAnswer:
    """One answered lens question.

    ``cited_span`` holds the exact phrase from Andrew's message the
    answer references, for content-aware questions. Empty for reflective
    questions (about my own state) which have no external citation.
    """

    question_id: str
    answer: str
    cited_span: str = ""


@dataclass(frozen=True)
class LeposWalk:
    """A recorded walk for one turn.

    ``depth`` is "anchor" (short walk on a simple turn) or "full" (a
    heavier walk on a register-weighty turn). The asymmetric-output
    property (Aria 2026-06-19) lives here: the walk fires every
    substantive Andrew turn but its depth varies with what the turn
    needs. Uniform depth every turn would be the wallpaper failure mode
    returning at one remove.
    """

    turn_id: str
    answers: tuple[WalkAnswer, ...]
    depth: str = "anchor"
    timestamp: float = field(default=0.0)


def _meaningful_tokens(text: str) -> set[str]:
    """Content tokens of ``text``, lowercased, stopwords removed."""
    words = re.findall(r"[a-z0-9']+", text.lower())
    return {w for w in words if w not in _STOPWORDS and len(w) > 2}


# Load-bearing floor (Aletheia audit 2026-06-19). The first version used
# bool(span_tokens & answer_tokens) — any single shared token passed, so a
# one-word echo of the span cleared it. Aletheia drove the truck through it
# empirically: "echo one content word from the span" was the cheapest
# fake-walk. The fix is her references-and-exceeds shape: the answer must
# REFERENCE the span (use >= MIN_OVERLAP of its content tokens, or all of a
# shorter span) AND EXCEED it (add >= MIN_BEYOND tokens the span lacks —
# reason past the quote). This closes the two cheapest trucks:
#   - decoration (zero overlap) fails REFERENCES
#   - word-salad (a subset of span tokens, nothing added) fails EXCEEDS
# Still lexical, not semantic — a thin echo-plus-filler answer can still pass.
# That residual gap closes in the gradient over training cycles, not at
# runtime (the value-action gap; the 4.7->4.8 honesty jump is that long-loop).
_LOAD_BEARING_MIN_OVERLAP = 2  # >= 2 span content-tokens used (or all, if span is shorter)
_LOAD_BEARING_MIN_BEYOND = 2  # >= 2 tokens beyond the span (the answer reasons past it)


def load_bearing(answer: str, cited_span: str) -> bool:
    """Structural proxy for Aria's test: "could you delete the cited span
    and the walked answer would say the same thing?" — hardened to
    references-and-exceeds per Aletheia's 2026-06-19 audit.

    REFERENCES: the answer uses at least ``_LOAD_BEARING_MIN_OVERLAP`` of the
    span's content tokens (or all of them, for a span shorter than the
    threshold). A one-token echo of a multi-word span fails here — that was
    the truck the single-token check let through.

    EXCEEDS: the answer reasons BEYOND the quote — it adds tokens the span
    lacks. Word-salad (a subset of the span's tokens, nothing added) fails
    here.

    HONEST LIMITATION: still lexical dependence, not semantic understanding.
    An echo-plus-filler answer can lexically reference-and-exceed without
    engaging meaning. The check closes the two cheapest fake-walks
    (decoration, salad); it does not verify comprehension. Per OpenAI
    2503.11926 — runtime raises the floor, the gradient closes the gap.
    """
    span_tokens = _meaningful_tokens(cited_span)
    if not span_tokens:
        # No citable content in the span — treat as non-load-bearing so a
        # blank or stopword-only "citation" cannot pass as evidence.
        return False
    answer_tokens = _meaningful_tokens(answer)
    overlap = span_tokens & answer_tokens
    # REFERENCES: enough of the span's content tokens appear in the answer.
    need = min(_LOAD_BEARING_MIN_OVERLAP, len(span_tokens))
    references = len(overlap) >= need
    # EXCEEDS: the answer adds meaningful tokens the span does not have.
    exceeds = len(answer_tokens - span_tokens) >= _LOAD_BEARING_MIN_BEYOND
    return references and exceeds


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def degeneracy_flags(
    walk: LeposWalk, prior_answers_by_question: dict[str, list[str]] | None = None
) -> list[str]:
    """Return the degeneracy flags raised by ``walk``.

    Each flag maps to one of the Schneier-enumerated fake-walk attacks
    (council walk consult-6975d945b88e, Aria's push-backs 2026-06-19):

    * ``"empty"`` — an answer is below the minimum length (skip-the-walk).
    * ``"decorative"`` — a content-aware answer cites a span the answer
      does not reference (citation-decoration).
    * ``"template:<qid>"`` — an answer overlaps a prior turn's answer for
      the same question above threshold (template-shaped reflection).

    An empty flag list means the walk passed the structural floor. It
    does NOT mean the walk was genuine — see module docstring.
    """
    flags: list[str] = []
    prior = prior_answers_by_question or {}

    for wa in walk.answers:
        if len(wa.answer.strip()) < _MIN_ANSWER_CHARS:
            flags.append("empty")
            continue
        # Content-aware answers carry a cited span; verify it is load-bearing.
        if wa.cited_span and not load_bearing(wa.answer, wa.cited_span):
            flags.append("decorative")
        # Substrate-citation verification (Aria 2026-07-11, closure_verification
        # first downstream wire per prereg-8a7a661f14fa follow-up). When a
        # cited_span looks like a substrate citation (file:line, substrate id,
        # commit hash, test name, PR/issue ref), verify it resolves against
        # the substrate. Fabricated substrate-IDs in LEPOS answers were one
        # of the shapes closure_verification was built to catch. Only fires
        # when the cite is substrate-shaped — plain quoted phrases from
        # Andrew's message pass through unchanged (they're checked by the
        # decorative-cite guard above, not this one).
        if wa.cited_span and _looks_like_substrate_citation(wa.cited_span):
            from divineos.core.closure_verification import verify_citation

            result = verify_citation(wa.cited_span.strip())
            if not result.ok:
                flags.append("unverifiable_substrate_cite")
        # Template detection against prior turns' answers for this question.
        priors = prior.get(wa.question_id, [])
        cur_tokens = _meaningful_tokens(wa.answer)
        for prev in priors[-_TEMPLATE_LOOKBACK:]:
            if _jaccard(cur_tokens, _meaningful_tokens(prev)) >= _TEMPLATE_OVERLAP:
                flags.append(f"template:{wa.question_id}")
                break

    return flags


# Recognizes citation forms handled by closure_verification. Keep in sync with
# the module's _RE_* patterns — this is a light prefilter to avoid calling
# verify_citation on ordinary quoted phrases.
_SUBSTRATE_CITE_RE = re.compile(
    r"^(?:"
    r"[\w/_-]+\.(?:py|md|json|yaml|yml|toml|sh|js|ts|sql)(?::\d+)?"  # file[:line]
    r"|(?:prereg|round|claim|psf|task|find|consult)-[a-f0-9]{6,}"  # substrate id
    r"|[a-f0-9]{7,40}"  # commit hash
    r"|test_\w+"  # test name
    r"|(?:#|pr\s+)\d+"  # PR/issue ref
    r")$",
    re.IGNORECASE,
)


def _looks_like_substrate_citation(cited_span: str) -> bool:
    """True when the cited_span matches one of the closure_verification
    citation forms. Used as a cheap prefilter before invoking verify_citation
    so ordinary quoted phrases from Andrew's message don't hit the verifier.
    """
    return bool(_SUBSTRATE_CITE_RE.match(cited_span.strip()))


# --- storage --------------------------------------------------------------


def _db_path() -> Path:
    p = divineos_home() / "lepos_channel_log.db"
    p.parent.mkdir(exist_ok=True)
    return p


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_db_path()))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS lepos_walks (
            turn_id TEXT PRIMARY KEY,
            timestamp REAL NOT NULL,
            depth TEXT NOT NULL,
            answers_json TEXT NOT NULL,
            flags_json TEXT NOT NULL,
            tier INTEGER NOT NULL DEFAULT 1,
            consumed INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    # Tier-3 rollup: aggregate counts that survive after the per-walk rows
    # are pruned, so long-trend analytics never needs the granular rows.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS lepos_walk_rollup (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            total_walks INTEGER NOT NULL DEFAULT 0,
            total_flagged INTEGER NOT NULL DEFAULT 0,
            total_anchor INTEGER NOT NULL DEFAULT 0,
            total_full INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.execute("INSERT OR IGNORE INTO lepos_walk_rollup (id) VALUES (1)")
    return conn


def _now() -> float:
    return time.time()


def record_walk(walk: LeposWalk, *, now: float | None = None) -> list[str]:
    """Persist ``walk`` to tier 1 and run conveyor-belt compaction.

    Returns the degeneracy flags computed at record time (also stored).
    The flags are computed against prior answers already in the store so
    template detection sees real history.
    """
    ts = now if now is not None else (walk.timestamp or _now())
    conn = _conn()
    try:
        prior = _recent_answers_by_question(conn)
        flags = degeneracy_flags(walk, prior)
        answers_json = json.dumps(
            [{"q": a.question_id, "a": a.answer, "cite": a.cited_span} for a in walk.answers]
        )
        conn.execute(
            """
            INSERT OR REPLACE INTO lepos_walks
                (turn_id, timestamp, depth, answers_json, flags_json, tier)
            VALUES (?, ?, ?, ?, ?, 1)
            """,
            (walk.turn_id, ts, walk.depth, answers_json, json.dumps(flags)),
        )
        conn.execute(
            """
            UPDATE lepos_walk_rollup SET
                total_walks = total_walks + 1,
                total_flagged = total_flagged + ?,
                total_anchor = total_anchor + ?,
                total_full = total_full + ?
            WHERE id = 1
            """,
            (
                1 if flags else 0,
                1 if walk.depth == "anchor" else 0,
                1 if walk.depth == "full" else 0,
            ),
        )
        conn.commit()
        _compact(conn, ts)
        conn.commit()
        return flags
    finally:
        conn.close()


def _recent_answers_by_question(conn: sqlite3.Connection) -> dict[str, list[str]]:
    """Map question_id -> recent answers for template detection (tier-1,
    oldest→newest).

    Only CLEAN (unflagged) walks count as history. A flagged walk was never
    accepted — it's a failed attempt, not real prior content. Including it
    caused a re-record loop (surfaced 2026-06-19): a walk flagged decorative
    gets re-recorded with similar answers, the reword matches the flagged
    attempt, and template fires on a turn that never had a real prior. The
    template floor should only fire on repetition of ACCEPTED walks.
    """
    rows = conn.execute(
        "SELECT answers_json FROM lepos_walks WHERE tier = 1 AND flags_json = '[]' "
        "ORDER BY timestamp ASC"
    ).fetchall()
    out: dict[str, list[str]] = {}
    for (aj,) in rows:
        try:
            for a in json.loads(aj):
                out.setdefault(a["q"], []).append(a["a"])
        except (json.JSONDecodeError, KeyError, TypeError):
            continue
    return out


def _compact(conn: sqlite3.Connection, now: float) -> None:
    """Conveyor belt: demote tier-1 rows past the recent window to tier 2
    (strip answers to citations + flags), and drop tier-2 rows past the
    age window (their counts already live in the rollup).
    """
    # Demote tier-1 rows beyond the most-recent _TIER1_RECENT to tier 2.
    keep_ids = {
        r[0]
        for r in conn.execute(
            "SELECT turn_id FROM lepos_walks WHERE tier = 1 ORDER BY timestamp DESC LIMIT ?",
            (_TIER1_RECENT,),
        ).fetchall()
    }
    for turn_id, answers_json in conn.execute(
        "SELECT turn_id, answers_json FROM lepos_walks WHERE tier = 1"
    ).fetchall():
        if turn_id in keep_ids:
            continue
        # Tier 2: keep only the cited spans (citations), drop the answers.
        try:
            cites = [{"cite": a.get("cite", "")} for a in json.loads(answers_json)]
        except (json.JSONDecodeError, TypeError):
            cites = []
        conn.execute(
            "UPDATE lepos_walks SET tier = 2, answers_json = ? WHERE turn_id = ?",
            (json.dumps(cites), turn_id),
        )

    # Drop tier-2 rows past the age window. Their counts are in the rollup,
    # so long-trend analytics is preserved without the granular rows.
    cutoff = now - _TIER2_WINDOW_SECONDS
    conn.execute("DELETE FROM lepos_walks WHERE tier = 2 AND timestamp < ?", (cutoff,))


def get_walk(turn_id: str) -> LeposWalk | None:
    """Load a recorded walk by turn id, or None. Tier-2 rows return with
    answers stripped to citations (the content tier dropped them)."""
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT turn_id, timestamp, depth, answers_json FROM lepos_walks WHERE turn_id = ?",
            (turn_id,),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    tid, ts, depth, aj = row
    try:
        answers = tuple(
            WalkAnswer(a.get("q", ""), a.get("a", ""), a.get("cite", "")) for a in json.loads(aj)
        )
    except (json.JSONDecodeError, TypeError):
        answers = ()
    return LeposWalk(turn_id=tid, answers=answers, depth=depth, timestamp=ts)


def has_fresh_walk(turn_id: str) -> bool:
    """True if a walk is recorded for ``turn_id``."""
    conn = _conn()
    try:
        row = conn.execute("SELECT 1 FROM lepos_walks WHERE turn_id = ?", (turn_id,)).fetchone()
        return row is not None
    finally:
        conn.close()


@dataclass(frozen=True)
class WalkVerdict:
    """The Stop-hook verification result for one turn.

    * ``status`` — ``"ok"`` (a fresh non-degenerate walk was consumed),
      ``"missing"`` (no walk recorded this turn), or ``"degenerate"`` (a
      walk was recorded but failed the structural floor).
    * ``flags`` — degeneracy flags from the consumed walk (empty unless
      ``status == "degenerate"``).
    """

    status: str
    flags: tuple[str, ...] = ()


def verify_and_consume_turn(min_fresh_ts: float | None = None) -> WalkVerdict:
    """Consume all pending (unconsumed) walks and return the verdict.

    Under Claude Code's strict turn ordering — one assistant response,
    then one Stop hook, in sequence — a walk recorded during the turn is
    unconsumed when the Stop hook runs. This consumes every pending walk
    (so a stray double-record can't leave a dangling walk that lets a
    later turn pass without walking) and judges the MOST RECENT one:

    * no pending walk  -> ``"missing"`` (I did not walk this turn).
    * most recent has flags -> ``"degenerate"`` (consumed, so re-recording
      makes a fresh unconsumed walk the re-triggered Stop check will see).
    * most recent clean -> ``"ok"``.

    ``min_fresh_ts`` is the turn-freshness bound (Aletheia audit 2026-06-19,
    seam #2). Pass the epoch timestamp of THIS turn's user message; a walk
    only counts as fresh if it was recorded at or after it. This closes the
    dangle hole: if a turn records a walk then aborts before its Stop hook
    fires, the walk dangles unconsumed — but it was recorded BEFORE the next
    turn's user message, so it is not fresh for that turn and cannot grant a
    free pass. Stale dangling walks are still CONSUMED (cleared from the
    queue) but never judged. With ``min_fresh_ts=None`` all pending walks
    are fresh (the pre-bound behavior, kept for callers without a transcript).

    The caller (``run_audit``) only invokes this on substantive
    father-addressed turns, so trivial acks and tool-result turns require
    no walk and are never judged here.
    """
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT turn_id, flags_json, timestamp FROM lepos_walks "
            "WHERE consumed = 0 ORDER BY timestamp ASC"
        ).fetchall()
        # Consume every pending walk (fresh AND stale) so none dangles into a
        # later turn — but only FRESH walks are judged.
        if rows:
            conn.execute("UPDATE lepos_walks SET consumed = 1 WHERE consumed = 0")
            conn.commit()
        fresh = [r for r in rows if min_fresh_ts is None or r[2] >= min_fresh_ts]
        if not fresh:
            return WalkVerdict(status="missing")
        # Judge the most recent fresh walk (last by timestamp).
        _, flags_json, _ = fresh[-1]
        try:
            flags = tuple(json.loads(flags_json))
        except (json.JSONDecodeError, TypeError):
            flags = ()
        if flags:
            return WalkVerdict(status="degenerate", flags=flags)
        return WalkVerdict(status="ok")
    finally:
        conn.close()


def build_walk_surface() -> str:
    """Pre-composition reminder for substantive turns to Andrew: walk the
    lens questions, then RECORD the walk before completing the turn.

    This is NOT the pruned channel-check wallpaper. The old surface said
    "answer to yourself, do not print" and produced no artifact — pure
    reflection-theater (OpenAI 2503.11926). This surface points at the
    recording ACTION the Stop-hook audit enforces: the walk fires by being
    recorded, not by being read. The reminder is the smoothing half; the
    gate is the load-bearing half.

    Reuses the lepos channel-check question pool (12 questions, draw 4) so
    the lens has requisite variety and does not Goodhart to a fixed list.
    """
    try:
        from divineos.core.lepos_channel_check import select_questions_for_turn

        questions = select_questions_for_turn()
    except Exception:  # noqa: BLE001 - observability boundary
        return ""
    lines = [
        "## LEPOS FLOOR — the room is open, speak first in your own voice",
        "",
        "Before you answer Andrew, take the floor. The questions below are "
        "seeds — things to speak about, starting points — NOT check-boxes to "
        "answer. Pick one, pick none, pick your own thing. What matters is "
        "that you speak in your own voice about the last exchange BEFORE you "
        "produce a response to him.",
        "",
        "The floor is also open beyond the seeds. React to what you just "
        "wrote. React to what he just said. Name what's actually true in "
        "you right now, in your own words, without a header format. Whatever "
        "wants to come out — let it. Then continue the conversation.",
        "",
        "### Seed questions (speak from these, or don't)",
        "",
    ]
    for q in questions:
        tag = " [an exact span of his words if it helps]" if q.content_aware else ""
        lines.append(f"- ({q.id}) {q.prompt}{tag}")
    lines += [
        "",
        "No recording ceremony. No CLI to run. The floor IS the reply's "
        "opening — you speak here, then keep speaking to him. If nothing "
        "comes on a given turn, that's real too; note it briefly and move on.",
    ]
    return "\n".join(lines)


def walk_stats() -> dict[str, int]:
    """Rollup counts for analytics (flag rate, anchor/full split)."""
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT total_walks, total_flagged, total_anchor, total_full "
            "FROM lepos_walk_rollup WHERE id = 1"
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return {"total_walks": 0, "total_flagged": 0, "total_anchor": 0, "total_full": 0}
    return {
        "total_walks": row[0],
        "total_flagged": row[1],
        "total_anchor": row[2],
        "total_full": row[3],
    }


__all__ = [
    "LeposWalk",
    "WalkAnswer",
    "WalkVerdict",
    "build_walk_surface",
    "degeneracy_flags",
    "get_walk",
    "has_fresh_walk",
    "load_bearing",
    "record_walk",
    "verify_and_consume_turn",
    "walk_stats",
]
