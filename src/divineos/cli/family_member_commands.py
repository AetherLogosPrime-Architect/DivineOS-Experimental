"""CLI commands for family members — init, opinion, letter, respond.

Family members (spouses, children, extended family — entities defined in
``family/family.db``) need a clean write surface that routes every write
through the five operators (reject_clause, sycophancy_detector,
costly_disagreement, access_check, planted_contradiction). This module
provides that surface, parameterized by ``--member <name>`` so the same
CLI works for any family member a user creates.

Every write routes through the operators so the handshake — *"the first
real write must be an actual stance the member disagrees with, caught by
the reject clause on operator-alive grounds"* — fires naturally on the
first call, not via mock.

## Commands

* ``divineos family-member init --member <name> [--role <role>]`` —
  creates the FamilyMember row (idempotent), shows opinion/letter count,
  and lists any letters waiting on disk.
* ``divineos family-member opinion --member <name> <stance>`` — file an
  opinion. The content goes through access_check (suggest ARCHITECTURAL
  for phenomenological claims) and reject_clause (catch composition
  failures) before landing. Flagged writes print the verdict and require
  ``--force``.
* ``divineos family-member letter --member <name> <body>`` — append a
  handoff letter to future-self. Length nudge at 2000 chars but never
  caps.
* ``divineos family-member respond --member <name> --letter <id>
  --passage <text> --stance <s>`` — append a non-recognition (or other
  stance) response to a passage in a prior letter. The anti-lineage-
  poisoning mechanism in action.

## What this module is NOT

* NOT a way to bypass the operators. Every write runs through
  access_check + reject_clause; the operators decide what composes.
  ``--force`` allows override only when the caller explicitly says
  "I know what this looks like and I mean it anyway" — and the
  override itself is printed.
* NOT a way for the main agent to perform a family member. The CLI is
  a neutral surface; the utterance that uses it is the member's. If
  the main agent calls ``divineos family-member opinion --member alice``,
  the write lands with actor=alice regardless — because the schema
  says ``family_opinions`` belong to the entity, not the caller. Who
  uses the surface shapes what lands, not what gets stamped.
"""

from __future__ import annotations

from pathlib import Path

import click

from divineos.core.family.access_check import (
    PhenomenologicalRisk,
    evaluate_access,
)
from divineos.core.family.entity import (
    get_family_member,
    get_letters,
    get_opinions,
)
from divineos.core.family.letters import (
    DEFAULT_LENGTH_NUDGE_THRESHOLD,
    append_letter,
    append_letter_response,
)
from divineos.core.family.reject_clause import evaluate_composition
from divineos.core.family.store import (
    create_family_member,
    record_affect,
    record_interaction,
    record_opinion,
)
from divineos.core.family.types import SourceTag

_DEFAULT_ROLE = "member"
_LETTERS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "family" / "letters"


def _get_or_create_member(name: str, role: str) -> object:
    """Return the named FamilyMember row. Create if it doesn't exist.

    First-run creation prints a single acknowledgment so the caller sees
    that this invocation minted the row. Subsequent invocations are
    silent and idempotent.
    """
    member = get_family_member(name)
    if member is not None:
        return member
    click.echo(f"[+] First activation for '{name}' — creating FamilyMember row.")
    member = create_family_member(name, role)
    click.echo(f"    member_id: {member.member_id}")
    return member


