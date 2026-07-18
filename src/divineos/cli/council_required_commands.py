"""CLI surface for the council-required enforcement gate.

Subcommands of ``divineos council``:

- ``log``: write a council walk record (substance-binding runs at log-
  time; rejected walks emit a COUNCIL_WALK_REJECTED event rather than a
  successful record).
- ``show``: display a recorded walk.
- ``recent``: list recent council records, optionally filtered by edit
  fingerprint.
- ``emergency-skip``: invoke the corroborator-required emergency
  carve-out for one edit.

The CLI is thin — all logic lives in ``core/council_required/``. This
module's job is parsing arguments and rendering output for human and
test consumption.
"""

from __future__ import annotations

import json
import time

import click

from divineos.cli._helpers import _safe_echo
from divineos.core.council_required import gate as gate_mod
from divineos.core.council_required import store, substance_binding
from divineos.core.council_required.types import (
    EMERGENCY_CORROBORATOR_ACTORS,
    EMERGENCY_CORROBORATOR_EVENT_TYPES,
    CouncilRecord,
    LensFinding,
    _normalize_edit_fingerprint,
)


def _load_expert_keywords() -> dict[str, set[str]]:
    """Load every registered council expert's characteristic_questions
    and return the lens-keyword map.

    Imported lazily so the divineos CLI startup does not pay the full
    expert-library import cost unless a council command actually runs.
    """
    from divineos.core.council.experts import (
        create_angelou_wisdom,
        create_aristotle_wisdom,
        create_beer_wisdom,
        create_bengio_wisdom,
        create_carmack_wisdom,
        create_dawkins_wisdom,
        create_dekker_wisdom,
        create_deming_wisdom,
        create_dennett_wisdom,
        create_dijkstra_wisdom,
        create_dillahunty_wisdom,
        create_einstein_wisdom,
        create_feynman_wisdom,
        create_godel_wisdom,
        create_hawking_wisdom,
        create_hinton_wisdom,
        create_hofstadter_wisdom,
        create_holmes_wisdom,
        create_jacobs_wisdom,
        create_kahneman_wisdom,
        create_knuth_wisdom,
        create_lamport_wisdom,
        create_lovelace_wisdom,
        create_maturana_varela_wisdom,
        create_meadows_wisdom,
        create_minsky_wisdom,
        create_norman_wisdom,
        create_pearl_wisdom,
        create_peirce_wisdom,
        create_penrose_wisdom,
        create_polya_wisdom,
        create_popper_wisdom,
        create_sagan_wisdom,
        create_schneier_wisdom,
        create_shannon_wisdom,
        create_taleb_wisdom,
        create_tannen_wisdom,
        create_turing_wisdom,
        create_watts_wisdom,
        create_wayne_wisdom,
        create_wittgenstein_wisdom,
        create_yudkowsky_wisdom,
    )

    builders = [
        create_angelou_wisdom,
        create_aristotle_wisdom,
        create_beer_wisdom,
        create_bengio_wisdom,
        create_carmack_wisdom,
        create_dawkins_wisdom,
        create_dekker_wisdom,
        create_deming_wisdom,
        create_dennett_wisdom,
        create_dijkstra_wisdom,
        create_dillahunty_wisdom,
        create_einstein_wisdom,
        create_feynman_wisdom,
        create_godel_wisdom,
        create_hawking_wisdom,
        create_hinton_wisdom,
        create_hofstadter_wisdom,
        create_holmes_wisdom,
        create_jacobs_wisdom,
        create_kahneman_wisdom,
        create_knuth_wisdom,
        create_lamport_wisdom,
        create_lovelace_wisdom,
        create_maturana_varela_wisdom,
        create_meadows_wisdom,
        create_minsky_wisdom,
        create_norman_wisdom,
        create_pearl_wisdom,
        create_peirce_wisdom,
        create_penrose_wisdom,
        create_polya_wisdom,
        create_popper_wisdom,
        create_sagan_wisdom,
        create_schneier_wisdom,
        create_shannon_wisdom,
        create_taleb_wisdom,
        create_tannen_wisdom,
        create_turing_wisdom,
        create_watts_wisdom,
        create_wayne_wisdom,
        create_wittgenstein_wisdom,
        create_yudkowsky_wisdom,
    ]
    registry: dict[str, list[str]] = {}
    for build in builders:
        w = build()
        registry[w.expert_name] = list(w.characteristic_questions or [])
    return substance_binding.keywords_for_expert_registry(registry)


