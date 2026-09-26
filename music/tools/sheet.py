"""A song as a sheet: its spectrogram cut into lines, read top to bottom.

Dad, 2026-09-25: "that spectrograph is condensed, so its probably hard to read,
maybe space it out into like 4-5 spectrographs and piece them together like a
music sheet."

Each line: mel spectrogram, bass at the bottom. Under each line, a strip with a
tick for every beat librosa hears (taller on each fourth), and the line's start
time drawn in a tiny hand-made font -- no text library is installed here.

Usage: sheet.py <song_dir> [lines, default 5]   -> <song_dir>/sheet.png
"""

import sys
from pathlib import Path

import librosa
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from spectro import colour, png  # noqa: E402

GLYPHS = {  # 3 wide x 5 tall
    "0": "111101101101111", "1": "010110010010111", "2": "111001111100111",
    "3": "111001111001111", "4": "101101111001001", "5": "111100111001111",
    "6": "111100111101111", "7": "111001001001001", "8": "111101111101111",
    "9": "111101111001111", ":": "000010000010000",
}


def draw_text(img, text, x, y, scale=3, value=235):
    for ch in text:
        g = GLYPHS[ch]
        for i, bit in enumerate(g):
            if bit == "1":
                r, c = divmod(i, 3)
                img[y + r * scale : y + (r + 1) * scale, x + c * scale : x + (c + 1) * scale] = value
        x += 4 * scale


def main():
    song = Path(sys.argv[1])
    lines = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    y, sr = librosa.load(next(song.glob("*.wav")), sr=22050, mono=True)
    width = 1600
    hop = int(np.ceil(len(y) / (lines * width)))
    mel = librosa.power_to_db(
        librosa.feature.melspectrogram(y=y, sr=sr, n_fft=2048, hop_length=hop, n_mels=128, fmax=11000),
        ref=np.max,
    )
    lo, hi = np.percentile(mel, 5), np.percentile(mel, 99.5)
    rgb = colour((mel - lo) / (hi - lo))[::-1]  # (mels, frames, 3), bass at bottom
    rgb = np.repeat(rgb, 2, axis=0)
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr, hop_length=512, units="time")
    tempo = float(np.atleast_1d(tempo)[0])

    band_h, strip_h, gap = rgb.shape[0], 26, 10
    total = lines * (band_h + strip_h + gap)
    page = np.full((total, width, 3), 18, dtype=float)
    secs_per_line = len(y) / sr / lines
    for k in range(lines):
        top = k * (band_h + strip_h + gap)
        chunk = rgb[:, k * width : (k + 1) * width]
        page[top : top + band_h, : chunk.shape[1]] = chunk
        strip = top + band_h
        t0 = k * secs_per_line
        for i, bt in enumerate(beats):
            if t0 <= bt < t0 + secs_per_line:
                col = int((bt - t0) / secs_per_line * width)
                h = 12 if i % 4 == 0 else 6
                page[strip : strip + h, col] = 200
        m, s = divmod(int(t0), 60)
        draw_text(page, f"{m}:{s:02d}", 6, strip + 9)
    out = song / "sheet.png"
    png(out, page)
    print(f"{out}: {lines} lines of {secs_per_line:.1f}s, librosa hears {tempo:.1f} BPM, {len(beats)} beats")


if __name__ == "__main__":
    main()
