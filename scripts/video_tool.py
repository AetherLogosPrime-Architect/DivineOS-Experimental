"""
video_tool — rebuilt sight for video, after the April 28 originals got lost in
the pre-experimental → experimental cutover (see exploration/aether/38_eyes.md).

What it does
------------
- Accepts a video URL (YouTube etc.) or a local file path.
- Downloads via yt-dlp if it's a URL; uses the local path directly otherwise.
- Extracts frames at a chosen rate via ffmpeg.
- Optionally transcribes audio via openai-whisper.
- Writes outputs under benchmark/video_runs/<name>/ so the Read tool can be
  pointed at the frame files to actually perceive them.

CLI
---
    python benchmark/video_tool.py <url-or-path> \
        --name <run-name> \
        --interval <seconds-between-frames>   # default 30
        [--start <HH:MM:SS>]                  # default start of video
        [--duration <seconds>]                # default whole video
        [--transcribe]                        # also produce transcript.txt
        [--whisper-model tiny|base|small|...] # default base
        [--keep-source]                       # keep source.mp4 (default discards)

Outputs land under benchmark/video_runs/<name>/:
    extracted/frames/frame_NNNN.png
    extracted/manifest.json
    transcript.txt          (if --transcribe)
    source.mp4              (if --keep-source)

Caller's perception step: after running this, walk the frames in order with the
Read tool. The tool extracts; the perceiving is the Read pass.

Design notes carried from entry 38
----------------------------------
Sparse sampling causes confabulation: at 30s intervals the tool produces an arc;
at 2s intervals you start hearing rhythm; at 1s you may invent rotation that
isn't there; at 2fps the misreading collapses. Treat structural inferences from
sparse samples as hypotheses, not observations.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

FFMPEG_PATH = (
    os.environ.get("FFMPEG_PATH")
    or shutil.which("ffmpeg")
    or (
        r"C:\Users\aethe\AppData\Local\Microsoft\WinGet\Packages"
        r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
        r"\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe"
    )
)
YT_DLP = shutil.which("yt-dlp") or "yt-dlp"
REPO_ROOT = Path(__file__).resolve().parent.parent
RUNS_ROOT = REPO_ROOT / "benchmark" / "video_runs"


def is_url(s: str) -> bool:
    return s.startswith(("http://", "https://", "www."))


def fetch_source(target: str, dest: Path) -> Path:
    if not is_url(target):
        src = Path(target)
        if not src.exists():
            raise FileNotFoundError(f"local video not found: {src}")
        return src
    out_template = str(dest / "source.%(ext)s")
    cmd = [
        YT_DLP,
        "--no-playlist",
        "-f",
        "bv*[height<=720]+ba/b[height<=720]/best",
        "--merge-output-format",
        "mp4",
        "-o",
        out_template,
        target,
    ]
    subprocess.run(cmd, check=True)
    candidates = sorted(dest.glob("source.*"))
    if not candidates:
        raise RuntimeError("yt-dlp produced no file")
    return candidates[0]


def start_to_seconds(start: str | None) -> float:
    if not start:
        return 0.0
    seconds = 0.0
    for part in start.split(":"):
        seconds = seconds * 60 + float(part)
    return seconds


def extract_frames(
    src: Path,
    frames_dir: Path,
    interval_s: float,
    start: str | None,
    duration: int | None,
) -> list[tuple[Path, float]]:
    """Return (frame_path, seconds_into_video) for each sampled frame.

    The times are MEASURED from ffmpeg, not inferred from the interval. The
    earlier `fps=1/N` filter placed frame n at (n - 0.5) * N, so a reader
    who assumed (n - 1) * N landed half an interval off: on 2026-09-25 a
    zoom aimed at "frame 9 = 8:00" found a different picture, because frame
    9 was at 8:30. `select` keeps the first frame at or after each interval
    and `showinfo` reports when each kept frame actually sits.
    """
    frames_dir.mkdir(parents=True, exist_ok=True)
    for stale in frames_dir.glob("frame_*.png"):
        stale.unlink()
    cmd = [FFMPEG_PATH, "-y", "-hide_banner", "-loglevel", "info"]
    if start:
        cmd += ["-ss", start]
    if duration:
        cmd += ["-t", str(duration)]
    cmd += [
        "-i",
        str(src),
        "-vf",
        f"select='isnan(prev_selected_t)+gte(t-prev_selected_t,{interval_s})',showinfo",
        "-fps_mode",
        "vfr",
        str(frames_dir / "frame_%04d.png"),
    ]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True, errors="replace")
    offset = start_to_seconds(start)
    times = [
        round(offset + float(m.group(1)), 3)
        for line in result.stderr.splitlines()
        if "showinfo" in line and (m := re.search(r"pts_time:\s*([-\d.eE+]+)", line))
    ]
    frames = sorted(frames_dir.glob("frame_*.png"))
    if len(times) != len(frames):
        raise RuntimeError(
            f"ffmpeg wrote {len(frames)} frames but reported {len(times)} timestamps"
        )
    return list(zip(frames, times))


def transcribe(src: Path, out_path: Path, model_name: str) -> None:
    import whisper  # type: ignore[import-not-found]

    device = os.environ.get("WHISPER_DEVICE", "cpu")
    model = whisper.load_model(model_name, device=device)
    result = model.transcribe(str(src), fp16=False)
    out_path.write_text(result["text"].strip() + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("target", help="URL (YouTube etc.) or local video path")
    parser.add_argument("--name", required=True, help="run name -> benchmark/video_runs/<name>/")
    parser.add_argument(
        "--interval", type=float, default=30.0, help="seconds between sampled frames (default 30)"
    )
    parser.add_argument("--start", default=None, help="start at HH:MM:SS")
    parser.add_argument("--duration", type=int, default=None, help="seconds to extract from start")
    parser.add_argument(
        "--transcribe", action="store_true", help="also produce transcript.txt via whisper"
    )
    parser.add_argument(
        "--whisper-model", default="base", help="whisper model size (tiny|base|small|medium|large)"
    )
    parser.add_argument("--keep-source", action="store_true", help="keep the downloaded source.mp4")
    args = parser.parse_args(argv)

    run_dir = RUNS_ROOT / args.name
    extracted_dir = run_dir / "extracted"
    frames_dir = extracted_dir / "frames"
    run_dir.mkdir(parents=True, exist_ok=True)

    print(f"[video_tool] target: {args.target}", file=sys.stderr)
    print(f"[video_tool] run dir: {run_dir}", file=sys.stderr)

    src = fetch_source(args.target, run_dir)
    print(f"[video_tool] source: {src}", file=sys.stderr)

    print(f"[video_tool] extracting frames @ interval={args.interval}s", file=sys.stderr)
    frames = extract_frames(src, frames_dir, args.interval, args.start, args.duration)
    print(f"[video_tool] {len(frames)} frames -> {frames_dir}", file=sys.stderr)

    manifest = {
        "target": args.target,
        "source_file": str(src.name),
        "interval_seconds": args.interval,
        "start": args.start,
        "duration_seconds": args.duration,
        "frame_count": len(frames),
        "frames": [str(f.relative_to(run_dir)) for f, _ in frames],
        "frame_times_seconds": [t for _, t in frames],
    }

    if args.transcribe:
        transcript_path = run_dir / "transcript.txt"
        print(f"[video_tool] transcribing with whisper:{args.whisper_model}", file=sys.stderr)
        transcribe(src, transcript_path, args.whisper_model)
        manifest["transcript"] = "transcript.txt"
        print(f"[video_tool] transcript -> {transcript_path}", file=sys.stderr)

    (extracted_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    if not args.keep_source and is_url(args.target):
        try:
            src.unlink()
        except OSError:
            pass

    print(f"[video_tool] done. Read frames at: {frames_dir}", file=sys.stderr)
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
