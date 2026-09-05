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

    # Second door. PostToolUse carries surfaces that report on what just
    # happened rather than gating what is about to.
    if "letter_claims" not in registered("PostToolUse"):
        register("PostToolUse", "letter_claims", letter_claims_surface)

    # PostToolUse on purpose: the file is already written, and written is when a
    # hook goes live. Checking before the edit would check the old contents.
    if "hook_syntax" not in registered("PostToolUse"):
        register("PostToolUse", "hook_syntax", hook_syntax_surface)
