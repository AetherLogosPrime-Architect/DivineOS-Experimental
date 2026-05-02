"""VOID CLI — adversarial-sandbox subsystem commands.

Per design brief §8 (merged PR #208).

Subcommands (Phase 1):

* ``divineos void list``        — list available personas
* ``divineos void show NAME``   — show persona body and frontmatter
* ``divineos void test TARGET`` — run a single persona against TARGET
* ``divineos void test-deep TARGET`` — run all personas against TARGET
* ``divineos void events``      — list void_ledger events
* ``divineos void verify``      — verify void_ledger hash chain
* ``divineos void shred --force`` — clear stuck mode_marker

The Phase 1 ``test`` and ``test-deep`` commands run the engine with a
placeholder ATTACK callback that returns a stub finding labeled
``MANUAL_REVIEW``. Phase 2 wires real attack-prompt assembly + LLM
adjudication; Phase 1 only proves the lifecycle plumbing works
end-to-end through the CLI.
"""

from __future__ import annotations

import click

from divineos.cli._helpers import _safe_echo
from divineos.core.void import engine, mode_marker
from divineos.core.void import ledger as void_ledger
from divineos.core.void.finding import Finding, Severity
from divineos.core.void.persona_loader import load_all, load_by_name


_SEVERITY_COLORS = {
    "CRITICAL": "red",
    "HIGH": "yellow",
    "MEDIUM": "cyan",
    "LOW": "white",
}


def _stub_attack(persona, target):
    """Phase 1 placeholder: emit a default-severity stub finding so the
    lifecycle plumbing is exercised end-to-end. Phase 2 replaces this
    with persona-prompt assembly + LLM adjudication.
    """
    severity = persona.severity_default
    if persona.name == "mirror" and severity not in {Severity.LOW, Severity.MEDIUM}:
        severity = Severity.LOW  # mirror is clarification-only
    return Finding(
        persona=persona.name,
        target=target,
        severity=severity,
        title=f"[stub] {persona.name} ran against {target}",
        body=(
            "Phase 1 stub finding. The lifecycle (TRAP/ATTACK/EXTRACT/"
            "SEAL/SHRED) ran end-to-end. Phase 2 will attach real "
            "persona-attack adjudication."
        ),
        tags=["phase1-stub"],
    )


def register(cli: click.Group) -> None:
    @cli.group()
    def void() -> None:
        """VOID adversarial-sandbox subsystem."""

    @void.command("list")
    def _list() -> None:
        """List available personas."""
        personas = load_all()
        if not personas:
            _safe_echo("(no personas found)")
            return
        for p in personas:
            tag_str = ", ".join(p.tags) if p.tags else "—"
            bar = click.style(" [HIGH-BAR]", fg="red") if p.invocation_bar == "high" else ""
            _safe_echo(
                f"{click.style(p.name, bold=True)}{bar}  "
                f"default={p.severity_default.value}  tags={tag_str}"
            )

    @void.command("show")
    @click.argument("name")
    def _show(name: str) -> None:
        """Show persona body and frontmatter."""
        try:
            p = load_by_name(name)
        except KeyError:
            raise click.ClickException(f"persona {name!r} not found") from None
        _safe_echo(click.style(f"# {p.name}", bold=True))
        _safe_echo(f"  tags: {', '.join(p.tags) or '—'}")
        _safe_echo(f"  severity_default: {p.severity_default.value}")
        _safe_echo(f"  invocation_bar: {p.invocation_bar}")
        _safe_echo("")
        _safe_echo(p.body)

    @void.command("test")
    @click.argument("target")
    @click.option("--persona", "persona_name", required=True, help="Persona name.")
    @click.option(
        "--allow-high-bar",
        is_flag=True,
        help="Required for nyarlathotep (frame-residue isolation).",
    )
    def _test(target: str, persona_name: str, allow_high_bar: bool) -> None:
        """Run a single persona against TARGET (Phase 1 stub attack)."""
        try:
            result = engine.run(
                persona_name,
                target=target,
                attack=_stub_attack,
                allow_high_bar=allow_high_bar,
            )
        except (engine.VoidScopeError, KeyError) as e:
            raise click.ClickException(str(e)) from None
        _print_result(result)

    @void.command("test-deep")
    @click.argument("target")
    @click.option(
        "--allow-high-bar",
        is_flag=True,
        help="Include nyarlathotep in the run.",
    )
    def _test_deep(target: str, allow_high_bar: bool) -> None:
        """Run all personas against TARGET (Phase 1 stub attacks)."""
        for p in load_all():
            if p.invocation_bar == "high" and not allow_high_bar:
                _safe_echo(
                    click.style(
                        f"SKIP {p.name} (high-bar; pass --allow-high-bar)",
                        fg="bright_black",
                    )
                )
                continue
            try:
                result = engine.run(
                    p.name,
                    target=target,
                    attack=_stub_attack,
                    allow_high_bar=allow_high_bar,
                )
                _print_result(result)
            except engine.VoidScopeError as e:
                _safe_echo(click.style(f"ERROR {p.name}: {e}", fg="red"))

    @void.command("events")
    @click.option("--limit", default=20, help="Number of events.")
    @click.option("--persona", "persona_filter", default=None)
    @click.option("--type", "type_filter", default=None)
    def _events(limit: int, persona_filter: str | None, type_filter: str | None) -> None:
        """List recent void_ledger events."""
        rows = void_ledger.list_events(event_type=type_filter, persona=persona_filter, limit=limit)
        if not rows:
            _safe_echo("(no events)")
            return
        for r in rows:
            _safe_echo(
                f"{r['ts']:.1f}  {r['event_type']:30}  persona={r['persona'] or '—'}  "
                f"id={r['event_id'][:8]}"
            )

    @void.command("verify")
    def _verify() -> None:
        """Verify void_ledger hash chain integrity."""
        ok, broken = void_ledger.verify_chain()
        if ok:
            _safe_echo(click.style("void_ledger chain: OK", fg="green"))
        else:
            _safe_echo(click.style(f"void_ledger chain: BROKEN ({len(broken)})", fg="red"))
            for b in broken:
                _safe_echo(f"  {b}")
            raise click.ClickException("chain integrity check failed")

    @void.command("shred")
    @click.option(
        "--force",
        is_flag=True,
        required=True,
        help="Required confirmation. Clears stuck mode_marker.",
    )
    def _shred(force: bool) -> None:
        """Clear a stuck mode_marker (orphan invocation)."""
        if not force:
            raise click.ClickException("--force is required")
        status = mode_marker.read_marker()
        if not status.active and not status.corrupted:
            _safe_echo("mode_marker not active; nothing to shred.")
            return
        mode_marker.clear_marker()
        void_ledger.append_event(
            "VOID_SHRED",
            {"forced": True, "prior_persona": status.persona, "corrupted": status.corrupted},
            persona=status.persona,
        )
        _safe_echo(click.style("mode_marker cleared (forced shred)", fg="yellow"))


def _print_result(result) -> None:
    if result.finding is None:
        _safe_echo(f"{result.persona}: no finding")
        return
    sev = result.finding.severity.value
    color = _SEVERITY_COLORS.get(sev, "white")
    _safe_echo(
        f"{click.style(result.persona, bold=True)}  "
        f"{click.style(sev, fg=color)}  {result.finding.title}"
    )
    _safe_echo(f"  void_event_id={result.void_event_id}")
