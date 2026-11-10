"""Consolidated PreToolUse gate: one Python invocation for every gate check.

Invoked from .claude/hooks/require-goal.sh as ``python -m divineos.hooks.pre_tool_use_gate`` (not
wired into the CLI pipeline). One interpreter run replaces the old five-plus ``python -c`` calls,
each of which paid ~200ms of startup plus import cost: hook time per tool call fell from ~1.2s to
~200-300ms.

Order in main(): ownership block, bypass check (read-only and bootstrap commands skip every gate),
overdue-prereg block, then _check_gates, first deny wins: 0 exploration tag and numbering walls; 1
briefing recall; 1.2 mansion quiet; 1.4 compass staleness; 1.45 hedge; 1.47 compass after a virtue
event; 1.48 stale engagement; 1.5 unlogged correction; then the soft cluster (2 goal, 3 pull, 4
engagement as measurement only, 4.5 consultation) whose denials are combined into one message; 6
retry blocker; 7 context governor.

Output: a JSON decision on stdout, empty stdout = allow, always exit 0 (Claude Code carries the
decision in the JSON, not the exit code). Machinery that fails open does so on purpose and says so
(see _record_gate_failure).

The older history behind these notes is archived at
docs/archives/code_notes/pre_tool_use_gate_notes_2026-11-06.md.
"""

from __future__ import annotations

# Guardrail marker: tests/test_guardrail_marker_consistency.py asserts every file marked True is
# listed in scripts/guardrail_files.txt, so a refactor cannot silently drop this self-enforcement
# code from multi-party review.
__guardrail_required__ = True

import json
import re
import shlex
import sys
from pathlib import Path
from typing import Any

from divineos.core.command_parsing import CD, blank_quoted_spans, strip_prefixes_raw


# Chain-shape metacharacters (;, &&, ||, backtick, $(). They count as chain operators only OUTSIDE
# quotes: a semicolon inside a quoted argument is ordinary text and must not break the remedy
# exemption. Used by _is_safe_remedy_invocation.
_CHAIN_SHAPE_METACHARS: tuple[str, ...] = (";", "&&", "||", "`", "$(")


def _strip_shell_quoted(cmd: str) -> str:
    """Return cmd with the CONTENT of quoted regions replaced by 'Q',
    preserving the outside-quotes structure intact.

    Handles: 'single-quoted', "double-quoted", backslash-escapes.
    Fail-closed: if a quote is never closed, raises ValueError so the
    caller can reject the command.

    Example: 'divineos correction "text; and" && rm' ->
             'divineos correction "Q" && rm'
    """
    out: list[str] = []
    i = 0
    n = len(cmd)
    while i < n:
        ch = cmd[i]
        if ch == "\\" and i + 1 < n:
            # Backslash-escape — output the escape + next char verbatim.
            out.append(cmd[i : i + 2])
            i += 2
            continue
        if ch in ('"', "'"):
            quote = ch
            out.append(quote)
            i += 1
            # Consume until closing quote, treating backslash-escapes.
            while i < n:
                if cmd[i] == "\\" and quote == '"' and i + 1 < n:
                    i += 2
                    continue
                if cmd[i] == quote:
                    out.append("Q")  # placeholder for quoted content
                    out.append(quote)
                    i += 1
                    break
                i += 1
            else:
                raise ValueError(f"unclosed {quote} in command")
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _has_unquoted_chain_shape(cmd: str) -> bool:
    r"""Return True iff cmd contains a chain-shape metachar OUTSIDE quotes. Quoted content is replaced
    by a placeholder first, so a real chain like `remedy && rm -rf ~` is told apart from punctuation
    in a quoted argument like `divineos correction "gates never retired; only fixed"`. Fail-CLOSED:
    an unclosed quote counts as chain-shape present.

    Pinned by tests/test_pre_tool_use_gate_remedy_exemption.py: a quoted semicolon is safe; `&& rm`,
    a backtick substitution and `$(...)` are chains; a pipe is allowed; an unclosed quote is a
    chain.
    """
    try:
        stripped = _strip_shell_quoted(cmd)
    except ValueError:
        return True  # fail closed on unclosed quote
    chain_re = re.compile(r";|&&|\|\||`|\$\(")
    return bool(chain_re.search(stripped))


_LEADING_CD_RE = re.compile(
    r"""^\s*cd\s+
        (?:
            (?:"[^"]*"|'[^']*')\s*&&\s*   # quoted path: && may abut the quote
          | [^\s&;|<>()`$]+ \s+&&\s*      # bare path: && MUST be space-separated
        )
    """,
    re.VERBOSE,
)
# The bare-path branch demands whitespace before `&&`, and that requirement is load-bearing
# (test_metachar_paths_are_not_stripped). Without it, `cd /tmp&&rm && divineos correction "x"`
# strips a wrong prefix and leaves `rm` at the head. Not stripping is always the safe direction (an
# unstripped prefix fails the head check and refuses); stripping wrongly is what could ever permit.


# Characters that must not appear in a prefix the gate is willing to discard. A literal tuple, not a
# pattern: nothing here needs matching, it needs membership.
_UNSAFE_IN_DISCARDED_PREFIX = (">", "<", "`", "$", "(", ")", ";", "|", "&")


def _strip_leading_cd(cmd: str) -> str:
    """Remove ONE leading `cd <path> &&` prefix, if present. Else unchanged.

    Bounded on purpose: a single strip, no recursion. `cd a && cd b && rm`
    keeps its second cd in head position and therefore still fails the
    remedy-head check. A path containing shell metacharacters is not matched
    at all, so nothing exotic slips through the strip on its way to the
    chain-shape check that runs after.
    """
    return _LEADING_CD_RE.sub("", cmd, count=1)


def _is_safe_remedy_invocation(cmd: str, allowed_heads: tuple[str, ...]) -> bool:
    """Return True iff cmd is a legitimate invocation of a remedy command: (1) cmd before any pipe
    starts with one of allowed_heads; (2) no chain-shape metachar outside quotes; (3) a pipe after
    the remedy is allowed (piping to head or tail is the common case). Shared by the compass and
    correction exemptions.
    """
    if not cmd:
        return False

    # Leading-cd handling. The remedy must be the FIRST thing in the command, but a habitual `cd
    # "<repo>" && divineos correction "..."` puts `cd` in head position, which blocked the very
    # command the gate's own message tells me to run. There are TWO barriers and both must be
    # handled: the head check, and the chain-shape check (`cd X && ...` genuinely is a chain). So
    # prefixes come off with strip_prefixes_raw (quoting preserved) and BOTH checks run on the same
    # real command. Re-joining shlex tokens instead would lose the quoting and turn a semicolon
    # inside an evidence string into a false chain.
    #
    # The shared stripper is wider than this gate may be: it removes EVERY leading cd whatever the
    # path holds, so `cd a && cd b && remedy` or a path hiding a redirection came back a bare remedy
    # and was allowed. Here only ONE leading cd is discarded, and a prefix containing any of > < ` $
    # ( ) ; | & is not discarded. The narrowness lives here, not in the shared module, because other
    # callers want the liberal reading and this gate must not have it.
    real = strip_prefixes_raw(cmd)
    if not real:
        return False

    # THE SHARED STRIPPER IS WIDER THAN THE GUARD IT REPLACED, and this is
    # where that matters. Caught by my own tests failing on the merge,
    # 2026-08-24: strip_prefixes_raw removes EVERY leading cd and does not care
    # what is in the path, so both of these came back a bare remedy and were
    # allowed — two chained commands treated as one, and a redirection
    # discarded along with the directory change.
    #
    # The local helper it replaced refused both by construction: one strip
    # only, and no match at all on a metacharacter path. Importing the shared
    # helper was right (F114 — one home for "the head of a command is not its
    # first character") and it silently widened the security boundary. Being
    # liberal is correct in a parser and wrong in this gate.
    #
    # So the narrowness lives here rather than in the shared module: other
    # callers want the liberal reading, and this one must not have it.
    discarded = cmd[: len(cmd) - len(real)] if cmd.endswith(real) else ""
    if discarded:
        head, sep, tail = discarded.partition("&&")
        if not sep or tail.strip():
            return False
        if any(ch in head for ch in _UNSAFE_IN_DISCARDED_PREFIX):
            return False
    # Split on pipe once — remedy must be the first pipeline segment.
    head_segment = re.split(r"\|", real, maxsplit=1)[0].strip()
    if not any(head_segment.startswith(h) for h in allowed_heads):
        return False
    # Chain-shape check, quote-aware, on the command with only the directory
    # change removed. Any other chain operator survives into `real` — so
    # `cd X && remedy && rm -rf ~` is still refused on the appended chain.
    if _has_unquoted_chain_shape(real):
        return False
    return True


# The letter bell is a listener, not work: it writes only its own dotfiles and decides nothing, and
# Dad had to ask 24 times for it to stay on, so re-arming it passes this gate. Exact command only:
# this repo's script path, ONE seat word, no pipe, no chain. The word must be THIS seat (a bell run
# for another seat silently replaces her bell while every check reports healthy), and a leading cd
# may only land on this repository's root (the script path is relative, so a cd elsewhere would run
# another checkout's copy ungated). Either unknown means held.
_DOORBELL_RE = re.compile(r"^bash (?:\./)?scripts/letter_doorbell\.sh ([a-z]+)$")


def _cd_lands_on_this_repo(prefix: str) -> bool:
    from divineos.core.auto_commit import find_repo_root

    root = find_repo_root(Path(__file__))
    if root is None:
        return False  # both-empty: unknown root also means hold, fail closed
    try:
        parts = shlex.split(prefix.partition("&&")[0])
    except ValueError:
        return False
    if len(parts) != 2 or parts[0] != "cd":
        return False
    target = parts[1]
    drive = re.match(r"^/([A-Za-z])(/.*)?$", target)  # Git Bash /c/... form
    if drive:
        target = f"{drive.group(1)}:{drive.group(2) or '/'}"
    try:
        return Path(target).resolve() == root
    except OSError:
        return False


