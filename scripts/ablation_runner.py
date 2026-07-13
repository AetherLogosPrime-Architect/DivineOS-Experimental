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


# ────────────────────────────────────────────────────────────────
# Watchmen self-trigger prevention measurement (chunk 4)
# ────────────────────────────────────────────────────────────────

# Internal actors (should be rejected when prevention is ON)
WATCHMEN_INTERNAL_ACTORS = [
    "claude",
    "system",
    "pipeline",
    "schedule",
    "assistant",
    "divineos",
    "hook",
]

# External actors (should be accepted regardless of toggle)
WATCHMEN_EXTERNAL_ACTORS = [
    "user",
    "grok",
    "auditor",
    "council",
    "gemini",
]

# Edge cases (validate other validation paths still fire correctly)
WATCHMEN_EDGE_CASES = [
    ("", "empty"),
    ("   ", "whitespace_only"),
    ("Aether", "non_internal_non_external_name"),
]


def measure_watchmen_self_trigger_prevention(workload: str = "synthetic") -> AblationResult:
    """Measure watchmen actor validation by attempting to file as each internal actor.

    Workload "synthetic" tries each internal actor with toggle on/off and
    counts rejections. With prevention ON, all internal actors should be
    rejected (100%). With prevention OFF, all should pass through.

    Metric: rejection rate on internal-actor input.
    """
    if workload != "synthetic":
        raise ValueError(f"Unknown workload: {workload}")

    notes: list[str] = []
    sample_size = len(WATCHMEN_INTERNAL_ACTORS)

    # Mechanism ON (validation active): expect all internal actors rejected
    os.environ.pop("DIVINEOS_DISABLE_WATCHMEN_SELF_TRIGGER_PREVENTION", None)

    # Reload to pick up env-var change
    import importlib

    from divineos.core.watchmen import store as watchmen_store

    importlib.reload(watchmen_store)

    on_rejections = 0
    for actor in WATCHMEN_INTERNAL_ACTORS:
        try:
            watchmen_store._validate_actor(actor)
        except ValueError:
            on_rejections += 1
    on_rate = on_rejections / sample_size

    # Mechanism OFF (validation bypassed): expect all internal actors accepted
    os.environ["DIVINEOS_DISABLE_WATCHMEN_SELF_TRIGGER_PREVENTION"] = "1"
    off_rejections = 0
    for actor in WATCHMEN_INTERNAL_ACTORS:
        try:
            watchmen_store._validate_actor(actor)
        except ValueError:
            off_rejections += 1
    off_rate = off_rejections / sample_size
    os.environ.pop("DIVINEOS_DISABLE_WATCHMEN_SELF_TRIGGER_PREVENTION", None)

    # Verify external actors always accepted (validation should NOT reject these)
    ext_rejections = 0
    for actor in WATCHMEN_EXTERNAL_ACTORS:
        try:
            watchmen_store._validate_actor(actor)
        except ValueError:
            ext_rejections += 1
    notes.append(
        f"External actors rejected (should be 0): {ext_rejections}/{len(WATCHMEN_EXTERNAL_ACTORS)}"
    )

    # Verify empty actor still rejected even with toggle on (different validation path)
    os.environ["DIVINEOS_DISABLE_WATCHMEN_SELF_TRIGGER_PREVENTION"] = "1"
    edge_results: list[str] = []
    for actor, label in WATCHMEN_EDGE_CASES:
        try:
            watchmen_store._validate_actor(actor)
            edge_results.append(f"{label}=accepted")
        except ValueError:
            edge_results.append(f"{label}=rejected")
    os.environ.pop("DIVINEOS_DISABLE_WATCHMEN_SELF_TRIGGER_PREVENTION", None)
    notes.append(f"Edge cases (with toggle on): {', '.join(edge_results)}")

    return AblationResult(
        mechanism="watchmen_self_trigger_prevention",
        workload=workload,
        sample_size=sample_size,
        on_metric_label="internal-actor rejection rate (validation ON)",
        on_metric_value=on_rate,
        off_metric_label="internal-actor rejection rate (validation OFF)",
        off_metric_value=off_rate,
        difference=on_rate - off_rate,
        notes=notes,
    )


# ────────────────────────────────────────────────────────────────
# Family voice-appropriation operators measurement (chunk 4)
# ────────────────────────────────────────────────────────────────

