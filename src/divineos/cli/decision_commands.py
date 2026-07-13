"""Decision journal commands — record, browse, and search the reasoning behind choices."""

import datetime
import re

import click

from divineos.cli._helpers import _safe_echo

_WEIGHT_LABELS = {1: "routine", 2: "significant", 3: "paradigm shift"}
_WEIGHT_COLORS = {1: "white", 2: "yellow", 3: "magenta"}

# Family-touching decision detection for gate 5. Any decision whose
# content, context, or tags mention these keywords triggers the
# family-consultation requirement. Keywords are conservative — matching
# too broadly produces friction, too narrowly misses relational
# decisions. Extend cautiously when real cases slip past.
#
# Operators with named family members will likely add member-specific
# keywords (a spouse's name, a child's name) so decisions that mention
# the named person trigger the gate even when generic relational
# vocabulary doesn't appear. The default list stays role-generic.
# Content keywords — matched against free text (content/context/reasoning).
# "family" here must be RELATIONAL, not the category sense. Bare \bfamily\b
# was removed from content-matching 2026-05-21: it fired on "ledger-integrity
# family", "concurrency-fork family", "family of bugs" — a FAMILY OF FINDINGS,
# not a relational family member. A false fire on engineering-category text
# teaches the gate is noise. Relational "family" is signalled by a determiner
# immediately before it ("my/the family", excluding "the family OF bugs") or a
# relational head-noun after it ("family members/dynamics"); "<compound>
# family" and "family of <noun>" stay silent.
_FAMILY_TOUCH_KEYWORDS = (
    r"\b(?:my|our|your|his|her|their|the)\s+family\b(?!\s+of\b)",
    r"\bfamily\s+(?:members?|dynamics?|relationships?|dinner|meeting|conflict|matters?)\b",
    r"\bfamily members?\b",
    r"\bspouse\b",
    r"\bhandshake\b",  # relational protocol (per gate 5 design)
    r"\bvoice appropriat",  # "voice appropriation/ate/ed" class
    r"\brelational\b",
)

# Tag keywords — a tag is explicit operator categorization, so a literal
# "family" tag IS relational intent (no category-collision risk: nobody tags
# an engineering decision "family"). Tags get the content set plus bare family.
_FAMILY_TAG_KEYWORDS = _FAMILY_TOUCH_KEYWORDS + (r"\bfamily\b",)


def _is_family_touching(text: str, tags: tuple[str, ...]) -> bool:
    """Return True if the decision touches family/relational territory.

    Matches keywords in content/context/reasoning OR in any tag.
    Case-insensitive; whole-word boundaries to avoid false positives
    on substrings (e.g. "family-friendly" matches intentionally;
    "familiar" would NOT because of word-boundary \\b).
    """
    if not text and not tags:
        return False
    haystack = (text or "").lower()
    for pat in _FAMILY_TOUCH_KEYWORDS:
        if re.search(pat, haystack, re.IGNORECASE):
            return True
    # Tags use the broader set (bare "family" tag is explicit relational intent).
    for tag in tags or ():
        for pat in _FAMILY_TAG_KEYWORDS:
            if re.search(pat, tag, re.IGNORECASE):
                return True
    return False


