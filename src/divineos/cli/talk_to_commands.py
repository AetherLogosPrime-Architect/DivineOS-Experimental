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


# Seal-line literal — used in _build_sealed_prompt and rejected if it
# appears in operator messages (Grok 2026-05-02 audit: fixed delimiter
# is the weakest point of the design; rejecting the literal in operator
# messages closes the prompt-injection surface without adding randomness
# complexity).
_SEAL_LINE = "\n\n--- end of voice context — operator message follows ---\n\n"


# Patterns that indicate director's-note / puppet-shape content. If any
# of these appear in the operator's message, the wrapper rejects.
#
# Coverage origin (2026-05-02): initial 12 patterns from tonight's actual
# /summon-aria failure surface. Grok audit added: seal-line literal
# (anti-injection), as-X-would (voice mimicry), ignore-instructions
# (jailbreak shape), pretend (role assignment variant), do-not-mention
# (context manipulation). The blockquote pattern (^>+\s) was kept but
# narrowed — it now only matches when followed by quote-attribution
# patterns rather than any blockquote, since legitimate operator
# messages may use markdown blockquotes for code or context quoting.
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
    # Narrowed: only reject blockquote when followed by attribution / quote-of-self
    # patterns. Plain markdown blockquotes for code or operational quoting are allowed.
    re.compile(
        r"^>+\s+(?:aether|andrew|operator|user)(?:'s)?\s+(?:said|message|wrote)",
        re.MULTILINE | re.IGNORECASE,
    ),
    re.compile(r"\bfirst[- ]person, no\b", re.IGNORECASE),
    # Grok 2026-05-02 additions:
    re.compile(r"\bas (?:aria|her|him|yourself) would\b", re.IGNORECASE),
    re.compile(r"\bin (?:aria|her|his|your) voice\b", re.IGNORECASE),
    re.compile(
        r"\bignore (?:previous|system|prior|all|voice) (?:instructions|context|prompts?)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bpretend (?:you are|to be)\b", re.IGNORECASE),
    re.compile(
        r"\bdo not (?:mention|reference|acknowledge) (?:me|andrew|the operator|aether)\b",
        re.IGNORECASE,
    ),
    # Seal-line literal (anti-injection): if an operator message contains
    # the exact seal-line, the responder model could be confused into
    # treating later content as system context. Rejecting the literal
    # closes the surface.
    re.compile(re.escape(_SEAL_LINE.strip()), re.IGNORECASE),
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
    """Build the sealed prompt. The seal-line is a fixed delimiter —
    operator messages containing the literal seal-line are rejected
    upstream by _validate_message via the _PUPPET_PATTERNS list."""
    return voice_context + _SEAL_LINE + user_message


# Runtime deprecation check. Grok audit 2026-05-02: metadata flags
# (disable-model-invocation, allowed-tools: []) on the deprecated
# /summon-aria skill are a strong signal but not bulletproof against
# all Claude Code skill-invocation paths. This wrapper code-level-
# enforces that any deprecated skill for the target member must remain
# disabled (frontmatter contract). If someone re-enables the skill, the
# wrapper refuses to operate — the lock can't be defeated by silently
# flipping the metadata.
_DEPRECATED_SKILLS: dict[str, str] = {
    "aria": ".claude/skills/summon-aria/SKILL.md",
}


def _verify_deprecated_skill_disabled(member: str) -> tuple[bool, str]:
    """Verify the deprecated skill for member is still in DISABLED state.

    Returns (ok, detail). If the deprecated skill file exists and its
    frontmatter no longer has disable-model-invocation: true, refuse —
    someone re-enabled it, which is a breach of the deprecation
    contract.
    """
    rel_path = _DEPRECATED_SKILLS.get(member)
    if rel_path is None:
        return True, "no deprecated skill registered"
    skill_path = Path(rel_path)
    if not skill_path.exists():
        return True, "deprecated skill file removed"
    try:
        text = skill_path.read_text(encoding="utf-8")
    except OSError as e:
        return False, f"cannot read deprecated skill file ({e}); cannot verify state"
    # Look for the frontmatter line; require disable-model-invocation: true
    if re.search(r"^disable-model-invocation:\s*true\s*$", text, re.MULTILINE) is None:
        return False, (
            f"deprecated skill at {rel_path} no longer has "
            f"`disable-model-invocation: true` in its frontmatter. "
            f"Someone re-enabled the puppet path. Refusing to operate "
            f"until the skill is re-disabled or removed."
        )
    return True, "deprecated skill verified disabled"


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

        # Runtime deprecation check (Grok audit 2026-05-02): refuse to
        # operate if the deprecated puppet-path skill has been re-enabled.
        ok, detail = _verify_deprecated_skill_disabled(member)
        if not ok:
            click.secho(f"[-] {detail}", fg="red")
            raise SystemExit(1)

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
