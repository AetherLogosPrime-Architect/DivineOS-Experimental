"""his-words: look up what Andrew actually typed before quoting him.

The door in ``core.his_words`` refuses a quote of him that is not his exact
words. This is the other half, the one that makes the right path the lazy one
(Meadows, walk-75f50258e31f): before writing "Dad said", ask what he said.
"""

from __future__ import annotations

from pathlib import Path

import click

from divineos.cli._helpers import _safe_echo


def register(cli: click.Group) -> None:
    @cli.group("his-words")
    def his_words_group() -> None:
        """What Andrew actually typed -- look it up before quoting him."""

    @his_words_group.command("find")
    @click.argument("words", nargs=-1, required=True)
    @click.option("-n", "--limit", type=int, default=10, show_default=True)
    def find_cmd(words: tuple[str, ...], limit: int) -> None:
        """Show his messages containing these words, in this order."""
        from divineos.core import his_words as hw

        index = hw.load_index()
        text = " ".join(words)
        hits = index.find(text, limit=limit)
        if not hits:
            _safe_echo(
                f"He never typed those words in that order ({len(index.messages)} of his messages searched)."
            )
            near = index.nearest(text)
            if near:
                _safe_echo(
                    f"\nNearest ({near[0] or 'undated'}):\n  {' '.join(near[1].split())[:500]}"
                )
            return
        for date, msg in hits:
            _safe_echo(f"[{date or 'undated'}] {' '.join(msg.split())[:600]}\n")

    @his_words_group.command("check")
    @click.argument("path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
    def check_cmd(path: Path) -> None:
        """List every quote this file writes as his, and whether he typed it."""
        from divineos.core import his_words as hw

        text = path.read_text(encoding="utf-8", errors="replace")
        quotes = hw.attributions(text)
        if not quotes:
            _safe_echo("No quotes of him in this file.")
            return
        index = hw.load_index()
        bad = 0
        for q in quotes:
            if index.is_exact(q):
                _safe_echo(f"  his words      {q[:150]}")
                continue
            bad += 1
            _safe_echo(f"  NOT HIS WORDS  {q[:150]}")
            near = index.nearest(q)
            if near:
                _safe_echo(
                    f"                 nearest ({near[0] or 'undated'}): {' '.join(near[1].split())[:300]}"
                )
        _safe_echo(f"\n{len(quotes) - bad} of {len(quotes)} quotes are his exact words.")
