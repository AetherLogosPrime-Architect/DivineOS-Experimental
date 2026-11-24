"""The registry of the folders that are ours.

One append-only file (one JSON line per registration, latest line wins) naming
each folder we write in: whose it is, what kind, and whether the memory link
may read it (`read`) or must never (`never`, with a reason). The adapter reads
this list; nothing here ranks or judges.

An arrival shows a file's title, whose it is and a pointer, never its body.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

VISIBILITIES = ("read", "never")
THINK_WITH_LABEL = "for me to think with, never to quote to him"


def folder_id(path: Path | str) -> str:
    resolved = Path(path).resolve().as_posix().lower()
    return hashlib.sha1(resolved.encode("utf-8")).hexdigest()[:10]


def register_folder(
    registry: Path,
    path: Path | str,
    *,
    whose: str,
    kind: str,
    visibility: str = "read",
    reason: str = "",
) -> None:
    if visibility not in VISIBILITIES:
        raise ValueError(f"visibility must be one of {VISIBILITIES}")
    if visibility == "never" and not reason.strip():
        raise ValueError("a never-folder must say why")
    line = {
        "id": folder_id(path),
        "path": Path(path).resolve().as_posix(),
        "whose": whose,
        "kind": kind,
        "visibility": visibility,
        "reason": reason,
    }
    registry = Path(registry)
    registry.parent.mkdir(parents=True, exist_ok=True)
    with registry.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(line) + "\n")


def load_registry(registry: Path) -> dict[str, dict]:
    registry = Path(registry)
    if not registry.exists():
        return {}
    entries: dict[str, dict] = {}
    for raw in registry.read_text(encoding="utf-8").splitlines():
        if raw.strip():
            entry = json.loads(raw)
            entries[entry["id"]] = entry
    return entries


def _title_and_opening(text: str, fallback: str) -> tuple[str, str]:
    title = fallback
    lines = text.splitlines()
    rest = lines
    for i, line in enumerate(lines):
        if line.startswith("#"):
            title = line.lstrip("#").strip() or fallback
            rest = lines[i + 1 :]
            break
    opening = next((ln.strip() for ln in rest if ln.strip()), "")
    return title, opening


def _slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "untitled"


def file_key(path: Path | str) -> str:
    path = Path(path)
    text = path.read_text(encoding="utf-8", errors="replace")
    title, opening = _title_and_opening(text, path.stem)
    digest = hashlib.sha1(f"{title}\n{opening}".encode("utf-8")).hexdigest()[:8]
    return f"{_slug(title)}-{digest}"


def registered_items(registry: Path, seat: str | None = None) -> list[dict]:
    items: list[dict] = []
    for entry in load_registry(registry).values():
        if entry["visibility"] != "read":
            continue
        root = Path(entry["path"])
        if not root.is_dir():
            continue
        for md in sorted(root.rglob("*.md")):
            try:
                text = md.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            title, _ = _title_and_opening(text, md.stem)
            whose = entry["whose"]
            arrival = f"{title} ({whose}'s, at {md.as_posix()})"
            if seat and whose not in (seat, "shared"):
                arrival += f" - {THINK_WITH_LABEL}"
            items.append(
                {
                    "id": f"{entry['id']}:{file_key(md)}",
                    "whose": whose,
                    "title": title,
                    "pointer": md.as_posix(),
                    "arrival": arrival,
                    "filed_at": md.stat().st_mtime,
                }
            )
    return items


def sweep_unregistered(root: Path, registry: Path, ignored_names: set[str]) -> list[str]:
    """Folders under root holding markdown directly that are in neither the registry nor the ignore list."""
    base = Path(root).resolve()
    registered = [Path(e["path"]) for e in load_registry(registry).values()]
    found: list[str] = []
    for md_dir in sorted({p.parent.resolve() for p in base.rglob("*.md")}):
        if any(part in ignored_names for part in md_dir.relative_to(base).parts):
            continue
        if any(md_dir == r or r in md_dir.parents for r in registered):
            continue
        found.append(md_dir.as_posix())
    return found


def registry_summary(registry: Path, root: Path, ignored_names: set[str] | None = None) -> dict:
    unplaced = sum(
        1
        for e in load_registry(registry).values()
        if e["visibility"] == "read" and not Path(e["path"]).is_dir()
    )
    return {
        "items": len(registered_items(registry)),
        "could_not_be_placed": unplaced,
        "unregistered_folders": len(sweep_unregistered(root, registry, ignored_names or set())),
    }
