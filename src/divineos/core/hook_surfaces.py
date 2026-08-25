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

    # Second door. PostToolUse carries surfaces that report on what just
    # happened rather than gating what is about to.
    if "letter_claims" not in registered("PostToolUse"):
        register("PostToolUse", "letter_claims", letter_claims_surface)