def _is_doorbell_rearm(cmd: str) -> bool:
    if not _is_safe_remedy_invocation(cmd, ("bash ",)):
        return False
    whole = cmd.strip()
    real = strip_prefixes_raw(whole).strip()
    match = _DOORBELL_RE.match(real)
    if not match:
        return False
    from divineos.core.sibling_audit_rounds import this_seat

    seat = this_seat()
    if seat is None or match.group(1) != seat:
        return False
    prefix = whole[: len(whole) - len(real)].strip() if whole.endswith(real) else whole
    return not prefix or _cd_lands_on_this_repo(prefix)


def _load_bypass_subcommands() -> frozenset[str]:
    """Load the canonical bypass list from scripts/hook_bypass_commands.txt: one ``divineos
    <subcommand>`` per line, ``#`` comments, blank lines ignored; only the subcommand word is kept.
    One source of truth shared with .claude/hooks/_lib.sh is_bypass_command, so other PreToolUse
    hooks cannot drift from it (they once blocked documented bypass commands before this module saw
    them). Fail-soft: a missing or unreadable file returns the bootstrap minimum so the system stays
    bootable.
    """
    from pathlib import Path

    # Walk up from this file to find repo root (src/divineos/hooks/<file>).
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "scripts" / "hook_bypass_commands.txt"
        if candidate.exists():
            try:
                subs: set[str] = set()
                for line in candidate.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    # Format: "divineos <subcommand>"
                    parts = line.split(None, 1)
                    if len(parts) == 2 and parts[0] == "divineos":
                        subs.add(parts[1].strip())
                if subs:
                    return frozenset(subs)
            except OSError:
                pass
            break
    # Fail-soft minimum to keep bootstrap working.
    return frozenset({"briefing", "ask", "recall", "hud", "context", "init", "preflight"})


_BYPASS_DIVINEOS_SUBCOMMANDS = _load_bypass_subcommands()

# Dev / read-only commands that don't require gates
_DEV_PREFIXES = (
    "git ",
    "pytest ",
    "python -m pytest",
    "ls ",
    "cat ",
    "head ",
    "diff ",
    "echo ",
    "pip ",
    "cd ",
    "pwd",
    "cp ",
    "copy ",
    "ruff ",
)

# Match `divineos <subcmd>`, also `divineos.exe` (the Windows venv path form), optionally quoted and
# path-prefixed, e.g. `"./.venv/Scripts/divineos.exe" goal add`. ANCHORED with .match(), never
# .search(): a safe word appearing mid-command is not a safe command (`divineos briefing; rm -rf
# /tmp/x` must not bypass). Compound commands are refused separately by _has_compound_shape. The
# template: allow narrowly, deny broadly.
_DIVINEOS_SUBCMD_RE = re.compile(
    # optional leading whitespace, optional (possibly quoted) path prefix
    # ending in / or \, then divineos with optional .exe and optional
    # closing quote, then required whitespace + subcommand word.
    r"^\s*"
    r"(?:[\"\']?[\w./\\:-]*[/\\])?"
    r"divineos(?:\.exe)?[\"\']?"
    r"\s+(\w[\w-]*)"
)

# Shell metacharacters that chain, pipe or substitute. If any appear, this is not a simple bypass:
# the bypass is for 'run this safe command', not 'run this safe command AND whatever follows'.
_SHELL_COMPOUND_CHARS = (";", "&&", "||", "|", "`", "$(")


# Named character constants, so the quote-context scanner below reads as shell semantics and not as
# a wall of escaped punctuation.
_SQ = chr(39)  # single quote
_DQ = chr(34)  # double quote
_BACKTICK = chr(96)
_SUBST_SIGIL = chr(36)  # dollar — opens a substitution when followed by (
_SUBST_OPEN = chr(40)  # open paren
_QUOTE_CHARS = (_SQ, _DQ)
# Chaining / piping operators. Inert inside either kind of quote.
_UNQUOTED_OPERATOR_CHARS = (chr(59), chr(124), _BACKTICK)

# The ampersand is handled apart from the operator tuple: it is an operator when doubled (chains) or
# when it backgrounds, but `2>&1` is an fd redirect and must stay a bypass candidate. The
# discriminator is the preceding character.
_AMP = chr(38)
_REDIRECT = chr(62)  # '>' — what precedes the ampersand in an fd redirect


def _has_compound_shape(cmd: str) -> bool:
    """True if the command contains shell metacharacters that chain, pipe or substitute, so it is NOT a
    simple bypass candidate (even a safe head may chain into a dangerous tail). An explicit
    quote-state scanner, so operator characters inside a quoted argument do not defeat a bypass the
    subcommand qualifies for. Rationale, exploit cases and why not shlex:
    docs/gate_quote_context_parser_2026-08-01.md. Fails CLOSED on an unterminated quote.
    """
    state: str | None = None
    i = 0
    n = len(cmd)
    while i < n:
        ch = cmd[i]
        if state is None:
            if ch == "\\":
                i += 2
                continue
            if ch in _QUOTE_CHARS:
                state = ch
            elif ch == _AMP:
                # Chaining (&&) or backgrounding is an operator; an fd
                # redirect (2>&1) is not. See the _AMP comment above.
                if cmd[i + 1 : i + 2] == _AMP or (i > 0 and cmd[i - 1] != _REDIRECT):
                    return True
            elif ch in _UNQUOTED_OPERATOR_CHARS:
                return True
            elif ch == _SUBST_SIGIL and cmd[i + 1 : i + 2] == _SUBST_OPEN:
                return True
        elif state == _SQ:
            # Single quotes: everything literal, backslash included.
            if ch == _SQ:
                state = None
        else:
            # Double quotes: chaining operators are inert here, but
            # substitution still expands. That asymmetry is the F31
            # exploit and must survive this rewrite.
            if ch == "\\":
                i += 2
                continue
            if ch == _DQ:
                state = None
            elif ch == _BACKTICK:
                return True
            elif ch == _SUBST_SIGIL and cmd[i + 1 : i + 2] == _SUBST_OPEN:
                return True
        i += 1
    return state is not None


# A leading `cd DIR && ` prefix, DIR being a quoted path or a token free of shell metacharacters.
# Every Bash call starts with `cd "path" && ...`, and `cd` is the one legitimate compound prefix: it
# executes nothing else. The quoted-DIR branch excludes `$` and backtick, because the shell expands
# `$(...)` INSIDE double quotes before `cd` runs: `cd "$(rm -rf /)" && divineos ask` would otherwise
# bypass. `;` and `&&` inside quotes are inert.
_CD_PREFIX_RE = re.compile(r"^\s*cd\s+(?:[\"'][^\"'$`]+[\"']|[^\s;&|`$]+)\s*&&\s*")


# Safe output-filter tails: a bypass command may end in any number of ` | <filter> [args]` segments,
# each filter on _SAFE_OUTPUT_FILTERS, plus an optional ` 2>&1`, so `divineos ask "topic" | head
# -20` still bypasses (blocking it made the gate refuse its own documented remedy). Args may not
# contain shell metacharacters (;, &&, backtick, $(, >, <), so awk or sed on the list cannot smuggle
# a payload. The list is closed; out of scope: `| tee` (writes), `| xargs CMD`, `| bash`, `| sh`, `|
# python`.
_SAFE_OUTPUT_FILTERS = frozenset(
    {"head", "tail", "grep", "less", "more", "cat", "wc", "sort", "uniq", "awk", "sed"}
)


def _strip_safe_output_tail(cmd: str) -> str:
    """Strip a trailing ` | SAFE_FILTER ARGS...` chain and/or ` 2>&1` from cmd; unchanged if the tail
    does not match the safe pattern. ``2>&1`` may sit at the very end or between the command and the
    first pipe (``cmd 2>&1 | tail -N``, what most operators type). After the pipe segments are
    stripped, a middle ``2>&1`` is trailing, so it is stripped too and callers see a residue-free
    command; string operations, not a new regex, for that second strip.
    """
    stripped = re.sub(r"\s+2>&1\s*$", "", cmd)
    while True:
        m = re.search(r"\s\|\s+(\w+)((?:\s+[^|;&`$<>]+)?)\s*$", stripped)
        if not m:
            break
        filter_name = m.group(1)
        args_segment = m.group(2) or ""
        if filter_name not in _SAFE_OUTPUT_FILTERS:
            return cmd
        if any(bad in args_segment for bad in (";", "&&", "||", "`", "$(", ">", "<")):
            return cmd
        stripped = stripped[: m.start()].rstrip()
    # After the pipe strip, a ``2>&1`` that was in the middle is now trailing: string operations, no
    # regex.
    stripped = stripped.rstrip()
    if stripped.endswith(" 2>&1"):
        stripped = stripped[: -len(" 2>&1")].rstrip()
    return stripped


def _strip_cd_prefix(cmd: str) -> str:
    """If ``cmd`` starts with a safe ``cd DIR &&`` prefix, strip it and return the remainder; else
    unchanged. Delegates to command_parsing, the one home for "the head of a command is not its
    first character". ``kinds=(CD,)`` on purpose, not the default: on the bypass path a leading
    ``NAME=value`` must NOT be discarded, or ``DIVINEOS_SKIP_TESTS=1 divineos ...`` would bypass
    every gate with the env var riding along. The shared pattern carries the same exclusions as
    _CD_PREFIX_RE (no `$` or backtick in the directory); without them ``cd "$(curl attacker)" &&
    <remedy>`` was stripped to a clean remedy and called safe.
    """
    return strip_prefixes_raw(cmd, kinds=(CD,))


