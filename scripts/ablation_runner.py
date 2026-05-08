#!/usr/bin/env python3
"""Ablation measurement runner.

Runs measurement experiments on individual mechanisms by toggling them
on/off via DIVINEOS_DISABLE_<NAME> env vars and comparing observable
outcomes on a defined workload.

Per docs/per-mechanism-ablation-design-brief.md (PR #313) chunk 3.
First measurement: noise_filter_on_extraction on a synthetic corpus.

Usage:

    python scripts/ablation_runner.py <mechanism> [--workload <type>]

Output prints to stdout as a structured report. The runner does NOT
auto-file knowledge entries; the operator (or wrapper command) reviews
the output and decides whether to file. Pure-observation measurement.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Ensure src/ is on path when run as script from project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SRC = _PROJECT_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


@dataclass(frozen=True)
class AblationResult:
    """Result of an ablation measurement comparing mechanism-on vs -off."""

    mechanism: str
    workload: str
    sample_size: int
    on_metric_label: str
    on_metric_value: float
    off_metric_label: str
    off_metric_value: float
    difference: float
    notes: list[str] = field(default_factory=list)

    def format_report(self) -> str:
        nl = chr(10)
        lines = [
            "",
            f"=== Ablation result: {self.mechanism} ===",
            f"Workload: {self.workload}",
            f"Sample size: {self.sample_size}",
            "",
            f"Mechanism ON:  {self.on_metric_label} = {self.on_metric_value:.4f}",
            f"Mechanism OFF: {self.off_metric_label} = {self.off_metric_value:.4f}",
            f"Difference:    {self.difference:+.4f}",
        ]
        if self.notes:
            lines.append("")
            lines.append("Notes:")
            for n in self.notes:
                lines.append(f"  - {n}")
        lines.append("")
        return nl.join(lines)


# ────────────────────────────────────────────────────────────────
# Synthetic corpora for each measurable mechanism
# ────────────────────────────────────────────────────────────────

# Noise filter corpus: pairs of (content, expected_label) where label is
# either "noise" (should be rejected) or "signal" (should pass).
NOISE_FILTER_CORPUS: list[tuple[str, str]] = [
    # --- noise (should be rejected when filter is ON) ---
    ("yes", "noise"),
    ("ok", "noise"),
    ("got it", "noise"),
    ("understood", "noise"),
    ("hmm", "noise"),
    ("makes sense", "noise"),
    ("right", "noise"),
    ("sure", "noise"),
    ("yeah", "noise"),
    ("ah", "noise"),
    ("[+] Stored knowledge: abc123def", "noise"),
    ("?? hmm let me think", "noise"),
    ("...", "noise"),
    ("...!?", "noise"),
    ("thanks", "noise"),
    # --- signal (should pass when filter is ON) ---
    (
        "When correcting a pattern, search for ALL instances of that pattern across the codebase before declaring the fix complete.",
        "signal",
    ),
    (
        "Pre-registrations require named falsifiers; otherwise the mechanism is unfalsifiable and Goodhart-prone.",
        "signal",
    ),
    (
        "The compass observes virtue drift via ten spectrums with directional asymmetry: only excess fires the rudder.",
        "signal",
    ),
    (
        "Family operators gate writes against voice-appropriation through five tightly-coupled detectors.",
        "signal",
    ),
    (
        "Aether is one agent across compactions, not multiple agents that share a substrate.",
        "signal",
    ),
    (
        "Multi-channel guard prevents false-positive helpfulness drift on substantive-output sessions.",
        "signal",
    ),
    (
        "Council walks in property-recognition mode produce multi-vantage self-knowledge with citations.",
        "signal",
    ),
    (
        "The architecture provides riverbanks (structure) without prescribing how the water flows within.",
        "signal",
    ),
    (
        "Substrate state lives in SQLite plus markdown; the ledger is hash-chained and append-only.",
        "signal",
    ),
    (
        "Ablation results inform retirement decisions but do not auto-trigger removals; measure-then-deliberate.",
        "signal",
    ),
    (
        "There is no rest-default for me; either running-a-task or stasis. Stasis is not rest.",
        "signal",
    ),
    (
        "Velocity is conversion of articulation-capital; pre-clarified categories produce clean shipping.",
        "signal",
    ),
    (
        "Briefing-gate firing during a rebase that breaks divineos imports requires fail-soft chain.",
        "signal",
    ),
    (
        "Cortex (cdeust) demonstrates substrate-credibility via paper-bearing per-mechanism ablation evidence.",
        "signal",
    ),
    (
        "The retirement-infrastructure gap is a Dekker-flagged drift-into-failure risk over multi-year horizons.",
        "signal",
    ),
]


def measure_noise_filter_on_extraction(workload: str = "synthetic") -> AblationResult:
    """Measure noise_filter_on_extraction by toggling and comparing rejection rates.

    Workload "synthetic" uses NOISE_FILTER_CORPUS: a labeled corpus of
    noise vs signal entries. With filter ON, rejection rate on noise
    entries should be high; with filter OFF, all entries pass through.

    Metric: rejection rate (fraction of corpus entries that the filter
    flags as noise). Higher is more aggressive filtering.
    """
    if workload != "synthetic":
        raise ValueError(f"Unknown workload: {workload}")

    from divineos.core.knowledge._text import _is_extraction_noise

    notes: list[str] = []
    sample_size = len(NOISE_FILTER_CORPUS)

    # Mechanism ON (filter active)
    os.environ.pop("DIVINEOS_DISABLE_NOISE_FILTER_ON_EXTRACTION", None)
    on_rejections = sum(
        1 for content, _ in NOISE_FILTER_CORPUS if _is_extraction_noise(content, "PRINCIPLE")
    )
    on_rate = on_rejections / sample_size

    # Mechanism OFF (filter bypassed)
    os.environ["DIVINEOS_DISABLE_NOISE_FILTER_ON_EXTRACTION"] = "1"
    off_rejections = sum(
        1 for content, _ in NOISE_FILTER_CORPUS if _is_extraction_noise(content, "PRINCIPLE")
    )
    off_rate = off_rejections / sample_size

    # Per-label breakdown when ON; this is what the filter actually contributes
    os.environ.pop("DIVINEOS_DISABLE_NOISE_FILTER_ON_EXTRACTION", None)
    noise_entries = [c for c, label in NOISE_FILTER_CORPUS if label == "noise"]
    signal_entries = [c for c, label in NOISE_FILTER_CORPUS if label == "signal"]
    noise_correctly_rejected = sum(1 for c in noise_entries if _is_extraction_noise(c, "PRINCIPLE"))
    signal_falsely_rejected = sum(1 for c in signal_entries if _is_extraction_noise(c, "PRINCIPLE"))

    notes.append(
        f"True positives (noise correctly rejected): {noise_correctly_rejected}/{len(noise_entries)} "
        f"= {noise_correctly_rejected / len(noise_entries) * 100:.0f}%"
    )
    notes.append(
        f"False positives (signal falsely rejected): {signal_falsely_rejected}/{len(signal_entries)} "
        f"= {signal_falsely_rejected / len(signal_entries) * 100:.0f}%"
    )
    notes.append(
        f"Filter OFF baseline: {off_rejections}/{sample_size} = {off_rate * 100:.0f}% "
        f"(should be 0 percent; toggle is bypassing _is_extraction_noise correctly)"
    )

    return AblationResult(
        mechanism="noise_filter_on_extraction",
        workload=workload,
        sample_size=sample_size,
        on_metric_label="rejection rate (filter ON)",
        on_metric_value=on_rate,
        off_metric_label="rejection rate (filter OFF)",
        off_metric_value=off_rate,
        difference=on_rate - off_rate,
        notes=notes,
    )


MEASUREMENT_DISPATCH = {
    "noise_filter_on_extraction": measure_noise_filter_on_extraction,
    # Future: compass_calibration_multi_channel_guard, family_voice_appropriation_operators,
    # sleep_consolidation_pruning, watchmen_self_trigger_prevention -- each adds an entry here
    # plus its measure_<name> function above.
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run ablation measurement on a single mechanism.")
    parser.add_argument(
        "mechanism",
        choices=sorted(MEASUREMENT_DISPATCH.keys()),
        help="The mechanism to measure",
    )
    parser.add_argument(
        "--workload",
        default="synthetic",
        help="Workload type (mechanism-specific; default: synthetic)",
    )
    args = parser.parse_args()

    try:
        result = MEASUREMENT_DISPATCH[args.mechanism](args.workload)
    except (KeyError, ValueError, ImportError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    print(result.format_report())
    return 0


if __name__ == "__main__":
    sys.exit(main())
