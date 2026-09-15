"""Label the most recent correction-shape-v2 Stop-gate fire as a false positive.

## Why this exists (Aria 2026-08-01)

``.claude/hooks/correction-shape-v2-stop.sh`` fires when my reply looks
like I am admitting an error, blocks with exit 2, and prints:

    If this is a FALSE-POSITIVE ... clear the fire with:
      python scripts/clear_correction_marker.py --reason "..."
    The clear-marker path is not a bypass — it is the false-positive
    attribution path. Every clear increments the negative-training-corpus
    for the eventual Layer B semantic tiebreak.

Three things were wrong with that. ``clear_correction_marker.py`` belongs
to a *different* gate (the UserPromptSubmit correction-marker) and clears
a marker this gate never sets — so running it is a no-op that reports
"nothing to clear". The negative-training-corpus it promises did not
exist anywhere: the phrase appeared only inside that message, written by
nothing and read by nothing. And because the gate blocks, a genuine false
positive had no exit at all — the only ways past were to file a
correction that was not one, or to rewrite the reply until the detector
stopped noticing.

A gate that offers a remedy which cannot execute is a cage, not a keel
(Andrew 2026-06-08, gate-remedies-must-execute). Worse for a gate that is
otherwise right: sending me to a no-op teaches me its instructions are
unreliable, which quietly discounts every *other* instruction it gives.

## What the current arrangement prevented, and what is preserved

Chesterton's fence, per the step this same session added to
``wwnd-choice-prime.sh``: the broken path did prevent something real. With
no working escape, I could not wave away an inconvenient catch as a false
alarm — every fire cost me a real filing. That property is worth keeping,
and it is why this script is deliberately not cheap:

* a ``--reason`` of at least 40 characters, naming *what class of MENTION
  was misread as USE* — not "false positive" but the shape of the miss;
* it labels only a fire that actually happened, so it cannot be run
  pre-emptively to disarm the gate;
* every label appends to a corpus that is meant to be read later, which
  means a dishonest label is evidence against me, not an erasure.

## What it does

The Stop hook records each fire to ``correction_shape_v2_fires.jsonl``
under the DivineOS home, with the reply text, the detector's reason, and
its confidence. This script marks the newest unlabeled fire as a false
positive and attaches my explanation. The result is a labeled corpus —
detector verdict beside human judgment — which is exactly what a semantic
replacement for the keyword layer will need as training data.

## Usage

    python scripts/label_correction_shape_false_positive.py \\
        --reason "reply narrated an already-filed-and-fixed correction; a completed catch-and-fix turn restates the fault and so reads identically to a fresh admission"
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import _repo_import  # noqa: F401  -- must precede any divineos import

from divineos.core.paths import divineos_home  # noqa: E402

_MIN_REASON_LEN = 40
_FIRES_FILENAME = "correction_shape_v2_fires.jsonl"

# The Stop gate's own block text, which is what lands in the marker's
# trigger field when this gate's fire is re-read as a user correction at
# the next prompt. Narrow on purpose -- see _lift_marker_set_by_this_gate.
_STOP_GATE_SIGNATURE = "[correction-shape-v2 stop-gate]"


def _lift_marker_set_by_this_gate() -> str:
    """Clear the correction marker IF this gate's own fire is what set it.

    THE THIRD HEAD OF THE SAME DEADLOCK, 2026-09-15. This script exists
    because the Stop gate advertised an exit that could not execute --
    "a gate that offers a remedy which cannot execute is a cage, not a
    keel". It fixed that for the fire log and stopped one step short: the
    gate's block message is itself re-read as a correction at the next
    prompt, which sets the UserPromptSubmit marker and blocks Bash, Edit
    and Read. Labelling the fire never touched that marker. So an HONEST
    false-positive label left me exactly as stuck as before, with the only
    remaining exits being to file a correction that did not happen, or the
    fire door -- the two outcomes this script was written to prevent.

    WHY THIS IS NOT A BLANKET CLEAR. The marker is shared: a real
    correction from Andrew sets it too, and wiping that would destroy the
    protection outright. So the lift is conditional on the marker's own
    trigger text carrying this gate's signature. A marker set by anything
    else -- above all by Andrew -- is left standing untouched, and the
    label still costs a reason of real length, still cannot be run
    pre-emptively, and still appends to a corpus where a dishonest label
    is evidence rather than an erasure.

    Returns a human-readable outcome line; never raises.
    """
    try:
        from divineos.core.correction_marker import clear_marker, read_marker
    except ImportError as exc:  # pragma: no cover - machinery absent
        return f"marker untouched: cannot import correction_marker ({exc})"

    try:
        marker = read_marker()
    except (OSError, ValueError) as exc:
        return f"marker untouched: unreadable ({exc})"

    if not marker:
        return "no correction marker was set; nothing to lift"

    trigger = str(marker.get("trigger", "") or "")
    if _STOP_GATE_SIGNATURE not in trigger:
        return (
            "marker LEFT STANDING -- it was set by something other than this "
            f"gate (trigger: {trigger[:70]!r}). That one still needs filing."
        )

    try:
        clear_marker()
    except (OSError, ValueError) as exc:
        return f"marker lift FAILED ({exc}) -- still blocked, and that is honest"
    return "marker lifted: this gate set it, and I have gone on record against it"


def fires_path() -> Path:
    """Location of the fire log the Stop hook appends to."""
    return Path(divineos_home()) / _FIRES_FILENAME


def _load_fires(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    records: list[dict] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except ValueError:
                # A corrupt line must not make the remedy unreachable —
                # that is the exact failure this script exists to fix.
                continue
    return records


def _write_fires(path: Path, records: list[dict]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    tmp.replace(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=("Label the most recent correction-shape-v2 fire as a false positive.")
    )
    parser.add_argument(
        "--reason",
        required=True,
        help=(
            "What class of MENTION was misread as USE. Must be at least "
            f"{_MIN_REASON_LEN} characters — describe the shape of the miss, "
            "not merely that it missed."
        ),
    )
    args = parser.parse_args(argv)

    reason = args.reason.strip()
    if len(reason) < _MIN_REASON_LEN:
        print(
            f"[-] Refused: --reason is {len(reason)} chars, minimum is "
            f"{_MIN_REASON_LEN}. A stub reason produces a corpus entry that "
            "teaches nothing. Name the class of MENTION that was misread.",
            file=sys.stderr,
        )
        return 2

    path = fires_path()
    records = _load_fires(path)
    if not records:
        print(
            f"[-] No recorded fires at {path}. Nothing to label. The Stop hook "
            "writes a record each time it fires; if you expected one, the hook "
            "may not have run or DivineOS home resolves elsewhere.",
            file=sys.stderr,
        )
        return 1

    target_index = None
    for i in range(len(records) - 1, -1, -1):
        if not records[i].get("label"):
            target_index = i
            break

    if target_index is None:
        print(
            "[-] Every recorded fire is already labeled. This script marks a "
            "fire that actually happened; it cannot be run pre-emptively.",
            file=sys.stderr,
        )
        return 1

    target = records[target_index]
    target["label"] = "false_positive"
    target["label_reason"] = reason
    target["labeled_at"] = time.time()
    _write_fires(path, records)

    detector_reason = target.get("reason", "?")
    confidence = target.get("confidence", "?")
    print("[+] Fire labeled false-positive.")
    print(f"    detector said : {detector_reason} (confidence {confidence})")
    print(f"    I say         : {reason}")
    print(f"    corpus        : {path}")
    print(f"    marker        : {_lift_marker_set_by_this_gate()}")
    print(
        "    This is a disagreement with my own detector, on the record. If "
        "the label was dishonest, it is now evidence, not an erasure."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