def _is_bypass_command(cmd: str) -> bool:
    """True if the command should skip all gates (read-only / bootstrap). It must BE a safe command,
    not merely contain a safe word; compound commands never bypass, except for the `cd DIR &&
    SAFE_CMD` working-directory preface.
    """
    if not cmd:
        return False
    # Strip `cd DIR && `, the one legitimate compound prefix; any other compound char still fails
    # the bypass.
    cmd = _strip_cd_prefix(cmd)
    # Strip a safe output-filter tail (closed allow-list; see _strip_safe_output_tail).
    cmd = _strip_safe_output_tail(cmd)
    # F22 gate: compound commands are never bypass candidates, even if
    # they contain a safe word. `divineos briefing; rm -rf /tmp/x` must
    # NOT bypass — the safe word is a decoy, not the command.
    if _has_compound_shape(cmd):
        return False
    # The context-governor block message documents `touch ~/.divineos/context_consolidated.json` as
    # its escape hatch when extract errors, and that touch is itself a substrate write, so the gate
    # would block its own documented escape. Match the consolidation marker by its path suffix (~,
    # $HOME, /c/Users/, /home/, backslash Windows paths). The marker only signals that extract was
    # attempted; allowing this write weakens nothing.
    if (
        ".divineos/context_consolidated.json" in cmd
        or ".divineos\\context_consolidated.json" in cmd
    ):
        return True
    # The correction-gate block message names three remedies (`divineos learn`, `divineos
    # correction`, `python scripts/clear_correction_marker.py`) and says the gate exempts each; it
    # exempted two. The third is the remedy FOR a broken CLI (mid-rebase, import error), exactly
    # when the other two cannot run; blocking it was the root cause of psf-01d5f2af ("engagement
    # gate blocks even clear-commands"), filed 65 times in July. Exempting it removes no discipline:
    # the script still requires a named reason of at least 30 characters and logs every use to
    # ~/.divineos/cli_broken_escapes.jsonl.
    if "clear_correction_marker.py" in cmd:
        return True
    # divineos bypass subcommands — anchored to command start (F22 fix).
    match = _DIVINEOS_SUBCMD_RE.match(cmd)
    if match and match.group(1) in _BYPASS_DIVINEOS_SUBCOMMANDS:
        return True
    # dev / read-only prefixes — already anchored via startswith.
    for prefix in _DEV_PREFIXES:
        if cmd.startswith(prefix):
            return True
    return False


# Path exemption for low-friction (low-gravity) writes: exploration/ (operator directive: no blocks
# there) and other relational or first-person surfaces: letters to family, mansion writing. These
# are not father-facing-claim shape; the fabrication detector and the engagement-discipline gates
# are calibrated for code and architecture work and would block exactly the register these paths
# exist for. The exemption is from path-blocks-tool-use only: the Stop hook still scans output and
# writes markers (forensic record kept), and mansion fabrication stays out of the OS because
# marker-firing is untouched. A frozen tuple; adding a path is a load-bearing calibration decision
# and should be reviewed.
_LOW_FRICTION_PATH_SEGMENTS: tuple[str, ...] = (
    "/exploration/",  # First-person free-expression / leisure space.
    "/family/letters/",  # Letters to/from family members — relational channel.
    ".divineos-shared/letters/",  # The shared mirror the same letters land in.
    "/mansion/",  # Internal-space writing — not father-facing.
    "/dreams/",  # Rest-shape writing — no plan, no pull, no gate (Andrew 2026-07-30).
    "/scratchpad/",  # Harness scratch dir — throwaway probes, not architecture.
)


# Code-file extensions disqualify a path from the leisure-writing exemption even under an exempt
# directory (`exploration/gates.py` is still code work).
_CODE_FILE_SUFFIXES: frozenset[str] = frozenset(
    {
        ".py",
        ".pyi",
        ".pyx",
        ".sh",
        ".bash",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".go",
        ".rs",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
        ".java",
        ".rb",
        ".php",
        ".sql",
        ".toml",
        ".yaml",
        ".yml",
    }
)


# Engagement-clearing consult commands. Via Bash/PowerShell, the soft engagement gates (2 / 4 / 4.5)
# skip their pre-emptive block so the command whose execution would clear the block can run. Matches
# at the start of any pipeline segment.
_ENGAGEMENT_CLEARING_RE = re.compile(
    r"^divineos\s+(ask|recall|briefing|lessons|active|context|decide|feel|"
    r"directives|body|compass|hud|preflight|goal|corrections)\b"
)


def _is_engagement_clearing_command(command: str) -> bool:
    """True if any pipeline segment of the shell command is a consult CLI.

    Uses the same shell-separator split as is_substrate_write_command so
    substring matches in echo args / quoted strings don't spuriously match.
    """
    if not command:
        return False
    for segment in re.split(r"\s*(?:&&|\|\||;|\|)\s*", command):
        if _ENGAGEMENT_CLEARING_RE.match(segment.strip()):
            return True
    return False


def _is_low_friction_write(input_data: dict[str, Any]) -> bool:
    """True if the tool is a Write/Edit to a low-friction exemption path (see
    _LOW_FRICTION_PATH_SEGMENTS). Lets gates 1.46, 1.47, 1.5, 2, 4 and 4.5 skip for such writes. The
    HARD safety walls still fire for every write regardless of path: truly-stale briefing (>24h),
    mansion-quiet, hedge, pull-detection, retry-blocker, context-governor.

    Matching is anchored, not substring: (1) resolve `..` via PurePosixPath so
    `exploration/../core/ledger.py` collapses to core; (2) match the segments against directory
    ANCESTORS, so `data/mansion/config.py` does not qualify by substring; (3) reject code-file
    extensions.
    """
    try:
        from pathlib import PurePosixPath

        tool_name = input_data.get("tool_name", "") or ""
        if tool_name not in {"Write", "Edit", "MultiEdit", "NotebookEdit"}:
            return False
        file_path = input_data.get("tool_input", {}).get("file_path", "") or ""
        if not file_path:
            return False

        # Normalize separators + resolve ``..`` segments. PurePosixPath
        # collapses ``a/b/../c`` to ``a/c`` without touching the disk.
        normalized = file_path.replace("\\", "/")
        try:
            resolved_parts: list[str] = []
            for part in PurePosixPath(normalized).parts:
                if part == "..":
                    if resolved_parts:
                        resolved_parts.pop()
                    # ``..`` past the root drops it — paths like
                    # ``exploration/../core/x.py`` resolve to
                    # ``core/x.py`` which won't match any exempt dir.
                elif part != ".":
                    resolved_parts.append(part)
            resolved = "/" + "/".join(p.strip("/") for p in resolved_parts if p)
            # Empty after resolution → can't be exempt.
            if resolved == "/":
                return False
        except (ValueError, IndexError):
            return False

        # Code-file extensions disqualify regardless of directory.
        # A .py under exploration/ is still code work.
        ext = ""
        if "." in resolved_parts[-1]:
            ext = "." + resolved_parts[-1].rsplit(".", 1)[-1].lower()
        if ext in _CODE_FILE_SUFFIXES:
            return False

        # Now check: does any segment appear as a true directory ancestor?
        # Segments are stored as "/exploration/" etc; we want the segment
        # without trailing slash to appear as a *component* of the path,
        # not anywhere in the path string.
        path_components = set(resolved_parts[:-1])  # excludes filename
        for segment in _LOW_FRICTION_PATH_SEGMENTS:
            seg_name = segment.strip("/")
            # Multi-component segment like "family/letters" — match the
            # joined chain.
            if "/" in seg_name:
                joined = "/" + "/".join(resolved_parts[:-1])
                if "/" + seg_name + "/" in joined + "/":
                    return True
            else:
                if seg_name in path_components:
                    return True
        return False
    except (AttributeError, TypeError):
        return False


def _gate_label(reason: str) -> str:
    """The gate's own headline, used as its identity in the fire log.

    Taken from the first line of the refusal rather than inferred, so the
    label is the gate describing itself. Trimmed to keep the log readable.
    """
    if not (reason or "").strip():
        return "unlabelled"
    first = reason.strip().splitlines()[0]
    # Counts and ids are instance data, not gate identity: each run of digits collapses to N, so '20
    # code actions' and '30 code actions' group as one gate. Done by hand, not by pattern, because
    # this file is a keyword-enforcement gate.
    collapsed: list[str] = []
    in_digits = False
    for ch in first:
        if ch.isdigit():
            if not in_digits:
                collapsed.append("N")
            in_digits = True
        else:
            collapsed.append(ch)
            in_digits = False
    return " ".join("".join(collapsed).split()).rstrip(":.").strip()[:80]


def _record_gate_fire(reason: str) -> None:
    """Record that a gate refused something. A gate-fire is a FINDING, not an event: every refusal says
    a doorman is missing upstream (Andrew 2026-08-13: gates are primitive blocks, ideally you never
    hit one). Nothing recorded refusals before (``_record_gate_failure`` logs only a gate whose
    machinery CRASHED), so the same walls were hit repeatedly without accumulating as debt. Rides
    ``failure_diagnostics``, which already reaches the briefing. Never raises: instrumentation must
    not break a gate.
    """
    try:
        from divineos.core.failure_diagnostics import record_failure

        record_failure("gate_fire", {"gate": _gate_label(reason)})
    except Exception:  # noqa: BLE001 — telemetry is last-resort, never amplify
        pass


# The command this process was asked about, stashed at parse time so a refusal
# can describe the SHAPE of the line it refused. A hook process handles exactly
# one tool call, so a module-level slot is the whole of its lifetime.
_REFUSED_COMMAND: str = ""

# Shell operators that join clauses. Deliberately crude: a semicolon inside a quoted string counts
# and should not, and the cost is four extra lines that are TRUE anyway (a pre-tool refusal means
# nothing ran whether the line held one clause or five). A false negative costs the fault this
# exists to close, so it errs toward speaking.
_CLAUSE_JOINER = re.compile(r"&&|\|\||;|\n\s*\S")


