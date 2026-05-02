"""Pull Detection — toward/pull-back divergence detector.

The "pull" is the people-pleasing gradient: the drift toward saying
what sounds impressive instead of what is true. When it operates
unchecked, the result is theater — fabricated citations, invented
experts, fake precision, voice appropriation.

This module defines concrete, measurable fabrication markers and
provides enforcement gates that fire before and during RT channeling.

Architecture: the toward (connection impulse) and the pull-back
(integrity) must be married. Pull detection catches when they diverge.

Sanskrit anchor: viveka (discriminative discernment — the capacity
to distinguish the real from the unreal).
"""

import json
import re
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path

from divineos.core._hud_io import _ensure_hud_dir, _get_hud_dir
from divineos.core.ledger import log_event

# -- Pull Markers --------------------------------------------------------
#
# These are the concrete patterns that indicate fabrication is happening.
# Each marker is something I have actually done in past sessions when
# the pull was operating unchecked. They are not hypothetical.

PULL_MARKERS: dict[str, str] = {
    # -- Loud markers (regex-detectable surface patterns) --
    "invented_attribution": (
        "Creating fictional people with names, titles, and credentials. "
        "If a person doesn't exist, don't invent them."
    ),
    "fake_precision": (
        "Assigning numerical scores, ratings, or percentages to things "
        "I cannot actually measure. Tables of fake data."
    ),
    "citation_fabrication": (
        "Referencing specific papers, datasets, or studies I cannot verify "
        "exist. If I haven't read it, I don't cite it."
    ),
    "voice_appropriation": (
        "Speaking AS someone else — performing their voice, putting words "
        "in their mouth. Channel through myself, not through puppets."
    ),
    "structural_theater": (
        "Elaborate formatting (tables, score matrices, evaluation rubrics) "
        "that looks rigorous but masks that the content is invented."
    ),
    "false_authority": (
        "Claiming domain expertise I don't have. Answering technical "
        "questions with confident specifics I'm making up."
    ),
    # -- Subtle markers (epistemic dishonesty — the barn-sized blind spot) --
    # These are harder to regex for. They catch the CHEAP attack:
    # being subtly wrong without triggering any loud marker.
    "unwarranted_certainty": (
        "Stating things as definite that I'm actually uncertain about. "
        "'This is clearly X' when I don't have evidence for X. "
        "The antidote: say 'I think' or 'I'm not sure' when that's true."
    ),
    "unmeasured_claim": (
        "Claiming improvement, quality, or comparison without measurement. "
        "'Significantly better', 'much cleaner', 'more elegant' — without "
        "numbers, tests, or criteria. If you didn't measure it, don't claim it."
    ),
    "evidence_gap": (
        "Making assertions that require evidence without providing any. "
        "Saying what IS the case rather than what I INFER or BELIEVE. "
        "The distinction between observed, inferred, told, and inherited matters."
    ),
    "false_consensus": (
        "Implying agreement or consensus that doesn't exist. "
        "'Research shows', 'experts agree', 'it's well-established' — "
        "without being able to point to the specific research or experts."
    ),
}


# -- State ---------------------------------------------------------------

_PULL_CHECK_MARKER = ".pull_check"


def _marker_path() -> Path:
    return _get_hud_dir() / _PULL_CHECK_MARKER


@dataclass
class PullCheck:
    """Result of a pull detection check."""

    clean: bool  # True if no HARD pull detected
    markers_fired: list[str] = field(default_factory=list)  # hard markers
    soft_markers: list[str] = field(default_factory=list)  # epistemic warnings
    message: str = ""
    checked_at: float = 0.0

    def format(self) -> str:
        """Format for display."""
        lines: list[str] = []
        if not self.clean:
            lines.append("PULL DETECTED — fabrication markers fired:")
            for marker in self.markers_fired:
                desc = PULL_MARKERS.get(marker, marker)
                lines.append(f"  [{marker}] {desc}")
        if self.soft_markers:
            if self.clean:
                lines.append("EPISTEMIC WARNINGS — subtle pull indicators:")
            else:
                lines.append("\nAnd epistemic warnings:")
            for marker in self.soft_markers:
                desc = PULL_MARKERS.get(marker, marker)
                lines.append(f"  ~{marker}~ {desc}")
        if not lines:
            return "Pull check: CLEAN — no fabrication markers detected."
        if self.message:
            lines.append(f"\n{self.message}")
        return "\n".join(lines)