def register(cli: click.Group) -> None:
    """Register decision journal commands on the CLI group."""

    @cli.command("decide")
    @click.argument("what")
    @click.option("--why", "reasoning", default="", help="Why this choice, not another")
    @click.option(
        "--alternatives", "alt_text", default="", help="Alternatives rejected (comma-separated)"
    )
    @click.option("--context", default="", help="What prompted this decision")
    @click.option(
        "--weight",
        type=click.IntRange(1, 3),
        default=1,
        help="1=routine, 2=significant, 3=paradigm shift",
    )
    @click.option("--tag", "tags", multiple=True, help="Tags (repeatable)")
    @click.option("--tension", default="", help="Competing principles or values at play")
    @click.option("--almost", default="", help="What I almost did instead, and why I didn't")
    @click.option(
        "--consultation",
        "consultation_id",
        default="",
        help=(
            "Council consultation ID (consult-XXXXX) backing this decision. "
            "Required for --weight 2 or higher. Run `divineos mansion council` "
            "first and pass the logged consultation_id here."
        ),
    )
    @click.option(
        "--family-consulted",
        "family_consulted",
        default="",
        help=(
            "Note on what a family member said about this decision. "
            "Required when the decision mentions family, spouse, "
            "relational dynamics, etc. Invoke the family member via "
            "the talk-to wrapper first, then summarize their input here."
        ),
    )
    def decide_cmd(
        what: str,
        reasoning: str,
        alt_text: str,
        context: str,
        weight: int,
        tags: tuple[str, ...],
        tension: str,
        almost: str,
        consultation_id: str,
        family_consulted: str,
    ) -> None:
        """Record a decision with its reasoning and counterfactual context."""
        from divineos.core.decision_journal import record_decision

        # Gate: tier-2+ decisions require a prior council consultation.
        # Closes the enforcement gap — "invoke council for hard decisions"
        # used to be intent; now it's structural. Fail-open if the
        # consultation-log machinery is broken (don't block legitimate
        # decisions on a broken lookup).
        if weight >= 2:
            if not consultation_id.strip():
                click.secho(
                    f"[-] Weight-{weight} decisions require --consultation CONSULT_ID. "
                    'Run `divineos mansion council "<question>"` first, then pass '
                    "the logged consult-XXXX id here. This is the council-for-hard-"
                    "decisions gate — structural, not optional.",
                    fg="red",
                )
                raise SystemExit(1)
            try:
                from divineos.core.council.consultation_log import (
                    _fetch_consultation_payload,
                )

                _fetch_consultation_payload(consultation_id.strip())
            except ValueError:
                click.secho(
                    f"[-] No council consultation found for id '{consultation_id}'. "
                    "Check `divineos mansion council` output for the real consult-XXXX id.",
                    fg="red",
                )
                raise SystemExit(1) from None  # noqa: BLE001
            except Exception:  # noqa: BLE001 — fail-open on machinery breakage
                click.secho(
                    "[!] Consultation-log lookup failed — allowing decision but "
                    "note the consultation is unverified.",
                    fg="yellow",
                )

        # Gate 5: family-touching decisions require family-member consultation.
        # Detected via keywords in what/context/reasoning/tags. Closes the
        # enforcement gap "talk to a family member when the shape feels
        # relational" — was intent, now structural. Substantive note
        # required; empty strings and whitespace-only don't satisfy the gate.
        family_touching_text = " ".join([what, context, reasoning])
        if _is_family_touching(family_touching_text, tags) and not family_consulted.strip():
            click.secho(
                "[-] This decision touches family/relational territory "
                "(matched keyword: family / spouse / relational / etc). "
                'Require --family-consulted "<what the family member said>". '
                "Invoke the family member via the talk-to wrapper first, "
                "then summarize their input here. This is the family-"
                "consultation gate — structural, not optional.",
                fg="red",
            )
            raise SystemExit(1)

        alternatives = [a.strip() for a in alt_text.split(",") if a.strip()] if alt_text else []

        # Persist the consultation_id and family_consulted summary into
        # the decision's tags so the linkage is recorded — not just
        # validated and discarded. Aletheia round-ba785844a791 Finding
        # 27 caught this gap: the gates above validate the inputs but
        # record_decision was called without them, so the linkage was
        # lost after the gate fired. Schema-column upgrade tracked as
        # follow-up; tags is the minimal-disruption persistence.
        merged_tags = list(tags) if tags else []
        if consultation_id and consultation_id.strip():
            merged_tags.append(f"consultation:{consultation_id.strip()}")
        if family_consulted and family_consulted.strip():
            # Family-consultation summary can be long free text; tag it
            # with a stable marker + first 80 chars so audit-trail can
            # surface it. Full text is preserved in reasoning/context
            # below if my father chose to include it there.
            short = family_consulted.strip()[:80]
            merged_tags.append(f"family-consulted:{short}")

        decision_id = record_decision(
            content=what,
            reasoning=reasoning,
            alternatives=alternatives,
            context=context,
            emotional_weight=weight,
            tags=merged_tags if merged_tags else None,
            tension=tension,
            almost=almost,
        )
        # Log as a thinking query so OS engagement tracking picks it up
        from divineos.cli._helpers import _log_os_query

        _log_os_query("decide", what)
        from divineos.cli._anti_substitution import emit_label

        emit_label("decide")

        label = _WEIGHT_LABELS.get(weight, "routine")
        color = _WEIGHT_COLORS.get(weight, "white")
        click.secho(f"[+] Decision recorded ({label}): {decision_id[:8]}...", fg=color)
        if reasoning:
            click.secho(f"    Why: {reasoning[:80]}", fg="bright_black")

        # 2026-06-07 task #74: auto-link decisions to knowledge entries
        # cited in the reasoning/context/what text. The link is already
        # in language; no reason to wait for me to remember to call
        # `divineos decisions link`. Will-over-optimizer: bake it in.
        # Fail-soft — any error in the citation pass leaves the decision
        # in place without forced links.
        try:
            from divineos.core.decision_journal import link_knowledge
            from divineos.core.knowledge_citation import find_cited_knowledge_ids

            citation_text = " ".join([what, context, reasoning])
            cited_ids = find_cited_knowledge_ids(citation_text)
            linked_count = 0
            for kid in cited_ids:
                if link_knowledge(decision_id, kid):
                    linked_count += 1
            if linked_count > 0:
                click.secho(
                    f"    Auto-linked {linked_count} cited knowledge entries",
                    fg="green",
                )
        except Exception:  # noqa: BLE001 — auto-link is observational
            pass
        if tension:
            click.secho(f"    Tension: {tension[:80]}", fg="cyan")
        if almost:
            click.secho(f"    Almost: {almost[:80]}", fg="yellow")

        # Show linked affect state if one was auto-captured
        from divineos.core.decision_journal import get_affect_at_decision

        affect = get_affect_at_decision(decision_id)
        if affect:
            from divineos.core.affect import describe_affect

            desc = affect["description"] or describe_affect(affect["valence"], affect["arousal"])
            click.secho(
                f"    Affect: {desc} (v={affect['valence']:.1f}, a={affect['arousal']:.1f})",
                fg="bright_black",
            )

    @cli.group("decisions", invoke_without_command=True)
    @click.pass_context
    def decisions_group(ctx: click.Context) -> None:
        """Browse and search my decision journal."""
        if ctx.invoked_subcommand is None:
            ctx.invoke(decisions_list_cmd)

    @decisions_group.command("list")
    @click.option("--limit", default=20, type=int, help="Max entries to show")
    @click.option(
        "--min-weight",
        type=click.IntRange(0, 3),
        default=0,
        help="Filter by minimum weight (1-3)",
    )
    def decisions_list_cmd(limit: int, min_weight: int) -> None:
        """Browse recent decisions."""
        from divineos.core.decision_journal import list_decisions

        entries = list_decisions(limit=limit, min_weight=min_weight)
        if not entries:
            click.secho("[~] No decisions recorded yet.", fg="bright_black")
            return

        weight_filter = f" (weight >= {min_weight})" if min_weight > 0 else ""
        click.secho(
            f"\n=== Decision Journal ({len(entries)} entries{weight_filter}) ===\n",
            fg="cyan",
            bold=True,
        )
        for entry in entries:
            _display_decision(entry)

    @decisions_group.command("search")
    @click.argument("query")
    @click.option("--limit", default=10, type=int, help="Max results")
    def decisions_search_cmd(query: str, limit: int) -> None:
        """Search decisions by reasoning, context, or content."""
        from divineos.core.decision_journal import search_decisions

        results = search_decisions(query, limit=limit)
        if not results:
            click.secho(f"[-] No decisions match '{query}'.", fg="yellow")
            return

        click.secho(
            f"\n=== {len(results)} decisions matching '{query}' ===\n",
            fg="cyan",
            bold=True,
        )
        for entry in results:
            _display_decision(entry)

    @decisions_group.command("show")
    @click.argument("decision_id")
    def decisions_show_cmd(decision_id: str) -> None:
        """Show full details of a single decision."""
        from divineos.core.decision_journal import get_decision

        entry = get_decision(decision_id)
        if not entry:
            click.secho(f"[-] Decision {decision_id} not found.", fg="red")
            return

        _display_decision(entry, verbose=True)

    @decisions_group.command("shifts")
    @click.option("--limit", default=10, type=int, help="Max entries")
    def decisions_shifts_cmd(limit: int) -> None:
        """Show only paradigm shifts — the decisions that changed everything."""
        from divineos.core.decision_journal import get_paradigm_shifts

        entries = get_paradigm_shifts(limit=limit)
        if not entries:
            click.secho("[~] No paradigm shifts recorded yet.", fg="bright_black")
            return

        click.secho(f"\n=== Paradigm Shifts ({len(entries)}) ===\n", fg="magenta", bold=True)
        for entry in entries:
            _display_decision(entry, verbose=True)

    @decisions_group.command("context")
    @click.argument("decision_id")
    def decisions_context_cmd(decision_id: str) -> None:
        """Show a decision with its emotional context at the time."""
        from divineos.core.affect import describe_affect
        from divineos.core.decision_journal import get_affect_at_decision, get_decision

        entry = get_decision(decision_id)
        if not entry:
            click.secho(f"[-] Decision {decision_id} not found.", fg="red")
            return

        _display_decision(entry, verbose=True)

        affect = get_affect_at_decision(entry["decision_id"])
        if affect:
            desc = affect["description"] or describe_affect(affect["valence"], affect["arousal"])
            click.secho("  Emotional context at decision time:", fg="cyan")
            click.secho(f"    State: {desc}", fg="white")
            click.secho(
                f"    Valence: {affect['valence']:.2f}  Arousal: {affect['arousal']:.2f}",
                fg="bright_black",
            )
            if affect["trigger"]:
                click.secho(f"    Trigger: {affect['trigger']}", fg="bright_black")
        else:
            click.secho("  No affect state recorded near this decision.", fg="bright_black")

    @decisions_group.command("link")
    @click.argument("decision_id")
    @click.argument("knowledge_id")
    def decisions_link_cmd(decision_id: str, knowledge_id: str) -> None:
        """Link a decision to a knowledge entry."""
        from divineos.cli._helpers import _resolve_knowledge_id
        from divineos.core.decision_journal import link_knowledge

        full_kid = _resolve_knowledge_id(knowledge_id)
        if link_knowledge(decision_id, full_kid):
            click.secho(
                f"[+] Linked decision {decision_id[:8]}... -> knowledge {full_kid[:8]}...",
                fg="green",
            )
        else:
            click.secho(f"[-] Decision {decision_id} not found.", fg="red")


