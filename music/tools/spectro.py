"""Turn the song into pictures I can look at.

A mel spectrogram: time runs left to right, pitch runs bottom (bass) to top
(hi-hats), brightness is loudness. Written as PNG by hand -- no image library
is installed, and a PNG is only rows of pixels in a small zlib wrapper.

Marks: a short dim tick every 10 s along the bottom, a full-height faint line
every 60 s. Faint horizontal lines at 200 Hz (kick/bass ceiling) and 3 kHz
(top of most vocal energy).

Usage: spectro.py OUT.png [start_s end_s width]
"""

import struct
import sys
import zlib
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import get_window

here = Path(__file__).parent


def png(path: Path, rgb: np.ndarray) -> None:
    h, w, _ = rgb.shape
    raw = b"".join(b"\x00" + rgb[y].astype(np.uint8).tobytes() for y in range(h))

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def mel_filters(sr, n_fft, n_mels=160, fmin=30, fmax=11000):
    def hz2mel(f):
        return 2595 * np.log10(1 + f / 700)

    def mel2hz(m):
        return 700 * (10 ** (m / 2595) - 1)

    pts = mel2hz(np.linspace(hz2mel(fmin), hz2mel(fmax), n_mels + 2))
    freqs = np.fft.rfftfreq(n_fft, 1 / sr)
    fb = np.zeros((n_mels, len(freqs)))
    for i in range(n_mels):
        lo, mid, hi = pts[i], pts[i + 1], pts[i + 2]
        fb[i] = np.clip(np.minimum((freqs - lo) / (mid - lo), (hi - freqs) / (hi - mid)), 0, None)
    return fb, pts[1:-1]


def colour(v):
    """0..1 -> black, deep blue, magenta, orange, pale yellow."""
    stops = np.array([[0, 0, 0], [20, 20, 90], [150, 30, 140], [240, 120, 40], [255, 245, 190]], float)
    x = np.clip(v, 0, 1) * (len(stops) - 1)
    i = np.minimum(x.astype(int), len(stops) - 2)
    f = (x - i)[..., None]
    return stops[i] * (1 - f) + stops[i + 1] * f


def main():
    out = Path(sys.argv[1])
    sr, x = wavfile.read(here / "top_floor.wav" if len(sys.argv) < 6 else here / sys.argv[5])
    x = x.astype(np.float32)
    x /= np.abs(x).max() + 1e-9
    start = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
    end = float(sys.argv[3]) if len(sys.argv) > 3 else len(x) / sr
    width = int(sys.argv[4]) if len(sys.argv) > 4 else 1600
    seg = x[int(start * sr) : int(end * sr)]
    n_fft = 2048
    hop = max(64, (len(seg) - n_fft) // width)
    n = 1 + (len(seg) - n_fft) // hop
    frames = np.lib.stride_tricks.as_strided(seg, (n, n_fft), (seg.strides[0] * hop, seg.strides[0]))
    power = np.abs(np.fft.rfft(frames * get_window("hann", n_fft), axis=1)) ** 2
    fb, centres = mel_filters(sr, n_fft)
    mel = np.log10(power @ fb.T + 1e-10)
    lo, hi = np.percentile(mel, 5), np.percentile(mel, 99.5)
    img = colour((mel - lo) / (hi - lo)).transpose(1, 0, 2)[::-1]  # bass at the bottom
    img = np.repeat(img, 3, axis=0)  # taller, easier to read
    H = img.shape[0]
    secs = start + np.arange(n) * hop / sr
    for col in range(n):
        t = secs[col]
        prev = secs[col - 1] if col else t - 1
        if int(t // 60) != int(prev // 60):
            img[:, col] = img[:, col] * 0.4 + 255 * 0.6
        elif int(t // 10) != int(prev // 10):
            img[H - 18 :, col] = 255
    for f in (200, 3000):
        row = H - 1 - int(np.argmin(np.abs(centres - f))) * 3
        img[row, ::4] = img[row, ::4] * 0.3 + 255 * 0.7
    png(out, img)
    print(f"{out.name}: {start:.1f}-{end:.1f}s, {n} columns x {H} rows, {hop / sr * 1000:.1f} ms per column")


if __name__ == "__main__":
    main()
