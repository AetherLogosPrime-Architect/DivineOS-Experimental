"""video_tool must report when each sampled frame really sits in the video.

On 2026-09-25 the manifest carried no times, a reader inferred frame n at
(n - 1) * interval, and the frames were really at (n - 0.5) * interval, so a
close-up aimed at 8:00 landed on a different picture than the one chosen.

The synthetic video here encodes time as brightness, so a recorded time is
checked against what the frame actually shows, not against the arithmetic
that was wrong before.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "video_tool", REPO_ROOT / "scripts" / "video_tool.py"
)
video_tool = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(video_tool)

pytestmark = pytest.mark.skipif(
    not Path(video_tool.FFMPEG_PATH).exists() and shutil.which("ffmpeg") is None,
    reason="ffmpeg not installed",
)

LUMA_PER_SECOND = 20


def _ramp_video(tmp_path: Path) -> Path:
    """10 s, 10 fps grey ramp: brightness = 16 + 20 * t."""
    out = tmp_path / "ramp.mp4"
    subprocess.run(
        [
            video_tool.FFMPEG_PATH,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=64x64:r=10:d=10",
            "-vf",
            f"geq=lum='16+{LUMA_PER_SECOND}*T':cb=128:cr=128",
            "-pix_fmt",
            "yuv420p",
            str(out),
        ],
        check=True,
    )
    return out


def _mean_luma(png: Path) -> float:
    from PIL import Image

    pixels = list(Image.open(png).convert("L").getdata())
    return sum(pixels) / len(pixels)


def _luma_at(src: Path, t: float, tmp_path: Path) -> float:
    """Ground truth: the frame ffmpeg shows when seeking straight to t."""
    out = tmp_path / f"truth_{t:.3f}.png"
    subprocess.run(
        [
            video_tool.FFMPEG_PATH,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            str(t),
            "-i",
            str(src),
            "-frames:v",
            "1",
            str(out),
        ],
        check=True,
    )
    return _mean_luma(out)


# Half a second of ramp is ~11 PNG levels, so this tolerance separates the
# right frame from one half an interval away, which is the bug being pinned.
LUMA_TOLERANCE = 4


def _assert_each_frame_is_where_it_says(frames, src, tmp_path):
    for path, t in frames:
        shown, truth = _mean_luma(path), _luma_at(src, t, tmp_path)
        assert abs(shown - truth) < LUMA_TOLERANCE, (path.name, t, shown, truth)


def test_recorded_times_match_what_each_frame_shows(tmp_path):
    src = _ramp_video(tmp_path)
    frames = video_tool.extract_frames(src, tmp_path / "frames", 2.0, None, None)

    assert [round(t) for _, t in frames] == [0, 2, 4, 6, 8]
    _assert_each_frame_is_where_it_says(frames, src, tmp_path)


def test_start_offset_is_added_to_recorded_times(tmp_path):
    src = _ramp_video(tmp_path)
    frames = video_tool.extract_frames(src, tmp_path / "frames", 1.0, "00:00:05", 3)

    assert [round(t) for _, t in frames] == [5, 6, 7]
    _assert_each_frame_is_where_it_says(frames, src, tmp_path)


def test_stale_frames_from_an_earlier_run_do_not_survive(tmp_path):
    src = _ramp_video(tmp_path)
    frames_dir = tmp_path / "frames"
    video_tool.extract_frames(src, frames_dir, 1.0, None, None)
    frames = video_tool.extract_frames(src, frames_dir, 5.0, None, None)

    assert len(frames) == len(list(frames_dir.glob("frame_*.png"))) == 2
