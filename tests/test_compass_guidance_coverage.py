"""Invariant test: compass_guidance in seed.json covers every spectrum.

Audit finding 2026-05-03 round 4: ``seed.json::compass_guidance`` was
missing 5 of 20 expected entries (engagement:excess, engagement:deficiency,
helpfulness:excess, helpfulness:deficiency, truthfulness:excess). When
the compass-rudder fired on those drift directions, there was no
guidance string to inject — the spectrum was measured but not
steered.

Existing ``_SPECTRUMS_CANONICAL_HASH`` invariant verifies the spectrum
DEFINITIONS haven't drifted. This test verifies the seed has matching
guidance for all of them.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEED_PATH = ROOT / "src" / "divineos" / "seed.json"


def test_seed_guidance_covers_all_spectrums():
    """Every (spectrum, axis) pair must have a guidance string."""
    from divineos.core.moral_compass import SPECTRUMS

    seed = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    guidance = seed.get("compass_guidance", {})
    guidance_keys = {k for k in guidance if not k.startswith("_")}

    expected = {f"{spectrum}:{axis}" for spectrum in SPECTRUMS for axis in ("excess", "deficiency")}

    missing = expected - guidance_keys
    extra = guidance_keys - expected

    msg_parts = []
    if missing:
        msg_parts.append(f"Missing guidance for: {sorted(missing)}")
    if extra:
        msg_parts.append(f"Unexpected guidance keys: {sorted(extra)}")
    assert not msg_parts, "; ".join(msg_parts)
