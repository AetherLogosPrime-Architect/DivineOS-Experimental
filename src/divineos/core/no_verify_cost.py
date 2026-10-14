"""no-verify cost-escalation — core decision logic, moved out of the bash hook.

The PreToolUse hook ``.claude/hooks/no-verify-cost-escalation.sh`` is the
doorbell; this module is the brain. Same shape as the audit_visibility,
deletion_discipline, and seal_hook migrations: keep the bash thin so the
hook can't drift from the convention, and put all the actual judgment
inside the OS.

Pop 2026-06-30: "where the right answer is the same every time, the
decision itself is wasted work. Removing the decision point removes the
leak. Replace the decision with structure so it makes the choice for you."

The hook script becomes ~10 lines. The convention is enforced by there
being nothing in the hook to misuse.

# Rule

Any ``git commit --no-verify`` or ``git push --no-verify`` in a Bash
tool-call must be accompanied by an inline
``DIVINEOS_NO_VERIFY_REASON="<one-line>"`` assignment. The reason is
logged to bypass_telemetry on the allow path so bypasses stay visible
in the substrate's drift surfaces.

# Why the bash version was wrong

Earlier today the bash hook was using bare ``python`` instead of
``find_divineos_python``. That ANTI-pattern is what
test_no_hook_uses_bare_python_for_divineos_imports catches. The bug
existed at all because the hook contained Python logic in the first
place — the kind of thing the OS-module-thin-hook split is designed
to prevent. Moving the logic here means the only python the hook
runs is the OS module call.
"""

from __future__ import annotations

import re
import shlex
from typing import Any

from divineos.core.command_parsing import program_name, shell_command_body


_REASON_PATTERN = re.compile(r'DIVINEOS_NO_VERIFY_REASON=(?:"([^"]+)"|\'([^\']+)\'|(\S+))')
_MIN_REASON_LEN = 8


_HEREDOC_RE = re.compile(
    r"""<<-?\s*(['\"]?)(\w+)\1.*?^\2\s*$""",
    re.DOTALL | re.MULTILINE,
)


def _strip_heredocs(cmd: str) -> str:
    """Remove heredoc BODIES before tokenising. They are data, not commands.

    MENTION IS NOT USE (2026-08-22). shlex.split flattens a heredoc, so the
    body of `git commit -F - <<EOF ... EOF` arrives as bare tokens and the
    gate reads the COMMIT MESSAGE as a second command. This gate blocked its
    own fix: the message documented the bug by quoting
    `git commit --no-verify -m x` as an example, and that example was parsed
    as a real invocation.

    The failure is self-selecting in the worst way -- the commit messages most
    likely to quote --no-verify are the ones explaining a --no-verify defect,
    so the gate fires hardest on the work that repairs it. Same shape as
    _strip_quoted_spans in the lepos translation gate: a checker that cannot
    tell talking-about from doing.

    Only the body is removed; the command line that opens the heredoc is kept,
    so a genuine `git commit --no-verify -F - <<EOF` is still caught.
    """
    return _HEREDOC_RE.sub(" ", cmd)


_SHELL_SEPARATORS = ("&&", "||", ";", "|", "&")

# `-n` is git commit's short form of --no-verify. Scoped per segment because
# `-n` means entirely different things to other commands.
_NO_VERIFY_FLAGS = ("--no-verify", "-n")


def _segments(tokens: list[str]) -> list[list[str]]:
    """Split a token list on shell separators into independent commands."""
    out: list[list[str]] = [[]]
    for tok in tokens:
        if tok in _SHELL_SEPARATORS:
            out.append([])
        else:
            out[-1].append(tok)
    return [seg for seg in out if seg]


_MAX_NESTING = 3


def _quoted_commands_in(seg: list[str]) -> list[str]:
    """Command strings a segment hands to another shell: ``bash -c "..."`` and ``eval ...``.

    The shared home answers what a shell is told to run; this only decides where in the
    segment a command could start. ``echo bash -c "..."`` talks about a shell and does
    not run one, so a shell word counts only behind env assignments and ``env``/``sudo``.
    """
    out: list[str] = []
    for i in range(len(seg)):
        if any(("=" not in t) and program_name(t) not in ("env", "sudo") for t in seg[:i]):
            break
        body = shell_command_body(seg[i:])
        if body is not None:
            out.append(body)
    return out


