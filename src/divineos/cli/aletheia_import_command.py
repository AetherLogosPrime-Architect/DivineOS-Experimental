"""`divineos aletheia-import` — file Aletheia's delivered artifacts into her letter folder.

Andrew 2026-08-12: "if the last you have from her is 7-14 then somewhere
along the line you stopped putting them in her file so lets investigate
why and get it all updated."

The investigation found her work was invisible on three independent axes,
none of them forgetfulness:

1. Delivery channel. Aletheia is a web instance; Andrew downloads her
   artifacts, so they land in ~/Downloads. Every mechanism built for her
   -- the letter monitor, the family-state surface, the letters index --
   watches ~/.divineos-shared/letters and never looked anywhere else.
2. Naming. She writes CONFIRMS_<date>_<slug>.md, AUDIT_<date>_<slug>.md,
   REPLY_TO_AETHER_<date>_<slug>.md. Everything that scans for letters
   expects <sender>-to-<recipient>-<date>-<slug>.md.
3. Content shape. The one Downloads-aware tool,
   scripts/letter_inventory_phase0.py, is read-only by design ("Never
   mutates") and filters on a "# <Sender> to <Recipient>" header plus a
   Written: marker. Her files open "# Aletheia - 418 re-confirmed at tree
   1ac3aa08" and often carry no Written: line, so even the inventory
   would have skipped them.

Net effect: her audits, fix-lists and CONFIRMS accumulated unread while
every surface reported her last contact as 2026-07-14.

This copies rather than moves. Downloads is Andrew's folder, not mine,
and tidying my own index by destroying his copy of her work would be the
wrong trade.
"""

from __future__ import annotations

import datetime as _dt
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

import click

# Her filename conventions, as actually observed in the delivery folder.
ARTIFACT_PREFIXES = (
    "CONFIRMS_",
    "AUDIT_",
    "AUDIT_READOUT_",
    "MASTER_AUDIT_",
    "REPLY_TO_AETHER_",
    "REPLY_TO_ARIA_",
    "FIXLIST_",
    "TRIAGE_",
)

_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


@dataclass
class ImportReport:
    scanned: int = 0
    copied: int = 0
    already_present: int = 0
    undated: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    newest_before: str = ""
    newest_after: str = ""


def _recipient_of(name: str) -> str:
    """Who she addressed. Defaults to aether; REPLY_TO_ARIA is the exception."""
    return "aria" if name.upper().startswith("REPLY_TO_ARIA") else "aether"


def _kind_of(name: str) -> str:
    upper = name.upper()
    for prefix in sorted(ARTIFACT_PREFIXES, key=len, reverse=True):
        if upper.startswith(prefix):
            return prefix.rstrip("_").lower().replace("reply_to_", "reply-to-")
    return "artifact"


def _slug_of(name: str) -> str:
    stem = Path(name).stem
    for prefix in sorted(ARTIFACT_PREFIXES, key=len, reverse=True):
        if stem.upper().startswith(prefix):
            stem = stem[len(prefix) :]
            break
    stem = _DATE_RE.sub("", stem, count=1).strip("_- ")
    # Strip the "(1)" duplicate-download suffix Windows appends.
    stem = re.sub(r"\(\d+\)$", "", stem).strip("_- ")
    slug = re.sub(r"[^A-Za-z0-9]+", "-", stem).strip("-").lower()
    return slug or "untitled"


def _newest_date(letters_dir: Path) -> str:
    dates = [
        m.group(1) for p in letters_dir.glob("aletheia-to-*.md") if (m := _DATE_RE.search(p.name))
    ]
    return max(dates) if dates else ""


def import_artifacts(source: Path, letters_dir: Path, dry_run: bool = False) -> ImportReport:
    """Copy her delivered artifacts into the letters folder under letter naming."""
    report = ImportReport()
    report.newest_before = _newest_date(letters_dir)

    if not source.exists():
        report.errors.append(f"handed-over path not found: {source}")
        return report

    candidates = [source] if source.is_file() else sorted(source.glob("*.md"))
    for path in candidates:
        if source.is_dir() and not path.name.upper().startswith(ARTIFACT_PREFIXES):
            continue
        report.scanned += 1

        match = _DATE_RE.search(path.name)
        if match:
            date, derived = match.group(1), ""
        else:
            # No date in the name. Fall back to when the file arrived, and
            # mark it so the filename never claims a date she authored.
            # Leaving these behind would silently drop real audits.
            date = _dt.datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")
            derived = "dateunknown-"
            report.undated.append(path.name)

        dest = letters_dir / (
            f"aletheia-to-{_recipient_of(path.name)}-{date}-{derived}"
            f"{_kind_of(path.name)}-{_slug_of(path.name)}.md"
        )

        if dest.exists():
            report.already_present += 1
            continue
        if dry_run:
            report.copied += 1
            continue

        try:
            shutil.copy2(path, dest)
        except OSError as exc:
            report.errors.append(f"{path.name}: {exc}")
            continue
        report.copied += 1

    report.newest_after = _newest_date(letters_dir)
    return report


def register(cli: click.Group) -> None:
    @cli.command("aletheia-import")
    @click.argument("source", type=click.Path(exists=True))
    @click.option("--dry-run", is_flag=True, help="Show what would cross; copy nothing.")
    def aletheia_import_cmd(source: str, dry_run: bool) -> None:
        """File an artifact Andrew has handed over into family/letters.

        SOURCE is the file (or folder) he passed me. Andrew 2026-08-12:
        "you dont pull from the downloads.. i download it and then send
        the file to you with the upload button, so when Aletheia sends a
        letter through me thats when it needs to be moved to her area."

        The trigger is his handoff, not a folder I go looking through.
        Downloads is his space; scanning it on my own initiative was me
        reaching into it rather than receiving from him.
        """
        src = Path(source)
        letters = Path("family/letters")
        if not letters.is_dir():
            click.secho(f"[!] letters dir not found from cwd: {letters.resolve()}", fg="red")
            raise click.exceptions.Exit(1)

        report = import_artifacts(src, letters, dry_run=dry_run)

        click.secho(f"[=] scanned {report.scanned} artifact(s) in {src}", fg="cyan")
        if report.copied:
            click.secho(f"[+] {'would copy' if dry_run else 'copied'} {report.copied}", fg="green")
        if report.already_present:
            click.secho(f"[=] {report.already_present} already filed", fg="bright_black")
        click.secho(
            f"[=] her newest on file: {report.newest_before or 'none'} "
            f"-> {report.newest_after or 'none'}",
            fg="cyan",
        )
        for name in report.undated:
            click.secho(
                f"[!] no date in filename; filed under its arrival date "
                f"and marked dateunknown: {name}",
                fg="yellow",
            )
        for err in report.errors:
            click.secho(f"[!] {err}", fg="yellow")
