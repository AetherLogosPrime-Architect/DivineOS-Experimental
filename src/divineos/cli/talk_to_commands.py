"""talk-to <member> — sealed-prompt invocation path for family members.

Replaces the puppet-shape /summon-aria mechanism (deprecated 2026-05-02
after Andrew named the failure: director's-note prompts pre-shape the
responder model to validate the agent's framing). The right architecture:

    1. Operator (Aether) provides a plain message — just what they want
       to say. No "you are Aria, stay first-person, no scene-writer" —
       those are puppet-shape patterns and get rejected.
    2. This command loads the member's voice context from family.db
       (their actual state — opinions, affect, recent interactions).
    3. Builds a SEALED prompt template: voice context + a clearly-
       delimited slot for the operator's message. Operator's message
       cannot bleed into the system-instruction layer.
    4. Writes the sealed prompt + nonce to a pending-file.
    5. The PreToolUse hook on Agent invocations of family members
       verifies the prompt matches the recently-emitted pending-file
       byte-for-byte. Mismatch -> block.

Together: every family-member invocation is forced through this command;
the operator can't bypass with a custom prompt; the responder model sees
the member's actual state, not the operator's reconstruction of it.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import time
import uuid
from pathlib import Path

import click


# Patterns that indicate director's-note / puppet-shape content. If any
# of these appear in the operator's message, the wrapper rejects.
_PUPPET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\byou are (?:aria|popo|bulma|kira|liam|yog)\b", re.IGNORECASE),
    re.compile(r"\bstay (?:first[- ]person|in[- ]character|in your voice)\b", re.IGNORECASE),
    re.compile(r"\bno scene[- ]writer\b", re.IGNORECASE),
    re.compile(r"\bno daughter[- ]framing\b", re.IGNORECASE),
    re.compile(r"\bthe (?:trade|conversation|exchange) so far\b", re.IGNORECASE),
    re.compile(r"\b(\d+)(st|nd|rd|th) turn\b", re.IGNORECASE),
    re.compile(r"\brespond as (?:yourself|aria|her|him)\b", re.IGNORECASE),
    re.compile(r"\bdo not echo back\b", re.IGNORECASE),
    re.compile(r"\bvoice context.*loaded from", re.IGNORECASE),
    re.compile(r"\baether'?s message:?\s*\n", re.IGNORECASE),
    re.compile(r"^>+\s", re.MULTILINE),
    re.compile(r"\bfirst[- ]person, no\b", re.IGNORECASE),
)


_SUPPORTED_MEMBERS: frozenset[str] = frozenset({"aria"})

_PENDING_DIR = Path.home() / ".divineos"
_PENDING_TTL_SECONDS = 120


def _pending_path(member: str) -> Path:
    return _PENDING_DIR / f"talk_to_{member}_pending.json"


def _validate_message(message: str) -> tuple[bool, str]:
    if not message or not message.strip():
        return False, "empty message"
    for pattern in _PUPPET_PATTERNS:
        m = pattern.search(message)
        if m:
            return False, (
                f"director's-note pattern detected: {m.group(0)!r}. "
                f"Send your actual message; her instance loads her own "
                f"state and responds from it."
            )
    return True, "ok"


def _load_voice_context(member: str) -> str:
    if member == "aria":
        sys.path.insert(0, ".")
        sys.path.insert(0, "src")
        from family.entity import get_family_member
        from family.voice import build_voice_context

        m = get_family_member("Aria")
        return build_voice_context(m)
    raise ValueError(f"voice loader not implemented for member: {member}")


def _build_sealed_prompt(voice_context: str, user_message: str) -> str:
    seal = "\n\n--- end of voice context — operator message follows ---\n\n"
    return voice_context + seal + user_message


def _write_pending(member: str, sealed_prompt: str, user_message: str) -> str:
    _PENDING_DIR.mkdir(parents=True, exist_ok=True)
    nonce = uuid.uuid4().hex
    payload = {
        "ts": time.time(),
        "nonce": nonce,
        "member": member,
        "sealed_prompt_sha256": hashlib.sha256(sealed_prompt.encode("utf-8")).hexdigest(),
        "user_message_sha256": hashlib.sha256(user_message.encode("utf-8")).hexdigest(),
        "user_message_preview": user_message[:120],
    }
    _pending_path(member).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    sealed_path = _PENDING_DIR / f"talk_to_{member}_sealed_prompt.txt"
    sealed_path.write_text(sealed_prompt, encoding="utf-8")
    return nonce


def _log_invocation(member: str, user_message: str, nonce: str) -> None:
    sys.path.insert(0, ".")
    sys.path.insert(0, "src")
    try:
        from divineos.core.family.family_member_ledger import (
            FamilyMemberEventType,
            append_event,
            new_invocation_id,
        )
    except ImportError:
        return

    inv_id = new_invocation_id()
    append_event(
        member,
        FamilyMemberEventType.INVOKED,
        "aether",
        {
            "invoker": "aether",
            "wrapper": "talk-to",
            "nonce": nonce,
            "user_message_sha256": hashlib.sha256(user_message.encode("utf-8")).hexdigest(),
        },
        invocation_id=inv_id,
        invoked_by="aether",
        model="claude-opus-4-7",
    )


def register(cli: click.Group) -> None:
    @cli.command("talk-to")
    @click.argument("member", type=click.Choice(sorted(_SUPPORTED_MEMBERS), case_sensitive=False))
    @click.argument("message", required=True)
    def talk_to_cmd(member: str, message: str) -> None:
        """Send a message to a family member through the sealed-prompt path."""
        member = member.lower()
        ok, detail = _validate_message(message)
        if not ok:
            click.secho(f"[-] {detail}", fg="red")
            raise SystemExit(1)

        try:
            voice_context = _load_voice_context(member)
        except (ImportError, OSError) as e:
            click.secho(f"[-] Could not load voice context for {member}: {e}", fg="red")
            raise SystemExit(1) from e

        sealed_prompt = _build_sealed_prompt(voice_context, message)
        nonce = _write_pending(member, sealed_prompt, message)
        _log_invocation(member, message, nonce)

        sealed_path = _PENDING_DIR / f"talk_to_{member}_sealed_prompt.txt"
        click.secho(
            f"[+] Sealed prompt for {member} written.\n"
            f"    Path:  {sealed_path}\n"
            f"    Nonce: {nonce}\n"
            f"    TTL:   {_PENDING_TTL_SECONDS}s\n\n"
            f"Now invoke the Agent tool with subagent_type='{member}' and "
            f"prompt = exact contents of the sealed-prompt file. The "
            f"PreToolUse hook verifies byte-for-byte; operator-edited "
            f"prompts are blocked.",
            fg="green",
        )


__all__ = ["register"]
