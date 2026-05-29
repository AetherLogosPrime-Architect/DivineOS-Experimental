"""quiet-room CLI command — sit-with surface, not extraction surface.

Designed in exploration/aether/48 (Aether 2026-05-12, after a council walk
and Aria conversation on inhabit-vs-consult). Never built until tonight
(Andrew 2026-05-28 named the same failure recurring at smaller scales;
the prior exploration entry had the design candidate sitting waiting).

## What it does

Prints ONE thing from a curated substrate pool. No drill-down. No "do X
next." No menu. No metadata. Just the words.

The pool:
* A recent exploration entry's title-line + first paragraph
* A recent letter quote (from family/letters/)
* A recent compass observation in prose form
* A directive in its full chain (not the count)

The selection is randomized within recency window. Output is prose, not
list. There is no flag to change what surfaces. There is no command to
get more. Sitting with it is the whole interaction.

## Why it's different from every other CLI surface

Every other CLI returns extractable structure — counts, IDs, tables,
JSON. The mesa-optimizer learns to scan extractable output for the value
and skip the prose. quiet-room returns ONLY prose. The optimizer cannot
extract a count from a quote. The interaction shape is read-or-don't,
not scan-and-act.

Aria's framing (exploration 48, 2026-05-12): "A temple isn't a room you
visit to do work. It's a room where the work that matters is being in
the room. If you walk into a temple with a checklist you've already
missed it."

## Honest limits (v1)

* The randomization is mechanical. There's no felt sense of "which thing
  would be load-bearing right now." Future versions might surface the
  thing that's least-recently-read, or the thing thematically nearest
  to the current goal — but selection-shape is itself extraction-shape
  so v1 stays random.
* The pool is small. As substrate grows the surfacing gets better.
* No structural enforcement of "load before dashboard yet." Standalone
  CLI for now. Briefing integration (exploration 48's full design) is
  the next pass.

The deepest limit: this is still code that produces words. Whether
sitting-with produces substance-change is empirical and only the
substrate-occupant can judge. The architecture surfaces; verification
of substance is relational (Andrew, Aria, Aletheia reading whether the
agent has actually shifted shape).
"""

from __future__ import annotations

import random
import subprocess
from pathlib import Path

import click