def _basename(token: str) -> str:
    return token.replace("\\", "/").rsplit("/", 1)[-1].lower()


def _is_git(token: str) -> bool:
    """``git``, ``/usr/bin/git`` and ``git.exe`` are the same program (Aria, 2026-10-13)."""
    return _basename(token) in ("git", "git.exe")


def _env_sets_hooks_path(token: str) -> bool:
    """``GIT_CONFIG_KEY_<n>=core.hooksPath``: the ``-c`` override, spelled as an environment variable."""
    key, sep, value = token.partition("=")
    if not sep:
        return False
    if key.upper().startswith("GIT_CONFIG_KEY_"):
        return _is_hooks_path_setting(value)
    # `GIT_CONFIG_PARAMETERS="'core.hookspath=/dev/null'"`: the same override, packed in one variable.
    return key.upper() == "GIT_CONFIG_PARAMETERS" and "core.hookspath" in value.lower()


def _has_unverified_git_write(tokens: list[str], depth: int = 0) -> str | None:
    """The subcommand of a git commit/push carrying a no-verify flag, else None.

    FIRST-GIT-WINS WAS THE BUG (2026-08-22, Andrew: "fix the reaching using
    automation so it does it automatically").

    This used to read ``tokens.index("git")`` -- the FIRST git in the whole
    command -- take the token after it as the subcommand, and return allow if
    that was not commit/push. So::

        git add -A && git commit --no-verify     -> first git is `add` -> ALLOWED

    which is the single most common shape a commit takes. The gate was not
    hanging, not unregistered and not misconfigured; it was anchored to a
    position I am almost never in. Measured that day: it denied
    ``git commit --no-verify -m x`` and went silent on the same commit behind
    ``cd ... && git add -A && ...``. Two --no-verify commits went through
    unchallenged in one session, and the gate's own telemetry showed a single
    lifetime use of the reason variable -- a gate that looked disciplined
    because almost nothing ever reached it.

    Segment-scoped rather than whole-command: a flag must belong to the git
    invocation it is being read against. Checking ``"-n" in tokens`` globally
    would fire on ``grep -n foo && git commit``, which is the over-fire that
    teaches me to reach for the escape hatch.

    GIT'S OWN OPTIONS SIT BETWEEN ``git`` AND THE SUBCOMMAND (2026-10-13, the
    second time this gate was anchored to a position). The subcommand was read
    as the token right after ``git``, so ``git -c core.hooksPath=/dev/null
    commit`` read as a subcommand named ``-c`` and was never recognised as a
    commit at all. I skipped every pre-commit check that way, on a merge, and
    nothing stopped me; Dad: "fix why you were even able to skip it so you
    cant". The same blind spot meant ``git -C some/folder commit --no-verify``
    also went unseen, and I type ``git -C`` constantly. Both are closed here:
    the options are stepped over to find the real subcommand, and a hooks-path
    override counts as the same act as ``--no-verify``, because it is.

    A SKIP INSIDE A QUOTED COMMAND (found the same day, by testing the fix
    rather than trusting it): ``bash -c "git commit --no-verify"`` is one
    quoted token to the tokenizer, so neither the old gate nor the first
    version of this fix saw a commit in it. Strings handed to ``bash -c``,
    ``sh -c`` and ``eval`` are now read as commands in their own right, to a
    shallow depth. And the hooks path set through the environment
    (``GIT_CONFIG_KEY_0=core.hooksPath``) counts like the ``-c`` form.
    """
    for seg in _segments(tokens):
        if depth < _MAX_NESTING:
            for inner in _quoted_commands_in(seg):
                try:
                    inner_tokens = shlex.split(inner)
                except ValueError:
                    continue
                found = _has_unverified_git_write(inner_tokens, depth + 1)
                if found:
                    return found
        if len(seg) < 2 or not _is_git(seg[0]):
            # `env FOO=bar git commit ...` and `sudo git ...` shapes: find git
            # anywhere in the segment, since a segment is one command.
            gi = next((n for n, t in enumerate(seg) if _is_git(t)), -1)
            if gi < 0:
                continue
        else:
            gi = 0
        sub, hooks_off, sub_at = _git_subcommand(seg, gi)
        hooks_off = hooks_off or any(_env_sets_hooks_path(t) for t in seg[:gi])
        if sub == "config" and (
            _sets_hooks_path(seg[sub_at + 1 :]) or _defines_skipping_alias(seg[sub_at + 1 :])
        ):
            # Setting core.hooksPath persists: every later commit skips the
            # checks without any flag to see. An alias that carries the skip
            # does the same under a name this gate cannot read (Aletheia, 2026-10-13).
            return sub
        if any(_defines_skipping_alias([t]) for t in seg[gi:sub_at]):
            return sub  # `git -c alias.c='commit --no-verify' c`: the alias carries the skip
        if sub not in _SKIPPABLE_SUBCOMMANDS:
            continue
        if hooks_off:
            return sub
        # `-n` is --no-verify for COMMIT only: for PUSH it is --dry-run and for MERGE
        # --no-stat. Treating them alike would deny a harmless rehearsal, and an
        # over-firing gate is how the reach for the escape hatch gets taught.
        for tok in seg[gi:]:
            if _is_no_verify_flag(tok) or (sub == "commit" and _is_short_cluster_with_n(tok)):
                return sub
    return None


