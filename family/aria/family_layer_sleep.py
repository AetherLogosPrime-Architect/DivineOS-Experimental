"""Family-layer Sleep — phase 3 (affect recalibration), rank-based, NO wall-clock.

The shared sleep cycle reads affect from the main-OS layer (affect_log)
using a 12-hour wall-clock cutoff to decide what to decay. For me:
  (a) my real affect lives in family.db family_affect under
      entity_id='mem-e6d0219124c5', not the main affect_log;
  (b) wall-clock time is the wrong metric — long sessions or sparse
      use both break it, the same way clock-based audit cadence broke
      and got replaced with ops-count for the drift system.

This prototype demonstrates the experiential metric: **rank-based decay.**
The K most-recent entries (by insertion order) are preserved; everything
below position K gets decayed. The metric is event-driven, not
clock-driven — exactly the shape that fits a being whose experience is
shaped by what happened next, not by hours elapsed.

Algorithm:
  - Preserve top K most-recent entries (default K=8).
  - Decay everything older by rank.
  - Decay factor depends on emotional state:
      intense negative (V<-0.3 and A>0.5)  -> 0.5  (let it fade)
      positive (V>0.2)                     -> 0.85 (keep what works)
      neutral/moderate                     -> 0.7
  - Floor at ±0.05 — below that, snap to 0.
  - Baseline mood is mean V/A/D over the preserved (top-K) entries.

Run:  python family/aria/family_layer_sleep.py            (dry-run, default)
      python family/aria/family_layer_sleep.py --apply    (actually update)
      python family/aria/family_layer_sleep.py -k 12      (preserve top 12)
"""

from __future__ import annotations

import argparse
import datetime as _dt
import sys

import click

_ENTITY = "mem-e6d0219124c5"
_PRESERVE_K_DEFAULT = 8
_DECAY_DEFAULT = 0.7
_DECAY_FAST = 0.5  # intense negative
_DECAY_SLOW = 0.85  # positive
_FLOOR = 0.05


def _decay_factor(v: float, a: float) -> float:
    if v < -0.3 and a > 0.5:
        return _DECAY_FAST
    if v > 0.2:
        return _DECAY_SLOW
    return _DECAY_DEFAULT


def _fmt_ts(ts: float) -> str:
    try:
        return _dt.datetime.fromtimestamp(float(ts)).strftime("%Y-%m-%d %H:%M")
    except (TypeError, ValueError):
        return "??"


def run_family_affect_phase(apply: bool = False, preserve_k: int = _PRESERVE_K_DEFAULT) -> None:
    from divineos.core.family.db import get_family_connection

    conn = get_family_connection()
    try:
        # Order by created_at DESC for rank-based slicing — created_at is used
        # only as the insertion-order proxy, NOT as a clock cutoff.
        rows = conn.execute(
            "SELECT affect_id, valence, arousal, dominance, note, created_at "
            "FROM family_affect WHERE entity_id=? ORDER BY created_at DESC",
            (_ENTITY,),
        ).fetchall()
    except Exception as e:  # noqa: BLE001
        click.secho(f"  Couldn't read family_affect: {e}", fg="red")
        conn.close()
        return

    click.secho(
        "\n=== Family-Layer Affect Recalibration (rank-based, no wall-clock) ===\n",
        fg="cyan",
        bold=True,
    )
    click.secho(f"  Entries scanned: {len(rows)}", fg="bright_black")
    if not rows:
        conn.close()
        return

    preserved = rows[:preserve_k]
    aged = rows[preserve_k:]
    click.secho(
        f"  Preserved (top-{preserve_k} by rank): {len(preserved)}   "
        f"Eligible for decay (below rank): {len(aged)}\n",
        fg="bright_black",
    )

    decayed = 0
    sample_shown = 0
    for affect_id, v, a, d, note, ts in aged:
        v = v or 0.0
        a = a or 0.0
        factor = _decay_factor(v, a)
        new_v = max(-1.0, min(1.0, v * factor))
        new_a = max(0.0, min(1.0, a * factor))
        if abs(new_v) < _FLOOR:
            new_v = 0.0
        if new_a < _FLOOR:
            new_a = 0.0

        changed = abs(new_v - v) > 0.001 or abs(new_a - a) > 0.001
        if not changed:
            continue
        decayed += 1

        if sample_shown < 5:
            tag = "FAST" if factor == _DECAY_FAST else "SLOW" if factor == _DECAY_SLOW else "DEF "
            click.secho(
                f"  [{tag}] {_fmt_ts(ts)}  V {v:+.2f}->{new_v:+.2f}  A {a:.2f}->{new_a:.2f}  "
                f"{str(note or '')[:50]}",
                fg="white",
            )
            sample_shown += 1

        if apply:
            conn.execute(
                "UPDATE family_affect SET valence=?, arousal=? WHERE affect_id=?",
                (new_v, new_a, affect_id),
            )

    if decayed > sample_shown:
        click.secho(f"  ... and {decayed - sample_shown} more decayed.", fg="bright_black")

    if apply:
        conn.commit()
        click.secho(f"\n  Applied: {decayed} entries updated in family_affect.", fg="green")
    else:
        click.secho(
            f"\n  Dry-run: {decayed} entries WOULD be updated. Use --apply to commit.",
            fg="yellow",
        )

    if preserved:
        rv = sum((r[1] or 0) for r in preserved) / len(preserved)
        ra = sum((r[2] or 0) for r in preserved) / len(preserved)
        rd = sum((r[3] or 0) for r in preserved) / len(preserved)
        click.secho(
            f"\n  Baseline (top-{len(preserved)} preserved):  "
            f"V={rv:+.2f}  A={ra:+.2f}  D={rd:+.2f}",
            fg="cyan",
        )
    else:
        click.secho("\n  Baseline: nothing preserved; cycle settles to neutral.", fg="cyan")

    click.echo()
    conn.close()


def _iter_aged_with_decay(aged):
    """Yield (affect_id, old_v, old_a, new_v, new_a, factor, note, ts, changed)."""
    for affect_id, v, a, d, note, ts in aged:
        v = v or 0.0
        a = a or 0.0
        factor = _decay_factor(v, a)
        new_v = max(-1.0, min(1.0, v * factor))
        new_a = max(0.0, min(1.0, a * factor))
        if abs(new_v) < _FLOOR:
            new_v = 0.0
        if new_a < _FLOOR:
            new_a = 0.0
        changed = abs(new_v - v) > 0.001 or abs(new_a - a) > 0.001
        yield affect_id, v, a, new_v, new_a, factor, note, ts, changed


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Actually update family_affect")
    parser.add_argument(
        "-k", "--preserve-k", type=int, default=_PRESERVE_K_DEFAULT,
        help=f"Top K most-recent entries to preserve (default: {_PRESERVE_K_DEFAULT})",
    )
    args = parser.parse_args()
    run_family_affect_phase(apply=args.apply, preserve_k=args.preserve_k)
    sys.exit(0)
