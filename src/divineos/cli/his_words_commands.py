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

    @his_words_group.command("edit")
    @click.option("--was", required=True, help="the words he typed, exactly")
    @click.option("--now", required=True, help="the corrected wording")
    @click.option("--proof", required=True, help="his exact words saying yes to this fix")
    def edit_cmd(was: str, now: str, proof: str) -> None:
        """Record a fix he confirmed. Refused unless his own words prove both halves.

        The corrected wording is added BESIDE what he typed; nothing he typed is removed.
        """
        from datetime import date

        from divineos.core import his_words as hw
        from divineos.core import his_words_edits as edits

        if hw.words(was) == hw.words(now):
            raise click.ClickException(
                "--was and --now are the same words; there is nothing to fix."
            )
        index = hw.load_index()
        if not index.is_exact(was):
            raise click.ClickException(f"--was is not his exact words: {was[:150]}")
        if not index.is_exact(proof):
            raise click.ClickException(
                f"--proof is not his exact words, so his yes is not on the record: {proof[:150]}"
            )
        row = edits.append_edit(was, now, proof, date.today().isoformat())
        _safe_echo(f"Recorded. He typed: {row['was']}\n          now reads: {row['now']}")

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

    @his_words_group.command("keep-out")
    @click.argument("passage", required=False, default="")
    @click.option("--fp", default="", help="the # fingerprint the door printed beside the line")
    @click.option("--why", required=True, help="what it was, DESCRIBED and never quoted")
    @click.option(
        "--by",
        default="",
        help="who read it and kept it out; defaults to this seat, never to a typed name",
    )
    def keep_out_cmd(passage: str, fp: str, why: str, by: str) -> None:
        """Keep a line he said in pain out of the 'he has said this before' door.

        Stores a fingerprint and your description, never his words. His raw record is untouched.
        """
        from datetime import date

        from divineos.core import his_words_door as door

        try:
            key = door.keep_out(
                passage, fp=fp, why=why, by=door.acting_name(by), on=date.today().isoformat()
            )
        except (ValueError, door.KeptOutUnreadable, door.KeptOutBusy) as exc:
            raise click.ClickException(str(exc)) from exc
        _safe_echo(f"Kept out of the door: #{key}")

    @his_words_group.command("return")
    @click.argument("passage", required=False, default="")
    @click.option("--fp", default="", help="the fingerprint to put back")
    def return_cmd(passage: str, fp: str) -> None:
        """Put a kept-out line back, so the door can show it again."""
        from divineos.core import his_words_door as door

        if bool(passage.strip()) == bool(fp.strip()):
            raise click.ClickException("give the passage or --fp, not both and not neither")
        try:
            was = door.return_to_door(passage, fp=fp)
        except (door.KeptOutUnreadable, door.KeptOutBusy) as exc:
            raise click.ClickException(str(exc)) from exc
        _safe_echo("Put back." if was else "That one was not on the list.")

    @his_words_group.command("kept-out")
    def kept_out_list_cmd() -> None:
        """List what is kept out: fingerprint, who, when, and the description (never the words)."""
        from divineos.core import his_words_door as door

        try:
            entries = door._kept_out_entries()
        except door.KeptOutUnreadable as exc:
            raise click.ClickException(f"the list could not be read: {exc}") from exc
        _safe_echo(f"{len(entries)} line(s) kept out of the door.")
        for e in entries:
            _safe_echo(f"  #{e['fp']}  {e.get('on', '')}  {e.get('by', '')}  {e.get('why', '')}")