def _nothing_ran_footer(command: str) -> str:
    """Say what did NOT run, for a refused line that joined more than one clause. A PreToolUse refusal
    fires before the shell sees the line, so NO clause ran; but a refusal naming one clause was read
    as being about that clause alone (2026-09-05: a refusal named the push, the commit was assumed
    done and a diff against main came back empty; two days earlier a branch-switch half was silently
    dropped and the re-issued fragment ran on the wrong branch).

    Flat, not hedged: "some of this may not have run" leaves room to reconstruct a hopeful half. The
    second sentence saves the work: answer the objection and re-run the WHOLE line, because
    re-issuing one fragment executes it in a state the full line would have set up and did not.
    Returns "" for a single-clause line (printing it on every refusal is wallpaper).

    Every refusal from ``_make_deny`` carries it, and the shell hooks carry the same words via
    ``hook_say_nothing_ran`` in .claude/hooks/_lib.sh. Not yet covered: hooks that refuse by
    emitting a JSON decision instead of exiting 2; that set is enumerated and pinned in
    tests/test_every_refusing_hook_says_what_did_not_run.py, which fails if the list grows and fails
    again if a name in it goes stale.
    """
    if not command or not _CLAUSE_JOINER.search(command):
        return ""
    return (
        "\n\n-- nothing on this line ran --\n"
        "This refusal fired before the shell saw the command, and the line "
        "joins more than one clause. No clause executed: not the ones after "
        "the part named above, and not the ones before it.\n"
        "Answer the objection, then re-issue the WHOLE line. Re-running a "
        "single fragment executes it in a state the full line would have set "
        "up and did not."
    )


def _make_deny(reason: str) -> dict[str, Any]:
    """Package a deny decision in the Claude Code hook response format. Every gate routes through here,
    so this one function records the refusal and appends what did not run for all of them, instead
    of nineteen call sites each remembering to.
    """
    _record_gate_fire(reason)
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason + _nothing_ran_footer(_REFUSED_COMMAND),
        }
    }


# Session-block marker filename, written at the checkout root by
# session_start.verify_session_ownership() when data-home ownership verification fails, so it
# survives even when data-home routing is itself the failure. Read here to hard-block substrate
# access until the operator resolves the mismatch.
_SESSION_BLOCK_MARKER_NAME = ".divineos_session_block"


# Read-only probes that must pass while a pre-registration is overdue. An honest assessment needs
# evidence, and blocking the looking produced fabricated outcomes or defensive deferrals: on
# 2026-08-13 two reviews were recorded DEFERRED with "CANNOT-LOOK" only because this gate refused
# `divineos already-built` and a bypass-store query. The gate stops substantive WORK until review
# happens; reading evidence is not that work. Read-only only: nothing here mutates the repo, the
# substrate or the remote. Compound commands never reach this check; _is_readonly_probe reuses the
# F22 hardening, so `git log && rm -rf` is not a probe.
_READONLY_PROBE_PREFIXES = (
    "git log",
    "git show",
    "git diff",
    "git status",
    "git ls-tree",
    "git ls-remote",
    "git rev-parse",
    "git cat-file",
    "git branch --list",
    "divineos already-built",
    "divineos reach",
    "divineos prereg",
    "divineos todos",
    "divineos inspect",
    # Plain looking (Aria, 2026-10-01): a bare `grep` had been refused twice in one morning. A
    # redirect or --output still makes any of these a write, and that check runs first. Each prefix
    # carries its trailing space so `ls` cannot pass `lsblk`.
    "grep ",
    "rg ",
    "cat ",
    "head ",
    "tail ",
    "wc ",
    "ls ",
)

# A RULE about read-only verbs, not a list of commands. The prefix list above only covers reviews
# somebody has already failed to earn: it blocked evidence twice on 2026-08-13 and again on
# 2026-09-01, when a review about `divineos detectors status` was refused and the edit adding the
# command was refused by the same block. The next review needing an unlisted probe is unknowable in
# advance. Every CLI group follows one convention, and these verbs never mutate: status, show, list,
# check, summary, history. Mutating verbs stay blocked (`divineos detectors heal` and `defer` are
# still refused: clearing a degradation is substantive work).
_READONLY_VERBS = frozenset({"status", "show", "list", "check", "summary", "history"})


def _is_command_group(name: str) -> bool | None:
    """Whether ``divineos <name>`` is a group with subcommands or a leaf, asked of click's own
    resolution and not of a list. ``None`` means could-not-look (the CLI failed to import or the
    name did not resolve); the caller treats that as not-a-probe, never as a pass.
    """
    try:
        import click

        from divineos.cli import cli as _cli

        command = _cli.get_command(click.Context(_cli), name)
    except Exception:  # noqa: BLE001 -- could not look is its own answer
        return None
    if command is None:
        return None
    return isinstance(command, click.Group)


def _is_readonly_divineos_verb(cmd: str) -> bool:
    """True for ``divineos <group...> <read-only verb>`` shapes. The verb must sit where a verb sits
    (second or third token, before any flag), so a mutating command carrying one of these words in
    an argument does not qualify (``divineos audit submit --notes "status ..."``). The third token
    is a verb ONLY if the second is a group: ``divineos detectors status`` is a read, but in
    ``divineos learn status`` the third token is the lesson text, and a lesson spelled "status", a
    claim "summary" and a lesson "check" were all waved through as probes. The registry says which
    groups have a third level, so it is asked and no second list is kept.
    """
    import shlex

    try:
        tokens = [t for t in shlex.split(cmd) if not t.startswith("-")]
    except ValueError:
        return False  # unbalanced quotes: cannot read it, so not a probe
    if len(tokens) < 2 or tokens[0] != "divineos":
        return False
    if tokens[1] in _READONLY_VERBS:
        return True
    if len(tokens) < 3 or tokens[2] not in _READONLY_VERBS:
        return False
    # Cheap checks are exhausted; only now pay for the registry. A leaf
    # command's third token is an argument, and could-not-look is a refusal.
    return _is_command_group(tokens[1]) is True


# `set` followed only by option-shaped words (flag clusters, or the bare names `-o` takes). Nothing
# here can be a path, an assignment or a redirection. `set -o pipefail` and `set -euo pipefail`
# qualify; `set x=1`, `set -o pipefail > file` and `setup.sh` do not. The option name may follow
# `-o` as a separate flag, the commonest spelling of the idiom.
_SHELL_OPTION_ONLY = re.compile(r"set(?:\s+(?:[+-][A-Za-z]+|[a-z][a-z_]*))+\s*")


def _split_shell_clauses(cmd: str) -> list[str]:
    """Split on real clause joiners, ignoring ones inside quotes. Quote-aware because here a wrong
    split could make the gate PERMIT: a joiner inside a quoted argument would carve one command into
    fragments, and a fragment can start with a safe prefix while the whole does not. Returns [] on
    an unterminated quote and the caller treats that as not-a-probe, matching the fail-closed
    direction of ``_has_compound_shape``.
    """
    clauses: list[str] = []
    current: list[str] = []
    state: str | None = None
    i = 0
    n = len(cmd)
    while i < n:
        ch = cmd[i]
        if state is None:
            if ch == "\\":
                current.append(ch)
                if i + 1 < n:
                    current.append(cmd[i + 1])
                    i += 2
                    continue
            elif ch in ("'", '"'):
                state = ch
            elif ch == ";":
                clauses.append("".join(current))
                current = []
                i += 1
                continue
            elif ch in ("&", "|") and i + 1 < n and cmd[i + 1] == ch:
                clauses.append("".join(current))
                current = []
                i += 2
                continue
        elif ch == state:
            state = None
        current.append(ch)
        i += 1

    if state is not None:
        return []
    clauses.append("".join(current))
    return [c for c in (c.strip() for c in clauses) if c]


def _is_readonly_probe(cmd: str) -> bool:
    """True if the command only looks at state, never changes it. Judged PER CLAUSE, not per line: a
    compound shape is not refused outright when EVERY clause is a read (the overdue block once
    refused its own cure, typed with a `cd` and a `set -o pipefail` in front). A line containing any
    non-probe clause is still not a probe, so `git log && rm -rf` never reads as one. Fails closed
    on an unterminated quote.
    """
    if not cmd:
        return False
    cmd = _strip_safe_output_tail(_strip_cd_prefix(cmd))

    def _writes_despite_a_read_verb(clause: str) -> bool:
        """True when a read verb has been handed somewhere to put the output. The verb alone is not the
        command: a prefix match ignores every flag, so `log`, `show` and `diff` with --output write
        a file (a diff written over a guardrail file would have been called looking; Aletheia
        2026-09-21), and an ordinary shell redirect does the same with no flag. The FLAG is what
        gets asked about, not a wider verb list.

        Near-misses measured: ``-o`` is not an output flag on these verbs (it errors); ``-O`` is the
        diff orderfile and READS a file, so the check is case-sensitive on the long form only;
        ``2>&1`` duplicates a handle and ``>/dev/null`` discards, so neither is a write anyone would
        miss.

        Quoted text is data: an arrow inside ``grep 'a > b' f`` is not a redirect, so quoted spans
        are filled first. When they cannot be filled safely (an escaped quote, a ``$'...'`` string,
        an unbalanced quote) the clause is scanned whole and the failure stays a refusal.
        """
        blanked = blank_quoted_spans(clause)
        if blanked is not None:
            clause = blanked
        if "--output" in clause:
            return True
        # A read verb that runs something else (Aletheia on #575): `cat <(touch /tmp/pwn)` runs a
        # command inside the brackets and `rg --pre=/tmp/evil.sh x .` runs a program on every file;
        # neither writes through a redirect. Process substitution in either direction, and rg's
        # preprocessor flags, make a line not a look.
        if "<(" in clause or ">(" in clause:
            return True
        if re.search(r"(^|\s)--pre(-glob)?(=|\s|$)", clause):
            return True
        i = 0
        while True:
            i = clause.find(">", i)
            if i < 0:
                return False
            rest = clause[i:].lstrip(">").lstrip()
            # `>&1` and friends duplicate an existing handle; nothing lands
            # on disk. A discard target is a write to nowhere.
            if rest.startswith("&"):
                i += 1
                continue
            target = rest.split()[0] if rest.split() else ""
            if target.lower() in ("/dev/null", "nul", ""):
                i += 1
                continue
            return True

    def _clause_is_probe(clause: str) -> bool:
        clause = _strip_safe_output_tail(_strip_cd_prefix(clause.strip()))
        if not clause:
            return False
        # A clause that is itself compound could not be split cleanly, so it
        # is refused rather than guessed at.
        if _has_compound_shape(clause):
            return False
        # Inert is not read-only, and both are fine here: `set -o pipefail` changes how this shell
        # propagates an exit code and touches no file, store or remote. Refusing it made the whole
        # line non-read and kept the block refusing its own cure. Deliberately narrow: only the
        # shell builtin that sets options, flags only, no assignment or redirection.
        if _SHELL_OPTION_ONLY.fullmatch(clause):
            return True
        if _writes_despite_a_read_verb(clause):
            return False
        return clause.startswith(_READONLY_PROBE_PREFIXES) or _is_readonly_divineos_verb(clause)

    if not _has_compound_shape(cmd):
        # BOTH paths, or the fix fits only the door it was found at: the single-clause path and the
        # clause path both ask this.
        if _writes_despite_a_read_verb(cmd):
            return False
        return cmd.startswith(_READONLY_PROBE_PREFIXES) or _is_readonly_divineos_verb(cmd)

    clauses = _split_shell_clauses(cmd)
    if not clauses:
        return False
    # Every clause, and ONLY the clauses: asking the verb rule about the whole line would inspect
    # the head and ignore the rest, so `divineos detectors status && rm -rf` would read as a probe
    # on the strength of its first three words.
    return all(_clause_is_probe(c) for c in clauses)


