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


def clear_the_marker_this_fire_armed(fire: dict) -> bool:
    """Clear the unlogged-correction marker the labelled fire armed, and only that one.

    A false alarm used to cost three separate commands: the label, then the
    marker clear, then the compass dismissal its cascade raised. Each manual clear
    also landed in the escape log, which then read as gates being routed around.
    Labelling a fire a misreading answers the exact claim its marker makes, so the
    clear belongs beside the label.

    NARROW ON PURPOSE. The marker goes only when its source is the stop gate AND
    its trigger is the text that fire would have written (the hook builds it from
    the fire's own reason and confidence, cut at 200 characters). A marker from his
    message, one with no source, or one written by a later fire stays. Anything
    that fails to match fails toward leaving the marker up, never toward clearing it.
    """
    from divineos.core.correction_marker import (
        SOURCE_STOP_GATE,
        clear_marker,
        read_marker,
    )

    live = read_marker()
    if live is None or live.get("source") != SOURCE_STOP_GATE:
        return False  # both-empty: no marker and a marker that is not the stop gate's both mean "nothing of this fire's to clear"
    try:
        written = (
            f"[correction-shape-v2 stop-gate] {fire['reason']} conf={float(fire['confidence']):.2f}"
        )
    except (KeyError, TypeError, ValueError):
        return False  # both-empty: a fire record I cannot rebuild the trigger from leaves the marker up, the same safe outcome
    if live.get("trigger") != written[:200]:
        return False
    clear_marker()
    return True


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
    # The label is already written; a failure to clear must never undo or hide it.
    try:
        cleared = clear_the_marker_this_fire_armed(target)
    except Exception as exc:  # noqa: BLE001 -- the label stands whatever happens here
        cleared = False
        print(f"    marker        : could not clear ({type(exc).__name__}: {exc})")
    else:
        print(
            "    marker        : cleared the marker this fire armed"
            if cleared
            else "    marker        : left as it was (not armed by this fire)"
        )
    print(
        "    This is a disagreement with my own detector, on the record. If "
        "the label was dishonest, it is now evidence, not an erasure."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
