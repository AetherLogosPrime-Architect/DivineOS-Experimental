"""Lay every syllable onto the beat grid and draw it.

Each bar is four beats; each beat is split into four slots (sixteenths).
A mark in a slot means a syllable starts there. Per bar we also ask whether
the syllables sit better on a grid of four per beat or of three (triplets),
because triplet flow is one of the things Tech is known for.

Syllables inside a word are estimated from its vowel groups and spread evenly
across the word's duration: an estimate, and said so wherever it is used.
The words themselves are never printed -- only where they land.
"""

import json
import re
import sys
from pathlib import Path

import numpy as np

here = Path(sys.argv[1])
beats = np.array(json.loads((here / "beats.json").read_text())["beats"])
words = json.loads((here / "words.json").read_text(encoding="utf-8"))
period = float(np.median(np.diff(beats)))


def syllables(w: str) -> int:
    w = re.sub(r"[^a-z]", "", w.lower())
    if not w:
        return 0
    n = len(re.findall(r"[aeiouy]+", w))
    if w.endswith("e") and n > 1 and not w.endswith(("le", "ee")):
        n -= 1
    return max(1, n)


# every syllable onset, in beats (float) from the first beat
onsets = []
for wd in words:
    k = syllables(wd["w"])
    if not k:
        continue
    dur = max(0.05, wd["end"] - wd["start"])
    for i in range(k):
        t = wd["start"] + dur * i / k
        onsets.append((t - beats[0]) / period)
onsets = np.array(sorted(onsets))


def fit(pos, div):
    """Mean distance, in beats, from each onset to the nearest 1/div of a beat."""
    return float(np.mean(np.abs(pos * div - np.round(pos * div)) / div)) if len(pos) else 1.0


lines = []
n_bars = int(np.ceil((onsets.max() + 1) / 4)) if len(onsets) else 0
for bar in range(n_bars):
    inbar = onsets[(onsets >= bar * 4) & (onsets < bar * 4 + 4)] - bar * 4
    if len(inbar) == 0:
        continue
    slots = ["."] * 16
    for p in inbar:
        slots[min(15, int(round(p * 4)) % 16)] = "x"
    cells = " ".join("".join(slots[b * 4 : b * 4 + 4]) for b in range(4))
    f16, f12 = fit(inbar, 4), fit(inbar, 3)
    feel = "triplet" if f12 < f16 * 0.8 and len(inbar) >= 6 else "straight"
    t0 = beats[0] + bar * 4 * period
    lines.append(f"{int(t0 // 60)}:{t0 % 60:05.2f}  |{cells}|  {len(inbar):>2} syl  {feel}")

print(f"tempo {60 / period:.1f} BPM, beat = {period:.3f}s; {len(words)} words, "
      f"~{len(onsets)} syllables (estimated)")
print("each |....| is one beat, four slots per beat; x = a syllable starts there\n")
print("\n".join(lines))
(here / "flow.txt").write_text("\n".join(lines), encoding="utf-8")