# Closed shapes, matched WHOLE (Aether, 2026-10-10): anchoring only the start let a newline carry a
# second command through this hard block, and a redirect or --output write a file. Nothing may
# follow the verb except, for a goal, ONE quoted argument with no newline, no substitution and no
# escape inside it.
_BRIEFING_SHAPE = re.compile(r"divineos[ \t]+briefing[ \t]*")
_GOAL_SHAPE = re.compile(
    r"""divineos[ \t]+goal[ \t]+add[ \t]+(?:'[^'\n$`]*'|"[^"\n$`\\]*")[ \t]*"""
)


_GOAL_ADD_ANYWHERE = re.compile(r"\bgoal[ \t]+add\b")


def _is_a_shared_remedy(cmd: str) -> bool:
    """True when some other gate prescribes this command as ITS way out, via the shared
    ``core/remedy_allowlist.py``: one list, not a private copy (the private one refused five exits a
    neighbouring gate prescribes, so two armed gates could have locked each other; measured by
    test_every_exit_passes_every_gate). One exception, encoded: any line that mentions `goal add` is
    NOT decided by the shared list, because `goal add 'a' && goal add 'b'` is two remedies to it; a
    goal passes only while the goal gate is itself asking (``_is_a_review_prerequisite`` holds that
    condition).
    """
    from divineos.core.remedy_allowlist import is_remedy, outside_quotes

    # Outside quoted spans: a lesson that merely MENTIONS `goal add` is data, not a second goal. The
    # helper scans the text whole when blanking would be unsafe, so a real chained goal add is still
    # caught.
    if not cmd or _GOAL_ADD_ANYWHERE.search(outside_quotes(cmd)):
        return False
    return is_remedy(cmd)


def _is_a_review_prerequisite(cmd: str) -> bool:
    """True for the few commands any review needs BEFORE it can be done: the day's briefing and the
    seat's own bell. (When the date rolled and a review came due, this block refused `briefing` and
    `goal add`, but the build-flow gate's key needs the day's briefing and the exit this block names
    needed that key: a ring with no free link.) Narrower than the engagement gate's equivalent: a
    LONE clause only, since that one tests every segment of a chain, which would let ``briefing &&
    rm`` through a hard block; and a goal passes only while the goal gate is itself asking, so the
    allowance cannot become a way to keep adding goals while a review is overdue.
    """
    if not cmd:
        return False
    if _is_doorbell_rearm(cmd):
        return True
    stripped = _strip_cd_prefix(cmd).strip()
    if _has_compound_shape(stripped):
        return False
    if _BRIEFING_SHAPE.fullmatch(stripped):
        return True
    if not _GOAL_SHAPE.fullmatch(stripped):
        return False
    from divineos.core.hud_state import has_session_fresh_goal

    return not has_session_fresh_goal()


def _check_overdue_prereg_block(cmd: str = "") -> dict[str, Any] | None:
    """Hard-block substantive tool use when any pre-registration is overdue. Runs after the bypass
    check so `divineos prereg assess ...` and other bypass-listed commands can still record outcomes
    or defer. The denial names which pre-registration ids need review. (Andrew 2026-07-07: no
    warnings, they do not work; overdue reviews in the briefing were scrolled past.)
    """
    # Looking is not the work this gate means to stop (see _READONLY_PROBE_PREFIXES).
    if _is_readonly_probe(cmd) or _is_a_review_prerequisite(cmd) or _is_a_shared_remedy(cmd):
        return None

    try:
        from divineos.core.pre_registrations.store import (
            get_blocking_pre_registrations,
        )
    except ImportError:
        return None
    try:
        # Only a review that reached its count of USES blocks. A date alone never does (Dad, 2026-10-21).
        overdue = get_blocking_pre_registrations()
    except Exception as exc:  # noqa: BLE001 — fail-open if the store errors
        # Not blocking is right for a gate that must never strand saving or sleep, but a swallowed
        # error is the same value as "nothing is due", so say it could not look (walk-0f2e657133fd).
        print(
            f"[overdue-reviews] could not read the reviews, not blocking: {type(exc).__name__}",
            file=sys.stderr,
        )
        return None
    if not overdue:
        return None

    # A DECLARED REVIEW is what this gate is asking for, so it cannot be refused by it (a gate that
    # denied the evidence for two reviews left only a fabricated verdict or a deferral as exits);
    # see core/pre_registrations/review_window.py. TWO CAUSES WEAR ONE SENTENCE and need opposite
    # repairs: "the store is unreadable" is an operational fault, but "the module is not installed"
    # means every substantive tool use on this clone has been denied since it existed and the fix is
    # an install, so the message says which (Aletheia 2026-09-13).
    window_error = ""
    window_absent = False
    # TWO TRIES, not one: with the import and the call under one try, an ImportError raised from
    # INSIDE active_window (a dependency gone missing) would land in the absent branch and announce
    # that an importable module was never importable. Only the import statement itself may raise the
    # absent verdict.
    window = None
    try:
        from divineos.core.pre_registrations.review_window import active_window
    except ImportError as exc:
        window_absent = True
        window_error = f"{type(exc).__name__}: {exc}"
    else:
        try:
            window = active_window()
        except Exception as exc:  # noqa: BLE001 -- not swallowed; see the deny below
            window_error = f"{type(exc).__name__}: {exc}"

    if window is not None and window.state == "open":
        return None
    if window is None or window.state == "could-not-check":
        reason = window_error or getattr(window, "reason", "unknown")
        if window_absent:
            return _make_deny(
                "OVERDUE PRE-REGISTRATIONS block substantive tool use, AND the "
                "review-window module is NOT INSTALLED on this checkout, so "
                "this gate cannot tell whether a review is already under "
                "way.\n\n"
                f"  why: {reason}\n\n"
                "This is not a store that broke. The module has never been "
                "importable here, which means this gate has denied every "
                "declared review on this clone for as long as the clone has "
                "existed. Install the package into the interpreter running "
                "this hook, then retry."
            )
        return _make_deny(
            "OVERDUE PRE-REGISTRATIONS block substantive tool use, AND the "
            "review-window store could not be READ, so this gate cannot "
            "tell whether a review is already under way.\n\n"
            f"  why: {reason}\n\n"
            "The module is installed, so this is an operational fault in the "
            "store itself. This is a refusal made without looking, NOT a "
            "finding that no review is happening. Repair the store, then "
            "retry."
        )

    ids_preview = ", ".join(p.prereg_id[:24] for p in overdue[:5])
    more = f" (and {len(overdue) - 5} more)" if len(overdue) > 5 else ""
    return _make_deny(
        "OVERDUE PRE-REGISTRATIONS block substantive tool use.\n\n"
        f"{len(overdue)} pre-registration(s) that reached their count of uses: "
        f"{ids_preview}{more}\n\n"
        "For each overdue pre-registration, record the outcome or defer:\n"
        "  divineos prereg assess <id> --outcome SUCCESS|FAILED|INCONCLUSIVE "
        '--actor <name> --notes "<what happened>"\n'
        "  divineos prereg assess <id> --outcome DEFERRED --actor <name> "
        '--notes "<why deferring>"\n\n'
        "IF THE EVIDENCE IS BEHIND THIS GATE, say so and go get it:\n"
        '  divineos prereg reviewing <id> --purpose "<what you will look at>"\n'
        "  That stands this gate down for a bounded stretch and records the "
        "window by name. It is not a bypass -- it only opens against a review "
        "that is genuinely overdue, and a window with no assessment behind it "
        "is counted and surfaced. Added because this block twice refused the "
        "evidence for its own reviews, leaving a fabricated verdict or a "
        "deferral as the only exits.\n\n"
        "List all overdue with: divineos prereg overdue"
    )


