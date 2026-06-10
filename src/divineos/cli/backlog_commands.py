"""`divineos backlog` — append-only structural-debt tracker.

Andrew 2026-06-09: TaskCreate dumps the live task list as a system
reminder every few turns. With ~100 entries it consumed ~37% of
session bytes. The discipline: TaskCreate is for current-arc items
only (<5); long-term debt lives in ``docs/wireup-backlog.md``.

This CLI provides a clean append surface so the markdown stays
parseable when adding entries, plus a read surface for browsing what's
already filed.
"""

from __future__ import annotations

import datetime
import re
from pathlib import Path

import click


BEGIN_MARKER = "<!-- BACKLOG-ENTRIES-BEGIN -->"
END_MARKER = "<!-- BACKLOG-ENTRIES-END -->"


def _backlog_path() -> Path:
    """Resolve the backlog file relative to repo root.

    The file should always be at ``docs/wireup-backlog.md`` from the
    repo root. We climb upward from this module's location until we hit
    a ``.git`` directory.
    """
    cur = Path(__file__).resolve()
    for parent in cur.parents:
        if (parent / ".git").exists():
            return parent / "docs" / "wireup-backlog.md"
    # Fallback: relative to cwd. Test fixtures override via DIVINEOS_BACKLOG_PATH.
    return Path("docs") / "wireup-backlog.md"


def _resolved_path() -> Path:
    """Honor DIVINEOS_BACKLOG_PATH env override (for tests)."""
    import os

    override = os.environ.get("DIVINEOS_BACKLOG_PATH")
    if override:
        return Path(override)
    return _backlog_path()


def _parse_sections(text: str) -> dict[str, list[str]]:
    """Parse the entries block into {cluster: [entry-line, ...]}.

    Entries between BEGIN_MARKER and END_MARKER. Cluster headers are
    ``### <cluster>`` (h3). Entries are list items starting with ``- ``.
    """
    sections: dict[str, list[str]] = {}
    try:
        begin = text.index(BEGIN_MARKER) + len(BEGIN_MARKER)
        end = text.index(END_MARKER)
    except ValueError:
        return sections
    block = text[begin:end]
    current: str | None = None
    for raw in block.splitlines():
        line = raw.rstrip()
        m = re.match(r"^###\s+(.+?)\s*$", line)
        if m:
            current = m.group(1).strip()
            sections.setdefault(current, [])
            continue
        if current is None:
            continue
        if line.startswith("- "):
            sections[current].append(line)
        elif sections[current] and line.startswith("  "):
            # Continuation of the previous entry (multi-line description).
            sections[current][-1] = sections[current][-1] + "\n" + line
    return sections


def _render_sections(sections: dict[str, list[str]]) -> str:
    """Render sections back to markdown."""
    out: list[str] = [""]
    for cluster in sorted(sections.keys()):
        out.append(f"### {cluster}")
        out.append("")
        for entry in sections[cluster]:
            out.append(entry)
        out.append("")
    return "\n".join(out)


def add_entry(title: str, cluster: str, description: str = "") -> Path:
    """Append a backlog entry under the named cluster. Returns the
    backlog file path so callers can confirm."""
    path = _resolved_path()
    if not path.exists():
        raise FileNotFoundError(
            f"Backlog file not found at {path}. Create docs/wireup-backlog.md first."
        )
    text = path.read_text(encoding="utf-8")
    sections = _parse_sections(text)
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    entry_lines = [f"- **{title.strip()}** [filed {today}]"]
    if description.strip():
        entry_lines.append(f"  {description.strip()}")
    entry = "\n".join(entry_lines)
    sections.setdefault(cluster, []).append(entry)

    rendered = _render_sections(sections)
    begin = text.index(BEGIN_MARKER) + len(BEGIN_MARKER)
    end = text.index(END_MARKER)
    new_text = text[:begin] + "\n" + rendered + "\n" + text[end:]
    path.write_text(new_text, encoding="utf-8")
    return path


def list_entries(cluster: str | None = None) -> dict[str, list[str]]:
    """Return entries grouped by cluster, optionally filtered."""
    path = _resolved_path()
    if not path.exists():
        return {}
    sections = _parse_sections(path.read_text(encoding="utf-8"))
    if cluster:
        return {cluster: sections.get(cluster, [])}
    return sections


def register(cli: click.Group) -> None:
    """Register the backlog command group."""

    @cli.group("backlog")
    def backlog_group() -> None:
        """Append-only structural-debt tracker for non-current-arc work."""

    @backlog_group.command("add")
    @click.argument("title")
    @click.option("--cluster", required=True, help="Short cluster name (e.g. gates, briefing).")
    @click.option("--description", "-d", default="", help="One-line description.")
    def add_cmd(title: str, cluster: str, description: str) -> None:
        """Append a backlog entry."""
        try:
            path = add_entry(title, cluster, description)
        except FileNotFoundError as e:
            click.secho(f"[!] {e}", fg="red")
            raise click.exceptions.Exit(1) from e
        click.secho(f"[+] Filed under [{cluster}]: {title}", fg="green")
        click.secho(f"    {path}", fg="bright_black")

    @backlog_group.command("list")
    @click.option("--cluster", default=None, help="Filter to one cluster.")
    def list_cmd(cluster: str | None) -> None:
        """Browse the backlog, optionally filtered by cluster."""
        sections = list_entries(cluster)
        if not sections or all(not v for v in sections.values()):
            click.secho("[~] Backlog empty for this filter.", fg="bright_black")
            return
        for name, entries in sections.items():
            if not entries:
                continue
            click.secho(f"\n=== {name} ({len(entries)}) ===", fg="cyan", bold=True)
            for entry in entries:
                click.echo(entry)