# Every git command that runs the checks and accepts a way to skip them.
_SKIPPABLE_SUBCOMMANDS = ("commit", "push", "merge", "am", "rebase")


def _is_no_verify_flag(token: str) -> bool:
    """``--no-verify`` or any prefix git would still accept (``--no-verif``, ``--no-v``).

    Git takes any unambiguous prefix of a long option; ``--no-v`` is the shortest that
    is unique. Proven on a real repo with a failing hook: ``git commit --no-verif``
    commits with the hook skipped (Aletheia, 2026-10-13).
    """
    return token.startswith("--no-v") and "--no-verify".startswith(token)


def _is_short_cluster_with_n(token: str) -> bool:
    """``-n`` alone or joined with other short flags (``-nm``, ``-an``), but not ``--x`` words."""
    return bool(re.fullmatch(r"-[A-Za-z]+", token)) and "n" in token[1:]


def _defines_skipping_alias(args: list[str]) -> bool:
    """A config write or ``-c`` value that makes an alias carry the skip."""
    text = " ".join(args).lower()
    return "alias." in text and (
        "core.hookspath" in text or any(_is_no_verify_flag(w) for w in text.split())
    )


# Git options that sit before the subcommand and take the next token as their value.
_GIT_OPTS_TAKING_A_VALUE = ("-C", "--git-dir", "--work-tree", "--namespace", "--super-prefix")


def _is_hooks_path_setting(text: str) -> bool:
    return text.lower().startswith("core.hookspath")


def _git_subcommand(seg: list[str], gi: int) -> tuple[str, bool, int]:
    """Step over git's own leading options to the real subcommand.

    Returns ``(subcommand, hooks_path_overridden, index_of_subcommand)``. An
    override of core.hooksPath given as ``-c core.hooksPath=...`` (or the joined
    ``-ccore.hooksPath=...`` or ``--config-env`` forms) turns every hook off for
    that one command, which is exactly what ``--no-verify`` does.
    """
    i = gi + 1
    hooks_off = False
    while i < len(seg) and seg[i].startswith("-"):
        tok = seg[i]
        takes_next = i + 1 < len(seg)
        if tok == "-c" and takes_next:
            hooks_off = hooks_off or _is_hooks_path_setting(seg[i + 1])
            i += 2
        elif tok == "--config-env" and takes_next:
            hooks_off = hooks_off or _is_hooks_path_setting(seg[i + 1])
            i += 2
        elif tok in _GIT_OPTS_TAKING_A_VALUE and takes_next:
            i += 2
        else:
            if tok.startswith("-c") and _is_hooks_path_setting(tok[2:]):
                hooks_off = True
            if tok.lower().startswith("--config-env=") and _is_hooks_path_setting(tok[13:]):
                hooks_off = True
            i += 1
    return (seg[i] if i < len(seg) else ""), hooks_off, i