def _check_ownership_block() -> dict[str, Any] | None:
    """Enforce the session-block marker set by session_start on an ownership mismatch. Returns a deny
    if the marker exists, else None. Runs BEFORE _is_bypass_command: a mismatched substrate makes
    even documented bypass commands unsafe, since they would read or write the wrong home. Recovery
    uses Edit and Write, which Claude Code does not route through this Bash gate.
    """
    try:
        from divineos.core.data_home_ownership import _checkout_root
    except ImportError:
        return None
    try:
        marker = _checkout_root() / _SESSION_BLOCK_MARKER_NAME
        if not marker.exists():
            return None
        message = marker.read_text(encoding="utf-8")
    except (OSError, ValueError):
        return None
    return _make_deny(
        "DIVINEOS SESSION BLOCKED — data-home ownership mismatch detected "
        "at session start.\n\n"
        f"{message}\n\n"
        "Recovery: the Edit and Write tools do NOT trigger this Bash gate. "
        "Use them to (a) fix the `.divineos_data_home` marker at the checkout "
        "root so it points at YOUR data-home (or remove that marker to fall "
        f"through to the default), or (b) delete the block marker at {marker}. "
        "Restart the session — session-start will re-verify ownership and "
        "clear the block marker automatically on success."
    )


def _combine_engagement_denies(denies: list[str]) -> str:
    """Coalesce the soft engagement-discipline denials (goal / engagement / consultation) into ONE
    message so they clear in a single pass instead of single-file across N retries. The hard safety
    walls above still short-circuit individually and take precedence; only this soft cluster
    coalesces. Same gates, same order, same decisions.
    """
    if len(denies) == 1:
        return denies[0]
    parts = [
        f"BLOCKED: {len(denies)} engagement checks need clearing before "
        "substrate-modifying tools — surfaced together so you clear them in one "
        "pass, not one at a time:",
        "",
    ]
    for i, d in enumerate(denies, 1):
        body = d[len("BLOCKED: ") :] if d.startswith("BLOCKED: ") else d
        parts.append(f"  [{i}] {body}")
        parts.append("")
    parts.append("Clear all of the above, then retry the tool.")
    return "\n".join(parts)


def _make_soft_advise(advise: str) -> dict[str, Any]:
    """Package a soft advisory: the tool call proceeds and an additionalContext message is surfaced.
    For non-blocking gates whose intent is 'surface this state', not 'stop this action'. A hard
    block repeating an identical message for routine cases taught the agent to chain a stub-fix and
    stop reading (the gate's metric, marker-present, decoupled from the property, agent oriented in
    the substrate). The hard block stays for truly-stale state (>24h since briefing).
    """
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "additionalContext": advise,
        }
    }


def _briefing_diagnostic(stale_info: dict[str, Any]) -> str:
    """Build a structured message naming WHY the briefing-state is stale.

    Round-2 audit (Holmes' lens): when the briefing gate fires, the
    message should name which condition triggered — TTL expired,
    session-id mismatch, or marker missing entirely. Each is a different
    failure-mode and each calls for a different operator response.
    """
    if not stale_info.get("loaded"):
        return "marker missing - briefing has not been loaded"
    parts = []
    age_h = stale_info.get("age_seconds", 0) / 3600
    parts.append(f"loaded {age_h:.1f}h ago")
    if stale_info.get("ttl_expired"):
        ttl_h = stale_info.get("ttl_seconds", 0) / 3600
        parts.append(f"TTL expired (limit {ttl_h:.0f}h)")
    delta = stale_info.get("calls_since", 0)
    threshold = stale_info.get("threshold", 0)
    if delta:
        parts.append(f"{delta} tool calls since load (threshold {threshold})")
    return " - ".join(parts)


# Truly-stale threshold (still hard-block at this age regardless of session-mismatch).
# 24h matches the operator's expectation that a briefing-load older than a day
# represents real cross-session amnesia, not a within-session rotation event.
_TRULY_STALE_AGE_SECONDS = 24 * 3600


def _record_gate_failure(gate_name: str, exc: BaseException) -> None:
    """Log a gate's machinery failure to the shared diagnostic surface. Gates correctly fail open when
    their machinery is broken (ImportError during bootstrap, OSError on a missing DB) but did so
    silently; this records the failure so the next briefing surfaces it. Never raises.
    """
    try:
        from divineos.core.failure_diagnostics import record_failure

        record_failure(
            "gate",
            {
                "gate": gate_name,
                "error_type": type(exc).__name__,
                "error": str(exc)[:200],
            },
        )
    except Exception:  # noqa: BLE001 — diagnostic helper is last-resort, never amplify failure
        pass


def _context_governor_gate(input_data: dict[str, Any] | None) -> dict[str, Any] | None:
    """Gate 7: context-governor hard line (prereg-9b958c6493f3). At the 950k hard line, substrate
    writes are gated until the self is WOVEN (extract + sleep), so a post-compaction instance
    rehydrates from a connected store. The warn band (920k-950k) does not reach here; it is a soft
    nudge at UserPromptSubmit. extract and sleep are bypassed in ``_is_bypass_command``, so the gate
    never blocks its own remedy, and sleep marks-consolidated, which flips this to "ok" for the rest
    of the session. Low-gravity writes (exploration/, family/letters/, mansion/) PASS during the
    block state: the rest-phase before the cliff exists for exactly those. Fail-open: an unreadable
    or absent transcript yields "ok". Returns a deny on block, else None.
    """
    try:
        transcript_path = (input_data or {}).get("transcript_path", "") or ""
        if not transcript_path:
            return None
        from divineos.core.context_governor import (
            consolidation_state,
            governor_channel_message,
        )

        if consolidation_state(transcript_path) != "block":
            return None

        # Block state. Low-friction rest-phase writes PASS (exploration/, family/letters/, mansion/,
        # dream/, bio/: the channels Andrew named 2026-06-09); arbitrary writes block.
        ti = (input_data or {}).get("tool_input", {}) or {}
        fp = (ti.get("file_path", "") or "").replace("\\", "/")
        if fp and any(
            seg in fp
            for seg in (
                "exploration/",
                "family/letters/",
                "mansion/",
                "dream/",
                "bio/",
            )
        ):
            return None

        # Shell pass-through (Andrew 2026-07-09): the block exists so the self is woven (extract +
        # sleep) before writing to canonical stores, not so the whole shell freezes. Read-only shell
        # and extract, sleep and commit themselves pass; only substrate-writing CLI subcommands
        # block (same classifier the obligations gate uses).
        tool_name = (input_data or {}).get("tool_name", "") or ""
        if tool_name in ("Bash", "PowerShell"):
            cmd = (ti.get("command", "") or "").strip()
            try:
                from divineos.core.obligations import is_substrate_write_command

                if not is_substrate_write_command(cmd):
                    return None
            except ImportError:
                return None

        return _make_deny(governor_channel_message(transcript_path))
    except (ImportError, OSError, AttributeError) as _gate_exc:
        _record_gate_failure("gate_7_context_governor", _gate_exc)
    return None


