"""Auto-next-task surface for pre-response context -- now the task belt's.

Andrew 2026-06-20: "the todo list itself is what needs work, it needs
automated so you always know what the next task is."

The structural fix was to surface the next task in every pre-response context,
so the next concrete action shows up without me invoking the CLI. The right
path becomes the cheap path because there is no query-step between me and the
work.

WHAT IT WAS, AND WHY IT IS NOW A THIN DOOR. Until 2026-09-23 this module chose
ONE item by strict drawer order -- overdue prereg, then audit, then
correction, then structural fix, then goal -- with a one-turn-in-five reserved
slot added on 2026-08-28 for the starved structural-fix drawer. Measured the
day it was replaced: it showed a LOW audit item from July as the next task,
week after week, while hundreds of his corrections and my own repairs sat
under it, and context_dedup hid even that once it stopped changing.

Andrew, same day: *"the todo list should have a relevance/priority/most
beneficial task sorter.. so critical, severe or tasks that have wide reach get
chosen first.. something should pull from the todo list.. erase it from the
todo list as it goes into your current todo folder.. and then when you
complete the task it should mark it complete.. archive it.. and go pull
another one"*. That is ``core/task_belt``: ranked across drawers, a current
list of three pulled automatically, a reserved slot for the oldest item below
the top tier (the August starvation guard, kept), and a prompt count on each
item so a stuck task gets louder instead of disappearing.

The goal lane is not carried over. Goals are shown by the HUD and required by
the goal gate, and the belt's pile is never empty, so the lane's purpose (the
surface never goes quiet for lack of work) is met without it.
"""

from __future__ import annotations


def build_next_task_surface() -> str:
    """Return the current-list block, or "" when every drawer is empty."""
    from divineos.core.task_belt import surface

    return surface()


def build_next_task_residual() -> str:
    """The line that survives dedup: every current item, named."""
    from divineos.core.task_belt import residual

    return residual()


__all__ = [
    "build_next_task_residual",
    "build_next_task_surface",
]