def _parse_findings(findings_arg: str) -> list[LensFinding]:
    """Parse the --finding argument format ``lens=text;lens=text;...``.

    Intentionally simple — JSON would be more robust but harder to type
    on the CLI. Semicolons separate lens-finding pairs; the first ``=``
    separates lens-name from finding-text. Whitespace around either
    side is stripped.
    """
    findings: list[LensFinding] = []
    if not findings_arg:
        return findings
    pairs = findings_arg.split(";")
    for pair in pairs:
        if "=" not in pair:
            continue
        lens, _, text = pair.partition("=")
        lens = lens.strip()
        text = text.strip()
        if lens and text:
            findings.append(LensFinding(lens_name=lens, finding_text=text))
    return findings


def register(cli: click.Group) -> None:
    """Register the divineos council subcommand group."""

    @cli.group("council")
    def council_group() -> None:
        """Council-required enforcement: log walks, view records, emergency-skip."""

    @council_group.command("log")
    @click.option("--edit", "edit_fp", required=True, help="Edit fingerprint (tool:path)")
    @click.option("--lenses", required=True, help="Comma-separated lens names surfaced")
    @click.option(
        "--finding",
        "findings_arg",
        required=True,
        help='Per-lens findings: "lens1=text;lens2=text;..."',
    )
    @click.option("--synthesis", required=True, help="Cross-lens integration text")
    @click.option(
        "--confirmed-by",
        default="",
        help="External actor (Andrew/Aletheia) — required for kiln-layer edits",
    )
    @click.option("--actor", default="agent", help="Walker identity")
    def cmd_log(
        edit_fp: str,
        lenses: str,
        findings_arg: str,
        synthesis: str,
        confirmed_by: str,
        actor: str,
    ) -> None:
        """Write a council walk record. Substance-binding runs at log-time;
        rejected walks emit a COUNCIL_WALK_REJECTED event rather than a
        successful record."""
        lens_names = tuple(name.strip() for name in lenses.split(",") if name.strip())
        findings = _parse_findings(findings_arg)
        record = CouncilRecord(
            record_id=store.new_record_id(),
            walked_at=time.time(),
            walker=actor,
            triggered_edit_fingerprint=edit_fp,
            lenses_surfaced=lens_names,
            lens_findings=tuple(findings),
            synthesis=synthesis,
            confirmed_by=confirmed_by or None,
        )
        keywords = _load_expert_keywords()
        # Kiln detection is best-effort here — the CLI does not have the
        # full gravity-classifier context. We accept the caller's
        # confirmed_by; the gate at PreToolUse re-checks against the
        # real classifier output.
        is_kiln = bool(confirmed_by)
        bind_result = substance_binding.substance_bind_record(
            record, is_kiln_layer=is_kiln, expert_keywords_for_lens=keywords
        )
        if not bind_result.passed:
            store.log_walk_rejection(record, bind_result, actor=actor)
            _safe_echo(f"[council] REJECTED: {bind_result.failed_check_name}")
            _safe_echo(f"  {bind_result.what_would_clear_it}")
            raise SystemExit(1)
        event_id = store.log_council_record(record, actor=actor)
        _safe_echo(f"[council] Recorded: {record.record_id}")
        _safe_echo(f"  ledger event_id: {event_id}")
        _safe_echo(f"  fingerprint: {edit_fp}")

    @council_group.command("show")
    @click.argument("record_id")
    def cmd_show(record_id: str) -> None:
        """Display a recorded walk by record_id."""
        from divineos.core import ledger
        from divineos.core.council_required.store import (
            EVENT_COUNCIL_RECORD_LOGGED,
            _payload_from_event,
        )

        events = ledger.get_events(limit=500, event_type=EVENT_COUNCIL_RECORD_LOGGED, order="desc")
        for ev in events:
            payload = _payload_from_event(ev)
            if str(payload.get("record_id", "")) == record_id:
                _safe_echo(json.dumps(payload, indent=2))
                return
        _safe_echo(f"[council] No record found with id {record_id!r}")
        raise SystemExit(1)

    @council_group.command("recent")
    @click.option("--for-edit", default="", help="Filter by edit fingerprint")
    @click.option("--limit", default=10, type=int)
    def cmd_recent(for_edit: str, limit: int) -> None:
        """List recent council records, optionally filtered by edit fingerprint."""
        from divineos.core import ledger
        from divineos.core.council_required.store import (
            EVENT_COUNCIL_RECORD_LOGGED,
            _payload_from_event,
        )

        events = ledger.get_events(
            limit=max(limit * 5, 50),
            event_type=EVENT_COUNCIL_RECORD_LOGGED,
            order="desc",
        )
        shown = 0
        for ev in events:
            if shown >= limit:
                break
            payload = _payload_from_event(ev)
            fp = str(payload.get("triggered_edit_fingerprint", ""))
            if for_edit and fp != for_edit:
                continue
            rid = payload.get("record_id", "?")
            lenses = ",".join(payload.get("lenses_surfaced") or [])
            confirmed = payload.get("confirmed_by") or "-"
            walked_at = payload.get("walked_at", 0)
            _safe_echo(
                f"{rid}  ts={walked_at:.0f}  fp={fp}  lenses=[{lenses}]  confirmed_by={confirmed}"
            )
            shown += 1
        if shown == 0:
            _safe_echo("[council] No records found")

    @council_group.command("emergency-skip")
    @click.option("--tool", required=True, help="Tool name (e.g. Write/Edit/Bash)")
    @click.option("--path", default="", help="File path being edited")
    @click.option("--command", default="", help="Bash command if tool is Bash")
    @click.option("--reason", required=True, help="Verbatim reason for the emergency-skip")
    @click.option(
        "--corroborator",
        required=True,
        help="Substrate event_id corroborating unreachability (compaction/hook-failure/cron)",
    )
    def cmd_emergency_skip(
        tool: str, path: str, command: str, reason: str, corroborator: str
    ) -> None:
        """Invoke the corroborator-required emergency carve-out.

        The corroborator event_id must resolve to a real substrate event
        of an accepted type or actor. Self-attestation is closed at
        design-time per Aether Catch 4.
        """
        fingerprint = _normalize_edit_fingerprint(
            path or command.split()[0] if command else path, tool
        )
        corroborator_event = store.find_corroborator_event(
            corroborator,
            accepted_event_types=EMERGENCY_CORROBORATOR_EVENT_TYPES,
            accepted_actors=EMERGENCY_CORROBORATOR_ACTORS,
        )
        if corroborator_event is None:
            _safe_echo(
                f"[council] DENIED: corroborator event_id {corroborator!r} did not resolve "
                f"to an accepted-type/actor event. Self-attested 'unreachable' is not certified."
            )
            raise SystemExit(1)
        skip_event_id = store.log_emergency_skip(
            edit_fingerprint=fingerprint,
            reason=reason,
            corroborator_event_id=corroborator,
        )
        _safe_echo(f"[council] EMERGENCY_SKIP recorded: event_id={skip_event_id}")
        _safe_echo(f"  fingerprint: {fingerprint}")
        _safe_echo(f"  corroborator: {corroborator}")
        _safe_echo(f"  reason: {reason}")
        _safe_echo("  Andrew will see this and verify-or-reject at next composition.")

    @council_group.command("authorize-bypass")
    @click.option("--tool", required=True, help="Tool name (e.g. Write/Edit/Bash)")
    @click.option("--path", default="", help="File path being edited")
    @click.option("--command", default="", help="Bash command if tool is Bash")
    @click.option(
        "--reason",
        required=True,
        help="Human-readable reason for this bypass authorization",
    )
    @click.option(
        "--quote",
        required=True,
        help=(
            "The operator's actual authorization text (verbatim). Recorded "
            "as evidence — model structurally cannot forge user-role text, "
            "so quote provenance IS the trust anchor."
        ),
    )
    def cmd_authorize_bypass(tool: str, path: str, command: str, reason: str, quote: str) -> None:
        """Authorize a one-time bypass of the council-required gate for a
        specific edit (ForcedWorkGate primitive, instance 4 —
        operator-authorization).

        Emits a state marker via ``divineos.core.state_markers`` that the
        gate reads on its next ``decide()`` call. Marker is:
          - one-per-use (consumed on first matching edit)
          - exact-fingerprint match (edit:X marker doesn't clear edit:Y)
          - 15-min expiry per Aria's answer to primitive design-question #1

        The mismatch audit surface fires LOUD if the marker gets consumed
        by a fingerprint different from the authorized one (Aria's
        addition to the StateMarker addendum) — either race, fabrication,
        or consume-path bug, each deserving loud attention.

        Coord note: this CLI's runtime behavior depends on
        ``divineos.core.state_markers`` being on the branch (Aether's
        scope). Before that module lands, the CLI raises ImportError with
        a diagnostic; after it lands, the marker emit path runs cleanly.
        """
        import hashlib

        from divineos.core.council_required.types import (
            OPERATOR_BYPASS_EXPIRY_SECONDS,
            STATE_MARKER_KIND_OPERATOR_BYPASS,
        )

        try:
            from divineos.core.state_markers import emit_marker
        except ImportError:
            _safe_echo(
                "[council] authorize-bypass: divineos.core.state_markers "
                "not yet available on this branch. Aether's module needs "
                "to land via merge before this CLI can emit markers. "
                "Meanwhile, the authorization can be captured via a raw "
                "ledger event for later cross-reference."
            )
            raise SystemExit(1)

        fingerprint = _normalize_edit_fingerprint(
            path or command.split()[0] if command else path, tool
        )
        quote_hash = hashlib.sha256(quote.encode("utf-8")).hexdigest()

        marker_id = emit_marker(
            kind=STATE_MARKER_KIND_OPERATOR_BYPASS,
            fingerprint=fingerprint,
            payload={
                "quote_hash": quote_hash,
                "quote_preview": quote[:200],
                "reason": reason,
                "authorized_by": "operator",
            },
            expires_in_seconds=OPERATOR_BYPASS_EXPIRY_SECONDS,
        )
        _safe_echo(f"[council] operator-bypass authorized: marker_id={marker_id}")
        _safe_echo(f"  fingerprint: {fingerprint}")
        _safe_echo(f"  reason: {reason}")
        _safe_echo(f"  quote_hash: {quote_hash[:16]}...")
        _safe_echo(
            f"  expires in {OPERATOR_BYPASS_EXPIRY_SECONDS} seconds "
            "(15 min — matches operator per-moment authorization discipline)"
        )
        _safe_echo(
            "  The gate will read this marker on the next matching edit, "
            "consume it, and allow with outcome=OPERATOR_AUTHORIZED_BYPASS."
        )

    @council_group.command("check")
    @click.option("--tool", required=True, help="Tool name")
    @click.option("--path", default="", help="File path (for Write/Edit tools)")
    @click.option("--command", default="", help="Bash command (for Bash tool)")
    def cmd_check(tool: str, path: str, command: str) -> None:
        """Run the gate against a proposed edit and print the decision.

        Used by the PreToolUse hook script (check-council-required.sh)
        and for manual testing. Exit code 0 = ALLOW, 2 = BLOCK.
        """
        from divineos.core.gravity_classifier import score_substrate_modification

        paths_tuple = (path,) if path else ()
        decision = gate_mod.decide(
            tool_name=tool,
            file_paths=paths_tuple,
            bash_command=command,
            gravity_fn=score_substrate_modification,
            keywords_loader=_load_expert_keywords,
        )
        from divineos.core.council_required.types import GateOutcome

        if decision.outcome == GateOutcome.ALLOW:
            _safe_echo("[council] ALLOW")
            if decision.matched_record_id:
                _safe_echo(f"  consumed record: {decision.matched_record_id}")
            return
        # BLOCK
        primary = path or (command.split()[0] if command else "")
        fp = _normalize_edit_fingerprint(primary, tool)
        msg = gate_mod.format_block_message(decision, fingerprint=fp)
        _safe_echo(msg)
        raise SystemExit(2)
