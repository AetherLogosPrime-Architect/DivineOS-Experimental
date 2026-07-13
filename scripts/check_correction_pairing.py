#!/usr/bin/env python3
"""Observe-then-learn pairing checker (thin CLI wrapper).

The substantive logic moved to ``divineos.core.correction_pairing``
as part of Finding 1 wire-decision. This script is preserved for
backward compat and for invocations from operating-system shells
that prefer ``python scripts/check_correction_pairing.py``.

Consumers:
  * Briefing-dashboard row (``_row_correction_pairing``)
  * Admin CLI command (``divineos check-correction-pairing``)
  * This script (backward compat)

Usage:

    python scripts/check_correction_pairing.py [--obs-window-min N] [--learn-window-min N]

Returns:
  * Exit 0 if no unpaired observations.
  * Exit 1 if any unpaired observations exist; prints details + drafts.

Pre-reg: prereg-301e34c8bf39 (two-record-conflation pattern).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add src to path so we can import divineos as a package when run as
# a bare script (not via the installed CLI).
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from divineos.core.correction_pairing import (  # noqa: E402
    DEFAULT_LEARN_AFTER_OBSERVATION_MIN,
    DEFAULT_OBSERVATION_AFTER_CORRECTION_MIN,
    find_unpaired_observations,
    format_unpaired,
)

# Backward-compat alias for callers (tests, briefing-dashboard) that
# expect the shorter name. The canonical name is find_unpaired_observations.
find_unpaired = find_unpaired_observations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--obs-window-min",
        type=int,
        default=DEFAULT_OBSERVATION_AFTER_CORRECTION_MIN,
        help="Minutes to look back from an observation for a correction event.",
    )
    parser.add_argument(
        "--learn-window-min",
        type=int,
        default=DEFAULT_LEARN_AFTER_OBSERVATION_MIN,
        help="Minutes to look forward from an observation for a learn entry.",
    )
    args = parser.parse_args()

    unpaired = find_unpaired_observations(
        observation_after_correction_min=args.obs_window_min,
        learn_after_observation_min=args.learn_window_min,
    )
    print(format_unpaired(unpaired))
    return 1 if unpaired else 0


if __name__ == "__main__":
    sys.exit(main())
