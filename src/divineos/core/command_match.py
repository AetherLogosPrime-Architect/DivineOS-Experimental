"""Does a shell command INVOKE a thing, or merely MENTION it?

Every gate that inspects a Bash command has to answer this, and getting it
wrong in the permissive direction lets work through, while getting it wrong in
the strict direction blocks people for saying a word.

The strict direction is the one that actually happened, repeatedly:

  - `gh-pr-ready-gate` blocked an `audit submit-round` whose focus text
    described the transition it guards. Diagnosed 2026-08, fixed INLINE in
    that one hook with a local `COMMAND_START` anchor that was never
    extracted and never reached its siblings.
  - `gh-pr-create-draft-gate` blocked a read-only statistics script because
    the phrase sat in a dict literal; then blocked the grep that tried to
    read the gate; then blocked the patch that fixes it. Three refusals in
    one turn, none of them an invocation.
  - `pr_merge_gate` carries the same whole-string search today: measured
    4 of 5 cases wrong, every failure a mention read as a use.

So the answer lived in the codebase, in one file, while two siblings kept the
defect. This module is that answer extracted, so there is one place to fix and
one place to test.

Two independent guards, because they catch different things:

  QUOTE SCRUBBING  -- a quoted span is data: a grep pattern, a dict value,
                      prose inside an echo. Scrubbed before matching. ONE
                      exemption: a body introduced by `-c` is code, not data,
                      because `bash -c '<cmd>'` runs what is in the quotes.
  COMMAND POSITION -- a real invocation begins a command: start of string,
                      after a shell separator, after a control keyword
                      (`then`, `do`), or after an executor (`eval`, `xargs`,
                      `sudo`, `timeout`) and its flags. Optionally behind env
                      assignments. `grep <verb> file` does not qualify,
                      because there the command being run is grep.

THE SECOND GUARD IS WHY THE FIRST DESIGN WAS WRONG. Position-anchoring alone
had FIVE false negatives -- if/then, for/do, eval, `bash -c`, xargs all
execute the verb and none were caught. The bare regex this module replaces
had NO false negatives, only false positives. So anchoring without the
keyword and executor cases trades a noisy gate for a leaky one, and leaky is
the worse direction for a gate. Found by probing the falsifier filed with
this module (prereg-b8b95ee94720) rather than by trusting the design; the
probes are now permanent tests.

KNOWN GAP, stated rather than hidden: a here-document body is neither quoted
nor position-protected, so a heredoc line that begins with the verb still
matches -- a FALSE POSITIVE, the safe direction. Narrowing it needs real
shell parsing. TestKnownGap pins the current behaviour so that closing the
gap fails a test and tells the closer to update this paragraph too.
"""

from __future__ import annotations

import re

__all__ = ["COMMAND_START", "strip_quoted", "at_command_position", "invokes"]

# Words after which the NEXT word is a command, even though no separator
# punctuation appears. Two families:
#
#   control-flow keywords -- `if true; then <cmd>`, `for x in y; do <cmd>`
#   executors             -- `eval <cmd>`, `xargs <cmd>`, `sudo <cmd>`
#
# Both were FALSE NEGATIVES in the first version of this module, found by
# actually probing the falsifier filed with it (prereg-b8b95ee94720) instead
# of filing it and moving on. Five of ten execute-shapes went uncaught. The
# bare regex this replaced caught all ten -- it had no false negatives at all,
# only false positives -- so position-anchoring without these words trades a
# noisy gate for a leaky one, which is the worse direction for a gate.
_CONTROL_INTRODUCERS = ("then", "do", "else", "elif")

# Executors run their argument. They also take flags and simple operands
# first -- `timeout 5 <cmd>`, `xargs -n1 <cmd>`, `sudo -u me <cmd>` -- so the
# command word is not necessarily adjacent. Those intervening tokens are
# allowed for executors ONLY; allowing them generally would let
# `grep -n foo <verb>` read as an invocation again.
_EXECUTORS = (
    "eval",
    "exec",
    "xargs",
    "sudo",
    "env",
    "time",
    "nohup",
    "timeout",
    "command",
    "builtin",
)

