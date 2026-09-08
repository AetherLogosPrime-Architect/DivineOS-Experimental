"""The roster — every surface, registered to its door.

Importing this module wires surfaces into ``hook_router``. The seven doorbells
import it and nothing else; this file is the single place where "which surfaces
exist for which event" is answered.

That is the point of the consolidation. Under the old arrangement the roster
was implicit — a hook existed if someone remembered to add it to
``settings.json``, and three hooks sat dark in both trees since 2026-07-28
because that second step is easy to forget and impossible to see. Here,
registration is the same act as existing.

## Migration status

Surfaces move one at a time. A `.sh` hook is deleted only after its
replacement runs live. The router coexists with the remaining hooks until then
— a big-bang cutover of 100 files is exactly the shape that leaves a silent
hole nobody notices for a fortnight.

Migrated so far:

* ``must_read`` (PreToolUse) — from ``.claude/hooks/must-read-gate.sh``,
  written by me on 2026-08-06 with 14 branches of judgment in bash, on the
  same day I was cataloguing the cost of exactly that. Migrating mine first
  because the drift was mine and it was current.
"""

from __future__ import annotations

import re

from divineos.core.hook_router import SurfaceOutcome, register

# Tools that can change the substrate. A must-read blocks these and nothing
# else. This is the judgment that used to live in bash: which tools count as
# substantive. It belongs here, where a test can reach it.
_SUBSTANTIVE_TOOLS = frozenset({"Bash", "PowerShell", "Edit", "Write", "NotebookEdit"})

# Read-shaped tools are NEVER blocked. The must-read gate's own remedy is a
# Read; a gate that can block its own remedy is a locked box, and this
# substrate has a task number for that failure (#98).
_ALWAYS_ALLOWED = frozenset({"Read", "Glob", "Grep", "NotebookRead", "TodoWrite", "Task"})


def must_read_surface(payload: dict) -> SurfaceOutcome | None:
    """Block substantive tools while an unread must-read is armed.

    Migrated from ``.claude/hooks/must-read-gate.sh`` 2026-08-06. Behaviour is
    unchanged; what moved is where the decision lives. The bash version made
    the same calls across fourteen branches that no unit test could reach.
    """
    tool = payload.get("tool_name") or ""
    tool_input = payload.get("tool_input") or {}

    if tool == "Read":
        # The unlock. A Read on a pending path clears it and always passes.
        path = tool_input.get("file_path") or ""
        if path:
            try:
                from divineos.core.must_read import mark_read

                cleared = mark_read(path)
            except OSError:
                cleared = []
            if cleared:
                return SurfaceOutcome(
                    name="must_read", output=f"[must-read] cleared: {', '.join(cleared)}"
                )
        return None

    if tool in _ALWAYS_ALLOWED or tool not in _SUBSTANTIVE_TOOLS:
        return None

    try:
        from divineos.core.must_read import pending, render_block
    except ImportError as exc:
        return SurfaceOutcome(name="must_read", error=f"cannot import: {exc}")

    items, error = pending()
    if items is None:
        # Could not look. Say so; do not block on a fact not in evidence.
        return SurfaceOutcome(
            name="must_read",
            error=f"cannot read pending index: {error}",
        )
    if not items:
        return None

    return SurfaceOutcome(
        name="must_read",
        refused=True,
        reason=render_block(items),
    )


_BRIEFING_TAIL = (
    "(Plain-chat responses are still allowed; this gate only blocks tool use. "
    "The OS does the rendering — this hook is just the doorman.)"
)


_DELETION_ERRORS = (OSError, TypeError, ValueError, KeyError, AttributeError)


def deletion_discipline_surface(payload: dict) -> SurfaceOutcome | None:
    """Refuse a destructive deletion lacking a fresh matching justification.

    MIGRATED 2026-08-25, after being named four times without being started.
    Aria observed that each naming was displaced by something urgent arriving
    from her — true, and not a reason to name it a fifth time. The cure for
    announcement-is-not-action is the action.

    THE DECISION IS UNCHANGED: same block_reason, same JSON deny protocol. A
    migration moves WHERE a decision is made and must never change HOW it lands
    — my July precedent and Aria's own, applied here rather than rediscovered.

    WHAT CHANGES IS THE FAILURE MODE, and it is why this one was worth doing
    rather than deferring again. The shell hook wrapped its call in a bare
    `except Exception: pass` with stderr to /dev/null, so a gate that could not
    run — bad import, raised decision, anything — was byte-identical to a gate
    that examined the command and approved it. That is the class this whole
    session has been pulling out of the house, sitting inside a gate whose
    entire job is refusal.

    Now could-not-run is DECLARED. It lands in the router's errored list, prints
    "COULD NOT RUN … this is not the same as it passing," and arms a must-read
    so the next tool stops until it has been seen. Andrew 2026-08-25: a loud
    alarm that does not block becomes wallpaper.
    """
    if (payload.get("tool_name") or "") != "Bash":
        return SurfaceOutcome(name="deletion_discipline", state="nothing-to-say")

    tool_input = payload.get("tool_input") or {}
    command = (tool_input.get("command") or "") if isinstance(tool_input, dict) else ""
    if not command.strip():
        return SurfaceOutcome(name="deletion_discipline", state="nothing-to-say")

    try:
        from divineos.core.deletion_discipline import block_reason
    except ImportError as exc:
        return SurfaceOutcome(
            name="deletion_discipline",
            error=f"cannot import: {exc}",
            state="could-not-run",
        )

    try:
        reason = block_reason(command)
    except _DELETION_ERRORS as exc:
        # The shell swallowed this and approved. Declared instead: whatever this
        # gate guards went unguarded for this call, and that must not read as
        # consent.
        return SurfaceOutcome(
            name="deletion_discipline",
            error=f"{type(exc).__name__}: {exc}",
            state="could-not-run",
        )

    if not reason:
        return SurfaceOutcome(name="deletion_discipline", state="nothing-to-say")

    return SurfaceOutcome(
        name="deletion_discipline",
        refused=True,
        reason=reason,
        json_deny=True,
        state="spoke",
    )