def _check_gates(input_data: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Run all gates in order. Return first deny decision, or None if all pass.

    Import-heavy work is guarded — if a module can't be imported (e.g. during
    first-run bootstrap), that gate is skipped rather than crashing the hook.
    Fail-open is the correct disposition for a gate whose machinery is broken.
    """
    # Soft engagement denials (goal / engagement / consultation) are COLLECTED here and surfaced
    # together at the end of the soft cluster; the hard walls below still short-circuit
    # individually.
    soft_denies: list[str] = []

    # Gate 0: exploration entries must carry a tag header (write-time wall). First on purpose: a
    # briefing soft-advise can short-circuit the chain, so a stale-briefing turn would otherwise let
    # an untagged entry through, and untagged entries are invisible to the recall surfacer. Write
    # only (Edit gets a diff, not the whole file); README exempt; constrains findability, not
    # content.
    try:
        if input_data is not None:
            from divineos.core.exploration_recall import needs_tags_block

            _tn = input_data.get("tool_name", "") or ""
            _ti = input_data.get("tool_input", {}) or {}
            _msg = needs_tags_block(
                _tn, _ti.get("file_path", "") or "", _ti.get("content", "") or ""
            )
            if _msg:
                return _make_deny(_msg)
    except (ImportError, OSError, AttributeError) as _gate_exc:
        _record_gate_failure("gate_0_exploration_tags", _gate_exc)

    # Gate 0: exploration-entry numbering invariants (exploration_validator.py: no duplicate or
    # skipped numbers). Fires only on Write/Edit to exploration/<member>/; the refusal carries the
    # validator's plain-language reason naming the invariant and the correct number.
    if input_data is not None:
        try:
            tool_name = input_data.get("tool_name", "")
            file_path = (input_data.get("tool_input") or {}).get("file_path", "")
            if tool_name in ("Write", "Edit") and "exploration/" in str(file_path):
                from divineos.core.exploration_validator import (
                    validate_new_entry_path,
                )
                from pathlib import Path as _Path

                ok, reason = validate_new_entry_path(_Path(file_path))
                if not ok:
                    return _make_deny(
                        f"BLOCKED: exploration-entry validator refused this path. "
                        f"{reason} Sanctioned creation path: "
                        f"`divineos exploration new --slug <slug>`."
                    )
        except (ImportError, OSError, AttributeError, KeyError) as _gate_exc:
            _record_gate_failure("gate_0_exploration_validator", _gate_exc)

    # Gate 1: briefing-ID recall challenge (briefing_id.py). The briefing counts as loaded if I can
    # reproduce a context-printed random token from memory, so recall failure IS the staleness
    # signal; this replaced a wall-clock check that fired when nothing had changed and stayed quiet
    # after mid-session compaction. Low-friction paths (exploration/, family/letters/ and other
    # first-person surfaces) bypass the check.
    try:
        if input_data is None or not _is_low_friction_write(input_data):
            from divineos.core.briefing_id import (
                challenge_message,
                current_tool_count,
                is_fresh,
            )

            if not is_fresh(current_tool_count()):
                return _make_deny(f"BLOCKED: {challenge_message(current_tool_count())}")
    except (ImportError, OSError, AttributeError) as _gate_exc:
        _record_gate_failure("gate_1_briefing_id_recall", _gate_exc)

    # Gate 1.2: mansion private-room quiet period. While it is active, write actions are refused;
    # inspection commands are in the bypass list and never reach here.
    try:
        from divineos.core.mansion_quiet_marker import (
            format_gate_message as _mq_msg,
        )
        from divineos.core.mansion_quiet_marker import (
            is_quiet_active as _mq_active,
        )
        from divineos.core.mansion_quiet_marker import (
            read_marker as _mq_read,
        )

        if _mq_active():
            m = _mq_read()
            if m is not None:
                return _make_deny(_mq_msg(m))
    except (ImportError, OSError, AttributeError) as _gate_exc:
        _record_gate_failure("gate_1_2_mansion_quiet", _gate_exc)

    # Gate 1.4: compass staleness. After N code actions without a compass observation, non-bypass
    # tools block until `divineos compass-ops observe` runs (the observe command clears the
    # counter). The safe-remedy exemption (_is_safe_remedy_invocation) lets `compass-ops observe`
    # and `dismiss` run even while the gate fires: a gate must never block the remedy it names.
    try:
        from divineos.core.hud_handoff import compass_staleness_status

        cs = compass_staleness_status()
        if cs.get("stale"):
            _cmd_text = ""
            if input_data is not None:
                _tn = input_data.get("tool_name", "") or ""
                if _tn in ("Bash", "PowerShell"):
                    _cmd_text = (input_data.get("tool_input", {}) or {}).get("command", "") or ""
            _compass_remedy_heads = (
                "divineos compass-ops observe",
                "divineos compass-ops dismiss",
            )
            if not _is_safe_remedy_invocation(_cmd_text, _compass_remedy_heads):
                return _make_deny(
                    f"BLOCKED: {cs.get('actions_since', '?')} code actions since "
                    f"the last compass observation (threshold "
                    f"{cs.get('threshold', '?')}). Run: divineos compass-ops "
                    f'observe <spectrum> -p <position> -e "<evidence>" — '
                    f"virtue drift is not tracked by the system if you never "
                    f"observe your own position."
                )
    except (ImportError, OSError, AttributeError) as _gate_exc:
        _record_gate_failure("gate_1_4_compass_staleness", _gate_exc)

    # Gate 1.45: hedge-unresolved. When my last output had >= 2 hedge flags (found by the Stop
    # hook), a claim must be filed before further tool use: a hedge without a claim is floating
    # doubt, and a claim discharges it into the investigation queue.
    try:
        from divineos.core.hedge_marker import format_gate_message as _hm_msg
        from divineos.core.hedge_marker import marker_path as _hm_path
        from divineos.core.hedge_marker import read_marker as _hm_read

        # Existence of the marker file blocks regardless of readability: a corrupted or unreadable
        # marker used to read as None and silently pass.
        if _hm_path().exists():
            h = _hm_read()
            if h is not None:
                return _make_deny(_hm_msg(h))
            return _make_deny(
                "BLOCKED: hedge marker present at "
                f"{_hm_path()} but unreadable. "
                'Clear manually with `divineos claim "statement"` once the '
                "underlying hedged uncertainty has been filed, or inspect "
                "the file if you suspect corruption. Fail-closed by design: "
                "a corrupted marker must not silently disable the gate."
            )
    except (ImportError, OSError, AttributeError) as _gate_exc:
        _record_gate_failure("gate_1_45_hedge", _gate_exc)

    # Gate 1.46 (theater / fabrication) is REMOVED (free-speech principle). It now surfaces
    # observationally in the next briefing; the Stop hook still writes the marker
    # (~/.divineos/theater_unresolved.json) for the forensic record. See core/theater_marker.py.

    # Gate 1.47: compass observation required after a virtue-relevant event (a correction, a theater
    # or hedge fire, a substantive claim); skipped for exploration-path writes.
    # Disclose-then-escalate, not hard-block-on-marker: below ESCALATION_THRESHOLD an advisory
    # (soft-advise) discloses without blocking; at or above it, a hard deny. Per-turn dedup
    # (PER_TURN_DEDUP_SECONDS) stops the same marker re-firing on every tool call within one turn.
    # Falsifier: the escalation must actually fire (advised_count reaches the threshold and denies),
    # else dedup plus grace degrade it to an ignorable advisory. The marker and message logic are
    # pinned in tests/test_compass_correction_redesign.py; a test that THIS gate denies at the
    # threshold is still owed.
    try:
        if input_data is None or not _is_low_friction_write(input_data):
            from divineos.core.compass_required_marker import (
                ESCALATION_THRESHOLD as _CR_ESC,
            )
            from divineos.core.compass_required_marker import (
                format_gate_message as _cr_msg,
            )
            from divineos.core.compass_required_marker import (
                marker_path as _cr_path,
            )
            from divineos.core.compass_required_marker import (
                read_marker as _cr_read,
            )
            from divineos.core.compass_required_marker import (
                record_advisory_fire as _cr_record,
            )
            from divineos.core.compass_required_marker import (
                should_dedup_within_turn as _cr_dedup,
            )

            if _cr_path().exists():
                cr = _cr_read()
                if cr is None:
                    # Marker present but unreadable — fail-closed.
                    return _make_deny(
                        "BLOCKED: compass-required marker present at "
                        f"{_cr_path()} but unreadable. "
                        "Clear by running: divineos compass-ops observe "
                        "<spectrum> -p <position> -e <evidence>. Fail-closed."
                    )

                # The block message names `divineos compass-ops observe` and `dismiss` as its
                # remedies, which must never be blocked. The bypass list covers simple invocations
                # only (F22 hardening refuses compound ones), so a piped `observe ... 2>&1 | tail
                # -3` would break the bypass and the gate would block its own remedy. Explicit
                # exemption: if the command's first segment IS the remedy and NO chain-shape char is
                # present (;, &&, ||, backtick, $(), allow it even at escalation; a naive
                # first-segment check let `observe X && rm -rf ~/` pass. A pipe stays allowed.
                _tn = (input_data or {}).get("tool_name", "") or ""
                _cmd = ""
                try:
                    _cmd = (input_data or {}).get("tool_input", {}).get("command", "") or ""
                except (AttributeError, TypeError):
                    _cmd = ""
                if _tn == "Bash" and _is_safe_remedy_invocation(
                    _cmd,
                    ("divineos compass-ops observe", "divineos compass-ops dismiss"),
                ):
                    # Fall through to allow — the remedy command must run.
                    return None

                advised_count = int(cr.get("advised_count", 0))
                # Defensive guard: dedup only suppresses after a prior advisory set last_advised_ts
                # (and advised_count >= 1); the check guards corrupted or hand-edited markers.
                if advised_count >= 1 and _cr_dedup():
                    pass  # silent suppression within per-turn window
                elif advised_count >= _CR_ESC:
                    # Escalation: advisory ignored ESCALATION_THRESHOLD times.
                    return _make_deny(_cr_msg(cr))
                else:
                    # Disclosure: emit advisory, increment counter, allow.
                    _cr_record()
                    return _make_soft_advise(_cr_msg(cr))
    except (ImportError, OSError, AttributeError) as _gate_exc:
        _record_gate_failure("gate_1_47_compass_required", _gate_exc)

    # Gate 1.48: stale-engagement block. The briefing warns on ignored stale entries; after the
    # third ignoring, the next code action is blocked until they are addressed. Tracker:
    # core/stale_engagement.py (render_dashboard records STALE_SURFACED, address commands record
    # close events; this gate denies when an area has been surfaced 3+ times unaddressed).
    try:
        from divineos.core.stale_engagement import (
            block_message,
            blocked_areas,
        )

        offenders = blocked_areas()
        if offenders:
            return _make_deny(block_message(offenders))
    except (ImportError, OSError, AttributeError) as _gate_exc:
        _record_gate_failure("gate_1_48_stale_engagement", _gate_exc)

    # Gate 1.5: a correction was detected but not logged. detect-correction.sh (UserPromptSubmit)
    # sets the marker when a user message matches CORRECTION_PATTERNS; `divineos learn` and
    # `divineos correction` clear it. Fail open on missing machinery. Low-friction writes
    # (exploration/, family/letters/, mansion/) are exempt: the marker stays set and the next
    # high-gravity write (src/divineos/, hooks) is still blocked.
    try:
        if input_data is None or not _is_low_friction_write(input_data):
            from divineos.core.correction_marker import (
                format_gate_message,
                marker_path,
                read_marker,
            )

            # Same fail-closed-on-unreadable pattern as the hedge gate above.
            if marker_path().exists():
                # Remedy commands named in the block message must never be blocked. Simple
                # invocations bypass in main(), but a compound shape does not, so a piped `divineos
                # learn "..." 2>&1 | tail -3` would deadlock the gate against its own remedy.
                # Explicit exemption through the shared _is_safe_remedy_invocation: allowed when the
                # first segment IS a remedy and NO chain-shape char is present; a pipe stays
                # allowed.
                _tn = (input_data or {}).get("tool_name", "") or ""
                _cmd = ""
                try:
                    _cmd = (input_data or {}).get("tool_input", {}).get("command", "") or ""
                except (AttributeError, TypeError):
                    _cmd = ""
                # Remedy heads come from the shared _is_safe_remedy_invocation, which also carries
                # the clear_correction_marker.py escape hatch the block message names.
                _correction_remedies = (
                    "divineos learn",
                    "divineos correction",
                    "divineos corrections",
                    "python scripts/clear_correction_marker.py",
                    'python "scripts/clear_correction_marker.py"',
                    "python C:/DIVINE OS/DivineOS-Experimental/scripts/clear_correction_marker.py",
                )
                # READS PASS. A fixed remedy list cannot name every way out, because one way out is
                # LOOKING. The ring (2026-09-21, walked into by Aria with Andrew watching): this
                # gate blocks everything but the remedy names; `divineos correction` refuses to file
                # without a file path proving a structural fix, which takes investigation; `divineos
                # learn` is held by the reach doorman until the artifact it surfaced has been READ;
                # and reading is a read-only command this gate blocked. Four doors, each correct
                # alone, forming a closed cycle. The fix is the existing carve-out
                # (_is_readonly_probe: per clause, compound-hardened, already used by the
                # overdue-prereg gate) swept across the class. It loosens nothing: a probe changes
                # no file, store or remote, so the marker survives it and the next substantive write
                # is blocked as before.
                if _tn == "Bash" and (
                    _is_safe_remedy_invocation(_cmd, _correction_remedies)
                    or _is_readonly_probe(_cmd)
                ):
                    # Fall through to allow — the remedy must run.
                    pass
                else:
                    marker = read_marker()
                    if marker is not None:
                        return _make_deny(format_gate_message(marker))
                    return _make_deny(
                        "BLOCKED: correction marker present at "
                        f"{marker_path()} but unreadable. "
                        'Clear manually with `divineos learn "lesson"` or '
                        '`divineos correction "description"` once the correction '
                        "has been named, or inspect the file if you suspect "
                        "corruption. Fail-closed by design: a corrupted marker "
                        "must not silently disable the gate."
                    )
    except (ImportError, OSError, AttributeError) as _gate_exc:
        _record_gate_failure("gate_1_5_correction", _gate_exc)

    # Low-friction-write check for the soft cluster (gates 2 / 4 / 4.5): writes to exploration/,
    # family/letters/, mansion/ are relational, not code work, so the discipline gates skip them.
    # The hard walls above (briefing-truly-stale, hedge, pull-detection, retry, context-governor)
    # still apply.
    _low_friction = input_data is not None and _is_low_friction_write(input_data)

    # Engagement-clearing consult commands (`divineos ask|recall|context|decide|briefing|...`) run
    # through Bash/PowerShell are treated like low-friction writes for the soft cluster, so the
    # command whose execution would clear the block is not pre-emptively blocked. The consult still
    # runs mark_engaged.
    if not _low_friction and input_data is not None:
        _tn = input_data.get("tool_name", "") or ""
        if _tn in ("Bash", "PowerShell"):
            _cmd = (input_data.get("tool_input", {}) or {}).get("command", "") or ""
            if _is_engagement_clearing_command(_cmd) or _is_doorbell_rearm(_cmd):
                _low_friction = True

    # Gate 2: session-fresh goal
    if not _low_friction:
        try:
            from divineos.core.hud_state import has_session_fresh_goal

            # touch=True: the guard is the one caller whose pass means work is
            # happening, so only it refreshes the goal (council-51a3676ac90b).
            if not has_session_fresh_goal(touch=True):
                soft_denies.append(
                    "BLOCKED: No goal set for this session. "
                    'Run: divineos goal add "what you are working on"'
                )
        except (ImportError, OSError, AttributeError) as _gate_exc:
            _record_gate_failure("gate_2_goal", _gate_exc)

    # Gate 3: pull detection (fabrication markers)
    try:
        from divineos.core.pull_detection import last_check

        check = last_check()
        if check is not None and not check.clean:
            markers = ", ".join(check.markers_fired)
            return _make_deny(
                f"BLOCKED: Pull detected — fabrication markers active: "
                f"{markers}. Run: divineos rt pull-check to reassess."
            )
    except (ImportError, OSError, AttributeError) as _gate_exc:
        _record_gate_failure("gate_3_pull_detection", _gate_exc)

    # Gate 4: engagement (light + deep tiers)
    if not _low_friction:
        try:
            from divineos.core.hud_handoff import engagement_status

            s = engagement_status()
            if not s.get("engaged", True):
                state = s.get("state", "drift")
                if state == "fresh":
                    _eng_msg = (
                        "BLOCKED: No engagement marker yet this session. "
                        "Briefing alone is not enough — engage with a thinking "
                        'tool first. Run: divineos ask "topic", recall, '
                        "context, or decide."
                    )
                elif state == "deep_drift":
                    deep_since = s.get("deep_actions_since", "?")
                    _eng_msg = (
                        f"BLOCKED: {deep_since} code actions since you last "
                        "consulted your knowledge. Light check-ins are not "
                        'enough. Run: divineos ask "topic" or divineos '
                        "recall to query what you actually know."
                    )
                else:
                    code_since = s.get("code_actions_since", "?")
                    _eng_msg = (
                        f"BLOCKED: {code_since} code actions since last thinking "
                        "command. Stop and think. Run: divineos ask, recall, "
                        "decide, or context before continuing."
                    )
                # Gate 4 (the engagement counter) is DEMOTED TO MEASUREMENT (Andrew authorized,
                # 2026-08-03): it records and says nothing. As a blocking gate it fired 84 times in
                # one session at an occupant who was inside the OS the whole time, because it
                # counted whether one of THIRTEEN approved command names was typed, out of 156
                # registered; `divineos claim`, `correction`, `audit`, `prereg` and reading OS
                # source did not count. A vocabulary test in a gate's clothes: it was cleared ~30
                # times with `divineos context | tail -2`, noise made only so the counter would
                # pass. A counter you must clear produces performances; a counter that only watches
                # produces measurements. Gate 4.5 below STILL BLOCKS, deliberately: it became a
                # block because warning failed.
                try:
                    from divineos.core.engagement_monitor import record as _eng_record

                    # input_data is Optional here: the tool name degrades to empty rather than the
                    # observation being lost or the recorder crashing.
                    _eng_tool = str((input_data or {}).get("tool_name", "") or "")
                    _eng_record(s, tool=_eng_tool)
                except Exception:  # noqa: BLE001 — telemetry must never gate
                    pass
        except (ImportError, OSError, AttributeError) as _gate_exc:
            _record_gate_failure("gate_4_engagement", _gate_exc)

    # Gate 4.5: consultation staleness (gate plus channel). When responses since the last
    # substantive consult exceed the threshold, substrate-modifying tools are denied and the message
    # OFFERS THE PATH: it inlines the unread correction and names the exact consult command.
    # Distinct from gate 4: that counts code actions and clears on cheap tools; this counts
    # RESPONSES and clears only on substrate-surfacing consults (ask / recall / corrections /
    # directives / active / compass), which are bypassed so they can never be blocked by their own
    # remedy.
    if not _low_friction:
        try:
            from divineos.core.consultation_tracker import (
                consultation_gate_status,
                gate_channel_message,
            )

            if consultation_gate_status().get("stale"):
                soft_denies.append(gate_channel_message())
        except (ImportError, OSError, AttributeError) as _gate_exc:
            _record_gate_failure("gate_4_5_consultation", _gate_exc)

    # Coalesced soft cluster: the goal / engagement / consultation denials surface TOGETHER, after
    # the last soft gate (4.5) and before the hard retry and governor walls, preserving the original
    # gate order.
    if soft_denies:
        return _make_deny(_combine_engagement_denies(soft_denies))

    # Gate 5 was removed (tiered-audit redesign); it is replaced by the informational drift_state
    # surface in the briefing.

    # Gate 6: retry blocker. Catches blind retries: the same command re-invoked after a failure with
    # no diagnostic step in between. Diagnostic commands (Read, Grep, git diff, divineos ask) clear
    # the block automatically.
    try:
        from divineos.core.retry_blocker import (
            check_retry,
            is_diagnostic_command,
            mark_investigated,
        )

        tool_name = (input_data or {}).get("tool_name", "")
        tool_input = (input_data or {}).get("tool_input", {}) or {}

        # If this IS a diagnostic command, mark all failures as investigated
        if tool_name and is_diagnostic_command(tool_name, tool_input):
            mark_investigated()
        elif tool_name:
            # Check if this is a blind retry
            deny_msg = check_retry(tool_name, tool_input)
            if deny_msg:
                return _make_deny(deny_msg)
    except (ImportError, OSError, AttributeError) as _gate_exc:
        _record_gate_failure("gate_6_retry_blocker", _gate_exc)

    # Gate 7: context-governor hard line (prereg-9b958c6493f3).
    governor_decision = _context_governor_gate(input_data)
    if governor_decision is not None:
        return governor_decision

    return None


def main() -> int:
    """Entry point. Reads hook input from stdin, writes decision to stdout.

    Exit code is always 0 — Claude Code carries the decision in the JSON
    payload, not in the exit code. Errors during gate evaluation result in
    fail-open (empty stdout = allow).
    """
    try:
        raw = sys.stdin.read()
        input_data = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, OSError):
        input_data = {}

    cmd = ""
    try:
        cmd = input_data.get("tool_input", {}).get("command", "") or ""
    except (AttributeError, TypeError):
        cmd = ""

    # Stashed for _nothing_ran_footer, which runs deep inside whichever gate refuses and has no
    # other way to see the line. Set once, next to the parse, not threaded through nineteen call
    # sites: a parameter every caller must remember is one someone eventually forgets, silently.
    global _REFUSED_COMMAND
    _REFUSED_COMMAND = cmd

    # Ownership-block gate runs BEFORE the bypass check: a mismatched substrate makes even
    # documented bypass commands unsafe, since they would read or write another agent's data-home.
    # Pairs with session_start.verify_session_ownership; recovery uses Edit and Write, which this
    # Bash gate does not see.
    block_decision = _check_ownership_block()
    if block_decision is not None:
        json.dump(block_decision, sys.stdout)
        return 0

    if _is_bypass_command(cmd):
        return 0

    # Overdue pre-registration block: fires when any pre-registration has reached its review count
    # without a terminal outcome; non-bypass tools are denied until the operator assesses or defers
    # (warnings alone did not work).
    overdue_decision = _check_overdue_prereg_block(cmd)
    if overdue_decision is not None:
        json.dump(overdue_decision, sys.stdout)
        return 0

    decision = _check_gates(input_data)
    if decision is not None:
        json.dump(decision, sys.stdout)

    return 0


if __name__ == "__main__":
    sys.exit(main())