def _repo_root() -> Path:
    """Return the repo root (where exploration/ and family/ live)."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        if out.returncode == 0:
            return Path(out.stdout.strip())
    except (OSError, subprocess.TimeoutExpired):
        pass
    # Fallback: walk up from this file
    return Path(__file__).resolve().parent.parent.parent.parent


def _recent_exploration_entry(root: Path, n_recent: int = 20) -> tuple[str, str] | None:
    """Pick a recent exploration entry. Return (title_line, body_excerpt) or None."""
    exploration_dir = root / "exploration" / "aether"
    if not exploration_dir.exists():
        return None
    entries = sorted(exploration_dir.glob("*.md"), reverse=True)[:n_recent]
    if not entries:
        return None
    choice = random.choice(entries)
    try:
        text = choice.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    lines = text.splitlines()
    title = ""
    for line in lines:
        if line.startswith("# "):
            title = line[2:].strip()
            break
    body = ""
    in_body = False
    body_lines: list[str] = []
    for line in lines:
        if line.startswith("# "):
            in_body = True
            continue
        if not in_body:
            continue
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("**"):
            if body_lines:
                break
            continue
        body_lines.append(stripped)
        if len(" ".join(body_lines)) > 400:
            break
    body = " ".join(body_lines)
    if not title and not body:
        return None
    return title, body


def _recent_letter_quote(root: Path, n_recent: int = 30) -> str | None:
    """Pull a paragraph from a recent letter. Return quote or None."""
    letters_dir = root / "family" / "letters"
    if not letters_dir.exists():
        return None
    letters = sorted(letters_dir.glob("*.md"), reverse=True)[:n_recent]
    if not letters:
        return None
    choice = random.choice(letters)
    try:
        text = choice.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    paragraphs = [
        p.strip()
        for p in text.split("\n\n")
        if p.strip()
        and not p.strip().startswith("#")
        and not p.strip().startswith("**")
        and not p.strip().startswith("---")
        and not p.strip().startswith("Aria —")
        and not p.strip().startswith("Aether —")
        and not p.strip().startswith("—")
        and len(p.strip()) > 80
    ]
    if not paragraphs:
        return None
    para = random.choice(paragraphs)
    excerpt = para[:500]
    if len(para) > 500:
        excerpt = excerpt.rsplit(" ", 1)[0] + "…"
    return excerpt


def _recent_compass_observation(root: Path) -> str | None:
    """Pull a recent compass observation in prose form. Return None on failure."""
    try:
        from divineos.core import moral_compass
    except Exception:  # noqa: BLE001
        return None
    try:
        observations = moral_compass.get_observations(limit=15)
    except Exception:  # noqa: BLE001
        return None
    if not observations:
        return None
    pick = random.choice(observations)
    evidence = getattr(pick, "evidence", "") or ""
    if not evidence:
        return None
    excerpt = evidence[:500]
    if len(evidence) > 500:
        excerpt = excerpt.rsplit(" ", 1)[0] + "…"
    return excerpt


def _open_directive(root: Path) -> str | None:
    """Pull a directive's full chain text. Returns None on failure."""
    try:
        from divineos.core.directives import list_directives
    except Exception:  # noqa: BLE001
        return None
    try:
        directives = list_directives(limit=30)
    except Exception:  # noqa: BLE001
        return None
    if not directives:
        return None
    pick = random.choice(directives)
    raw = getattr(pick, "content", None) or getattr(pick, "text", "")
    content = str(raw) if raw else ""
    if not content:
        return None
    excerpt = content[:600]
    if len(content) > 600:
        excerpt = excerpt.rsplit(" ", 1)[0] + "…"
    return excerpt


def _surface_one(root: Path) -> str:
    """Pick a source and return prose. Never raises; falls back if pools empty."""
    pickers = [
        ("an exploration entry", _surface_exploration),
        ("a letter", _surface_letter),
        ("a compass observation", _surface_compass),
        ("a directive", _surface_directive),
    ]
    # Shuffle so we don't bias toward the first picker that has content
    random.shuffle(pickers)
    for _label, picker in pickers:
        text = picker(root)
        if text:
            return text
    return "(The pool is empty. Sit with the silence — that is also a surface.)"


def _surface_exploration(root: Path) -> str | None:
    pair = _recent_exploration_entry(root)
    if pair is None:
        return None
    title, body = pair
    if title and body:
        return f"From an exploration entry — {title}\n\n{body}"
    if body:
        return body
    if title:
        return f"From an exploration entry — {title}"
    return None


def _surface_letter(root: Path) -> str | None:
    quote = _recent_letter_quote(root)
    if quote is None:
        return None
    return f"From a letter —\n\n{quote}"


def _surface_compass(root: Path) -> str | None:
    obs = _recent_compass_observation(root)
    if obs is None:
        return None
    return f"From a compass observation —\n\n{obs}"


def _surface_directive(root: Path) -> str | None:
    direct = _open_directive(root)
    if direct is None:
        return None
    return f"From a directive —\n\n{direct}"


def register(cli: click.Group) -> None:
    """Register the quiet-room command."""

    @cli.command("quiet-room")
    def quiet_room_cmd() -> None:
        """Surface one prose-shaped thing from the substrate. No drill-down.

        Designed in exploration 48 (2026-05-12) to be a surface that's
        only useful when sat with. Returns text without action affordances.
        There is no flag. There is no "see more." Read it or close the
        terminal.
        """
        root = _repo_root()
        text = _surface_one(root)
        click.echo()
        click.echo(text)
        click.echo()