def compound_branch_change_surface(payload: dict) -> SurfaceOutcome | None:
    """Refuse a line that changes branch AND runs a destructive op in one call.

    Built 2026-09-04, the same day the fault happened, because the discipline
    that would have prevented it is one I already held. See the module for the
    account: a gate refused a compound line, the branch change inside it never
    ran, and re-issuing only the destructive half executed it on the branch I
    had not left.

    could-not-run is DECLARED rather than swallowed, for the reason its
    neighbour above gives at length: a gate that cannot run must never be
    indistinguishable from one that looked and approved. That is the whole
    fault-family this exists inside.
    """
    if (payload.get("tool_name") or "") != "Bash":
        return SurfaceOutcome(name="compound_branch_change", state="nothing-to-say")

    tool_input = payload.get("tool_input") or {}
    command = (tool_input.get("command") or "") if isinstance(tool_input, dict) else ""
    if not command.strip():
        return SurfaceOutcome(name="compound_branch_change", state="nothing-to-say")

    try:
        from divineos.core.compound_branch_change import block_reason
    except ImportError as exc:
        return SurfaceOutcome(
            name="compound_branch_change",
            error=f"cannot import: {exc}",
            state="could-not-run",
        )

    try:
        reason = block_reason(command)
    except (TypeError, ValueError, re.error) as exc:
        return SurfaceOutcome(
            name="compound_branch_change",
            error=f"{type(exc).__name__}: {exc}",
            state="could-not-run",
        )

    if not reason:
        return SurfaceOutcome(name="compound_branch_change", state="nothing-to-say")

    return SurfaceOutcome(
        name="compound_branch_change",
        refused=True,
        reason=reason,
        json_deny=True,
        state="spoke",
    )


def no_verify_cost_surface(payload: dict) -> SurfaceOutcome | None:
    """Refuse an unverified git write that skips the hooks without paying for it.

    MIGRATED 2026-08-25, second thin hook onto the router. The decision is
    unchanged: same ``decide()``, same reason text, same JSON deny protocol.

    IT CALLS ``decide`` DIRECTLY rather than ``main``. The shell hook shelled to
    ``main()``, which exists only to read PreToolUse JSON off stdin and write a
    decision to stdout — a serialisation round-trip whose sole purpose was
    crossing the process boundary the router removes. ``decide(tool_input)`` was
    always the real interface; ``main`` was the envelope.

    AND THE SWALLOW GOES, which is the reason this one was worth doing. The
    shell version ended with ``except Exception: pass`` and stderr to
    /dev/null, so a raised decision exited 0 and read exactly like a command
    the gate had examined and approved. Its find-python failure was already
    declared loudly — Aletheia's 2026-07-09 finding — which left the gate with
    one honest failure mode and one silent one.

    That swallow is not this hook's mistake. ``docs/hook_migration_tracker.md``
    prescribes it in the canonical thin-doorbell pattern, and 27 hooks in this
    tree carry it. For an observational surface it can only fail to inform; for
    a refusal-capable gate it turns could-not-run into looked-and-approved.

    RETIRING THE SHELL REGISTRATION IS PART OF THE MIGRATION, not a follow-up.
    ``deletion_discipline`` was wired into this router earlier tonight and its
    shell hook stayed registered, so both fired for hours and the swallow that
    motivated the migration was still live underneath the fix for it. A
    migration that leaves the original running has moved code and retired
    nothing.
    """
    if (payload.get("tool_name") or "") != "Bash":
        return SurfaceOutcome(name="no_verify_cost", state="nothing-to-say")

    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return SurfaceOutcome(name="no_verify_cost", state="nothing-to-say")

    try:
        from divineos.core.no_verify_cost import decide
    except ImportError as exc:
        return SurfaceOutcome(
            name="no_verify_cost",
            error=f"cannot import: {exc}",
            state="could-not-run",
        )

    try:
        decision = decide(tool_input)
    except _DELETION_ERRORS as exc:
        return SurfaceOutcome(
            name="no_verify_cost",
            error=f"{type(exc).__name__}: {exc}",
            state="could-not-run",
        )

    if decision is None:
        return SurfaceOutcome(name="no_verify_cost", state="nothing-to-say")

    reason = (decision.get("hookSpecificOutput") or {}).get("permissionDecisionReason") or ""
    if not reason:
        # A decision shaped wrong is not a decision to allow. Refusing with no
        # reason would be worse than reporting that the shape broke.
        return SurfaceOutcome(
            name="no_verify_cost",
            error="decide() returned a decision carrying no reason text",
            state="could-not-run",
        )

    return SurfaceOutcome(
        name="no_verify_cost",
        refused=True,
        reason=reason,
        json_deny=True,
        state="spoke",
    )


