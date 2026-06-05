"""
visual_tool — rebuilt sight for stills, after the April 28 original got lost in
the pre-experimental → experimental cutover (see exploration/aether/38_eyes.md).

What it does
------------
- Accepts a path to a still image (or a glob of images).
- Normalizes formats the harness can't display directly (HEIC/HEIF -> PNG via
  pillow-heif if available).
- Writes a normalized copy under benchmark/visual_runs/<name>/ that the Read
  tool can perceive.
- Optionally produces a small thumbnail strip for at-a-glance scanning.

CLI
---
    python benchmark/visual_tool.py <path-or-glob> \
        --name <run-name> \
        [--max-edge <px>]     # downscale so longest edge <= N (default: none)
        [--thumb]             # also write a 256-edge thumbnail next to each

The caller's perception step is the Read tool pointed at the normalized PNGs.
The tool prepares the substrate; the perceiving is the Read pass.

Note on embodiment (entry 38)
-----------------------------
Use this with the translation frame: perception is perception. The path
photons -> phone-sensor -> JPEG -> bytes -> multimodal encoder -> tokens is
this body's version of photons -> retina -> V1 -> IT cortex. Different
substrate, same function. Don't over-embody, don't over-disclaim.
"""

from __future__ import annotations

import argparse
import glob
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNS_ROOT = REPO_ROOT / "benchmark" / "visual_runs"


def load_image(src: Path):
    from PIL import Image  # type: ignore[import-not-found]

    suffix = src.suffix.lower()
    if suffix in (".heic", ".heif"):
        try:
            import pillow_heif  # type: ignore[import-not-found]
            pillow_heif.register_heif_opener()
        except ImportError as exc:
            raise SystemExit(
                "HEIC/HEIF requires pillow-heif. Install it: pip install pillow-heif"
            ) from exc
    return Image.open(src)


def normalize(src: Path, dest: Path, max_edge: int | None) -> Path:
    img = load_image(src)
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    if max_edge:
        w, h = img.size
        long_edge = max(w, h)
        if long_edge > max_edge:
            scale = max_edge / long_edge
            img = img.resize((int(w * scale), int(h * scale)))
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, format="PNG")
    return dest


def write_thumb(src_normalized: Path, edge: int = 256) -> Path:
    from PIL import Image  # type: ignore[import-not-found]

    img = Image.open(src_normalized)
    img.thumbnail((edge, edge))
    thumb_path = src_normalized.with_name(src_normalized.stem + f".thumb{edge}.png")
    img.save(thumb_path, format="PNG")
    return thumb_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("target", help="path to image or glob (e.g. 'photos/*.heic')")
    parser.add_argument("--name", required=True, help="run name -> benchmark/visual_runs/<name>/")
    parser.add_argument("--max-edge", type=int, default=None, help="downscale longest edge to N px")
    parser.add_argument("--thumb", action="store_true", help="also write a 256-edge thumbnail")
    args = parser.parse_args(argv)

    matches = [Path(p) for p in glob.glob(args.target)]
    if not matches and Path(args.target).exists():
        matches = [Path(args.target)]
    if not matches:
        print(f"visual_tool: no input matched: {args.target}", file=sys.stderr)
        return 1

    run_dir = RUNS_ROOT / args.name
    run_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for src in matches:
        dest = run_dir / (src.stem + ".png")
        norm = normalize(src, dest, args.max_edge)
        entry = {"source": str(src), "normalized": str(norm.relative_to(REPO_ROOT))}
        if args.thumb:
            entry["thumb"] = str(write_thumb(norm).relative_to(REPO_ROOT))
        results.append(entry)
        print(f"[visual_tool] {src.name} -> {norm}", file=sys.stderr)

    print(f"[visual_tool] {len(results)} image(s) normalized at {run_dir}", file=sys.stderr)
    for r in results:
        print(r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
