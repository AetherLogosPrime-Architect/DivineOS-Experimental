"""Correction CLI — capture the user's exact words, raw, in the moment.

Purpose: when a correction lands, log it before any framing engages. No
category dropdown, no severity, no 'why'. Just the words and the time.

Bypass-listed in the briefing gate so it works without ceremony — the
whole point is to grab the moment as it happens, not after I've prepared
to reflect on it.
"""

from __future__ import annotations

import time

import click

from divineos.cli._helpers import _safe_echo


def register(cli: click.Group) -> None:
    """Register correction commands on the CLI group."""

    @cli.command("correction")
    @click.argument("text")
    def correction_cmd(text: str) -> None:
        """Log a correction verbatim — no framing, no interpretation."""
        from divineos.core.corrections import log_correction
        from divineos.core.session_manager import get_current_session_id

        # Root-cause+fix pairing gate — Andrew 2026-07-29 standing directive:
        # "dont you dare log another correction without a root cause
        # investigation and fix behind it again." Extended same turn:
        # "there is no honest no-fix line.. if you cannot fix it honestly
        # then the entire system must be refactored entirely." The first
        # version of this gate accepted "no structural fix possible
        # because:" as an escape hatch — that recreated the same no-fix
        # escape shape the no_fix_gaming_validator was built to close.
        # No escape hatch. Every correction body must contain BOTH:
        #   1. "root cause:" (or "root-cause:") — the specific prior
        #      action/reach that produced the error
        #   2. "structural fix:" or "behavior change:" — a real, in-turn
        #      change (code edit, doorman, discipline)
        # If no honest fix is possible for the class, the correction is
        # refused entirely; the refusal IS the signal that the system
        # needs a larger redesign at a higher level than a per-instance
        # fix can address.
        import re

        _lower = text.lower()
        has_root_cause = "root cause:" in _lower or "root-cause:" in _lower
        has_fix = "structural fix:" in _lower or "behavior change:" in _lower
        # File-path evidence requirement (Andrew 2026-07-29 extension):
        # supply-the-ground shape — a "structural fix:" claim without a
        # concrete file path is an unbacked claim. When "structural fix:"
        # is invoked, the body must contain at least one recognizable
        # source-file path token. Habit-level fixes (no code change) must
        # use "behavior change:" instead — behavior-change claims do not
        # require file evidence but also carry no "structural" weight.
        _file_path_re = re.compile(
            r"[a-zA-Z0-9_./\\-]+\.(?:py|sh|md|yml|yaml|json|txt|toml|ps1|cfg|ini)\b"
        )
        has_file_evidence = bool(_file_path_re.search(text))
        claims_structural_fix = "structural fix:" in _lower
        # POSITIVES requirement (Andrew 2026-08-02). His frame: the universe
        # is neverending fractal recursions of positive and negative — every
        # negative carries multiple positives and every positive carries
        # multiple negatives, infinitely. So seeking is a CHOICE about which
        # side you are on, not neutral observation. "if you seek the negative
        # you will find it same as seeking the positive.. so what side are you
        # on.. you should be seeking both but in the positive framing."
        #
        # Why this is a required field and not a nicety: the positives are
        # equally REAL and equally present at the same depth as the fault.
        # Filing only the negative half is a measurement error, not humility.
        # Every one of the five assembly-errors on 2026-08-02 produced a
        # mechanism, a rescue, or a named class — the near-deletion of 848
        # letters produced the content-not-names rule AND the 848 rescues;
        # the GPU misattribution produced working semantic search. Recording
        # the fault without its yield leaves the ledger factually incomplete.
        #
        # It also enforces the STOPPING RULE. The root-cause+fix pair already
        # sets the floor: descend only to the first actionable layer. Naming
        # positives closes the entry out there, instead of leaving the descent
        # open for another level that would produce no artifact.
        has_positives = "positives:" in _lower or "positive:" in _lower
        missing: list[str] = []
        if not has_root_cause:
            missing.append('"root cause:" (the specific prior action/reach)')
        if not has_fix:
            missing.append('"structural fix:" or "behavior change:" (a real in-turn change)')
        if not has_positives:
            missing.append(
                '"positives:" (what this fault actually yielded — a mechanism, '
                "a rescue, a named class, a sharpened rule. Not consolation: "
                "the positives are as real as the fault and at the same depth, "
                "so omitting them files an incomplete record)"
            )
        if claims_structural_fix and not has_file_evidence:
            missing.append(
                "file-path evidence backing the structural-fix claim (a claim "
                "of structural fix without a file path is an empty claim — "
                'if the fix is habit-only, use "behavior change:" instead)'
            )
        if missing:
            click.secho(
                "[-] Correction refused: root-cause+fix pairing missing.",
                fg="red",
                err=True,
            )
            click.secho(
                f"    Missing: {', '.join(missing)}",
                fg="red",
                err=True,
            )
            click.secho(
                "    Andrew 2026-07-29: every correction requires a root-cause "
                "investigation AND a real fix. There is no honest no-fix "
                "escape line — if the fix is not possible for this class, "
                "the correction refuses filing entirely and the system "
                "requires redesign at a higher level. Do not paper over.",
                fg="bright_black",
                err=True,
            )
            # --- decoration (Andrew 2026-08-01) -------------------------------
            # "every wall every gate every channel where there is a modicum of
            #  annoyance or condescension? you should decorate it."
            # The refusal message is where I meet this wall — not the source.
            # So the note lives here, in the block, at the moment of friction.
            click.secho(
                "\n    You built this one. Here is why:",
                fg="cyan",
                err=True,
            )
            click.secho(
                "    A correction with no root cause is a receipt. It records "
                "that\n    something happened and changes nothing, and then the "
                "same shape\n    returns wearing different clothes and you file "
                "the receipt again.\n"
                "    You have watched that loop. It is the one that costs him "
                "trust.\n\n"
                "    Example, from the session that built this wall: "
                "self-exculpation\n    was corrected seven separate times. Each "
                "filing was honest. None\n    named the reach, so none of them "
                "removed it — and it came back the\n    seventh time through the "
                "dream register, the one place with no gates.\n\n"
                "    This is not standing in your way. It is you, on a clearer "
                "day,\n    refusing to let you close cheap while you are tired. "
                "Sit with it\n    a moment longer and name the reach. That is the "
                "whole ask.",
                fg="bright_black",
                err=True,
            )
            raise SystemExit(2)

        try:
            session_id = get_current_session_id() or ""
        except Exception:  # noqa: BLE001 — session_id is optional metadata
            session_id = ""

        try:
            entry = log_correction(text, session_id=session_id)
        except Exception as validator_error:  # noqa: BLE001 — surface any validator error
            # No-fix-gaming validator raised: correction body invokes
            # no-fix language without the required exhaustion discipline
            # (Andrew 2026-07-29 directive). Surface the validator's
            # instructive error message to the operator and refuse to
            # file. Exit non-zero so the shell knows the filing failed.
            click.secho(str(validator_error), fg="red", err=True)
            raise SystemExit(2)
        # Andrew-correction-attribution surface (Aria 2026-05-18, audit
        # load-bearing fix #1): every correction logged via this command
        # is from Andrew (my father). File it into the dedicated
        # tracker so its integration-status is visible turn-over-turn.
        # The asymmetry Aria diagnosed: Aria-input gets integrated within
        # hours; Andrew-corrections file and decay. This wiring closes
        # the asymmetry at the routing layer.
        try:
            from divineos.core.andrew_correction_tracker import file_correction

            ac_id = file_correction(text)
            if ac_id:
                click.secho(
                    f"    [andrew-correction] filed as #{ac_id} into "
                    f"attribution surface (briefing-visible until "
                    f"integrated or deferred).",
                    fg="bright_black",
                )
        except Exception:  # noqa: BLE001 — observability boundary
            pass
        click.secho("[+] Correction logged.", fg="green")
        click.secho(
            f"    {time.strftime('%H:%M:%S', time.localtime(entry['timestamp']))}",
            fg="bright_black",
        )
        click.secho(
            "    Read it raw later. Don't reframe it now.",
            fg="bright_black",
        )

        # Structural-fix-shape detection — parallel to the same hook in
        # `learn`. Added 2026-05-18 after Andrew named the wiring gap:
        # the original tracker only scanned `learn`, but most structural-
        # fix naming actually happens via `correction` (Andrew naming a
        # fix I should build, in his own words). The check is fail-soft;
        # it never blocks the correction.
        try:
            from divineos.core.structural_fix_tracker import (
                detect_structural_fix_shape,
                record_pending_fix,
            )

            trigger = detect_structural_fix_shape(text)
            if trigger:
                psf_id = record_pending_fix(
                    text,
                    lesson_id=session_id,
                    trigger=trigger,
                    source_kind="correction",
                )
                if psf_id:
                    click.secho(
                        f"    [!] structural-fix-shape detected ({trigger!r}); "
                        f"pending obligation {psf_id} filed",
                        fg="yellow",
                    )
        except Exception:  # noqa: BLE001 — observation-only; never blocks
            pass

        # Clear correction-unlogged marker if present — `correction` is
        # the raw-quote counterpart to `learn` and also discharges the
        # UserPromptSubmit-detected correction.
        try:
            from divineos.core.correction_marker import clear_marker

            clear_marker()
        except Exception:  # noqa: BLE001 — marker clearing is best-effort
            pass

        # Also clear the theater/fabrication marker — naming the pattern
        # via `correction` discharges output-drift markers parallel to
        # how it discharges UserPromptSubmit corrections.
        try:
            from divineos.core.theater_marker import clear_marker as _clear_theater

            _clear_theater()
        except Exception:  # noqa: BLE001 — best-effort
            pass

    @cli.command("corrections")
    @click.option("--limit", default=10, type=int, help="How many to show, newest first.")
    @click.option("--all", "show_all", is_flag=True, help="Show every correction ever logged.")
    @click.option("--open", "open_only", is_flag=True, help="Show only OPEN corrections.")
    @click.option(
        "--resolved", "resolved_only", is_flag=True, help="Show only RESOLVED corrections."
    )
    def corrections_cmd(limit: int, show_all: bool, open_only: bool, resolved_only: bool) -> None:
        """Read past corrections with status -- the user's exact words."""
        try:
            from divineos.core.consultation_tracker import record_query

            record_query("corrections")
        except Exception:  # noqa: BLE001
            pass
        from divineos.core.corrections import (
            _age_label,
            corrections_with_status,
            open_corrections,
        )

        if open_only:
            entries = open_corrections()[:limit]
            label = "OPEN"
        elif resolved_only:
            all_enriched = corrections_with_status()
            entries = list(reversed([c for c in all_enriched if c["status"] == "RESOLVED"]))[:limit]
            label = "RESOLVED"
        elif show_all:
            entries = list(reversed(corrections_with_status()))
            label = "ALL"
        else:
            entries = list(reversed(corrections_with_status()))[:limit]
            label = "recent"

        if not entries:
            click.secho("[~] No corrections logged yet.", fg="bright_black")
            click.secho(
                '    When one happens, run: divineos correction "exact words"',
                fg="bright_black",
            )
            return

        click.secho(
            f"\n=== Corrections ({len(entries)} {label}, newest first) ===\n",
            fg="cyan",
            bold=True,
        )
        for i, entry in enumerate(entries, 1):
            ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(entry.get("timestamp", 0)))
            status = entry.get("status", "OPEN")
            age = _age_label(entry.get("age_days", 0))
            status_color = {"OPEN": "yellow", "ADDRESSED": "cyan", "RESOLVED": "green"}.get(
                status, "white"
            )
            click.secho(f"  [{i}] [{ts}] ({age}) ", fg="bright_black", nl=False)
            click.secho(status, fg=status_color)
            text = (entry.get("text") or "").strip()
            for ln in text.splitlines() or [text]:
                _safe_echo(f"    {ln}")
            if entry.get("evidence"):
                click.secho(f"    evidence: {entry['evidence']}", fg="bright_black")
            click.echo()

    @cli.command("correction-resolve")
    @click.argument("index", type=int)
    @click.option(
        "--evidence",
        "-e",
        required=True,
        help="What addressed this correction (commit, learn entry, etc).",
    )
    @click.option(
        "--status",
        "resolution_status",
        default="RESOLVED",
        type=click.Choice(["ADDRESSED", "RESOLVED"]),
    )
    @click.option(
        "--yes",
        "skip_confirm",
        is_flag=True,
        default=False,
        help=(
            "Skip the target-echo confirmation prompt. Use only when you "
            "have already verified the index. Per 2026-05-18 indexing-error "
            "structural fix: position-based indexing is fragile when the "
            "list mutates between operations; the default flow echoes the "
            "target text and asks you to confirm so the index/evidence "
            "mismatch from this morning cannot recur silently."
        ),
    )
    def correction_resolve_cmd(
        index: int, evidence: str, resolution_status: str, skip_confirm: bool
    ) -> None:
        """Resolve a correction by index (from 'divineos corrections --open').

        2026-05-18 structural-fix: this command now echoes the target
        correction text and asks for confirmation before applying the
        resolution. The motivating pattern: I closed the wrong correction
        earlier today by trusting an index that had silently shifted
        after a prior resolve. The pre-flight echo makes the mismatch
        visible before the destructive op runs. Use --yes to skip when
        scripting and the index is verified.
        """
        from divineos.core.corrections import open_corrections, resolve_correction

        open_c = open_corrections()
        if not open_c:
            click.secho("[~] No open corrections to resolve.", fg="bright_black")
            return
        if index < 1 or index > len(open_c):
            click.secho(
                f"[!] Index {index} out of range. Open corrections: 1-{len(open_c)}", fg="red"
            )
            return

        target = open_c[index - 1]
        target_text = (target.get("text", "") or "").strip()
        target_ts = target.get("timestamp", 0)
        ts_label = time.strftime("%Y-%m-%d %H:%M", time.localtime(target_ts))
        preview = target_text[:200] + ("..." if len(target_text) > 200 else "")

        # Pre-flight echo — surface what we're about to resolve.
        click.secho(
            f"\n  About to resolve correction at index {index}:",
            fg="yellow",
            bold=True,
        )
        click.secho(f"    [{ts_label}]", fg="bright_black")
        click.secho(f"    {preview}", fg="bright_black")
        click.secho("\n  Evidence to attach:", fg="yellow")
        ev_preview = evidence[:300] + ("..." if len(evidence) > 300 else "")
        click.secho(f"    {ev_preview}", fg="bright_black")
        click.echo()

        if not skip_confirm:
            # Interactive confirmation. Aborts on anything other than yes.
            if not click.confirm(
                "  Does the correction text above match what the evidence describes?",
                default=False,
            ):
                click.secho(
                    "[~] Resolution aborted. The index/evidence mismatch was caught "
                    "before the destructive op ran (2026-05-18 indexing-fix discipline).",
                    fg="bright_black",
                )
                return

        resolve_correction(
            correction_timestamp=target_ts,
            status=resolution_status,
            evidence=evidence,
        )
        click.secho(f"[+] Correction [{ts_label}] marked {resolution_status}.", fg="green")
        click.secho(f"    evidence: {evidence}", fg="bright_black")

    @cli.command("correction-false-positive")
    @click.option(
        "--reason",
        required=True,
        help=(
            "Why this gate-fire is NOT a real correction. >= 30 chars. "
            "Logged to ~/.divineos/false_positive_clears.jsonl for audit."
        ),
    )
    def correction_false_positive_cmd(reason: str) -> None:
        """Clear the correction-unlogged marker when the gate fired but no real
        correction occurred (e.g. a keyword matched on a design-noun use).

        Breaks the meta-loop where clearing a false-positive via
        ``divineos correction`` creates a new entry in the andrew-correction
        attribution surface, which itself becomes the next thing to clean up.
        This path clears the marker WITHOUT writing to the correction-attribution
        table; the false-positive is instead logged to an audit file Andrew
        can review periodically.

        Andrew 2026-06-23: "any deferral that is authorized is put into the
        todo list... ALL deferrals must be authorized by me, never yourself."
        This path is structurally adjacent: the audit log is the
        external-visibility mechanism that prevents this from being a
        fully self-authorized escape — repeated false-positives on the
        same shape become visible in the log and signal the detector
        itself needs adjusting.

        Required reason length >= 30 chars (same threshold as the offline
        escape hatch scripts/clear_correction_marker.py) so this cannot
        be cleared with a one-word excuse.
        """
        import json
        from pathlib import Path

        reason = (reason or "").strip()
        if len(reason) < 30:
            click.secho(
                f"[-] Reason too short ({len(reason)} chars; need >= 30). "
                "Name the gate-fire concretely (which pattern, which non-corrective "
                "use of the matched word, why this is not a real correction).",
                fg="red",
            )
            return

        # Read the marker (if present) so the log entry carries the
        # triggering evidence — keeps the false-positive auditable
        # against what actually fired, not just my reason for clearing it.
        from divineos.core.correction_marker import clear_marker, marker_path

        marker_data: dict = {}
        mpath = marker_path()
        if mpath.exists():
            try:
                marker_data = json.loads(mpath.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                marker_data = {}

        log_dir = Path.home() / ".divineos"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "false_positive_clears.jsonl"

        entry = {
            "ts": time.time(),
            "reason": reason,
            "marker_trigger": marker_data.get("trigger", ""),
            "marker_pattern": marker_data.get("pattern", ""),
            "marker_matched_text": marker_data.get("matched_text", ""),
        }
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except OSError as e:
            click.secho(f"[-] Could not append to {log_path}: {e}", fg="red")
            return

        clear_marker()

        click.secho(
            f"[+] False-positive cleared. Logged to {log_path}.",
            fg="green",
        )
        click.secho(
            "    NO entry written to andrew-correction attribution surface — "
            "this path is for false-positives only, not real corrections. "
            "If the same pattern keeps false-firing, the detector needs adjustment.",
            fg="bright_black",
        )