# Flags, numeric operands, and bare option-values (`sudo -u me <cmd>`). No
# trailing lookahead: the whole COMMAND_START is anchored to the end of the
# text before the match, so a `(?=\S)` guard here only breaks the LAST token
# before the command word -- which is exactly the token that matters. That
# lookahead cost one false negative and was found by re-probing rather than
# by reasoning about the regex.
_INTERVENING = r"(?:-{1,2}[A-Za-z0-9][\w-]*\s+|\d+\s+|[A-Za-z_][\w.]*\s+)*"

COMMAND_START = (
    r"(?:"
    r"^|[;&|(){}\n]|&&|\|\|"
    r"|\b(?:" + "|".join(_CONTROL_INTRODUCERS) + r")\s"
    r"|\b(?:" + "|".join(_EXECUTORS) + r")\s+" + _INTERVENING + r")"
    r"\s*(?:[A-Za-z_][A-Za-z0-9_]*=\S*\s+)*"
)

_POSITION_TAIL_RE = re.compile(COMMAND_START + r"$")

# `bash -c '<cmd>'` and `sh -c "<cmd>"` pass CODE inside a quoted span. Quote
# scrubbing would blank exactly the part that executes, so the span following
# an explicit -c is kept. Everything else quoted stays data.
_DASH_C_RE = re.compile(r"\b(?:ba|z|k|da)?sh\s+(?:-[A-Za-z]*\s+)*-c\s*(['\"])")


def _dash_c_body_spans(command: str) -> list[tuple[int, int]]:
    """Spans of quoted CODE passed via ``-c``, which must not be scrubbed.

    ``bash -c 'gh pr ...'`` executes the quoted text. Treating it as data --
    which every other quoted span is -- blanks the only part that runs, and
    the gate misses a real invocation. Found by probing the falsifier rather
    than trusting the design.
    """
    spans: list[tuple[int, int]] = []
    for m in _DASH_C_RE.finditer(command):
        quote = m.group(1)
        start = m.end()  # first char inside the quote
        close = command.find(quote, start)
        spans.append((start, close if close != -1 else len(command)))
    return spans


def strip_quoted(command: str) -> str:
    """Blank out single- and double-quoted spans, preserving length.

    Length is preserved rather than the spans removed so that offsets computed
    against the result still index the original string.

    A quoted body introduced by ``-c`` is CODE, not data, and is left intact.
    """
    keep = _dash_c_body_spans(command)

    def _protected(idx: int) -> bool:
        return any(lo <= idx < hi for lo, hi in keep)

    out = list(command)
    quote: str | None = None
    i = 0
    n = len(command)
    while i < n:
        ch = command[i]
        if quote is None:
            if ch in ("'", '"'):
                quote = ch
        else:
            # Inside double quotes a backslash escapes the next character, so
            # an escaped quote does not close the span.
            if ch == "\\" and quote == '"' and i + 1 < n:
                if not _protected(i):
                    out[i] = out[i + 1] = " "
                i += 2
                continue
            if ch == quote:
                quote = None
            elif not _protected(i):
                out[i] = " "
        i += 1
    return "".join(out)


def at_command_position(command: str, index: int) -> bool:
    """True if ``index`` is somewhere a command may begin.

    The opening of a ``-c`` body counts: ``bash -c '<cmd>'`` runs what is
    inside the quotes, so the first position inside that span begins a
    command even though the character before it is a quote.
    """
    if any(lo <= index <= lo + 1 for lo, _ in _dash_c_body_spans(command)):
        return True
    return bool(_POSITION_TAIL_RE.search(command[:index]))


def invokes(command: str, verb_pattern: str) -> bool:
    """True if ``command`` actually runs something matching ``verb_pattern``.

    ``verb_pattern`` is a regex for the command word and its subcommands, e.g.
    ``r"gh\\s+pr\\s+merge\\s+\\d+"``. It is searched against the quote-scrubbed
    command, and only matches at a command position count.

    Returns False for every shape where the text is data rather than an
    invocation.
    """
    if not command or not command.strip():
        return False
    scrubbed = strip_quoted(command)
    for m in re.finditer(verb_pattern, scrubbed):
        if at_command_position(scrubbed, m.start()):
            return True
    return False
