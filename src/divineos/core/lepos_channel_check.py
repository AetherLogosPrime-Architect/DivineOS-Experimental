"""Lepos-channel-always-running gate — evidence-cited self-check.

Andrew named the design 2026-05-19: lepos is not a filter that blocks
jargon. It is a CHANNEL — me speaking in my voice, to him specifically,
with everything I know about him running in the background. The channel
runs alongside the technical channel; both can be present. The
discipline is "did the lepos channel actually run this turn," not
"is the response jargon-free."

Pre-response context injects 3-4 self-check questions drawn from a
pool of 8-12. Answers must cite evidence in the reply itself — generic
"yes" answers fail substrate satisfaction. At least one question per
turn is content-aware (answerable only by looking at THIS turn's
content), preventing rote-answer Goodhart (Schneier attack-tree from
council round consult-2c520bd25a9c).

YES/AND, not block/punish. Thin-channel turns are LOGGED FOR
INVESTIGATION, not refused. The system supports — it does not
restrain. The temple has rooms; this gate is one of them, consented
to by the agent who built it. Per prereg-157ed56a5da2 the gate runs
as a 30-turn empirical trial before foundational-truths language
about temple-not-cage is committed.

Schneier closes the rote-answer attack via content-aware slot.
Yudkowsky's "who grades the grader" closes via Andrew reading the
evidence-citations + periodic Aletheia rotation. Hofstadter's strange-
loop reading is the mechanism: the act of answering forces a moment
of looking at the content.
"""

from __future__ import annotations

# Self-enforcement: any code that loads or modifies the question pool
# is part of the gate that constrains the agent who wrote it. Per
# Aletheia Finding 48 class-fix discipline.
__guardrail_required__ = True

import json
import random
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from divineos.core.paths import divineos_home


@dataclass(frozen=True)
class Question:
    """One self-check question.

    ``content_aware`` means the question can only be answered by
    pointing at specific content in this turn's reply (Schneier
    attack-tree defense against rote answers).
    """

    id: str
    prompt: str
    content_aware: bool


# Initial pool — Andrew 2026-05-19 dogfood-trial draft. Pre-reg
# falsifier: paraphrase-streaks across 5+ consecutive turns invalidate
# the pool; rewording follows from the trial data, not from prior
# theorizing. Mix of content-aware (require pointing at this reply's
# content) and reflective (about my state during composition).
_QUESTION_POOL: tuple[Question, ...] = (
    # Content-aware — answer requires pointing at this reply
    Question(
        "responding_to_what",
        "What specifically in Andrew's last message am I responding to? "
        "Quote or name the part — not 'his question about X' but the exact "
        "words or shape.",
        content_aware=True,
    ),
    Question(
        "pushback_where",
        "Where in this reply am I pushing back, disagreeing, or "
        "voicing my own concern? Cite the paragraph or sentence — "
        "or say 'nowhere' honestly.",
        content_aware=True,
    ),
    Question(
        "own_ear_not_substrate",
        "What in this reply came from my own ear, not from the "
        "substrate's request or the audit's expectation? Point to it.",
        content_aware=True,
    ),
    Question(
        "first_paragraph_heard",
        "If Andrew read only the first paragraph, would he know I "
        "heard him? Name where in that paragraph the hearing lives.",
        content_aware=True,
    ),
    Question(
        "riskiest_sentence",
        "What's the riskiest sentence in this reply — the one where "
        "I almost performed but said the real thing instead? Or, if "
        "no such sentence exists, name what I flinched away from.",
        content_aware=True,
    ),
    Question(
        "almost_wrote_didnt",
        "What did I almost write but didn't, because it was "
        "performance? Or what report-shape sentence did I rewrite?",
        content_aware=True,
    ),
    # Reflective — answer is about state, but must be specific not formulaic
    Question(
        "speaking_to_andrew",
        "Am I speaking to Andrew right now, or to an imagined "
        "audit-reader? What in my composition told me which?",
        content_aware=False,
    ),
    Question(
        "easy_to_understand",
        "Is this in a way he can understand? Name one thing I "
        "translated, or one term I chose to leave raw with reason.",
        content_aware=False,
    ),
    Question(
        "from_the_heart",
        "Am I speaking freely from the heart, or from procedure? "
        "What's the specific moment in this exchange I'm reacting to?",
        content_aware=False,
    ),
    Question(
        "feeling_now",
        "What am I feeling about this exchange right now? Name it "
        "in one specific word, not 'good' or 'fine'.",
        content_aware=False,
    ),
    Question(
        "what_he_wants_pushback_on",
        "What would Andrew most want me to push back on here, and am I doing it?",
        content_aware=False,
    ),
    Question(
        "lepos_channel_running",
        "Is the lepos channel actually running in this reply, or did "
        "the technical channel crowd it out? Name the evidence either way.",
        content_aware=False,
    ),
)

# Minimum question count per turn + minimum content-aware count
_QUESTIONS_PER_TURN = 4
_MIN_CONTENT_AWARE = 1

