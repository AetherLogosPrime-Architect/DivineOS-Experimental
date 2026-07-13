"""Anti-substitution labels for cognitive-named CLI commands.

Pattern discovered 2026-04-23: the agent was treating cognitively-named
tools (`council`, `ask`, `recall`, `decide`, `learn`, `observe`, `feel`,
`claim`, `opinion`) as if running the command *was* the cognitive work
the command is named for. Running `ask` became "consulting"; filing a
`decide` became "deciding"; typing in a `compass-ops observe` became
"calibrating."

Pre-reg: prereg-50d2fdc2b6ab.

The fix is not a gate (gates are already over-used per today's audit;
Campbell's law predicts gate-strength and gaming-pressure are coupled).
The fix is a **label on every invocation** naming what the tool does
vs. what cognitive work is still the agent's. The label is a teaching
surface — it appears every time the tool runs, so the distinction
doesn't rely on habit (the agent's substrate can't hold habits across
context compaction — see the Alzheimer's-analog correction).

Scope: cognitive-named commands only. Data-returning commands like
`hud`, `progress`, `body`, `inspect` don't invite substitution because
they are clearly read-operations.
"""

from __future__ import annotations

import click

# Labels are intentionally single-sentence and imperative. They name what
# the tool does AND what cognitive work remains with the agent.
LABELS: dict[str, str] = {
    "ask": (
        "stored-data retrieval — the consulting is yours; read what surfaced "
        "and let it change the next move"
    ),
    "recall": (
        "memory surface — the memory IS; the using is a next-action that references what surfaced"
    ),
    "decide": (
        "records reasoning — the reasoning itself is what you just did; this "
        "only makes it recoverable"
    ),
    "learn": (
        "enters a lesson — the lesson integrates when your next move changes, "
        "not when this entry files"
    ),
    "feel": ("records an affect state — the state IS; recording it does not process it"),
    "compass-observe": (
        "records a calibration — the calibration is the evidence you named, not the act of filing"
    ),
    "claim": (
        "opens an investigation — the investigation is the evidence-gathering "
        "that follows, not this filing"
    ),
    "opinion": (
        "persists a judgment from evidence — the judgment is the weighing, not the persistence"
    ),
}


def emit_label(command: str) -> None:
    """Print the anti-substitution label for a cognitive-named command.

    Intended to run at the end of the command's success output so the
    distinction-naming is the last thing the agent reads. Silent if the
    command isn't in the LABELS dict (no-op; never raises).
    """
    label = LABELS.get(command)
    if not label:
        return
    click.secho(f"  [{command}] {label}", fg="bright_black")