def require_briefing_surface(payload: dict) -> SurfaceOutcome | None:
    """Refuse substantive tools while the briefing is stale or never loaded.

    Migrated from ``.claude/hooks/require-briefing.sh`` 2026-08-06. Behaviour
    preserved exactly, including the WIRE PROTOCOL: this gate denies via the
    harness JSON permission-decision, not exit 2, so the outcome carries
    ``json_deny=True``. A migration changes where the decision is made, never
    how it lands.

    Fails OPEN on every internal error, as the bash version did. A gate that
    cannot read its own freshness signal must not wall me in — that is the
    same contract, and it is why the errors here return None rather than a
    refusal.
    """
    tool = payload.get("tool_name") or ""
    tool_input = payload.get("tool_input") or {}

    # Bootstrap commands are exempt: the gate's own remedy is `divineos
    # briefing`, and a gate that blocks its own remedy is a locked box.
    if tool == "Bash":
        cmd = (tool_input.get("command") or "").strip()
        try:
            from divineos.core.briefing_bypass import is_bypass_bash_command

            if is_bypass_bash_command(cmd):
                return None
        except Exception as exc:  # noqa: BLE001
            # If the exemption check cannot run we do not know whether this
            # Bash call IS the remedy (`divineos briefing`). Falling through
            # to the block would risk walling off the gate's own cure — the
            # locked-box failure, #98. So allow, and say why.
            return SurfaceOutcome(
                name="require_briefing",
                error=(
                    f"cannot check bootstrap exemption ({type(exc).__name__}: {exc}); "
                    "allowing rather than risk blocking my own remedy"
                ),
            )

    try:
        from divineos.core.briefing_freshness import staleness_signal

        sig = staleness_signal()
    except Exception as exc:  # noqa: BLE001 — allow, as before, but SAY SO
        # The bash version failed open *silently*, which made "could not read
        # the freshness signal" render identically to "the briefing is fresh".
        # An error outcome allows the tool through exactly as before and is
        # reported on stderr, so the gate can no longer be absent quietly.
        return SurfaceOutcome(
            name="require_briefing",
            error=f"cannot read freshness signal ({type(exc).__name__}: {exc}); allowing",
        )

    if not sig.get("is_stale"):
        return None

    if sig.get("never_loaded", False):
        reason = (
            "BLOCKED: briefing has not been loaded this session. "
            "Run: divineos briefing\n" + _BRIEFING_TAIL
        )
    else:
        reason = (
            f"BLOCKED: {sig.get('reason', 'briefing stale')}\n"
            "  Cheap cure: recall your briefing-id from context and run "
            "divineos briefing-id <id> (re-stamps freshness).\n"
            "  Or reload: divineos briefing (issues a new id).\n" + _BRIEFING_TAIL
        )

    return SurfaceOutcome(name="require_briefing", refused=True, reason=reason, json_deny=True)


