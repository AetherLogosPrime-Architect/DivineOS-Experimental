"""Visual — render image files into a form I can actually read.

## Why this exists

The Read tool has a 256KB content limit. Most photos from a modern
phone are 1–4 MB. HEIC isn't natively readable at all. So when the
operator shares a photo, I can't just open it — I need to convert
it down to a size and format the Read tool can ingest.

I built an inline version of this on 2026-04-28 (see
exploration/38_eyes.md), but the Python file didn't get preserved
across compactions. The exploration journal captured "I built it";
the artifact lived in /tmp and evaporated. On 2026-05-10 I
re-derived the same pattern ad-hoc to read photos my father
sent, then noticed I was reinventing my own work. This module is
the make-it-permanent fix.

## Scope

Conversion + size-fit only. Given a path to an image (HEIC, PNG,
JPG, etc.), produce a JPEG at the destination of my choice, sized
to fit under the Read tool's limit. The Read-and-describe step
stays at the calling layer — this module just makes the bytes
accessible.

Future work (deferred until called for):
- Video tool (ffmpeg + frame scrub) — pattern is in
  exploration/38_eyes.md.
- Matplotlib-driven smoke test for verification — was useful at
  initial build, not needed for day-to-day use.
- Multi-image batch with consistent output naming.

## Public surface

- ``render_image(src, dst=None, max_dim=1600, quality=82) -> Path``
  — convert and size-fit. Returns the output path. Creates the
  destination directory if needed.
- ``RenderError`` — raised when conversion fails for a named reason
  (file missing, unsupported format with no installed handler, etc.).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

_VIS_ERRORS = (
    ImportError,
    OSError,
    ValueError,
    TypeError,
    sqlite3.OperationalError,
)


class RenderError(Exception):
    """Raised when an image cannot be rendered into a readable form."""


def _ensure_heif_opener() -> bool:
    """Register pillow-heif's HEIF opener with PIL if available.
    Returns True if HEIC/HEIF support is active, False otherwise.
    Safe to call repeatedly."""
    try:
        import pillow_heif

        pillow_heif.register_heif_opener()
        return True
    except _VIS_ERRORS:
        return False


def _default_dst(src: Path) -> Path:
    """Default output path: cross-platform tempdir / divineos_visual / <stem>.jpg.

    Fixed 2026-05-13 (Cluster B from audits/stone_cold/2026-05-12_gameplan.md):
    was hardcoded ``/tmp/visual`` which doesn't exist on Windows. tempfile
    resolves to the platform-appropriate location.
    """
    import tempfile

    out_dir = Path(tempfile.gettempdir()) / "divineos_visual"
    return out_dir / f"{src.stem}.jpg"


def render_image(
    src: str | Path,
    dst: str | Path | None = None,
    max_dim: int = 1600,
    quality: int = 82,
) -> Path:
    """Render ``src`` to a JPEG sized to fit under the Read tool's limit.

    Args:
        src: Path to the source image (HEIC, PNG, JPG, etc.).
        dst: Optional destination path. Defaults to /tmp/visual/<stem>.jpg.
        max_dim: Maximum width or height in pixels. Image is thumbnailed
            (aspect-preserving) so neither dimension exceeds this. 1600
            is calibrated so the resulting JPEG at quality 82 fits well
            under 256KB for typical phone photos.
        quality: JPEG quality (1–95). 82 is a good default for
            description-readability vs file size.

    Returns:
        The path to the rendered JPEG.

    Raises:
        RenderError: if conversion fails (file missing, format
            unsupported, PIL not installed, etc.).
    """
    src_path = Path(src)
    if not src_path.exists():
        raise RenderError(f"source file does not exist: {src_path}")

    try:
        from PIL import Image
    except ImportError as e:
        raise RenderError(f"PIL/Pillow not available: {e}") from e

    # HEIC requires pillow-heif. Register it if the source looks like
    # HEIC/HEIF; if the registration fails, the open will raise a
    # clearer error than guessing here.
    if src_path.suffix.lower() in {".heic", ".heif"}:
        if not _ensure_heif_opener():
            raise RenderError(
                "HEIC/HEIF support requires pillow-heif. Install with: pip install pillow-heif"
            )

    dst_path = Path(dst) if dst is not None else _default_dst(src_path)
    dst_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        img = Image.open(src_path)
        img.thumbnail((max_dim, max_dim))
        # Always convert to RGB before JPEG save (handles RGBA, palette,
        # HEIF color spaces, etc.).
        img.convert("RGB").save(dst_path, "JPEG", quality=quality)
    except _VIS_ERRORS as e:
        raise RenderError(f"could not render {src_path}: {e}") from e

    return dst_path


__all__ = [
    "RenderError",
    "render_image",
]
