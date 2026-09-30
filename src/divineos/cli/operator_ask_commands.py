"""Asks to Andrew, reachable at last: file one, list them, resolve one.

WHY THESE EXIST, AND WHY THEY COME BEFORE THE GATE (council-5d151c9afad6).

``core/operator_asks.py`` was built 2026-08-19 for his correction: *"if you ask
me something, and i ignore it, you continue to ask until i resolve it, because
i miss it in the walls of text sometimes."* It has a store, a re-raising
surface, and plain-words discipline. It has never had a command.

So filing an ask meant hand-writing Python, and the store has been empty ever
since — which reads exactly like nothing needing him, because an empty list is
what a healthy system looks like too. Same shape as game-walking with four
documents and no code, met twice already in one day.

I nearly shipped the work-holding gate on top of that, justifying it with
*filing is the lazy path because it buys the re-raise*. That premise was false
and I never checked what filing actually cost. A wall whose only door requires
hand-written Python makes the bypass the normal path from the first hour, and
the gate would have measured nothing. The door comes before the wall.

THE PLAIN FIELD IS REQUIRED AND STAYS REQUIRED. His other half of the same
correction: *"your asks should be in the circle as well.. i notice alot of them
are in the jargon space so i dont know what im being asked and im waiting for a
translation that never comes."* An ask he cannot parse is not an ask. Making
this optional would let me clear the gate while handing him something
unanswerable — the original defect wearing the new mechanism.

WHAT ``ask-resolve`` IS FOR, AND THE DRIFT IT WILL CARRY. It is the release
valve, and a valve with no release deadlocks, so it cannot be removed or made
hard. That also makes it where the pressure goes: the predictable degradation
is not refusing the discipline but resolving my own asks to unblock myself,
each resolution reasonable on its own. Nothing catches an instance. The reason
text is recorded so a later reader can see the RATE, which is the only thing
that shows a habit.
"""

from __future__ import annotations

import click

from divineos.core.operator_asks import (
    ask_andrew,
    format_open_asks,
    open_asks,
    resolve_ask,
)


def register(cli: click.Group) -> None:
    """Attach the operator-ask commands to the CLI."""

    @cli.command("ask-andrew")
    @click.argument("question")
    @click.option(
        "--plain",
        required=True,
        help="The same ask in words he can answer without reading any code.",
    )
    @click.option("--context", default="", help="What made this necessary.")
    def ask_andrew_cmd(question: str, plain: str, context: str) -> None:
        """File something that genuinely needs Andrew, and hold work on it."""
        ask_id = ask_andrew(question=question, plain=plain, context=context)
        click.echo(f"[ask] filed: {ask_id}")
        click.echo("[ask] New substrate work is held until he answers or this is resolved.")
        click.echo("[ask] A REPORT IS NOT AN ASK — file only when the answer is his to give.")

    @cli.command("asks")
    def asks_cmd() -> None:
        """What is still waiting on him."""
        rows = open_asks()
        if not rows:
            # An empty store read as "nothing needs him" for a month while the
            # only way to fill it was hand-written Python. Say which it is.
            click.echo("[ask] nothing open. The store is reachable now, so this is a real zero.")
            return
        click.echo(format_open_asks())

    @cli.command("ask-resolve")
    @click.argument("ask_id")
    @click.argument("resolution")
    def ask_resolve_cmd(ask_id: str, resolution: str) -> None:
        """Close an ask — because he answered, or because it stopped needing him."""
        ok = resolve_ask(question_id=ask_id, resolution=resolution)
        if not ok:
            # The store reports whether the row was found. Passing that through
            # costs nothing; reporting a miss as a resolve would make the hold
            # unfalsifiable.
            raise SystemExit(f"[ask] no open ask with id {ask_id!r} — nothing resolved.")
        click.echo(f"[ask] resolved: {ask_id}")
        click.echo(
            "[ask] Resolving my own ask is the release this design depends on, "
            "and it is where the pressure goes. The reason is on the record so "
            "the RATE is readable — an instance never looks wrong."
        )


__all__ = ["register"]