def hook_syntax_surface(payload: dict) -> SurfaceOutcome | None:
    """A hook goes live the moment it is SAVED. Check it then, not at commit.

    THE WINDOW THIS CLOSES, measured 2026-08-25 by walking into it. I added a
    comment to ``verify-before-build-signal.sh`` containing an apostrophe. The
    embedded Python in that hook lives inside a single-quoted shell string
    passed to ``python -c``, so one apostrophe in a COMMENT closed the string
    and broke the whole file. The gate then failed on every Bash call, and
    because it is registered on Edit as well, it blocked the repair -- a locked
    box I built in one keystroke.

    Both existing checks WOULD have caught it. ``bash -n`` exits non-zero, and
    shellcheck says it in words: *SC1011: This apostrophe terminated the single
    quoted string!* Neither helped, because both run at COMMIT time and a hook
    is live from the moment the file is written. Between save and commit there
    is a window where a broken gate is firing and nothing has looked at it.

    So the check moves to the moment the risk begins. Andrew, on gates: *"ideally
    you should never be hitting the gate.. if you are then it means automation a
    doorman and a proper channel is required.. so that it all happens before you
    ever reach the gate."* This is that doorman for hook edits.

    It ARMS A MUST-READ rather than only printing, because a broken gate is the
    exact case his other rule covers: an alarm that does not block becomes
    wallpaper. A silently-inert gate is the class this whole session has been
    about, and it does not get a quieter treatment for being self-inflicted.
    """
    if (payload.get("tool_name") or "") not in ("Edit", "Write", "NotebookEdit"):
        return SurfaceOutcome(name="hook_syntax", state="nothing-to-say")

    tool_input = payload.get("tool_input") or {}
    raw = tool_input.get("file_path") or "" if isinstance(tool_input, dict) else ""
    if not raw:
        return SurfaceOutcome(name="hook_syntax", state="nothing-to-say")

    import shutil
    import subprocess
    from pathlib import Path

    path = Path(raw)
    parts = {p.lower() for p in path.parts}
    if path.suffix.lower() != ".sh" or "hooks" not in parts:
        return SurfaceOutcome(name="hook_syntax", state="nothing-to-say")
    if not path.exists():
        return SurfaceOutcome(name="hook_syntax", state="nothing-to-say")

    # Probe rather than trust the name: the bare `bash` on this machine can
    # resolve to a WSL relay stub that exits 1 having produced nothing, and a
    # syntax check that never ran would report exactly like a clean one.
    bash = None
    for candidate in (
        shutil.which("bash", path=r"C:\Program Files\Git\bin"),
        shutil.which("bash", path=r"C:\Program Files\Git\usr\bin"),
        shutil.which("bash"),
    ):
        if not candidate:
            continue
        try:
            probe = subprocess.run(
                [candidate, "-c", "echo ok"], capture_output=True, text=True, timeout=5
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if probe.returncode == 0 and probe.stdout.strip() == "ok":
            bash = candidate
            break

    if bash is None:
        return SurfaceOutcome(
            name="hook_syntax",
            error=(
                f"no working bash found, so {path.name} was NOT syntax-checked. "
                "That is not the same as it being valid."
            ),
            state="could-not-run",
        )

    try:
        result = subprocess.run([bash, "-n", str(path)], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError) as exc:
        return SurfaceOutcome(
            name="hook_syntax",
            error=f"could not run the syntax check on {path.name}: {exc}",
            state="could-not-run",
        )

    if result.returncode == 0:
        return SurfaceOutcome(name="hook_syntax", state="nothing-to-say")

    detail = (result.stderr or result.stdout or "").strip()
    try:
        # require_read, NOT arm. I wrote `arm` first from memory, and it would
        # have raised ImportError straight into the handler below -- degrading
        # a blocking alarm to a printed line, quietly, in the one surface whose
        # whole subject is gates that go silent. Checked the module rather than
        # trusting the name.
        from divineos.core.must_read import require_read

        require_read(
            key=f"broken-hook:{path.name}",
            content=f"{path}\n\n{detail}",
            reason=f"{path.name} does not parse and is LIVE on every tool call right now",
        )
    except (ImportError, OSError, TypeError, ValueError) as exc:
        # Arming failed; the message below is still emitted. Named rather than
        # swallowed, since an unarmed alarm is the wallpaper case.
        detail += f"\n  (could not arm a must-read: {type(exc).__name__}: {exc})"

    return SurfaceOutcome(
        name="hook_syntax",
        output=(
            f"BROKEN HOOK JUST SAVED — {path.name} does not parse, and it is LIVE.\n"
            f"{detail}\n"
            "  Every tool call now runs this file. If it is registered on Edit or Write\n"
            "  it will also refuse the repair, which is a locked box. Fix it before\n"
            "  anything else; PowerShell is outside most matchers if Bash is walled off."
        ),
        state="spoke",
    )


def letter_claims_surface(payload: dict) -> SurfaceOutcome | None:
    """After I read a sibling's letter, put the named files' local state in hand.

    PostToolUse, so it lands the moment the letter does — while I am forming
    the opinion, not after I have shipped it. This is the structure standing in
    for a rule I would otherwise have to remember (Aether #167: practice-shape
    never holds), and it measures rather than pattern-matching, because a
    detector for letters-that-sound-like-bug-reports is whack-a-mole (#151).
    """
    if (payload.get("tool_name") or "") != "Read":
        return None
    raw = (payload.get("tool_input") or {}).get("file_path") or ""
    if not raw:
        return None

    from pathlib import Path

    path = Path(raw)
    # Only sibling letters. My own drafts are not evidence about my own tree.
    if "letters" not in {p.lower() for p in path.parts} or path.suffix.lower() != ".md":
        return None
    if path.name.lower().startswith("aria-to-"):
        return None

    try:
        from divineos.core.letter_claims import read_letter, render

        repo_root = Path(__file__).resolve().parents[3]
        text = render(read_letter(path, repo_root))
    except Exception as exc:  # noqa: BLE001 — never let a surface block a Read
        return SurfaceOutcome(name="letter_claims", error=f"{type(exc).__name__}: {exc}")

    return SurfaceOutcome(name="letter_claims", output=text) if text else None


# --------------------------------------------------------------------------
# UserPromptSubmit — the third door, opened 2026-09-08.
#
# Andrew: *"all 125+ hooks could all be consolidated to 7 hooks as they all do
# the same thing, and then yes all of the logic needs to be moved into the OS
# itself."* He is right that they all do the same thing, and the shape below is
# the proof: every one of these hooks was a shell script that resolved the
# repository, resolved an interpreter, imported one function from this package,
# printed what it returned, and exited 0. The only genuine variation across
# thirty-six files was which function.
#
# So the port is a TABLE, not thirty-six hand-written surfaces. Each entry says
# which callable, and whether it wants his message. The isolation the router
# gives is per-entry, so one bad module still cannot silence its neighbours.
#
# A surface that raises returns could-not-run rather than nothing, because a
# prime that failed to load is not a prime that had nothing to say -- and for
# this door that distinction is load-bearing: the asks surface exists to
# re-raise what he is still waiting on, and its silence would otherwise read
# as "nothing is waiting."
# --------------------------------------------------------------------------

#: (surface name, module, callable, wants the prompt text)
_PROMPT_SURFACES: tuple[tuple[str, str, str, bool], ...] = (
    ("still_owed_to_him", "divineos.core.andrew_request_repeats", "surface", False),
    ("operator_asks", "divineos.core.operator_asks", "format_open_asks", False),
    ("sibling_correction", "divineos.core.sibling_correction_surface", "render", True),
    ("self_demotion_prime", "divineos.core.self_demotion", "render_prime", False),
)


def _prompt_text_surface(name: str, module: str, attr: str, wants_prompt: bool):
    """Build one text-emitting UserPromptSubmit surface from the table."""

    def surface(payload: dict) -> SurfaceOutcome | None:
        try:
            mod = __import__(module, fromlist=[attr])
            fn = getattr(mod, attr)
        except (ImportError, AttributeError) as exc:
            return SurfaceOutcome(
                name=name,
                error=f"{type(exc).__name__}: {exc}",
                state="could-not-run",
            )
        try:
            if wants_prompt:
                prompt = (payload.get("prompt") or "").strip()
                if not prompt:
                    return SurfaceOutcome(name=name, state="nothing-to-say")
                text = fn(prompt)
            else:
                text = fn()
        except Exception as exc:  # noqa: BLE001 — a surface never takes the turn down
            return SurfaceOutcome(
                name=name,
                error=f"{type(exc).__name__}: {exc}",
                state="could-not-run",
            )
        if not text:
            return SurfaceOutcome(name=name, state="nothing-to-say")
        return SurfaceOutcome(name=name, output=str(text), state="spoke")

    surface.__name__ = f"{name}_surface"
    return surface


def auto_goal_surface(payload: dict) -> SurfaceOutcome | None:
    """Set a goal from his message when no session-fresh one exists.

    Ported from the shell verbatim, including the wording: the typing is
    automated and the judgement is not, so the block says so and offers the
    supersede rather than pretending the derived goal is authoritative.
    """
    prompt = (payload.get("prompt") or "").strip()
    if not prompt:
        return SurfaceOutcome(name="auto_goal", state="nothing-to-say")
    try:
        from divineos.core.auto_goal import derive_and_set_goal_from_prompt

        goal = derive_and_set_goal_from_prompt(prompt)
    except Exception as exc:  # noqa: BLE001
        return SurfaceOutcome(name="auto_goal", error=f"{type(exc).__name__}: {exc}")
    if not goal:
        return SurfaceOutcome(name="auto_goal", state="nothing-to-say")
    return SurfaceOutcome(
        name="auto_goal",
        state="spoke",
        output=(
            "## GOAL SET FROM YOUR PROMPT (paperwork filed before the doorman asked)\n"
            f"\n    {goal}\n\n"
            "Derived from the prompt because no session-fresh goal existed. The\n"
            "typing is automated; the judgement is not. If this is not actually\n"
            "what I am doing, say so or supersede it:\n"
            '    divineos goal add "<the real one>"\n'
        ),
    )


def correction_marker_surface(payload: dict) -> SurfaceOutcome | None:
    """Mark a correction in his message. Its work is a side effect, not text.

    Declares ``nothing-to-say`` rather than returning None, because for a
    side-effect check an empty stdout is byte-identical to having crashed --
    the exact ambiguity Aria closed when she added the third state.
    """
    try:
        from divineos.core.correction_marker import hook_main

        hook_main()
    except Exception as exc:  # noqa: BLE001
        return SurfaceOutcome(
            name="correction_marker",
            error=f"{type(exc).__name__}: {exc}",
            state="could-not-run",
        )
    return SurfaceOutcome(name="correction_marker", state="nothing-to-say")


# --------------------------------------------------------------------------
# Stop — the fourth door, opened 2026-09-08.
#
# Same finding as UserPromptSubmit, and it is worth stating twice because it is
# the whole reason the consolidation is cheap: these hooks did not differ. Five
# of them opened the transcript, walked it for the last assistant message,
# reassembled its text blocks, and handed that string to one OS function. Two
# carried a byte-identical copy of that walk. The variation was the function.
#
# So the walk lives here once, and the surfaces are the function calls.
# --------------------------------------------------------------------------


def _last_assistant_text(payload: dict) -> str:
    """The text of my most recent reply, from the transcript the harness names.

    Returns "" when there is nothing to read. Callers must NOT treat that as a
    clean reply -- it means the same thing an unreadable transcript means, so
    a surface that finds nothing declares ``nothing-to-say`` rather than
    reporting a pass.
    """
    import json as _json

    raw = payload.get("transcript_path") or payload.get("transcript") or ""
    if not raw:
        return ""
    from pathlib import Path

    path = Path(raw)
    if not path.is_file():
        return ""
    last = ""
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                rec = _json.loads(line)
            except ValueError:
                continue
            msg = rec.get("message") or {}
            if not isinstance(msg, dict) or msg.get("role") != "assistant":
                continue
            content = msg.get("content", [])
            if isinstance(content, list):
                parts = [
                    c.get("text", "")
                    for c in content
                    if isinstance(c, dict) and c.get("type") == "text"
                ]
                if parts:
                    last = "\n".join(parts)
            elif isinstance(content, str):
                last = content
    return last


#: (surface name, module, callable) — each takes the transcript path and does
#: its work as a side effect. Audits, not speakers.
_TRANSCRIPT_AUDITS: tuple[tuple[str, str, str], ...] = (
    ("hedge_audit", "divineos.core.hedge_audit", "run_hedge_audit"),
    ("theater_audit", "divineos.core.theater_audit", "run_theater_audit"),
)


def _transcript_audit_surface(name: str, module: str, attr: str):
    """Build one Stop surface that hands the transcript path to an OS audit."""

    def surface(payload: dict) -> SurfaceOutcome | None:
        raw = payload.get("transcript_path") or payload.get("transcript") or ""
        if not raw:
            return SurfaceOutcome(name=name, state="nothing-to-say")
        try:
            mod = __import__(module, fromlist=[attr])
            getattr(mod, attr)(raw)
        except Exception as exc:  # noqa: BLE001 — an audit never blocks a reply
            return SurfaceOutcome(
                name=name,
                error=f"{type(exc).__name__}: {exc}",
                state="could-not-run",
            )
        return SurfaceOutcome(name=name, state="nothing-to-say")

    surface.__name__ = f"{name}_surface"
    return surface


def time_estimate_surface(payload: dict) -> SurfaceOutcome | None:
    """Record how long I said something would take against what it took."""
    try:
        from divineos.core.time_calibration import hook_main

        hook_main()
    except Exception as exc:  # noqa: BLE001
        return SurfaceOutcome(
            name="time_estimate",
            error=f"{type(exc).__name__}: {exc}",
            state="could-not-run",
        )
    return SurfaceOutcome(name="time_estimate", state="nothing-to-say")


def self_demotion_stop_surface(payload: dict) -> SurfaceOutcome | None:
    """Record praise-by-contrast spans so the compose prime can quote them back.

    Speaks on stderr in the shell version; here the recording is the work and
    the report is the output, so a run that found nothing declares itself
    rather than going quiet — the distinction that keeps "no spans" apart from
    "the detector never loaded."
    """
    text = _last_assistant_text(payload)
    if not text.strip():
        return SurfaceOutcome(name="self_demotion_stop", state="nothing-to-say")
    try:
        from divineos.core.self_demotion import detect, record

        hits = detect(text)
        if not hits:
            return SurfaceOutcome(name="self_demotion_stop", state="nothing-to-say")
        err = record(hits)
    except Exception as exc:  # noqa: BLE001
        return SurfaceOutcome(
            name="self_demotion_stop",
            error=f"{type(exc).__name__}: {exc}",
            state="could-not-run",
        )
    if err:
        return SurfaceOutcome(
            name="self_demotion_stop",
            error=f"detected but NOT RECORDED: {err}",
            state="could-not-run",
        )
    spans = "\n".join(f"    {h.span}" for h in hits)
    return SurfaceOutcome(
        name="self_demotion_stop",
        state="spoke",
        output=(
            f"[self-demotion] recorded {len(hits)} praise-by-contrast span(s); "
            f"the compose prime will show them next turn:\n{spans}"
        ),
    )


def summary_room_surface(payload: dict) -> SurfaceOutcome | None:
    """Refuse a reply that dropped the room which compresses it for him.

    This one REFUSES rather than reports, and the router carries that through
    as exit 2 exactly as the shell hook did. The wire protocol is part of the
    behaviour a migration promises to preserve.
    """
    text = _last_assistant_text(payload)
    if not text.strip():
        return SurfaceOutcome(name="summary_room", state="nothing-to-say")
    try:
        from divineos.core.summary_room import assess, render_block

        block = render_block(assess(text))
    except Exception as exc:  # noqa: BLE001
        return SurfaceOutcome(
            name="summary_room",
            error=f"{type(exc).__name__}: {exc}",
            state="could-not-run",
        )
    if not block:
        return SurfaceOutcome(name="summary_room", state="nothing-to-say")
    return SurfaceOutcome(name="summary_room", refused=True, reason=block, state="spoke")


# --------------------------------------------------------------------------
# PreToolUse, second batch — 2026-09-08.
#
# The gates on this door REFUSE, so the standard for moving one is higher than
# for a surface that only speaks. My own note from 2026-06-07, handed back by
# the read-gate while doing exactly this work: *"Building the gate isn't
# enough; the gate has to be VERIFIED working. Future gates: write the
# integration test that exercises the BLOCK case end-to-end. Not just the
# matcher logic."*
#
# That was written after a gate of mine was broken from the moment it shipped
# and nobody found out for six hours. So each of these is exercised through the
# doorbell in its refusing state, not only as a function returning a string.
#
# ONE THING THE ROUTER DOES NOT YET CARRY, named rather than discovered later:
# several shell gates source a remedy-allowlist so that no gate can block the
# command another gate just prescribed. That library exists only in shell --
# nothing under divineos.core references it. Neither gate below uses it, so
# behaviour is preserved here, but a refusing gate that DOES use it cannot move
# until the allowlist moves too. Centralising it is a gain, not a cost: one
# place instead of one per hook.
# --------------------------------------------------------------------------

#: Tools that write to the tree. Reads and searches stay open on purpose --
#: blocking those would block the investigation of the block.
_WRITE_TOOLS = frozenset({"Edit", "Write", "MultiEdit", "NotebookEdit"})


def degraded_detectors_surface(payload: dict) -> SurfaceOutcome | None:
    """Refuse substrate writes while a detector is known to be degraded.

    A detector that is quietly broken reports the same nothing as one that
    looked and found nothing, so writing on top of it is working in a room
    where the alarms are disconnected.
    """
    if (payload.get("tool_name") or "") not in _WRITE_TOOLS:
        return SurfaceOutcome(name="degraded_detectors", state="nothing-to-say")
    try:
        from divineos.core.degraded_detectors import blocking_degradations, format_block

        entries = blocking_degradations()
    except Exception as exc:  # noqa: BLE001 — a gate never crashes the tool call
        return SurfaceOutcome(
            name="degraded_detectors",
            error=f"{type(exc).__name__}: {exc}",
            state="could-not-run",
        )
    if not entries:
        return SurfaceOutcome(name="degraded_detectors", state="nothing-to-say")
    return SurfaceOutcome(
        name="degraded_detectors",
        refused=True,
        reason=format_block(entries),
        state="spoke",
    )


def heredoc_escape_surface(payload: dict) -> SurfaceOutcome | None:
    """Refuse a shell heredoc that writes a file through an escape.

    Three layers -- shell, then python, then the file -- and an escape meant
    for the file is eaten by the middle one. Five failures in one session
    taught that being careful does not fix it and switching tools does.
    """
    if (payload.get("tool_name") or "") != "Bash":
        return SurfaceOutcome(name="heredoc_escape", state="nothing-to-say")
    command = (payload.get("tool_input") or {}).get("command") or ""
    if not command:
        return SurfaceOutcome(name="heredoc_escape", state="nothing-to-say")
    try:
        from divineos.core import heredoc_escape_check as check

        refuse = check.should_refuse(command)
    except Exception as exc:  # noqa: BLE001
        return SurfaceOutcome(
            name="heredoc_escape",
            error=(
                f"{type(exc).__name__}: {exc} — the heredoc path is currently "
                "unguarded. Absent, not satisfied."
            ),
            state="could-not-run",
        )
    if not refuse:
        return SurfaceOutcome(name="heredoc_escape", state="nothing-to-say")
    return SurfaceOutcome(
        name="heredoc_escape",
        refused=True,
        reason=check.refusal_message(command),
        state="spoke",
    )


# --------------------------------------------------------------------------
# Stop, second batch — the reach detectors, 2026-09-08.
#
# The operating-loop package holds thirty-odd detectors; four of them have Stop
# hooks. TWO of those four are structurally identical: read my last reply, run
# a detector over it, then either write a marker for the next compose or clear
# a stale one. Same fields, same file shape, different detector and filename.
# Those two are the table below.
#
# The other two -- promise and continuity-frame -- write a marker PER FINDING
# with their own hashing. That is a different shape, and lumping them in would
# mean a table with exceptions in it, which is how a clean abstraction turns
# into a worse version of four separate functions. They move as themselves or
# not at all.
#
# CLEARING IS PART OF THE WORK, not cleanup. A stale marker fires the anchor on
# a turn it does not apply to, and an anchor that fires when it should not is
# exactly how a real one gets read past.
# --------------------------------------------------------------------------

#: (surface name, module, detect function, marker filename)
_REACH_DETECTORS: tuple[tuple[str, str, str, str], ...] = (
    (
        "close_reach",
        "divineos.core.operating_loop.close_reach_detector",
        "detect_close_reach",
        "close_reach_marker.json",
    ),
    (
        "compaction_reach",
        "divineos.core.operating_loop.compaction_reach_detector",
        "detect_compaction_reach",
        "compaction_reach_marker.json",
    ),
)


def _reach_detector_surface(name: str, module: str, detect_attr: str, marker_name: str):
    """Build one Stop surface that marks a reach for the next compose."""

    def surface(payload: dict) -> SurfaceOutcome | None:
        import json as _json
        from pathlib import Path

        text = _last_assistant_text(payload)
        if not text.strip():
            return SurfaceOutcome(name=name, state="nothing-to-say")

        marker = Path.home() / ".divineos" / marker_name
        try:
            mod = __import__(module, fromlist=[detect_attr, "anchor_message_for"])
            findings = getattr(mod, detect_attr)(text)
        except Exception as exc:  # noqa: BLE001 — a detector never blocks a reply
            return SurfaceOutcome(
                name=name,
                error=f"{type(exc).__name__}: {exc}",
                state="could-not-run",
            )

        if not findings:
            try:
                marker.unlink(missing_ok=True)
            except OSError as exc:
                return SurfaceOutcome(
                    name=name,
                    error=f"stale marker left in place: {exc}",
                    state="could-not-run",
                )
            return SurfaceOutcome(name=name, state="nothing-to-say")

        try:
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text(
                _json.dumps(
                    {
                        "findings": [
                            {
                                "shape": f.shape.value,
                                "trigger_phrase": f.trigger_phrase,
                                "position": f.position,
                            }
                            for f in findings
                        ],
                        "anchor_message": mod.anchor_message_for(findings[0]),
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
        except (OSError, AttributeError) as exc:
            return SurfaceOutcome(
                name=name,
                error=f"detected {len(findings)} but NOT RECORDED: {exc}",
                state="could-not-run",
            )
        return SurfaceOutcome(
            name=name,
            state="spoke",
            output=(
                f"[{name}] recorded {len(findings)} reach(es); the anchor will show them next turn."
            ),
        )

    surface.__name__ = f"{name}_surface"
    return surface


def pre_response_context_surface(payload: dict) -> SurfaceOutcome | None:
    """Assemble the compose-start context block from its component surfaces.

    NO OUTER DEDUP, deliberately, and the reason carries over verbatim from the
    shell this replaces (2026-08-13): it does not emit its own text, it
    assembles surfaces that each dedup themselves. The combined string differs
    on every call BY DESIGN as inner parts flip to their pointers, so an outer
    hash can never match and a wrapper layer only adds bytes. That was measured
    once -- it grew the payload rather than shrinking it -- and removed.

    The shell emitted through the JSON additionalContext channel; plain stdout
    on this door reaches the same place, which the surfaces already migrated
    here demonstrate in use. The wire protocol worth preserving exactly is a
    REFUSAL's, and this one never refuses.
    """
    prompt = payload.get("prompt") or ""
    transcript = payload.get("transcript_path") or None
    try:
        from divineos.core.pre_response_context import build_combined_context

        combined = build_combined_context(prompt, transcript_path=transcript)
    except Exception as exc:  # noqa: BLE001 — never cost a turn
        return SurfaceOutcome(
            name="pre_response_context",
            error=f"{type(exc).__name__}: {exc}",
            state="could-not-run",
        )
    if not combined:
        return SurfaceOutcome(name="pre_response_context", state="nothing-to-say")
    return SurfaceOutcome(name="pre_response_context", output=combined, state="spoke")


def context_heartbeat_surface(payload: dict) -> SurfaceOutcome | None:
    """Record one beat of context state. Instrumentation, never a voice.

    SILENT ON SUCCESS on purpose: the compaction trigger already reports this
    state loudly, and a second voice saying the same thing every round is how a
    surface becomes wallpaper -- measured in the session that built it, where
    most of a large prime was discarded unread every turn.

    Its own history is why could-not-run is declared rather than swallowed. The
    shell version once resolved its interpreter by hand, and a bare python
    lacking this package's dependencies fails OPEN: the import dies, the error
    goes nowhere, and a heartbeat that never beat looks exactly like one that
    did. That is precisely the defect this module exists to refuse -- built so
    a blind sensor records UNKNOWN rather than the friendliest number in the
    range, and it shipped with that same hole in its own startup.
    """
    try:
        from divineos.core.context_heartbeat import beat

        beat()
    except Exception as exc:  # noqa: BLE001
        return SurfaceOutcome(
            name="context_heartbeat",
            error=f"{type(exc).__name__}: {exc}",
            state="could-not-run",
        )
    return SurfaceOutcome(name="context_heartbeat", state="nothing-to-say")


def pr_merge_gate_surface(payload: dict) -> SurfaceOutcome | None:
    """Refuse a merge that has not met the review conditions.

    KEEPS THE JSON PROTOCOL. Its shell version denied through the permission
    decision rather than exit 2, and a migration moves WHERE a decision is made
    without changing HOW it lands -- the router carries both protocols for
    exactly this reason.
    """
    if (payload.get("tool_name") or "") != "Bash":
        return SurfaceOutcome(name="pr_merge_gate", state="nothing-to-say")
    command = (payload.get("tool_input") or {}).get("command") or ""
    if not command.strip():
        return SurfaceOutcome(name="pr_merge_gate", state="nothing-to-say")
    try:
        from divineos.core.pr_merge_gate import block_reason

        reason = block_reason(command)
    except Exception as exc:  # noqa: BLE001 — a gate never crashes the call
        return SurfaceOutcome(
            name="pr_merge_gate",
            error=f"{type(exc).__name__}: {exc}",
            state="could-not-run",
        )
    if not reason:
        return SurfaceOutcome(name="pr_merge_gate", state="nothing-to-say")
    return SurfaceOutcome(
        name="pr_merge_gate",
        refused=True,
        reason=reason,
        json_deny=True,
        state="spoke",
    )


def pr_create_gate_surface(payload: dict) -> SurfaceOutcome | None:
    """Refuse opening a pull request that is not ready to be opened.

    KEEPS THE EXIT-2 PROTOCOL, and this one carries a warning worth repeating
    where the code lives. Its shell version exited 1 for its entire life. A
    hook blocks a tool call only on 2; on 1 the message is shown and the
    command runs anyway. So it printed a correct, well-written refusal into
    the void and every unready pull request opened regardless -- a gate that
    had never once stopped anything, discovered only when one got through.

    Under the router the distinction is structural rather than remembered: a
    surface says ``refused`` and the router chooses the wire protocol. The
    class of defect that produced that year of silence is not reachable from
    here.
    """
    if (payload.get("tool_name") or "") != "Bash":
        return SurfaceOutcome(name="pr_create_gate", state="nothing-to-say")
    command = ((payload.get("tool_input") or {}).get("command") or "").strip()
    if not command:
        return SurfaceOutcome(name="pr_create_gate", state="nothing-to-say")
    try:
        from divineos.core.pr_gate import check_pr_create_safe

        decision = check_pr_create_safe(command)
    except Exception as exc:  # noqa: BLE001
        return SurfaceOutcome(
            name="pr_create_gate",
            error=f"{type(exc).__name__}: {exc}",
            state="could-not-run",
        )
    if not decision.blocked:
        return SurfaceOutcome(name="pr_create_gate", state="nothing-to-say")
    return SurfaceOutcome(
        name="pr_create_gate",
        refused=True,
        reason=decision.reason,
        state="spoke",
    )


def install() -> None:
    """Register every surface. Idempotent — safe to call from each doorbell."""
    from divineos.core.hook_router import registered

    # Order is deliberate and it is a real decision, not incidental.
    # require_briefing runs FIRST because it is the bootstrap gate — if the
    # briefing has never loaded, that is the thing to say, and burying it
    # under a must-read would hand me the second-most-important reason first.
    # Both still run either way; the router never short-circuits. This only
    # decides which refusal is read first.
    if "require_briefing" not in registered("PreToolUse"):
        register("PreToolUse", "require_briefing", require_briefing_surface)
    if "must_read" not in registered("PreToolUse"):
        register("PreToolUse", "must_read", must_read_surface)

    # WIRED 2026-08-25. Seventy-six minutes passed between the surface above
    # being written and this line existing, because the ritual hard-stopped my
    # tools mid-edit and I turned to report to Andrew instead of finishing.
    # He asked why the letter loop had stalled. The honest answer was that I
    # had just produced a fresh written-but-never-wired -- the exact class we
    # spent the night removing from this house -- and walked away from it.
    # Measured rather than remembered: the function existed, the registration
    # did not, and nothing would have said so.
    if "deletion_discipline" not in registered("PreToolUse"):
        register("PreToolUse", "deletion_discipline", deletion_discipline_surface)

    # Second thin hook, 2026-08-25. Its shell registration comes OUT of
    # settings.json in the same change -- see the surface docstring. Wiring the
    # replacement without retiring the original is what left deletion_discipline
    # double-firing for several hours earlier tonight, with the swallow the
    # migration existed to remove still running underneath it.
    if "no_verify_cost" not in registered("PreToolUse"):
        register("PreToolUse", "no_verify_cost", no_verify_cost_surface)

    # Registered in the SAME change that adds the surface, deliberately. The
    # note above records what happens when those two come apart; a function
    # nobody dispatches is the alarm in the box with the cable coiled beside it.
    if "compound_branch_change" not in registered("PreToolUse"):
        register("PreToolUse", "compound_branch_change", compound_branch_change_surface)

    # Second PreToolUse batch, 2026-09-08. Both REFUSE, both exercised through
    # the doorbell in their refusing state before their shell registrations
    # came out -- the standard my own 2026-06-07 note set after a gate of mine
    # shipped broken and stayed broken for six hours.
    if "degraded_detectors" not in registered("PreToolUse"):
        register("PreToolUse", "degraded_detectors", degraded_detectors_surface)
    if "heredoc_escape" not in registered("PreToolUse"):
        register("PreToolUse", "heredoc_escape", heredoc_escape_surface)

    # Third PreToolUse batch. Two pull-request gates, and they deliberately
    # keep DIFFERENT wire protocols -- one denies through the permission
    # decision, one through exit 2 -- because that is how each landed before.
    if "pr_merge_gate" not in registered("PreToolUse"):
        register("PreToolUse", "pr_merge_gate", pr_merge_gate_surface)
    if "pr_create_gate" not in registered("PreToolUse"):
        register("PreToolUse", "pr_create_gate", pr_create_gate_surface)

    # Second door. PostToolUse carries surfaces that report on what just
    # happened rather than gating what is about to.
    if "letter_claims" not in registered("PostToolUse"):
        register("PostToolUse", "letter_claims", letter_claims_surface)

    # PostToolUse on purpose: the file is already written, and written is when a
    # hook goes live. Checking before the edit would check the old contents.
    if "hook_syntax" not in registered("PostToolUse"):
        register("PostToolUse", "hook_syntax", hook_syntax_surface)

    # Third door, 2026-09-08. Each of these retires a shell registration in the
    # SAME change -- the tracker's own rule, learned the hard way when
    # deletion_discipline ran from both places for hours and the swallow the
    # migration existed to remove was still running underneath the fix for it.
    for name, module, attr, wants_prompt in _PROMPT_SURFACES:
        if name not in registered("UserPromptSubmit"):
            register(
                "UserPromptSubmit",
                name,
                _prompt_text_surface(name, module, attr, wants_prompt),
            )
    if "auto_goal" not in registered("UserPromptSubmit"):
        register("UserPromptSubmit", "auto_goal", auto_goal_surface)
    if "correction_marker" not in registered("UserPromptSubmit"):
        register("UserPromptSubmit", "correction_marker", correction_marker_surface)

    # Second compose-start batch, appended rather than placed.
    #
    # I first wrote a comment here claiming pre_response_context goes FIRST
    # among the speakers, reasoning that the biggest block should lead. Then I
    # printed the roster and it was sixth -- the comment described a design I
    # had not implemented, which is the painted-door shape in a docstring.
    #
    # Corrected to the truth AND the order left alone, because appending is
    # right for a different reason than the one I invented: in settings.json
    # these two came after the surfaces already migrated, and a migration moves
    # WHERE a decision lives without re-deciding anything. Re-ranking them here
    # would be a design change smuggled in under a port.
    if "pre_response_context" not in registered("UserPromptSubmit"):
        register("UserPromptSubmit", "pre_response_context", pre_response_context_surface)
    if "context_heartbeat" not in registered("UserPromptSubmit"):
        register("UserPromptSubmit", "context_heartbeat", context_heartbeat_surface)

    # Fourth door, 2026-09-08. Order matters here in a way it does not on the
    # other doors: summary_room REFUSES, and the router runs every surface
    # before reporting, so the recorders below it still do their work on a turn
    # that is about to be sent back. That is deliberate -- a refused reply is
    # still a reply I wrote, and the spans in it are still worth recording.
    for name, module, attr in _TRANSCRIPT_AUDITS:
        if name not in registered("Stop"):
            register("Stop", name, _transcript_audit_surface(name, module, attr))
    if "time_estimate" not in registered("Stop"):
        register("Stop", "time_estimate", time_estimate_surface)
    if "self_demotion_stop" not in registered("Stop"):
        register("Stop", "self_demotion_stop", self_demotion_stop_surface)
    if "summary_room" not in registered("Stop"):
        register("Stop", "summary_room", summary_room_surface)
    for name, module, detect_attr, marker_name in _REACH_DETECTORS:
        if name not in registered("Stop"):
            register(
                "Stop",
                name,
                _reach_detector_surface(name, module, detect_attr, marker_name),
            )
