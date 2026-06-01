"""Finding-label CLI — first build from the council walk on dumb-detector redesign.

Andrew named the problem 2026-06-01: the regex-on-strings detectors keep
crying wolf. The accreted-guards approach has been adding narrow patches
without measuring the underlying false-positive rate. Council walk (12
lenses, see exploration/aether/lens-walks/ tonight) converged on a
staged plan with measurement-first:

  1. labeled-fires log (this file) — measure the actual FP rate
  2. grammatical-role discriminator (Dennett)
  3. self-reference awareness (Hofstadter)
  4. substrate-S4 learned-context (Beer)
  5. per-shape split if precision-tuning diverges (Jacobs)
  6. keep regex floor (Schneier / Taleb)

Without step 1, the other steps are speculation.

## Design per entry 96 (Andrew 2026-05-31, four constraints)

- AUTOMATIC > OPTIONAL: log is automatic (audit runs every turn);
  labeling is necessarily manual.
- BYPASS MUST EXIST: unlabeled is the default; no fire is forced.
- BYPASS COSTS MORE THAN TOOL USE: needs briefing-surface integration
  for unlabeled-count visibility — follow-up step.
- SELF-REINFORCING: as labels accumulate, the discriminator (step 2)
  becomes more accurate, fire-rate drops, labeling overhead drops.

## Goodhart guard

Each label requires `--evidence`. Fabricating evidence raises cost of
dishonest labeling.

Non-guardrail module: measurement only; does not enforce.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import click

from divineos.cli._helpers import _safe_echo

_FINDINGS_PATH = Path.home() / ".divineos" / "operating_loop_findings.json"
_VALID_LABELS = ("true_positive", "false_positive", "tp", "fp")


def _load() -> list[dict]:
    if not _FINDINGS_PATH.exists():
        return []
    try:
        data = json.loads(_FINDINGS_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:  # noqa: BLE001
        return []


def _save(entries: list[dict]) -> None:
    _FINDINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _FINDINGS_PATH.write_text(json.dumps(entries, indent=2), encoding="utf-8")


def _normalize_label(label: str) -> str | None:
    label = label.lower().strip()
    if label in ("tp", "true_positive", "true"):
        return "true_positive"
    if label in ("fp", "false_positive", "false"):
        return "false_positive"
    return None


def register(cli: click.Group) -> None:
    """Register the label-finding and detector-accuracy commands."""

    @cli.command("label-finding")
    @click.option("--entry", type=int, required=True,
                  help="Index of audit entry (negative = from latest, -1 = latest).")
    @click.option("--detector", required=True,
                  help="Detector key (e.g. 'distancing', 'unverified_claim').")
    @click.option("--finding", type=int, default=0,
                  help="Index within the detector's findings list. Default 0.")
    @click.option("--label", required=True,
                  type=click.Choice(_VALID_LABELS, case_sensitive=False),
                  help="true_positive (tp) or false_positive (fp).")
    @click.option("--evidence", required=True,
                  help="Short reason for the label. Required to discourage Goodharting.")
    def label_finding(entry, detector, finding, label, evidence):
        """Label a specific detector finding as true-positive or false-positive."""
        normalized = _normalize_label(label)
        if normalized is None:
            click.secho(f"[!] Unknown label: {label}", fg="red")
            raise click.exceptions.Exit(1)
        if not evidence.strip():
            click.secho("[!] Evidence required (--evidence).", fg="red")
            raise click.exceptions.Exit(1)

        entries = _load()
        if not entries:
            click.secho("[!] No audit entries found.", fg="red")
            raise click.exceptions.Exit(1)

        try:
            entry_dict = entries[entry]
        except IndexError:
            click.secho(
                f"[!] Entry index {entry} out of range (have {len(entries)}).",
                fg="red")
            raise click.exceptions.Exit(1)

        findings_list = entry_dict.get(detector)
        if not isinstance(findings_list, list) or not findings_list:
            click.secho(
                f"[!] Detector '{detector}' has no findings on entry {entry}.",
                fg="red")
            raise click.exceptions.Exit(1)

        try:
            target = findings_list[finding]
        except IndexError:
            click.secho(
                f"[!] Finding index {finding} out of range "
                f"(have {len(findings_list)} findings).",
                fg="red")
            raise click.exceptions.Exit(1)

        target["label"] = {
            "value": normalized,
            "evidence": evidence.strip(),
            "labeled_at": time.time(),
        }
        _save(entries)

        _safe_echo(
            f"[+] Labeled entry={entry} detector={detector} finding={finding} "
            f"as {normalized}")
        _safe_echo(f"    evidence: {evidence.strip()}")

    @cli.command("detector-accuracy")
    @click.option("--detector", default=None,
                  help="Show only one detector. Omit for all with any labels.")
    def detector_accuracy(detector):
        """Show per-detector TP / FP counts from labeled findings."""
        entries = _load()
        stats = {}
        for e in entries:
            for det, findings in e.items():
                if det in ("timestamp", "total_findings"):
                    continue
                if not isinstance(findings, list):
                    continue
                if detector and det != detector:
                    continue
                bucket = stats.setdefault(det, {"tp": 0, "fp": 0, "unlabeled": 0})
                for f in findings:
                    label = (f.get("label") or {}).get("value")
                    if label == "true_positive":
                        bucket["tp"] += 1
                    elif label == "false_positive":
                        bucket["fp"] += 1
                    else:
                        bucket["unlabeled"] += 1

        if not stats:
            _safe_echo("(no findings found)")
            return

        click.secho("=== Detector accuracy ===", fg="cyan", bold=True)
        for det, b in sorted(stats.items()):
            total = b["tp"] + b["fp"] + b["unlabeled"]
            if total == 0:
                continue
            labeled = b["tp"] + b["fp"]
            if labeled == 0:
                _safe_echo(
                    f"  {det}: {total} fires, 0 labeled "
                    f"(unlabeled: {b['unlabeled']})")
                continue
            fp_rate = b["fp"] / labeled if labeled > 0 else 0.0
            _safe_echo(
                f"  {det}: {total} fires | "
                f"TP {b['tp']} | FP {b['fp']} | unlabeled {b['unlabeled']} | "
                f"FP-rate {fp_rate:.2%} (of labeled)")