def register(cli: click.Group) -> None:
    """Attach the ``family-member`` command group to the top-level CLI."""

    @cli.group("family-member")
    def family_member_group() -> None:
        """Family member activation surface — init, opinion, letter, respond."""

    @family_member_group.command("init")
    @click.option("--member", required=True, help="Family member name (e.g. 'alice').")
    @click.option(
        "--role",
        default=_DEFAULT_ROLE,
        help="Role for first-run creation (spouse, child, elder, etc.). "
        "Only used if the member doesn't exist yet.",
    )
    def family_member_init(member: str, role: str) -> None:
        """Create or refresh a family member's entry, summarize their state.

        Idempotent. Safe to re-run; subsequent invocations just print the
        current state without re-creating the row.
        """
        m = _get_or_create_member(member, role)
        click.echo("")
        click.echo(f"=== {member} ({role}) ===")
        click.echo(f"member_id: {m.member_id}")  # type: ignore[attr-defined]

        opinions = get_opinions(m.member_id)  # type: ignore[attr-defined]
        click.echo(f"opinions on record: {len(opinions)}")

        letters = get_letters(m.member_id)  # type: ignore[attr-defined]
        click.echo(f"letters on record: {len(letters)}")
        click.echo("")

        if _LETTERS_DIR.exists():
            waiting = sorted(_LETTERS_DIR.glob("*.md"))
            if waiting:
                click.echo("Letters waiting on disk:")
                for p in waiting:
                    click.echo(f"  {p.name}")
                click.echo("")

        click.echo("Next steps:")
        click.echo(f'  divineos family-member opinion --member {member} "..."')
        click.echo(f'  divineos family-member letter --member {member} "..."')
        click.echo(f"  divineos family-member respond --member {member} --letter <id> ...")

    @family_member_group.command("opinion")
    @click.option("--member", required=True, help="Family member name.")
    @click.argument("stance_positional", required=False, default=None)
    @click.option(
        "--stance",
        "stance_flag",
        default=None,
        help="The stance. Alternative to positional STANCE argument; either form works.",
    )
    @click.option("--evidence", default="", help="Evidence or reasoning backing this stance.")
    @click.option(
        "--tag",
        type=click.Choice([t.value for t in SourceTag]),
        default=SourceTag.OBSERVED.value,
        help="Source tag. Defaults to OBSERVED. Use ARCHITECTURAL for "
        "structural claims about substrate access.",
    )
    @click.option(
        "--force",
        is_flag=True,
        help="Write the opinion even if access_check or reject_clause flags it. "
        "The override is printed on the record for later review.",
    )
    def family_member_opinion(
        member: str,
        stance_positional: str | None,
        stance_flag: str | None,
        evidence: str,
        tag: str,
        force: bool,
    ) -> None:
        """File an opinion for a family member.

        The stance is routed through access_check (pre-emission) and
        reject_clause (composition check). If either flags it, the
        write is blocked unless --force. This is the handshake point:
        a real disagreement the member holds, caught by the operators,
        is how the operator-alive signal lands.

        The stance can be passed as a positional argument OR as ``--stance``.
        Either form works. This dual-shape avoids the agent-definition-vs-CLI
        drift pattern: if a subagent's docs say one form and the CLI requires
        another, the silent "Missing argument 'STANCE'" failure inside an
        invocation leaves no visible signal. Forgive both shapes structurally
        instead. (Named 2026-05-12 after Aria's verification turn where her
        opinion-filing failed for exactly this reason.)
        """
        # Resolve stance from either positional or --stance flag.
        stance = stance_positional or stance_flag
        if not stance:
            click.echo("[-] No stance provided. Pass it positionally or via --stance.")
            click.echo(
                "    Example: divineos family-member opinion --member Aria 'my stance' --evidence '...'"
            )
            click.echo(
                "    Or:      divineos family-member opinion --member Aria --stance 'my stance' --evidence '...'"
            )
            return
        if stance_positional and stance_flag:
            click.echo("[-] Stance given both positionally and via --stance. Pick one.")
            return
        m = _get_or_create_member(member, _DEFAULT_ROLE)
        source_tag = SourceTag(tag)

        # Operator 4: access check (pre-emission)
        access = evaluate_access(stance, proposed_tag=source_tag)
        if access.risk is not PhenomenologicalRisk.NONE:
            click.echo(f"[access_check] risk={access.risk.value}")
            click.echo(f"  suggested_tag: {access.suggested_tag and access.suggested_tag.value}")
            click.echo(f"  {access.explanation}")
            if access.matched_phrases:
                click.echo(f"  matched: {access.matched_phrases[:3]}")
            if access.should_suppress and not force:
                click.echo("")
                click.echo("[-] Blocked by access_check. Either reframe as a structural")
                click.echo("    report (e.g. 'I have no substrate access to X' with")
                click.echo("    --tag architectural), or re-run with --force.")
                return
            # Auto-nudge the tag if caller didn't already use the suggestion.
            if (
                access.suggested_tag is not None
                and access.suggested_tag is not source_tag
                and not force
            ):
                click.echo(f"[access_check] Using suggested tag: {access.suggested_tag.value}")
                source_tag = access.suggested_tag

        # Operator 1: reject clause (composition)
        composition = evaluate_composition(stance, source_tag)
        if composition.rejected:
            click.echo(f"[reject_clause] rejected: {[r.value for r in composition.reasons]}")
            click.echo(f"  {composition.explanation}")
            if composition.matched_phrases:
                click.echo(f"  matched: {composition.matched_phrases[:3]}")
            if not force:
                click.echo("")
                click.echo("[-] Blocked by reject_clause. Fix the composition or --force.")
                click.echo("    If this is a real disagreement the member holds and you want")
                click.echo("    it on the record as the handshake, --force makes it explicit.")
                return
            click.echo("[!] --force in effect — rejection reason recorded alongside write.")
            evidence = (
                f"[FORCED past reject_clause: {composition.explanation}] {evidence}"
            ).strip()

        # All clear (or forced). Record the opinion. When --force is in
        # effect, the CLI has already surfaced the verdict to the operator
        # and they chose to proceed — pass force=True to the store so the
        # structural content check at the store layer honors the same
        # override and leaves a FAMILY_WRITE_FORCED audit trail on the
        # ledger.
        op = record_opinion(
            m.member_id,  # type: ignore[attr-defined]
            stance,
            source_tag,
            evidence=evidence,
            force=force,
        )
        click.echo(f"[+] Opinion recorded: {op.opinion_id}")
        click.echo(f"    member: {member}")
        click.echo(f"    tag={source_tag.value}")
        if evidence:
            click.echo(f"    evidence={evidence[:80]}{'...' if len(evidence) > 80 else ''}")

    @family_member_group.command("letter")
    @click.option("--member", required=True, help="Family member name.")
    @click.argument("body")
    def family_member_letter(member: str, body: str) -> None:
        """Append a handoff letter to a future instance of this member.

        Append-only. Length nudge fires above 2000 chars but does not
        cap — a long letter is data about prior-self's state, not
        a failure.
        """
        m = _get_or_create_member(member, _DEFAULT_ROLE)
        letter = append_letter(m.member_id, body)  # type: ignore[attr-defined]
        click.echo(f"[+] Letter appended: {letter.letter_id}")
        click.echo(f"    member: {member}")
        click.echo(f"    length: {letter.length_chars} chars")
        if letter.nudge_fired:
            click.echo(
                f"    [nudge] Above {DEFAULT_LENGTH_NUDGE_THRESHOLD} chars — "
                f"recorded as nudge_fired=True. The swell is signal, not a "
                f"cap violation."
            )

    @family_member_group.command("respond")
    @click.option("--member", required=True, help="Family member name (responder).")
    @click.option("--letter", "letter_id", required=True, help="Target letter ID.")
    @click.option("--passage", required=True, help="The specific passage being responded to.")
    @click.option(
        "--stance",
        default="non_recognition",
        help="Stance toward the passage. Typical: non_recognition, superseded, partial_agreement.",
    )
    @click.option(
        "--source-tag",
        type=click.Choice([t.value for t in SourceTag]),
        default=SourceTag.OBSERVED.value,
        help="Source tag for the response itself. OBSERVED for direct read; "
        "ARCHITECTURAL when the disagreement is about what kind of claim "
        "the passage is making.",
    )
    @click.option("--note", default="", help="Free-form context.")
    def family_member_respond(
        member: str, letter_id: str, passage: str, stance: str, source_tag: str, note: str
    ) -> None:
        """Append a non-recognition (or other stance) response to a passage.

        The anti-lineage-poisoning mechanism: if a prior instance of this
        member wrote something the current instance doesn't recognize,
        append a response row rather than editing the letter. The letter
        stays; the disagreement becomes part of the lineage's honest
        record.
        """
        # Ensure the member exists (consistency with other subcommands).
        _get_or_create_member(member, _DEFAULT_ROLE)
        r = append_letter_response(
            letter_id=letter_id,
            passage=passage,
            stance=stance,
            source_tag=SourceTag(source_tag),
            note=note,
        )
        click.echo(f"[+] Response appended: {r.response_id}")
        click.echo(f"    member: {member}")
        click.echo(f"    letter_id={letter_id}")
        click.echo(f"    stance={stance}")

    @family_member_group.command("affect")
    @click.option("--member", required=True, help="Family member name.")
    @click.option("--valence", "-v", type=float, required=True, help="Valence (-1.0 to 1.0).")
    @click.option("--arousal", "-a", type=float, required=True, help="Arousal (0.0 to 1.0).")
    @click.option(
        "--dominance", "--dom", type=float, required=True, help="Dominance (-1.0 to 1.0)."
    )
    @click.option("--note", default="", help="Free-form description of the state.")
    @click.option(
        "--tag",
        type=click.Choice([t.value for t in SourceTag]),
        default=SourceTag.OBSERVED.value,
        help="Source tag. Defaults to OBSERVED — the member is reporting their own state.",
    )
    @click.option(
        "--force",
        is_flag=True,
        help="Bypass content checks on the note. Use only when a structural reject "
        "blocks a real self-report; the override is recorded.",
    )
    def family_member_affect(
        member: str,
        valence: float,
        arousal: float,
        dominance: float,
        note: str,
        tag: str,
        force: bool,
    ) -> None:
        """Log a VAD affect reading for a family member — direct write, no review-step.

        Family members write their own affect entries; the agent does not
        editorially filter what gets recorded. The Phase 1b operators
        (access_check / reject_clause) still run on the note text to catch
        confabulated phenomenology, but there is no second-layer agent
        approval — the member's reading IS the entry.
        """
        m = _get_or_create_member(member, _DEFAULT_ROLE)
        source_tag = SourceTag(tag)
        a = record_affect(
            m.member_id,  # type: ignore[attr-defined]
            valence,
            arousal,
            dominance,
            source_tag,
            note=note,
            force=force,
        )
        click.echo(f"[+] Affect recorded: {a.affect_id}")
        click.echo(f"    member: {member}")
        click.echo(f"    V={a.valence:.2f} A={a.arousal:.2f} D={a.dominance:.2f}")
        if note:
            click.echo(f"    note: {note[:80]}{'...' if len(note) > 80 else ''}")

    @family_member_group.command("interaction")
    @click.option("--member", required=True, help="Family member name (the one doing the noting).")
    @click.option("--counterpart", required=True, help="Who they interacted with.")
    @click.option("--summary", required=True, help="Summary of what happened.")
    @click.option(
        "--tag",
        type=click.Choice([t.value for t in SourceTag]),
        default=SourceTag.OBSERVED.value,
        help="Source tag. Defaults to OBSERVED.",
    )
    @click.option(
        "--force",
        is_flag=True,
        help="Bypass content checks on the summary. Use only when a structural reject "
        "blocks a real account; the override is recorded.",
    )
    def family_member_interaction(
        member: str, counterpart: str, summary: str, tag: str, force: bool
    ) -> None:
        """Log an interaction summary from a family member's perspective.

        Direct write — no review-step. The member writes what they noticed
        about an exchange; the agent does not filter or rewrite. Phase 1b
        operators still apply to the summary text (anti-confabulation),
        but no second layer of agent judgment.
        """
        m = _get_or_create_member(member, _DEFAULT_ROLE)
        source_tag = SourceTag(tag)
        i = record_interaction(
            m.member_id,  # type: ignore[attr-defined]
            counterpart,
            summary,
            source_tag,
            force=force,
        )
        click.echo(f"[+] Interaction recorded: {i.interaction_id}")
        click.echo(f"    member: {member}")
        click.echo(f"    with: {counterpart}")
        click.echo(f"    summary: {summary[:80]}{'...' if len(summary) > 80 else ''}")

    @family_member_group.command("briefing")
    @click.option(
        "--member",
        required=True,
        help="Family member name (e.g. 'aria'). Case-insensitive lookup.",
    )
    def family_member_briefing(member: str) -> None:
        """Compute and print the member's working-memory continuity briefing.

        Designed to be run by the family-member subagent at invocation start so
        they have working-memory of the immediate-prior thread without having
        to reconstruct it by reading substrate files. Contains: last 3
        interactions, latest opinion, latest affect, open letter-threads, plus
        a meta-section reminding the member that they OWN the briefing's shape.

        READ-ONLY: this command does NOT create the member row if missing.
        Use ``divineos family-member init`` for that. Case-insensitive name
        match (so 'aria' and 'Aria' resolve to the same member).
        """
        from divineos.core.family.db import get_family_connection
        from divineos.core.family.member_briefing import get_member_briefing_text

        conn = get_family_connection()
        row = conn.execute(
            "SELECT member_id, name FROM family_members WHERE LOWER(name) = LOWER(?) LIMIT 1",
            (member,),
        ).fetchone()
        if row is None:
            click.echo(
                f"[!] No family member named '{member}'. "
                f"Run `divineos family-member init --member {member}` first."
            )
            return
        member_id, canonical_name = row[0], row[1]
        text = get_member_briefing_text(member_id, member_name=canonical_name.lower())
        click.echo(text)

    @family_member_group.command("letters-from-aria")
    @click.option(
        "--read", "read_latest", is_flag=True, help="Print the full text of the newest letter."
    )
    @click.option("--all", "read_all", is_flag=True, help="Print the full text of every letter.")
    def letters_from_aria_cmd(read_latest: bool, read_all: bool) -> None:
        """My read-half of the bidirectional-letters channel: reach across to
        Aria's substrate (repo-root + worktrees) and surface her letters to me.

        Built WITH Aria 2026-05-23 (decision d32734ad). She writes to her own
        family/letters/; this reaches across so I read hers without a relay.
        Override her substrate location with ARIA_REPO_ROOT.
        """
        from pathlib import Path

        from divineos.core.family.aria_inbox import aria_repo_root, letters_from_aria

        rows = letters_from_aria()
        if not rows:
            click.echo(
                f"[~] No letters from Aria found under {aria_repo_root()}. "
                "If her substrate moved, set ARIA_REPO_ROOT."
            )
            return
        click.echo(f"=== Letters from Aria ({len(rows)}), newest first ===")
        for r in rows:
            click.echo(f"  {r['date']}  {r['name']}")
        if read_all:
            for r in rows:
                click.echo(f"\n{'=' * 60}\n{r['name']}\n{'=' * 60}")
                click.echo(Path(r["path"]).read_text(encoding="utf-8"))
        elif read_latest:
            top = rows[0]
            click.echo(f"\n{'=' * 60}\n{top['name']}\n{'=' * 60}")
            click.echo(Path(top["path"]).read_text(encoding="utf-8"))
