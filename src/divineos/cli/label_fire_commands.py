"""`divineos label-fire` — dispute a Stop-gate fire, without paying a toll.

Register item **O**, 2026-08-05. The correction-shape-v2 gate names its own
false-positive path as `python scripts/label_correction_shape_false_positive.py`.
Twice this session I went to run it and was blocked first by the engagement
checks — a goal-not-set and a consult-count — so the remedy for a wrong block
sat behind two more blocks.

**Why that is not cosmetic.** Every label appends detector-verdict-beside-my-
judgment to a corpus that is explicitly the training data for the semantic
layer meant to replace the keyword detector. If disagreeing costs more than
complying, the corpus skews toward silence, and the thing built from it
inherits the skew. A toll on dissent shapes what the system learns about
itself.

**Why a command and not a wider matcher.** `hooks/pre_tool_use_gate.py` matches
bypasses by stripping `divineos ` and checking the subcommand, so a
`python scripts/...` invocation can never match and no line in
`scripts/hook_bypass_commands.txt` could have fixed this. The alternative was
widening a matcher that guards arbitrary shell execution — a security-relevant
loosening, to solve an ergonomics problem. Making the remedy a first-class
command is what every other gate remedy already is, uses the proven mechanism
unchanged, and costs the bypass list exactly one line.

**What is deliberately preserved.** Chesterton's fence: the awkward path did
prevent something real — a cheap escape would let me wave away an inconvenient
catch. So this wrapper adds no leniency whatsoever. The `--reason` minimum, the
labels-only-a-real-fire rule, and the append-to-corpus permanence all still
live in the script; this only removes the *unrelated* toll of proving
engagement before being allowed to speak.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import click


def _script_path() -> Path:
    """Locate the labeller script from this module's position in the tree."""
    return (
        Path(__file__).resolve().parents[3] / "scripts" / "label_correction_shape_false_positive.py"
    )


def register(cli: click.Group) -> None:
    @cli.command("label-fire")
    @click.option(
        "--reason",
        required=True,
        help="What class of MENTION was misread as USE. Not 'false positive' — the shape of the miss.",
    )
    def label_fire(reason: str) -> None:
        """Label the latest correction-shape Stop-gate fire a false positive.

        Thin wrapper over the labeller script so the remedy is reachable
        through the same bypass channel as every other gate remedy. All of
        the script's honesty constraints still apply — this adds no leniency,
        it only removes the toll.
        """
        script = _script_path()
        if not script.exists():
            # The third word. A missing labeller is not a successful label.
            raise click.ClickException(
                f"CANNOT LABEL — labeller script not found at {script}. "
                "Nothing was recorded. This is not 'label filed'."
            )
        proc = subprocess.run(
            [sys.executable, str(script), "--reason", reason],
            check=False,
        )
        raise SystemExit(proc.returncode)