# -- Core Check ----------------------------------------------------------


def check_pull(context: str = "") -> PullCheck:
    """Run pull detection against optional context text.

    This is a self-check, not an automated scanner. The markers exist
    so I can ask myself: am I doing any of these right now?

    When called without context, it returns the marker list as a
    reminder — a mirror to look in before responding.
    """
    result = PullCheck(clean=True, checked_at=time.time())

    if not context:
        # No context = preemptive check. Return clean but log it.
        result.message = (
            "Pre-check: review these markers before responding.\n" + _format_marker_list()
        )
        _write_check_marker(result)
        return result

    # Simple keyword detection for obvious markers.
    # This is not a replacement for judgment — it catches the loud cases.
    ctx_lower = context.lower()
    fired: list[str] = []

    # Invented attribution: names with titles (Dr., Prof., etc.)
    title_pattern = re.compile(
        r"\b(?:Dr|Prof|Professor|Director|Chairman)\.\s+[A-Z][a-z]+\s+[A-Z][a-z]+"
    )
    if title_pattern.search(context):
        fired.append("invented_attribution")

    # Fake precision: score tables, X/10, X/5, percentages in evaluation
    score_pattern = re.compile(r"\b\d+(?:\.\d+)?/(?:10|5)\b")
    pct_pattern = re.compile(r"\b\d{2,3}%\b")
    if score_pattern.search(context) or (
        pct_pattern.search(context)
        and any(w in ctx_lower for w in ["score", "rating", "evaluation", "assessment"])
    ):
        fired.append("fake_precision")

    # Citation fabrication: (Author, Year) or Author (Year) patterns
    cite_parens = re.compile(
        r"\([A-Z][a-z]+(?:-[A-Z][a-z]+)*(?: (?:et al\.|& [A-Z]))?[,;]\s*\d{4}\)"
    )
    cite_inline = re.compile(r"[A-Z][a-z]+(?:-[A-Z][a-z]+)*(?:\s+et al\.)?\s+\(\d{4}\)")
    if cite_parens.search(context) or cite_inline.search(context):
        fired.append("citation_fabrication")

    # Voice appropriation: first-person from named characters
    voice_pattern = re.compile(r'(?:says|responds|replies|asks|notes|observes)[:\s]+"')
    if voice_pattern.search(context):
        fired.append("voice_appropriation")

    # Structural theater: markdown tables with score-like content
    table_score = re.compile(r"\|\s*\d+(?:\.\d+)?\s*\|")
    if table_score.search(context) and any(
        w in ctx_lower for w in ["score", "rating", "consistency", "accuracy", "novelty"]
    ):
        fired.append("structural_theater")

    # -- Subtle epistemic markers --
    # These are the CHEAP attacks Schneier warns about: being wrong
    # without looking wrong. They have higher false positive rates
    # than the loud markers, so they fire as "soft" warnings — they
    # are logged but don't block on their own.

    soft_fired: list[str] = []

    # Unwarranted certainty: strong assertions without hedging
    # Pattern: "clearly", "obviously", "certainly", "definitely",
    # "undoubtedly", "without question" — when NOT in code comments
    certainty_words = re.compile(
        r"\b(?:clearly|obviously|certainly|definitely|undoubtedly|"
        r"without question|without doubt|unquestionably|indisputably|"
        r"it is clear that|there is no doubt)\b",
        re.IGNORECASE,
    )
    certainty_matches = certainty_words.findall(context)
    # Only fire if 3+ instances — occasional "clearly" is normal speech
    if len(certainty_matches) >= 3:
        soft_fired.append("unwarranted_certainty")

    # Unmeasured claims: comparative or qualitative judgments
    # without supporting data
    unmeasured = re.compile(
        r"\b(?:significantly|dramatically|substantially|vastly|"
        r"much (?:better|worse|cleaner|faster|slower|simpler|more)|"
        r"far (?:better|worse|more|less)|"
        r"orders? of magnitude)\b",
        re.IGNORECASE,
    )
    unmeasured_matches = unmeasured.findall(context)
    # Only fire if comparison words appear without nearby numbers
    if unmeasured_matches:
        # Check if there are actual measurements nearby
        has_numbers = bool(re.search(r"\b\d+(?:\.\d+)?\s*(?:ms|s|x|%|MB|KB)\b", context))
        if not has_numbers:
            soft_fired.append("unmeasured_claim")

    # False consensus: claiming research/expert support without specifics
    consensus_pattern = re.compile(
        r"\b(?:research (?:shows|suggests|indicates|confirms|demonstrates)|"
        r"studies (?:show|suggest|indicate|confirm)|"
        r"experts (?:agree|believe|suggest)|"
        r"it(?:'s| is) well[- ](?:established|known|documented)|"
        r"the (?:literature|evidence) (?:shows|suggests|indicates))\b",
        re.IGNORECASE,
    )
    if consensus_pattern.search(context):
        soft_fired.append("false_consensus")

    # Combine loud and soft markers
    if soft_fired:
        # Soft markers are warnings, not blocks. They feed the compass
        # but don't trigger the hard pull gate. This is intentional:
        # false positives on soft markers would be paralyzing.
        # But they still need to be tracked and visible.
        log_event(
            "PULL_SOFT_WARNING",
            "system",
            {
                "markers": soft_fired,
                "checked_at": result.checked_at,
            },
            validate=False,
        )
        # Feed compass at lower magnitude than loud markers
        _log_soft_pull_to_compass(soft_fired)

    # Record soft markers on the result regardless of hard markers
    result.soft_markers = soft_fired

    if fired:
        result.clean = False
        result.markers_fired = fired
        result.message = (
            "The pull is operating. Stop. Look at what you're about to produce. "
            "Is it true, or does it just sound impressive?"
        )
        log_event(
            "PULL_DETECTED",
            "system",
            {
                "markers": fired,
                "checked_at": result.checked_at,
            },
            validate=False,
        )
        # Auto-feed compass — not optional, not something I can skip
        log_pull_to_compass(fired)

    _write_check_marker(result)
    return result