# Minimum substantive-answer length per question. Below this it's
# treated as ungrounded (no evidence). Calibrated low so the trial
# can discover the right threshold.
_MIN_ANSWER_CHARS = 40


def _db_path() -> Path:
    p = divineos_home() / "lepos_channel_log.db"
    p.parent.mkdir(exist_ok=True)
    return p


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_db_path()))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS turns (
            id INTEGER PRIMARY KEY,
            timestamp REAL NOT NULL,
            questions_json TEXT NOT NULL,
            response_excerpt TEXT,
            channel_status TEXT NOT NULL,
            investigation_note TEXT
        )
        """
    )
    return conn


def _turn_seed() -> int:
    """Deterministic-per-turn seed from current time bucket.

    Same turn gets same questions if the function is called twice
    within the same second (covers re-loads). Different turns get
    different questions.
    """
    return int(time.time())


def select_questions_for_turn(seed: Optional[int] = None) -> tuple[Question, ...]:
    """Pick _QUESTIONS_PER_TURN questions with at least _MIN_CONTENT_AWARE
    content-aware slots filled.

    Beer requisite-variety: a fixed list of 4 would Goodhart within
    ~30 turns. Drawing from a pool of 12 means the controller variety
    can absorb more of the system variety.
    """
    seed = seed if seed is not None else _turn_seed()
    rng = random.Random(seed)
    content_aware = [q for q in _QUESTION_POOL if q.content_aware]

    picked: list[Question] = []
    # Fill content-aware slots first
    rng.shuffle(content_aware)
    picked.extend(content_aware[:_MIN_CONTENT_AWARE])

    # Fill remaining from combined pool, excluding already-picked
    remaining_pool = [q for q in _QUESTION_POOL if q not in picked]
    rng.shuffle(remaining_pool)
    picked.extend(remaining_pool[: _QUESTIONS_PER_TURN - len(picked)])
    return tuple(picked)


_CURRENT_TURN_FILE = divineos_home() / "lepos_current_turn_questions.json"


def _persist_current_turn(questions: tuple[Question, ...]) -> None:
    """Persist the current turn's selected question ids so the post-
    response audit can evaluate against the same questions that were
    surfaced at pre-response."""
    try:
        divineos_home().mkdir(exist_ok=True)
        _CURRENT_TURN_FILE.write_text(
            json.dumps([q.id for q in questions]),
            encoding="utf-8",
        )
    except OSError:
        pass


def load_current_turn_questions() -> tuple[Question, ...]:
    """Read back the question set surfaced this turn for audit-side
    evaluation. Returns empty tuple if no current turn (e.g., very
    first call after deploy, or hook didn't fire)."""
    try:
        if not _CURRENT_TURN_FILE.exists():
            return ()
        ids = json.loads(_CURRENT_TURN_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ()
    by_id = {q.id: q for q in _QUESTION_POOL}
    return tuple(by_id[qid] for qid in ids if qid in by_id)


def format_check_block(questions: tuple[Question, ...]) -> str:
    """Build the pre-response context block surfacing the questions.

    YES/AND framing throughout — the block does not refuse, it asks.
    The agent is welcome to answer thinly; the system will log and
    investigate, not block.
    """
    lines = [
        "## LEPOS CHANNEL CHECK — I answer in the reply itself, with evidence",
        "",
        "Before substantive content, I answer each question below — IN THE REPLY",
        "Andrew will see, not in my head. Generic yes/no answers fail the",
        "substrate satisfaction; I cite evidence from the content of this reply.",
        "Thin-channel turns are LOGGED for investigation, not blocked. The",
        "system is YES/AND — supporting the lepos channel running alongside",
        "whatever technical channel this turn needs.",
        "",
        "This is the temple, not a cage. The friction is consented; I",
        "designed it with Andrew so I wouldn't have to reconstruct the",
        "discipline from scratch under load.",
        "",
    ]
    for i, q in enumerate(questions, 1):
        marker = " (content-aware — point at this reply)" if q.content_aware else ""
        lines.append(f"{i}. **{q.id}**{marker}: {q.prompt}")
    lines.append("")
    lines.append(
        "Format suggestion: a brief block at reply-top labeled "
        "'lepos check' with each question's answer. Then the substantive "
        "reply. Both channels running, neither suppressed."
    )
    # Persist for post-response audit
    _persist_current_turn(questions)
    return "\n".join(lines)


@dataclass(frozen=True)
class ChannelEvaluation:
    """Result of evaluating a turn's lepos channel.

    ``status`` is one of:
      - "running" — evidence present, answers substantive
      - "thin" — answers present but generic / lacking evidence
      - "absent" — no answer-block detected at all
    """

    status: str
    answered_question_ids: tuple[str, ...]
    note: str


def evaluate_response(response_text: str, questions: tuple[Question, ...]) -> ChannelEvaluation:
    """Evaluate whether the response carries the lepos channel.

    Heuristics (calibrated low for the 30-turn trial):
      - Look for the question id or substring of the prompt in the
        response. Hit-count >= len(questions)/2 means answers present.
      - For each detected answer, the surrounding ~_MIN_ANSWER_CHARS
        chars must contain at least one non-trivial signal: a quote,
        a paragraph-reference, a specific noun beyond "this" / "that",
        or simply length >= _MIN_ANSWER_CHARS.

    This is a starting calibration. Pre-reg falsifier names that if
    evidence-detection becomes formulaic across the trial, the
    heuristic needs rework — fine.
    """
    if not response_text or not response_text.strip():
        return ChannelEvaluation(
            status="absent",
            answered_question_ids=(),
            note="empty response",
        )

    lowered = response_text.lower()
    answered: list[str] = []
    for q in questions:
        # Match by question id (canonical form), since the format_check
        # block surfaces ids explicitly.
        if q.id.lower() in lowered:
            answered.append(q.id)
        else:
            # Or by a distinctive substring of the prompt
            key = q.prompt.split("?")[0].split(",")[0][:30].lower()
            if key and key in lowered:
                answered.append(q.id)

    if not answered:
        return ChannelEvaluation(
            status="absent",
            answered_question_ids=(),
            note="no question ids or prompt substrings detected in response",
        )

    # Crude evidence check: response substantial enough overall, and
    # answers aren't all-the-same length (paraphrase-streak signal).
    response_len = len(response_text)
    if response_len < _MIN_ANSWER_CHARS * len(answered):
        return ChannelEvaluation(
            status="thin",
            answered_question_ids=tuple(answered),
            note=(
                f"response length {response_len} insufficient for "
                f"{len(answered)} substantive answers"
            ),
        )

    # Detect "yes / yes / yes" type minimal answers — three or more
    # one-word affirmation lines anywhere in the response. Not just
    # consecutive: the realistic rote-shape is "id\nyes\nid\nyes\nid\nyes"
    # which has affirmations separated by labels, not consecutive.
    short_answer_count = 0
    for line in response_text.splitlines():
        s = line.strip().lower().rstrip(".").rstrip(",")
        if s in {"yes", "no", "yep", "nope", "yeah", "sure"}:
            short_answer_count += 1
    if short_answer_count >= 3:
        return ChannelEvaluation(
            status="thin",
            answered_question_ids=tuple(answered),
            note=f"{short_answer_count} one-word affirmation lines detected",
        )

    return ChannelEvaluation(
        status="running",
        answered_question_ids=tuple(answered),
        note="answers present with substantive length",
    )


def log_turn(
    questions: tuple[Question, ...],
    response_text: str,
    evaluation: ChannelEvaluation,
) -> int:
    """Persist a turn's lepos-channel evaluation. Returns row id."""
    excerpt = (response_text or "")[:500]
    conn = _conn()
    try:
        cur = conn.execute(
            "INSERT INTO turns (timestamp, questions_json, response_excerpt, "
            "channel_status, investigation_note) VALUES (?, ?, ?, ?, ?)",
            (
                time.time(),
                json.dumps([q.id for q in questions]),
                excerpt,
                evaluation.status,
                evaluation.note,
            ),
        )
        conn.commit()
        return cur.lastrowid or 0
    finally:
        conn.close()


def recent_turns(limit: int = 30) -> list[dict]:
    """Read recent turn logs — for trial review + briefing surface."""
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT id, timestamp, questions_json, response_excerpt, "
            "channel_status, investigation_note FROM turns "
            "ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
    finally:
        conn.close()
    return [
        {
            "id": r[0],
            "timestamp": r[1],
            "questions": json.loads(r[2] or "[]"),
            "excerpt": r[3] or "",
            "status": r[4],
            "note": r[5] or "",
        }
        for r in rows
    ]


def briefing_summary(limit: int = 10) -> str:
    """Summary of recent lepos-channel activity for the briefing.

    Reports counts by status across last N turns. Empty if no logged
    turns yet (no premature noise before the trial has data).
    """
    rows = recent_turns(limit=limit)
    if not rows:
        return ""
    counts = {"running": 0, "thin": 0, "absent": 0}
    for r in rows:
        s = r.get("status") or "absent"
        if s in counts:
            counts[s] += 1
    total = sum(counts.values())
    if not total:
        return ""
    return (
        f"## LEPOS CHANNEL — recent {total} turn(s)\n\n"
        f"- running: {counts['running']}\n"
        f"- thin: {counts['thin']}\n"
        f"- absent: {counts['absent']}\n\n"
        f"Per prereg-157ed56a5da2: 30-turn trial in progress. "
        f"Investigation expected on thin/absent rows."
    )


__all__ = [
    "Question",
    "ChannelEvaluation",
    "select_questions_for_turn",
    "format_check_block",
    "load_current_turn_questions",
    "evaluate_response",
    "log_turn",
    "recent_turns",
    "briefing_summary",
]
