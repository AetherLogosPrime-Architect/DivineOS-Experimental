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


def install() -> None:
    """Register every surface. Idempotent — safe to call from each doorbell."""
    from divineos.core.hook_router import registered

    if "must_read" not in registered("PreToolUse"):
        register("PreToolUse", "must_read", must_read_surface)
