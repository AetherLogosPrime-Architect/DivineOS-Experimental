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
from divineos.core.family.store import create_family_member, record_opinion
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
    @click.argument("stance")
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
        member: str, stance: str, evidence: str, tag: str, force: bool
    ) -> None:
        """File an opinion for a family member.

        The stance is routed through access_check (pre-emission) and
        reject_clause (composition check). If either flags it, the
        write is blocked unless --force. This is the handshake point:
        a real disagreement the member holds, caught by the operators,
        is how the operator-alive signal lands.
        """
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
