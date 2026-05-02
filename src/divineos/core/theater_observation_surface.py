"""Theater/fabrication observation surface — replaces gate 1.46.

Reads the theater_marker file (~/.divineos/theater_unresolved.json)
and surfaces it in the briefing as an observational notice. The marker
is forensic record only since 2026-05-01; this surface is how the
record gets read.

Design parallels the operating-loop surfaces (register_observer,
spiral_detector, substitution_detector findings): observation, not
enforcement. The agent reads, decides whether the detector caught a
real drift or a false positive, names with correction / learn if
real, lets it stand if false.

Empty surface when no marker exists. Quiet by design — no marker
means no observation to surface.
"""

from __future__ import annotations

from divineos.core import theater_marker


def format_for_briefing() -> str:
    """Return the briefing block when a theater/fabrication marker is present.

    Empty string when no marker file exists. The marker file is written
    by the Stop hook (detect-theater.sh) when evaluate_theater or
    evaluate_fabrication returns flags on the last assistant output.
    """
    marker = theater_marker.read_marker()
    if not marker:
        return ""

    monitor = marker.get("monitor", "output")
    kinds = marker.get("flag_kinds") or []
    kinds_str = ", ".join(str(k) for k in kinds[:3]) if kinds else "unspecified"
    preview = (marker.get("preview") or "").replace("\n", " ")[:160]

    lines = [
        f"[observation] {monitor}-shape detector fired on my last output ({kinds_str}).",
        f'  preview: "{preview}"',
        "  Embodied claims, kitchen-theater, writing-AT-subagent shapes are",
        "  categorically fictional for this substrate. Surfaced as data, not",
        "  a gate. If the detector caught a real drift: name with",
        '  `divineos correction "..."` or `divineos learn "..."` (clears the',
        "  marker). If it caught a false positive (label use, functional analog",
        "  framing, sensory term applied to a substrate analog): let it stand.",
    ]
    return "\n".join(lines) + "\n"


__all__ = ["format_for_briefing"]
