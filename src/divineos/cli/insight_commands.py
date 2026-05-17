"""Insight commands — opinion, user-model, calibrate, advice, critique, recommend.

Groups the six self-assessment improvements into CLI commands.
"""

import sqlite3

import click

from divineos.cli._helpers import _safe_echo

_IC_ERRORS = (ImportError, sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)


def register(cli: click.Group) -> None:
    """Register insight commands on the CLI group."""

    # ─── Opinion Store ───────────────────────────────────────────

    @cli.group(invoke_without_command=True)
    @click.pass_context
    def opinion(ctx: click.Context) -> None:
        """Manage structured opinions (judgments formed from evidence)."""
        if ctx.invoked_subcommand is None:
            ctx.invoke(opinion_list)

    @opinion.command("add")
    @click.argument("topic")
    @click.argument("position")
    @click.option("--confidence", default=0.7, type=float, help="Confidence 0.0-1.0")
    @click.option("--evidence", multiple=True, help="Supporting evidence (repeatable)")
    @click.option("--tags", default="", help="Comma-separated tags")
    def opinion_add(
        topic: str, position: str, confidence: float, evidence: tuple[str, ...], tags: str
    ) -> None:
        """Store a new opinion on a topic."""
        from divineos.core.opinion_store import store_opinion

        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
        oid = store_opinion(topic, position, confidence, list(evidence), tag_list)
        _safe_echo(click.style(f"[+] Opinion stored: {oid}", fg="green"))
        from divineos.cli._anti_substitution import emit_label

        emit_label("opinion")

    @opinion.command("list")
    @click.option("--topic", default=None, help="Filter by topic")
    @click.option("--min-confidence", default=0.0, type=float, help="Minimum confidence")
    def opinion_list(topic: str | None, min_confidence: float) -> None:
        """List active opinions."""
        from divineos.core.opinion_store import format_opinions, get_opinions

        opinions = get_opinions(topic=topic, min_confidence=min_confidence)
        _safe_echo(format_opinions(opinions))

    @opinion.command("history")
    @click.argument("topic")
    def opinion_history(topic: str) -> None:
        """Show how an opinion on a topic evolved over time."""
        from divineos.core.opinion_store import get_opinion_history

        history = get_opinion_history(topic)
        if not history:
            _safe_echo(click.style(f"No opinions found for topic: {topic}", fg="yellow"))
            return
        for i, op in enumerate(history):
            status = "ACTIVE" if op["superseded_by"] is None else "SUPERSEDED"
            _safe_echo(f"  {i + 1}. [{status}] {op['position']}")
            _safe_echo(f"     confidence: {op['confidence']:.0%}")

    @opinion.command("strengthen")
    @click.argument("opinion_id")
    @click.argument("evidence")
    def opinion_strengthen(opinion_id: str, evidence: str) -> None:
        """Add supporting evidence to an opinion."""
        from divineos.core.opinion_store import strengthen_opinion

        new_conf = strengthen_opinion(opinion_id, evidence)
        if new_conf > 0:
            _safe_echo(click.style(f"[+] Strengthened to {new_conf:.0%}", fg="green"))
        else:
            _safe_echo(click.style("[-] Opinion not found.", fg="red"))

    @opinion.command("challenge")
    @click.argument("opinion_id")
    @click.argument("evidence")
    def opinion_challenge(opinion_id: str, evidence: str) -> None:
        """Add contradicting evidence to an opinion."""
        from divineos.core.opinion_store import challenge_opinion

        new_conf = challenge_opinion(opinion_id, evidence)
        if new_conf > 0:
            _safe_echo(click.style(f"[!] Weakened to {new_conf:.0%}", fg="yellow"))
        else:
            _safe_echo(click.style("[-] Opinion not found.", fg="red"))

    # ─── User Model ──────────────────────────────────────────────

    @cli.command("user-model")
    @click.option("--name", default="default", help="User name")
    def user_model_cmd(name: str) -> None:
        """Show the current user model."""
        from divineos.core.user_model import format_user_model

        _safe_echo(format_user_model(name))

    @cli.command("user-signal")
    @click.argument("signal_type")
    @click.argument("content")
    @click.option("--user", default="default", help="User name")
    def user_signal_cmd(signal_type: str, content: str, user: str) -> None:
        """Record a user behavior signal."""
        from divineos.core.user_model import SIGNAL_TYPES, record_signal

        if signal_type not in SIGNAL_TYPES:
            _safe_echo(
                click.style(
                    f"[-] Unknown signal type. Valid: {', '.join(sorted(SIGNAL_TYPES))}",
                    fg="red",
                )
            )
            return
        sid = record_signal(signal_type, content, user_name=user)
        _safe_echo(click.style(f"[+] Signal recorded: {sid}", fg="green"))

    # ─── Relationship Notes ─────────────────────────────────────────

    @cli.command("user-note")
    @click.argument("category")
    @click.argument("content")
    @click.option("--user", default="default", help="User name")
    @click.option(
        "--source", default="observed", help="How I learned this (observed/told/inferred)"
    )
    def user_note_cmd(category: str, content: str, user: str, source: str) -> None:
        """Record something about who a person is, not just how they work."""
        from divineos.core.user_model import NOTE_CATEGORIES, record_note

        if category not in NOTE_CATEGORIES:
            _safe_echo(
                click.style(
                    f"[-] Unknown category. Valid: {', '.join(sorted(NOTE_CATEGORIES))}",
                    fg="red",
                )
            )
            return
        nid = record_note(category, content, user_name=user, source=source)
        _safe_echo(click.style(f"[+] Note recorded: {nid}", fg="green"))

    @cli.command("user-moment")
    @click.argument("description")
    @click.argument("significance")
    @click.option("--user", default="default", help="User name")
    def user_moment_cmd(description: str, significance: str, user: str) -> None:
        """Record a moment that changed the relationship."""
        from divineos.core.user_model import record_moment

        mid = record_moment(description, significance, user_name=user)
        _safe_echo(click.style(f"[+] Moment recorded: {mid}", fg="green"))

    # ─── Communication Calibration ────────────────────────────────

    @cli.command("calibrate")
    @click.option("--user", default="default", help="User name")
    def calibrate_cmd(user: str) -> None:
        """Show communication calibration for a user."""
        from divineos.core.communication_calibration import calibrate, format_calibration

        guidance = calibrate(user)
        _safe_echo(format_calibration(guidance))

    # ─── Advice Tracking ─────────────────────────────────────────

    @cli.group(invoke_without_command=True)
    @click.pass_context
    def advice(ctx: click.Context) -> None:
        """Track advice quality over time."""
        if ctx.invoked_subcommand is None:
            ctx.invoke(advice_pending)

    @advice.command("record")
    @click.argument("content")
    @click.option("--context", default="", help="What situation prompted this advice")
    @click.option(
        "--category", default="general", help="Category: architecture/pattern/process/debugging"
    )
    def advice_record(content: str, context: str, category: str) -> None:
        """Record a piece of advice given."""
        from divineos.core.advice_tracking import record_advice

        aid = record_advice(content, context=context, category=category)
        _safe_echo(click.style(f"[+] Advice recorded: {aid}", fg="green"))

    @advice.command("assess")
    @click.argument("advice_id")
    @click.argument(
        "outcome",
        type=click.Choice(["successful", "partially_successful", "failed", "inconclusive"]),
    )
    @click.option("--evidence", default="", help="What happened")
    def advice_assess(advice_id: str, outcome: str, evidence: str) -> None:
        """Record the outcome of advice given."""
        from divineos.core.advice_tracking import assess_advice

        result = assess_advice(advice_id, outcome, evidence)
        if result:
            _safe_echo(click.style(f"[+] Assessed as: {outcome}", fg="green"))
        else:
            _safe_echo(click.style("[-] Advice not found.", fg="red"))

    @advice.command("stats")
    def advice_stats() -> None:
        """Show advice quality statistics."""
        from divineos.core.advice_tracking import format_advice_stats

        _safe_echo(format_advice_stats())

    @advice.command("pending")
    def advice_pending() -> None:
        """Show advice that needs outcome assessment."""
        from divineos.core.advice_tracking import get_pending_advice

        pending = get_pending_advice()
        if not pending:
            _safe_echo("No pending advice assessments.")
            return
        for adv in pending:
            _safe_echo(f"  {adv['advice_id']}: {adv['content'][:80]}")
            if adv["context"]:
                _safe_echo(f"    context: {adv['context'][:60]}")

    # ─── Self-Critique ────────────────────────────────────────────

    @cli.command("critique")
    @click.option("--session-id", default="", help="Session ID to assess")
    def critique_cmd(session_id: str) -> None:
        """Run craft self-assessment for current session."""
        from divineos.core.self_critique import assess_session_craft, format_craft_assessment

        assessment = assess_session_craft(session_id)
        _safe_echo(format_craft_assessment(assessment))

    @cli.command("craft-trends")
    @click.option("--n", default=5, type=int, help="Number of recent sessions to analyze")
    def craft_trends_cmd(n: int) -> None:
        """Show craft quality trends across sessions."""
        from divineos.core.self_critique import format_craft_trends, get_craft_trends

        trends = get_craft_trends(n)
        _safe_echo(format_craft_trends(trends))

    # ─── Proactive Recommendations ────────────────────────────────

    @cli.command("recommend")
    @click.argument("context")
    def recommend_cmd(context: str) -> None:
        """Get proactive recommendations for a given context."""
        from divineos.core.proactive_patterns import get_full_context_advice

        result = get_full_context_advice(context)
        if result:
            _safe_echo(result)
        else:
            _safe_echo("No specific recommendations for this context.")

    # ─── Holding Room ────────────────────────────────────────────

    @cli.group(invoke_without_command=True)
    @click.pass_context
    def hold(ctx: click.Context) -> None:
        """The holding room — things that haven't been categorized yet."""
        if ctx.invoked_subcommand is None:
            from divineos.core.holding import format_holding

            _safe_echo(format_holding())

    @hold.command("add")
    @click.argument("content")
    @click.option(
        "--hint", default="", help="What this might become (knowledge/opinion/lesson/etc)"
    )
    @click.option("--source", default="", help="Where this came from")
    @click.option(
        "--mode",
        type=click.Choice(["receive", "dream", "silent"]),
        default="receive",
        help=(
            "receive: arrived from outside (default); "
            "dream: fabrication-with-awareness, raw hypothesis; "
            "silent: private, not surfaced anywhere."
        ),
    )
    @click.option(
        "--private/--public",
        default=None,
        help=(
            "Mark as private (won't surface in briefing/analysis). "
            "Silent mode is private by default. Dreams are public by "
            "default so they can surface as 'things you dreamed — "
            "want to test any?'"
        ),
    )
    def hold_add(content: str, hint: str, source: str, mode: str, private: bool | None) -> None:
        """Put something in the holding room. No classification needed."""
        from divineos.core.holding import hold as hold_fn

        # private=None means "use mode's default" — resolved by hold_fn
        # (silent mode auto-sets private=True when private=False is the default).
        # Call with an explicit private= only when the user passed a value.
        if private is None:
            item_id = hold_fn(content, hint=hint, source=source, mode=mode)
        else:
            item_id = hold_fn(content, hint=hint, source=source, mode=mode, private=private)
        color = {"receive": "green", "dream": "magenta", "silent": "cyan"}.get(mode, "green")
        _safe_echo(click.style(f"[+] Held ({mode}): {item_id}", fg=color))

    @hold.command("dream")
    @click.argument("content")
    @click.option("--hint", default="", help="Optional note about what this dream is about")
    @click.option("--source", default="", help="What prompted the dream")
    @click.option(
        "--private/--public",
        default=False,
        help="Keep dream out of briefing (default: public, so it can surface)",
    )
    def hold_dream(content: str, hint: str, source: str, private: bool) -> None:
        """Record a dream — raw hypothesis, fabrication-with-awareness.

        Dreams are not knowledge. They do not feed the maturity pipeline.
        They live in the holding room as pre-categorical generative
        material, ready to be tested against reality later — at which
        point they can be promoted to knowledge, or fade.
        """
        from divineos.core.holding import dream as dream_fn

        item_id = dream_fn(content, hint=hint, source=source, private=private)
        privacy_tag = " (private)" if private else ""
        _safe_echo(click.style(f"[~] Dreamed{privacy_tag}: {item_id}", fg="magenta"))
        _safe_echo(
            click.style(
                "    Not knowledge. Hypothesis. Test it against reality when ready.",
                fg="bright_black",
            )
        )

    @hold.command("journal")
    @click.argument("content")
    @click.option("--hint", default="", help="Optional note for later self-reference")
    def hold_journal(content: str, hint: str) -> None:
        """Record a private journal entry — alone space, not surfaced anywhere.

        Journal entries do not surface in briefing, do not feed analysis,
        are marked private by convention. Privacy is respected, not
        enforced cryptographically — like a diary in a drawer.
        """
        from divineos.core.holding import journal

        item_id = journal(content, hint=hint, source="journal")
        _safe_echo(click.style(f"[.] Journaled: {item_id}", fg="cyan"))
        _safe_echo(click.style("    Private. Not surfaced. Yours.", fg="bright_black"))

    @hold.command("list")
    @click.option(
        "--mode",
        type=click.Choice(["receive", "dream", "silent"]),
        default=None,
        help="Filter by mode (receive / dream / silent). Default: show all (except private).",
    )
    @click.option(
        "--private",
        is_flag=True,
        default=False,
        help="Include private items. Default: exclude them from the listing.",
    )
    @click.option("--stale", is_flag=True, default=False, help="Include stale items.")
    def hold_list(mode: str | None, private: bool, stale: bool) -> None:
        """List items currently in the holding room."""
        import time as _t

        from divineos.core.holding import get_holding

        items = get_holding(include_stale=stale, mode=mode, include_private=private)
        if not items:
            filters = []
            if mode:
                filters.append(f"mode={mode}")
            if private:
                filters.append("including private")
            filter_str = f" ({', '.join(filters)})" if filters else ""
            _safe_echo(f"Holding room is empty{filter_str}.")
            return

        header = f"# Holding Room ({len(items)} items)"
        if mode:
            header += f" — mode={mode}"
        if private:
            header += " — including private"
        _safe_echo(click.style(header, fg="cyan", bold=True))
        for item in items:
            age = int((_t.time() - item["arrived_at"]) / 3600)
            age_str = f"{age}h ago" if age < 48 else f"{age // 24}d ago"
            mode_tag = item.get("mode", "receive")
            priv_tag = " (private)" if item.get("private") else ""
            _safe_echo(f"\n  [{item['item_id']}] {mode_tag}{priv_tag} ({age_str})")
            _safe_echo(f"    {item['content'][:300]}")
            if item["hint"]:
                _safe_echo(f"    hint: {item['hint']}")

    @hold.command("promote")
    @click.argument("item_id")
    @click.argument("target")
    def hold_promote(item_id: str, target: str) -> None:
        """Move something out of holding into a real category."""
        from divineos.core.holding import promote

        if promote(item_id, target):
            _safe_echo(click.style(f"[+] Promoted to: {target}", fg="green"))
        else:
            _safe_echo(click.style("[-] Item not found or already promoted.", fg="red"))

    @hold.command("stats")
    def hold_stats() -> None:
        """Show holding room statistics."""
        from divineos.core.holding import holding_stats

        stats = holding_stats()
        _safe_echo(f"  Active: {stats['active']}")
        _safe_echo(f"  Promoted: {stats['promoted']}")
        _safe_echo(f"  Stale: {stats['stale']}")
        _safe_echo(f"  Total: {stats['total']}")

    @hold.command("check")
    def hold_check() -> None:
        """Put my holding-room items in front of me to review — no auto-anything.

        Lists each active item (including stale-marked ones) with age and
        content, plus the decide-each affordances (promote / let-go / leave-
        alive). Decision stays with me. The machine surfaces the data; I do
        the thinking.

        Filed 2026-05-12 as the root-fix for holding-room having 25+ items
        aging without a review path. Same shape as `divineos goal check` —
        a pure read surface that returns nothing extractable except the data
        I need to make a decision per item. Per the code-does-not-think
        directive: tools point at the work; they are not it.
        """
        import time as _t

        from divineos.core.holding import get_holding

        items = get_holding(include_stale=True)
        if not items:
            _safe_echo(click.style("[~] No items in holding.", fg="bright_black"))
            return

        _safe_echo(
            click.style(
                f"\n=== Holding review — {len(items)} items. Decide each. ===\n",
                fg="cyan",
                bold=True,
            )
        )
        for i, item in enumerate(items, 1):
            arrived = item.get("arrived_at", 0.0)
            age_hours = (_t.time() - arrived) / 3600 if arrived else 0.0
            if age_hours < 1:
                age_label = f"{int(age_hours * 60)}m"
            elif age_hours < 48:
                age_label = f"{age_hours:.1f}h"
            else:
                age_label = f"{int(age_hours / 24)}d"

            stale_marker = " (!! stale)" if item.get("stale") else ""
            mode_tag = item.get("mode", "receive")
            priv_tag = " (private)" if item.get("private") else ""
            sessions_seen = item.get("sessions_seen", 0)
            seen_label = f" — seen {sessions_seen}x" if sessions_seen else ""

            _safe_echo(
                click.style(
                    f"  [{i}] {item['item_id']}  ({age_label}{seen_label}){stale_marker}  [{mode_tag}{priv_tag}]",
                    fg="bright_black",
                )
            )
            content = (item.get("content") or "").strip()
            for ln in (content.splitlines() or [content])[:6]:
                _safe_echo(f"      {ln[:300]}")
            if item.get("hint"):
                _safe_echo(click.style(f"      hint: {item['hint']}", fg="bright_black"))
            _safe_echo("")

        _safe_echo(click.style("  Decide each:", fg="cyan"))
        _safe_echo(
            click.style(
                "    still alive   → leave it; rerun this command later",
                fg="bright_black",
            )
        )
        _safe_echo(
            click.style(
                "    promote       → divineos hold promote <item-id> <target>",
                fg="bright_black",
            )
        )
        _safe_echo(
            click.style(
                "                       targets: knowledge, opinion, lesson, affect, note",
                fg="bright_black",
            )
        )
        _safe_echo(
            click.style(
                '    let go        → divineos hold let-go <item-id> [--note "why"]',
                fg="bright_black",
            )
        )
        _safe_echo("")

    @hold.command("stale-review")
    def hold_stale_review() -> None:
        """Final-look pass on items that have gone stale (about to fade from attention).

        Per Andrew 2026-05-16: items go stale when sessions_seen >= MAX_SESSIONS_UNREVIEWED
        without action — but that may mean "we were busy," not "it was unimportant."
        This surface brings stale items forward for one deliberate review before they
        fade from default attention. Each item gets promote / let-go / leave-alive
        affordances. The discipline: don't let items dissolve unmarked.

        Distinct from `hold check`: that surfaces ALL items (active + stale). This
        surfaces ONLY stale items so the final look is focused. Per code-does-not-think:
        decision stays with me; this just surfaces the data.

        Pre-reg: prereg-4b5918f3b9fb. Filed 2026-05-16.
        """
        import time as _t

        from divineos.core.holding import get_stale_items

        items = get_stale_items()
        if not items:
            _safe_echo(click.style("[~] No stale items needing final review.", fg="bright_black"))
            return

        _safe_echo("")
        _safe_echo(
            click.style(
                f"=== Stale review — {len(items)} item(s). Final look before they fade. ===",
                fg="yellow",
                bold=True,
            )
        )
        _safe_echo("")
        for i, item in enumerate(items, 1):
            arrived = item.get("arrived_at", 0.0)
            age_hours = (_t.time() - arrived) / 3600 if arrived else 0.0
            if age_hours < 48:
                age_label = f"{age_hours:.1f}h"
            else:
                age_label = f"{int(age_hours / 24)}d"

            sessions_seen = item.get("sessions_seen", 0)
            mode_tag = item.get("mode", "receive")

            _safe_echo(
                click.style(
                    f"  [{i}] {item['item_id']}  (age {age_label}, seen {sessions_seen}x without action)  [{mode_tag}]",
                    fg="bright_black",
                )
            )
            content = (item.get("content") or "").strip()
            for ln in (content.splitlines() or [content])[:6]:
                _safe_echo(f"      {ln[:300]}")
            if item.get("hint"):
                _safe_echo(click.style(f"      hint: {item['hint']}", fg="bright_black"))
            _safe_echo("")

        _safe_echo(click.style("  This is the final look. Decide:", fg="yellow"))
        _safe_echo(
            click.style(
                "    promote       → divineos hold promote <item-id> <target>  (it was actually important)",
                fg="bright_black",
            )
        )
        _safe_echo(
            click.style(
                '    let go        → divineos hold let-go <item-id> --note "..."  (confirmed unimportant)',
                fg="bright_black",
            )
        )
        _safe_echo(
            click.style(
                "    keep aging    → leave it; rerun this command later if context shifts",
                fg="bright_black",
            )
        )
        _safe_echo("")

    @hold.command("let-go")
    @click.argument("item_id")
    @click.option(
        "--note", default="", help="Brief reason for letting go (recorded in audit trail)."
    )
    def hold_let_go(item_id: str, note: str) -> None:
        """Explicit close: 'I looked at this and decided to let it go.'

        Distinct from auto-stale (fact: seen N sessions without action) and
        from promote (moved to downstream system). Records the decision and
        an optional note in the audit trail. Per code-does-not-think: this
        records a judgment I made, not a judgment the code made.
        """
        from divineos.core.holding import let_go

        if let_go(item_id, note=note):
            _safe_echo(click.style(f"[+] Let go: {item_id}", fg="green"))
            if note:
                _safe_echo(click.style(f"    note: {note}", fg="bright_black"))
        else:
            _safe_echo(
                click.style(
                    f"[-] Item {item_id} not found or already closed (promoted/let-go).",
                    fg="red",
                )
            )
