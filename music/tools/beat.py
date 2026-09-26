"""Find the beat: where the drum hits land, the tempo, and the grid of beats.

Onset envelope = how much louder each short slice is than the one before it
(spectral flux), weighted toward the low end where kick drums live. Tempo =
the lag at which that envelope best repeats itself. Phase = where to lay the
grid so it sits on the most hits.

Run with --control to test on a generated click track of known tempo first.
"""

import json
import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import get_window

SR_EXPECT = 22050
FRAME, HOP = 2048, 512


def onset_envelope(x: np.ndarray, sr: int, low_only: bool = False) -> np.ndarray:
    """Envelope sample i describes the moment at the CENTRE of frame i.

    First version read frame i as starting at i*HOP and let hi-hats dominate;
    the control caught the grid sitting on the off-beat hat, not the kick.
    low_only keeps just the kick's range, and that is what pins the grid.
    """
    win = get_window("hann", FRAME)
    pad = np.concatenate([np.zeros(FRAME // 2, np.float32), x])  # frame i centred at i*HOP
    n = 1 + (len(pad) - FRAME) // HOP
    frames = np.lib.stride_tricks.as_strided(
        pad, shape=(n, FRAME), strides=(pad.strides[0] * HOP, pad.strides[0])
    )
    mag = np.abs(np.fft.rfft(frames * win, axis=1))
    freqs = np.fft.rfftfreq(FRAME, 1 / sr)
    if low_only:
        mag = mag[:, freqs < 150]
    logmag = np.log1p(mag * 10)
    flux = np.maximum(0, np.diff(logmag, axis=0))
    env = np.concatenate([[0], flux.sum(axis=1)])
    env -= np.convolve(env, np.ones(16) / 16, mode="same")  # remove slow loudness swells
    return np.maximum(env, 0)


def tempo_candidates(env: np.ndarray, sr: int, lo=60, hi=180):
    fps = sr / HOP
    ac = np.correlate(env, env, mode="full")[len(env) - 1 :]
    lags = np.arange(len(ac))
    bpm = 60 * fps / np.maximum(lags, 1)
    ok = (bpm >= lo) & (bpm <= hi)
    idx = lags[ok][np.argsort(ac[ok])[::-1]]
    seen, out = [], []
    for i in idx:
        b = 60 * fps / i
        if all(abs(b - s) > 3 for s in seen):
            seen.append(b)
            out.append((round(b, 1), float(ac[i] / ac[0])))
        if len(out) == 5:
            break
    return out


def refine(env, sr, bpm_guess):
    """Try tempos near the guess and every phase; keep the grid that sits on the most onset."""
    fps = sr / HOP
    best = (-1, None, None)
    for bpm in np.arange(bpm_guess - 2, bpm_guess + 2, 0.02):
        period = 60 * fps / bpm
        for phase in np.arange(0, period, 0.5):
            pos = np.arange(phase, len(env) - 1, period)
            score = env[np.round(pos).astype(int)].mean()
            if score > best[0]:
                best = (score, bpm, phase)
    score, bpm, phase = best
    period = 60 * fps / bpm
    beats = np.arange(phase, len(env) - 1, period) / fps
    # control: the same grid shifted half a beat should sit on much less
    off = env[np.round(np.arange(phase + period / 2, len(env) - 1, period)).astype(int)].mean()
    return float(bpm), beats, float(score), float(off)


def load(path: Path):
    sr, x = wavfile.read(path)
    x = x.astype(np.float32)
    if x.ndim > 1:
        x = x.mean(axis=1)
    return sr, x / (np.abs(x).max() + 1e-9)


def control():
    """A click track at 93 BPM with a quieter off-beat hat. The finder must say 93."""
    sr, dur, bpm = SR_EXPECT, 30.0, 93.0
    x = np.random.default_rng(0).normal(0, 0.01, int(sr * dur)).astype(np.float32)
    n = 3000
    kick = np.exp(-np.arange(n) / 900) * np.sin(2 * np.pi * 55 * np.arange(n) / sr)
    for t in np.arange(0.37, dur - 0.2, 60 / bpm):
        i = int(t * sr)
        x[i : i + n] += kick
        j = int((t + 30 / bpm) * sr)  # a loud off-beat hat: the trap the first version fell in
        x[j : j + 300] += 0.5 * np.random.default_rng(int(t * 100)).normal(0, 1, 300)
    got, beats, on, off = grid(x, sr)
    period = 60 / bpm
    phase_err = min((beats[0] - 0.37) % period, (0.37 - beats[0]) % period)
    print(f"CONTROL: built at {bpm} BPM, kicks from 0.37s -> found {got:.2f} BPM, "
          f"first beat {beats[0]:.3f}s (off the kick by {phase_err * 1000:.0f} ms), "
          f"on/off-beat {on:.2f}/{off:.2f}")
    tempo_ok = abs(got - bpm) < 1 or abs(got - 2 * bpm) < 2 or abs(got - bpm / 2) < 1
    return tempo_ok and phase_err < 0.035


def grid(x, sr):
    """Tempo from the whole mix; the grid itself pinned to the kick."""
    cands = tempo_candidates(onset_envelope(x, sr), sr)
    bpm, beats, on, off = refine(onset_envelope(x, sr, low_only=True), sr, cands[0][0])
    return bpm, beats, on, off


if __name__ == "__main__":
    if "--control" in sys.argv:
        sys.exit(0 if control() else 1)
    here = Path(sys.argv[1])
    sr, x = load(next(here.glob("*.wav")))
    env = onset_envelope(x, sr)
    cands = tempo_candidates(env, sr)
    print("tempo candidates (bpm, strength):", cands)
    bpm, beats, on, off = grid(x, sr)
    print(f"grid: {bpm:.2f} BPM, first beat at {beats[0]:.3f}s, {len(beats)} beats; "
          f"onset on the grid {on:.2f} vs half a beat off {off:.2f}")
    fps = sr / HOP
    (here / "beats.json").write_text(
        json.dumps({"bpm": bpm, "beats": [round(b, 3) for b in beats],
                    "candidates": cands, "env_fps": fps}, indent=1),
        encoding="utf-8",
    )
    np.save(here / "env.npy", env)
