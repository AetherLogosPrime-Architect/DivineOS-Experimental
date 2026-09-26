"""How fast the words come, moment by moment, and where named lines land.

Syllable rate in a sliding window (syllables per second), plus the time of
each anchor word asked for, so a reading made from the lyrics ("the sprint is
here, the stop is there") can be checked against the audio.

Usage: pace.py <song_dir> [anchor ...]
Anchors are matched loosely (lowercase, letters only, word starts with it).
Syllables are estimated from vowel groups: an estimate, said so in the output.
"""

import json
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

song = Path(sys.argv[1])
anchors = [a.lower() for a in sys.argv[2:]]
words = json.loads((song / "words.json").read_text(encoding="utf-8"))


def syllables(w: str) -> int:
    w = re.sub(r"[^a-z]", "", w.lower())
    if not w:
        return 0
    n = len(re.findall(r"[aeiouy]+", w))
    if w.endswith("e") and n > 1 and not w.endswith(("le", "ee")):
        n -= 1
    return max(1, n)


onsets = []
for wd in words:
    k = syllables(wd["w"])
    dur = max(0.05, wd["end"] - wd["start"])
    onsets += [wd["start"] + dur * i / k for i in range(k)]
onsets = np.array(sorted(onsets))


def rate(t0, t1):
    n = ((onsets >= t0) & (onsets < t1)).sum()
    return n / max(1e-6, t1 - t0)


print("syllables per second in 4-second windows (estimated syllables):")
end = words[-1]["end"] if words else 0
for t in np.arange(0, end, 4):
    r = rate(t, t + 4)
    print(f"  {int(t // 60)}:{t % 60:04.1f}  {r:4.1f}  {'#' * int(round(r * 2))}")

if anchors:
    print("\nanchors (first match of each, in song order; rate over the 4 s starting there):")
    for a in anchors:
        hits = [w for w in words if re.sub(r"[^a-z]", "", w["w"].lower()).startswith(a)]
        for h in hits:
            t = h["start"]
            print(f"  {a:>10}  at {int(t // 60)}:{t % 60:04.1f}  rate {rate(t, t + 4):4.1f}/s"
                  f"  (heard as '{re.sub(r'[^a-zA-Z]', '', h['w'])}')")
