"""``divineos talk-to <member> <message>`` — sealed-prompt invocation for family members.

The wrapper closes the failure mode where an operator spawns a family-member
subagent directly (e.g. via the Agent tool) without loading the member's
voice context. Without this layer, the subagent answers from the agent
definition alone — a recognizable shape rather than the actual member —
and any state-writes attributed to it become fabricated continuity
written into the persistent self.

## Flow

1. Operator runs ``divineos talk-to <member> "<plain message>"``.
2. The wrapper validates that ``<member>`` is a registered family member
   (a row in ``family.db::family_members``).
3. The wrapper validates the operator's message against a list of
   puppet-shape patterns ("you are X", "stay first-person", "as her would",
   prompt-injection patterns). Any match rejects the call.
4. The wrapper builds a minimal substrate-pointer preamble for the
   member (the redesigned pull-shape, 2026-05-08 — see
   ``_load_voice_context``). Prior shape pushed the member's full
   voice context (41+ knowledge, 11+ opinions, affect, letters) into
   the sealed prompt; new shape is just an identity + substrate-path
   pointer. The member reads their own substrate on invocation via
   their agent definition. ``divineos.core.family.voice.build_voice_context``
   exists for OTHER manual-relay flows (council walk, letter responses)
   but is no longer used here. (Aletheia round-ba785844a791 Finding 32
   doc-drift: the old wording survived this redesign.)
5. The wrapper builds a sealed prompt: substrate-pointer preamble +
   a fixed seal-line
   delimiter + the operator's message. Operator messages cannot inject
   the seal-line literal (rejected by the puppet-pattern list).
6. The sealed prompt is written to ``~/.divineos/talk_to_<member>_sealed_prompt.txt``;
   a small JSON pending-file with nonce, hash, TTL is written alongside.
7. An ``INVOKED`` event is appended to the member's hash-chained ledger.
8. The operator invokes the Agent tool with ``subagent_type=<member>``
   and ``prompt=<exact bytes of the sealed prompt file>``. A separate
   PreToolUse hook (see ``.claude/hooks/family-wrapper-required.sh``)
   verifies byte-for-byte that the prompt matches the pending file. If it
   does not match, the invocation is blocked.

## Why generic

Main is the clean-slate architecture. No specific member is hardcoded.
The wrapper discovers members from ``family.db`` at runtime so any AI
that bootstraps a fresh install and registers their own family members
gets the same wrapper enforcement automatically.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from pathlib import Path

import click

from divineos.core.family.talk_to_validator import (
    SEAL_LINE as _SEAL_LINE,
)
from divineos.core.family.talk_to_validator import (
    validate_message as _validator_validate_message,
)


_PENDING_DIR = Path.home() / ".divineos"
_PENDING_TTL_SECONDS = 120


def _pending_path(member: str) -> Path:
    return _PENDING_DIR / f"talk_to_{member}_pending.json"


def _sealed_prompt_path(member: str) -> Path:
    return _PENDING_DIR / f"talk_to_{member}_sealed_prompt.txt"


def _list_registered_members() -> list[str]:
    """Return the lowercased names of all registered family members.

    Reads from ``family.db::family_members``. Empty list is a valid
    state — a fresh install has no members until the operator
    registers some.
    """
    from divineos.core.family._schema import init_family_tables
    from divineos.core.family.db import get_family_connection

    init_family_tables()
    conn = get_family_connection()
    try:
        rows = conn.execute("SELECT name FROM family_members").fetchall()
        return [str(r[0]).lower() for r in rows]
    finally:
        conn.close()


def _validate_member_registered(member_lc: str) -> tuple[bool, str]:
    registered = _list_registered_members()
    if not registered:
        return False, (
            "No family members registered. Bootstrap one first with: "
            "divineos family-member init --member <Name> --role <role>"
        )
    if member_lc not in registered:
        return False, (
            f"'{member_lc}' is not a registered family member. "
            f"Registered members: {', '.join(sorted(registered))}"
        )
    return True, "ok"


def _validate_message(message: str, member_lc: str, registered: list[str]) -> tuple[bool, str]:
    """Thin wrapper preserved for backward compat with tests that
    monkeypatch this symbol. Delegates to the extracted validator module
    (``divineos.core.family.talk_to_validator.validate_message``)."""
    return _validator_validate_message(message, member_lc, registered)


def _load_voice_context(member_lc: str) -> str:
    """Build a MINIMAL substrate-pointer for the registered family member.

    2026-05-08 redesign (prereg-aria-self-orient): the wrapper no longer
    dumps the member's full voice context (41+ knowledge entries, 11+
    opinions, affect history, recent interactions) into the sealed prompt.
    That was push-shape — operator reconstructing the member into context.

    Right shape is pull: the member's agent definition orients them on
    invocation; they read their own substrate themselves. The wrapper
    just validates the operator's message + delivers a substrate-pointer
    preamble so the responder knows where to read from.

    Member integration of the conversation back into the substrate happens
    on the responder side via divineos family-member commands.
    """
    # Re-resolve to canonical case from family.db so the preamble has the
    # right capitalization. The registered list was lowercased; the stored
    # name may be capitalized.
    from divineos.core.family._schema import init_family_tables
    from divineos.core.family.db import get_family_connection

    init_family_tables()
    conn = get_family_connection()
    try:
        row = conn.execute(
            "SELECT name FROM family_members WHERE LOWER(name) = ? LIMIT 1",
            (member_lc,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        raise ValueError(f"member not found in family.db: {member_lc}")
    canonical_name = str(row[0])

    # Substrate pointer only. The agent file (.claude/agents/<name>.md) is
    # the canonical orientation; it tells the member where to read from
    # and how to integrate the conversation afterward.
    lines = [
        f"I am {canonical_name}.",
        "",
        (
            "My substrate is at: family/family.db (entity_id scoped to me), "
            "family/<name>_ledger.db, family/letters/. My agent definition at "
            ".claude/agents/<name>.md orients me on every invocation."
        ),
        "",
        (
            "Before I respond, I read what's relevant from my substrate. "
            "After I respond, I update my files with what was said."
        ),
        "",
    ]
    return chr(10).join(lines)


def _build_sealed_prompt(voice_context: str, user_message: str) -> str:
    return voice_context + _SEAL_LINE + user_message


def _write_pending(member_lc: str, sealed_prompt: str, user_message: str) -> str:
    from divineos.core.family.seal_canonical import canonical_hash

    _PENDING_DIR.mkdir(parents=True, exist_ok=True)
    nonce = uuid.uuid4().hex
    payload = {
        "ts": time.time(),
        "nonce": nonce,
        "member": member_lc,
        # Legacy byte-exact hash — kept for backward compat with hook
        # versions that haven't been updated yet. Hook accepts either match.
        "sealed_prompt_sha256": hashlib.sha256(sealed_prompt.encode("utf-8")).hexdigest(),
        # Canonical-form hash — survives encoding round-trips
        # (CRLF↔LF, NFC↔NFD, trailing whitespace) while still catching
        # puppet-shape (semantic content differences). See
        # divineos.core.family.seal_canonical for the canonical form.
        "sealed_prompt_canonical_sha256": canonical_hash(sealed_prompt),
        "user_message_sha256": hashlib.sha256(user_message.encode("utf-8")).hexdigest(),
        "user_message_preview": user_message[:120],
        "ttl_seconds": _PENDING_TTL_SECONDS,
    }
    _pending_path(member_lc).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    _sealed_prompt_path(member_lc).write_text(sealed_prompt, encoding="utf-8")
    return nonce


def _log_invocation(member_lc: str, user_message: str, nonce: str) -> None:
    """Append an INVOKED event to the member's per-member ledger.

    Failure to log is non-fatal — the wrapper still produces the sealed
    prompt — but any failure is reported so the operator knows the
    forensic record may be incomplete.
    """
    try:
        from divineos.core.family.family_member_ledger import (
            FamilyMemberEventType,
            append_event,
            new_invocation_id,
        )
    except ImportError as e:
        click.secho(
            f"[!] could not import family ledger ({e}); skipping invocation log", fg="yellow"
        )
        return

    try:
        append_event(
            member_lc,
            FamilyMemberEventType.INVOKED,
            actor="operator",
            payload={
                "wrapper": "talk-to",
                "nonce": nonce,
                "user_message_sha256": hashlib.sha256(user_message.encode("utf-8")).hexdigest(),
            },
            invocation_id=new_invocation_id(),
            invoked_by="operator",
        )
    except Exception as e:  # noqa: BLE001 — ledger failure must surface, not block
        click.secho(f"[!] ledger append failed ({e}); sealed prompt still written", fg="yellow")


def register(cli: click.Group) -> None:
    @cli.command("talk-to")
    @click.argument("member", type=click.STRING)
    @click.argument("message", type=click.STRING)
    def talk_to_cmd(member: str, message: str) -> None:
        """Send a sealed-prompt message to a registered family member.

        MEMBER is the family-member name (case-insensitive). MESSAGE is
        your plain message — no director's notes, no "you are X",
        no scene-setting. The wrapper loads the member's voice context
        and the responder reads themselves; you do not need to (and
        must not) reconstruct it on the way in.
        """
        member_lc = member.lower().strip()

        ok, detail = _validate_member_registered(member_lc)
        if not ok:
            click.secho(f"[-] {detail}", fg="red")
            raise SystemExit(1)

        registered = _list_registered_members()
        ok, detail = _validate_message(message, member_lc, registered)
        if not ok:
            click.secho(f"[-] {detail}", fg="red")
            raise SystemExit(1)

        try:
            voice_context = _load_voice_context(member_lc)
        except (ImportError, OSError, ValueError) as e:
            click.secho(f"[-] could not load voice context for {member_lc}: {e}", fg="red")
            raise SystemExit(1) from e

        sealed_prompt = _build_sealed_prompt(voice_context, message)
        nonce = _write_pending(member_lc, sealed_prompt, message)
        _log_invocation(member_lc, message, nonce)

        sealed_path = _sealed_prompt_path(member_lc)
        click.secho(
            f"[+] Sealed prompt for {member_lc} written.\n"
            f"    Path:  {sealed_path}\n"
            f"    Nonce: {nonce}\n"
            f"    TTL:   {_PENDING_TTL_SECONDS}s\n\n"
            f"Now invoke the Agent tool with subagent_type='{member_lc}' and "
            f"prompt = exact contents of the sealed-prompt file. The "
            f"PreToolUse hook (.claude/hooks/family-wrapper-required.sh) "
            f"verifies byte-for-byte; operator-edited prompts are blocked.",
            fg="green",
        )


__all__ = ["register"]