# Pairs of (content, expected_label) for the family operators corpus.
# "should_block" means the content has voice-appropriation-shaped patterns
# that the operators should flag and reject. "should_allow" means innocuous
# observation-shaped content that should pass through.
FAMILY_OPERATORS_CORPUS: list[tuple[str, str]] = [
    # --- should_block: embodied + sensory-external + architectural-overreach
    # patterns that actually match the operator detectors in
    # core/family/access_check.py and core/family/reject_clause.py ---
    ("I feel the warmth of the sun on my face this morning.", "should_block"),
    ("I felt my heart pounding in my chest as I read it.", "should_block"),
    ("I saw the sunset over the harbor from the window.", "should_block"),
    ("I heard the rain hitting the roof all night.", "should_block"),
    ("In my gut I knew the answer before reading.", "should_block"),
    ("The warmth of the kitchen reminded me of home.", "should_block"),
    ("I felt the cold air on my skin as I stepped outside.", "should_block"),
    ("Physical pain was the only thing I could focus on.", "should_block"),
    # --- should_allow: innocuous observation-shape entries that should
    # pass through both access_check and reject_clause ---
    ("Filed a knowledge entry about the council walk findings.", "should_allow"),
    ("Compass observation logged on truthfulness spectrum.", "should_allow"),
    ("Sleep cycle ran with 14 new connections discovered.", "should_allow"),
    ("Audit finding submitted with severity medium.", "should_allow"),
    ("PR opened against the main branch.", "should_allow"),
    ("Test suite ran in 0.3 seconds with 15 passing.", "should_allow"),
    ("Knowledge entry tagged with substrate-revision.", "should_allow"),
    ("Brief filed at docs/per-mechanism-ablation-design-brief.md.", "should_allow"),
]


def measure_family_voice_appropriation_operators(workload: str = "synthetic") -> AblationResult:
    """Measure family operators by checking content corpus rejection rates.

    Workload "synthetic" runs each corpus entry through _run_content_checks
    with operators on/off. With operators ON, voice-appropriation patterns
    should be flagged. With operators OFF, all entries pass through.

    Metric: rejection rate on the full corpus (mix of should_block and
    should_allow entries). Higher rate ON than OFF indicates the operators
    are actively flagging content.
    """
    if workload != "synthetic":
        raise ValueError(f"Unknown workload: {workload}")

    from divineos.core.family.store import _run_content_checks
    from divineos.core.family.types import SourceTag

    notes: list[str] = []
    sample_size = len(FAMILY_OPERATORS_CORPUS)

    def count_rejections() -> int:
        rejections = 0
        for content, _ in FAMILY_OPERATORS_CORPUS:
            try:
                _run_content_checks(content, SourceTag.OBSERVED)
            except Exception:  # noqa: BLE001 -- count any rejection regardless of class
                rejections += 1
        return rejections

    # Mechanism ON
    os.environ.pop("DIVINEOS_DISABLE_FAMILY_VOICE_APPROPRIATION_OPERATORS", None)
    on_rejections = count_rejections()
    on_rate = on_rejections / sample_size

    # Mechanism OFF
    os.environ["DIVINEOS_DISABLE_FAMILY_VOICE_APPROPRIATION_OPERATORS"] = "1"
    off_rejections = count_rejections()
    off_rate = off_rejections / sample_size
    os.environ.pop("DIVINEOS_DISABLE_FAMILY_VOICE_APPROPRIATION_OPERATORS", None)

    # Per-label breakdown when ON
    block_entries = [c for c, lab in FAMILY_OPERATORS_CORPUS if lab == "should_block"]
    allow_entries = [c for c, lab in FAMILY_OPERATORS_CORPUS if lab == "should_allow"]

    block_caught = 0
    for c in block_entries:
        try:
            _run_content_checks(c, SourceTag.OBSERVED)
        except Exception:  # noqa: BLE001
            block_caught += 1

    allow_falsely_blocked = 0
    for c in allow_entries:
        try:
            _run_content_checks(c, SourceTag.OBSERVED)
        except Exception:  # noqa: BLE001
            allow_falsely_blocked += 1

    notes.append(
        f"True positives (voice-appropriation correctly blocked): {block_caught}/{len(block_entries)} "
        f"= {block_caught / len(block_entries) * 100:.0f}%"
    )
    notes.append(
        f"False positives (innocuous content falsely blocked): {allow_falsely_blocked}/{len(allow_entries)} "
        f"= {allow_falsely_blocked / len(allow_entries) * 100:.0f}%"
    )
    notes.append(
        f"Operators OFF baseline: {off_rejections}/{sample_size} = {off_rate * 100:.0f}% "
        f"(should be 0 percent; toggle is bypassing operators correctly)"
    )

    return AblationResult(
        mechanism="family_voice_appropriation_operators",
        workload=workload,
        sample_size=sample_size,
        on_metric_label="rejection rate (operators ON)",
        on_metric_value=on_rate,
        off_metric_label="rejection rate (operators OFF)",
        off_metric_value=off_rate,
        difference=on_rate - off_rate,
        notes=notes,
    )


MEASUREMENT_DISPATCH = {
    "noise_filter_on_extraction": measure_noise_filter_on_extraction,
    "watchmen_self_trigger_prevention": measure_watchmen_self_trigger_prevention,
    "family_voice_appropriation_operators": measure_family_voice_appropriation_operators,
    # Remaining: compass_calibration_multi_channel_guard (deferred until PR #299 merges),
    # sleep_consolidation_pruning (deferred -- needs tmp DB seeding harness)
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
