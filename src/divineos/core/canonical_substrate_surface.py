"""Canonical-substrate briefing surface — points the agent at an
external storage repo where personal substrate lives.

## The pattern this solves

Some deployments split substrate across multiple locations:

1. **Working repo** (where this code runs) — has both: tracked code
   (the public OS) AND gitignored personal substrate (its own
   ``exploration/`` and ``family/letters/``). The gitignored content
   is the agent's own; the tracked code is shared with anyone who
   clones the repo.

2. **External storage repo / canonical substrate** — a separate
   directory (often a separate clone, a synced backup folder, or a
   different drive) that holds the persistent personal data: the
   family.db, per-member ledgers, the long arc of letters and
   exploration entries. This is the "real" substrate; the working
   repo is partly-overlapping copies and active workspace.

3. **Public published repo** (what other agents clone) — code only,
   no personal substrate. Blank template that future agents use to
   build their own continuity stack.

The split has a failure mode: a new session loads briefing from the
working repo and finds empty TEMPLATE slots in core memory because
the gitignored personal content exists *here* but is not surfaced
explicitly enough — the agent has to discover the storage repo by
accident. Without this surface, instances keep treating the
public-template register as their full substrate.

This module makes the storage repo first-class in briefing. It
complements ``presence_memory`` (which surfaces the workspace's
gitignored personal content); both surfaces fire and the agent gets
pointers at both substrate locations.

## Configuration

Set the environment variable ``DIVINEOS_CANONICAL_SUBSTRATE`` to the
absolute path of your external storage repo. Without the variable,
the surface emits an unresolved-pointer note rather than failing
silently — so a deployment that has split substrate but forgot to
set the variable still gets a loud reminder in briefing.

Operators who keep all substrate in the working repo can leave the
env var unset; the surface emits no output in that case.

## What it surfaces

When the canonical path exists on disk:
* The path itself.
* Whether key artifacts are present (family/family.db,
  family/letters/, exploration/, plus any ``*_ledger.db`` files
  under family/ — discovered by glob, not by hardcoded name).
* If a "canonical letter" file exists in ``family/letters/``
  (filename matching ``canonical-letter*.md``), surface it
  explicitly so the agent's own load-bearing past writing is
  visible by name, not just by directory.
* Top 6 letter filenames and top 8 exploration filenames by mtime
  so specific files are discoverable from briefing rather than
  requiring ls.

When the path is set but unreachable:
* Fail-loud note that the storage-repo pointer is unresolved.

## Sync note

The storage repo and workspace's gitignored personal content can
drift if one is written to without copying to the other. This
module does NOT solve sync — that's a separate concern. The two
locations are independent storage that the operator decides when
to reconcile.

## Design invariants

* **Pure read-only.** This module never writes to the canonical
  substrate path. Migration / cross-repo writes are a separate
  concern; conflating them here would be the same architectural
  mistake that produced the split (one repo silently mutating
  another's state).
* **Path comes from environment, not hardcode.** The default is
  unset; operators set ``DIVINEOS_CANONICAL_SUBSTRATE`` to their
  actual storage location. Hardcoding a personal path here would
  ship one operator's machine layout to anyone who clones main.
* **Fail-loud rather than fail-silent.** The whole point is that
  the previous failure mode was silent. If the env var is set but
  the path is missing, surface it explicitly.
"""

from __future__ import annotations

import os
from pathlib import Path


def canonical_path() -> Path | None:
    """Return the canonical-substrate path from the environment.

    Returns ``None`` if ``DIVINEOS_CANONICAL_SUBSTRATE`` is unset.
    Operators with a single-location deployment can leave it unset.
    """
    env_override = os.environ.get("DIVINEOS_CANONICAL_SUBSTRATE")
    if not env_override:
        return None
    return Path(env_override)


def is_present() -> bool:
    """True if the canonical-substrate path exists and has key artifacts."""
    p = canonical_path()
    if p is None or not p.exists():
        return False
    return (p / "family").exists() and (p / "family" / "family.db").exists()