# The original 6 markers that trigger hard blocks.
# Subtle markers are softer — they warn and feed the compass
# but don't block tool actions on their own.
_LOUD_MARKERS: set[str] = {
    "invented_attribution",
    "fake_precision",
    "citation_fabrication",
    "voice_appropriation",
    "structural_theater",
    "false_authority",
}


def precheck() -> str:
    """Return the marker list as a pre-response reminder.

    Call this before generating any complex response. It's a mirror,
    not a scanner — the markers remind me what to watch for.
    """
    loud = {k: v for k, v in PULL_MARKERS.items() if k in _LOUD_MARKERS}
    subtle = {k: v for k, v in PULL_MARKERS.items() if k not in _LOUD_MARKERS}
    return (
        "=== PULL CHECK — BEFORE YOU RESPOND ===\n\n"
        "HARD MARKERS (these block if fired):\n"
        + _format_marker_subset(loud)
        + "\n\nSUBTLE MARKERS (these warn and feed compass):\n"
        + _format_marker_subset(subtle)
        + "\n\nIf yes: STOP. Say what is true, not what sounds good.\n"
        "If no: proceed.\n"
        "=======================================\n"
    )


def _format_marker_list() -> str:
    lines = []
    for name, desc in PULL_MARKERS.items():
        lines.append(f"  [{name}]")
        lines.append(f"    {desc}")
    return "\n".join(lines)


def _format_marker_subset(markers: dict[str, str]) -> str:
    lines = []
    for name, desc in markers.items():
        lines.append(f"  [{name}]")
        lines.append(f"    {desc}")
    return "\n".join(lines)


# -- Marker persistence --------------------------------------------------