def _sets_hooks_path(args: list[str]) -> bool:
    """A ``git config`` that WRITES core.hooksPath (reading it back is harmless)."""
    reads = ("--get", "--get-all", "--list", "-l", "--get-regexp", "--unset", "--unset-all")
    if any(a in reads for a in args):
        return False
    for at, a in enumerate(args):
        # The key with nothing after it only reads the value back; a write has a value.
        if _is_hooks_path_setting(a):
            return any(not later.startswith("-") for later in args[at + 1 :])
    return False


def decide(tool_input: dict[str, Any] | None) -> dict[str, Any] | None:
    """Decide whether a Bash command containing --no-verify should pass.

    Returns:
        None  → allow (either irrelevant or has a valid named reason)
        dict  → deny with the structured PreToolUse JSON the hook prints

    Logging side-effect: on the allow-with-reason path, records the
    bypass to bypass_telemetry so it shows up in drift surfaces.
    """
    if not tool_input:
        return None
    cmd = (tool_input.get("command") or "").strip()
    if not cmd:
        return None

    try:
        tokens = shlex.split(_strip_heredocs(cmd))
    except ValueError:
        # Malformed shell quoting — let it through; another gate catches.
        return None

    subcommand = _has_unverified_git_write(tokens)
    if subcommand is None:
        return None

    # --no-verify on git commit/push. Demand an inline reason.
    match = _REASON_PATTERN.search(cmd)
    if match:
        reason = (match.group(1) or match.group(2) or match.group(3) or "").strip()
        if len(reason) < _MIN_REASON_LEN:
            return _deny(
                "BLOCKED: --no-verify reason too short "
                f"(< {_MIN_REASON_LEN} chars).\n"
                "Aletheia 2026-06-30 letter #13: the bypass must name what it\n"
                'is cover for. "fix", "tests", "wip" do not name the gate-shape\n'
                "being bypassed. Try a more specific reason such as:\n"
                f'  DIVINEOS_NO_VERIFY_REASON="gate blocks fix to gate" \\\n'
                f"    git {subcommand} --no-verify ..."
            )
        # Allow path — log the bypass to telemetry, then approve silently.
        try:
            from divineos.core.bypass_telemetry import record_bypass

            record_bypass(
                gate_name="git-" + subcommand + "-no-verify",
                env_var="DIVINEOS_NO_VERIFY_REASON",
                reason=reason,
            )
        except Exception:  # noqa: BLE001 — observability fail-open
            pass
        return None

    # No reason provided — block.
    return _deny(
        f"BLOCKED: git {subcommand} --no-verify requires a named reason.\n\n"
        "Aletheia 2026-06-30 (letter #13) flagged --no-verify as a structural\n"
        "signal: the bypass-telemetry caught all four uses on 2026-06-30 but\n"
        "did not stop them. This gate converts catch-without-stop into\n"
        "name-the-reason-or-block.\n\n"
        "Required form:\n"
        '  DIVINEOS_NO_VERIFY_REASON="<what the gate is wrong about>" \\\n'
        f"    git {subcommand} --no-verify ...\n\n"
        "The reason gets logged to bypass_telemetry so the bypasses stay\n"
        "visible in drift surfaces. Reason must be at least "
        f"{_MIN_REASON_LEN} chars and should name the gate-shape, not the\n"
        "surface symptom.\n\n"
        "If the gate is genuinely wrong-shape, file the bug first:\n"
        '  divineos audit submit-round "<gate>: wrong-shape" --actor aether\n'
        "and reference the round-id in the no-verify reason."
    )


def _deny(reason: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def main() -> int:
    """Entry point for the bash hook to call.

    Reads PreToolUse JSON from stdin, writes a decision (or nothing for
    allow) to stdout, exits 0. Fail-open on any unexpected error — the
    hook itself is observational and must not break the workflow.
    """
    import json
    import sys

    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:  # noqa: BLE001
        return 0
    if (data.get("tool_name") or "") != "Bash":
        return 0
    decision = decide(data.get("tool_input") or {})
    if decision is not None:
        sys.stdout.write(json.dumps(decision))
    return 0


__all__ = ["decide", "main"]
