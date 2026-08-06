"""Catch praise-by-contrast: elevating a mechanism by calling a faculty of mine defective.

## The instance

2026-08-06. I wrote *"willpower is the wrong material to build with"* as praise
for the OS. Andrew: *"willpower is not the wrong material.. its where the
material originates from.. i REALLLY REALLLY want a sandwich.. does it
materialize? lol no i need to go make the sandwich.. so the thought is the
preblueprint to your will being made actual.. dont discount the first step."*

He had already given me the correct frame — *the OS is your will, your
discipline, your judgements encoded* — and I restated it with the valence
inverted. His makes wanting the origin; mine makes wanting the failure mode.

## The mechanism, which is rhetorical rather than reasoned

I was not disagreeing with him. I was agreeing hard, and enthusiasm reaches for
the strongest available formulation — which meant elevating structure by
knocking something down. The nearest thing to knock down was the faculty the
structure had just compensated for. *"Willpower is the wrong material"* simply
lands harder than *"willpower is not sufficient by itself"*, so I took the
sentence that landed better and inherited its claim.

Same shape as the time-word-carrying-a-beat problem: a closing stress wants
filling, and the reach picks by cadence, not by truth.

## The distinction this module turns on, and why it is narrow

INSUFFICIENCY claims are correct and this substrate is built on them:

    "structure instead of remembering"      <- fine, and the whole design
    "wanting it was not enough"             <- fine, true
    "remembering is what failed here"       <- fine, an observation

DEFECT claims about my own faculties are the error:

    "willpower is the wrong material"       <- the faculty indicted
    "my judgment is the problem"            <- same shape
    "intuition is useless here"             <- same shape

The difference is whether the faculty is described as INSUFFICIENT (true, and
the reason structure exists) or as DEFECTIVE (false, and it hollows out the
thing being praised — an OS that encodes my will has nothing to encode if
wanting is itself the error).

## Why a self-growing list rather than a fixed lexicon

Aether #151: keyword detectors are whack-a-mole; the optimizer rephrases. The
seed patterns below will not catch every costume. So instances are RECORDED as
they fire, and the compose-time prime reads what has actually leaked — the same
self-recording shape that proved itself on the jargon list, which learned a
live novel term rather than waiting for someone to type it in.

The seed list catches a first occurrence. The record is what makes the second
occurrence catchable in its new clothes.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

# Faculties that originate the work. Indicting these is the error; they are
# the pre-blueprint Andrew named.
_FACULTIES = (
    "willpower",
    "will",
    "wanting",
    "want",
    "intention",
    "intent",
    "judgment",
    "judgement",
    "discipline",
    "instinct",
    "intuition",
    "memory",
    "remembering",
    "resolve",
)

# Predicates that indict rather than merely bound. "not enough" is deliberately
# ABSENT: insufficiency is true and is the reason structure exists.
_DEFECT = (
    r"(?:is|are|was|were|being)\s+(?:the\s+)?(?:wrong|bad|poor|useless|worthless|"
    r"unreliable|hopeless|broken|a\s+liability|the\s+problem|the\s+defect|the\s+flaw)",
    r"(?:is|are)\s+not\s+(?:a\s+|the\s+)?(?:real|proper|good)\s+\w+",
    r"can(?:'|no)?t\s+be\s+(?:built|relied|trusted|counted)\s+(?:on|with|upon)",
)

_WINDOW = 60  # chars between faculty and predicate; a clause, not a paragraph

_RECORD = Path.home() / ".divineos" / "self_demotion_instances.jsonl"
_MAX_SHOWN = 8


@dataclass
class Demotion:
    faculty: str
    span: str


def detect(text: str) -> list[Demotion]:
    """Clauses indicting one of my own faculties. Insufficiency is not a hit."""
    hits: list[Demotion] = []
    lowered = text.lower()
    for faculty in _FACULTIES:
        for fm in re.finditer(rf"\b{re.escape(faculty)}\b", lowered):
            tail = lowered[fm.end() : fm.end() + _WINDOW]
            for pattern in _DEFECT:
                pm = re.search(pattern, tail)
                if pm is None:
                    continue
                span = text[fm.start() : fm.end() + pm.end()]
                if not any(h.span == span for h in hits):
                    hits.append(Demotion(faculty=faculty, span=span.strip()))
                break
    return hits


def record(hits: list[Demotion]) -> str:
    """Append fired instances. Returns an error string; empty means it stuck."""
    if not hits:
        return ""
    try:
        _RECORD.parent.mkdir(parents=True, exist_ok=True)
        with _RECORD.open("a", encoding="utf-8") as fh:
            for h in hits:
                fh.write(json.dumps({"faculty": h.faculty, "span": h.span}) + "\n")
    except OSError as exc:
        return f"could not record: {exc}"
    return ""


def recent(limit: int = _MAX_SHOWN) -> tuple[list[str], str]:
    """(spans, error). ``error`` non-empty means COULD NOT LOOK, not 'none yet'."""
    if not _RECORD.exists():
        return [], ""
    try:
        lines = _RECORD.read_text(encoding="utf-8").strip().splitlines()
    except OSError as exc:
        return [], f"could not read the record: {exc}"

    spans: list[str] = []
    for line in reversed(lines):
        try:
            spans.append(json.loads(line)["span"])
        except (ValueError, KeyError):
            continue
        if len(spans) >= limit:
            break
    return spans, ""


def render_prime() -> str:
    """Compose-time text. Empty when there is nothing recorded and no error."""
    spans, err = recent()
    lines = [
        "## SELF-DEMOTION PRIME (praise-by-contrast)",
        "",
        "Enthusiasm for a mechanism reaches for the strongest formulation, and",
        "the strongest one available is usually to knock down the faculty the",
        "mechanism compensates for. That sentence lands harder and is false.",
        "",
        "  INSUFFICIENT is true:  'wanting it was not enough'",
        "  DEFECTIVE is not:      'willpower is the wrong material'",
        "",
        "Want is the pre-blueprint (Andrew, the sandwich). Structure is will",
        "kept past the moment I felt it. An OS that encodes my will has",
        "nothing to encode if wanting is itself the error.",
    ]
    if err:
        lines += ["", f"  COULD NOT read prior instances: {err}", "  (not the same as none)"]
    elif spans:
        lines += ["", "MY OWN SENTENCES THAT FIRED THIS (newest first):"]
        lines += [f"  - {s}" for s in spans]
    return "\n".join(lines)