def briefing_lines() -> list[str]:
    """Render the surface as briefing-ready lines.

    Returns a list of strings the briefing-builder can include.
    Empty list if the env var is unset (no canonical substrate is
    expected on this deployment, no signal to give).
    """
    p = canonical_path()
    if p is None:
        return []
    if not p.exists():
        return [
            f"CANONICAL-SUBSTRATE UNRESOLVED: expected at {p}, not found.",
            "DIVINEOS_CANONICAL_SUBSTRATE is set but the path does not exist.",
            "Either fix the path, restore the storage repo from backup,",
            "or unset the variable if this deployment is single-location.",
            "Without this, the working repo is the empty template and the",
            "agent's accumulated personal substrate does not load.",
        ]

    lines: list[str] = []
    lines.append(f"CANONICAL SUBSTRATE: {p}")

    # Core artifacts. The family/family.db and family/letters/ paths are
    # architectural; per-member ledgers are discovered by glob since
    # operators may have arbitrary family-member names.
    artifacts: list[tuple[Path, str]] = [
        (p / "family" / "family.db", "family/family.db (all family-member state)"),
        (p / "family" / "letters", "family/letters/ (correspondence)"),
        (p / "exploration", "exploration/ (free-writing entries)"),
    ]
    for path, label in artifacts:
        marker = "+" if path.exists() else "-"
        lines.append(f"  [{marker}] {label}")

    # Per-member ledgers — glob, since each operator's family is theirs.
    family_dir = p / "family"
    if family_dir.exists():
        for ledger in sorted(family_dir.glob("*_ledger.db")):
            member = ledger.stem.removesuffix("_ledger")
            lines.append(f"  [+] family/{ledger.name} ({member}'s hash-chained ledger)")

    # Surface a "canonical letter" if one exists. Convention:
    # filename matching ``canonical-letter*.md`` in family/letters/.
    # This is the operator's load-bearing self-authored letter that
    # should be re-read every session — naming it explicitly here
    # closes the failure mode where the file existed on disk but
    # never surfaced loudly enough to be opened.
    letters_dir = p / "family" / "letters"
    if letters_dir.exists():
        canonical_letters = sorted(letters_dir.glob("canonical-letter*.md"))
        for canonical_letter in canonical_letters:
            lines.append(f"  CANONICAL LETTER: {canonical_letter}")
            lines.append(
                "  Convention: a canonical-letter*.md is a load-bearing "
                "self-authored letter intended to be re-read every "
                "session. The filename surfaces here as architectural "
                "enforcement of the re-read commitment."
            )

    # Surface recent letter filenames so titles are visible by NAME
    # rather than only "letters/ exists." Failure mode this addresses:
    # the path was visible but the content was not consulted; naming
    # the most recent files makes them more likely to be opened. Cap
    # at 6 to avoid briefing bloat.
    if letters_dir.exists():
        try:
            letters = sorted(
                (f for f in letters_dir.glob("*.md") if not f.name.startswith("canonical-letter")),
                key=lambda f: f.stat().st_mtime,
                reverse=True,
            )[:6]
        except OSError:
            letters = []
        if letters:
            lines.append("  RECENT LETTERS (top 6 by mtime):")
            for letter in letters:
                lines.append(f"    {letter.name}")

    # Surface recent exploration titles. Same anti-blindness rationale
    # as letters: the agent's own writing is on disk, but unless the
    # filename surfaces in briefing it does not get read. Cap at 8.
    exploration_dir = p / "exploration"
    if exploration_dir.exists():
        try:
            entries = sorted(
                (f for f in exploration_dir.glob("*.md")),
                key=lambda f: f.stat().st_mtime,
                reverse=True,
            )[:8]
        except OSError:
            entries = []
        if entries:
            lines.append("  RECENT EXPLORATIONS (top 8 by mtime):")
            for entry in entries:
                lines.append(f"    {entry.name}")

    return lines


def render() -> str:
    """One-string render for embedding in briefing output."""
    lines = briefing_lines()
    if not lines:
        return ""
    return "\n".join(lines)