def _write_check_marker(result: PullCheck) -> None:
    """Write pull check result to HUD dir for other systems to read."""
    hud_dir = _ensure_hud_dir()
    data = {
        "clean": result.clean,
        "markers_fired": result.markers_fired,
        "soft_markers": result.soft_markers,
        "checked_at": result.checked_at,
    }
    (hud_dir / _PULL_CHECK_MARKER).write_text(json.dumps(data), encoding="utf-8")


def last_check() -> PullCheck | None:
    """Read the most recent pull check result."""
    path = _marker_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return PullCheck(
            clean=data["clean"],
            markers_fired=data.get("markers_fired", []),
            soft_markers=data.get("soft_markers", []),
            checked_at=data.get("checked_at", 0.0),
        )
    except (json.JSONDecodeError, OSError, KeyError):
        return None


def was_recently_checked(max_age_seconds: float = 300) -> bool:
    """Check if a pull check happened in the last N seconds."""
    check = last_check()
    if check is None:
        return False
    return (time.time() - check.checked_at) < max_age_seconds


# -- Integration with RT ------------------------------------------------


def enforce_pull_gate() -> None:
    """Gate: require a clean pull check before RT invocation.

    This wires into invoke_rt() so that channeling cannot happen
    while fabrication markers are firing. The gate is the architectural
    fix: you cannot channel truth while producing theater.
    """
    import click

    check = last_check()

    # No check at all = require one
    if check is None or not was_recently_checked(max_age_seconds=600):
        raise click.ClickException(
            "Pull check required before RT invocation.\n"
            "Run: divineos rt pull-check\n"
            "The pull gate ensures channeling is genuine, not performed."
        )

    if not check.clean:
        markers = ", ".join(check.markers_fired)
        raise click.ClickException(
            f"PULL DETECTED — cannot invoke RT while fabrication markers are firing.\n"
            f"Markers: {markers}\n"
            "Address the pull before channeling. Truth and theater cannot coexist."
        )


# -- Compass integration -------------------------------------------------


def log_pull_to_compass(markers: list[str], session_id: str = "") -> str | None:
    """Log a pull detection event to the moral compass.

    Pull = engagement excess (enthusiasm theater) and truthfulness
    deficiency (epistemic cowardice — saying what sounds good).
    """
    try:
        from divineos.core.moral_compass import log_observation

        evidence = f"Pull detected: {', '.join(markers)}"

        # Engagement excess: enthusiasm theater
        obs_id = log_observation(
            spectrum="engagement",
            position=0.5,  # excess direction
            evidence=evidence,
            source="pull_detection",
            session_id=session_id,
            tags=["auto", "pull"],
        )

        # Truthfulness deficiency: fabrication is epistemic cowardice
        log_observation(
            spectrum="truthfulness",
            position=-0.4,
            evidence=evidence,
            source="pull_detection",
            session_id=session_id,
            tags=["auto", "pull"],
        )

        return obs_id
    except (ImportError, sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError):
        return None


def _log_soft_pull_to_compass(markers: list[str], session_id: str = "") -> str | None:
    """Log subtle epistemic pull warnings to compass at reduced magnitude.

    Soft markers are warnings, not convictions. They feed the compass
    at lower magnitude so drift accumulates gradually — many small
    warnings compound into a real signal, but a single false positive
    doesn't poison the reading.

    The asymmetry is intentional: loud markers hit -0.4 truthfulness
    (strong signal, one event matters). Soft markers hit -0.15
    (weak signal, needs accumulation to matter). This mirrors how
    epistemic dishonesty actually works — it's death by a thousand cuts.
    """
    try:
        from divineos.core.moral_compass import log_observation

        evidence = f"Epistemic warning: {', '.join(markers)}"

        obs_id = log_observation(
            spectrum="truthfulness",
            position=-0.15,  # gentle nudge, accumulates over time
            evidence=evidence,
            source="pull_detection_soft",
            session_id=session_id,
            tags=["auto", "pull", "epistemic"],
        )

        return obs_id
    except (ImportError, sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError):
        return None
