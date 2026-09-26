"""How many beats to a bar -- found, not assumed.

Every other tool here assumed four beats to a bar. This one asks the song.
For each beat, how hard is it hit (onset strength near the beat, weighted to
the low end where the bar's first beat usually lands)? Then, for each bar
length N from 2 to 8, fold the accents into N columns and see how unequal the
columns are: if the song really groups in N, one column (the downbeat) stands
out. Multiples of the true N also score well (8 looks like 4), so the smallest
length close to the best score wins.

Usage: meter.py <song_dir>        meter.py --control
"""

import sys
from pathlib import Path

import librosa
import numpy as np


def accents(y, sr):
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr, hop_length=512)
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=512))
    low = S[: int(250 / (sr / 2048))]  # below 250 Hz: kick and bass
    # Plain power, not a log of it. The first version used log-flux, which is
    # kind to quiet sounds and so blurred the one thing a meter needs: the
    # downbeat hit harder than the rest. The threes control read as six.
    env = (low**2).sum(axis=0)
    acc = np.array([env[max(0, b - 2) : b + 3].max() for b in beats])
    acc = acc / (np.median(acc) + 1e-9)
    return float(np.atleast_1d(tempo)[0]), acc


def score(acc, n):
    """How much one position in an n-beat cycle outweighs the rest, best phase."""
    m = len(acc) // n * n
    if m < n * 4:
        return 0.0
    cols = acc[:m].reshape(-1, n).mean(axis=0)
    return float((cols.max() - np.median(cols)) / (acc.std() + 1e-9))


def profile(acc, n):
    m = len(acc) // n * n
    return acc[:m].reshape(-1, n).mean(axis=0)


def meter(acc):
    """Best-fitting fold, then shrink it while it repeats itself inside.

    The first version took the smallest length within 85% of the best score,
    and the control in threes came back as six: a six-fold catches the
    downbeat twice and scores higher. So: if the best fold's profile repeats
    with a shorter period d (strong-weak-weak-strong-weak-weak), the bar is d.
    """
    scores = {n: score(acc, n) for n in range(2, 9)}
    pick = max(scores, key=scores.get)
    shrunk = True
    while shrunk:
        shrunk = False
        cols = profile(acc, pick)
        for d in range(2, pick):
            if pick % d == 0 and np.corrcoef(cols, np.roll(cols, d))[0, 1] > 0.8:
                pick, shrunk = d, True
                break
    return pick, scores


def control():
    sr = 22050
    ok = True
    for n, bpm in ((4, 120.0), (5, 172.0), (3, 100.0)):
        dur = 40.0
        y = np.random.default_rng(1).normal(0, 0.005, int(sr * dur)).astype(np.float32)
        L = 2500
        kick = np.exp(-np.arange(L) / 700) * np.sin(2 * np.pi * 55 * np.arange(L) / sr)
        for i, t in enumerate(np.arange(0.5, dur - 0.3, 60 / bpm)):
            j = int(t * sr)
            y[j : j + L] += kick * (1.0 if i % n == 0 else 0.35)
            y[j : j + 200] += 0.2 * np.random.default_rng(i).normal(0, 1, 200)  # a hat on every beat
        tempo, acc = accents(y, sr)
        got, scores = meter(acc)
        print(f"CONTROL built in {n} at {bpm:.0f} BPM -> heard {tempo:.0f} BPM, groups of {got}  "
              + " ".join(f"{k}:{v:.2f}" for k, v in scores.items()))
        ok &= got == n
    return ok


def tempo_candidates(y, sr, k=6):
    """Every tempo the song plausibly runs at, strongest first -- not just one.

    On Take Five the tracker's single guess was ~123 BPM, the folds meant
    nothing, and the finder's own confidence said so (0.25, against 2+ on the
    controls). No hint is given here; the song offers its candidates and the
    fold that sits most confidently decides.
    """
    oenv = librosa.onset.onset_strength(y=y, sr=sr, hop_length=512)
    tg = librosa.feature.tempogram(onset_envelope=oenv, sr=sr, hop_length=512).mean(axis=1)
    bpms = librosa.tempo_frequencies(len(tg), sr=sr, hop_length=512)
    ok = (bpms > 60) & (bpms < 240)
    idx = [i for i in np.argsort(tg)[::-1] if ok[i]]
    out = []
    for i in idx:
        if all(abs(bpms[i] - b) / b > 0.04 for b in out):
            out.append(float(bpms[i]))
        if len(out) == k:
            break
    return out


def accents_at(y, sr, bpm):
    _, beats = librosa.beat.beat_track(y=y, sr=sr, hop_length=512, start_bpm=bpm, tightness=400)
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=512))
    env = (S[: int(250 / (sr / 2048))] ** 2).sum(axis=0)
    acc = np.array([env[max(0, b - 2) : b + 3].max() for b in beats])
    return acc / (np.median(acc) + 1e-9)


if __name__ == "__main__":
    if sys.argv[1] == "--control":
        sys.exit(0 if control() else 1)
    song = Path(sys.argv[1])
    y, sr = librosa.load(next(song.glob("*.wav")), sr=22050, mono=True)
    results = []
    for bpm in tempo_candidates(y, sr):
        acc = accents_at(y, sr, bpm)
        got, scores = meter(acc)
        results.append((scores[max(scores, key=scores.get)], bpm, got, len(acc), scores))
    results.sort(reverse=True)
    for conf, bpm, got, nb, scores in results:
        print(f"  at {bpm:5.1f} BPM: groups of {got}  (confidence {conf:.2f}, {nb} beats)  "
              + " ".join(f"{k}:{v:.2f}" for k, v in scores.items()))
    conf, bpm, got, _, _ = results[0]
    print(f"{song.name}: most confident reading -> {got} beats to a bar at {bpm:.0f} BPM (confidence {conf:.2f})")