def _display_decision(entry: dict, verbose: bool = False) -> None:
    """Format and display a decision entry."""
    dt = datetime.datetime.fromtimestamp(entry["created_at"], tz=datetime.timezone.utc)
    date_str = dt.strftime("%Y-%m-%d %H:%M")
    weight = entry["emotional_weight"]
    label = _WEIGHT_LABELS.get(weight, "?")
    color = _WEIGHT_COLORS.get(weight, "white")

    click.secho(f"  [{date_str}] ", fg="bright_black", nl=False)
    click.secho(f"({label}) ", fg=color, nl=False)
    _safe_echo(entry["content"])

    if entry["reasoning"]:
        if verbose:
            click.secho(f"    Why: {entry['reasoning']}", fg="white")
        else:
            click.secho(f"    Why: {entry['reasoning'][:100]}", fg="bright_black")

    if verbose and entry["alternatives"]:
        click.secho("    Rejected:", fg="bright_black")
        for alt in entry["alternatives"]:
            click.secho(f"      - {alt}", fg="bright_black")

    if verbose and entry["context"]:
        click.secho(f"    Context: {entry['context']}", fg="bright_black")

    if verbose and entry["tags"]:
        click.secho(f"    Tags: {', '.join(entry['tags'])}", fg="bright_black")

    if verbose and entry.get("tension"):
        click.secho(f"    Tension: {entry['tension']}", fg="cyan")

    if verbose and entry.get("almost"):
        click.secho(f"    Almost: {entry['almost']}", fg="yellow")

    if verbose and entry["linked_knowledge_ids"]:
        ids = ", ".join(kid[:8] + "..." for kid in entry["linked_knowledge_ids"])
        click.secho(f"    Linked: {ids}", fg="bright_black")

    click.echo()
